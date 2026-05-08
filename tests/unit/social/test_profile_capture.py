# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Failing tests for AUTH-04 per-provider profile capture.

These tests assert that ``SocialConnector.handle_callback`` populates
``platform_user_id`` and ``platform_username`` in the upserted
``connected_accounts`` row for each of the 6 in-scope OAuth platforms,
and that profile-fetch failures do NOT abort the OAuth flow.

All seven tests fail today because ``handle_callback`` does not call any
profile endpoint and the upsert payload lacks both columns.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar
from unittest.mock import patch

import pytest

from tests.unit.social.conftest import FakeClient, make_connector

# ---------------------------------------------------------------------------
# Fake httpx.AsyncClient -- queue of responses, asserts call order.
# ---------------------------------------------------------------------------


class _MockResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200, text: str = ""):
        self._payload = payload
        self.status_code = status_code
        self.text = text or ""

    def json(self):
        return self._payload

    def raise_for_status(self):
        # httpx-style: raise on 4xx/5xx so connector code paths that call
        # raise_for_status (e.g., _fetch_facebook_pages) behave correctly.
        if self.status_code >= 400:
            import httpx

            request = httpx.Request("GET", "https://example.invalid/")
            response = httpx.Response(
                self.status_code, text=self.text or str(self._payload), request=request
            )
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}", request=request, response=response
            )


class _MockAsyncClient:
    """Replays a class-level FIFO of responses for ``post`` then ``get``."""

    responses: ClassVar[list[tuple[str, dict[str, Any], int]]] = []

    def __init__(self, *args: Any, **kwargs: Any):
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args: Any):
        return False

    def _pop(self) -> tuple[str, dict[str, Any], int]:
        if not _MockAsyncClient.responses:
            raise AssertionError("Mock httpx ran out of queued responses")
        return _MockAsyncClient.responses.pop(0)

    async def post(self, url: str, data: dict[str, Any] | None = None, **_kw: Any):
        self.calls.append(("POST", {"url": url, "data": data}))
        kind, payload, status = self._pop()
        assert kind == "post", f"Expected POST next; got queued '{kind}' for {url}"
        if status >= 400:
            return _MockResponse(payload, status_code=status, text=str(payload))
        return _MockResponse(payload, status_code=status)

    async def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
        **_kw: Any,
    ):
        self.calls.append(("GET", {"url": url, "headers": headers, "params": params}))
        kind, payload, status = self._pop()
        assert kind == "get", f"Expected GET next; got queued '{kind}' for {url}"
        if status >= 400:
            return _MockResponse(payload, status_code=status, text=str(payload))
        return _MockResponse(payload, status_code=status)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _seed_pkce(client: FakeClient, state: str, platform: str, verifier: str) -> None:
    """Seed an unexpired PKCE row so ``_pop_pkce_verifier`` succeeds."""
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    client.pkce_states[state] = {
        "state": state,
        "user_id": state.split(":")[0],
        "platform": platform,
        "code_verifier": f"enc:{verifier}",
        "expires_at": expires_at.isoformat(),
    }


_PLATFORM_ENV = {
    "linkedin": ("LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"),
    "twitter": ("TWITTER_CLIENT_ID", "TWITTER_CLIENT_SECRET"),
    "facebook": ("FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET"),
    "instagram": ("FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET"),
    "tiktok": ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET"),
    "youtube": ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"),
}


def _set_env(monkeypatch: pytest.MonkeyPatch, platform: str) -> None:
    cid, csec = _PLATFORM_ENV[platform]
    monkeypatch.setenv(cid, "id")
    monkeypatch.setenv(csec, "secret")


_TOKEN_RESPONSE: dict[str, Any] = {
    "access_token": "real-bearer",
    "refresh_token": "refresh-bearer",
    "expires_in": 3600,
}


async def _drive_callback(
    platform: str,
    profile_payload: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    *,
    profile_status: int = 200,
) -> tuple[dict[str, Any], FakeClient, list[tuple[str, dict[str, Any]]]]:
    """Run handle_callback once; return (result, client, recorded_calls)."""
    client = FakeClient()
    connector = make_connector(client)
    state = "user-1:abc"
    verifier = "v-plain"
    _seed_pkce(client, state, platform, verifier)
    _set_env(monkeypatch, platform)

    _MockAsyncClient.responses = [
        ("post", _TOKEN_RESPONSE, 200),
        ("get", profile_payload, profile_status),
    ]

    captured_calls: list[tuple[str, dict[str, Any]]] = []

    original_init = _MockAsyncClient.__init__

    def _record_init(self, *a, **kw):
        original_init(self, *a, **kw)
        # Share the per-instance call log with the test via closure.
        captured_calls.append(("__init__", {}))
        self.calls = captured_calls

    with (
        patch("app.social.connector.httpx.AsyncClient", _MockAsyncClient),
        patch.object(_MockAsyncClient, "__init__", _record_init),
        patch("app.social.connector.encrypt_secret", side_effect=lambda v: f"enc:{v}"),
        patch(
            "app.social.connector.decrypt_secret",
            side_effect=lambda v: (
                (v or "").removeprefix("enc:") if isinstance(v, str) else v
            ),
        ),
    ):
        result = await connector.handle_callback(
            platform, "code-xyz", state, "https://app.test/cb"
        )

    return result, client, captured_calls


# ---------------------------------------------------------------------------
# Per-provider tests (six platforms in scope)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_linkedin_profile_capture(monkeypatch: pytest.MonkeyPatch):
    profile = {
        "sub": "li-12345",
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
    }
    result, client, _calls = await _drive_callback("linkedin", profile, monkeypatch)

    assert result.get("success") is True
    assert client.connected_account_upserts, "handle_callback never upserted"
    upsert = client.connected_account_upserts[-1]
    assert upsert["platform_user_id"] == "li-12345"
    assert upsert["platform_username"] == "Test User"


@pytest.mark.asyncio
async def test_twitter_profile_capture(monkeypatch: pytest.MonkeyPatch):
    profile = {"data": {"id": "tw-67890", "username": "testhandle", "name": "Test"}}
    result, client, _calls = await _drive_callback("twitter", profile, monkeypatch)

    assert result.get("success") is True
    upsert = client.connected_account_upserts[-1]
    assert upsert["platform_user_id"] == "tw-67890"
    assert upsert["platform_username"] == "testhandle"


@pytest.mark.asyncio
async def test_facebook_profile_capture(monkeypatch: pytest.MonkeyPatch):
    """Facebook OAuth callback writes the selected Page id/name (not the
    User id/name) thanks to Plan 107-02's Page-token capture step.

    Driver enqueues an extra GET response for /me/accounts so the
    Facebook branch in handle_callback can resolve a Page. The
    /me Profile fetch (User id/name) still happens in
    _fetch_platform_profile but its values are overridden by the
    Page-token branch -- the row stores Page id + Page name.
    """
    profile = {"id": "fb-111", "name": "Test FB"}
    pages_payload = {
        "data": [
            {"id": "page-fb-1", "name": "Test FB Page", "access_token": "pt-1"},
        ]
    }
    client = FakeClient()
    connector = make_connector(client)
    state = "user-1:abc"
    verifier = "v-plain"
    _seed_pkce(client, state, "facebook", verifier)
    _set_env(monkeypatch, "facebook")

    # FIFO: token POST -> /me GET -> /me/accounts GET (added by 107-02)
    _MockAsyncClient.responses = [
        ("post", _TOKEN_RESPONSE, 200),
        ("get", profile, 200),
        ("get", pages_payload, 200),
    ]

    with (
        patch("app.social.connector.httpx.AsyncClient", _MockAsyncClient),
        patch("app.social.connector.encrypt_secret", side_effect=lambda v: f"enc:{v}"),
        patch(
            "app.social.connector.decrypt_secret",
            side_effect=lambda v: (
                (v or "").removeprefix("enc:") if isinstance(v, str) else v
            ),
        ),
    ):
        result = await connector.handle_callback(
            "facebook", "code-xyz", state, "https://app.test/cb"
        )

    assert result.get("success") is True
    upsert = client.connected_account_upserts[-1]
    # platform_user_id stores the PAGE id (D-5 locked decision), not the
    # User id from /me. Page name + token come from /me/accounts.
    assert upsert["platform_user_id"] == "page-fb-1"
    assert upsert["platform_username"] == "Test FB Page"
    assert upsert["access_token"] == "enc:pt-1"
    assert upsert["metadata"]["selected_page_id"] == "page-fb-1"


@pytest.mark.asyncio
async def test_instagram_profile_capture(monkeypatch: pytest.MonkeyPatch):
    profile = {
        "data": [
            {
                "id": "page-1",
                "instagram_business_account": {
                    "id": "ig-222",
                    "username": "testig",
                },
            }
        ]
    }
    result, client, _calls = await _drive_callback("instagram", profile, monkeypatch)

    assert result.get("success") is True
    upsert = client.connected_account_upserts[-1]
    assert upsert["platform_user_id"] == "ig-222"
    assert upsert["platform_username"] == "testig"


@pytest.mark.asyncio
async def test_tiktok_profile_capture(monkeypatch: pytest.MonkeyPatch):
    profile = {"data": {"user": {"open_id": "tt-333"}}}
    result, client, _calls = await _drive_callback("tiktok", profile, monkeypatch)

    assert result.get("success") is True
    upsert = client.connected_account_upserts[-1]
    assert upsert["platform_user_id"] == "tt-333"
    # username requires user.info.profile scope (Phase 108)
    assert upsert["platform_username"] is None


@pytest.mark.asyncio
async def test_youtube_profile_capture(monkeypatch: pytest.MonkeyPatch):
    profile = {"items": [{"id": "yt-444", "snippet": {"title": "Test Channel"}}]}
    result, client, _calls = await _drive_callback("youtube", profile, monkeypatch)

    assert result.get("success") is True
    upsert = client.connected_account_upserts[-1]
    assert upsert["platform_user_id"] == "yt-444"
    assert upsert["platform_username"] == "Test Channel"


# ---------------------------------------------------------------------------
# Failure-tolerance test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_profile_capture_failure_does_not_abort_callback(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    """A 5xx from the profile endpoint must not break the OAuth flow."""
    caplog.set_level(logging.WARNING, logger="app.social.connector")

    result, client, _calls = await _drive_callback(
        "linkedin",
        profile_payload={"error": "server error"},
        monkeypatch=monkeypatch,
        profile_status=500,
    )

    assert result.get("success") is True, (
        "Profile-fetch 500 must not abort the OAuth flow"
    )
    upsert = client.connected_account_upserts[-1]
    assert upsert["platform_user_id"] is None
    assert upsert["platform_username"] is None

    warnings = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("Profile capture failed" in m and "linkedin" in m for m in warnings), (
        f"Expected a WARNING with 'Profile capture failed' and 'linkedin'; got {warnings!r}"
    )
