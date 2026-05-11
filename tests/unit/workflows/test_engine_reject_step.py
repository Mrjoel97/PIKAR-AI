"""Regression tests for reject_step SSE channel name and approve_step step_id forwarding."""

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workflows.engine import WorkflowEngine

EXECUTION_ID = "exec-abc-123"
STEP_ID = "step-xyz-456"
USER_ID = "user-111"

_FAKE_EXECUTION = {
    "id": EXECUTION_ID,
    "user_id": USER_ID,
    "status": "running",
    "template_id": "tmpl-1",
    "name": "Test Workflow",
}

_FAKE_STEP = {
    "id": STEP_ID,
    "execution_id": EXECUTION_ID,
    "status": "waiting_approval",
    "step_name": "Review Step",
    "phase_name": "Phase 1",
    "created_at": "2026-01-01T00:00:00",
}


def _make_client(step_data: list[dict]) -> MagicMock:
    """Build a minimal mock Supabase client for reject/approve tests."""
    client = MagicMock()

    # SELECT on workflow_steps — returns provided step data
    step_select_res = MagicMock()
    step_select_res.data = step_data

    step_chain = MagicMock()
    step_chain.select.return_value = step_chain
    step_chain.eq.return_value = step_chain
    step_chain.order.return_value = step_chain
    step_chain.limit.return_value = step_chain
    step_chain.execute = AsyncMock(return_value=step_select_res)

    # UPDATE on workflow_steps
    step_update_chain = MagicMock()
    step_update_chain.update.return_value = step_update_chain
    step_update_chain.eq.return_value = step_update_chain
    step_update_chain.execute = AsyncMock(return_value=MagicMock(data=[]))

    # UPDATE on workflow_executions
    exec_update_chain = MagicMock()
    exec_update_chain.update.return_value = exec_update_chain
    exec_update_chain.eq.return_value = exec_update_chain
    exec_update_chain.execute = AsyncMock(return_value=MagicMock(data=[]))

    # audit table INSERT
    audit_chain = MagicMock()
    audit_chain.insert.return_value = audit_chain
    audit_chain.execute = AsyncMock(return_value=MagicMock(data=[]))

    def _table_router(name: str):
        if name == "workflow_steps":
            # Distinguish select vs update by call order is tricky with a single
            # chain mock, so return separate chains based on which method is called
            # first.  We do this by returning a dispatcher mock.
            dispatcher = MagicMock()
            dispatcher.select.return_value = step_chain
            dispatcher.update.return_value = step_update_chain
            return dispatcher
        if name == "workflow_executions":
            return exec_update_chain
        if name == "workflow_execution_audit":
            return audit_chain
        return MagicMock()

    client.table.side_effect = _table_router
    return client


@pytest.fixture()
def engine():
    """Return a WorkflowEngine with a mocked sync client."""
    eng = WorkflowEngine.__new__(WorkflowEngine)
    eng._client = None  # will be set per test
    eng._async_client = None
    return eng


@pytest.mark.asyncio
async def test_reject_step_publishes_to_canonical_sse_channel():
    """reject_step must publish to workflow.execution.<id>, not workflow:<id>."""
    eng = WorkflowEngine.__new__(WorkflowEngine)

    status_result = {
        "execution": _FAKE_EXECUTION,
        "history": [],
        "current_phase_index": 0,
        "current_step_index": 0,
    }

    captured_channels: list[str] = []

    async def fake_publish(channel: str, event: dict) -> None:  # noqa: ARG001
        captured_channels.append(channel)

    client = _make_client([_FAKE_STEP])

    with (
        patch.object(
            WorkflowEngine,
            "get_execution_status",
            new=AsyncMock(return_value=status_result),
        ),
        patch.object(
            WorkflowEngine,
            "_get_client",
            new=AsyncMock(return_value=client),
        ),
        patch(
            "app.workflows.engine.publish_workflow_event",
            side_effect=fake_publish,
        ),
        patch.object(
            WorkflowEngine,
            "_audit_execution_action",
            new=AsyncMock(return_value=None),
        ),
    ):
        result = await WorkflowEngine.reject_step(
            eng,
            execution_id=EXECUTION_ID,
            step_id=STEP_ID,
            user_id=USER_ID,
        )

    assert result.get("status") == "rejected", f"Unexpected result: {result}"
    assert len(captured_channels) == 1, "Expected exactly one publish call"
    published_channel = captured_channels[0]

    # Must match the canonical pattern used by SSE subscribers
    assert re.match(
        r"^workflow\.execution\.", published_channel
    ), (
        f"SSE channel '{published_channel}' does not match canonical "
        f"'workflow.execution.<id>' pattern — live view would never receive the event"
    )
    assert published_channel == f"workflow.execution.{EXECUTION_ID}", (
        f"Channel '{published_channel}' does not contain the correct execution ID"
    )


@pytest.mark.asyncio
async def test_reject_step_writes_error_message_to_execution_row():
    """reject_step must write error_message to workflow_executions on rejection."""
    eng = WorkflowEngine.__new__(WorkflowEngine)

    status_result = {
        "execution": _FAKE_EXECUTION,
        "history": [],
        "current_phase_index": 0,
        "current_step_index": 0,
    }

    client = _make_client([_FAKE_STEP])

    # Capture what was passed to the executions update
    execution_updates: list[dict] = []
    original_side_effect = client.table.side_effect

    def _capturing_table(name: str):
        tbl = original_side_effect(name)
        if name == "workflow_executions":
            original_update = tbl.update

            def capturing_update(payload: dict):
                execution_updates.append(payload)
                return original_update(payload)

            tbl.update = capturing_update
        return tbl

    client.table.side_effect = _capturing_table

    with (
        patch.object(
            WorkflowEngine,
            "get_execution_status",
            new=AsyncMock(return_value=status_result),
        ),
        patch.object(
            WorkflowEngine,
            "_get_client",
            new=AsyncMock(return_value=client),
        ),
        patch("app.workflows.engine.publish_workflow_event", new=AsyncMock()),
        patch.object(
            WorkflowEngine,
            "_audit_execution_action",
            new=AsyncMock(return_value=None),
        ),
    ):
        await WorkflowEngine.reject_step(
            eng,
            execution_id=EXECUTION_ID,
            step_id=STEP_ID,
            user_id=USER_ID,
        )

    assert execution_updates, "No update was called on workflow_executions"
    update_payload = execution_updates[0]
    assert "error_message" in update_payload, (
        "error_message was not written to workflow_executions row on rejection"
    )
    assert update_payload["error_message"] == "Rejected by user"


@pytest.mark.asyncio
async def test_approve_step_uses_step_id_filter_when_provided():
    """approve_step must filter by step_id when one is supplied."""
    eng = WorkflowEngine.__new__(WorkflowEngine)

    status_result = {
        "execution": _FAKE_EXECUTION,
        "history": [],
        "current_phase_index": 0,
        "current_step_index": 0,
    }

    # Capture which eq() calls are made on the steps query chain
    eq_calls: list[tuple] = []

    step_select_res = MagicMock()
    step_select_res.data = [_FAKE_STEP]

    step_chain = MagicMock()

    def _eq(col: str, val: str):
        eq_calls.append((col, val))
        return step_chain

    step_chain.select.return_value = step_chain
    step_chain.eq.side_effect = _eq
    step_chain.order.return_value = step_chain
    step_chain.limit.return_value = step_chain
    step_chain.execute = AsyncMock(return_value=step_select_res)

    step_update_chain = MagicMock()
    step_update_chain.update.return_value = step_update_chain
    step_update_chain.eq.return_value = step_update_chain
    step_update_chain.execute = AsyncMock(return_value=MagicMock(data=[]))

    client = MagicMock()

    def _table_router(name: str):
        if name == "workflow_steps":
            dispatcher = MagicMock()
            dispatcher.select.return_value = step_chain
            dispatcher.update.return_value = step_update_chain
            return dispatcher
        return MagicMock()

    client.table.side_effect = _table_router

    with (
        patch.object(
            WorkflowEngine,
            "get_execution_status",
            new=AsyncMock(return_value=status_result),
        ),
        patch.object(
            WorkflowEngine,
            "_get_client",
            new=AsyncMock(return_value=client),
        ),
        patch("app.workflows.engine.edge_function_client") as mock_ef,
        patch.object(
            WorkflowEngine,
            "_audit_execution_action",
            new=AsyncMock(return_value=None),
        ),
    ):
        mock_ef.execute_workflow = AsyncMock(return_value={"status": "ok"})
        result = await WorkflowEngine.approve_step(
            eng,
            execution_id=EXECUTION_ID,
            step_message="Approved",
            user_id=USER_ID,
            step_id=STEP_ID,
        )

    assert result.get("status") == "approved", f"Unexpected result: {result}"
    # The step_id filter must appear in eq() calls on the steps query
    assert ("id", STEP_ID) in eq_calls, (
        f"step_id was not forwarded to the DB filter. eq() calls: {eq_calls}"
    )
