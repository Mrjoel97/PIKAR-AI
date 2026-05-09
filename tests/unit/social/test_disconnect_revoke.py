# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Per-platform disconnect-revoke ordering tests (Plan 108-04 / HYGIENE-04).

Asserts that ``SocialConnector.disconnect_account(user_id, platform)``:

1. POSTs to the provider's OAuth revoke endpoint BEFORE marking the
   local ``connected_accounts`` row ``status='revoked'`` -- provable via
   ``parent.mock_calls`` ordering.
2. Skips the remote HTTP call entirely for LinkedIn (no public revoke
   endpoint), still updates the local row, and returns
   ``remote_revoked=False, remote_error="no_remote_revoke_endpoint"``.
3. Updates the local row even when the remote revoke call fails (4xx /
   5xx / network exception). The user is never permanently stuck
   connected.
4. Skips the HTTP call when no token is stored for the
   ``(user_id, platform)`` row (already revoked / never connected).
5. The sync ``revoke_connection`` wrapper preserves backward compat
   with ``app/agents/tools/social.py:disconnect_social_account``.

Provider revoke endpoint matrix (from 108-RESEARCH.md):

- twitter:    POST https://api.twitter.com/2/oauth2/revoke (Basic auth)
- youtube:    POST https://oauth2.googleapis.com/revoke (no auth)
- facebook:   DELETE https://graph.facebook.com/v18.0/me/permissions (Bearer)
- instagram:  DELETE https://graph.facebook.com/v18.0/me/permissions (Bearer)
- threads:    DELETE https://graph.threads.net/v1.0/me/permissions (Bearer)
- tiktok:     POST https://open.tiktokapis.com/v2/oauth/revoke/ (form: client_key)
- pinterest:  POST https://api.pinterest.com/v5/oauth/token/revoke (Basic auth)
- linkedin:   NO ENDPOINT (skip HTTP, update local only)
"""

from __future__ import annotations

from typing import Any, ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.unit.social.conftest import FakeClient, make_connector


class _MockResponse:
    def __init__(self, status_code: int = 200, text: str = "", payload: dict | None = None):
        self.status_code = status_code
        self.text = text or ""
        self._payload = payload or {}

    def json(self):
        return self._payload


class _RecordingAsyncClient:
    """httpx.AsyncClient double recording every call into a parent MagicMock.

    Both ``.post`` and ``.delete`` route through the same recorded mock so
    tests can assert ordering across HTTP method + DB update.
    """

    parent: ClassVar[MagicMock | None] = None
    next_response: ClassVar[_MockResponse] = _MockResponse(status_code=200)
    raise_exc: ClassVar[Exception | None] = None

    def __init__(self, *_args: Any, **_kwargs: Any):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args: Any):
        return False

    async def post(self, url: str, **kwargs: Any):
        if _RecordingAsyncClient.parent is not None:
            _RecordingAsyncClient.parent.http_call(method="POST", url=url, **kwargs)
        if _RecordingAsyncClient.raise_exc is not None:
            raise _RecordingAsyncClient.raise_exc
        return _RecordingAsyncClient.next_response

    async def delete(self, url: str, **kwargs: Any):
        if _RecordingAsyncClient.parent is not None:
            _RecordingAsyncClient.parent.http_call(method="DELETE", url=url, **kwargs)
        if _RecordingAsyncClient.raise_exc is not None:
            raise _RecordingAsyncClient.raise_exc
        return _RecordingAsyncClient.next_response


def _seed_active_account(client: FakeClient, user_id: str, platform: str) -> None:
    """Seed an active connected_accounts row with a stored token."""
    client.connected_accounts.append(
        {
            "user_id": user_id,
            "platform": platform,
            "access_token": "enc:test-token",
            "refresh_token": None,
            "token_expires_at": None,  # never expires for these tests
            "status": "active",
        }
    )


class _OrderingClient(FakeClient):
    """FakeClient that delegates ``update`` execution to the parent mock.

    Allows ``parent.mock_calls`` to record a single ``db_call`` entry the
    moment ``.execute()`` lands on the update branch -- so the ordering
    test can compare against the recorded ``http_call`` entries.
    """

    def __init__(self, parent: MagicMock):
        super().__init__()
        self.parent = parent

    def table(self, name: str):
        tbl = _OrderingTable(name, self, self.parent)
        return tbl


class _OrderingTable:
    def __init__(self, name: str, client: _OrderingClient, parent: MagicMock):
        from tests.unit.social.conftest import FakeTable

        self._inner = FakeTable(name, client)
        self._parent = parent
        self.name = name

    def select(self, columns: str):
        self._inner.select(columns)
        return self

    def update(self, payload: dict[str, Any]):
        self._inner.update(payload)
        return self

    def upsert(self, payload: dict[str, Any], on_conflict: str | None = None):
        self._inner.upsert(payload, on_conflict)
        return self

    def delete(self):
        self._inner.delete()
        return self

    def eq(self, column: str, value: Any):
        self._inner.eq(column, value)
        return self

    def limit(self, n: int):
        self._inner.limit(n)
        return self

    def execute(self):
        if self._inner._operation == "update" and self.name == "connected_accounts":
            self._parent.db_call(payload=self._inner._payload)
        return self._inner.execute()


@pytest.fixture
def parent_mock() -> MagicMock:
    """Parent MagicMock recording http_call + db_call in chronological order."""
    return MagicMock()


@pytest.fixture(autouse=True)
def _reset_recording_client():
    _RecordingAsyncClient.parent = None
    _RecordingAsyncClient.next_response = _MockResponse(status_code=200)
    _RecordingAsyncClient.raise_exc = None
    yield
    _RecordingAsyncClient.parent = None
    _RecordingAsyncClient.next_response = _MockResponse(status_code=200)
    _RecordingAsyncClient.raise_exc = None


def _make_connector_for_ordering(parent: MagicMock):
    client = _OrderingClient(parent)
    connector = make_connector(client)
    return connector, client


def _decrypt_id(v):
    if isinstance(v, str) and v.startswith("enc:"):
        return v.removeprefix("enc:")
    return v


# ---------------------------------------------------------------------------
# Helpers to assert ordering
# ---------------------------------------------------------------------------


def _ordered_call_names(parent: MagicMock) -> list[str]:
    """Return list of ('http_call'|'db_call') in chronological order."""
    names = []
    for call in parent.mock_calls:
        # call is a Call object: call[0] is the dotted name, e.g. 'http_call'
        name = call[0]
        # Skip nested attribute calls; only top-level http_call / db_call
        if name in ("http_call", "db_call"):
            names.append(name)
    return names


# ---------------------------------------------------------------------------
# Twitter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_twitter_disconnect_calls_revoke_before_db_update(
    monkeypatch: pytest.MonkeyPatch, parent_mock: MagicMock
):
    monkeypatch.setenv("TWITTER_CLIENT_ID", "test-twitter-id")
    monkeypatch.setenv("TWITTER_CLIENT_SECRET", "test-twitter-secret")
    connector, client = _make_connector_for_ordering(parent_mock)
    _seed_active_account(client, "u1", "twitter")

    _RecordingAsyncClient.parent = parent_mock
    _RecordingAsyncClient.next_response = _MockResponse(status_code=200)

    with (
        patch("app.social.connector.httpx.AsyncClient", _RecordingAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt_id),
    ):
        result = await connector.disconnect_account("u1", "twitter")

    names = _ordered_call_names(parent_mock)
    assert "http_call" in names, f"Expected http_call recorded; got {names}"
    assert "db_call" in names, f"Expected db_call recorded; got {names}"
    assert names.index("http_call") < names.index("db_call"), (
        f"Revoke HTTP must precede DB update; saw {names}"
    )

    # Inspect the recorded HTTP call for shape
    http_calls = [c for c in parent_mock.mock_calls if c[0] == "http_call"]
    kwargs = http_calls[0].kwargs
    assert kwargs["method"] == "POST"
    assert kwargs["url"] == "https://api.twitter.com/2/oauth2/revoke"
    body = kwargs.get("data") or {}
    assert body.get("token") == "test-token"
    assert body.get("client_id") == "test-twitter-id"
    assert kwargs.get("auth") == ("test-twitter-id", "test-twitter-secret")

    assert result["success"] is True
    assert result["remote_revoked"] is True
    assert result["remote_error"] is None


# ---------------------------------------------------------------------------
# LinkedIn (no remote endpoint)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_linkedin_disconnect_skips_remote_revoke(
    monkeypatch: pytest.MonkeyPatch, parent_mock: MagicMock
):
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "test-li-id")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "test-li-secret")
    connector, client = _make_connector_for_ordering(parent_mock)
    _seed_active_account(client, "u1", "linkedin")

    _RecordingAsyncClient.parent = parent_mock

    with (
        patch("app.social.connector.httpx.AsyncClient", _RecordingAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt_id),
    ):
        result = await connector.disconnect_account("u1", "linkedin")

    names = _ordered_call_names(parent_mock)
    assert "http_call" not in names, f"LinkedIn must not issue HTTP; saw {names}"
    assert "db_call" in names, f"Expected db_call; saw {names}"

    assert result["success"] is True
    assert result["remote_revoked"] is False
    assert result["remote_error"] == "no_remote_revoke_endpoint"


# ---------------------------------------------------------------------------
# Facebook
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_facebook_disconnect_calls_delete_permissions_before_db_update(
    monkeypatch: pytest.MonkeyPatch, parent_mock: MagicMock
):
    monkeypatch.setenv("FACEBOOK_APP_ID", "test-fb-id")
    monkeypatch.setenv("FACEBOOK_APP_SECRET", "test-fb-secret")
    connector, client = _make_connector_for_ordering(parent_mock)
    _seed_active_account(client, "u1", "facebook")

    _RecordingAsyncClient.parent = parent_mock
    _RecordingAsyncClient.next_response = _MockResponse(status_code=200)

    with (
        patch("app.social.connector.httpx.AsyncClient", _RecordingAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt_id),
    ):
        result = await connector.disconnect_account("u1", "facebook")

    names = _ordered_call_names(parent_mock)
    assert names.index("http_call") < names.index("db_call"), names

    http_calls = [c for c in parent_mock.mock_calls if c[0] == "http_call"]
    kwargs = http_calls[0].kwargs
    assert kwargs["method"] == "DELETE"
    assert kwargs["url"] == "https://graph.facebook.com/v18.0/me/permissions"
    headers = kwargs.get("headers") or {}
    assert headers.get("Authorization") == "Bearer test-token"

    assert result["success"] is True
    assert result["remote_revoked"] is True


# ---------------------------------------------------------------------------
# Instagram (same Meta endpoint)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_instagram_disconnect_calls_delete_permissions_before_db_update(
    monkeypatch: pytest.MonkeyPatch, parent_mock: MagicMock
):
    monkeypatch.setenv("FACEBOOK_APP_ID", "test-fb-id")
    monkeypatch.setenv("FACEBOOK_APP_SECRET", "test-fb-secret")
    connector, client = _make_connector_for_ordering(parent_mock)
    _seed_active_account(client, "u1", "instagram")

    _RecordingAsyncClient.parent = parent_mock
    _RecordingAsyncClient.next_response = _MockResponse(status_code=200)

    with (
        patch("app.social.connector.httpx.AsyncClient", _RecordingAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt_id),
    ):
        result = await connector.disconnect_account("u1", "instagram")

    names = _ordered_call_names(parent_mock)
    assert names.index("http_call") < names.index("db_call"), names

    http_calls = [c for c in parent_mock.mock_calls if c[0] == "http_call"]
    kwargs = http_calls[0].kwargs
    assert kwargs["method"] == "DELETE"
    assert kwargs["url"] == "https://graph.facebook.com/v18.0/me/permissions"

    assert result["remote_revoked"] is True


# ---------------------------------------------------------------------------
# YouTube (Google revoke)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_youtube_disconnect_calls_google_revoke_before_db_update(
    monkeypatch: pytest.MonkeyPatch, parent_mock: MagicMock
):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-g-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-g-secret")
    connector, client = _make_connector_for_ordering(parent_mock)
    _seed_active_account(client, "u1", "youtube")

    _RecordingAsyncClient.parent = parent_mock
    _RecordingAsyncClient.next_response = _MockResponse(status_code=200)

    with (
        patch("app.social.connector.httpx.AsyncClient", _RecordingAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt_id),
    ):
        result = await connector.disconnect_account("u1", "youtube")

    names = _ordered_call_names(parent_mock)
    assert names.index("http_call") < names.index("db_call"), names

    http_calls = [c for c in parent_mock.mock_calls if c[0] == "http_call"]
    kwargs = http_calls[0].kwargs
    assert kwargs["method"] == "POST"
    assert kwargs["url"] == "https://oauth2.googleapis.com/revoke"
    body = kwargs.get("data") or {}
    assert body.get("token") == "test-token"

    assert result["remote_revoked"] is True


@pytest.mark.asyncio
async def test_google_search_console_disconnect_uses_google_revoke_endpoint(
    monkeypatch: pytest.MonkeyPatch, parent_mock: MagicMock
):
    monkeypatch.setenv("GOOGLE_SEO_CLIENT_ID", "test-g-id")
    monkeypatch.setenv("GOOGLE_SEO_CLIENT_SECRET", "test-g-secret")
    connector, client = _make_connector_for_ordering(parent_mock)
    _seed_active_account(client, "u1", "google_search_console")

    _RecordingAsyncClient.parent = parent_mock
    _RecordingAsyncClient.next_response = _MockResponse(status_code=200)

    with (
        patch("app.social.connector.httpx.AsyncClient", _RecordingAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt_id),
    ):
        result = await connector.disconnect_account("u1", "google_search_console")

    http_calls = [c for c in parent_mock.mock_calls if c[0] == "http_call"]
    assert http_calls, "Expected at least one HTTP call"
    kwargs = http_calls[0].kwargs
    assert kwargs["url"] == "https://oauth2.googleapis.com/revoke"
    assert result["remote_revoked"] is True


# ---------------------------------------------------------------------------
# TikTok (client_key not client_id)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tiktok_disconnect_uses_client_key_in_body(
    monkeypatch: pytest.MonkeyPatch, parent_mock: MagicMock
):
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "test-tiktok-key")
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "test-tiktok-secret")
    connector, client = _make_connector_for_ordering(parent_mock)
    _seed_active_account(client, "u1", "tiktok")

    _RecordingAsyncClient.parent = parent_mock
    _RecordingAsyncClient.next_response = _MockResponse(status_code=200)

    with (
        patch("app.social.connector.httpx.AsyncClient", _RecordingAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt_id),
    ):
        result = await connector.disconnect_account("u1", "tiktok")

    names = _ordered_call_names(parent_mock)
    assert names.index("http_call") < names.index("db_call"), names

    http_calls = [c for c in parent_mock.mock_calls if c[0] == "http_call"]
    kwargs = http_calls[0].kwargs
    assert kwargs["method"] == "POST"
    assert kwargs["url"] == "https://open.tiktokapis.com/v2/oauth/revoke/"
    body = kwargs.get("data") or {}
    assert body.get("client_key") == "test-tiktok-key"
    assert body.get("client_secret") == "test-tiktok-secret"
    assert body.get("token") == "test-token"
    # MUST NOT have client_id key
    assert "client_id" not in body, body

    assert result["remote_revoked"] is True


# ---------------------------------------------------------------------------
# Threads (graph.threads.net/me/permissions)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_threads_disconnect_calls_delete_permissions_on_threads_net(
    monkeypatch: pytest.MonkeyPatch, parent_mock: MagicMock
):
    monkeypatch.setenv("THREADS_APP_ID", "test-th-id")
    monkeypatch.setenv("THREADS_APP_SECRET", "test-th-secret")
    connector, client = _make_connector_for_ordering(parent_mock)
    _seed_active_account(client, "u1", "threads")

    _RecordingAsyncClient.parent = parent_mock
    _RecordingAsyncClient.next_response = _MockResponse(status_code=200)

    with (
        patch("app.social.connector.httpx.AsyncClient", _RecordingAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt_id),
    ):
        result = await connector.disconnect_account("u1", "threads")

    names = _ordered_call_names(parent_mock)
    assert names.index("http_call") < names.index("db_call"), names

    http_calls = [c for c in parent_mock.mock_calls if c[0] == "http_call"]
    kwargs = http_calls[0].kwargs
    assert kwargs["method"] == "DELETE"
    assert kwargs["url"] == "https://graph.threads.net/v1.0/me/permissions"
    headers = kwargs.get("headers") or {}
    assert headers.get("Authorization") == "Bearer test-token"

    assert result["remote_revoked"] is True


# ---------------------------------------------------------------------------
# Pinterest (basic auth, token_type_hint)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pinterest_disconnect_uses_basic_auth_token_revoke(
    monkeypatch: pytest.MonkeyPatch, parent_mock: MagicMock
):
    monkeypatch.setenv("PINTEREST_CLIENT_ID", "test-pin-id")
    monkeypatch.setenv("PINTEREST_CLIENT_SECRET", "test-pin-secret")
    connector, client = _make_connector_for_ordering(parent_mock)
    _seed_active_account(client, "u1", "pinterest")

    _RecordingAsyncClient.parent = parent_mock
    _RecordingAsyncClient.next_response = _MockResponse(status_code=200)

    with (
        patch("app.social.connector.httpx.AsyncClient", _RecordingAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt_id),
    ):
        result = await connector.disconnect_account("u1", "pinterest")

    names = _ordered_call_names(parent_mock)
    assert names.index("http_call") < names.index("db_call"), names

    http_calls = [c for c in parent_mock.mock_calls if c[0] == "http_call"]
    kwargs = http_calls[0].kwargs
    assert kwargs["method"] == "POST"
    assert kwargs["url"] == "https://api.pinterest.com/v5/oauth/token/revoke"
    assert kwargs.get("auth") == ("test-pin-id", "test-pin-secret")
    body = kwargs.get("data") or {}
    assert body.get("token") == "test-token"
    assert body.get("token_type_hint") == "access_token"

    assert result["remote_revoked"] is True


# ---------------------------------------------------------------------------
# Revoke failure still updates local row
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disconnect_revoke_failure_still_updates_local_row(
    monkeypatch: pytest.MonkeyPatch, parent_mock: MagicMock
):
    monkeypatch.setenv("TWITTER_CLIENT_ID", "test-twitter-id")
    monkeypatch.setenv("TWITTER_CLIENT_SECRET", "test-twitter-secret")
    connector, client = _make_connector_for_ordering(parent_mock)
    _seed_active_account(client, "u1", "twitter")

    _RecordingAsyncClient.parent = parent_mock
    _RecordingAsyncClient.next_response = _MockResponse(
        status_code=500, text="Internal Server Error"
    )

    with (
        patch("app.social.connector.httpx.AsyncClient", _RecordingAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt_id),
    ):
        result = await connector.disconnect_account("u1", "twitter")

    # DB update STILL fired
    assert client.connected_account_updates, "Local row update did not fire"
    assert client.connected_account_updates[-1].get("status") == "revoked"

    assert result["success"] is True
    assert result["remote_revoked"] is False
    assert result["remote_error"] is not None
    assert "500" in result["remote_error"]


@pytest.mark.asyncio
async def test_disconnect_revoke_network_exception_still_updates_local_row(
    monkeypatch: pytest.MonkeyPatch, parent_mock: MagicMock
):
    monkeypatch.setenv("TWITTER_CLIENT_ID", "test-twitter-id")
    monkeypatch.setenv("TWITTER_CLIENT_SECRET", "test-twitter-secret")
    connector, client = _make_connector_for_ordering(parent_mock)
    _seed_active_account(client, "u1", "twitter")

    _RecordingAsyncClient.parent = parent_mock
    _RecordingAsyncClient.raise_exc = RuntimeError("dns failure")

    with (
        patch("app.social.connector.httpx.AsyncClient", _RecordingAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt_id),
    ):
        result = await connector.disconnect_account("u1", "twitter")

    assert client.connected_account_updates[-1].get("status") == "revoked"
    assert result["success"] is True
    assert result["remote_revoked"] is False
    assert result["remote_error"] is not None


# ---------------------------------------------------------------------------
# No stored token -> skip remote
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disconnect_with_no_stored_token_skips_remote_call(
    monkeypatch: pytest.MonkeyPatch, parent_mock: MagicMock
):
    monkeypatch.setenv("TWITTER_CLIENT_ID", "test-twitter-id")
    monkeypatch.setenv("TWITTER_CLIENT_SECRET", "test-twitter-secret")
    connector, client = _make_connector_for_ordering(parent_mock)
    # No row in connected_accounts -- get_access_token returns None.

    _RecordingAsyncClient.parent = parent_mock

    with (
        patch("app.social.connector.httpx.AsyncClient", _RecordingAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt_id),
    ):
        result = await connector.disconnect_account("u1", "twitter")

    names = _ordered_call_names(parent_mock)
    assert "http_call" not in names, f"No HTTP must fire when no token; saw {names}"
    assert "db_call" in names, f"DB update must still fire; saw {names}"

    assert result["success"] is True


# ---------------------------------------------------------------------------
# Sync wrapper preserved
# ---------------------------------------------------------------------------


def test_revoke_connection_sync_wrapper_works(
    monkeypatch: pytest.MonkeyPatch, parent_mock: MagicMock
):
    monkeypatch.setenv("TWITTER_CLIENT_ID", "test-twitter-id")
    monkeypatch.setenv("TWITTER_CLIENT_SECRET", "test-twitter-secret")
    connector, client = _make_connector_for_ordering(parent_mock)
    _seed_active_account(client, "u1", "twitter")

    _RecordingAsyncClient.parent = parent_mock
    _RecordingAsyncClient.next_response = _MockResponse(status_code=200)

    with (
        patch("app.social.connector.httpx.AsyncClient", _RecordingAsyncClient),
        patch("app.social.connector.decrypt_secret", side_effect=_decrypt_id),
    ):
        result = connector.revoke_connection("u1", "twitter")  # sync call

    assert result["success"] is True
    assert result.get("platform") == "twitter"
    # Both http and db should have fired through the sync wrapper
    names = _ordered_call_names(parent_mock)
    assert "http_call" in names and "db_call" in names, names
    assert names.index("http_call") < names.index("db_call")
