"""Tests for LinkedIn webhook signature realignment (POST-03, Phase 103-02).

LinkedIn signs every webhook payload with HMAC-SHA256 of the raw body, prefixed
with ``hmacsha256=``, in the ``X-LI-Signature`` header — using the application's
``LINKEDIN_CLIENT_SECRET`` (NOT a separate webhook secret).

These tests pin the three concrete defects fixed in Phase 103-02:

1. Header name was ``X-LinkedIn-Signature`` instead of ``X-LI-Signature``
2. Secret env var was ``LINKEDIN_WEBHOOK_SECRET`` instead of ``LINKEDIN_CLIENT_SECRET``
3. The mandatory ``hmacsha256=`` prefix was never stripped before HMAC compare

Audit-mandated status codes:
- Invalid / missing signature: HTTP 401 (was 403)
- Missing ``LINKEDIN_CLIENT_SECRET``: HTTP 500 (fail-closed, matches Linear/Asana/Stripe)

The GET challenge handler at ``app/routers/webhooks.py:linkedin_webhook_verification``
is already correct and is preserved by a regression test in this file.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.routers.webhooks as webhooks_module

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_app() -> FastAPI:
    """Build a minimal FastAPI app that mounts only the webhook router."""
    mini = FastAPI()
    mini.include_router(webhooks_module.router)
    return mini


def _sign(body_bytes: bytes, secret: str) -> str:
    """Compute the LinkedIn-style ``X-LI-Signature`` header value."""
    digest = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    return f"hmacsha256={digest}"


def _patch_router_helpers(monkeypatch) -> AsyncMock:
    """Stub out store_webhook_event + extractors so tests don't hit Supabase.

    Returns the AsyncMock bound to ``store_webhook_event`` so callers can
    assert call counts.
    """
    store_mock = AsyncMock(return_value={"id": "evt-1"})
    monkeypatch.setattr(
        "app.routers.webhooks.store_webhook_event",
        store_mock,
    )
    monkeypatch.setattr(
        "app.routers.webhooks.extract_event_type",
        lambda payload: "MEMBER_SOCIAL_ACTION",
    )
    monkeypatch.setattr(
        "app.routers.webhooks.extract_organization_id",
        lambda payload: None,
    )
    monkeypatch.setattr(
        "app.routers.webhooks.resolve_user_from_event",
        lambda payload: None,
    )
    return store_mock


_PAYLOAD = {"eventType": "MEMBER_SOCIAL_ACTION", "actor": "urn:li:person:abc"}
_PAYLOAD_BYTES = json.dumps(_PAYLOAD).encode("utf-8")


# ---------------------------------------------------------------------------
# Signature acceptance / rejection tests
# ---------------------------------------------------------------------------


def test_valid_signature_accepted_with_201_path(monkeypatch):
    """Valid X-LI-Signature with hmacsha256= prefix is accepted; event is stored."""
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "test-secret")
    store_mock = _patch_router_helpers(monkeypatch)

    sig = _sign(_PAYLOAD_BYTES, "test-secret")
    app = _build_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/webhooks/linkedin",
            content=_PAYLOAD_BYTES,
            headers={
                "X-LI-Signature": sig,
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body.get("event_id") == "evt-1"
    assert store_mock.await_count == 1


def test_invalid_signature_rejected_with_401(monkeypatch):
    """Invalid X-LI-Signature must return 401 (audit-mandated, was 403)."""
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "test-secret")
    store_mock = _patch_router_helpers(monkeypatch)

    app = _build_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/webhooks/linkedin",
            content=_PAYLOAD_BYTES,
            headers={
                "X-LI-Signature": "hmacsha256=deadbeef0000",
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 401
    assert store_mock.await_count == 0


def test_missing_signature_header_rejected_with_401(monkeypatch):
    """Missing X-LI-Signature header must return 401."""
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "test-secret")
    _patch_router_helpers(monkeypatch)

    app = _build_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/webhooks/linkedin",
            content=_PAYLOAD_BYTES,
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 401


def test_signature_without_hmacsha256_prefix_rejected(monkeypatch):
    """Bare hex digest (no hmacsha256= prefix) must be rejected with 401."""
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "test-secret")
    _patch_router_helpers(monkeypatch)

    bare_hex = hmac.new(b"test-secret", _PAYLOAD_BYTES, hashlib.sha256).hexdigest()

    app = _build_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/webhooks/linkedin",
            content=_PAYLOAD_BYTES,
            headers={
                "X-LI-Signature": bare_hex,
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 401


def test_old_X_LinkedIn_Signature_header_rejected(monkeypatch):
    """The deprecated X-LinkedIn-Signature header must NOT be accepted."""
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "test-secret")
    _patch_router_helpers(monkeypatch)

    sig = _sign(_PAYLOAD_BYTES, "test-secret")

    app = _build_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/webhooks/linkedin",
            content=_PAYLOAD_BYTES,
            headers={
                # Old header name — must be IGNORED by the new code path
                "X-LinkedIn-Signature": sig,
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 401


def test_missing_LINKEDIN_CLIENT_SECRET_returns_500(monkeypatch):
    """Missing LINKEDIN_CLIENT_SECRET must fail closed with HTTP 500."""
    monkeypatch.delenv("LINKEDIN_CLIENT_SECRET", raising=False)
    _patch_router_helpers(monkeypatch)

    app = _build_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/webhooks/linkedin",
            content=_PAYLOAD_BYTES,
            headers={
                "X-LI-Signature": "hmacsha256=anything",
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 500
    detail = response.json().get("detail", "")
    assert "secret" in detail.lower()


def test_LINKEDIN_WEBHOOK_SECRET_alone_does_not_verify(monkeypatch):
    """Legacy LINKEDIN_WEBHOOK_SECRET is unused — only LINKEDIN_CLIENT_SECRET works."""
    monkeypatch.delenv("LINKEDIN_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("LINKEDIN_WEBHOOK_SECRET", "test-secret")
    _patch_router_helpers(monkeypatch)

    sig = _sign(_PAYLOAD_BYTES, "test-secret")

    app = _build_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/webhooks/linkedin",
            content=_PAYLOAD_BYTES,
            headers={
                "X-LI-Signature": sig,
                "Content-Type": "application/json",
            },
        )

    # LINKEDIN_CLIENT_SECRET absent -> fail-closed 500, even though the
    # legacy var is set with the matching value.
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# Regression: GET challenge handler unchanged
# ---------------------------------------------------------------------------


def test_get_challenge_handler_still_works(monkeypatch):
    """GET /webhooks/linkedin?challengeCode=... must still echo signed challenge."""
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "test-secret")

    expected = hmac.new(b"test-secret", b"abc123", hashlib.sha256).hexdigest()

    app = _build_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/webhooks/linkedin",
            params={"challengeCode": "abc123"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["challengeCode"] == "abc123"
    assert body["challengeResponse"] == expected
