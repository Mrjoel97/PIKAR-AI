"""Unit tests for admin authentication middleware (require_admin dependency).

Tests the OR logic: ADMIN_EMAILS env allowlist OR user_roles DB role.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


@pytest.fixture
def credentials():
    """Fake HTTPAuthorizationCredentials for dependency injection."""
    creds = MagicMock(spec=HTTPAuthorizationCredentials)
    creds.credentials = "fake-jwt-token"
    return creds


@pytest.fixture
def admin_creds(credentials):
    """Credentials object (token details irrelevant, verify_token is mocked)."""
    return credentials


# ---------------------------------------------------------------------------
# test_require_admin_env_allowlist
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_admin_env_allowlist(admin_creds):
    """Admin in ADMIN_EMAILS env var is granted access with admin_source='env_allowlist'."""
    admin_user = {"id": "u1", "email": "admin@test.com", "role": "authenticated", "metadata": {}}
    with (
        patch("app.middleware.admin_auth.verify_token", new=AsyncMock(return_value=admin_user)),
        patch.dict(os.environ, {"ADMIN_EMAILS": "admin@test.com"}),
    ):
        from app.middleware.admin_auth import require_admin

        result = await require_admin(admin_creds)

    assert result["admin_source"] == "env_allowlist"
    assert result["email"] == "admin@test.com"


# ---------------------------------------------------------------------------
# test_require_admin_db_role
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_admin_db_role():
    """Admin with DB role is granted access with admin_source='db_role'."""
    non_admin_email_user = {
        "id": "u2",
        "email": "dbadmin@test.com",
        "role": "authenticated",
        "metadata": {},
    }
    mock_client = MagicMock()
    mock_rpc = MagicMock()
    mock_rpc.execute.return_value = MagicMock(data=True)
    mock_client.rpc.return_value = mock_rpc

    creds = MagicMock(spec=HTTPAuthorizationCredentials)
    creds.credentials = "fake-token"

    with (
        patch("app.middleware.admin_auth.verify_token", new=AsyncMock(return_value=non_admin_email_user)),
        patch.dict(os.environ, {"ADMIN_EMAILS": ""}),
        patch("app.middleware.admin_auth.get_service_client", return_value=mock_client),
    ):
        from app.middleware.admin_auth import require_admin

        result = await require_admin(creds)

    assert result["admin_source"] == "db_role"
    assert result["email"] == "dbadmin@test.com"
    mock_client.rpc.assert_called_once_with("is_admin", {"user_id_param": "u2"})


# ---------------------------------------------------------------------------
# test_require_admin_or_logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_admin_or_logic():
    """Either env allowlist OR DB role grants access — env path is taken first when both would pass."""
    user = {"id": "u3", "email": "admin@test.com", "role": "authenticated", "metadata": {}}
    mock_client = MagicMock()

    creds = MagicMock(spec=HTTPAuthorizationCredentials)
    creds.credentials = "fake-token"

    with (
        patch("app.middleware.admin_auth.verify_token", new=AsyncMock(return_value=user)),
        patch.dict(os.environ, {"ADMIN_EMAILS": "admin@test.com"}),
        patch("app.middleware.admin_auth.get_service_client", return_value=mock_client),
    ):
        from app.middleware.admin_auth import require_admin

        result = await require_admin(creds)

    # Env check should short-circuit — DB should NOT be called
    mock_client.rpc.assert_not_called()
    assert result["admin_source"] == "env_allowlist"


# ---------------------------------------------------------------------------
# test_require_admin_denied
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_admin_denied():
    """Non-admin user (not in env, not in DB) receives HTTP 403."""
    user = {"id": "u4", "email": "nobody@test.com", "role": "authenticated", "metadata": {}}
    mock_client = MagicMock()
    mock_rpc = MagicMock()
    mock_rpc.execute.return_value = MagicMock(data=False)
    mock_client.rpc.return_value = mock_rpc

    creds = MagicMock(spec=HTTPAuthorizationCredentials)
    creds.credentials = "fake-token"

    with (
        patch("app.middleware.admin_auth.verify_token", new=AsyncMock(return_value=user)),
        patch.dict(os.environ, {"ADMIN_EMAILS": ""}),
        patch("app.middleware.admin_auth.get_service_client", return_value=mock_client),
    ):
        from app.middleware.admin_auth import require_admin

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(creds)

    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# test_require_admin_db_error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_admin_db_error():
    """DB check raises exception -> returns 503 Service Unavailable."""
    user = {"id": "u5", "email": "admin@test.com", "role": "authenticated", "metadata": {}}
    mock_client = MagicMock()
    mock_rpc = MagicMock()
    mock_rpc.execute.side_effect = RuntimeError("DB connection failed")
    mock_client.rpc.return_value = mock_rpc

    creds = MagicMock(spec=HTTPAuthorizationCredentials)
    creds.credentials = "fake-token"

    with (
        patch("app.middleware.admin_auth.verify_token", new=AsyncMock(return_value=user)),
        patch.dict(os.environ, {"ADMIN_EMAILS": ""}),
        patch("app.middleware.admin_auth.get_service_client", return_value=mock_client),
    ):
        from app.middleware.admin_auth import require_admin

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(creds)

    assert exc_info.value.status_code == 503
