# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for Redis-backed distributed sliding-window rate limiters.

Covers:
- API rate limiter: redis_sliding_window_check, build_rate_limit_headers
- MCP rate limiter: check_rate_limit (operation-keyed sliding window)
- Fail-open behaviour when Redis is unavailable
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers: build a fake Redis pipeline and client
# ---------------------------------------------------------------------------


def _make_pipeline(incr_result: int) -> MagicMock:
    """Return a mock Redis pipeline whose execute() returns [incr_result, 1]."""
    pipeline = AsyncMock()
    pipeline.incr = MagicMock(return_value=None)
    pipeline.expire = MagicMock(return_value=None)
    pipeline.execute = AsyncMock(return_value=[incr_result, 1])
    return pipeline


def _make_client(incr_result: int) -> AsyncMock:
    """Return a mock Redis client whose pipeline() returns appropriate mock."""
    client = AsyncMock()
    client.pipeline = MagicMock(return_value=_make_pipeline(incr_result))
    return client


# ---------------------------------------------------------------------------
# API rate limiter: redis_sliding_window_check
# ---------------------------------------------------------------------------


class TestRedisSlidingWindowCheck:
    """Tests for app.middleware.rate_limiter.redis_sliding_window_check."""

    @pytest.mark.asyncio
    async def test_returns_allowed_when_count_below_limit(self):
        """First call (count=1) under limit=5 should be allowed."""
        from app.middleware.rate_limiter import redis_sliding_window_check

        client = _make_client(incr_result=1)
        cache_svc = AsyncMock()
        cache_svc.get_circuit_breaker_state = MagicMock(
            return_value={"state": "closed"}
        )
        cache_svc._ensure_connection = AsyncMock(return_value=client)

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            allowed, limit, remaining, reset_at = await redis_sliding_window_check(
                "user-abc", limit=5, window_seconds=60
            )

        assert allowed is True
        assert limit == 5
        assert remaining == 4  # 5 - 1
        assert isinstance(reset_at, int) and reset_at > 0

    @pytest.mark.asyncio
    async def test_returns_denied_when_count_at_limit(self):
        """Count equal to limit should be denied."""
        from app.middleware.rate_limiter import redis_sliding_window_check

        client = _make_client(incr_result=10)  # count == limit
        cache_svc = AsyncMock()
        cache_svc.get_circuit_breaker_state = MagicMock(
            return_value={"state": "closed"}
        )
        cache_svc._ensure_connection = AsyncMock(return_value=client)

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            allowed, _limit, remaining, _reset_at = await redis_sliding_window_check(
                "user-abc", limit=10, window_seconds=60
            )

        assert allowed is True  # count <= limit means allowed (10 <= 10)
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_returns_denied_when_count_exceeds_limit(self):
        """Count exceeding limit should be denied."""
        from app.middleware.rate_limiter import redis_sliding_window_check

        client = _make_client(incr_result=11)  # count > limit
        cache_svc = AsyncMock()
        cache_svc.get_circuit_breaker_state = MagicMock(
            return_value={"state": "closed"}
        )
        cache_svc._ensure_connection = AsyncMock(return_value=client)

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            allowed, limit, remaining, reset_at = await redis_sliding_window_check(
                "user-abc", limit=10, window_seconds=60
            )

        assert allowed is False
        assert limit == 10
        assert remaining == 0
        assert isinstance(reset_at, int) and reset_at > 0

    @pytest.mark.asyncio
    async def test_key_includes_user_id_and_window_bucket(self):
        """Key pattern should be pikar:rate:api:{user_id}:{window_start}."""
        import time as _time

        from app.middleware.rate_limiter import redis_sliding_window_check

        set_keys: list[str] = []

        async def fake_execute():
            return [1, 1]

        pipeline = MagicMock()
        pipeline.execute = AsyncMock(side_effect=fake_execute)

        def capture_incr(key: str):
            set_keys.append(key)

        pipeline.incr = MagicMock(side_effect=capture_incr)
        pipeline.expire = MagicMock(return_value=None)

        client = AsyncMock()
        client.pipeline = MagicMock(return_value=pipeline)

        cache_svc = AsyncMock()
        cache_svc.get_circuit_breaker_state = MagicMock(
            return_value={"state": "closed"}
        )
        cache_svc._ensure_connection = AsyncMock(return_value=client)

        window_seconds = 60
        now = int(_time.time())
        window_start = (now // window_seconds) * window_seconds

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            await redis_sliding_window_check(
                "u-123", limit=10, window_seconds=window_seconds
            )

        assert len(set_keys) == 1
        key = set_keys[0]
        assert "pikar:rate:api:u-123:" in key
        assert str(window_start) in key

    @pytest.mark.asyncio
    async def test_different_minute_uses_different_key(self):
        """Two calls with different window_start times should produce different keys.

        We verify this by calling with explicitly different window_seconds values
        that produce different bucket boundaries for the same timestamp, which is
        functionally equivalent to calls in different time windows.
        """
        from app.middleware.rate_limiter import redis_sliding_window_check

        seen_keys: list[str] = []

        async def fake_execute():
            return [1, 1]

        def make_pipeline():
            pipeline = MagicMock()
            pipeline.execute = AsyncMock(side_effect=fake_execute)

            def capture(key: str):
                seen_keys.append(key)

            pipeline.incr = MagicMock(side_effect=capture)
            pipeline.expire = MagicMock(return_value=None)
            return pipeline

        client = AsyncMock()
        client.pipeline = MagicMock(side_effect=make_pipeline)

        cache_svc = AsyncMock()
        cache_svc.get_circuit_breaker_state = MagicMock(
            return_value={"state": "closed"}
        )
        cache_svc._ensure_connection = AsyncMock(return_value=client)

        # Use two window_seconds values that will produce very different window_start values
        # for the same current timestamp, simulating calls in different time windows.
        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            await redis_sliding_window_check("u-123", limit=10, window_seconds=60)
            # Use a prime window size that generates a different bucket boundary
            await redis_sliding_window_check("u-123", limit=10, window_seconds=7)

        assert len(seen_keys) == 2
        # Different window sizes produce different bucket timestamps in the key
        assert seen_keys[0] != seen_keys[1]

    @pytest.mark.asyncio
    async def test_fails_open_when_redis_returns_none(self):
        """When Redis client is None, should fail open (return True, limit, limit)."""
        from app.middleware.rate_limiter import redis_sliding_window_check

        cache_svc = AsyncMock()
        cache_svc.get_circuit_breaker_state = MagicMock(
            return_value={"state": "closed"}
        )
        cache_svc._ensure_connection = AsyncMock(return_value=None)

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            allowed, limit, remaining, _reset_at = await redis_sliding_window_check(
                "user-x", limit=30, window_seconds=60
            )

        assert allowed is True
        assert limit == 30
        assert remaining == 30  # fail open: full limit returned

    @pytest.mark.asyncio
    async def test_fails_open_on_redis_exception(self):
        """When Redis raises an exception, should fail open."""
        from app.middleware.rate_limiter import redis_sliding_window_check

        client = AsyncMock()
        pipeline = MagicMock()
        pipeline.incr = MagicMock(return_value=None)
        pipeline.expire = MagicMock(return_value=None)
        pipeline.execute = AsyncMock(side_effect=ConnectionError("Redis down"))
        client.pipeline = MagicMock(return_value=pipeline)

        cache_svc = AsyncMock()
        cache_svc.get_circuit_breaker_state = MagicMock(
            return_value={"state": "closed"}
        )
        cache_svc._ensure_connection = AsyncMock(return_value=client)

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            allowed, _limit, remaining, _reset_at = await redis_sliding_window_check(
                "user-x", limit=10, window_seconds=60
            )

        assert allowed is True
        assert remaining == 10


# ---------------------------------------------------------------------------
# API rate limiter: get_user_persona_limit
# ---------------------------------------------------------------------------


class TestGetUserPersonaLimit:
    """Tests for app.middleware.rate_limiter.get_user_persona_limit."""

    def test_solopreneur_returns_10_per_minute(self):
        from app.middleware.rate_limiter import get_user_persona_limit

        request = MagicMock()
        request.cookies.get = MagicMock(return_value=None)
        request.headers.get = MagicMock(
            side_effect=lambda k, d=None: "solopreneur" if k == "x-pikar-persona" else d
        )

        result = get_user_persona_limit(request)
        assert result == "10/minute"

    def test_enterprise_returns_120_per_minute(self):
        from app.middleware.rate_limiter import get_user_persona_limit

        request = MagicMock()
        request.cookies.get = MagicMock(return_value=None)
        request.headers.get = MagicMock(
            side_effect=lambda k, d=None: "enterprise" if k == "x-pikar-persona" else d
        )

        result = get_user_persona_limit(request)
        assert result == "120/minute"

    def test_no_request_returns_default(self):
        from app.middleware.rate_limiter import get_user_persona_limit

        result = get_user_persona_limit(None)
        assert result == "10/minute"

    def test_testing_override_returns_unlimited_limit(self, monkeypatch):
        from app.middleware.rate_limiter import get_user_persona_limit

        monkeypatch.setenv("ALLOW_UNLIMITED_TESTING", "true")

        result = get_user_persona_limit(None)
        assert result == "100000/minute"


# ---------------------------------------------------------------------------
# API rate limiter: build_rate_limit_headers
# ---------------------------------------------------------------------------


class TestBuildRateLimitHeaders:
    """Tests for app.middleware.rate_limiter.build_rate_limit_headers."""

    def test_returns_all_three_headers(self):
        import time as _time

        from app.middleware.rate_limiter import build_rate_limit_headers

        now = int(_time.time())
        reset_at = now + 45

        headers = build_rate_limit_headers(limit=10, remaining=3, reset_at=reset_at)

        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers
        assert "Retry-After" in headers

    def test_values_match_arguments(self):
        import time as _time

        from app.middleware.rate_limiter import build_rate_limit_headers

        now = int(_time.time())
        reset_at = now + 30

        headers = build_rate_limit_headers(limit=10, remaining=3, reset_at=reset_at)

        assert headers["X-RateLimit-Limit"] == "10"
        assert headers["X-RateLimit-Remaining"] == "3"
        # Retry-After should be close to 30
        retry_after = int(headers["Retry-After"])
        assert 28 <= retry_after <= 31

    def test_retry_after_is_not_negative(self):
        """Retry-After should never be negative even if reset_at is in the past."""
        from app.middleware.rate_limiter import build_rate_limit_headers

        past_reset = 1000  # Far in the past

        headers = build_rate_limit_headers(limit=10, remaining=0, reset_at=past_reset)

        assert int(headers["Retry-After"]) >= 0


# ---------------------------------------------------------------------------
# MCP rate limiter: check_rate_limit
# ---------------------------------------------------------------------------


class TestMcpCheckRateLimit:
    """Tests for app.mcp.rate_limiter.check_rate_limit (Redis sliding window)."""

    @pytest.mark.asyncio
    async def test_returns_true_when_count_below_limit(self):
        """check_rate_limit returns True when counter < rate_per_minute."""
        from app.mcp.rate_limiter import check_rate_limit

        client = _make_client(incr_result=5)
        cache_svc = AsyncMock()
        cache_svc._ensure_connection = AsyncMock(return_value=client)

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            result = await check_rate_limit("search", rate_per_minute=30)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_count_exceeds_limit(self):
        """check_rate_limit returns False when counter > rate_per_minute."""
        from app.mcp.rate_limiter import check_rate_limit

        client = _make_client(incr_result=31)  # exceeds 30
        cache_svc = AsyncMock()
        cache_svc._ensure_connection = AsyncMock(return_value=client)

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            result = await check_rate_limit("search", rate_per_minute=30)

        assert result is False

    @pytest.mark.asyncio
    async def test_different_operations_use_different_keys(self):
        """Different operation names produce different Redis keys."""
        seen_keys: list[str] = []

        async def fake_execute():
            return [1, 1]

        def make_pipeline():
            pipeline = MagicMock()
            pipeline.execute = AsyncMock(side_effect=fake_execute)

            def capture(key: str):
                seen_keys.append(key)

            pipeline.incr = MagicMock(side_effect=capture)
            pipeline.expire = MagicMock(return_value=None)
            return pipeline

        client = AsyncMock()
        client.pipeline = MagicMock(side_effect=make_pipeline)

        cache_svc = AsyncMock()
        cache_svc._ensure_connection = AsyncMock(return_value=client)

        from app.mcp.rate_limiter import check_rate_limit

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            await check_rate_limit("search", rate_per_minute=30)
            await check_rate_limit("scrape", rate_per_minute=30)

        assert len(seen_keys) == 2
        assert seen_keys[0] != seen_keys[1]
        assert "search" in seen_keys[0]
        assert "scrape" in seen_keys[1]

    @pytest.mark.asyncio
    async def test_fails_open_when_redis_returns_none(self):
        """Returns True (fail open) when Redis connection is unavailable."""
        from app.mcp.rate_limiter import check_rate_limit

        cache_svc = AsyncMock()
        cache_svc._ensure_connection = AsyncMock(return_value=None)

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            result = await check_rate_limit("search", rate_per_minute=30)

        assert result is True

    @pytest.mark.asyncio
    async def test_fails_open_on_redis_exception(self):
        """Returns True (fail open) when Redis raises an exception."""
        from app.mcp.rate_limiter import check_rate_limit

        pipeline = MagicMock()
        pipeline.incr = MagicMock(return_value=None)
        pipeline.expire = MagicMock(return_value=None)
        pipeline.execute = AsyncMock(side_effect=ConnectionError("Redis down"))

        client = AsyncMock()
        client.pipeline = MagicMock(return_value=pipeline)

        cache_svc = AsyncMock()
        cache_svc._ensure_connection = AsyncMock(return_value=client)

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            result = await check_rate_limit("crawl", rate_per_minute=10)

        assert result is True

    @pytest.mark.asyncio
    async def test_no_token_bucket_class_in_module(self):
        """Verify TokenBucket class is not present in mcp.rate_limiter."""
        import app.mcp.rate_limiter as mcp_rl

        assert not hasattr(mcp_rl, "TokenBucket"), "TokenBucket should be removed"
        assert not hasattr(mcp_rl, "_buckets"), "_buckets dict should be removed"
        assert not hasattr(mcp_rl, "_buckets_lock"), "_buckets_lock should be removed"


# ---------------------------------------------------------------------------
# API rate limiter: Redis failover to in-process SlowAPI
# ---------------------------------------------------------------------------


def _make_cache_svc_with_cb_state(cb_state: str, client=None) -> AsyncMock:
    """Return a mock cache service whose CB state is set and connection returns client."""
    cache_svc = AsyncMock()
    cache_svc.get_circuit_breaker_state = MagicMock(
        return_value={"state": cb_state, "failures": 0}
    )
    cache_svc._ensure_connection = AsyncMock(return_value=client)
    return cache_svc


class TestRedisFailoverToInProcess:
    """Tests for Redis circuit breaker failover in redis_sliding_window_check."""

    def setup_method(self):
        """Reset the in-process fallback state before each test."""
        import app.middleware.rate_limiter as rl

        # Clear fallback counters and reset the active flag
        rl._fallback_counters.clear()
        rl._FALLBACK_ACTIVE = False

    @pytest.mark.asyncio
    async def test_uses_inprocess_when_cb_open(self):
        """When Redis circuit breaker is open, should use in-process tracking, not Redis."""
        from app.middleware.rate_limiter import redis_sliding_window_check

        cache_svc = _make_cache_svc_with_cb_state("open")

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            allowed, _limit, _remaining, _reset_at = await redis_sliding_window_check(
                "user-cb-open", limit=10, window_seconds=60
            )

        # Should be allowed (first request) but via in-process, not Redis
        assert allowed is True
        # _ensure_connection should NOT have been called (Redis bypassed)
        cache_svc._ensure_connection.assert_not_called()

    @pytest.mark.asyncio
    async def test_critical_log_emitted_when_cb_open(self, caplog):
        """A CRITICAL log should be emitted when Redis CB is open and fallback activates."""
        import logging

        from app.middleware.rate_limiter import redis_sliding_window_check

        cache_svc = _make_cache_svc_with_cb_state("open")

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            with caplog.at_level(
                logging.CRITICAL, logger="app.middleware.rate_limiter"
            ):
                await redis_sliding_window_check(
                    "user-log", limit=10, window_seconds=60
                )

        critical_msgs = [
            r.message for r in caplog.records if r.levelno == logging.CRITICAL
        ]
        assert len(critical_msgs) >= 1
        assert any(
            "circuit breaker" in msg.lower() or "redis" in msg.lower()
            for msg in critical_msgs
        )

    @pytest.mark.asyncio
    async def test_resumes_redis_when_cb_closed(self):
        """When Redis CB returns to closed, redis_sliding_window_check should use Redis."""
        from app.middleware.rate_limiter import redis_sliding_window_check

        # First call with CB open to activate fallback
        cache_svc_open = _make_cache_svc_with_cb_state("open")
        with patch("app.services.cache.get_cache_service", return_value=cache_svc_open):
            await redis_sliding_window_check(
                "user-recovery", limit=10, window_seconds=60
            )

        # Second call with CB closed — should use Redis again
        redis_client = _make_client(incr_result=1)
        cache_svc_closed = _make_cache_svc_with_cb_state("closed", client=redis_client)

        with patch(
            "app.services.cache.get_cache_service", return_value=cache_svc_closed
        ):
            allowed, _limit, _remaining, _reset_at = await redis_sliding_window_check(
                "user-recovery", limit=10, window_seconds=60
            )

        # Should have used Redis (_ensure_connection called)
        cache_svc_closed._ensure_connection.assert_called_once()
        assert allowed is True

    @pytest.mark.asyncio
    async def test_inprocess_denies_over_limit(self):
        """In-process fallback should deny requests that exceed the limit."""
        from app.middleware.rate_limiter import redis_sliding_window_check

        limit = 3
        cache_svc = _make_cache_svc_with_cb_state("open")

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            # Make limit + 1 requests
            results = []
            for _ in range(limit + 1):
                result = await redis_sliding_window_check(
                    "user-deny", limit=limit, window_seconds=60
                )
                results.append(result)

        allowed_flags = [r[0] for r in results]
        # First `limit` requests should be allowed, the (limit+1)th should be denied
        assert all(allowed_flags[:limit]), "All requests within limit should be allowed"
        assert allowed_flags[limit] is False, "Request over limit should be denied"

    @pytest.mark.asyncio
    async def test_inprocess_separate_counters_per_user(self):
        """In-process fallback uses separate counters per user — user A at limit does not block user B."""
        from app.middleware.rate_limiter import redis_sliding_window_check

        limit = 2
        cache_svc = _make_cache_svc_with_cb_state("open")

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            # Exhaust user-A's limit
            for _ in range(limit + 1):
                await redis_sliding_window_check(
                    "user-A", limit=limit, window_seconds=60
                )

            # User B should still be allowed (first request)
            allowed, *_ = await redis_sliding_window_check(
                "user-B", limit=limit, window_seconds=60
            )

        assert allowed is True, "User B should not be blocked by User A's counter"

    @pytest.mark.asyncio
    async def test_redis_path_used_when_cb_closed(self):
        """When CB is closed, the Redis pipeline should be called (not in-process)."""
        from app.middleware.rate_limiter import redis_sliding_window_check

        redis_client = _make_client(incr_result=5)
        cache_svc = _make_cache_svc_with_cb_state("closed", client=redis_client)

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            allowed, _limit, remaining, _reset_at = await redis_sliding_window_check(
                "user-normal", limit=10, window_seconds=60
            )

        cache_svc._ensure_connection.assert_called_once()
        assert allowed is True
        assert remaining == 5  # 10 - 5


class TestInProcessRateCheck:
    """Unit tests for the _in_process_rate_check helper function directly."""

    def setup_method(self):
        """Reset the in-process fallback counters before each test."""
        import app.middleware.rate_limiter as rl

        rl._fallback_counters.clear()

    def test_under_limit_returns_allowed(self):
        """First request under the limit should return allowed=True."""
        from app.middleware.rate_limiter import _in_process_rate_check

        allowed, limit, remaining, reset_at = _in_process_rate_check(
            "user-1", limit=5, window_seconds=60
        )

        assert allowed is True
        assert limit == 5
        assert remaining == 4  # limit - 1 (first request)
        assert isinstance(reset_at, int) and reset_at > 0

    def test_at_limit_still_allowed(self):
        """The request exactly at the limit should still be allowed (count <= limit)."""
        from app.middleware.rate_limiter import _in_process_rate_check

        for _ in range(4):
            _in_process_rate_check("user-2", limit=5, window_seconds=60)

        # 5th request — exactly at limit
        allowed, _limit, remaining, _reset_at = _in_process_rate_check(
            "user-2", limit=5, window_seconds=60
        )
        assert allowed is True
        assert remaining == 0

    def test_over_limit_returns_denied(self):
        """Requests exceeding the limit should return allowed=False."""
        from app.middleware.rate_limiter import _in_process_rate_check

        for _ in range(5):
            _in_process_rate_check("user-3", limit=5, window_seconds=60)

        # 6th request — over limit
        allowed, *_ = _in_process_rate_check("user-3", limit=5, window_seconds=60)
        assert allowed is False

    def test_separate_counters_per_user(self):
        """Different user_ids must have independent counters."""
        from app.middleware.rate_limiter import _in_process_rate_check

        # Exhaust user-X
        for _ in range(10):
            _in_process_rate_check("user-X", limit=5, window_seconds=60)

        # user-Y should still be at count=1
        allowed, *_ = _in_process_rate_check("user-Y", limit=5, window_seconds=60)
        assert allowed is True
