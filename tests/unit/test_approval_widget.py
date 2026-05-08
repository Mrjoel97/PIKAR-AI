# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the `approval` widget envelope (ARTIFACT-03).

Covers:
- Test 1: `request_human_approval` returns a widget envelope dict with
  ``type == "approval"`` and a populated ``data.token``.
- Test 2: The envelope contains a ``data.decision_endpoint`` that points at
  ``/approvals/{token}/decision``.
- Test 3: On error path (Supabase blows up), it returns a back-compat
  ``{"type": "text", "message": ...}`` dict (no exception).
- Test 4: The ``"approval"`` widget type is in
  ``app.sse_utils.RENDERABLE_WIDGET_TYPES`` so the SSE pipeline lets it
  through to the frontend.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_request_human_approval_returns_approval_widget_envelope() -> None:
    """Happy path: returns dict with type=='approval' and data.token populated."""
    from app.agents.tools import approval_tool

    fake_supabase = MagicMock()
    fake_supabase.table.return_value.insert.return_value = MagicMock()

    with (
        patch.object(approval_tool, "get_service_client", return_value=fake_supabase),
        patch.object(
            approval_tool, "execute_async", new=AsyncMock(return_value=MagicMock())
        ),
    ):
        result = await approval_tool.request_human_approval(
            action_type="POST_TWEET",
            action_description="Post a tweet about the launch",
            payload={"requester_user_id": "user-123", "text": "Hello!"},
        )

    assert isinstance(result, dict)
    assert result["type"] == "approval"
    assert isinstance(result.get("data"), dict)
    assert isinstance(result["data"].get("token"), str)
    assert result["data"]["token"]  # non-empty
    assert result["data"]["action_type"] == "POST_TWEET"
    assert result["title"] == "Post a tweet about the launch"
    assert result.get("dismissible") is True
    assert "widget_id" in result
    # legacy `message` key for back-compat
    assert isinstance(result.get("message"), str)
    assert "Post a tweet about the launch" in result["message"]


@pytest.mark.asyncio
async def test_request_human_approval_envelope_decision_endpoint() -> None:
    """The widget envelope exposes /approvals/{token}/decision."""
    from app.agents.tools import approval_tool

    fake_supabase = MagicMock()
    fake_supabase.table.return_value.insert.return_value = MagicMock()

    with (
        patch.object(approval_tool, "get_service_client", return_value=fake_supabase),
        patch.object(
            approval_tool, "execute_async", new=AsyncMock(return_value=MagicMock())
        ),
    ):
        result = await approval_tool.request_human_approval(
            action_type="SEND_EMAIL",
            action_description="Send weekly digest",
            payload={"requester_user_id": "user-456"},
        )

    token = result["data"]["token"]
    endpoint = result["data"]["decision_endpoint"]
    assert endpoint == f"/approvals/{token}/decision"
    assert result["data"].get("magic_link", "").endswith(f"/approval/{token}")


@pytest.mark.asyncio
async def test_request_human_approval_error_path_returns_text_dict() -> None:
    """When the DB write fails, return a back-compat type='text' dict."""
    from app.agents.tools import approval_tool

    with patch.object(
        approval_tool,
        "get_service_client",
        side_effect=RuntimeError("supabase down"),
    ):
        result = await approval_tool.request_human_approval(
            action_type="POST_TWEET",
            action_description="Whatever",
            payload={},
        )

    assert isinstance(result, dict)
    assert result["type"] == "text"
    assert "Failed to generate approval link" in result["message"]
    assert result.get("success") is False


def test_approval_widget_type_in_renderable_allowlist() -> None:
    """The `approval` widget type must be in the SSE allowlist."""
    from app.sse_utils import RENDERABLE_WIDGET_TYPES

    assert "approval" in RENDERABLE_WIDGET_TYPES
