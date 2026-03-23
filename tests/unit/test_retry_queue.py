"""Unit tests for the failed operation retry queue."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.retry_queue import (
    DEFAULT_MAX_RETRIES,
    RETRY_BACKOFF_MULTIPLIER,
    RETRY_BASE_DELAY_SECONDS,
    enqueue_failed_operation,
    get_queue_stats,
    process_retry_queue,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_supabase_client():
    """Create a mock Supabase client with chained query builder."""
    client = MagicMock()

    def _make_chain(data=None):
        chain = MagicMock()
        chain.insert.return_value = chain
        chain.select.return_value = chain
        chain.update.return_value = chain
        chain.eq.return_value = chain
        chain.lte.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.single.return_value = chain
        result = MagicMock()
        result.data = data if data is not None else []
        chain.execute.return_value = result
        return chain

    client.table.return_value = _make_chain()
    return client


def _make_op(
    *,
    op_id="op-1",
    step_id="step-1",
    execution_id="exec-1",
    tool_name="send_email",
    attempt_count=0,
    max_retries=3,
    status="pending",
):
    return {
        "id": op_id,
        "step_id": step_id,
        "execution_id": execution_id,
        "tool_name": tool_name,
        "input_data": {"to": "test@example.com"},
        "step_definition": {"timeout_seconds": 30},
        "error_message": "Connection refused",
        "reason_code": "step_execution_failed",
        "attempt_count": attempt_count,
        "max_retries": max_retries,
        "status": status,
        "next_retry_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# enqueue_failed_operation
# ---------------------------------------------------------------------------


class TestEnqueueFailedOperation:
    """Tests for inserting failed ops into the retry queue."""

    @pytest.mark.asyncio
    async def test_enqueue_inserts_row(self):
        mock_client = _mock_supabase_client()
        inserted_row = _make_op()
        mock_client.table.return_value.execute.return_value.data = [inserted_row]

        with patch("app.services.retry_queue.get_service_client", return_value=mock_client):
            result = await enqueue_failed_operation(
                step_id="step-1",
                execution_id="exec-1",
                tool_name="send_email",
                input_data={"to": "test@example.com"},
                step_definition={"timeout_seconds": 30},
                error_message="Connection refused",
                reason_code="step_execution_failed",
            )

        assert result is not None
        assert result["step_id"] == "step-1"
        assert result["tool_name"] == "send_email"
        mock_client.table.assert_called_with("failed_operations")

    @pytest.mark.asyncio
    async def test_enqueue_uses_pending_status(self):
        mock_client = _mock_supabase_client()
        captured_payload = {}

        def capture_insert(payload):
            captured_payload.update(payload)
            chain = MagicMock()
            chain.execute.return_value = MagicMock(data=[{**payload, "id": "op-new"}])
            return chain

        mock_client.table.return_value.insert.side_effect = capture_insert

        with patch("app.services.retry_queue.get_service_client", return_value=mock_client):
            await enqueue_failed_operation(
                step_id="step-1",
                execution_id="exec-1",
                tool_name="send_email",
                input_data={},
                step_definition={},
                error_message="fail",
                reason_code="timeout",
            )

        assert captured_payload["status"] == "pending"

    @pytest.mark.asyncio
    async def test_enqueue_returns_none_on_exception(self):
        mock_client = MagicMock()
        mock_client.table.side_effect = Exception("DB down")

        with patch("app.services.retry_queue.get_service_client", return_value=mock_client):
            result = await enqueue_failed_operation(
                step_id="step-1",
                execution_id="exec-1",
                tool_name="send_email",
                input_data={},
                step_definition={},
                error_message="fail",
                reason_code="timeout",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_enqueue_respects_custom_max_retries(self):
        mock_client = _mock_supabase_client()
        captured = {}

        def capture_insert(payload):
            captured.update(payload)
            chain = MagicMock()
            chain.execute.return_value = MagicMock(data=[{**payload, "id": "op-x"}])
            return chain

        mock_client.table.return_value.insert.side_effect = capture_insert

        with patch("app.services.retry_queue.get_service_client", return_value=mock_client):
            await enqueue_failed_operation(
                step_id="s-1",
                execution_id="e-1",
                tool_name="t",
                input_data={},
                step_definition={},
                error_message="err",
                reason_code="rc",
                max_retries=5,
            )

        assert captured["max_retries"] == 5


# ---------------------------------------------------------------------------
# process_retry_queue
# ---------------------------------------------------------------------------


class TestProcessRetryQueue:
    """Tests for the background retry processor."""

    @pytest.mark.asyncio
    async def test_empty_queue_returns_zero_summary(self):
        mock_client = _mock_supabase_client()
        # No pending ops
        mock_client.table.return_value.execute.return_value.data = []

        with patch("app.services.retry_queue.get_service_client", return_value=mock_client):
            summary = await process_retry_queue()

        assert summary["processed"] == 0
        assert summary["succeeded"] == 0

    @pytest.mark.asyncio
    async def test_successful_retry_marks_completed(self):
        op = _make_op(attempt_count=0, max_retries=3)
        mock_client = _mock_supabase_client()

        # First call (select pending) returns the op
        select_result = MagicMock()
        select_result.data = [op]
        # Subsequent calls return empty
        empty_result = MagicMock()
        empty_result.data = []

        call_count = {"n": 0}
        original_table = mock_client.table

        def smart_table(name):
            chain = MagicMock()
            chain.select.return_value = chain
            chain.insert.return_value = chain
            chain.update.return_value = chain
            chain.eq.return_value = chain
            chain.lte.return_value = chain
            chain.order.return_value = chain
            chain.limit.return_value = chain
            chain.single.return_value = chain

            if name == "failed_operations" and call_count["n"] == 0:
                call_count["n"] += 1
                chain.execute.return_value = select_result
            else:
                chain.execute.return_value = empty_result
            return chain

        mock_client.table.side_effect = smart_table

        mock_executor = AsyncMock()
        mock_executor.execute_step.return_value = {
            "_execution_meta": {"verification_status": "passed"}
        }

        with (
            patch("app.services.retry_queue.get_service_client", return_value=mock_client),
            patch("app.workflows.step_executor.StepExecutor", return_value=mock_executor),
        ):
            summary = await process_retry_queue()

        assert summary["processed"] == 1
        assert summary["succeeded"] == 1
        mock_executor.execute_step.assert_called_once()

    @pytest.mark.asyncio
    async def test_exhausted_retries_moves_to_dead_letter(self):
        op = _make_op(attempt_count=2, max_retries=3)  # attempt 3 = last try
        mock_client = _mock_supabase_client()

        select_result = MagicMock()
        select_result.data = [op]
        empty_result = MagicMock()
        empty_result.data = []

        call_count = {"n": 0}

        def smart_table(name):
            chain = MagicMock()
            chain.select.return_value = chain
            chain.update.return_value = chain
            chain.eq.return_value = chain
            chain.lte.return_value = chain
            chain.order.return_value = chain
            chain.limit.return_value = chain
            chain.single.return_value = chain

            if name == "failed_operations" and call_count["n"] == 0:
                call_count["n"] += 1
                chain.execute.return_value = select_result
            else:
                chain.execute.return_value = empty_result
            return chain

        mock_client.table.side_effect = smart_table

        mock_executor = AsyncMock()
        mock_executor.execute_step.side_effect = Exception("Still failing")

        with (
            patch("app.services.retry_queue.get_service_client", return_value=mock_client),
            patch("app.workflows.step_executor.StepExecutor", return_value=mock_executor),
        ):
            summary = await process_retry_queue()

        assert summary["dead_letter"] == 1

    @pytest.mark.asyncio
    async def test_failed_retry_reschedules_with_backoff(self):
        op = _make_op(attempt_count=0, max_retries=3)
        mock_client = _mock_supabase_client()

        select_result = MagicMock()
        select_result.data = [op]
        empty_result = MagicMock()
        empty_result.data = []

        captured_updates = []
        call_count = {"n": 0}

        def smart_table(name):
            chain = MagicMock()
            chain.select.return_value = chain
            chain.update.return_value = chain
            chain.eq.return_value = chain
            chain.lte.return_value = chain
            chain.order.return_value = chain
            chain.limit.return_value = chain
            chain.single.return_value = chain

            def capture_update(payload):
                captured_updates.append(payload)
                inner = MagicMock()
                inner.eq.return_value = inner
                inner.execute.return_value = MagicMock(data=[])
                return inner

            chain.update.side_effect = capture_update

            if name == "failed_operations" and call_count["n"] == 0:
                call_count["n"] += 1
                chain.execute.return_value = select_result
            else:
                chain.execute.return_value = empty_result
            return chain

        mock_client.table.side_effect = smart_table

        mock_executor = AsyncMock()
        mock_executor.execute_step.side_effect = Exception("Transient error")

        with (
            patch("app.services.retry_queue.get_service_client", return_value=mock_client),
            patch("app.workflows.step_executor.StepExecutor", return_value=mock_executor),
        ):
            summary = await process_retry_queue()

        assert summary["failed"] == 1
        # Should have at least one update with status=pending (reschedule)
        reschedule_updates = [u for u in captured_updates if u.get("status") == "pending"]
        assert len(reschedule_updates) >= 1
        assert reschedule_updates[0]["attempt_count"] == 1


# ---------------------------------------------------------------------------
# get_queue_stats
# ---------------------------------------------------------------------------


class TestGetQueueStats:
    """Tests for queue monitoring stats."""

    @pytest.mark.asyncio
    async def test_empty_queue_stats(self):
        mock_client = _mock_supabase_client()
        mock_client.table.return_value.execute.return_value.data = []

        with patch("app.services.retry_queue.get_service_client", return_value=mock_client):
            stats = await get_queue_stats()

        assert stats["total"] == 0
        assert stats["pending"] == 0

    @pytest.mark.asyncio
    async def test_stats_counts_by_status(self):
        mock_client = _mock_supabase_client()
        mock_client.table.return_value.execute.return_value.data = [
            {"status": "pending"},
            {"status": "pending"},
            {"status": "completed"},
            {"status": "dead_letter"},
        ]

        with patch("app.services.retry_queue.get_service_client", return_value=mock_client):
            stats = await get_queue_stats()

        assert stats["total"] == 4
        assert stats["pending"] == 2
        assert stats["completed"] == 1
        assert stats["dead_letter"] == 1


# ---------------------------------------------------------------------------
# StepExecutor integration — _enqueue_for_retry
# ---------------------------------------------------------------------------


class TestStepExecutorEnqueueIntegration:
    """Verify StepExecutor calls retry queue on retryable failures."""

    @pytest.mark.asyncio
    async def test_handle_failure_enqueues_retryable_error(self):
        mock_client = _mock_supabase_client()
        # Mock the step row lookup for input_data
        step_result = MagicMock()
        step_result.data = {"input_data": {"key": "value"}}

        call_count = {"n": 0}

        def smart_table(name):
            chain = MagicMock()
            chain.select.return_value = chain
            chain.update.return_value = chain
            chain.eq.return_value = chain
            chain.single.return_value = chain
            chain.execute.return_value = MagicMock(data=[])

            if name == "workflow_steps" and call_count["n"] < 2:
                call_count["n"] += 1
                if call_count["n"] == 2:
                    chain.execute.return_value = step_result
            return chain

        mock_client.table.side_effect = smart_table

        from app.workflows.step_executor import StepExecutor

        executor = StepExecutor(supabase_client=mock_client)

        with patch("app.services.retry_queue.enqueue_failed_operation", new_callable=AsyncMock) as mock_enqueue:
            mock_enqueue.return_value = {"id": "op-1"}

            with pytest.raises(Exception):
                await executor._handle_failure(
                    step_id="step-1",
                    tool_name="send_email",
                    step_definition={"timeout_seconds": 30},
                    exc=Exception("timeout"),
                    reason_code="step_timeout",
                    duration_ms=1000,
                    attempt=3,
                    execution_id="exec-1",
                    on_failure="fail",
                )

            mock_enqueue.assert_called_once()
            call_kwargs = mock_enqueue.call_args[1]
            assert call_kwargs["step_id"] == "step-1"
            assert call_kwargs["tool_name"] == "send_email"

    @pytest.mark.asyncio
    async def test_handle_failure_skips_enqueue_for_non_retryable(self):
        mock_client = _mock_supabase_client()
        from app.workflows.execution_contracts import WorkflowContractError
        from app.workflows.step_executor import StepExecutor

        executor = StepExecutor(supabase_client=mock_client)

        with patch("app.services.retry_queue.enqueue_failed_operation", new_callable=AsyncMock) as mock_enqueue:
            with pytest.raises(WorkflowContractError):
                await executor._handle_failure(
                    step_id="step-1",
                    tool_name="bad_tool",
                    step_definition={},
                    exc=WorkflowContractError("bad schema", reason_code="schema_mismatch"),
                    reason_code="schema_mismatch",
                    duration_ms=0,
                    attempt=1,
                    execution_id="exec-1",
                    on_failure="fail",
                )

            mock_enqueue.assert_not_called()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Verify retry queue constants have sensible values."""

    def test_default_max_retries_is_positive(self):
        assert DEFAULT_MAX_RETRIES > 0

    def test_base_delay_is_positive(self):
        assert RETRY_BASE_DELAY_SECONDS > 0

    def test_backoff_multiplier_greater_than_one(self):
        assert RETRY_BACKOFF_MULTIPLIER > 1.0

    def test_exponential_backoff_schedule(self):
        """Verify the backoff produces increasing delays."""
        delays = [
            RETRY_BASE_DELAY_SECONDS * (RETRY_BACKOFF_MULTIPLIER ** i)
            for i in range(DEFAULT_MAX_RETRIES)
        ]
        assert delays == sorted(delays)
        assert delays[-1] > delays[0]
