# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the Facebook Page-token capture step in handle_callback.

Covers POST-09 SC-1 prerequisite (Plan 107-02): the OAuth callback must
exchange the User token for a per-Page access token (via
``GET /v23.0/me/accounts``) and store the Page ID + Page-scoped access
token in ``connected_accounts`` so Plan 107-01's three-phase video upload
can resolve them.

Four tests cover:
1. Single-Page success path -- payload stores Page id/name/Page-token,
   and stashes the User token in metadata.user_token_enc.
2. Multi-Page auto-select -- first Page wins; available_pages list of
   {id, name} stashed in metadata for future selection UI (Phase 108).
3. Zero Pages -- structured ``facebook_no_pages_found`` error and no
   row written.
4. ``/me/accounts`` HTTP failure -- structured
   ``facebook_pages_fetch_failed`` error and no row written.

Implementation note: ``respx`` is NOT a project dependency. We reuse the
``_MockAsyncClient`` FIFO pattern from ``test_profile_capture.py`` and
patch ``app.social.connector.httpx.AsyncClient`` plus the
``encrypt_secret`` / ``decrypt_secret`` helpers.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar
from unittest.mock import patch

import pytest

from tests.unit.social.conftest import FakeClient, make_connector


# ---------------------------------------------------------------------------
# Fake httpx.AsyncClient (mirrors the one in test_profile_capture.py).
# ---------------------------------------------------------------------------


class _MockResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200, text: str = ""):
        self._payload = payload
        self.status_code = status_code
        self.text = text or str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        # httpx-style: raise on 4xx/5xx so the connector's
        # except httpx.HTTPStatusError block fires.
        if self.status_code >= 400:
            import httpx

            request = httpx.Request(
                "GET", "https://graph.facebook.com/v23.0/me/accounts"
            )
            response = httpx.Response(self.status_code, text=self.text, request=request)
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}", request=request, response=response
            )


class _MockAsyncClient:
    """Replays a class-level FIFO of responses for ``post`` then ``get`` calls."""

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


_TOKEN_RESPONSE: dict[str, Any] = {
    "access_token": "USER_TOKEN",
    "refresh_token": "USER_REFRESH",
    "expires_in": 3600,
}

# Profile (/v18.0/me) response used by the existing
# _fetch_platform_profile path. The Facebook branch ignores its values
# (overridden by Page data) but the call still happens, so we must
# queue a response.
_PROFILE_RESPONSE: dict[str, Any] = {"id": "USER_ID", "name": "User Name"}


async def _drive_facebook_callback(
    pages_payload: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    *,
    pages_status: int = 200,
) -> tuple[dict[str, Any], FakeClient]:
    """Run handle_callback for facebook with the given /me/accounts payload."""
    client = FakeClient()
    connector = make_connector(client)
    state = "user-1:abc"
    verifier = "v-plain"
    _seed_pkce(client, state, "facebook", verifier)
    monkeypatch.setenv("FACEBOOK_APP_ID", "id")
    monkeypatch.setenv("FACEBOOK_APP_SECRET", "secret")

    # FIFO: token exchange POST -> profile GET (/me) -> Page list GET (/me/accounts)
    _MockAsyncClient.responses = [
        ("post", _TOKEN_RESPONSE, 200),
        ("get", _PROFILE_RESPONSE, 200),
        ("get", pages_payload, pages_status),
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

    return result, client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_callback_writes_page_id_for_single_page_user(
    monkeypatch: pytest.MonkeyPatch,
):
    """Happy path: one Page returned -> row stores Page id + Page token."""
    pages_payload = {
        "data": [
            {"id": "PAGE_1", "name": "My Page", "access_token": "PAGE_TOKEN_1"},
        ]
    }
    result, client = await _drive_facebook_callback(pages_payload, monkeypatch)

    assert result.get("success") is True
    assert result["page_id"] == "PAGE_1"
    assert result["page_name"] == "My Page"
    assert result["available_pages"] == [{"id": "PAGE_1", "name": "My Page"}]

    assert len(client.connected_account_upserts) == 1
    upsert = client.connected_account_upserts[-1]
    assert upsert["platform"] == "facebook"
    assert upsert["platform_user_id"] == "PAGE_1"
    assert upsert["platform_username"] == "My Page"
    # access_token stores the encrypted PAGE token, not the User token.
    assert upsert["access_token"] == "enc:PAGE_TOKEN_1"
    metadata = upsert["metadata"]
    # User token is preserved for future Page re-listing (Phase 108).
    assert metadata["user_token_enc"] == "enc:USER_TOKEN"
    assert metadata["available_pages"] == [{"id": "PAGE_1", "name": "My Page"}]
    assert metadata["selected_page_id"] == "PAGE_1"
    assert metadata["selected_page_name"] == "My Page"


@pytest.mark.asyncio
async def test_callback_auto_selects_first_page_for_multi_page_user(
    monkeypatch: pytest.MonkeyPatch,
):
    """Multi-Page: auto-select first; stash full list in metadata."""
    pages_payload = {
        "data": [
            {"id": "PAGE_A", "name": "Page A", "access_token": "PT_A"},
            {"id": "PAGE_B", "name": "Page B", "access_token": "PT_B"},
            {"id": "PAGE_C", "name": "Page C", "access_token": "PT_C"},
        ]
    }
    result, client = await _drive_facebook_callback(pages_payload, monkeypatch)

    assert result.get("success") is True
    assert result["page_id"] == "PAGE_A"  # first auto-selected
    assert len(result["available_pages"]) == 3
    assert {p["id"] for p in result["available_pages"]} == {
        "PAGE_A",
        "PAGE_B",
        "PAGE_C",
    }
    assert "3 Pages available" in result["message"]

    upsert = client.connected_account_upserts[-1]
    assert upsert["platform_user_id"] == "PAGE_A"
    assert upsert["access_token"] == "enc:PT_A"
    metadata = upsert["metadata"]
    assert len(metadata["available_pages"]) == 3
    assert metadata["selected_page_id"] == "PAGE_A"


@pytest.mark.asyncio
async def test_callback_returns_error_when_user_has_no_pages(
    monkeypatch: pytest.MonkeyPatch,
):
    """Zero Pages -> structured error, no row written."""
    pages_payload: dict[str, Any] = {"data": []}
    result, client = await _drive_facebook_callback(pages_payload, monkeypatch)

    assert result.get("error") == "facebook_no_pages_found"
    assert "detail" in result
    assert client.connected_account_upserts == [], "no row should be written"


@pytest.mark.asyncio
async def test_callback_returns_error_when_me_accounts_fails_http(
    monkeypatch: pytest.MonkeyPatch,
):
    """HTTP 400 from /me/accounts -> structured error, no row written."""
    pages_payload = {"error": {"message": "Invalid OAuth access token"}}
    result, client = await _drive_facebook_callback(
        pages_payload, monkeypatch, pages_status=400
    )

    assert result.get("error") == "facebook_pages_fetch_failed"
    assert result["detail"].startswith("HTTP 400:")
    assert client.connected_account_upserts == [], "no row should be written"
