"""Unit tests for admin chat session and token logic.

Covers:
- Session creation on missing session_id
- Session ownership rejection for wrong admin user
- Confirmation token consumption before streaming
- Double-use token error (expired / already consumed)
- User message persistence (role="user")
- Agent response persistence (role="agent")
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session_row(session_id: str, admin_user_id: str) -> dict:
    """Build a fake admin_chat_sessions row."""
    return {
        "id": session_id,
        "admin_user_id": admin_user_id,
        "title": "Test session",
    }


def _make_select_response(data: list) -> MagicMock:
    """Supabase-style select response."""
    resp = MagicMock()
    resp.data = data
    return resp


def _make_insert_response(session_id: str, admin_user_id: str) -> MagicMock:
    """Supabase-style insert response for admin_chat_sessions."""
    resp = MagicMock()
    resp.data = [_make_session_row(session_id, admin_user_id)]
    return resp


def _sse_lines(stream_text: str) -> list[str]:
    """Parse ``data: {...}`` lines from an SSE string into dicts."""
    results = []
    for line in stream_text.splitlines():
        if line.startswith("data: "):
            try:
                results.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return results


# ---------------------------------------------------------------------------
# Test: session creation when session_id is None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_session_on_missing_id():
    """When session_id is None, a new admin_chat_sessions row is created."""
    from app.routers.admin.chat import _get_or_create_session

    new_session_id = "new-session-uuid"
    admin_user_id = "admin-user-uuid"
    message = "Check system health please"

    # Mock supabase client
    client = MagicMock()
    insert_chain = MagicMock()
    insert_chain.execute.return_value = _make_insert_response(
        new_session_id, admin_user_id
    )
    client.table.return_value.insert.return_value = insert_chain

    with patch("app.routers.admin.chat.get_service_client", return_value=client):
        result = await _get_or_create_session(
            session_id=None,
            admin_user_id=admin_user_id,
            message=message,
        )

    assert result == new_session_id
    # Verify insert was called with admin_user_id and title (first 50 chars of message)
    call_args = client.table.return_value.insert.call_args[0][0]
    assert call_args["admin_user_id"] == admin_user_id
    assert call_args["title"] == message[:50]


# ---------------------------------------------------------------------------
# Test: session ownership rejected for wrong user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_ownership_rejected():
    """When session_id belongs to a different user, HTTPException 403 is raised."""
    from fastapi import HTTPException

    from app.routers.admin.chat import _get_or_create_session

    session_id = "existing-session-uuid"
    admin_user_id = "admin-user-uuid"

    # Mock: select returns empty (session not owned by this user)
    client = MagicMock()
    select_chain = MagicMock()
    select_chain.execute.return_value = _make_select_response([])
    client.table.return_value.select.return_value.eq.return_value.eq.return_value = (
        select_chain
    )

    with patch("app.routers.admin.chat.get_service_client", return_value=client):
        with pytest.raises(HTTPException) as exc_info:
            await _get_or_create_session(
                session_id=session_id,
                admin_user_id=admin_user_id,
                message="any message",
            )

    assert exc_info.value.status_code == 403
    assert "not found" in exc_info.value.detail.lower() or "not owned" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Test: confirmation token consumed before stream starts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_consumed_before_stream():
    """consume_confirmation_token is called with the provided token."""
    from app.routers.admin.chat import _consume_token_or_error

    token = "valid-token-uuid"
    payload = {
        "action_details": {"tool": "delete_user", "user_id": "u1"},
        "admin_user_id": "admin-uuid",
    }

    with patch(
        "app.routers.admin.chat.consume_confirmation_token",
        new_callable=AsyncMock,
        return_value=payload,
    ) as mock_consume:
        result = await _consume_token_or_error(token)

    mock_consume.assert_called_once_with(token)
    assert result == payload


# ---------------------------------------------------------------------------
# Test: double-use token returns None → SSE error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_double_use_token_error():
    """When consume_confirmation_token returns None, _consume_token_or_error returns None."""
    from app.routers.admin.chat import _consume_token_or_error

    token = "expired-token-uuid"

    with patch(
        "app.routers.admin.chat.consume_confirmation_token",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await _consume_token_or_error(token)

    assert result is None


# ---------------------------------------------------------------------------
# Test: user message persisted before streaming
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_message_persisted():
    """User message is saved to admin_chat_messages with role='user'."""
    from app.routers.admin.chat import _persist_message

    session_id = "session-uuid"
    message = "Hello admin agent"
    role = "user"

    client = MagicMock()
    insert_chain = MagicMock()
    insert_chain.execute.return_value = MagicMock(data=[{"id": "msg-uuid"}])
    client.table.return_value.insert.return_value = insert_chain

    with patch("app.routers.admin.chat.get_service_client", return_value=client):
        await _persist_message(
            session_id=session_id,
            role=role,
            content=message,
        )

    call_args = client.table.return_value.insert.call_args[0][0]
    assert call_args["session_id"] == session_id
    assert call_args["role"] == "user"
    assert call_args["content"] == message


# ---------------------------------------------------------------------------
# Test: agent response persisted with role="agent"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_response_persisted():
    """Agent response is saved to admin_chat_messages with role='agent'."""
    from app.routers.admin.chat import _persist_message

    session_id = "session-uuid"
    response_text = "System health is degraded: Redis is down."
    role = "agent"

    client = MagicMock()
    insert_chain = MagicMock()
    insert_chain.execute.return_value = MagicMock(data=[{"id": "msg-uuid"}])
    client.table.return_value.insert.return_value = insert_chain

    with patch("app.routers.admin.chat.get_service_client", return_value=client):
        await _persist_message(
            session_id=session_id,
            role=role,
            content=response_text,
        )

    call_args = client.table.return_value.insert.call_args[0][0]
    assert call_args["session_id"] == session_id
    assert call_args["role"] == "agent"
    assert call_args["content"] == response_text
