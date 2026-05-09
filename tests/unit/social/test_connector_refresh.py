# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Per-platform _refresh_token tests (Plan 108-04 / HYGIENE-04).

Asserts the auth_method branch correctness (form vs basic) on
``SocialConnector._refresh_token`` for every platform that issues a
refresh token. Also covers refresh failure (4xx → return None, no
token rotation) and concurrent refresh under the per-key lock (covered
already by ``test_async_refresh.py`` for linkedin; this file backfills
the per-platform refresh body shape).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar
from unittest.mock import patch

import pytest

from app.social.connector import SocialConnector
from tests.unit.social.conftest import FakeClient, make_connector


class _MockResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = ""

    def json(self):
        return self._payload


class _RefreshAsyncClient:
    """Records every POST call; replays a single queued response per platform."""

    response: ClassVar[_MockResponse] = _MockResponse({}, 200)
    calls: ClassVar[list[dict[str, Any]]] = []

    def __init__(self, *_a: Any, **_kw: Any):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a: Any):
        return False

    async def post(self, url: str, **kwargs: Any):
        _RefreshAsyncClient.calls.append({"url": url, **kwargs})
        return _RefreshAsyncClient.response


def _seed_expired(client: FakeClient, user_id: str, platform: str) -> None:
    client.connected_accounts.append(
        {
            "user_id": user_id,
            "platform": platform,
            "status": "active",
            "access_token": "enc:old-access",
            "refresh_token": "enc:refresh-token",
            "token_expires_at": (
                datetime.now(timezone.utc) - timedelta(minutes=5)
            ).isoformat(),
        }
    )


def _reset_mock(payload: dict[str, Any] | None = None, status: int = 200):
    _RefreshAsyncClient.calls = []
    _RefreshAsyncClient.response = _MockResponse(payload or {}, status)


def _decrypt(v):
    if isinstance(v, str) and v.startswith("enc:"):
        return v.removeprefix("enc:")
    return v


def _encrypt(v):
    return f"enc:{v}"


@pytest.fixture(autouse=True)
def _reset_refresh_state():
    SocialConnector._refresh_locks = {}
    SocialConnector._locks_guard = None
    yield
    SocialConnector._refresh_locks = {}
    SocialConnector._locks_guard = None


# ---------------------------------------------------------------------------
# Form-auth platforms
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "platform,client_id_env,client_secret_env,client_id,client_secret",
    [
        ("twitter", "TWITTER_CLIENT_ID", "TWITTER_CLIENT_SECRET", "tw-id", "tw-sec"),
        ("linkedin", "LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET", "li-id", "li-sec"),
        ("facebook", "FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET", "fb-id", "fb-sec"),
        ("instagram", "FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET", "fb-id", "fb-sec"),
        ("youtube", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "g-id", "g-sec"),
        ("tiktok", "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "tt-key", "tt-sec"),
        ("threads", "THREADS_APP_ID", "THREADS_APP_SECRET", "th-id", "th-sec"),
    ],
)
@pytest.mark.asyncio
async def test_refresh_form_auth_includes_client_credentials_in_body(
    monkeypatch: pytest.MonkeyPatch,
    platform: str,
    client_id_env: str,
    client_secret_env: str,
    client_id: str,
    client_secret: str,
):
    monkeypatch.setenv(client_id_env, client_id)
    monkeypatch.setenv(client_secret_env, client_secret)

    client = FakeClient()
    connector = make_connector(client)
    _seed_expired(client, "u1", platform)

    _reset_mock(
        {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        },
        200,
    )

    with (
        patch("app.social.connector.httpx.AsyncClient", _RefreshAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt),
        patch("app.social.connector.encrypt_secret", side_effect=_encrypt),
    ):
        token = await connector.get_access_token("u1", platform)

    assert token == "new-access"
    assert len(_RefreshAsyncClient.calls) == 1
    call = _RefreshAsyncClient.calls[0]
    body = call.get("data") or {}
    # form-auth platforms put credentials in the body, not auth=
    assert body.get("client_id") == client_id
    assert body.get("client_secret") == client_secret
    assert body.get("grant_type") == "refresh_token"
    assert body.get("refresh_token") == "refresh-token"
    assert call.get("auth") is None

    # Refresh token rotation persisted
    upd = client.connected_account_updates[-1]
    assert upd.get("access_token") == "enc:new-access"
    assert upd.get("refresh_token") == "enc:new-refresh"


# ---------------------------------------------------------------------------
# Basic-auth platforms
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pinterest_refresh_uses_basic_auth_not_body(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("PINTEREST_CLIENT_ID", "pin-id")
    monkeypatch.setenv("PINTEREST_CLIENT_SECRET", "pin-sec")

    client = FakeClient()
    connector = make_connector(client)
    _seed_expired(client, "u1", "pinterest")

    _reset_mock(
        {
            "access_token": "new-access",
            "expires_in": 3600,
        },
        200,
    )

    with (
        patch("app.social.connector.httpx.AsyncClient", _RefreshAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt),
        patch("app.social.connector.encrypt_secret", side_effect=_encrypt),
    ):
        token = await connector.get_access_token("u1", "pinterest")

    assert token == "new-access"
    call = _RefreshAsyncClient.calls[0]
    body = call.get("data") or {}
    # Pinterest body MUST NOT contain client credentials
    assert "client_id" not in body
    assert "client_secret" not in body
    # Basic auth tuple instead
    assert call.get("auth") == ("pin-id", "pin-sec")


# ---------------------------------------------------------------------------
# Refresh failures
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_4xx_returns_none_no_token_rotation(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TWITTER_CLIENT_ID", "tw-id")
    monkeypatch.setenv("TWITTER_CLIENT_SECRET", "tw-sec")

    client = FakeClient()
    connector = make_connector(client)
    _seed_expired(client, "u1", "twitter")

    _reset_mock({"error": "invalid_grant"}, 401)

    with (
        patch("app.social.connector.httpx.AsyncClient", _RefreshAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt),
        patch("app.social.connector.encrypt_secret", side_effect=_encrypt),
    ):
        token = await connector.get_access_token("u1", "twitter")

    assert token is None
    # No update fired -- old token remains
    assert client.connected_account_updates == []


@pytest.mark.asyncio
async def test_refresh_no_refresh_token_returns_none():
    client = FakeClient()
    connector = make_connector(client)
    # Seed an expired row WITHOUT a refresh_token
    client.connected_accounts.append(
        {
            "user_id": "u1",
            "platform": "twitter",
            "status": "active",
            "access_token": "enc:old",
            "refresh_token": None,
            "token_expires_at": (
                datetime.now(timezone.utc) - timedelta(minutes=5)
            ).isoformat(),
        }
    )

    with (
        patch("app.social.connector.httpx.AsyncClient", _RefreshAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt),
        patch("app.social.connector.encrypt_secret", side_effect=_encrypt),
    ):
        token = await connector.get_access_token("u1", "twitter")

    assert token is None


@pytest.mark.asyncio
async def test_refresh_missing_credentials_env_returns_none(
    monkeypatch: pytest.MonkeyPatch,
):
    # Missing client id env var -> _refresh_token returns None
    monkeypatch.delenv("TWITTER_CLIENT_ID", raising=False)
    monkeypatch.delenv("TWITTER_CLIENT_SECRET", raising=False)

    client = FakeClient()
    connector = make_connector(client)
    _seed_expired(client, "u1", "twitter")

    with (
        patch("app.social.connector.httpx.AsyncClient", _RefreshAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt),
        patch("app.social.connector.encrypt_secret", side_effect=_encrypt),
    ):
        token = await connector.get_access_token("u1", "twitter")

    assert token is None


@pytest.mark.asyncio
async def test_refresh_unknown_platform_returns_none():
    client = FakeClient()
    connector = make_connector(client)
    # Seed expired row for a platform NOT in PLATFORM_CONFIGS
    client.connected_accounts.append(
        {
            "user_id": "u1",
            "platform": "myspace",
            "status": "active",
            "access_token": "enc:old",
            "refresh_token": "enc:refresh",
            "token_expires_at": (
                datetime.now(timezone.utc) - timedelta(minutes=5)
            ).isoformat(),
        }
    )

    with patch("app.social.connector.decrypt_secret", side_effect=_decrypt):
        token = await connector.get_access_token("u1", "myspace")

    assert token is None


@pytest.mark.asyncio
async def test_refresh_response_no_access_token_returns_none(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TWITTER_CLIENT_ID", "tw-id")
    monkeypatch.setenv("TWITTER_CLIENT_SECRET", "tw-sec")

    client = FakeClient()
    connector = make_connector(client)
    _seed_expired(client, "u1", "twitter")

    _reset_mock({"expires_in": 3600}, 200)  # no access_token

    with (
        patch("app.social.connector.httpx.AsyncClient", _RefreshAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt),
        patch("app.social.connector.encrypt_secret", side_effect=_encrypt),
    ):
        token = await connector.get_access_token("u1", "twitter")

    assert token is None


# ---------------------------------------------------------------------------
# get_access_token surface tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_access_token_no_active_row_returns_none():
    client = FakeClient()  # empty
    connector = make_connector(client)
    token = await connector.get_access_token("u1", "twitter")
    assert token is None


@pytest.mark.asyncio
async def test_get_access_token_non_expired_returns_decrypted_immediately():
    client = FakeClient()
    client.connected_accounts.append(
        {
            "user_id": "u1",
            "platform": "twitter",
            "status": "active",
            "access_token": "enc:my-token",
            "refresh_token": "enc:my-refresh",
            "token_expires_at": (
                datetime.now(timezone.utc) + timedelta(hours=1)
            ).isoformat(),
        }
    )
    connector = make_connector(client)

    with patch("app.social.connector.decrypt_secret", side_effect=_decrypt):
        token = await connector.get_access_token("u1", "twitter")

    assert token == "my-token"


# ---------------------------------------------------------------------------
# _is_token_expired edge cases
# ---------------------------------------------------------------------------


def test_is_token_expired_none_returns_false():
    assert SocialConnector._is_token_expired(None) is False


def test_is_token_expired_unparseable_returns_false():
    assert SocialConnector._is_token_expired("not-a-date") is False


def test_is_token_expired_past_returns_true():
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert SocialConnector._is_token_expired(past) is True


def test_is_token_expired_future_returns_false():
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    assert SocialConnector._is_token_expired(future) is False


def test_is_token_expired_z_suffix_handled():
    # Code converts "Z" to "+00:00" via replace
    past = (
        datetime.now(timezone.utc) - timedelta(hours=1)
    ).isoformat().replace("+00:00", "Z")
    assert SocialConnector._is_token_expired(past) is True
