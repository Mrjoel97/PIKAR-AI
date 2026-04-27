"""Unit tests for AppBuilderOrchestrator state machine helpers."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.app_builder_orchestrator import (
    AUTOPILOT_STATES,
    AppBuilderOrchestrator,
)

PROJECT_ID = "aaaaaaaa-0000-0000-0000-000000000001"
SESSION_ID = "session-001"


def _orch(supabase: MagicMock) -> AppBuilderOrchestrator:
    return AppBuilderOrchestrator(
        project_id=PROJECT_ID,
        session_id=SESSION_ID,
        supabase=supabase,
    )


def test_states_cover_spec():
    """The state set must match the spec exactly."""
    assert AUTOPILOT_STATES == {
        "idle",
        "running",
        "paused_brief",
        "paused_variant",
        "paused_screen",
        "paused_ship",
        "failed",
        "done",
    }


def test_set_state_writes_to_supabase():
    supabase = MagicMock()
    orch = _orch(supabase)
    orch.set_state("running")
    supabase.table.return_value.update.assert_called_with(
        {"autopilot_status": "running"}
    )


def test_publish_event_appends_to_jsonb_array():
    supabase = MagicMock()
    # Simulate row.fetchone returning current events array
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"autopilot_events": []}
    )
    orch = _orch(supabase)
    orch.publish_event(kind="status", message="Running research")
    # Last update call should contain autopilot_events with one entry
    update_call = supabase.table.return_value.update.call_args_list[-1]
    new_events = update_call.args[0]["autopilot_events"]
    assert len(new_events) == 1
    assert new_events[0]["kind"] == "status"
    assert new_events[0]["message"] == "Running research"
    assert "ts" in new_events[0]


def test_fail_records_error_and_state():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"autopilot_events": []}
    )
    orch = _orch(supabase)
    orch.fail("Stitch unavailable")
    update_call = supabase.table.return_value.update.call_args_list[-1]
    payload = update_call.args[0]
    assert payload["autopilot_status"] == "failed"
    assert payload["autopilot_error"] == "Stitch unavailable"


@pytest.mark.asyncio
async def test_run_research_step_publishes_status_and_pauses_at_brief():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"creative_brief": {"what": "bakery"}, "autopilot_events": []}
    )
    orch = _orch(supabase)

    async def fake_research(brief):
        yield {"step": "searching", "message": "..."}
        yield {"step": "synthesizing", "message": "..."}
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

    with patch(
        "app.services.app_builder_orchestrator.run_design_research",
        side_effect=lambda brief: fake_research(brief),
    ):
        await orch.run_research_step()

    last_state_call = next(
        c
        for c in reversed(supabase.table.return_value.update.call_args_list)
        if "autopilot_status" in c.args[0]
    )
    assert last_state_call.args[0]["autopilot_status"] == "paused_brief"
    appended_events_calls = [
        c
        for c in supabase.table.return_value.update.call_args_list
        if "autopilot_events" in c.args[0]
    ]
    assert len(appended_events_calls) >= 2


@pytest.mark.asyncio
async def test_run_after_brief_generates_build_plan_and_pauses_at_variant():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={
            "design_system": {"colors": []},
            "sitemap": [
                {
                    "page": "home",
                    "title": "Home",
                    "sections": [],
                    "device_targets": ["DESKTOP"],
                }
            ],
            "autopilot_events": [],
        }
    )
    orch = _orch(supabase)
    fake_plan = [
        {
            "phase": 1,
            "label": "Core",
            "screens": [{"name": "Home", "page": "home", "device": "DESKTOP"}],
            "dependencies": [],
        }
    ]

    async def fake_variants(*_a, **_kw):
        yield {"step": "ready", "variants": []}

    with (
        patch(
            "app.services.app_builder_orchestrator._generate_build_plan",
            new=AsyncMock(return_value=fake_plan),
        ),
        patch(
            "app.services.app_builder_orchestrator.generate_screen_variants",
            side_effect=lambda *a, **kw: fake_variants(),
        ),
    ):
        await orch.run_after_brief()

    last_state_call = next(
        c
        for c in reversed(supabase.table.return_value.update.call_args_list)
        if "autopilot_status" in c.args[0]
    )
    assert last_state_call.args[0]["autopilot_status"] in ("paused_variant", "running")


@pytest.mark.asyncio
async def test_run_next_screen_generates_variants_and_pauses_at_variant():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"autopilot_events": []}
    )
    orch = _orch(supabase)
    build_plan = [
        {
            "phase": 1,
            "label": "Core",
            "screens": [{"name": "Home", "page": "home", "device": "DESKTOP"}],
            "dependencies": [],
        }
    ]

    async def fake_variants(*args, **kwargs):
        yield {"step": "variant_generated", "variant_id": "v1", "screen_id": "s1"}
        yield {"step": "variant_generated", "variant_id": "v2", "screen_id": "s1"}
        yield {"step": "variant_generated", "variant_id": "v3", "screen_id": "s1"}
        yield {"step": "ready", "variants": []}

    with patch(
        "app.services.app_builder_orchestrator.generate_screen_variants",
        side_effect=lambda *a, **kw: fake_variants(),
    ):
        await orch.run_next_screen(build_plan, completed_screen_ids=[])

    last_state_call = next(
        c
        for c in reversed(supabase.table.return_value.update.call_args_list)
        if "autopilot_status" in c.args[0]
    )
    assert last_state_call.args[0]["autopilot_status"] == "paused_variant"


@pytest.mark.asyncio
async def test_run_after_screen_approved_advances_to_next_screen_or_ship():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={
            "build_plan": [
                {
                    "phase": 1,
                    "label": "Core",
                    "screens": [
                        {"name": "Home", "page": "home", "device": "DESKTOP"},
                        {"name": "About", "page": "about", "device": "DESKTOP"},
                    ],
                    "dependencies": [],
                }
            ],
            "autopilot_events": [],
        }
    )
    orch = _orch(supabase)

    async def fake_variants(*a, **kw):
        yield {"step": "variant_generated", "variant_id": "v1", "screen_id": "s2"}
        yield {"step": "ready", "variants": []}

    with patch(
        "app.services.app_builder_orchestrator.generate_screen_variants",
        side_effect=lambda *a, **kw: fake_variants(),
    ):
        # Simulate "home" was just approved; should advance to "About"
        await orch.run_after_screen_approved(completed_screen_ids=["home"])

    appended = [
        c
        for c in supabase.table.return_value.update.call_args_list
        if "autopilot_events" in c.args[0]
    ]
    flat = [e for c in appended for e in c.args[0]["autopilot_events"]]
    assert any("About" in (e.get("message") or "") for e in flat)
