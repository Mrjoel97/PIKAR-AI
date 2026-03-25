"""Unit tests for role-based access control in admin middleware.

Tests verify:
- test_require_admin_returns_role: require_admin returns admin_role field from user_roles table
- test_require_admin_env_allowlist_returns_super_admin: env allowlist path returns admin_role='super_admin'
- test_require_admin_role_blocks_insufficient_role: require_admin_role('admin') raises 403 for junior_admin
- test_require_admin_role_allows_sufficient_role: require_admin_role('senior_admin') allows admin (level 3 >= 2)
- test_junior_admin_write_blocked: junior_admin calling write endpoint gated by require_admin_role('senior_admin') gets 403
- test_senior_admin_no_role_management: senior_admin calling role-management endpoint gated by require_admin_role('admin') gets 403
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_creds(token: str = "fake-jwt") -> HTTPAuthorizationCredentials:
    """Create fake HTTPAuthorizationCredentials."""
    creds = MagicMock(spec=HTTPAuthorizationCredentials)
    creds.credentials = token
    return creds


def _make_user(user_id: str = "u1", email: str = "admin@test.com") -> dict:
    """Build a base user dict (as returned by verify_token)."""
    return {
        "id": user_id,
        "email": email,
        "role": "authenticated",
        "metadata": {},
    }


def _mock_client_with_role(role: str) -> MagicMock:
    """Return a service client mock whose user_roles query returns *role*."""
    client = MagicMock()
    # is_admin RPC (used by require_admin DB path)
    rpc_mock = MagicMock()
    rpc_mock.execute.return_value = MagicMock(data=True)
    client.rpc.return_value = rpc_mock

    # user_roles table query chain: .table().select().eq().execute()
    role_result = MagicMock()
    role_result.data = [{"role": role}]
    table_mock = MagicMock()
    select_mock = MagicMock()
    eq_mock = MagicMock()
    eq_mock.execute.return_value = role_result
    select_mock.eq.return_value = eq_mock
    table_mock.select.return_value = select_mock
    client.table.return_value = table_mock

    return client


# ---------------------------------------------------------------------------
# Test 1: require_admin returns admin_role field from user_roles table
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_admin_returns_role():
    """require_admin returns dict with admin_role field set to the user's role from user_roles table."""
    user = _make_user(user_id="u1", email="dbadmin@test.com")
    client = _mock_client_with_role("senior_admin")

    with (
        patch("app.middleware.admin_auth.verify_token", new=AsyncMock(return_value=user)),
        patch.dict(os.environ, {"ADMIN_EMAILS": ""}),
        patch("app.middleware.admin_auth.get_service_client", return_value=client),
    ):
        from app.middleware.admin_auth import require_admin

        result = await require_admin(_make_creds())

    assert result["admin_role"] == "senior_admin"
    assert result["admin_source"] == "db_role"


# ---------------------------------------------------------------------------
# Test 2: env allowlist path returns admin_role='super_admin'
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_admin_env_allowlist_returns_super_admin():
    """Env allowlist path always returns admin_role='super_admin' (bootstrap admins are super)."""
    user = _make_user(email="admin@test.com")

    with (
        patch("app.middleware.admin_auth.verify_token", new=AsyncMock(return_value=user)),
        patch.dict(os.environ, {"ADMIN_EMAILS": "admin@test.com"}),
    ):
        from app.middleware.admin_auth import require_admin

        result = await require_admin(_make_creds())

    assert result["admin_role"] == "super_admin"
    assert result["admin_source"] == "env_allowlist"


# ---------------------------------------------------------------------------
# Test 3: require_admin_role('admin') raises 403 for junior_admin (level 1 < 3)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_admin_role_blocks_insufficient_role():
    """require_admin_role('admin') raises HTTP 403 for a junior_admin (level 1 < required 3)."""
    user = _make_user(user_id="u3", email="junior@test.com")
    client = _mock_client_with_role("junior_admin")

    with (
        patch("app.middleware.admin_auth.verify_token", new=AsyncMock(return_value=user)),
        patch.dict(os.environ, {"ADMIN_EMAILS": ""}),
        patch("app.middleware.admin_auth.get_service_client", return_value=client),
    ):
        from app.middleware.admin_auth import require_admin_role

        checker = require_admin_role("admin")
        with pytest.raises(HTTPException) as exc_info:
            await checker(_make_creds())

    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Test 4: require_admin_role('senior_admin') allows admin (level 3 >= level 2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_admin_role_allows_sufficient_role():
    """require_admin_role('senior_admin') passes when caller has 'admin' role (level 3 >= 2)."""
    user = _make_user(user_id="u4", email="fulladmin@test.com")
    client = _mock_client_with_role("admin")

    with (
        patch("app.middleware.admin_auth.verify_token", new=AsyncMock(return_value=user)),
        patch.dict(os.environ, {"ADMIN_EMAILS": ""}),
        patch("app.middleware.admin_auth.get_service_client", return_value=client),
    ):
        from app.middleware.admin_auth import require_admin_role

        checker = require_admin_role("senior_admin")
        result = await checker(_make_creds())

    assert result["admin_role"] == "admin"


# ---------------------------------------------------------------------------
# Test 5: junior_admin calling a write endpoint gated by require_admin_role('senior_admin') gets 403
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_junior_admin_write_blocked():
    """junior_admin (level 1) calling an endpoint gated by require_admin_role('senior_admin') gets 403."""
    user = _make_user(user_id="u5", email="junior2@test.com")
    client = _mock_client_with_role("junior_admin")

    with (
        patch("app.middleware.admin_auth.verify_token", new=AsyncMock(return_value=user)),
        patch.dict(os.environ, {"ADMIN_EMAILS": ""}),
        patch("app.middleware.admin_auth.get_service_client", return_value=client),
    ):
        from app.middleware.admin_auth import require_admin_role

        # Write endpoints require senior_admin (level 2)
        checker = require_admin_role("senior_admin")
        with pytest.raises(HTTPException) as exc_info:
            await checker(_make_creds())

    assert exc_info.value.status_code == 403
    assert "senior_admin" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Test 6: senior_admin calling a role-management endpoint gated by require_admin_role('admin') gets 403
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_senior_admin_no_role_management():
    """senior_admin (level 2) calling a role-management endpoint gated by require_admin_role('admin') gets 403."""
    user = _make_user(user_id="u6", email="senior@test.com")
    client = _mock_client_with_role("senior_admin")

    with (
        patch("app.middleware.admin_auth.verify_token", new=AsyncMock(return_value=user)),
        patch.dict(os.environ, {"ADMIN_EMAILS": ""}),
        patch("app.middleware.admin_auth.get_service_client", return_value=client),
    ):
        from app.middleware.admin_auth import require_admin_role

        # Role management requires admin (level 3)
        checker = require_admin_role("admin")
        with pytest.raises(HTTPException) as exc_info:
            await checker(_make_creds())

    assert exc_info.value.status_code == 403
    assert "admin" in exc_info.value.detail
