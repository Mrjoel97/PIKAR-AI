# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""App Builder Autopilot orchestrator.

Runs the GSD flow autonomously after the user completes the questioning
wizard. Pauses only at meaningful user decisions (brief approval, variant
pick, per-screen approval, ship target).

State transitions persist to `app_projects.autopilot_status`. Narration
events append to `app_projects.autopilot_events` (JSONB array). The
canvas and chat hooks poll those columns; this service does not push
SSE itself.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

from app.services.design_brief_service import _generate_build_plan, run_design_research
from app.services.screen_generation_service import generate_screen_variants
from app.services.ship_service import ship_project

logger = logging.getLogger(__name__)

AutopilotState = Literal[
    "idle",
    "running",
    "paused_brief",
    "paused_variant",
    "paused_screen",
    "paused_ship",
    "failed",
    "done",
]

AUTOPILOT_STATES: set[str] = {
    "idle",
    "running",
    "paused_brief",
    "paused_variant",
    "paused_screen",
    "paused_ship",
    "failed",
    "done",
}


class AppBuilderOrchestrator:
    """Per-project orchestrator. One instance == one autopilot run.

    Lifecycle:
        1. Constructed in `start_autopilot` endpoint.
        2. `await self.run()` schedules an asyncio task; returns immediately.
        3. The task transitions states, calling existing app-builder
           services and persisting state/events between steps.
        4. At each pause point, the task awaits a `resume()` signal that
           the resume endpoint flips by updating autopilot_status.
        5. Terminates by setting state to `done` or `failed`.

    Authorization boundary:
        Methods on this class scope queries by `id` only — they do NOT
        re-check `user_id`. The orchestrator is constructed by trusted
        server-side code (the start/resume autopilot endpoints) AFTER
        the endpoint has already verified that `project_id` belongs to
        the authenticated user. Do NOT instantiate this class with a
        `project_id` taken directly from a user request without a prior
        authorization check.
    """

    def __init__(
        self,
        project_id: str,
        session_id: str,
        supabase: Any,
    ) -> None:
        self.project_id = project_id
        self.session_id = session_id
        self._supabase = supabase

    # ---- state ----
    def set_state(self, state: AutopilotState) -> None:
        if state not in AUTOPILOT_STATES:
            raise ValueError(f"Invalid autopilot state: {state}")
        self._supabase.table("app_projects").update(
            {"autopilot_status": state}
        ).eq("id", self.project_id).execute()

    # ---- narration ----
    def publish_event(
        self,
        kind: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Append a narration event to autopilot_events.

        Read-modify-write on a JSONB array. Acceptable for append-only
        in this scope; if contention surfaces we'd switch to a Postgres
        function with `jsonb_insert`.
        """
        result = (
            self._supabase.table("app_projects")
            .select("autopilot_events")
            .eq("id", self.project_id)
            .single()
            .execute()
        )
        events: list[dict[str, Any]] = (
            (result.data or {}).get("autopilot_events") or []
        )
        events.append(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "kind": kind,
                "message": message,
                "payload": payload or {},
            }
        )
        self._supabase.table("app_projects").update(
            {"autopilot_events": events}
        ).eq("id", self.project_id).execute()

    # ---- failure ----
    def fail(self, error: str) -> None:
        """Mark autopilot as failed and append an error event."""
        self.publish_event(kind="error", message=error)
        self._supabase.table("app_projects").update(
            {
                "autopilot_status": "failed",
                "autopilot_error": error,
            }
        ).eq("id", self.project_id).execute()

    # ---- transitions ----
    async def run_research_step(self) -> None:
        """Run research, persist intermediate progress, pause at paused_brief."""
        result = (
            self._supabase.table("app_projects")
            .select("creative_brief")
            .eq("id", self.project_id)
            .single()
            .execute()
        )
        creative_brief = (result.data or {}).get("creative_brief") or {}

        self.publish_event(kind="status", message="Running design research")

        try:
            async for event in run_design_research(creative_brief):
                step = event.get("step")
                if step == "ready":
                    self.publish_event(
                        kind="status",
                        message="Design brief is ready — review in the canvas",
                        payload={"data_keys": list((event.get("data") or {}).keys())},
                    )
                    self.set_state("paused_brief")
                    return
                if step == "error":
                    self.fail(event.get("message", "research failed"))
                    return
                if step in ("searching", "synthesizing"):
                    self.publish_event(
                        kind="progress",
                        message=event.get("message") or step,
                    )
        except Exception as exc:
            self.fail(f"Research raised: {exc!s}")
            return
        self.fail("Research stream ended without a ready event.")

    async def run_after_brief(self) -> None:
        """Called after brief approval. Generate build plan and start first screen."""
        result = (
            self._supabase.table("app_projects")
            .select("design_system, sitemap")
            .eq("id", self.project_id)
            .single()
            .execute()
        )
        project = result.data or {}
        design_system = project.get("design_system") or {}
        sitemap = project.get("sitemap") or []

        self.publish_event(kind="status", message="Generating build plan")
        try:
            build_plan = await _generate_build_plan(design_system, sitemap)
        except Exception as exc:
            self.fail(f"Build plan failed: {exc!s}")
            return

        # Persist build_plan onto the project so building stage can read it
        self._supabase.table("app_projects").update(
            {"build_plan": build_plan, "stage": "building"}
        ).eq("id", self.project_id).execute()
        self._supabase.table("build_sessions").update({"stage": "building"}).eq(
            "project_id", self.project_id
        ).execute()

        # Begin first screen — defer to run_next_screen (filled in Task 7)
        await self.run_next_screen(build_plan, completed_screen_ids=[])

    async def run_next_screen(
        self,
        build_plan: list[dict],
        completed_screen_ids: list[str],
    ) -> None:
        """Generate variants for the next screen in the build plan and pause."""
        # Find next screen (flat across phases) that's not in completed_screen_ids
        next_screen: dict | None = None
        for phase in build_plan:
            for screen in phase.get("screens") or []:
                screen_id = screen.get("page")  # use page slug as id
                if screen_id and screen_id not in completed_screen_ids:
                    next_screen = screen
                    break
            if next_screen:
                break

        if not next_screen:
            # All screens done — pause at ship target
            self.publish_event(
                kind="status",
                message="All screens approved. Ready to ship — pick a target.",
            )
            self.set_state("paused_ship")
            return

        self.publish_event(
            kind="status",
            message=f"Generating screen: {next_screen.get('name')}",
            payload={"page": next_screen.get("page")},
        )
        try:
            async for event in generate_screen_variants(
                self.project_id,
                next_screen.get("name", ""),
                next_screen.get("page", ""),
            ):
                step = event.get("step")
                if step == "variant_generated":
                    self.publish_event(
                        kind="progress",
                        message=f"Variant ready for {next_screen.get('name')}",
                        payload={"variant_id": event.get("variant_id")},
                    )
                elif step == "ready":
                    self.set_state("paused_variant")
                    return
                elif step == "error":
                    self.fail(event.get("message", "variant generation failed"))
                    return
        except Exception as exc:
            self.fail(f"Variant generation raised: {exc!s}")
            return

    async def run_after_screen_approved(
        self,
        completed_screen_ids: list[str],
    ) -> None:
        """Called after the user approves a screen. Generates the next one."""
        result = (
            self._supabase.table("app_projects")
            .select("build_plan")
            .eq("id", self.project_id)
            .single()
            .execute()
        )
        build_plan = (result.data or {}).get("build_plan") or []
        await self.run_next_screen(build_plan, completed_screen_ids)

    async def run_ship(self, target: str) -> None:
        """Execute the ship pipeline for the chosen target and complete autopilot."""
        if target not in ("react", "pwa", "capacitor", "video"):
            self.fail(f"Invalid ship target: {target}")
            return
        self.publish_event(
            kind="status",
            message=f"Shipping as {target}",
        )
        try:
            async for event in ship_project(self.project_id, [target]):
                step = event.get("step")
                if step == "target_complete":
                    self.publish_event(
                        kind="result",
                        message=f"{event.get('target')} ready",
                        payload={"url": event.get("url")},
                    )
                elif step == "target_failed":
                    self.fail(event.get("error") or "ship target failed")
                    return
                elif step == "ship_complete":
                    self.publish_event(
                        kind="status",
                        message="App ready",
                        payload={"downloads": event.get("downloads") or {}},
                    )
                    self._supabase.table("app_projects").update(
                        {"stage": "done"}
                    ).eq("id", self.project_id).execute()
                    self.set_state("done")
                    return
        except Exception as exc:
            self.fail(f"Shipping raised: {exc!s}")
            return
        self.fail("Ship stream ended without completion.")
