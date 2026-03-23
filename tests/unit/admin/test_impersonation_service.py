"""Unit tests for impersonation_service and related integrations.

Tests cover:
- create_impersonation_session
- validate_impersonation_session (active, expired, inactive, not found)
- deactivate_impersonation_session
- is_impersonation_active
- validate_impersonation_path (allow-list)
- log_admin_action with impersonation_session_id (upgrade + backward compat)
- NotificationService.create_notification suppressed during impersonation
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SERVICE_CLIENT_PATCH = "app.services.impersonation_service.get_service_client"
_EXECUTE_ASYNC_PATCH = "app.services.impersonation_service.execute_async"

_AUDIT_CLIENT_PATCH = "app.services.admin_audit.get_service_client"
# execute_async is lazy-imported inside log_admin_action — patch at source module
_AUDIT_EXECUTE_PATCH = "app.services.supabase_async.execute_async"

_NOTIF_IMPERSONATION_PATCH = "app.notifications.notification_service.is_impersonation_active"


def _make_mock_response(data: dict | list | None = None, count: int = 0) -> MagicMock:
    """Return a MagicMock mimicking a Supabase APIResponse."""
    resp = MagicMock()
    resp.data = data
    resp.count = count
    return resp


# ---------------------------------------------------------------------------
# create_impersonation_session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_session() -> None:
    """create_impersonation_session inserts row and returns a dict with expected keys."""
    from app.services.impersonation_service import create_impersonation_session

    session_row = {
        "id": "sess-uuid",
        "admin_user_id": "admin-uuid",
        "target_user_id": "target-uuid",
        "is_active": True,
        "expires_at": "2026-03-23T19:05:26Z",
        "created_at": "2026-03-23T18:35:26Z",
        "ended_at": None,
    }
    mock_response = _make_mock_response(data=[session_row])

    with (
        patch(_SERVICE_CLIENT_PATCH) as mock_client,
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=mock_response)),
    ):
        # Wire the query builder chain
        mock_client.return_value.table.return_value.insert.return_value = MagicMock()

        result = await create_impersonation_session("admin-uuid", "target-uuid")

    assert result["id"] == "sess-uuid"
    assert result["admin_user_id"] == "admin-uuid"
    assert result["target_user_id"] == "target-uuid"
    assert result["is_active"] is True
    assert "expires_at" in result


# ---------------------------------------------------------------------------
# validate_impersonation_session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_session_active() -> None:
    """validate_impersonation_session returns row dict for active, non-expired session."""
    from app.services.impersonation_service import validate_impersonation_session

    session_row = {
        "id": "sess-uuid",
        "admin_user_id": "admin-uuid",
        "target_user_id": "target-uuid",
        "is_active": True,
        "expires_at": "2099-01-01T00:00:00Z",
    }
    mock_response = _make_mock_response(data=[session_row])

    with (
        patch(_SERVICE_CLIENT_PATCH) as mock_client,
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=mock_response)),
    ):
        mock_client.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value = MagicMock()

        result = await validate_impersonation_session("sess-uuid")

    assert result is not None
    assert result["id"] == "sess-uuid"
    assert result["is_active"] is True


@pytest.mark.asyncio
async def test_validate_session_expired() -> None:
    """validate_impersonation_session returns None when expires_at is in the past."""
    from app.services.impersonation_service import validate_impersonation_session

    # Empty data = no matching rows (query filters expires_at > now())
    mock_response = _make_mock_response(data=[])

    with (
        patch(_SERVICE_CLIENT_PATCH) as mock_client,
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=mock_response)),
    ):
        mock_client.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value = MagicMock()

        result = await validate_impersonation_session("expired-sess-uuid")

    assert result is None


@pytest.mark.asyncio
async def test_validate_session_inactive() -> None:
    """validate_impersonation_session returns None when is_active=False."""
    from app.services.impersonation_service import validate_impersonation_session

    # Query filters is_active=True, so inactive sessions return empty data
    mock_response = _make_mock_response(data=[])

    with (
        patch(_SERVICE_CLIENT_PATCH) as mock_client,
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=mock_response)),
    ):
        mock_client.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value = MagicMock()

        result = await validate_impersonation_session("inactive-sess-uuid")

    assert result is None


@pytest.mark.asyncio
async def test_validate_session_not_found() -> None:
    """validate_impersonation_session returns None for unknown session_id."""
    from app.services.impersonation_service import validate_impersonation_session

    mock_response = _make_mock_response(data=None)

    with (
        patch(_SERVICE_CLIENT_PATCH) as mock_client,
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=mock_response)),
    ):
        mock_client.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value = MagicMock()

        result = await validate_impersonation_session("nonexistent-sess-uuid")

    assert result is None


# ---------------------------------------------------------------------------
# deactivate_impersonation_session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deactivate_session() -> None:
    """deactivate_impersonation_session sets is_active=False and sets ended_at."""
    from app.services.impersonation_service import deactivate_impersonation_session

    mock_response = _make_mock_response(data=[{"id": "sess-uuid", "is_active": False}])

    with (
        patch(_SERVICE_CLIENT_PATCH) as mock_client,
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=mock_response)) as mock_exec,
    ):
        update_mock = MagicMock()
        mock_client.return_value.table.return_value.update.return_value.eq.return_value = update_mock

        await deactivate_impersonation_session("sess-uuid")

    # Verify execute_async was called (update happened)
    mock_exec.assert_called_once()
    # Verify the update payload included is_active=False
    update_call_args = mock_client.return_value.table.return_value.update.call_args
    update_payload = update_call_args[0][0]
    assert update_payload.get("is_active") is False
    assert "ended_at" in update_payload


# ---------------------------------------------------------------------------
# is_impersonation_active
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_is_impersonation_active_true() -> None:
    """is_impersonation_active returns True when an active non-expired session exists."""
    from app.services.impersonation_service import is_impersonation_active

    session_row = {"id": "sess-uuid", "is_active": True}
    mock_response = _make_mock_response(data=[session_row], count=1)

    with (
        patch(_SERVICE_CLIENT_PATCH) as mock_client,
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=mock_response)),
    ):
        mock_client.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value = MagicMock()

        result = await is_impersonation_active("target-uuid")

    assert result is True


@pytest.mark.asyncio
async def test_is_impersonation_active_false() -> None:
    """is_impersonation_active returns False when no active session exists."""
    from app.services.impersonation_service import is_impersonation_active

    mock_response = _make_mock_response(data=[], count=0)

    with (
        patch(_SERVICE_CLIENT_PATCH) as mock_client,
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=mock_response)),
    ):
        mock_client.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value = MagicMock()

        result = await is_impersonation_active("target-uuid")

    assert result is False


# ---------------------------------------------------------------------------
# validate_impersonation_path (allow-list)
# ---------------------------------------------------------------------------


def test_validate_allow_list_permitted() -> None:
    """validate_impersonation_path returns True for paths in IMPERSONATION_ALLOWED_PATHS."""
    from app.services.impersonation_service import (
        IMPERSONATION_ALLOWED_PATHS,
        validate_impersonation_path,
    )

    for allowed in IMPERSONATION_ALLOWED_PATHS:
        assert validate_impersonation_path(allowed) is True
        assert validate_impersonation_path(allowed + "/subpath") is True


def test_validate_allow_list_blocked() -> None:
    """validate_impersonation_path returns False for paths not in the allow-list."""
    from app.services.impersonation_service import validate_impersonation_path

    assert validate_impersonation_path("/admin/system/secret") is False
    assert validate_impersonation_path("/api/admin/super-secret") is False
    assert validate_impersonation_path("/billing/payments") is False
    assert validate_impersonation_path("") is False


# ---------------------------------------------------------------------------
# audit log — impersonation_session_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_impersonation_session_id() -> None:
    """log_admin_action with impersonation_session_id includes it in the inserted row."""
    from app.services.admin_audit import log_admin_action

    mock_response = _make_mock_response(data=[{"id": "audit-row-uuid"}])

    with (
        patch(_AUDIT_CLIENT_PATCH) as mock_client,
        patch(_AUDIT_EXECUTE_PATCH, new=AsyncMock(return_value=mock_response)),
    ):
        mock_client.return_value.table.return_value.insert.return_value = MagicMock()

        await log_admin_action(
            "admin-uuid",
            "start_impersonation",
            "user",
            "target-uuid",
            None,
            "impersonation",
            impersonation_session_id="sess-uuid",
        )

    # Verify the row passed to insert() contained the session id
    insert_call_args = mock_client.return_value.table.return_value.insert.call_args
    inserted_row = insert_call_args[0][0]
    assert inserted_row.get("impersonation_session_id") == "sess-uuid"


@pytest.mark.asyncio
async def test_audit_backward_compat() -> None:
    """log_admin_action without impersonation_session_id still works (defaults to None)."""
    from app.services.admin_audit import log_admin_action

    mock_response = _make_mock_response(data=[{"id": "audit-row-uuid"}])

    with (
        patch(_AUDIT_CLIENT_PATCH) as mock_client,
        patch(_AUDIT_EXECUTE_PATCH, new=AsyncMock(return_value=mock_response)),
    ):
        mock_client.return_value.table.return_value.insert.return_value = MagicMock()

        # Existing callers use 6 positional args — no impersonation_session_id
        await log_admin_action(
            "admin-uuid",
            "suspend_user",
            "user",
            "target-uuid",
            None,
            "manual",
        )

    insert_call_args = mock_client.return_value.table.return_value.insert.call_args
    inserted_row = insert_call_args[0][0]
    # impersonation_session_id should be None (present in row but null)
    assert "impersonation_session_id" in inserted_row
    assert inserted_row["impersonation_session_id"] is None


# ---------------------------------------------------------------------------
# NotificationService — suppression during impersonation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notification_suppressed_during_impersonation() -> None:
    """create_notification returns None without DB insert when impersonation is active."""
    from app.notifications.notification_service import NotificationService

    svc = NotificationService.__new__(NotificationService)
    # Set up client mock so the guard runs (client is truthy)
    svc.client = MagicMock()
    svc.table_name = "notifications"

    with patch(_NOTIF_IMPERSONATION_PATCH, new=AsyncMock(return_value=True)):
        result = await svc.create_notification(
            user_id="target-user",
            title="Hello",
            message="World",
        )

    assert result is None
    # The DB insert must NOT have been called
    svc.client.table.assert_not_called()
