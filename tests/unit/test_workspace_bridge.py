# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for the Google Workspace credential bridge (Phase 102, WORKSPACE-03).

Patch convention: ``app.agents.context_extractor.get_google_workspace_auth_service``
is patched at the consumer module — Task 2 imports it at module scope so this
patch target is the canonical site. Tests will fail with ImportError until
Task 2 lands the helper, sentinel, and module-scope import.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch


def _make_callback_context(state: dict | None = None) -> MagicMock:
    """Return a fake CallbackContext with a mutable state dict."""
    ctx = MagicMock(spec_set=["state"])
    ctx.state = state if state is not None else {}
    return ctx


class TestGoogleWorkspaceBridge:
    """Tests for ``_try_load_google_workspace_credentials`` in context_extractor."""

    def test_anonymous_user_short_circuits(self) -> None:
        """When user_id resolves to 'anonymous', the service is never called."""
        from app.agents.context_extractor import (
            _GOOGLE_WORKSPACE_LOADED_KEY,
            _try_load_google_workspace_credentials,
        )

        ctx = _make_callback_context({"user_id": "anonymous"})
        with patch(
            "app.agents.context_extractor.get_google_workspace_auth_service"
        ) as mock_factory:
            _try_load_google_workspace_credentials(ctx)
            mock_factory.assert_not_called()

        assert "google_provider_token" not in ctx.state
        assert ctx.state.get(_GOOGLE_WORKSPACE_LOADED_KEY) is True

    def test_no_user_id_short_circuits(self) -> None:
        """Missing user_id resolves to 'anonymous' via _get_callback_user_id."""
        from app.agents.context_extractor import (
            _GOOGLE_WORKSPACE_LOADED_KEY,
            _try_load_google_workspace_credentials,
        )

        ctx = _make_callback_context({})
        with patch(
            "app.agents.context_extractor.get_google_workspace_auth_service"
        ) as mock_factory:
            _try_load_google_workspace_credentials(ctx)
            mock_factory.assert_not_called()

        assert "google_provider_token" not in ctx.state
        assert ctx.state.get(_GOOGLE_WORKSPACE_LOADED_KEY) is True

    def test_no_credentials_returns_silently(self) -> None:
        """When resolve_credentials returns None, state is untouched but sentinel sets."""
        from app.agents.context_extractor import (
            _GOOGLE_WORKSPACE_LOADED_KEY,
            _try_load_google_workspace_credentials,
        )

        ctx = _make_callback_context({"user_id": "user-1"})
        service = MagicMock()
        service.resolve_credentials.return_value = None
        with patch(
            "app.agents.context_extractor.get_google_workspace_auth_service",
            return_value=service,
        ):
            _try_load_google_workspace_credentials(ctx)

        service.resolve_credentials.assert_called_once_with(
            "user-1", allow_legacy_fallback=True
        )
        assert "google_provider_token" not in ctx.state
        assert "google_refresh_token" not in ctx.state
        assert ctx.state.get(_GOOGLE_WORKSPACE_LOADED_KEY) is True

    def test_credentials_injected(self) -> None:
        """A successful resolve writes access_token, refresh_token, expires_at."""
        from app.agents.context_extractor import (
            _GOOGLE_WORKSPACE_LOADED_KEY,
            _try_load_google_workspace_credentials,
        )

        ctx = _make_callback_context({"user_id": "user-1"})
        service = MagicMock()
        service.resolve_credentials.return_value = {
            "access_token": "ya29.test",
            "refresh_token": "1//test",
            "expires_at": "2026-05-08T12:00:00+00:00",
            "source": "integration_credentials",
        }
        with patch(
            "app.agents.context_extractor.get_google_workspace_auth_service",
            return_value=service,
        ):
            _try_load_google_workspace_credentials(ctx)

        service.resolve_credentials.assert_called_once_with(
            "user-1", allow_legacy_fallback=True
        )
        assert ctx.state["google_provider_token"] == "ya29.test"
        assert ctx.state["google_refresh_token"] == "1//test"
        assert ctx.state["google_token_expires_at"] == "2026-05-08T12:00:00+00:00"
        assert ctx.state.get(_GOOGLE_WORKSPACE_LOADED_KEY) is True

    def test_sentinel_makes_call_idempotent(self) -> None:
        """If sentinel is already set, the service factory is never invoked."""
        from app.agents.context_extractor import (
            _GOOGLE_WORKSPACE_LOADED_KEY,
            _try_load_google_workspace_credentials,
        )

        ctx = _make_callback_context(
            {"user_id": "user-1", _GOOGLE_WORKSPACE_LOADED_KEY: True}
        )
        with patch(
            "app.agents.context_extractor.get_google_workspace_auth_service"
        ) as mock_factory:
            _try_load_google_workspace_credentials(ctx)
            mock_factory.assert_not_called()

        assert "google_provider_token" not in ctx.state

    def test_resolve_exception_is_swallowed(
        self, caplog: logging.LogCaptureFixture
    ) -> None:
        """A RuntimeError from resolve_credentials must not propagate."""
        from app.agents.context_extractor import (
            _GOOGLE_WORKSPACE_LOADED_KEY,
            _try_load_google_workspace_credentials,
        )

        ctx = _make_callback_context({"user_id": "user-1"})
        service = MagicMock()
        service.resolve_credentials.side_effect = RuntimeError("supabase down")
        caplog.set_level(logging.DEBUG, logger="app.agents.context_extractor")

        with patch(
            "app.agents.context_extractor.get_google_workspace_auth_service",
            return_value=service,
        ):
            _try_load_google_workspace_credentials(ctx)  # must not raise

        assert "google_provider_token" not in ctx.state
        assert ctx.state.get(_GOOGLE_WORKSPACE_LOADED_KEY) is True
        # Debug log records the skip reason
        debug_records = [
            r for r in caplog.records if r.levelno == logging.DEBUG
        ]
        assert any(
            "GoogleWorkspace" in r.getMessage()
            and "Cred injection skipped" in r.getMessage()
            for r in debug_records
        )
