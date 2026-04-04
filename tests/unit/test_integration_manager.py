# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for IntegrationManager service."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Patch env vars before importing the service module
_ENV_PATCH = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_ANON_KEY": "test-anon-key",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
    "ADMIN_ENCRYPTION_KEY": "dGVzdGtleTEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNA==",
}


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required env vars for all tests."""
    for key, value in _ENV_PATCH.items():
        monkeypatch.setenv(key, value)


def _make_db_response(data: list | None = None) -> SimpleNamespace:
    """Create a mock Supabase response."""
    return SimpleNamespace(data=data or [])


class TestStoreCredentials:
    """Tests for IntegrationManager.store_credentials."""

    @pytest.mark.asyncio
    async def test_store_credentials_encrypts_tokens(self) -> None:
        """store_credentials should encrypt access_token and refresh_token."""
        from app.services.integration_manager import IntegrationManager

        mgr = IntegrationManager.__new__(IntegrationManager)
        mgr._url = "https://test.supabase.co"
        mgr._anon_key = "test-anon-key"
        mgr._user_token = None
        mgr._client = None

        cred_row = {
            "id": "cred-1",
            "user_id": "user-1",
            "provider": "hubspot",
            "access_token": "encrypted_access",
            "refresh_token": "encrypted_refresh",
        }

        with (
            patch(
                "app.services.integration_manager.encrypt_secret",
                side_effect=lambda x: f"encrypted_{x}",
            ) as mock_encrypt,
            patch.object(
                mgr,
                "execute",
                new_callable=AsyncMock,
                return_value=_make_db_response([cred_row]),
            ),
        ):
            result = await mgr.store_credentials(
                user_id="user-1",
                provider="hubspot",
                access_token="real_access_token",
                refresh_token="real_refresh_token",
                expires_at="2026-05-01T00:00:00Z",
                scopes="contacts.read",
                account_name="Test Account",
            )

            # encrypt_secret should be called for both tokens
            assert mock_encrypt.call_count == 2
            mock_encrypt.assert_any_call("real_access_token")
            mock_encrypt.assert_any_call("real_refresh_token")
            assert result == cred_row


class TestGetValidToken:
    """Tests for IntegrationManager.get_valid_token."""

    @pytest.mark.asyncio
    async def test_get_valid_token_decrypts(self) -> None:
        """get_valid_token should decrypt the access token from DB."""
        from app.services.integration_manager import IntegrationManager

        mgr = IntegrationManager.__new__(IntegrationManager)
        mgr._url = "https://test.supabase.co"
        mgr._anon_key = "test-anon-key"
        mgr._user_token = None
        mgr._client = None

        future_time = (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat()
        cred_row = {
            "id": "cred-1",
            "user_id": "user-1",
            "provider": "hubspot",
            "access_token": "encrypted_token",
            "refresh_token": "encrypted_refresh",
            "expires_at": future_time,
        }

        with (
            patch.object(
                mgr,
                "execute",
                new_callable=AsyncMock,
                return_value=_make_db_response([cred_row]),
            ),
            patch(
                "app.services.integration_manager.decrypt_secret",
                return_value="decrypted_access_token",
            ) as mock_decrypt,
        ):
            token = await mgr.get_valid_token("user-1", "hubspot")

            mock_decrypt.assert_called_once_with("encrypted_token")
            assert token == "decrypted_access_token"

    @pytest.mark.asyncio
    async def test_get_valid_token_refreshes_when_expiring(self) -> None:
        """get_valid_token should refresh when token expires in <5 min."""
        from app.services.integration_manager import IntegrationManager

        mgr = IntegrationManager.__new__(IntegrationManager)
        mgr._url = "https://test.supabase.co"
        mgr._anon_key = "test-anon-key"
        mgr._user_token = None
        mgr._client = None

        # Token expires in 2 minutes (should trigger refresh)
        expiring_time = (datetime.now(tz=timezone.utc) + timedelta(minutes=2)).isoformat()
        cred_row = {
            "id": "cred-1",
            "user_id": "user-1",
            "provider": "hubspot",
            "access_token": "old_encrypted",
            "refresh_token": "encrypted_refresh",
            "expires_at": expiring_time,
        }

        refreshed_row = {**cred_row, "access_token": "new_encrypted"}

        with (
            patch.object(
                mgr,
                "execute",
                new_callable=AsyncMock,
                return_value=_make_db_response([cred_row]),
            ),
            patch.object(
                mgr,
                "_refresh_token",
                new_callable=AsyncMock,
                return_value=refreshed_row,
            ) as mock_refresh,
            patch(
                "app.services.integration_manager.decrypt_secret",
                return_value="new_decrypted_token",
            ),
        ):
            token = await mgr.get_valid_token("user-1", "hubspot")

            mock_refresh.assert_called_once()
            assert token == "new_decrypted_token"

    @pytest.mark.asyncio
    async def test_get_valid_token_double_check_after_lock(self) -> None:
        """get_valid_token should re-read credential after acquiring lock."""
        from app.services.integration_manager import IntegrationManager

        mgr = IntegrationManager.__new__(IntegrationManager)
        mgr._url = "https://test.supabase.co"
        mgr._anon_key = "test-anon-key"
        mgr._user_token = None
        mgr._client = None

        # First call: token is expiring
        expiring_time = (datetime.now(tz=timezone.utc) + timedelta(minutes=2)).isoformat()
        # Second call (after lock): token is fresh (another coroutine refreshed it)
        fresh_time = (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat()

        expiring_row = {
            "id": "cred-1",
            "user_id": "user-1",
            "provider": "hubspot",
            "access_token": "old_encrypted",
            "refresh_token": "encrypted_refresh",
            "expires_at": expiring_time,
        }
        fresh_row = {**expiring_row, "access_token": "fresh_encrypted", "expires_at": fresh_time}

        call_count = 0

        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_db_response([expiring_row])
            return _make_db_response([fresh_row])

        with (
            patch.object(mgr, "execute", side_effect=mock_execute),
            patch(
                "app.services.integration_manager.decrypt_secret",
                return_value="fresh_decrypted_token",
            ),
            patch.object(mgr, "_refresh_token", new_callable=AsyncMock) as mock_refresh,
        ):
            token = await mgr.get_valid_token("user-1", "hubspot")

            # Should NOT have called _refresh_token since re-read found fresh token
            mock_refresh.assert_not_called()
            assert token == "fresh_decrypted_token"
            # Should have read from DB twice (initial + after lock)
            assert call_count == 2


class TestGetCredentials:
    """Tests for IntegrationManager.get_credentials."""

    @pytest.mark.asyncio
    async def test_get_credentials_returns_none_for_missing(self) -> None:
        """get_credentials should return None for non-existent user+provider."""
        from app.services.integration_manager import IntegrationManager

        mgr = IntegrationManager.__new__(IntegrationManager)
        mgr._url = "https://test.supabase.co"
        mgr._anon_key = "test-anon-key"
        mgr._user_token = None
        mgr._client = None

        with patch.object(
            mgr,
            "execute",
            new_callable=AsyncMock,
            return_value=_make_db_response([]),
        ):
            result = await mgr.get_credentials("user-1", "nonexistent")
            assert result is None


class TestDeleteCredentials:
    """Tests for IntegrationManager.delete_credentials."""

    @pytest.mark.asyncio
    async def test_delete_credentials_removes_row(self) -> None:
        """delete_credentials should remove the credential row."""
        from app.services.integration_manager import IntegrationManager

        mgr = IntegrationManager.__new__(IntegrationManager)
        mgr._url = "https://test.supabase.co"
        mgr._anon_key = "test-anon-key"
        mgr._user_token = None
        mgr._client = None

        with patch.object(
            mgr,
            "execute",
            new_callable=AsyncMock,
            return_value=_make_db_response([{"id": "cred-1"}]),
        ) as mock_exec:
            result = await mgr.delete_credentials("user-1", "hubspot")
            assert result is True
            mock_exec.assert_called_once()


class TestSyncState:
    """Tests for IntegrationManager sync state operations."""

    @pytest.mark.asyncio
    async def test_update_sync_state_upserts(self) -> None:
        """update_sync_state should upsert sync state with cursor and error_count."""
        from app.services.integration_manager import IntegrationManager

        mgr = IntegrationManager.__new__(IntegrationManager)
        mgr._url = "https://test.supabase.co"
        mgr._anon_key = "test-anon-key"
        mgr._user_token = None
        mgr._client = None

        state_row = {
            "id": "state-1",
            "user_id": "user-1",
            "provider": "hubspot",
            "sync_cursor": {"page": 2},
            "error_count": 0,
        }

        with patch.object(
            mgr,
            "execute",
            new_callable=AsyncMock,
            return_value=_make_db_response([state_row]),
        ):
            result = await mgr.update_sync_state(
                user_id="user-1",
                provider="hubspot",
                sync_cursor={"page": 2},
                error_count=0,
            )
            assert result == state_row

    @pytest.mark.asyncio
    async def test_get_sync_state_returns_none_when_no_state(self) -> None:
        """get_sync_state should return None when no state exists."""
        from app.services.integration_manager import IntegrationManager

        mgr = IntegrationManager.__new__(IntegrationManager)
        mgr._url = "https://test.supabase.co"
        mgr._anon_key = "test-anon-key"
        mgr._user_token = None
        mgr._client = None

        with patch.object(
            mgr,
            "execute",
            new_callable=AsyncMock,
            return_value=_make_db_response([]),
        ):
            result = await mgr.get_sync_state("user-1", "hubspot")
            assert result is None
