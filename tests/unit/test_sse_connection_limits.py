# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Async unit tests for Redis-backed SSE connection limits."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_redis_mock() -> AsyncMock:
    """Return an AsyncMock that behaves like a redis.asyncio.Redis client."""
    mock = AsyncMock()
    mock.incr = AsyncMock(return_value=1)
    mock.decr = AsyncMock(return_value=0)
    mock.get = AsyncMock(return_value=None)
    mock.expire = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.scan = AsyncMock(return_value=(0, []))
    # pipeline support
    pipeline_mock = AsyncMock()
    pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
    pipeline_mock.__aexit__ = AsyncMock(return_value=False)
    pipeline_mock.delete = MagicMock()
    pipeline_mock.execute = AsyncMock(return_value=[])
    mock.pipeline = MagicMock(return_value=pipeline_mock)
    return mock


@pytest.fixture(autouse=True)
def reset_env(monkeypatch):
    """Ensure SSE env vars start at known defaults for each test."""
    monkeypatch.delenv("SSE_MAX_CONNECTIONS_PER_USER", raising=False)
    monkeypatch.delenv("SSE_MAX_NEW_CONN_PER_MINUTE", raising=False)
    monkeypatch.delenv("SSE_MAX_TOTAL_CONNECTIONS", raising=False)
    monkeypatch.delenv("SSE_CONN_TTL_SECONDS", raising=False)


# ---------------------------------------------------------------------------
# Tests for try_acquire_sse_connection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_acquire_returns_true(monkeypatch):
    """First connection for a user is granted; count becomes 1."""
    monkeypatch.setenv("SSE_MAX_CONNECTIONS_PER_USER", "3")

    redis_mock = _make_redis_mock()
    # No existing count, INCR returns 1
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.incr = AsyncMock(return_value=1)
    # rate limiter: first INCR returns 1 (under limit)
    # We need separate mocks for rate vs conn keys — use side_effect
    incr_calls: list[str] = []

    async def incr_side(key):
        incr_calls.append(key)
        if "rate" in key:
            return 1  # first rate check
        return 1  # first conn acquire

    redis_mock.incr = AsyncMock(side_effect=incr_side)
    # total count scan returns 0
    redis_mock.scan = AsyncMock(return_value=(0, []))

    from app.services import sse_connection_limits

    with patch(
        "app.services.sse_connection_limits.get_cache_service"
    ) as mock_get_cache:
        cache = MagicMock()
        cache._ensure_connection = AsyncMock(return_value=redis_mock)
        mock_get_cache.return_value = cache

        result = await sse_connection_limits.try_acquire_sse_connection(
            "user-1", stream_name="chat"
        )

    assert result.acquired is True
    assert result.active == 1
    assert result.limit == 3
    assert result.reason is None


@pytest.mark.asyncio
async def test_second_acquire_returns_true_count_2(monkeypatch):
    """Second connection for a user is granted; count becomes 2."""
    monkeypatch.setenv("SSE_MAX_CONNECTIONS_PER_USER", "3")

    redis_mock = _make_redis_mock()
    # Existing count is 1; after INCR it becomes 2
    redis_mock.get = AsyncMock(return_value=b"1")
    redis_mock.scan = AsyncMock(return_value=(0, [b"pikar:sse:conn:user-2"]))
    redis_mock.get = AsyncMock(return_value=b"1")  # total check returns 1

    call_count = 0

    async def incr_side(key):
        nonlocal call_count
        call_count += 1
        if "rate" in key:
            return 1  # first rate call
        return 2  # second conn acquire

    redis_mock.incr = AsyncMock(side_effect=incr_side)

    from app.services import sse_connection_limits

    with patch(
        "app.services.sse_connection_limits.get_cache_service"
    ) as mock_get_cache:
        cache = MagicMock()
        cache._ensure_connection = AsyncMock(return_value=redis_mock)
        mock_get_cache.return_value = cache

        result = await sse_connection_limits.try_acquire_sse_connection(
            "user-2", stream_name="chat"
        )

    assert result.acquired is True
    assert result.active == 2
    assert result.limit == 3


@pytest.mark.asyncio
async def test_third_acquire_rejected_at_per_user_limit(monkeypatch):
    """Third connection is rejected when limit=3 and user already has 3 slots."""
    monkeypatch.setenv("SSE_MAX_CONNECTIONS_PER_USER", "3")

    redis_mock = _make_redis_mock()
    # Current count is at limit; total well under server cap
    redis_mock.scan = AsyncMock(return_value=(0, [b"pikar:sse:conn:user-3"]))

    async def get_side(key):
        if "conn" in key:
            return b"3"
        return None

    redis_mock.get = AsyncMock(side_effect=get_side)

    async def incr_side(key):
        if "rate" in key:
            return 1
        # conn INCR should NOT be called when count >= limit, but if it is, return 3
        return 3

    redis_mock.incr = AsyncMock(side_effect=incr_side)

    from app.services import sse_connection_limits

    with patch(
        "app.services.sse_connection_limits.get_cache_service"
    ) as mock_get_cache:
        cache = MagicMock()
        cache._ensure_connection = AsyncMock(return_value=redis_mock)
        mock_get_cache.return_value = cache

        result = await sse_connection_limits.try_acquire_sse_connection(
            "user-3", stream_name="chat"
        )

    assert result.acquired is False
    assert result.active == 3
    assert result.limit == 3
    from app.services.sse_connection_limits import SSERejectReason

    assert result.reason == SSERejectReason.PER_USER_LIMIT


@pytest.mark.asyncio
async def test_acquire_fails_open_when_redis_unavailable():
    """When Redis is down, try_acquire returns (True, 0, limit) — fail open."""
    from app.services import sse_connection_limits

    with patch(
        "app.services.sse_connection_limits.get_cache_service"
    ) as mock_get_cache:
        cache = MagicMock()
        cache._ensure_connection = AsyncMock(return_value=None)
        mock_get_cache.return_value = cache

        result = await sse_connection_limits.try_acquire_sse_connection(
            "user-failopen", stream_name="chat"
        )

    assert result.acquired is True
    assert result.active == 0


@pytest.mark.asyncio
async def test_server_backpressure_rejects_when_total_exceeds_threshold(monkeypatch):
    """Returns (False, ..., ...) with SERVER_BACKPRESSURE when total >= max."""
    monkeypatch.setenv("SSE_MAX_TOTAL_CONNECTIONS", "5")

    redis_mock = _make_redis_mock()
    # Return 5 conn keys each with value 1 → total = 5
    redis_mock.scan = AsyncMock(
        return_value=(
            0,
            [
                b"pikar:sse:conn:u1",
                b"pikar:sse:conn:u2",
                b"pikar:sse:conn:u3",
                b"pikar:sse:conn:u4",
                b"pikar:sse:conn:u5",
            ],
        )
    )

    async def get_side(key):
        return b"1"

    redis_mock.get = AsyncMock(side_effect=get_side)

    from app.services import sse_connection_limits
    from app.services.sse_connection_limits import SSERejectReason

    with patch(
        "app.services.sse_connection_limits.get_cache_service"
    ) as mock_get_cache:
        cache = MagicMock()
        cache._ensure_connection = AsyncMock(return_value=redis_mock)
        mock_get_cache.return_value = cache

        result = await sse_connection_limits.try_acquire_sse_connection(
            "user-bp", stream_name="chat"
        )

    assert result.acquired is False
    assert result.reason == SSERejectReason.SERVER_BACKPRESSURE


@pytest.mark.asyncio
async def test_per_user_rate_limit_rejects_excess_new_connections(monkeypatch):
    """Rejects (False, ...) with PER_USER_RATE when rate > SSE_MAX_NEW_CONN_PER_MINUTE."""
    monkeypatch.setenv("SSE_MAX_NEW_CONN_PER_MINUTE", "5")

    redis_mock = _make_redis_mock()
    # total count = 0 (no backpressure)
    redis_mock.scan = AsyncMock(return_value=(0, []))

    async def incr_side(key):
        if "rate" in key:
            return 6  # exceeded rate limit
        return 1

    redis_mock.incr = AsyncMock(side_effect=incr_side)

    from app.services import sse_connection_limits
    from app.services.sse_connection_limits import SSERejectReason

    with patch(
        "app.services.sse_connection_limits.get_cache_service"
    ) as mock_get_cache:
        cache = MagicMock()
        cache._ensure_connection = AsyncMock(return_value=redis_mock)
        mock_get_cache.return_value = cache

        result = await sse_connection_limits.try_acquire_sse_connection(
            "user-rate", stream_name="chat"
        )

    assert result.acquired is False
    assert result.reason == SSERejectReason.PER_USER_RATE


# ---------------------------------------------------------------------------
# Tests for release_sse_connection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_release_decrements_counter():
    """release_sse_connection decrements the Redis counter."""
    redis_mock = _make_redis_mock()
    redis_mock.decr = AsyncMock(return_value=1)

    from app.services import sse_connection_limits

    with patch(
        "app.services.sse_connection_limits.get_cache_service"
    ) as mock_get_cache:
        cache = MagicMock()
        cache._ensure_connection = AsyncMock(return_value=redis_mock)
        mock_get_cache.return_value = cache

        remaining = await sse_connection_limits.release_sse_connection(
            "user-rel", stream_name="chat"
        )

    assert remaining == 1
    redis_mock.decr.assert_called_once()


@pytest.mark.asyncio
async def test_release_deletes_key_when_count_reaches_zero():
    """When count reaches 0, the Redis key is deleted."""
    redis_mock = _make_redis_mock()
    redis_mock.decr = AsyncMock(return_value=0)

    from app.services import sse_connection_limits

    with patch(
        "app.services.sse_connection_limits.get_cache_service"
    ) as mock_get_cache:
        cache = MagicMock()
        cache._ensure_connection = AsyncMock(return_value=redis_mock)
        mock_get_cache.return_value = cache

        remaining = await sse_connection_limits.release_sse_connection(
            "user-del", stream_name="chat"
        )

    assert remaining == 0
    redis_mock.delete.assert_called_once()


@pytest.mark.asyncio
async def test_release_fails_open_when_redis_unavailable():
    """release returns 0 gracefully when Redis is down."""
    from app.services import sse_connection_limits

    with patch(
        "app.services.sse_connection_limits.get_cache_service"
    ) as mock_get_cache:
        cache = MagicMock()
        cache._ensure_connection = AsyncMock(return_value=None)
        mock_get_cache.return_value = cache

        remaining = await sse_connection_limits.release_sse_connection(
            "user-down", stream_name="chat"
        )

    assert remaining == 0


# ---------------------------------------------------------------------------
# Tests for get_total_active_sse_count
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_total_active_sse_count_sums_all_values():
    """get_total_active_sse_count sums all pikar:sse:conn:* key values."""
    redis_mock = _make_redis_mock()
    redis_mock.scan = AsyncMock(
        return_value=(
            0,
            [b"pikar:sse:conn:userA", b"pikar:sse:conn:userB"],
        )
    )

    get_responses = {
        b"pikar:sse:conn:userA": b"2",
        b"pikar:sse:conn:userB": b"3",
    }

    async def get_side(key):
        return get_responses.get(key)

    redis_mock.get = AsyncMock(side_effect=get_side)

    from app.services import sse_connection_limits

    with patch(
        "app.services.sse_connection_limits.get_cache_service"
    ) as mock_get_cache:
        cache = MagicMock()
        cache._ensure_connection = AsyncMock(return_value=redis_mock)
        mock_get_cache.return_value = cache

        total = await sse_connection_limits.get_total_active_sse_count()

    assert total == 5


@pytest.mark.asyncio
async def test_get_total_active_sse_count_returns_zero_when_redis_down():
    """Returns 0 when Redis is unavailable."""
    from app.services import sse_connection_limits

    with patch(
        "app.services.sse_connection_limits.get_cache_service"
    ) as mock_get_cache:
        cache = MagicMock()
        cache._ensure_connection = AsyncMock(return_value=None)
        mock_get_cache.return_value = cache

        total = await sse_connection_limits.get_total_active_sse_count()

    assert total == 0


# ---------------------------------------------------------------------------
# Tests for reset_sse_connection_limits (test helper)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_deletes_all_sse_keys():
    """reset_sse_connection_limits deletes all pikar:sse:* keys."""
    redis_mock = _make_redis_mock()
    redis_mock.scan = AsyncMock(
        return_value=(0, [b"pikar:sse:conn:u1", b"pikar:sse:rate:u1"])
    )

    from app.services import sse_connection_limits

    with patch(
        "app.services.sse_connection_limits.get_cache_service"
    ) as mock_get_cache:
        cache = MagicMock()
        cache._ensure_connection = AsyncMock(return_value=redis_mock)
        mock_get_cache.return_value = cache

        await sse_connection_limits.reset_sse_connection_limits()

    # Pipeline delete should have been called
    pipeline_mock = redis_mock.pipeline.return_value
    assert pipeline_mock.delete.called


# ---------------------------------------------------------------------------
# Tests for get_sse_connection_limit (sync, env-driven)
# ---------------------------------------------------------------------------


def test_get_sse_connection_limit_default():
    """Returns default 3 when env var is not set."""
    from app.services.sse_connection_limits import get_sse_connection_limit

    assert get_sse_connection_limit() == 3


def test_get_sse_connection_limit_from_env(monkeypatch):
    """Returns the configured value from env."""
    monkeypatch.setenv("SSE_MAX_CONNECTIONS_PER_USER", "10")
    from app.services.sse_connection_limits import get_sse_connection_limit

    assert get_sse_connection_limit() == 10


def test_get_sse_connection_limit_invalid_falls_back_to_default(monkeypatch):
    """Falls back to default 3 on invalid env var."""
    monkeypatch.setenv("SSE_MAX_CONNECTIONS_PER_USER", "not_a_number")
    from app.services.sse_connection_limits import get_sse_connection_limit

    assert get_sse_connection_limit() == 3


# ---------------------------------------------------------------------------
# Backward compat: tuple unpacking still works
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_result_is_tuple_unpackable():
    """SSEAcquireResult can be unpacked as (acquired, active, limit)."""
    redis_mock = _make_redis_mock()
    redis_mock.scan = AsyncMock(return_value=(0, []))

    async def incr_side(key):
        if "rate" in key:
            return 1
        return 1

    redis_mock.incr = AsyncMock(side_effect=incr_side)
    redis_mock.get = AsyncMock(return_value=None)

    from app.services import sse_connection_limits

    with patch(
        "app.services.sse_connection_limits.get_cache_service"
    ) as mock_get_cache:
        cache = MagicMock()
        cache._ensure_connection = AsyncMock(return_value=redis_mock)
        mock_get_cache.return_value = cache

        acquired, active, limit = await sse_connection_limits.try_acquire_sse_connection(
            "user-compat", stream_name="chat"
        )

    assert acquired is True
    assert active == 1
    assert limit == 3
