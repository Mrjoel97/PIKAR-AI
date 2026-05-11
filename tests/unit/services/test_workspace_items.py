"""Unit tests for WorkspaceItemEmitter."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.workspace_items import WorkspaceItemEmitter


@pytest.fixture
def mock_client():
    """Mock Supabase client — execute_async is patched separately."""
    client = MagicMock()
    # .upsert() returns a query builder; execute_async will receive that builder.
    # No need to make .execute() awaitable since execute_async is patched out.
    client.table.return_value.upsert.return_value = MagicMock()
    return client


@pytest.mark.asyncio
async def test_emits_focus_for_user_ui_run_source(mock_client):
    with patch(
        "app.services.workspace_items.execute_async",
        new=AsyncMock(return_value=MagicMock(data=[{"id": "ws-1"}])),
    ):
        emitter = WorkspaceItemEmitter(client=mock_client)
        await emitter.emit_for_execution(
            execution={"id": "exec-1", "user_id": "u-1", "name": "Marketing Plan"},
            run_source="user_ui",
        )
    payload = mock_client.table.return_value.upsert.call_args[0][0]
    assert payload["widget_type"] == "workflow_timeline"
    assert payload["workflow_execution_id"] == "exec-1"
    assert payload["layout_mode"] == "focus"
    assert payload["widget_payload"]["interactive"] is True


@pytest.mark.asyncio
async def test_emits_embedded_for_scheduler_run_source(mock_client):
    with patch(
        "app.services.workspace_items.execute_async",
        new=AsyncMock(return_value=MagicMock(data=[{"id": "ws-2"}])),
    ):
        emitter = WorkspaceItemEmitter(client=mock_client)
        await emitter.emit_for_execution(
            execution={"id": "exec-2", "user_id": "u-1", "name": "Cron Job"},
            run_source="scheduler",
        )
    payload = mock_client.table.return_value.upsert.call_args[0][0]
    assert payload["layout_mode"] == "embedded"
    assert payload["widget_payload"]["interactive"] is False


@pytest.mark.asyncio
async def test_swallows_upsert_failure(mock_client, caplog):
    with patch(
        "app.services.workspace_items.execute_async",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        emitter = WorkspaceItemEmitter(client=mock_client)
        # Should not raise — graceful degradation per spec.
        await emitter.emit_for_execution(
            execution={"id": "exec-3", "user_id": "u-1", "name": "X"},
            run_source="user_ui",
        )
    assert "workspace_items emit failed" in caplog.text
