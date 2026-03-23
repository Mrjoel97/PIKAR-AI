"""Unit tests for impersonation API endpoints on the admin users router.

Tests cover:
- POST /admin/impersonate/{userId}/start (super-admin gate, audit log)
- DELETE /admin/impersonate/sessions/{sessionId} (deactivate, 404 on missing)
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.admin_auth import require_admin
from app.routers.admin import users as users_module
from app.routers.admin.users import router


# ---------------------------------------------------------------------------
# App fixture — override require_admin so no JWT needed
# ---------------------------------------------------------------------------

ADMIN_ID = "user-admin-uuid"
ADMIN_EMAIL = "admin@test.com"

_ADMIN_DICT = {
    "id": ADMIN_ID,
    "email": ADMIN_EMAIL,
    "role": "authenticated",
    "metadata": {},
    "admin_source": "env_allowlist",
}

_SUPER_ADMIN_EMAIL = "superadmin@test.com"
_SUPER_ADMIN_DICT = {
    "id": "super-admin-uuid",
    "email": _SUPER_ADMIN_EMAIL,
    "role": "authenticated",
    "metadata": {},
    "admin_source": "env_allowlist",
}


def _make_app(admin_dict: dict) -> FastAPI:
    """Create a test FastAPI app with require_admin overridden."""
    app = FastAPI()
    app.include_router(router, prefix="/admin")
    app.dependency_overrides[require_admin] = lambda: admin_dict
    return app


# Patch targets
_CREATE_SESSION_PATCH = "app.routers.admin.users.create_impersonation_session"
_DEACTIVATE_SESSION_PATCH = "app.routers.admin.users.deactivate_impersonation_session"
_VALIDATE_SESSION_PATCH = "app.routers.admin.users.validate_impersonation_session"
_LOG_ACTION_PATCH = "app.routers.admin.users.log_admin_action"
_EXECUTE_ASYNC_PATCH = "app.routers.admin.users.execute_async"


# ---------------------------------------------------------------------------
# Helper: a mock session row returned by create_impersonation_session
# ---------------------------------------------------------------------------

def _mock_session(session_id: str = "sess-uuid") -> dict:
    return {
        "id": session_id,
        "admin_user_id": ADMIN_ID,
        "target_user_id": "target-user-uuid",
        "is_active": True,
        "expires_at": "2099-01-01T00:00:00Z",
        "created_at": "2026-03-23T18:35:26Z",
        "ended_at": None,
    }


# ---------------------------------------------------------------------------
# POST /admin/impersonate/{userId}/start — success (super-admin via env var)
# ---------------------------------------------------------------------------


def test_start_impersonation_success() -> None:
    """POST start returns 200 with session_id when caller is super-admin (env var)."""
    app = _make_app(_SUPER_ADMIN_DICT)
    client = TestClient(app, raise_server_exceptions=True)

    session = _mock_session()

    with (
        patch.dict(os.environ, {"SUPER_ADMIN_EMAILS": _SUPER_ADMIN_EMAIL}),
        patch(_CREATE_SESSION_PATCH, new=AsyncMock(return_value=session)),
        patch(_LOG_ACTION_PATCH, new=AsyncMock()),
    ):
        resp = client.post("/admin/impersonate/target-user-uuid/start")

    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == "sess-uuid"
    assert body["mode"] == "interactive"
    assert "expires_at" in body


# ---------------------------------------------------------------------------
# POST /admin/impersonate/{userId}/start — non-super-admin gets 403
# ---------------------------------------------------------------------------


def test_start_impersonation_non_super_admin() -> None:
    """POST start returns 403 when caller is NOT super-admin."""
    app = _make_app(_ADMIN_DICT)
    client = TestClient(app, raise_server_exceptions=False)

    # Patch _check_super_admin to raise 403 — simulates failing both env-var and DB checks
    from fastapi import HTTPException as _HTTPException

    async def _raise_403(admin_user: dict) -> None:  # noqa: ARG001
        raise _HTTPException(status_code=403, detail="Super admin access required for interactive impersonation.")

    with patch("app.routers.admin.users._check_super_admin", new=_raise_403):
        resp = client.post("/admin/impersonate/target-user-uuid/start")

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /admin/impersonate/sessions/{sessionId} — success
# ---------------------------------------------------------------------------


def test_end_impersonation_success() -> None:
    """DELETE sessions/{sessionId} returns 200 and deactivates session."""
    app = _make_app(_ADMIN_DICT)
    client = TestClient(app, raise_server_exceptions=True)

    session = _mock_session()

    with (
        patch(_VALIDATE_SESSION_PATCH, new=AsyncMock(return_value=session)),
        patch(_DEACTIVATE_SESSION_PATCH, new=AsyncMock()),
        patch(_LOG_ACTION_PATCH, new=AsyncMock()),
    ):
        resp = client.delete("/admin/impersonate/sessions/sess-uuid")

    assert resp.status_code == 200
    assert resp.json()["success"] is True


# ---------------------------------------------------------------------------
# DELETE /admin/impersonate/sessions/{sessionId} — 404 when not found
# ---------------------------------------------------------------------------


def test_end_impersonation_not_found() -> None:
    """DELETE sessions/{sessionId} returns 404 when session not found."""
    app = _make_app(_ADMIN_DICT)
    client = TestClient(app, raise_server_exceptions=False)

    with (
        patch(_VALIDATE_SESSION_PATCH, new=AsyncMock(return_value=None)),
    ):
        resp = client.delete("/admin/impersonate/sessions/nonexistent-sess-uuid")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST start — audit log called with impersonation_session_id
# ---------------------------------------------------------------------------


def test_start_creates_audit_log() -> None:
    """POST start calls log_admin_action with source='impersonation' and session_id."""
    app = _make_app(_SUPER_ADMIN_DICT)
    client = TestClient(app, raise_server_exceptions=True)

    session = _mock_session("audit-sess-uuid")
    mock_log = AsyncMock()

    with (
        patch.dict(os.environ, {"SUPER_ADMIN_EMAILS": _SUPER_ADMIN_EMAIL}),
        patch(_CREATE_SESSION_PATCH, new=AsyncMock(return_value=session)),
        patch(_LOG_ACTION_PATCH, mock_log),
    ):
        resp = client.post("/admin/impersonate/target-user-uuid/start")

    assert resp.status_code == 200
    mock_log.assert_called_once()
    call_kwargs = mock_log.call_args.kwargs
    assert call_kwargs.get("impersonation_session_id") == "audit-sess-uuid"
    # Positional args: admin_user_id, action, target_type, target_id, details, source
    call_args = mock_log.call_args.args
    assert call_args[5] == "impersonation"


# ---------------------------------------------------------------------------
# DELETE end — audit log called
# ---------------------------------------------------------------------------


def test_end_creates_audit_log() -> None:
    """DELETE end calls log_admin_action with source='impersonation' and session_id."""
    app = _make_app(_ADMIN_DICT)
    client = TestClient(app, raise_server_exceptions=True)

    session = _mock_session("deact-sess-uuid")
    mock_log = AsyncMock()

    with (
        patch(_VALIDATE_SESSION_PATCH, new=AsyncMock(return_value=session)),
        patch(_DEACTIVATE_SESSION_PATCH, new=AsyncMock()),
        patch(_LOG_ACTION_PATCH, mock_log),
    ):
        resp = client.delete("/admin/impersonate/sessions/deact-sess-uuid")

    assert resp.status_code == 200
    mock_log.assert_called_once()
    call_kwargs = mock_log.call_args.kwargs
    assert call_kwargs.get("impersonation_session_id") == "deact-sess-uuid"
    call_args = mock_log.call_args.args
    assert call_args[5] == "impersonation"
