"""Unit tests for AppBuilderOrchestrator state machine helpers."""
from unittest.mock import MagicMock

import pytest

from app.services.app_builder_orchestrator import (
    AUTOPILOT_STATES,
    AppBuilderOrchestrator,
    AutopilotState,
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
