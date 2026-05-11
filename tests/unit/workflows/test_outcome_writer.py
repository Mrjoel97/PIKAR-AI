"""Unit tests for OutcomeWriter precedence rules."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workflows.outcome_writer import OutcomeWriter


@pytest.fixture
def mock_client():
    """Plain MagicMock; execute_async is patched per-test."""
    return MagicMock()


@pytest.mark.asyncio
async def test_tool_summary_short_used_verbatim(mock_client):
    with patch("app.workflows.outcome_writer.execute_async", new=AsyncMock()) as ea:
        writer = OutcomeWriter(client=mock_client)
        await writer.write_for_step(
            step_id="s1",
            tool_output={"summary": "Generated draft for Q3 marketing plan."},
            status="completed",
            tool_name="generate_doc",
            duration_ms=820,
        )
    update_payload = mock_client.table.return_value.update.call_args[0][0]
    assert update_payload["outcome_text"] == "Generated draft for Q3 marketing plan."
    assert update_payload["outcome_source"] == "tool"


@pytest.mark.asyncio
async def test_tool_summary_long_truncated(mock_client):
    long_summary = "x" * 500
    with patch("app.workflows.outcome_writer.execute_async", new=AsyncMock()):
        writer = OutcomeWriter(client=mock_client)
        await writer.write_for_step(
            step_id="s2",
            tool_output={"summary": long_summary},
            status="completed",
            tool_name="t",
            duration_ms=10,
        )
    update_payload = mock_client.table.return_value.update.call_args[0][0]
    assert len(update_payload["outcome_text"]) == 280
    assert update_payload["outcome_text"].endswith("...")
    assert update_payload["outcome_source"] == "tool"


@pytest.mark.asyncio
async def test_no_tool_summary_writes_status_fallback(mock_client):
    with patch("app.workflows.outcome_writer.execute_async", new=AsyncMock()):
        writer = OutcomeWriter(client=mock_client)
        await writer.write_for_step(
            step_id="s3",
            tool_output={"data": [1, 2, 3]},  # no summary key
            status="completed",
            tool_name="fetch_rows",
            duration_ms=120,
        )
    update_payload = mock_client.table.return_value.update.call_args[0][0]
    assert update_payload["outcome_text"] == "Completed fetch_rows in 120ms."
    assert update_payload["outcome_source"] == "status"


@pytest.mark.asyncio
async def test_failed_step_writes_error_fallback(mock_client):
    with patch("app.workflows.outcome_writer.execute_async", new=AsyncMock()):
        writer = OutcomeWriter(client=mock_client)
        await writer.write_for_step(
            step_id="s4",
            tool_output=None,
            status="failed",
            tool_name="bad_tool",
            duration_ms=50,
            error_message="boom",
        )
    update_payload = mock_client.table.return_value.update.call_args[0][0]
    assert "Failed" in update_payload["outcome_text"]
    assert "bad_tool" in update_payload["outcome_text"]
    assert update_payload["outcome_source"] == "status"
