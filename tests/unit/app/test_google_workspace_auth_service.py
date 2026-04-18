# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Regression tests for Google Workspace credential sync and status truth."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request

from app.routers import configuration as configuration_router

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


def _make_upsert_client() -> tuple[MagicMock, MagicMock]:
    """Return a mock client and the underlying table mock."""
    client = MagicMock()
    table = MagicMock()
    execute = MagicMock(return_value=SimpleNamespace(data=[{"id": "cred-1"}]))
    table.upsert.return_value.execute = execute
    client.table.return_value = table
    return client, table


def _make_request(path: str) -> Request:
    """Create a minimal Starlette request for rate-limited router tests."""
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
            "query_string": b"",
        }
    )


class TestGoogleWorkspaceAuthService:
    """Tests for canonical Google Workspace credential storage and lookup."""

    def test_sync_credentials_encrypts_tokens_and_preserves_existing_refresh_token(
        self,
    ) -> None:
        """A refresh-token-less sync should not wipe an existing stored refresh token."""
        from app.services.google_workspace_auth_service import (
            GoogleWorkspaceAuthService,
        )

        client, table = _make_upsert_client()
        service = GoogleWorkspaceAuthService(client=client)

        existing = {
            "refresh_token": "encrypted-existing-refresh",
            "scopes": "gmail.readonly calendar",
            "account_name": "founder@example.com",
            "expires_at": "2026-04-11T12:00:00Z",
        }

        with (
            patch.object(service, "_get_raw_canonical_row", return_value=existing),
            patch(
                "app.services.google_workspace_auth_service.encrypt_secret",
                side_effect=lambda value: f"encrypted::{value}",
            ),
        ):
            service.sync_credentials(
                user_id="user-123",
                access_token="new-access-token",
                refresh_token=None,
                email=None,
                scopes=None,
            )

        row = table.upsert.call_args.args[0]
        assert row["access_token"] == "encrypted::new-access-token"
        assert row["refresh_token"] == "encrypted-existing-refresh"
        assert row["scopes"] == "gmail.readonly calendar"
        assert row["account_name"] == "founder@example.com"

    def test_resolve_credentials_prefers_canonical_storage(self) -> None:
        """Canonical integration_credentials rows should win over legacy fallbacks."""
        from app.services.google_workspace_auth_service import (
            GoogleWorkspaceAuthService,
        )

        service = GoogleWorkspaceAuthService(client=MagicMock())
        canonical = {
            "access_token": "canonical-access",
            "refresh_token": "canonical-refresh",
            "source": "integration_credentials",
        }

        with (
            patch.object(service, "get_canonical_credentials", return_value=canonical),
            patch.object(service, "_get_legacy_google_token_row") as legacy_google,
            patch.object(service, "_get_legacy_refresh_token_row") as legacy_refresh,
        ):
            resolved = service.resolve_credentials("user-123")

        assert resolved == canonical
        legacy_google.assert_not_called()
        legacy_refresh.assert_not_called()

    def test_resolve_credentials_falls_back_to_legacy_sources(self) -> None:
        """Legacy refresh-token storage remains usable while the canonical path rolls out."""
        from app.services.google_workspace_auth_service import (
            GoogleWorkspaceAuthService,
        )

        service = GoogleWorkspaceAuthService(client=MagicMock())
        legacy = {
            "access_token": None,
            "refresh_token": "legacy-refresh",
            "source": "legacy_refresh_token",
        }

        with (
            patch.object(service, "get_canonical_credentials", return_value=None),
            patch.object(service, "_get_legacy_google_token_row", return_value=None),
            patch.object(
                service,
                "_get_legacy_refresh_token_row",
                return_value=legacy,
            ),
        ):
            resolved = service.resolve_credentials("user-123")

        assert resolved == legacy

    def test_resolve_credentials_ignores_legacy_after_explicit_disconnect(self) -> None:
        """An explicit disconnect must suppress legacy fallback credentials."""
        from app.services.google_workspace_auth_service import (
            GoogleWorkspaceAuthService,
        )

        service = GoogleWorkspaceAuthService(client=MagicMock())

        with (
            patch.object(service, "get_canonical_credentials", return_value=None),
            patch.object(service, "_is_explicitly_disconnected", return_value=True),
            patch.object(service, "_get_legacy_google_token_row") as legacy_google,
            patch.object(service, "_get_legacy_refresh_token_row") as legacy_refresh,
        ):
            resolved = service.resolve_credentials("user-123")

        assert resolved is None
        legacy_google.assert_not_called()
        legacy_refresh.assert_not_called()

    def test_get_connection_status_requires_reconnect_for_identity_only(self) -> None:
        """Google identity alone must not report a fully reusable Workspace connection."""
        from app.services.google_workspace_auth_service import (
            GoogleWorkspaceAuthService,
        )

        identity = SimpleNamespace(
            provider="google",
            identity_data={"email": "founder@example.com"},
        )
        user = SimpleNamespace(email="founder@example.com", identities=[identity])
        client = MagicMock()
        client.auth.admin.get_user_by_id.return_value = SimpleNamespace(user=user)
        service = GoogleWorkspaceAuthService(client=client)

        with patch.object(service, "resolve_credentials", return_value=None):
            status = service.get_connection_status("user-123")

        assert status["connected"] is False
        assert status["needs_reconnect"] is True
        assert status["provider"] == "google"
        assert status["email"] == "founder@example.com"

    def test_get_connection_status_accepts_usable_legacy_refresh_token(self) -> None:
        """A reusable legacy refresh token should still count as connected."""
        from app.services.google_workspace_auth_service import (
            GoogleWorkspaceAuthService,
        )

        client = MagicMock()
        client.auth.admin.get_user_by_id.return_value = SimpleNamespace(user=None)
        service = GoogleWorkspaceAuthService(client=client)

        with patch.object(
            service,
            "resolve_credentials",
            return_value={
                "access_token": None,
                "refresh_token": "legacy-refresh",
                "account_name": "legacy@example.com",
                "source": "legacy_refresh_token",
            },
        ):
            status = service.get_connection_status("user-123")

        assert status["connected"] is True
        assert status["needs_reconnect"] is False
        assert status["email"] == "legacy@example.com"
        assert status["connection_source"] == "legacy_refresh_token"

    def test_disconnect_clears_backend_rows_and_marks_explicit_disconnect(self) -> None:
        """Disconnect should remove reusable rows and persist a tombstone."""
        from app.services.google_workspace_auth_service import (
            GoogleWorkspaceAuthService,
        )

        service = GoogleWorkspaceAuthService(client=MagicMock())

        with (
            patch.object(
                service,
                "resolve_credentials",
                return_value={"refresh_token": "legacy-refresh"},
            ),
            patch.object(service, "_delete_rows", side_effect=[True, False, True, True]) as delete_rows,
            patch.object(service, "_set_disconnect_marker") as set_marker,
        ):
            disconnected = service.disconnect("user-123")

        assert disconnected is True
        assert delete_rows.call_count == 4
        set_marker.assert_called_once_with("user-123")


class TestConfigurationRouterGoogleWorkspace:
    """Tests for the configuration router's Google Workspace contract."""

    @pytest.mark.asyncio
    async def test_status_endpoint_returns_service_truth(self) -> None:
        """The router should surface the backend truth contract unchanged."""
        mocked_status = {
            "connected": False,
            "email": "founder@example.com",
            "provider": "google",
            "features": [],
            "message": "Reconnect Google Workspace to finish storing a reusable server-side token.",
            "needs_reconnect": True,
            "connected_via_identity": True,
            "connection_source": None,
        }

        service = MagicMock()
        service.get_connection_status.return_value = mocked_status

        with patch(
            "app.routers.configuration.get_google_workspace_auth_service",
            return_value=service,
        ):
            result = await configuration_router.get_google_workspace_status(
                request=_make_request("/configuration/google-workspace-status"),
                current_user_id="user-123",
            )

        assert result.connected is False
        assert result.needs_reconnect is True
        assert result.email == "founder@example.com"
        service.get_connection_status.assert_called_once_with("user-123")

    @pytest.mark.asyncio
    async def test_sync_endpoint_persists_credentials_for_current_user(self) -> None:
        """The sync endpoint should store credentials against the authenticated user."""
        service = MagicMock()

        body = configuration_router.GoogleWorkspaceSyncRequest(
            access_token="google-access",
            refresh_token="google-refresh",
            scopes=["email", "profile"],
            email="founder@example.com",
        )

        with patch(
            "app.routers.configuration.get_google_workspace_auth_service",
            return_value=service,
        ):
            result = await configuration_router.sync_google_workspace_credentials(
                body=body,
                request=_make_request("/configuration/google-workspace/sync"),
                current_user_id="user-123",
            )

        assert result["success"] is True
        service.sync_credentials.assert_called_once_with(
            user_id="user-123",
            access_token="google-access",
            refresh_token="google-refresh",
            expires_at=None,
            scopes=["email", "profile"],
            email="founder@example.com",
        )

    @pytest.mark.asyncio
    async def test_disconnect_endpoint_uses_backend_owned_disconnect(self) -> None:
        """The router should disconnect Google Workspace without exposing tokens."""
        service = MagicMock()
        service.disconnect.return_value = True

        with patch(
            "app.routers.configuration.get_google_workspace_auth_service",
            return_value=service,
        ):
            result = await configuration_router.disconnect_google_workspace(
                request=_make_request("/configuration/google-workspace"),
                current_user_id="user-123",
            )

        assert result.success is True
        assert result.message == "Google Workspace disconnected."
        service.disconnect.assert_called_once_with("user-123")

    @pytest.mark.asyncio
    async def test_disconnect_endpoint_returns_404_when_no_connection_exists(self) -> None:
        """Disconnect should report 404 when nothing reusable is connected."""
        service = MagicMock()
        service.disconnect.return_value = False

        with (
            patch(
                "app.routers.configuration.get_google_workspace_auth_service",
                return_value=service,
            ),
            pytest.raises(configuration_router.HTTPException) as exc_info,
        ):
            await configuration_router.disconnect_google_workspace(
                request=_make_request("/configuration/google-workspace"),
                current_user_id="user-123",
            )

        assert exc_info.value.status_code == 404
