"""Tests for LinkedIn URN capture (POST-01) at OAuth callback time.

These tests target ``SocialConnector._fetch_linkedin_identity`` and the
``handle_callback`` wiring that persists ``platform_user_id`` (the bare
OIDC ``sub`` claim) and ``platform_username`` (display name) into
``connected_accounts``.

Fixture pattern mirrors ``tests/unit/test_social_connector_security.py``
to keep test infrastructure consistent across the social-connector
suite.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar
from unittest.mock import patch

import pytest

from app.social.connector import SocialConnector


class _Result:
    def __init__(self, data: list[dict[str, Any]] | None = None):
        self.data = data or []


class _FakeTable:
    def __init__(self, name: str, client: _FakeClient):
        self.name = name
        self.client = client
        self._operation: str | None = None
        self._payload: dict[str, Any] | None = None
        self._filters: list[tuple[str, Any]] = []

    def upsert(self, payload: dict[str, Any], on_conflict: str | None = None):
        self._operation = "upsert"
        self._payload = payload
        return self

    def select(self, _columns: str):
        self._operation = "select"
        return self

    def delete(self):
        self._operation = "delete"
        return self

    def update(self, payload: dict[str, Any]):
        self._operation = "update"
        self._payload = payload
        return self

    def eq(self, column: str, value: Any):
        self._filters.append((column, value))
        return self

    def limit(self, _count: int):
        return self

    def execute(self):
        if self.name == "oauth_pkce_states":
            return self._execute_pkce()
        if self.name == "connected_accounts":
            return self._execute_connected_accounts()
        return _Result()

    def _state_filter(self) -> str | None:
        return next(
            (value for column, value in self._filters if column == "state"), None
        )

    def _execute_pkce(self):
        if self._operation == "upsert" and self._payload:
            self.client.pkce_rows[self._payload["state"]] = self._payload
            return _Result([self._payload])

        state = self._state_filter()
        if self._operation == "select" and state:
            row = self.client.pkce_rows.get(state)
            return _Result([row] if row else [])

        if self._operation == "delete" and state:
            self.client.pkce_rows.pop(state, None)
            return _Result()

        return _Result()

    def _execute_connected_accounts(self):
        if self._operation == "upsert" and self._payload:
            self.client.connected_account_upserts.append(self._payload)
            return _Result([self._payload])

        if self._operation == "select":
            return _Result(self.client.connected_accounts)

        if self._operation == "update" and self._payload:
            self.client.connected_account_updates.append(self._payload)
            return _Result([self._payload])

        return _Result()


class _FakeClient:
    def __init__(self):
        self.pkce_rows: dict[str, dict[str, Any]] = {}
        self.connected_accounts: list[dict[str, Any]] = []
        self.connected_account_upserts: list[dict[str, Any]] = []
        self.connected_account_updates: list[dict[str, Any]] = []

    def table(self, name: str):
        return _FakeTable(name, self)


def _connector(client: _FakeClient) -> SocialConnector:
    connector = SocialConnector.__new__(SocialConnector)
    connector.client = client
    connector._pkce_verifiers = {}
    return connector


class _Response:
    def __init__(
        self,
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        text: str = "",
    ):
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._json


class _RecordingAsyncClient:
    """httpx.AsyncClient stand-in that records calls and dispatches by URL.

    Each test sets the class-level ``responses`` dict before instantiation
    (URL substring -> ``_Response``). ``requests`` accumulates one entry
    per call as ``{"method", "url", "headers", "data", "json"}``.
    """

    responses: ClassVar[dict[str, _Response]] = {}
    requests: ClassVar[list[dict[str, Any]]] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def _dispatch(self, url: str) -> _Response:
        for key, resp in self.responses.items():
            if key in url:
                return resp
        return _Response(status_code=404, text="no mock response")

    async def post(
        self,
        url: str,
        data: Any = None,
        json: Any = None,
        headers: dict | None = None,
        timeout: float | None = None,
    ):
        self.requests.append(
            {
                "method": "POST",
                "url": url,
                "headers": headers or {},
                "data": data,
                "json": json,
            }
        )
        return self._dispatch(url)

    async def get(
        self,
        url: str,
        headers: dict | None = None,
        params: dict | None = None,
        timeout: float | None = None,
    ):
        self.requests.append(
            {
                "method": "GET",
                "url": url,
                "headers": headers or {},
                "params": params or {},
            }
        )
        return self._dispatch(url)


def _seed_pkce(client: _FakeClient, state: str, platform: str = "linkedin") -> None:
    client.pkce_rows[state] = {
        "state": state,
        "platform": platform,
        "code_verifier": "enc:verifier",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
    }


@pytest.mark.asyncio
async def test_linkedin_callback_captures_urn(monkeypatch):
    """Happy path: callback persists bare OIDC sub + display name."""
    client = _FakeClient()
    connector = _connector(client)
    state = "00000000-0000-0000-0000-000000000001:state"
    _seed_pkce(client, state, "linkedin")

    _RecordingAsyncClient.responses = {
        "oauth/v2/accessToken": _Response(
            status_code=200,
            json_data={
                "access_token": "AT",
                "refresh_token": "RT",
                "expires_in": 1800,
            },
        ),
        "v2/userinfo": _Response(
            status_code=200,
            json_data={
                "sub": "782bbtaQ",
                "name": "John Doe",
                "given_name": "John",
                "email": "doe@example.com",
            },
        ),
    }
    _RecordingAsyncClient.requests = []

    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "client-id")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "client-secret")

    with (
        patch("httpx.AsyncClient", _RecordingAsyncClient),
        patch(
            "app.social.connector.encrypt_secret",
            side_effect=lambda value: f"enc:{value}",
        ),
        patch("app.social.connector.decrypt_secret", return_value="verifier"),
    ):
        result = await connector.handle_callback(
            "linkedin",
            "auth-code",
            state,
            "https://example.test/callback",
        )

    assert result["success"] is True
    assert client.connected_account_upserts, (
        "expected an upsert into connected_accounts"
    )
    upsert = client.connected_account_upserts[0]
    assert upsert["platform_user_id"] == "782bbtaQ"
    assert upsert["platform_username"] == "John Doe"

    # Verify the userinfo GET happened with the bearer token.
    userinfo_calls = [
        r for r in _RecordingAsyncClient.requests if "v2/userinfo" in r["url"]
    ]
    assert len(userinfo_calls) == 1
    assert userinfo_calls[0]["headers"].get("Authorization") == "Bearer AT"


@pytest.mark.asyncio
async def test_linkedin_callback_userinfo_failure_does_not_block_callback(
    monkeypatch, caplog
):
    """If /v2/userinfo returns 500, the callback still succeeds; URN is null."""
    client = _FakeClient()
    connector = _connector(client)
    state = "00000000-0000-0000-0000-000000000002:state"
    _seed_pkce(client, state, "linkedin")

    _RecordingAsyncClient.responses = {
        "oauth/v2/accessToken": _Response(
            status_code=200,
            json_data={
                "access_token": "AT",
                "refresh_token": "RT",
                "expires_in": 1800,
            },
        ),
        "v2/userinfo": _Response(status_code=500, text="boom"),
    }
    _RecordingAsyncClient.requests = []

    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "client-id")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "client-secret")

    caplog.set_level(logging.WARNING, logger="app.social.connector")

    with (
        patch("httpx.AsyncClient", _RecordingAsyncClient),
        patch(
            "app.social.connector.encrypt_secret",
            side_effect=lambda value: f"enc:{value}",
        ),
        patch("app.social.connector.decrypt_secret", return_value="verifier"),
    ):
        result = await connector.handle_callback(
            "linkedin",
            "auth-code",
            state,
            "https://example.test/callback",
        )

    assert result["success"] is True
    upsert = client.connected_account_upserts[0]
    assert upsert["platform_user_id"] is None
    assert upsert["platform_username"] is None
    # A warning must mention the userinfo failure for operator triage.
    relevant = [
        rec
        for rec in caplog.records
        if rec.levelno == logging.WARNING
        and (
            "userinfo" in rec.getMessage().lower()
            or "linkedin" in rec.getMessage().lower()
        )
    ]
    assert relevant, "expected a WARNING log mentioning userinfo / linkedin"


@pytest.mark.asyncio
async def test_non_linkedin_platform_does_not_call_userinfo(monkeypatch):
    """Twitter callback must NOT touch /v2/userinfo."""
    client = _FakeClient()
    connector = _connector(client)
    state = "00000000-0000-0000-0000-000000000003:state"
    _seed_pkce(client, state, "twitter")

    _RecordingAsyncClient.responses = {
        "oauth2/token": _Response(
            status_code=200,
            json_data={
                "access_token": "AT",
                "refresh_token": "RT",
                "expires_in": 1800,
            },
        ),
        # Twitter's profile endpoint is /2/users/me; we return 500 so the
        # connector's existing _fetch_platform_profile dispatch logs a
        # warning but still completes the callback.
        "/2/users/me": _Response(status_code=500, text=""),
    }
    _RecordingAsyncClient.requests = []

    monkeypatch.setenv("TWITTER_CLIENT_ID", "client-id")
    monkeypatch.setenv("TWITTER_CLIENT_SECRET", "client-secret")

    with (
        patch("httpx.AsyncClient", _RecordingAsyncClient),
        patch(
            "app.social.connector.encrypt_secret",
            side_effect=lambda value: f"enc:{value}",
        ),
        patch("app.social.connector.decrypt_secret", return_value="verifier"),
    ):
        result = await connector.handle_callback(
            "twitter",
            "auth-code",
            state,
            "https://example.test/callback",
        )

    assert result["success"] is True
    # Critical: no GET to /v2/userinfo for non-LinkedIn platforms.
    userinfo_calls = [
        r for r in _RecordingAsyncClient.requests if "v2/userinfo" in r["url"]
    ]
    assert userinfo_calls == [], "Twitter callback must not call LinkedIn /v2/userinfo"
