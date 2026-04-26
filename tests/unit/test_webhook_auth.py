"""Tests for webhook signing-secret enforcement on Linear and Asana handlers.

Security: Both handlers must fail-closed (HTTP 500) when signing secrets are
absent so that unauthenticated payloads are never processed.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

import app.routers.webhooks as webhooks_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_minimal_app():
    """Build a minimal FastAPI app that mounts only the webhook router.

    The router already defines prefix="/webhooks" internally, so we include
    it without adding an extra prefix.
    """
    from fastapi import FastAPI

    mini = FastAPI()
    mini.include_router(webhooks_module.router)
    return mini


# ---------------------------------------------------------------------------
# Linear webhook tests
# ---------------------------------------------------------------------------


class TestLinearWebhookSecretEnforcement:
    """Linear handler returns 500 when LINEAR_WEBHOOK_SECRET is absent."""

    def test_linear_returns_500_when_secret_missing(self, monkeypatch):
        """HTTP 500 when LINEAR_WEBHOOK_SECRET is not configured."""
        monkeypatch.delenv("LINEAR_WEBHOOK_SECRET", raising=False)
        monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", "")

        app = _build_minimal_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/webhooks/linear",
                json={"type": "Issue", "action": "create", "data": {}},
                headers={"Linear-Signature": "some-sig"},
            )

        assert response.status_code == 500
        assert "secret" in response.json().get("detail", "").lower()

    def test_linear_returns_500_when_secret_unset(self, monkeypatch):
        """HTTP 500 when LINEAR_WEBHOOK_SECRET env var is completely absent."""
        monkeypatch.delenv("LINEAR_WEBHOOK_SECRET", raising=False)

        app = _build_minimal_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/webhooks/linear",
                json={"type": "Issue", "action": "create", "data": {}},
            )

        assert response.status_code == 500

    def test_linear_proceeds_to_verify_when_secret_set(self, monkeypatch):
        """When LINEAR_WEBHOOK_SECRET is set the handler proceeds to HMAC verification."""
        monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", "test-secret-value")

        app = _build_minimal_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            # Send a request with an intentionally wrong signature — we expect
            # 403 (invalid signature) NOT 500, which proves the secret-check
            # passed and signature verification ran.
            response = client.post(
                "/webhooks/linear",
                json={"type": "Issue", "action": "create", "data": {}},
                headers={"Linear-Signature": "wrong-signature"},
            )

        # 403 means we got past the secret-missing guard and reached HMAC verification
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Asana webhook tests
# ---------------------------------------------------------------------------


class TestAsanaWebhookSecretEnforcement:
    """Asana handler returns 500 when hook secret is absent."""

    @pytest.mark.asyncio
    async def test_asana_returns_500_when_hook_secret_empty(self, monkeypatch):
        """HTTP 500 when _get_asana_hook_secret returns an empty string."""
        monkeypatch.delenv("ASANA_WEBHOOK_SECRET", raising=False)

        app = _build_minimal_app()
        with patch(
            "app.routers.webhooks._get_asana_hook_secret",
            new=AsyncMock(return_value=""),
        ):
            with TestClient(app, raise_server_exceptions=False) as client:
                # No X-Hook-Secret header so this is treated as an events request
                response = client.post(
                    "/webhooks/asana",
                    json={"events": [{"action": "changed", "resource": {}}]},
                )

        assert response.status_code == 500
        assert "secret" in response.json().get("detail", "").lower()

    @pytest.mark.asyncio
    async def test_asana_proceeds_to_verify_when_hook_secret_set(self, monkeypatch):
        """When hook secret is non-empty the handler proceeds to HMAC verification."""
        secret = "valid-asana-secret"

        app = _build_minimal_app()
        with patch(
            "app.routers.webhooks._get_asana_hook_secret",
            new=AsyncMock(return_value=secret),
        ):
            with TestClient(app, raise_server_exceptions=False) as client:
                # Wrong signature — expect 403 (HMAC ran) not 500 (secret missing)
                response = client.post(
                    "/webhooks/asana",
                    json={"events": []},
                    headers={"X-Hook-Signature": "wrong-signature"},
                )

        # 403 means we got past the secret-missing guard and reached HMAC verification
        assert response.status_code == 403
