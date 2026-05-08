from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
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
        return next((value for column, value in self._filters if column == "state"), None)

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


def test_pkce_verifier_is_persisted_encrypted_and_consumed():
    client = _FakeClient()
    connector = _connector(client)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()

    with patch("app.social.connector.encrypt_secret", side_effect=lambda value: f"enc:{value}"):
        connector._store_pkce_verifier(
            "state-1",
            "00000000-0000-0000-0000-000000000001",
            "linkedin",
            "verifier-1",
        )

    assert client.pkce_rows["state-1"]["code_verifier"] == "enc:verifier-1"

    client.pkce_rows["state-1"]["expires_at"] = expires_at
    with patch("app.social.connector.decrypt_secret", return_value="verifier-1"):
        verifier = connector._pop_pkce_verifier("state-1", "linkedin")

    assert verifier == "verifier-1"
    assert "state-1" not in client.pkce_rows


@pytest.mark.asyncio
async def test_callback_uses_persisted_pkce_and_stores_encrypted_tokens(monkeypatch):
    client = _FakeClient()
    connector = _connector(client)
    state = "00000000-0000-0000-0000-000000000001:state"
    client.pkce_rows[state] = {
        "state": state,
        "platform": "linkedin",
        "code_verifier": "enc:verifier",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
    }
    requests: list[dict[str, Any]] = []

    class _Response:
        status_code = 200
        text = ""

        def json(self):
            return {
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "expires_in": 1800,
            }

    class _AsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def post(self, url: str, data: dict[str, Any]):
            requests.append({"url": url, "data": data})
            return _Response()

    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "client-id")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "client-secret")

    with (
        patch("httpx.AsyncClient", _AsyncClient),
        patch("app.social.connector.encrypt_secret", side_effect=lambda value: f"enc:{value}"),
        patch("app.social.connector.decrypt_secret", return_value="verifier"),
    ):
        result = await connector.handle_callback(
            "linkedin",
            "auth-code",
            state,
            "https://example.test/callback",
        )

    assert result["success"] is True
    assert requests[0]["data"]["code_verifier"] == "verifier"
    assert client.connected_account_upserts[0]["access_token"] == "enc:access-token"
    assert client.connected_account_upserts[0]["refresh_token"] == "enc:refresh-token"


def test_get_access_token_decrypts_stored_token():
    client = _FakeClient()
    client.connected_accounts = [
        {
            "access_token": "enc:access-token",
            "refresh_token": "enc:refresh-token",
            "token_expires_at": (
                datetime.now(timezone.utc) + timedelta(minutes=5)
            ).isoformat(),
        }
    ]
    connector = _connector(client)

    with patch("app.social.connector.decrypt_secret", return_value="access-token"):
        assert connector.get_access_token("user-id", "linkedin") == "access-token"
