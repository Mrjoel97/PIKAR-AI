"""Verify StepExecutor calls OutcomeWriter and emits SSE events."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workflows.step_executor import StepExecutor


@pytest.mark.asyncio
async def test_completed_step_writes_outcome():
    fake_writer = AsyncMock()
    fake_publish = AsyncMock()
    with patch(
        "app.workflows.outcome_writer.OutcomeWriter",
        return_value=MagicMock(write_for_step=fake_writer),
    ), patch(
        "app.workflows.event_bus.publish_workflow_event",
        new=fake_publish,
    ):
        executor = StepExecutor(supabase_client=MagicMock())
        await executor._finalize_step(
            step={"id": "s1", "tool_name": "t", "workflow_execution_id": "exec-1"},
            status="completed",
            tool_output={"summary": "Done."},
            duration_ms=100,
            error_message=None,
        )
    fake_writer.assert_awaited_once()
    assert fake_writer.call_args.kwargs["step_id"] == "s1"
    assert fake_writer.call_args.kwargs["status"] == "completed"
    fake_publish.assert_awaited()
    event = fake_publish.call_args[0][1]
    assert event["type"] == "workflow.step.completed"
    assert event["step_id"] == "s1"


@pytest.mark.asyncio
async def test_paused_step_emits_sse_event():
    fake_publish = AsyncMock()
    with patch("app.workflows.event_bus.publish_workflow_event", new=fake_publish):
        executor = StepExecutor(supabase_client=MagicMock())
        await executor._on_step_paused_for_approval(
            execution_id="exec-1",
            step={"id": "s1", "name": "Send email"},
        )
    fake_publish.assert_awaited_once()
    event = fake_publish.call_args[0][1]
    assert event["type"] == "workflow.step.paused"
    assert event["step_id"] == "s1"
    assert event["step_name"] == "Send email"
