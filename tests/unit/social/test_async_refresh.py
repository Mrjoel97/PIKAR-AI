# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Failing tests for async OAuth refresh path in SocialConnector.

These tests assert AUTH-05 invariants:

1. ``SocialConnector.get_access_token`` is a coroutine function and returns
   the decrypted access token for a non-expired row.
2. Five concurrent ``get_access_token`` calls for the same
   ``(user_id, platform)`` against an expired row fire EXACTLY ONE
   ``httpx.AsyncClient.post`` (per-key ``asyncio.Lock`` dedupes).
3. The refresh path does NOT block the event loop -- a parallel heartbeat
   counter advances during the in-flight refresh, proving
   ``httpx.AsyncClient`` actually yields control.

All tests fail today because ``get_access_token`` and ``_refresh_token``
in ``app.social.connector`` are synchronous and use ``httpx.Client``.
"""

from __future__ import annotations

import asyncio
import inspect
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import patch

import pytest

from app.social.connector import SocialConnector

# ---------------------------------------------------------------------------
# Minimal Supabase fakes -- only the connected_accounts shape we exercise.
# ---------------------------------------------------------------------------


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

    def select(self, _columns: str):
        self._operation = "select"
        return self

    def update(self, payload: dict[str, Any]):
        self._operation = "update"
        self._payload = payload
        return self

    def eq(self, column: str, value: Any):
        self._filters.append((column, value))
        return self

    def execute(self):
        if self.name != "connected_accounts":
            return _Result()
        if self._operation == "select":
            return _Result(list(self.client.connected_accounts))
        if self._operation == "update" and self._payload:
            self.client.connected_account_updates.append(dict(self._payload))
            # Mutate the seeded row in-place so subsequent selects see the
            # new expiry -- mirrors real Supabase update semantics.
            for row in self.client.connected_accounts:
                row.update(self._payload)
            return _Result(list(self.client.connected_accounts))
        return _Result()


class _FakeClient:
    def __init__(self):
        self.connected_accounts: list[dict[str, Any]] = []
        self.connected_account_updates: list[dict[str, Any]] = []

    def table(self, name: str):
        return _FakeTable(name, self)


def _make_connector(client: _FakeClient) -> SocialConnector:
    """Construct a connector without invoking the real Supabase singleton."""
    connector = SocialConnector.__new__(SocialConnector)
    connector.client = client
    # Preserve the (legacy) in-memory dict attribute so code paths that still
    # reference it during the migration window do not blow up.
    connector._pkce_verifiers = {}
    return connector


# ---------------------------------------------------------------------------
# Fake httpx.AsyncClient -- records calls and sleeps to expose blocking bugs.
# ---------------------------------------------------------------------------


def _make_fake_async_client(post_calls: list[dict[str, Any]], delay: float):
    """Return a class that patches ``httpx.AsyncClient``.

    Each ``.post`` call appends a record to ``post_calls`` and awaits
    ``asyncio.sleep(delay)`` so concurrency tests can exercise the lock.
    """

    class _Response:
        def __init__(self):
            self.status_code = 200
            self.text = ""

        def json(self):
            return {
                "access_token": "plain-new-access",
                "refresh_token": "plain-new-refresh",
                "expires_in": 3600,
            }

    class _AsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def post(self, url: str, data: dict[str, Any] | None = None, **_kw):
            post_calls.append({"url": url, "data": data})
            await asyncio.sleep(delay)
            return _Response()

    return _AsyncClient


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_access_token_is_awaitable_and_returns_decrypted_token():
    """get_access_token must be a coroutine and decrypt a non-expired token."""
    assert inspect.iscoroutinefunction(SocialConnector.get_access_token), (
        "SocialConnector.get_access_token must be `async def` after AUTH-05"
    )

    client = _FakeClient()
    client.connected_accounts = [
        {
            "user_id": "user-1",
            "platform": "linkedin",
            "status": "active",
            "access_token": "enc:tok",
            "refresh_token": "enc:refresh",
            "token_expires_at": (
                datetime.now(timezone.utc) + timedelta(minutes=30)
            ).isoformat(),
        }
    ]
    connector = _make_connector(client)

    with patch("app.social.connector.decrypt_secret", return_value="plain-tok"):
        result = await connector.get_access_token("user-1", "linkedin")

    assert result == "plain-tok"


@pytest.mark.asyncio
async def test_concurrent_refresh_uses_per_key_lock_single_http_post():
    """Five concurrent calls for an expired row must fire ONE refresh."""
    client = _FakeClient()
    client.connected_accounts = [
        {
            "user_id": "user-1",
            "platform": "linkedin",
            "status": "active",
            "access_token": "enc:old-access",
            "refresh_token": "enc:refresh",
            "token_expires_at": (
                datetime.now(timezone.utc) - timedelta(minutes=1)
            ).isoformat(),
        }
    ]
    connector = _make_connector(client)

    post_calls: list[dict[str, Any]] = []
    fake_client = _make_fake_async_client(post_calls, delay=0.5)

    # Reset class-level lock registry so the test is isolated.
    SocialConnector._refresh_locks = {}
    SocialConnector._locks_guard = None

    monkey_env = {
        "LINKEDIN_CLIENT_ID": "client-id",
        "LINKEDIN_CLIENT_SECRET": "client-secret",
    }

    with (
        patch.dict("os.environ", monkey_env, clear=False),
        patch("httpx.AsyncClient", fake_client),
        patch(
            "app.social.connector.decrypt_secret",
            side_effect=lambda v: (
                (v or "").removeprefix("enc:") if isinstance(v, str) else v
            ),
        ),
        patch(
            "app.social.connector.encrypt_secret",
            side_effect=lambda v: f"enc:{v}",
        ),
    ):
        results = await asyncio.gather(
            *[connector.get_access_token("user-1", "linkedin") for _ in range(5)]
        )

    assert len(post_calls) == 1, (
        f"Per-key Lock failed: expected 1 HTTP refresh, got {len(post_calls)}"
    )
    assert all(r == "plain-new-access" for r in results), (
        f"All concurrent callers must see the new token; got {results!r}"
    )


@pytest.mark.asyncio
async def test_refresh_does_not_block_event_loop():
    """A parallel task must keep ticking while the refresh is in flight."""
    client = _FakeClient()
    client.connected_accounts = [
        {
            "user_id": "user-2",
            "platform": "linkedin",
            "status": "active",
            "access_token": "enc:old-access",
            "refresh_token": "enc:refresh",
            "token_expires_at": (
                datetime.now(timezone.utc) - timedelta(minutes=1)
            ).isoformat(),
        }
    ]
    connector = _make_connector(client)

    post_calls: list[dict[str, Any]] = []
    # 1.0s delay during the refresh -- heartbeat ticks every 100ms.
    fake_client = _make_fake_async_client(post_calls, delay=1.0)

    SocialConnector._refresh_locks = {}
    SocialConnector._locks_guard = None

    heartbeat_count = 0
    stop_heartbeat = asyncio.Event()

    async def heartbeat():
        nonlocal heartbeat_count
        while not stop_heartbeat.is_set():
            heartbeat_count += 1
            try:
                await asyncio.wait_for(stop_heartbeat.wait(), timeout=0.1)
            except asyncio.TimeoutError:
                continue

    monkey_env = {
        "LINKEDIN_CLIENT_ID": "client-id",
        "LINKEDIN_CLIENT_SECRET": "client-secret",
    }

    with (
        patch.dict("os.environ", monkey_env, clear=False),
        patch("httpx.AsyncClient", fake_client),
        patch(
            "app.social.connector.decrypt_secret",
            side_effect=lambda v: (
                (v or "").removeprefix("enc:") if isinstance(v, str) else v
            ),
        ),
        patch(
            "app.social.connector.encrypt_secret",
            side_effect=lambda v: f"enc:{v}",
        ),
    ):
        hb_task = asyncio.create_task(heartbeat())
        try:
            token = await connector.get_access_token("user-2", "linkedin")
        finally:
            stop_heartbeat.set()
            await hb_task

    assert token == "plain-new-access"
    assert heartbeat_count >= 8, (
        f"Event loop appears blocked during refresh: heartbeat ticks={heartbeat_count} "
        "(expected >=8 for a 1s refresh with 100ms heartbeats)"
    )
