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
