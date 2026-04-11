# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the account router's personal-data export endpoint.

Covers GDPR-01: an authenticated user can trigger a personal-data export
through POST /account/export and receive a signed download URL.

Test matrix:
- Authenticated success path returns signed URL and export metadata
- Service exception is surfaced as HTTP 500 (never leaks raw error)
- Unauthenticated request is rejected by the auth gate (401/403)
- Returned export is scoped to the requesting user (not another user's data)
"""

from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Stub heavy / Windows-flaky modules BEFORE importing the router.
# ---------------------------------------------------------------------------

if "app.middleware.rate_limiter" not in sys.modules:
    _mock_rate_limiter = types.ModuleType("app.middleware.rate_limiter")
    _mock_limiter = MagicMock()
    _mock_limiter.limit = lambda *a, **kw: (lambda fn: fn)
    _mock_rate_limiter.limiter = _mock_limiter
    _mock_rate_limiter.get_user_persona_limit = MagicMock(return_value="100/minute")
    sys.modules["app.middleware.rate_limiter"] = _mock_rate_limiter

# Stub the heavy import chain BEFORE the router is imported.
#
# app/routers/account.py imports:
#   - app.routers.onboarding (get_current_user_id) → deep chain into services/personas
#   - app.services.personal_data_export_service → supabase chain
#   - app.services.supabase (get_service_client) → supabase chain
#
# Strategy: stub app.routers.onboarding directly (it is not a package) so the
# entire user_onboarding_service / personas / supabase_client chain is bypassed.
# Also stub the two services account.py imports directly.

# Shared fake dependency function that will be used in dependency_overrides.
async def _default_get_current_user_id() -> str:  # noqa: RUF029
    return "user-test-123"


_MOCK_CLIENT = MagicMock()


def _stub_module(path: str, **attrs: object) -> None:
    """Insert a stub module if not already present in sys.modules."""
    if path not in sys.modules:
        mod = types.ModuleType(path)
        for name, val in attrs.items():
            setattr(mod, name, val)
        sys.modules[path] = mod


# Stub onboarding router — account.py only uses get_current_user_id from it.
_stub_module(
    "app.routers.onboarding",
    get_current_user_id=_default_get_current_user_id,
    router=MagicMock(),
)
_stub_module(
    "app.services.supabase",
    get_service_client=MagicMock(return_value=_MOCK_CLIENT),
    get_async_client=MagicMock(return_value=_MOCK_CLIENT),
)
_stub_module(
    "app.services.personal_data_export_service",
    PersonalDataExportService=MagicMock(),
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_EXPORT_SUCCESS_RESULT = {
    "url": "https://storage.example.com/signed/export.json",
    "filename": "personal-data-export_20260411T120000123456Z_abc12345.json",
    "size_bytes": 4096,
    "format": "json",
    "generated_at": "2026-04-11T12:00:00+00:00",
    "sections": ["account", "privacy", "initiatives", "workflows", "content"],
    "warnings": [],
}


def _build_app(*, user_id: str = "user-test-123"):
    """Build a minimal FastAPI app wrapping the account router.

    Overrides ``get_current_user_id`` so no real JWT is needed.
    Returns ``(app, service_mock, service_patcher)``.
    """
    from app.routers.account import router
    from app.routers.onboarding import get_current_user_id

    service_mock = MagicMock()
    service_mock.export_personal_data = AsyncMock(return_value=_EXPORT_SUCCESS_RESULT)
    service_patcher = patch(
        "app.routers.account.PersonalDataExportService",
        return_value=service_mock,
    )
    service_patcher.start()

    app = FastAPI()

    async def _fake_user_id() -> str:
        return user_id

    app.dependency_overrides[get_current_user_id] = _fake_user_id
    app.include_router(router)

    return app, service_mock, service_patcher


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_authenticated_success_returns_signed_url():
    """Authenticated POST /account/export returns 200 with signed URL."""
    app, _service_mock, patcher = _build_app()
    try:
        client = TestClient(app)
        resp = client.post("/account/export")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        assert body["url"] == _EXPORT_SUCCESS_RESULT["url"]
        assert body["filename"] == _EXPORT_SUCCESS_RESULT["filename"]
        assert body["format"] == "json"
        assert body["size_bytes"] == 4096
        assert "account" in body["sections"]
    finally:
        patcher.stop()


@pytest.mark.asyncio
async def test_export_response_contains_all_required_fields():
    """The export response contract provides every field the frontend needs."""
    app, _service_mock, patcher = _build_app()
    try:
        client = TestClient(app)
        resp = client.post("/account/export")
        body = resp.json()
        for field in ("success", "message", "url", "filename", "size_bytes", "format", "generated_at", "sections"):
            assert field in body, f"Missing required field: {field}"
    finally:
        patcher.stop()


# ---------------------------------------------------------------------------
# Scoping: service receives the authenticated user_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_scoped_to_authenticated_user():
    """PersonalDataExportService is constructed with the authenticated user_id."""
    actor_id = "user-actor-abc"
    app, _service_mock, patcher = _build_app(user_id=actor_id)
    try:
        from app.routers import account as account_module

        service_cls_mock = account_module.PersonalDataExportService
        client = TestClient(app)
        client.post("/account/export")
        service_cls_mock.assert_called_once_with(user_id=actor_id)
    finally:
        patcher.stop()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_service_exception_returns_500():
    """An unhandled service error is mapped to HTTP 500, not leaked."""
    from app.routers.account import router
    from app.routers.onboarding import get_current_user_id

    service_mock = MagicMock()
    service_mock.export_personal_data = AsyncMock(
        side_effect=RuntimeError("DB connection failed")
    )
    patcher = patch(
        "app.routers.account.PersonalDataExportService",
        return_value=service_mock,
    )
    patcher.start()

    app = FastAPI()

    async def _fake_user_id() -> str:
        return "user-test-123"

    app.dependency_overrides[get_current_user_id] = _fake_user_id
    app.include_router(router)

    try:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/account/export")
        assert resp.status_code == 500, resp.text
        body = resp.json()
        assert "detail" in body
        # Raw error must not leak internal details
        assert "DB connection failed" not in body["detail"]
    finally:
        patcher.stop()


# ---------------------------------------------------------------------------
# Auth gate: no auth token -> 401 or 403
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_without_auth_header_is_rejected():
    """POST /account/export without an Authorization header is rejected.

    The real ``get_current_user_id`` from ``app.app_utils.auth`` raises 401
    when no valid bearer token is present. This test uses that real dependency
    (not the onboarding stub) to verify the auth gate fires.
    """
    from fastapi.security import HTTPBearer

    from app.routers.account import router

    # Retrieve the real dependency from app_utils.auth (not the onboarding stub).
    from app.app_utils.auth import get_current_user_id as real_get_current_user_id

    service_patcher = patch("app.routers.account.PersonalDataExportService")
    service_patcher.start()

    try:
        app = FastAPI()
        # Override the stubbed dependency with the real one that enforces auth.
        app.dependency_overrides[_default_get_current_user_id] = real_get_current_user_id
        app.include_router(router)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/account/export")
        assert resp.status_code in (401, 403), resp.text
    finally:
        service_patcher.stop()


# ===========================================================================
# Account DELETION endpoint tests (GDPR-02 / GDPR-03)
# ===========================================================================
#
# Test matrix:
# - Authenticated DELETE /account/delete returns 200 success response
# - Response contract: success=True, message is non-empty, action is irreversible
# - Database failure is surfaced as HTTP 500 (with privacy@pikar-ai.com contact)
# - Unauthenticated request is rejected (401/403)
# - Deletion is scoped to the authenticated user (RPC called with correct user_id)
# ===========================================================================


class _DeleteAppContext:
    """Context manager that builds a deletion-endpoint test app and keeps the patch active."""

    def __init__(self, *, user_id: str = "user-del-test-999", rpc_side_effect=None):
        self._user_id = user_id
        self._rpc_side_effect = rpc_side_effect
        self._patcher = None
        self.mock_client: MagicMock | None = None
        self.app: FastAPI | None = None

    def __enter__(self):
        from app.routers.account import router
        from app.routers.onboarding import get_current_user_id

        mock_client = MagicMock()

        # Chain: .table().insert().execute() → success
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock()
        # Chain: .table().update().eq().execute() → success
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        # Chain: .rpc().execute() → success or side effect
        rpc_mock = MagicMock()
        if self._rpc_side_effect:
            rpc_mock.execute.side_effect = self._rpc_side_effect
        mock_client.rpc.return_value = rpc_mock

        self._patcher = patch("app.routers.account.get_service_client", return_value=mock_client)
        self._patcher.start()
        self.mock_client = mock_client

        app = FastAPI()
        user_id = self._user_id

        async def _fake_user_id() -> str:
            return user_id

        app.dependency_overrides[get_current_user_id] = _fake_user_id
        app.include_router(router)
        self.app = app
        return self

    def __exit__(self, *args):
        if self._patcher:
            self._patcher.stop()


@pytest.mark.asyncio
async def test_deletion_authenticated_success_returns_200():
    """Authenticated DELETE /account/delete returns 200 with success=True."""
    with _DeleteAppContext() as ctx:
        client = TestClient(ctx.app)
        resp = client.delete("/account/delete")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["message"]


@pytest.mark.asyncio
async def test_deletion_response_message_is_non_empty():
    """The deletion response message communicates that the action is permanent."""
    with _DeleteAppContext() as ctx:
        client = TestClient(ctx.app)
        resp = client.delete("/account/delete")
    body = resp.json()
    assert isinstance(body["message"], str)
    assert len(body["message"]) > 10


@pytest.mark.asyncio
async def test_deletion_rpc_called_with_authenticated_user_id():
    """delete_user_account RPC is called with the authenticated user_id."""
    actor_id = "user-actor-delete-xyz"
    with _DeleteAppContext(user_id=actor_id) as ctx:
        client = TestClient(ctx.app)
        client.delete("/account/delete")
        ctx.mock_client.rpc.assert_called_once_with(
            "delete_user_account", {"p_user_id": actor_id}
        )


@pytest.mark.asyncio
async def test_deletion_database_failure_returns_500():
    """A database exception during deletion is surfaced as HTTP 500."""
    with _DeleteAppContext(rpc_side_effect=RuntimeError("DB unavailable")) as ctx:
        client = TestClient(ctx.app, raise_server_exceptions=False)
        resp = client.delete("/account/delete")
    assert resp.status_code == 500, resp.text
    body = resp.json()
    assert "detail" in body
    # Raw error must not leak
    assert "DB unavailable" not in body["detail"]


@pytest.mark.asyncio
async def test_deletion_500_detail_includes_privacy_contact():
    """The 500 error detail must include the privacy contact email."""
    with _DeleteAppContext(rpc_side_effect=RuntimeError("fail")) as ctx:
        client = TestClient(ctx.app, raise_server_exceptions=False)
        resp = client.delete("/account/delete")
    body = resp.json()
    assert "privacy@pikar-ai.com" in body["detail"]


@pytest.mark.asyncio
async def test_deletion_without_auth_is_rejected():
    """DELETE /account/delete without Authorization header is rejected (401/403)."""
    from app.app_utils.auth import get_current_user_id as real_get_current_user_id
    from app.routers.account import router

    app = FastAPI()
    app.dependency_overrides[_default_get_current_user_id] = real_get_current_user_id
    app.include_router(router)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.delete("/account/delete")
    assert resp.status_code in (401, 403), resp.text
