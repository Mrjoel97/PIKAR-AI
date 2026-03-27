"""Unit tests for AdminAgent user management tools.

Tests verify:
- list_users returns user list at auto tier (no confirmation)
- get_user_detail returns user profile at auto tier (no confirmation)
- suspend_user returns requires_confirmation at confirm tier
- unsuspend_user returns requires_confirmation at confirm tier
- change_user_persona returns requires_confirmation at confirm tier
- impersonate_user returns requires_confirmation dict with impersonation URL
- Any tool returns error dict when autonomy level is "blocked"
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Patch targets at the users module level
_SERVICE_CLIENT_PATCH = "app.agents.admin.tools.users.get_service_client"
_EXECUTE_ASYNC_PATCH = "app.agents.admin.tools.users.execute_async"
_LOG_AUDIT_PATCH = "app.agents.admin.tools.users.log_admin_action"
# The autonomy check imports get_service_client in its own module — must patch there too
_AUTONOMY_CLIENT_PATCH = "app.agents.admin.tools._autonomy.get_service_client"

_TEST_USER_ID = "user-00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Fixtures — autonomy mocks
# ---------------------------------------------------------------------------


def _build_autonomy_client(level: str) -> MagicMock:
    """Build a mock Supabase client that returns the given autonomy level."""
    client = MagicMock()
    table_mock = MagicMock()
    client.table.return_value = table_mock
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=[{"autonomy_level": level}])
    return client


@pytest.fixture
def client_auto():
    """Supabase mock returning autonomy_level='auto'."""
    return _build_autonomy_client("auto")


@pytest.fixture
def client_confirm():
    """Supabase mock returning autonomy_level='confirm'."""
    return _build_autonomy_client("confirm")


@pytest.fixture
def client_blocked():
    """Supabase mock returning autonomy_level='blocked'."""
    return _build_autonomy_client("blocked")


# ---------------------------------------------------------------------------
# execute_async mock that returns an empty user list by default
# ---------------------------------------------------------------------------


def _make_execute_async_empty() -> AsyncMock:
    """AsyncMock for execute_async that returns empty data."""
    mock = AsyncMock(return_value=MagicMock(data=[]))
    return mock


def _make_execute_async_with_user() -> AsyncMock:
    """AsyncMock for execute_async that returns one user row."""
    user_row = {
        "user_id": _TEST_USER_ID,
        "persona": "startup",
        "created_at": "2026-01-01T00:00:00Z",
    }
    mock = AsyncMock(return_value=MagicMock(data=[user_row]))
    return mock


# ---------------------------------------------------------------------------
# Task 1.1: list_users — auto tier (no confirmation)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_users_tool_auto_tier(client_auto):
    """Auto tier: list_users() returns user list dict without confirmation."""
    execute_async_mock = _make_execute_async_empty()

    # auth.admin.list_users is synchronous — wrap in to_thread mock
    auth_user = MagicMock()
    auth_user.id = _TEST_USER_ID
    auth_user.email = "test@example.com"
    auth_user.created_at = "2026-01-01T00:00:00Z"
    auth_user.last_sign_in_at = None

    # asyncio.to_thread is used for sync auth.admin calls
    with patch(_SERVICE_CLIENT_PATCH, return_value=client_auto):
        with patch(_EXECUTE_ASYNC_PATCH, new=execute_async_mock):
            with patch("asyncio.to_thread", new=AsyncMock(return_value=[auth_user])):
                from app.agents.admin.tools.users import list_users

                result = await list_users()

    assert "requires_confirmation" not in result
    assert "error" not in result
    assert "users" in result
    assert "page" in result
    assert isinstance(result["users"], list)


# ---------------------------------------------------------------------------
# Task 1.2: get_user_detail — auto tier (no confirmation)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_user_detail_tool_auto_tier(client_auto):
    """Auto tier: get_user_detail(user_id) returns user profile without confirmation."""
    execute_async_mock = _make_execute_async_with_user()

    auth_user = MagicMock()
    auth_user.id = _TEST_USER_ID
    auth_user.email = "test@example.com"
    auth_user.created_at = "2026-01-01T00:00:00Z"
    auth_user.last_sign_in_at = None
    auth_user.ban_duration = None

    with patch(_SERVICE_CLIENT_PATCH, return_value=client_auto):
        with patch(_EXECUTE_ASYNC_PATCH, new=execute_async_mock):
            with patch("asyncio.to_thread", new=AsyncMock(return_value=MagicMock(user=auth_user))):
                from app.agents.admin.tools.users import get_user_detail

                result = await get_user_detail(_TEST_USER_ID)

    assert "requires_confirmation" not in result
    assert "error" not in result
    assert "user_id" in result or "user" in result


# ---------------------------------------------------------------------------
# Task 1.3: suspend_user — confirm tier returns confirmation dict
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_suspend_user_confirm_tier(client_confirm):
    """Confirm tier: suspend_user() returns requires_confirmation dict."""
    with patch(_SERVICE_CLIENT_PATCH, return_value=client_confirm), patch(
        _AUTONOMY_CLIENT_PATCH, return_value=client_confirm
    ):
        from app.agents.admin.tools.users import suspend_user

        result = await suspend_user(_TEST_USER_ID)

    assert result.get("requires_confirmation") is True
    assert "confirmation_token" in result
    assert "action_details" in result
    # Validate token is a UUID
    uuid.UUID(result["confirmation_token"])
    assert result["action_details"]["action"] == "suspend_user"


# ---------------------------------------------------------------------------
# Task 1.4: unsuspend_user — confirm tier returns confirmation dict
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unsuspend_user_confirm_tier(client_confirm):
    """Confirm tier: unsuspend_user() returns requires_confirmation dict."""
    with patch(_SERVICE_CLIENT_PATCH, return_value=client_confirm), patch(
        _AUTONOMY_CLIENT_PATCH, return_value=client_confirm
    ):
        from app.agents.admin.tools.users import unsuspend_user

        result = await unsuspend_user(_TEST_USER_ID)

    assert result.get("requires_confirmation") is True
    assert "confirmation_token" in result
    assert "action_details" in result
    uuid.UUID(result["confirmation_token"])
    assert result["action_details"]["action"] == "unsuspend_user"


# ---------------------------------------------------------------------------
# Task 1.5: change_user_persona — confirm tier returns confirmation dict
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_change_persona_confirm_tier(client_confirm):
    """Confirm tier: change_user_persona() returns requires_confirmation dict."""
    with patch(_SERVICE_CLIENT_PATCH, return_value=client_confirm), patch(
        _AUTONOMY_CLIENT_PATCH, return_value=client_confirm
    ):
        from app.agents.admin.tools.users import change_user_persona

        result = await change_user_persona(_TEST_USER_ID, "startup")

    assert result.get("requires_confirmation") is True
    assert "confirmation_token" in result
    assert "action_details" in result
    uuid.UUID(result["confirmation_token"])
    assert result["action_details"]["action"] == "change_user_persona"


# ---------------------------------------------------------------------------
# Task 1.6: impersonate_user — confirm tier returns confirmation dict with URL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_impersonate_user_confirm_tier(client_confirm):
    """Confirm tier: impersonate_user() returns requires_confirmation dict with impersonation URL."""
    # Phase 13 upgrade: action name changed to 'activate_impersonation'; patch _autonomy directly
    # so the confirm-tier response is controlled regardless of Supabase env vars.
    import uuid as _uuid

    gate = {
        "requires_confirmation": True,
        "confirmation_token": str(_uuid.uuid4()),
        "action_details": {
            "action": "activate_impersonation",
            "risk_level": "low",
            "description": "Admin operation: activate_impersonation",
        },
    }
    with patch("app.agents.admin.tools.users._check_autonomy", new=AsyncMock(return_value=gate)):
        from app.agents.admin.tools.users import impersonate_user

        result = await impersonate_user(_TEST_USER_ID)

    assert result.get("requires_confirmation") is True
    assert "confirmation_token" in result
    assert "action_details" in result
    uuid.UUID(result["confirmation_token"])
    assert result["action_details"]["action"] == "activate_impersonation"
    assert "interactive" in result["action_details"]["description"].lower()


# ---------------------------------------------------------------------------
# Task 1.7: blocked tier — any tool returns error dict
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blocked_tool_returns_error_suspend(client_blocked):
    """Blocked tier: suspend_user returns error dict without executing."""
    with patch(_SERVICE_CLIENT_PATCH, return_value=client_blocked), patch(
        _AUTONOMY_CLIENT_PATCH, return_value=client_blocked
    ):
        from app.agents.admin.tools.users import suspend_user

        result = await suspend_user(_TEST_USER_ID)

    assert "error" in result
    assert "block" in result["error"].lower()
    assert "requires_confirmation" not in result


@pytest.mark.asyncio
async def test_blocked_tool_returns_error_list_users(client_blocked):
    """Blocked tier: list_users returns error dict without executing."""
    execute_async_mock = _make_execute_async_empty()
    with patch(_SERVICE_CLIENT_PATCH, return_value=client_blocked), patch(
        _AUTONOMY_CLIENT_PATCH, return_value=client_blocked
    ):
        with patch(_EXECUTE_ASYNC_PATCH, new=execute_async_mock):
            from app.agents.admin.tools.users import list_users

            result = await list_users()

    assert "error" in result
    assert "block" in result["error"].lower()
    assert "users" not in result


# ---------------------------------------------------------------------------
# Task 1.8: auto tier for suspend_user (when permissions table is set to auto)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_suspend_user_auto_tier_executes(client_auto):
    """Auto tier: suspend_user() calls auth.admin.update_user_by_id and logs audit."""
    with patch(_SERVICE_CLIENT_PATCH, return_value=client_auto):
        with patch("asyncio.to_thread", new=AsyncMock(return_value=MagicMock())):
            with patch(_LOG_AUDIT_PATCH, new=AsyncMock()) as mock_audit:
                from app.agents.admin.tools.users import suspend_user

                result = await suspend_user(_TEST_USER_ID)

    assert "error" not in result
    assert "requires_confirmation" not in result
    assert result.get("status") == "suspended"
    mock_audit.assert_called_once()


# ---------------------------------------------------------------------------
# Task 1.9: impersonate_user — auto tier creates interactive session (Phase 13)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_impersonate_user_auto_tier_interactive_session():
    """Auto tier: impersonate_user() creates an interactive session and returns session_id."""
    _IMPERSONATE_SESSION_PATCH = "app.agents.admin.tools.users.create_impersonation_session"
    _CHECK_AUTONOMY_PATCH_USERS = "app.agents.admin.tools.users._check_autonomy"

    fake_session = {
        "id": "sess-aaaaaaaa-0000-0000-0000-000000000001",
        "admin_user_id": None,
        "target_user_id": _TEST_USER_ID,
        "is_active": True,
        "expires_at": "2026-03-23T20:00:00Z",
    }

    with patch(_CHECK_AUTONOMY_PATCH_USERS, new=AsyncMock(return_value=None)):
        with patch(_IMPERSONATE_SESSION_PATCH, new=AsyncMock(return_value=fake_session)):
            with patch(_LOG_AUDIT_PATCH, new=AsyncMock()) as mock_audit:
                from app.agents.admin.tools.users import impersonate_user

                result = await impersonate_user(_TEST_USER_ID)

    assert "error" not in result
    assert "requires_confirmation" not in result
    assert result.get("mode") == "interactive"
    assert result.get("session_id") == fake_session["id"]
    assert "expires_at" in result
    assert f"/admin/impersonate/{_TEST_USER_ID}" in result.get("impersonation_url", "")
    mock_audit.assert_called_once()
