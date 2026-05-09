# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the synchronous Google Workspace token refresh helper.

Pins WORKSPACE-04 from Phase 102: tokens auto-refresh within 5 minutes of
expiry without rewriting the in-flight tool helpers to async.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest


def _make_tool_context(state: dict) -> SimpleNamespace:
    """Return a minimal stand-in for an ADK ToolContext with mutable state."""
    return SimpleNamespace(state=state)


def _iso_now_plus(seconds: int) -> str:
    """Return an ISO-8601 UTC timestamp `seconds` from now."""
    return (datetime.now(tz=timezone.utc) + timedelta(seconds=seconds)).isoformat()


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default Google Workspace OAuth client env for refresh tests."""
    monkeypatch.setenv("GOOGLE_WORKSPACE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_WORKSPACE_CLIENT_SECRET", "cs")


class TestRefreshIfExpiring:
    """Tests for app.services.google_workspace_token_refresh.refresh_if_expiring."""

    def test_refresh_when_expiring(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Within the 5-min threshold, the helper posts to /token and updates state."""
        from app.services import google_workspace_token_refresh as module

        state: dict = {
            "user_id": "user-1",
            "google_provider_token": "old-access",
            "google_refresh_token": "rt-1",
            "google_token_expires_at": _iso_now_plus(120),  # 2 min from now
        }
        tool_context = _make_tool_context(state)

        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {
            "access_token": "new-access",
            "refresh_token": "rt-2",
            "expires_in": 3600,
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response

        mock_service = MagicMock()
        mock_service.sync_credentials = MagicMock(return_value=True)

        with (
            patch.object(module, "httpx") as mock_httpx,
            patch.object(
                module, "get_google_workspace_auth_service", return_value=mock_service
            ),
        ):
            mock_httpx.Client.return_value.__enter__.return_value = mock_client
            mock_httpx.RequestError = httpx.RequestError
            module.refresh_if_expiring(tool_context)

        # HTTP call assertions
        assert mock_client.post.call_count == 1
        call_args = mock_client.post.call_args
        assert call_args.args[0] == "https://oauth2.googleapis.com/token"
        data = call_args.kwargs.get("data") or (
            call_args.args[1] if len(call_args.args) > 1 else {}
        )
        assert data["grant_type"] == "refresh_token"
        assert data["refresh_token"] == "rt-1"
        assert data["client_id"] == "cid"
        assert data["client_secret"] == "cs"

        # State updated
        assert state["google_provider_token"] == "new-access"
        assert state["google_refresh_token"] == "rt-2"
        new_expiry = datetime.fromisoformat(state["google_token_expires_at"])
        delta = new_expiry - datetime.now(tz=timezone.utc)
        assert timedelta(seconds=3300) <= delta <= timedelta(seconds=3700)

        # Persisted via sync_credentials
        mock_service.sync_credentials.assert_called_once()
        kwargs = mock_service.sync_credentials.call_args.kwargs
        assert kwargs["user_id"] == "user-1"
        assert kwargs["access_token"] == "new-access"
        assert kwargs["refresh_token"] == "rt-2"
        assert kwargs["expires_at"] == state["google_token_expires_at"]

    def test_no_op_when_token_fresh(self) -> None:
        """If expiry is more than 5 minutes away, no HTTP call is made."""
        from app.services import google_workspace_token_refresh as module

        state: dict = {
            "user_id": "user-1",
            "google_provider_token": "fresh-access",
            "google_refresh_token": "rt-1",
            "google_token_expires_at": _iso_now_plus(1800),  # 30 min from now
        }
        original_state = dict(state)
        tool_context = _make_tool_context(state)

        mock_client = MagicMock()
        with patch.object(module, "httpx") as mock_httpx:
            mock_httpx.Client.return_value.__enter__.return_value = mock_client
            module.refresh_if_expiring(tool_context)

        mock_client.post.assert_not_called()
        assert state == original_state

    def test_no_op_when_expires_at_none(self) -> None:
        """Legacy fallback paths with no expiry must remain a no-op."""
        from app.services import google_workspace_token_refresh as module

        state: dict = {
            "user_id": "user-1",
            "google_provider_token": "legacy-access",
            "google_refresh_token": "rt-1",
            "google_token_expires_at": None,
        }
        original_state = dict(state)
        tool_context = _make_tool_context(state)

        mock_client = MagicMock()
        with patch.object(module, "httpx") as mock_httpx:
            mock_httpx.Client.return_value.__enter__.return_value = mock_client
            module.refresh_if_expiring(tool_context)

        mock_client.post.assert_not_called()
        assert state == original_state

    def test_no_op_when_no_user_id(self) -> None:
        """Missing user_id (e.g., anonymous context) must skip the refresh."""
        from app.services import google_workspace_token_refresh as module

        state: dict = {
            "google_provider_token": "old-access",
            "google_refresh_token": "rt-1",
            "google_token_expires_at": _iso_now_plus(60),
        }
        tool_context = _make_tool_context(state)

        mock_client = MagicMock()
        with patch.object(module, "httpx") as mock_httpx:
            mock_httpx.Client.return_value.__enter__.return_value = mock_client
            module.refresh_if_expiring(tool_context)

        mock_client.post.assert_not_called()

    def test_no_op_when_no_refresh_token(self) -> None:
        """Without a refresh token, the helper cannot mint a new access token."""
        from app.services import google_workspace_token_refresh as module

        state: dict = {
            "user_id": "user-1",
            "google_provider_token": "old-access",
            "google_refresh_token": None,
            "google_token_expires_at": _iso_now_plus(60),
        }
        tool_context = _make_tool_context(state)

        mock_client = MagicMock()
        with patch.object(module, "httpx") as mock_httpx:
            mock_httpx.Client.return_value.__enter__.return_value = mock_client
            module.refresh_if_expiring(tool_context)

        mock_client.post.assert_not_called()

    def test_no_op_when_env_unconfigured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without GOOGLE_WORKSPACE_CLIENT_ID/SECRET, refresh cannot be attempted."""
        from app.services import google_workspace_token_refresh as module

        monkeypatch.delenv("GOOGLE_WORKSPACE_CLIENT_ID", raising=False)
        state: dict = {
            "user_id": "user-1",
            "google_provider_token": "old-access",
            "google_refresh_token": "rt-1",
            "google_token_expires_at": _iso_now_plus(60),
        }
        tool_context = _make_tool_context(state)

        mock_client = MagicMock()
        with patch.object(module, "httpx") as mock_httpx:
            mock_httpx.Client.return_value.__enter__.return_value = mock_client
            module.refresh_if_expiring(tool_context)

        mock_client.post.assert_not_called()

    def test_refresh_token_rotation_fallback(self) -> None:
        """Google may omit refresh_token in the response; we keep the old one."""
        from app.services import google_workspace_token_refresh as module

        state: dict = {
            "user_id": "user-1",
            "google_provider_token": "old-access",
            "google_refresh_token": "rt-1",
            "google_token_expires_at": _iso_now_plus(60),
        }
        tool_context = _make_tool_context(state)

        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {
            "access_token": "new-access",
            "expires_in": 3600,
            # NOTE: no "refresh_token" field in response
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response

        mock_service = MagicMock()
        mock_service.sync_credentials = MagicMock(return_value=True)

        with (
            patch.object(module, "httpx") as mock_httpx,
            patch.object(
                module, "get_google_workspace_auth_service", return_value=mock_service
            ),
        ):
            mock_httpx.Client.return_value.__enter__.return_value = mock_client
            mock_httpx.RequestError = httpx.RequestError
            module.refresh_if_expiring(tool_context)

        assert state["google_refresh_token"] == "rt-1"
        assert mock_service.sync_credentials.call_args.kwargs["refresh_token"] == "rt-1"

    def test_refresh_failure_is_best_effort(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A network error during refresh must NOT bubble up; state unchanged."""
        from app.services import google_workspace_token_refresh as module

        state: dict = {
            "user_id": "user-1",
            "google_provider_token": "old-access",
            "google_refresh_token": "rt-1",
            "google_token_expires_at": _iso_now_plus(60),
        }
        original_state = dict(state)
        tool_context = _make_tool_context(state)

        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.RequestError("network down")

        with (
            patch.object(module, "httpx") as mock_httpx,
            caplog.at_level(logging.WARNING),
        ):
            mock_httpx.Client.return_value.__enter__.return_value = mock_client
            mock_httpx.RequestError = httpx.RequestError
            # MUST NOT raise
            module.refresh_if_expiring(tool_context)

        assert state == original_state
        warning_messages = " | ".join(
            record.message for record in caplog.records if record.levelno >= logging.WARNING
        )
        assert "refresh_if_expiring" in warning_messages or "token refresh failed" in warning_messages
