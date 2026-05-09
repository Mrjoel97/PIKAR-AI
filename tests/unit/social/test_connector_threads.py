# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Failing tests for HYGIENE-01 -- Threads OAuth + connector wiring.

Asserts:

1. ``get_authorization_url("threads", ...)`` produces a Threads-flavored
   authorization URL with the correct scopes and an S256 PKCE challenge.
2. ``get_authorization_url`` errors out cleanly when ``THREADS_APP_ID`` is
   unset, mirroring the existing missing-client-id error shape.
3. ``handle_callback("threads", ...)`` exchanges the auth code at
   ``graph.threads.net/oauth/access_token``, captures the ``user_id`` from
   the token response into ``connected_accounts.platform_user_id``, and
   upserts a Fernet-encrypted token row with ``status="active"``.
4. A token response missing ``user_id`` (e.g., legacy / partial response)
   stores ``None`` as ``platform_user_id`` and does NOT abort the flow --
   the column is nullable.
5. A 4xx token-exchange response surfaces a structured ``"Token exchange
   failed"`` error WITHOUT writing a row.
6. ``get_platform_user_id`` returns the captured value or ``None`` when
   no active row exists.

These tests fail today because ``PLATFORM_CONFIGS["threads"]`` does not
exist and ``handle_callback`` never reads ``tokens.get("user_id")``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar
from unittest.mock import patch

import pytest

from tests.unit.social.conftest import FakeClient, make_connector

# ---------------------------------------------------------------------------
# Mock httpx.AsyncClient -- queue of responses, records sent body for
# assertions.
# ---------------------------------------------------------------------------


class _MockResponse:
    def __init__(
        self, payload: dict[str, Any], status_code: int = 200, text: str = ""
    ):
        self._payload = payload
        self.status_code = status_code
        self.text = text or str(payload)

    def json(self):
        return self._payload


class _MockAsyncClient:
    """FIFO replay of ``post``/``get`` responses; records every call."""

    responses: ClassVar[list[tuple[str, dict[str, Any], int]]] = []
    calls: ClassVar[list[dict[str, Any]]] = []

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

    async def post(self, url: str, data: Any = None, **kwargs: Any):
        _MockAsyncClient.calls.append(
            {"method": "POST", "url": url, "data": data, **kwargs}
        )
        kind, payload, status = self._pop()
        assert kind == "post", f"Expected POST next; got queued '{kind}' for {url}"
        return _MockResponse(payload, status_code=status)

    async def get(self, url: str, **kwargs: Any):
        _MockAsyncClient.calls.append({"method": "GET", "url": url, **kwargs})
        kind, payload, status = self._pop()
        assert kind == "get", f"Expected GET next; got queued '{kind}' for {url}"
        return _MockResponse(payload, status_code=status)


def _seed_pkce(client: FakeClient, state: str, platform: str, verifier: str) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    client.pkce_states[state] = {
        "state": state,
        "user_id": state.split(":")[0],
        "platform": platform,
        "code_verifier": f"enc:{verifier}",
        "expires_at": expires_at.isoformat(),
    }


def _set_threads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THREADS_APP_ID", "test-threads-id")
    monkeypatch.setenv("THREADS_APP_SECRET", "test-threads-secret")


def _reset_mock() -> None:
    _MockAsyncClient.responses = []
    _MockAsyncClient.calls = []


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestThreadsAuthorizationUrl:
    def test_authorization_url_uses_threads_net(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        _set_threads_env(monkeypatch)
        client = FakeClient()
        connector = make_connector(client)

        result = connector.get_authorization_url(
            "threads", "user-1", "https://example.com/cb"
        )

        assert "authorization_url" in result, result
        url = result["authorization_url"]
        assert url.startswith("https://threads.net/oauth/authorize?"), url
        assert "client_id=test-threads-id" in url
        # urlencode renders space as '+' for application/x-www-form-urlencoded.
        assert "scope=threads_basic+threads_content_publish" in url
        assert "code_challenge_method=S256" in url
        assert "state=user-1" in url
        assert result["platform"] == "threads"

    def test_authorization_url_missing_client_id_returns_error(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("THREADS_APP_ID", raising=False)
        client = FakeClient()
        connector = make_connector(client)

        result = connector.get_authorization_url(
            "threads", "user-1", "https://example.com/cb"
        )

        assert "error" in result
        assert "THREADS_APP_ID" in result["error"]


class TestThreadsCallback:
    @pytest.mark.asyncio
    async def test_callback_state_round_trip_and_token_exchange(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        _set_threads_env(monkeypatch)
        client = FakeClient()
        connector = make_connector(client)
        state = "user-9:abc"
        verifier = "ver-9"
        _seed_pkce(client, state, "threads", verifier)

        token_payload = {
            "access_token": "AT",
            "refresh_token": "RT",
            "user_id": "1122334455",
            "expires_in": 3600,
        }
        _reset_mock()
        _MockAsyncClient.responses = [("post", token_payload, 200)]

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
                "threads", "CODE-X", state, "https://example.com/cb"
            )

        # Token exchange POST went to the right URL with the right body.
        assert _MockAsyncClient.calls, "no httpx calls recorded"
        first = _MockAsyncClient.calls[0]
        assert first["url"] == "https://graph.threads.net/oauth/access_token"
        sent = first["data"] or {}
        assert sent.get("code_verifier") == verifier
        assert sent.get("code") == "CODE-X"
        assert sent.get("client_id") == "test-threads-id"
        assert sent.get("client_secret") == "test-threads-secret"

        # Upsert payload carries the captured platform_user_id.
        assert client.connected_account_upserts, "handle_callback never upserted"
        upsert = client.connected_account_upserts[-1]
        assert upsert["platform"] == "threads"
        assert upsert["user_id"] == "user-9"
        assert upsert["platform_user_id"] == "1122334455"
        assert upsert["access_token"] == "enc:AT"
        assert upsert["refresh_token"] == "enc:RT"
        assert upsert["status"] == "active"

        assert result == {
            "success": True,
            "platform": "threads",
            "message": "Successfully connected threads account",
        }

    @pytest.mark.asyncio
    async def test_callback_token_response_without_user_id_uses_none(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        _set_threads_env(monkeypatch)
        client = FakeClient()
        connector = make_connector(client)
        state = "user-7:abc"
        _seed_pkce(client, state, "threads", "ver-7")

        token_payload = {"access_token": "AT", "expires_in": 3600}
        _reset_mock()
        _MockAsyncClient.responses = [("post", token_payload, 200)]

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
                "threads", "CODE-Y", state, "https://example.com/cb"
            )

        assert result.get("success") is True
        upsert = client.connected_account_upserts[-1]
        assert upsert["platform_user_id"] is None

    @pytest.mark.asyncio
    async def test_callback_token_exchange_4xx_returns_error(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        _set_threads_env(monkeypatch)
        client = FakeClient()
        connector = make_connector(client)
        state = "user-3:abc"
        _seed_pkce(client, state, "threads", "ver-3")

        _reset_mock()
        _MockAsyncClient.responses = [("post", {"error": "invalid_grant"}, 400)]

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
                "threads", "BAD-CODE", state, "https://example.com/cb"
            )

        assert "error" in result
        assert "Token exchange failed" in result["error"]
        # No row should have been written.
        assert client.connected_account_upserts == []


class TestGetPlatformUserId:
    def test_returns_id_when_active_row_exists(self):
        client = FakeClient()
        client.connected_accounts.append(
            {
                "user_id": "u1",
                "platform": "threads",
                "platform_user_id": "1122334455",
                "status": "active",
            }
        )
        connector = make_connector(client)

        result = connector.get_platform_user_id("u1", "threads")

        assert result == "1122334455"

    def test_returns_none_when_no_row(self):
        client = FakeClient()
        connector = make_connector(client)

        result = connector.get_platform_user_id("u1", "threads")

        assert result is None
