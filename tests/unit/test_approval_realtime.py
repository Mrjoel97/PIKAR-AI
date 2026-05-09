# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for Realtime-push upgrade to ``wait_for_approval``.

These tests prove that:

- Test 1: when Supabase Realtime delivers an UPDATE event with a terminal
  status, ``wait_for_approval`` returns the decision in well under one
  polling interval (target: <500ms vs. the 3s polling floor) — proving the
  wait is push-based, not poll-based.
- Test 2: when the Realtime subscription raises on ``subscribe()``, the
  helper falls back to the polling arm and still produces the correct
  decision — Realtime errors must never break the wait.
- Test 3: when Realtime fires first, the polling task is cancelled cleanly
  and no orphaned tasks linger after ``wait_for_approval`` returns.

The Wave 4 polling-only tests in ``tests/unit/test_approval_resume.py``
are unchanged and MUST keep passing alongside these.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any, Callable
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Stubs that mimic the chained Supabase query builder (sync client) used by
# the polling + precheck path. Same shape as test_approval_resume.py.
# ---------------------------------------------------------------------------


class _StubResponse:
    def __init__(self, data: dict[str, Any] | None) -> None:
        self.data = data


class _StubQuery:
    def __init__(self, parent: "_StubSupabase") -> None:
        self._parent = parent

    def select(self, *_args: Any, **_kwargs: Any) -> "_StubQuery":
        return self

    def eq(self, *_args: Any, **_kwargs: Any) -> "_StubQuery":
        return self

    def single(self) -> "_StubQuery":
        return self

    def execute(self) -> _StubResponse:
        self._parent.poll_count += 1
        return _StubResponse(self._parent.row)


class _StubSupabase:
    def __init__(self, initial_row: dict[str, Any] | None) -> None:
        self.row = initial_row
        self.poll_count = 0

    def table(self, _name: str) -> _StubQuery:
        return _StubQuery(self)


# ---------------------------------------------------------------------------
# Realtime channel stubs. The async client + channel are wired so a test
# can grab the registered ``on_postgres_changes`` callback and fire it
# manually to simulate Supabase pushing an UPDATE event over the WebSocket.
# ---------------------------------------------------------------------------


class _StubChannel:
    def __init__(self, fail_subscribe: bool = False) -> None:
        self._fail_subscribe = fail_subscribe
        self.callback: Callable[[dict[str, Any]], None] | None = None
        self.subscribed = False
        self.unsubscribed = False
        # Set by ``on_postgres_changes`` for inspection
        self.last_filter: str | None = None
        self.last_event: str | None = None
        self.last_table: str | None = None

    def on_postgres_changes(
        self,
        event: str,
        callback: Callable[[dict[str, Any]], None],
        table: str | None = None,
        schema: str | None = None,
        filter: str | None = None,  # noqa: A002 — match SDK signature
    ) -> "_StubChannel":
        self.last_event = event
        self.last_table = table
        self.last_filter = filter
        self.callback = callback
        return self

    async def subscribe(self) -> "_StubChannel":
        if self._fail_subscribe:
            raise RuntimeError("simulated WebSocket connect failure")
        self.subscribed = True
        return self

    async def unsubscribe(self) -> None:
        self.unsubscribed = True


class _StubAsyncClient:
    def __init__(self, channel: _StubChannel) -> None:
        self._channel = channel
        self.channel_calls: list[str] = []

    def channel(self, name: str) -> _StubChannel:
        self.channel_calls.append(name)
        return self._channel


class _StubAsyncService:
    def __init__(self, async_client: _StubAsyncClient) -> None:
        self.client = async_client


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Test 1 — Realtime push delivers the decision in <500ms.
# Proves: wait_for_approval is push-based, not 3s polling.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wait_for_approval_resolves_via_realtime_push() -> None:
    from app.agents.tools import approval_tool

    token = "tkn_realtime_push"
    token_hash = _hash(token)
    # Polling stub stays PENDING the whole time so we know the result MUST
    # have come from the realtime callback firing (not a poll hit).
    stub = _StubSupabase({"status": "PENDING", "responded_at": None, "payload": {}})
    channel = _StubChannel()
    async_client = _StubAsyncClient(channel)
    service = _StubAsyncService(async_client)

    async def _fake_get_async_service() -> _StubAsyncService:
        return service

    async def _push_decision_after(delay: float) -> None:
        # Simulate Supabase pushing the UPDATE event over the WebSocket.
        await asyncio.sleep(delay)
        assert channel.callback is not None, "callback must be registered first"
        channel.callback(
            {
                "data": {
                    "record": {
                        "status": "APPROVED",
                        "responded_at": "2026-05-09T13:00:00+00:00",
                        "payload": {"decided_by": "user-realtime"},
                        "token": token_hash,
                    }
                }
            }
        )

    # Patch the lazy import inside _wait_via_realtime so we don't need
    # SUPABASE_URL / WebSocket access in the test runner.
    with patch.object(approval_tool, "get_service_client", return_value=stub), patch(
        "app.services.supabase_client.get_async_service",
        new=_fake_get_async_service,
    ):
        pusher = asyncio.create_task(_push_decision_after(0.05))
        start = time.monotonic()
        # poll_interval_s=3 (the default Wave 4 floor) — proves we're NOT
        # waiting on a poll: with polling-only this would take 3s.
        result = await approval_tool.wait_for_approval(
            token, timeout_s=2, poll_interval_s=3
        )
        elapsed = time.monotonic() - start
        await pusher

    assert result["decision"] == "approve"
    assert result["token"] == token
    assert result["status"] == "APPROVED"
    assert result["decided_at"] == "2026-05-09T13:00:00+00:00"
    assert result["decided_by"] == "user-realtime"
    # Push-based: decision propagation must beat the 3s polling floor.
    assert elapsed < 0.5, (
        f"realtime should resolve in <500ms, got {elapsed:.3f}s "
        "— wait_for_approval is still polling"
    )
    # Sanity: the channel was subscribed and torn down cleanly.
    assert channel.subscribed is True
    assert channel.unsubscribed is True
    # And the filter we registered actually targets this token's row.
    assert channel.last_event == "UPDATE"
    assert channel.last_table == "approval_requests"
    assert channel.last_filter == f"token=eq.{token_hash}"


# ---------------------------------------------------------------------------
# Test 2 — Realtime subscribe failure falls back to polling.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wait_for_approval_falls_back_to_polling_when_realtime_errors() -> None:
    from app.agents.tools import approval_tool

    token = "tkn_realtime_broken"
    stub = _StubSupabase({"status": "PENDING", "responded_at": None, "payload": {}})
    channel = _StubChannel(fail_subscribe=True)
    async_client = _StubAsyncClient(channel)
    service = _StubAsyncService(async_client)

    async def _fake_get_async_service() -> _StubAsyncService:
        return service

    async def _flip_to_approved() -> None:
        # Give the realtime arm a beat to fail and the polling arm to start.
        await asyncio.sleep(0.15)
        stub.row = {
            "status": "APPROVED",
            "responded_at": "2026-05-09T13:05:00+00:00",
            "payload": {"decided_by": "user-fallback"},
        }

    with patch.object(approval_tool, "get_service_client", return_value=stub), patch(
        "app.services.supabase_client.get_async_service",
        new=_fake_get_async_service,
    ):
        flipper = asyncio.create_task(_flip_to_approved())
        result = await approval_tool.wait_for_approval(
            token, timeout_s=2, poll_interval_s=0.05
        )
        await flipper

    # Same correct result, just via the fallback path.
    assert result["decision"] == "approve"
    assert result["token"] == token
    assert result["status"] == "APPROVED"
    assert result["decided_by"] == "user-fallback"
    # Realtime arm must have at least attempted to subscribe.
    assert channel.subscribed is False, "subscribe was patched to raise"
    # Polling arm did real work (precheck + at least one poll past the flip).
    assert stub.poll_count >= 2


# ---------------------------------------------------------------------------
# Test 3 — Realtime wins; polling task is cancelled cleanly (no orphans).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wait_for_approval_cancels_polling_when_realtime_wins() -> None:
    from app.agents.tools import approval_tool

    token = "tkn_race_cleanup"
    token_hash = _hash(token)
    stub = _StubSupabase({"status": "PENDING", "responded_at": None, "payload": {}})
    channel = _StubChannel()
    async_client = _StubAsyncClient(channel)
    service = _StubAsyncService(async_client)

    async def _fake_get_async_service() -> _StubAsyncService:
        return service

    async def _push_quickly() -> None:
        # Fire well before the polling arm's first sleep would even elapse.
        await asyncio.sleep(0.05)
        assert channel.callback is not None
        channel.callback(
            {
                "data": {
                    "record": {
                        "status": "REJECTED",
                        "responded_at": "2026-05-09T13:10:00+00:00",
                        "payload": {"decided_by": "user-race"},
                        "token": token_hash,
                    }
                }
            }
        )

    # Snapshot the task set BEFORE the call so we can diff after.
    pre_tasks = {t for t in asyncio.all_tasks() if not t.done()}

    with patch.object(approval_tool, "get_service_client", return_value=stub), patch(
        "app.services.supabase_client.get_async_service",
        new=_fake_get_async_service,
    ):
        pusher = asyncio.create_task(_push_quickly())
        result = await approval_tool.wait_for_approval(
            # Long polling interval so any leaked polling task would clearly
            # show up as a still-running asyncio.sleep(5).
            token,
            timeout_s=10,
            poll_interval_s=5,
        )
        await pusher

    assert result["decision"] == "reject"
    assert result["token"] == token
    # Yield to give cancelled tasks a tick to clean up.
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    # No leaked tasks from wait_for_approval should still be running.
    leaked = {
        t
        for t in asyncio.all_tasks()
        if not t.done() and t not in pre_tasks
        # ignore the current test task itself
        and t is not asyncio.current_task()
    }
    leaked_names = [t.get_name() for t in leaked]
    assert not leaked, f"orphaned tasks after race resolution: {leaked_names}"
    # And the realtime channel was unsubscribed.
    assert channel.unsubscribed is True
