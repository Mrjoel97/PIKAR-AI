# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the inline ``approval`` widget envelope.

Verifies that ``request_human_approval`` returns a structured widget dict
(not a bare string) so the frontend ApprovalCard can render Approve/Reject
buttons inline in chat. The full agent-resume flow is ARTIFACT-04 and is
NOT exercised here.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


_TOOL_MODULE = "app.agents.tools.approval_tool"


def _mock_supabase_client() -> MagicMock:
    """Build a Supabase client whose .table().insert() chain returns truthy."""
    client = MagicMock()
    table = MagicMock()
    insert = MagicMock()
    table.insert.return_value = insert
    client.table.return_value = table
    return client


@pytest.mark.asyncio
async def test_request_human_approval_returns_widget_envelope():
    """Happy path: returns a dict with type='approval' and decision_endpoint."""
    from app.agents.tools.approval_tool import request_human_approval

    with (
        patch(
            f"{_TOOL_MODULE}.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            f"{_TOOL_MODULE}.execute_async",
            new=AsyncMock(return_value=MagicMock(data=[{"id": "row-1"}])),
        ),
        patch(
            f"{_TOOL_MODULE}.asyncio.create_task",
            lambda coro: (coro.close(), MagicMock())[1],
        ),
    ):
        result = await request_human_approval(
            action_type="POST_TWEET",
            action_description="Post launch tweet",
            payload={"requester_user_id": "user-1", "text": "hello"},
        )

    assert isinstance(result, dict)
    assert result["type"] == "approval"
    assert result["title"] == "Post launch tweet"
    assert result["dismissible"] is True
    assert "widget_id" in result and isinstance(result["widget_id"], str)

    data = result["data"]
    assert isinstance(data["token"], str) and len(data["token"]) > 16
    assert data["action_type"] == "POST_TWEET"
    assert data["decision_endpoint"].endswith(f"/approvals/{data['token']}/decision")
    assert "magic_link" in data
    assert "base_url" in data
    # Legacy back-compat: callers that still expect text get a non-empty message.
    assert isinstance(result["message"], str)
    assert data["token"] in result["message"]


@pytest.mark.asyncio
async def test_request_human_approval_uses_explicit_deadline():
    """If requires_response_by is supplied, it is preserved in data."""
    from app.agents.tools.approval_tool import request_human_approval

    deadline = "2030-01-01T00:00:00+00:00"
    with (
        patch(
            f"{_TOOL_MODULE}.get_service_client",
            return_value=_mock_supabase_client(),
        ),
        patch(
            f"{_TOOL_MODULE}.execute_async",
            new=AsyncMock(return_value=MagicMock(data=[{"id": "row-2"}])),
        ),
        patch(
            f"{_TOOL_MODULE}.asyncio.create_task",
            lambda coro: (coro.close(), MagicMock())[1],
        ),
    ):
        result = await request_human_approval(
            action_type="SEND_EMAIL",
            action_description="Send launch email",
            payload={"requester_user_id": "user-1"},
            requires_response_by=deadline,
        )

    assert result["data"]["requires_response_by"] == deadline


@pytest.mark.asyncio
async def test_request_human_approval_error_returns_text_envelope():
    """If supabase explodes, return type='text' with an error message
    rather than raising — keeps the widget contract tolerant.
    """
    from app.agents.tools.approval_tool import request_human_approval

    with patch(
        f"{_TOOL_MODULE}.get_service_client",
        side_effect=RuntimeError("supabase down"),
    ):
        result = await request_human_approval(
            action_type="POST_TWEET",
            action_description="Post launch tweet",
            payload={"requester_user_id": "user-1"},
        )

    assert isinstance(result, dict)
    assert result["type"] == "text"
    assert "Failed to generate approval link" in result["message"]
    assert "supabase down" in result["message"]


def test_approval_in_renderable_widget_types():
    """The 'approval' string must be in RENDERABLE_WIDGET_TYPES so SSE
    extracts it as a widget instead of dropping it as text.
    """
    from app.sse_utils import RENDERABLE_WIDGET_TYPES

    assert "approval" in RENDERABLE_WIDGET_TYPES
