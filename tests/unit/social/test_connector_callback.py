# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Pinterest OAuth callback tests (Plan 108-02 / HYGIENE-02).

Pinterest's OAuth 2.0 token endpoint is RFC 6749-strict: it requires HTTP
Basic auth (``Authorization: Basic base64(client_id:client_secret)``) and
rejects body-encoded ``client_id``/``client_secret`` fields. Pinterest's
token response also lacks a ``user_id`` field, so the callback must make
a follow-up ``GET /v5/user_account`` call to capture ``platform_username``.

These tests assert:

1. The Pinterest authorization URL points at ``pinterest.com/oauth/`` with
   the right scopes.
2. The token POST sends Basic auth via the httpx ``auth=`` tuple kwarg
   and does NOT include ``client_id``/``client_secret`` in the body.
3. The follow-up GET to ``/v5/user_account`` captures ``username``.
4. A 5xx from ``/v5/user_account`` is best-effort -- the connection
   still succeeds.
5. A 4xx from the token endpoint surfaces a structured error.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar
from unittest.mock import patch

import pytest

from tests.unit.social.conftest import FakeClient, make_connector


class _MockResponse:
    def __init__(
        self, payload: dict[str, Any], status_code: int = 200, text: str = ""
    ):
        self._payload = payload
        self.status_code = status_code
        self.text = text or ""

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            request = httpx.Request("GET", "https://example.invalid/")
            response = httpx.Response(
                self.status_code,
                text=self.text or str(self._payload),
                request=request,
            )
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}", request=request, response=response
            )


class _MockAsyncClient:
    """FIFO-replay mock for ``httpx.AsyncClient`` POST + GET calls.

    Records every call so tests can assert kwargs (auth tuple, body,
    headers, URL).
    """

    responses: ClassVar[list[tuple[str, dict[str, Any], int]]] = []
    calls: ClassVar[list[tuple[str, dict[str, Any]]]] = []

    def __init__(self, *_args: Any, **_kwargs: Any):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args: Any):
        return False

    def _pop(self) -> tuple[str, dict[str, Any], int]:
        if not _MockAsyncClient.responses:
            raise AssertionError("Mock httpx ran out of queued responses")
        return _MockAsyncClient.responses.pop(0)

    async def post(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        _MockAsyncClient.calls.append(
            ("POST", {"url": url, "data": data, **kwargs})
        )
        kind, payload, status = self._pop()
        assert kind == "post", (
            f"Expected POST next; got queued '{kind}' for {url}"
        )
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
        _MockAsyncClient.calls.append(
            ("GET", {"url": url, "headers": headers, "params": params})
        )
        kind, payload, status = self._pop()
        assert kind == "get", (
            f"Expected GET next; got queued '{kind}' for {url}"
        )
        if status >= 400:
            return _MockResponse(payload, status_code=status, text=str(payload))
        return _MockResponse(payload, status_code=status)


def _seed_pkce(
    client: FakeClient, state: str, platform: str, verifier: str
) -> None:
    """Seed an unexpired PKCE row so ``_pop_pkce_verifier`` succeeds."""
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    client.pkce_states[state] = {
        "state": state,
        "user_id": state.split(":")[0],
        "platform": platform,
        "code_verifier": f"enc:{verifier}",
        "expires_at": expires_at.isoformat(),
    }


def _set_pinterest_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PINTEREST_CLIENT_ID", "test-pin-id")
    monkeypatch.setenv("PINTEREST_CLIENT_SECRET", "test-pin-secret")


_TOKEN_RESPONSE: dict[str, Any] = {
    "access_token": "AT-PIN",
    "refresh_token": "RT-PIN",
    "expires_in": 2592000,
    "token_type": "bearer",
    "scope": "boards:read pins:write user_accounts:read",
}


def _reset_mock() -> None:
    _MockAsyncClient.responses = []
    _MockAsyncClient.calls = []


# ---------------------------------------------------------------------------
# 1. Authorization URL
# ---------------------------------------------------------------------------


def test_pinterest_authorization_url_uses_pinterest_dot_com(
    monkeypatch: pytest.MonkeyPatch,
):
    _set_pinterest_env(monkeypatch)
    client = FakeClient()
    connector = make_connector(client)

    result = connector.get_authorization_url(
        "pinterest", "user-1", "https://example.com/cb"
    )

    assert "authorization_url" in result, result
    url = result["authorization_url"]
    assert url.startswith("https://www.pinterest.com/oauth/?"), url
    assert "client_id=test-pin-id" in url
    # urlencode default quote_plus encodes spaces as '+' but leaves ':' alone
    # Either form is acceptable; we just verify all 3 scopes are present.
    assert "boards" in url and "read" in url
    assert "pins" in url and "write" in url
    assert "user_accounts" in url


# ---------------------------------------------------------------------------
# 2. Basic auth header on token exchange
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pinterest_callback_uses_basic_auth_header(
    monkeypatch: pytest.MonkeyPatch,
):
    _set_pinterest_env(monkeypatch)
    client = FakeClient()
    connector = make_connector(client)
    state = "user-9:abc"
    _seed_pkce(client, state, "pinterest", "ver-9")

    _reset_mock()
    _MockAsyncClient.responses = [
        ("post", _TOKEN_RESPONSE, 200),
        ("get", {"username": "alice_pins", "account_type": "BUSINESS"}, 200),
    ]

    with (
        patch("app.social.connector.httpx.AsyncClient", _MockAsyncClient),
        patch(
            "app.social.connector.encrypt_secret",
            side_effect=lambda v: f"enc:{v}",
        ),
        patch(
            "app.social.connector.decrypt_secret",
            side_effect=lambda v: (
                (v or "").removeprefix("enc:") if isinstance(v, str) else v
            ),
        ),
    ):
        result = await connector.handle_callback(
            "pinterest", "CODE-X", state, "https://example.com/cb"
        )

    assert result.get("success") is True, result

    # First call must be the token POST.
    assert _MockAsyncClient.calls[0][0] == "POST"
    post_kwargs = _MockAsyncClient.calls[0][1]
    assert post_kwargs["url"] == "https://api.pinterest.com/v5/oauth/token"

    # auth tuple (httpx Basic-auth helper) must be set.
    assert post_kwargs.get("auth") == ("test-pin-id", "test-pin-secret"), (
        post_kwargs
    )

    # Body MUST NOT contain client_id / client_secret -- Pinterest rejects.
    body = post_kwargs.get("data") or {}
    assert "client_id" not in body, body
    assert "client_secret" not in body, body

    # Body MUST contain the standard PKCE auth-code grant fields.
    assert body.get("grant_type") == "authorization_code"
    assert body.get("code") == "CODE-X"
    assert body.get("redirect_uri") == "https://example.com/cb"
    assert body.get("code_verifier") == "ver-9"


# ---------------------------------------------------------------------------
# 3. Follow-up /v5/user_account call captures username
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pinterest_callback_followup_user_account_call(
    monkeypatch: pytest.MonkeyPatch,
):
    _set_pinterest_env(monkeypatch)
    client = FakeClient()
    connector = make_connector(client)
    state = "user-9:abc"
    _seed_pkce(client, state, "pinterest", "ver-9")

    _reset_mock()
    _MockAsyncClient.responses = [
        ("post", _TOKEN_RESPONSE, 200),
        ("get", {"username": "alice_pins", "account_type": "BUSINESS"}, 200),
    ]

    with (
        patch("app.social.connector.httpx.AsyncClient", _MockAsyncClient),
        patch(
            "app.social.connector.encrypt_secret",
            side_effect=lambda v: f"enc:{v}",
        ),
        patch(
            "app.social.connector.decrypt_secret",
            side_effect=lambda v: (
                (v or "").removeprefix("enc:") if isinstance(v, str) else v
            ),
        ),
    ):
        result = await connector.handle_callback(
            "pinterest", "CODE-X", state, "https://example.com/cb"
        )

    assert result.get("success") is True

    # Two HTTP calls: token POST then /v5/user_account GET.
    methods = [c[0] for c in _MockAsyncClient.calls]
    assert methods == ["POST", "GET"], methods

    get_kwargs = _MockAsyncClient.calls[1][1]
    assert get_kwargs["url"] == "https://api.pinterest.com/v5/user_account"
    headers = get_kwargs.get("headers") or {}
    assert headers.get("Authorization") == "Bearer AT-PIN"

    # Upsert payload should carry the captured username; user_id is None.
    upsert = client.connected_account_upserts[-1]
    assert upsert["platform_username"] == "alice_pins"
    assert upsert["platform_user_id"] is None


# ---------------------------------------------------------------------------
# 4. /v5/user_account 5xx is non-fatal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pinterest_callback_user_account_call_failure_does_not_break(
    monkeypatch: pytest.MonkeyPatch,
):
    _set_pinterest_env(monkeypatch)
    client = FakeClient()
    connector = make_connector(client)
    state = "user-9:abc"
    _seed_pkce(client, state, "pinterest", "ver-9")

    _reset_mock()
    _MockAsyncClient.responses = [
        ("post", _TOKEN_RESPONSE, 200),
        ("get", {"error": "boom"}, 500),
    ]

    with (
        patch("app.social.connector.httpx.AsyncClient", _MockAsyncClient),
        patch(
            "app.social.connector.encrypt_secret",
            side_effect=lambda v: f"enc:{v}",
        ),
        patch(
            "app.social.connector.decrypt_secret",
            side_effect=lambda v: (
                (v or "").removeprefix("enc:") if isinstance(v, str) else v
            ),
        ),
    ):
        result = await connector.handle_callback(
            "pinterest", "CODE-X", state, "https://example.com/cb"
        )

    # Connection still succeeds even if profile follow-up fails.
    assert result.get("success") is True, result
    upsert = client.connected_account_upserts[-1]
    assert upsert["platform_username"] is None
    assert upsert["platform_user_id"] is None


# ---------------------------------------------------------------------------
# 5. Token-endpoint 4xx surfaces an error and skips the follow-up GET
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pinterest_callback_token_exchange_4xx_returns_error(
    monkeypatch: pytest.MonkeyPatch,
):
    _set_pinterest_env(monkeypatch)
    client = FakeClient()
    connector = make_connector(client)
    state = "user-9:abc"
    _seed_pkce(client, state, "pinterest", "ver-9")

    _reset_mock()
    _MockAsyncClient.responses = [
        ("post", {"error": "invalid_client"}, 401),
    ]

    with (
        patch("app.social.connector.httpx.AsyncClient", _MockAsyncClient),
        patch(
            "app.social.connector.encrypt_secret",
            side_effect=lambda v: f"enc:{v}",
        ),
        patch(
            "app.social.connector.decrypt_secret",
            side_effect=lambda v: (
                (v or "").removeprefix("enc:") if isinstance(v, str) else v
            ),
        ),
    ):
        result = await connector.handle_callback(
            "pinterest", "CODE-X", state, "https://example.com/cb"
        )

    assert "error" in result, result
    assert "Token exchange failed" in result["error"], result

    # Only the token POST was issued -- no follow-up.
    methods = [c[0] for c in _MockAsyncClient.calls]
    assert methods == ["POST"], methods
    # No connected_account row was written.
    assert client.connected_account_upserts == []
