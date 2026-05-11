"""Verify cleanup invokes the archive RPC and returns the archived count."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.workspace_items_cleanup import archive_stale_workflow_items


@pytest.mark.asyncio
async def test_archive_returns_count_from_rpc():
    fake_client = MagicMock()
    rpc_chain = fake_client.rpc.return_value
    # The function returns a result with .data = [{"archived": 3}]

    with patch(
        "app.services.workspace_items_cleanup.execute_async",
        new=AsyncMock(return_value=MagicMock(data=[{"archived": 3}])),
    ):
        archived = await archive_stale_workflow_items(client=fake_client)

    assert archived == 3
    # RPC was called by name
    fake_client.rpc.assert_called_with("archive_stale_workflow_items")


@pytest.mark.asyncio
async def test_archive_returns_zero_on_empty_result():
    fake_client = MagicMock()
    with patch(
        "app.services.workspace_items_cleanup.execute_async",
        new=AsyncMock(return_value=MagicMock(data=[])),
    ):
        archived = await archive_stale_workflow_items(client=fake_client)
    assert archived == 0


@pytest.mark.asyncio
async def test_archive_swallows_rpc_failure():
    fake_client = MagicMock()
    with patch(
        "app.services.workspace_items_cleanup.execute_async",
        new=AsyncMock(side_effect=RuntimeError("connection refused")),
    ):
        # Should not raise; returns 0 to indicate nothing archived
        archived = await archive_stale_workflow_items(client=fake_client)
    assert archived == 0
