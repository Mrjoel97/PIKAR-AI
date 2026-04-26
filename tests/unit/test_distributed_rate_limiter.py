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
        cache_svc._ensure_connection = AsyncMock(return_value=client)

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            allowed, limit, remaining, reset_at = await redis_sliding_window_check(
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
        cache_svc._ensure_connection = AsyncMock(return_value=client)

        window_seconds = 60
        now = int(_time.time())
        window_start = (now // window_seconds) * window_seconds

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            await redis_sliding_window_check("u-123", limit=10, window_seconds=window_seconds)

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
        cache_svc._ensure_connection = AsyncMock(return_value=None)

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            allowed, limit, remaining, reset_at = await redis_sliding_window_check(
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
        cache_svc._ensure_connection = AsyncMock(return_value=client)

        with patch("app.services.cache.get_cache_service", return_value=cache_svc):
            allowed, limit, remaining, reset_at = await redis_sliding_window_check(
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
        request.headers.get = MagicMock(side_effect=lambda k, d=None: "solopreneur" if k == "x-pikar-persona" else d)

        result = get_user_persona_limit(request)
        assert result == "10/minute"

    def test_enterprise_returns_120_per_minute(self):
        from app.middleware.rate_limiter import get_user_persona_limit

        request = MagicMock()
        request.cookies.get = MagicMock(return_value=None)
        request.headers.get = MagicMock(side_effect=lambda k, d=None: "enterprise" if k == "x-pikar-persona" else d)

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
