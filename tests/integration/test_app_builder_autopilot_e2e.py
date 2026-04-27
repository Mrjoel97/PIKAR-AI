# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""End-to-end happy-path test for app-builder autopilot.

Drives a project from idle → done by stepping the orchestrator through
each transition in sequence. External services (research, build plan,
variants, ship) are mocked at module boundary. Supabase is a stateful
MagicMock that records the autopilot_status / autopilot_events updates
the orchestrator emits — close enough to exercise the full state
machine without requiring Docker / a local Postgres.

For a true Postgres-backed integration test, adapt this to use a real
Supabase fixture once Docker is available in CI.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.app_builder_orchestrator import AppBuilderOrchestrator

PROJECT_ID = "11111111-2222-3333-4444-555555555555"
SESSION_ID = "session-001"


def _stateful_supabase() -> MagicMock:
    """Build a MagicMock that loosely tracks app_projects state.

    Reads always return the latest known shape; writes update the shape.
    Good enough to drive the orchestrator through every transition.
    """
    state: dict = {
        "creative_brief": {"what": "landing page", "vibe": "minimal"},
        "design_system": {"colors": []},
        "sitemap": [
            {
                "page": "home",
                "title": "Home",
                "sections": [],
                "device_targets": ["DESKTOP"],
            }
        ],
        "build_plan": [],
        "autopilot_status": "idle",
        "autopilot_events": [],
    }

    client = MagicMock()

    def select_chain(*_args, **_kwargs):
        # The orchestrator's reads always end with .single().execute()
        # returning a MagicMock with .data == state. We don't try to honor
        # the column projection — the orchestrator only reads keys it
        # needs and tolerates extras.
        return MagicMock(data=dict(state))

    select_mock = MagicMock()
    select_mock.eq.return_value.single.return_value.execute.side_effect = (
        select_chain
    )

    def update_chain(payload):
        # Apply payload to our local state mirror so subsequent reads see it.
        state.update(payload)
        chain = MagicMock()
        chain.eq.return_value.execute.return_value = MagicMock(data=[dict(state)])
        return chain

    table_mock = MagicMock()
    table_mock.select.return_value = select_mock
    table_mock.update.side_effect = update_chain

    client.table.return_value = table_mock
    client._state = state  # exposed for test assertions
    return client


@pytest.mark.asyncio
async def test_autopilot_drives_project_from_idle_to_done():
    """Run the full orchestrator chain end-to-end with mocked services."""
    supabase = _stateful_supabase()
    orch = AppBuilderOrchestrator(
        project_id=PROJECT_ID, session_id=SESSION_ID, supabase=supabase
    )

    async def fake_research(_brief):
        yield {
            "step": "ready",
            "data": {
                "colors": [],
                "typography": {},
                "spacing": {},
                "raw_markdown": "",
                "sitemap": [],
            },
        }

    fake_plan = [
        {
            "phase": 1,
            "label": "Core",
            "screens": [{"name": "Home", "page": "home", "device": "DESKTOP"}],
            "dependencies": [],
        }
    ]

    async def fake_variants(*_a, **_kw):
        yield {"step": "variant_generated", "variant_id": "v1", "screen_id": "s1"}
        yield {"step": "ready", "variants": []}

    async def fake_ship(_pid, _targets):
        yield {
            "step": "target_complete",
            "target": "react",
            "url": "https://example/output.zip",
        }
        yield {
            "step": "ship_complete",
            "downloads": {"react": "https://example/output.zip"},
        }

    with (
        patch(
            "app.services.app_builder_orchestrator.run_design_research",
            side_effect=lambda brief: fake_research(brief),
        ),
        patch(
            "app.services.app_builder_orchestrator._generate_build_plan",
            new=AsyncMock(return_value=fake_plan),
        ),
        patch(
            "app.services.app_builder_orchestrator.generate_screen_variants",
            side_effect=lambda *a, **kw: fake_variants(),
        ),
        patch(
            "app.services.app_builder_orchestrator.ship_project",
            side_effect=lambda pid, targets: fake_ship(pid, targets),
        ),
    ):
        # Drive each transition in the same order the endpoints would.
        await orch.run_research_step()
        assert supabase._state["autopilot_status"] == "paused_brief"

        await orch.run_after_brief()
        assert supabase._state["autopilot_status"] == "paused_variant"

        # Simulate user picking a variant — the resume endpoint flips
        # paused_variant → paused_screen directly without orchestrator work.
        supabase._state["autopilot_status"] = "paused_screen"

        # User approved the only screen; advancing should land at paused_ship.
        await orch.run_after_screen_approved(completed_screen_ids=["home"])
        assert supabase._state["autopilot_status"] == "paused_ship"

        # User picked react.
        await orch.run_ship("react")
        assert supabase._state["autopilot_status"] == "done"
        assert supabase._state["stage"] == "done"

    # Narration log should include at least one entry per major phase.
    events = supabase._state["autopilot_events"]
    messages = [e.get("message", "") for e in events]
    joined = " | ".join(messages).lower()
    assert "research" in joined
    assert "build plan" in joined
    assert "home" in joined.lower()
    assert "ship" in joined or "ready" in joined
    assert "app ready" in joined
