"""Tests for Redis-backed persona cache in rate_limiter.py.

Validates the L1 (local dict) + L2 (Redis) caching strategy for persona
lookups, including fallback to in-memory dict when Redis is unavailable.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_persona_cache():
    """Clear the module-level persona cache before each test."""
    from app.middleware.rate_limiter import _persona_cache

    _persona_cache.clear()
    yield
    _persona_cache.clear()


# ---------------------------------------------------------------------------
# Test 1: _get_cached_persona_async returns persona from Redis when available
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_cached_persona_async_returns_from_redis():
    """When local cache misses but Redis has the value, return it."""
    from app.middleware.rate_limiter import _get_cached_persona_async

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=b"startup")

    mock_cache = MagicMock()
    mock_cache._ensure_connection = AsyncMock(return_value=mock_redis)

    with patch(
        "app.services.cache.get_cache_service", return_value=mock_cache
    ):
        result = await _get_cached_persona_async("user-123")

    assert result == "startup"
    mock_redis.get.assert_awaited_once_with("pikar:persona:user-123")


# ---------------------------------------------------------------------------
# Test 2: _get_cached_persona_async returns None when Redis key missing
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_cached_persona_async_returns_none_when_key_missing():
    """When neither local cache nor Redis has the value, return None."""
    from app.middleware.rate_limiter import _get_cached_persona_async

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)

    mock_cache = MagicMock()
    mock_cache._ensure_connection = AsyncMock(return_value=mock_redis)

    with patch(
        "app.services.cache.get_cache_service", return_value=mock_cache
    ):
        result = await _get_cached_persona_async("user-999")

    assert result is None


# ---------------------------------------------------------------------------
# Test 3: _get_cached_persona_async falls back to in-memory when Redis down
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_cached_persona_async_falls_back_to_local():
    """When Redis is unavailable, return from local cache if present."""
    from app.middleware.rate_limiter import (
        _get_cached_persona_async,
        _persona_cache,
    )

    # Pre-populate L1 cache
    _persona_cache["user-456"] = ("enterprise", time.time())

    mock_cache = MagicMock()
    mock_cache._ensure_connection = AsyncMock(return_value=None)

    with patch(
        "app.services.cache.get_cache_service", return_value=mock_cache
    ):
        result = await _get_cached_persona_async("user-456")

    assert result == "enterprise"


# ---------------------------------------------------------------------------
# Test 4: _set_cached_persona_async writes to Redis with TTL
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_set_cached_persona_async_writes_redis_with_ttl():
    """Persona is written to Redis via SETEX with the configured TTL."""
    from app.middleware.rate_limiter import (
        _cache_ttl_seconds,
        _set_cached_persona_async,
    )

    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()

    mock_cache = MagicMock()
    mock_cache._ensure_connection = AsyncMock(return_value=mock_redis)

    with patch(
        "app.services.cache.get_cache_service", return_value=mock_cache
    ):
        await _set_cached_persona_async("user-789", "sme")

    mock_redis.setex.assert_awaited_once_with(
        "pikar:persona:user-789",
        _cache_ttl_seconds,
        "sme",
    )


# ---------------------------------------------------------------------------
# Test 5: _set_cached_persona_async falls back to local when Redis down
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_set_cached_persona_async_falls_back_to_local():
    """When Redis is unavailable, persona is still written to local cache."""
    from app.middleware.rate_limiter import (
        _persona_cache,
        _set_cached_persona_async,
    )

    mock_cache = MagicMock()
    mock_cache._ensure_connection = AsyncMock(return_value=None)

    with patch(
        "app.services.cache.get_cache_service", return_value=mock_cache
    ):
        await _set_cached_persona_async("user-abc", "solopreneur")

    assert "user-abc" in _persona_cache
    persona, _ts = _persona_cache["user-abc"]
    assert persona == "solopreneur"


# ---------------------------------------------------------------------------
# Test 6: Redis key pattern is pikar:persona:{user_id}
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_redis_key_pattern_is_correct():
    """Redis operations use the pikar:persona:{user_id} key pattern."""
    from app.middleware.rate_limiter import _REDIS_PERSONA_PREFIX

    assert _REDIS_PERSONA_PREFIX == "pikar:persona:"

    from app.middleware.rate_limiter import _set_cached_persona_async

    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()

    mock_cache = MagicMock()
    mock_cache._ensure_connection = AsyncMock(return_value=mock_redis)

    with patch(
        "app.services.cache.get_cache_service", return_value=mock_cache
    ):
        await _set_cached_persona_async("test-user-id", "enterprise")

    # Verify the key used in the Redis call
    call_args = mock_redis.setex.call_args
    redis_key = call_args[0][0]
    assert redis_key == "pikar:persona:test-user-id"


# ---------------------------------------------------------------------------
# Test 7: In-memory cache cleanup still triggers at 1000 entries
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_inmemory_cache_cleanup_at_1000_entries():
    """When local cache exceeds 1000 entries, expired entries are cleaned."""
    from app.middleware.rate_limiter import (
        _cache_ttl_seconds,
        _persona_cache,
        _set_cached_persona_async,
    )

    # Pre-populate with 1000 expired entries
    expired_time = time.time() - _cache_ttl_seconds - 10
    for i in range(1000):
        _persona_cache[f"old-user-{i}"] = ("solopreneur", expired_time)

    assert len(_persona_cache) == 1000

    mock_cache = MagicMock()
    mock_cache._ensure_connection = AsyncMock(return_value=None)

    with patch(
        "app.services.cache.get_cache_service", return_value=mock_cache
    ):
        # This should trigger cleanup (cache > 1000 after adding new entry)
        await _set_cached_persona_async("new-user", "enterprise")

    # All 1000 expired entries should be cleaned; only the new one remains
    assert "new-user" in _persona_cache
    assert len(_persona_cache) < 100  # Most expired entries cleaned


# ---------------------------------------------------------------------------
# Test 8: _get_cached_persona_async backfills L1 from Redis hit
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_cached_persona_async_backfills_l1_from_redis():
    """When Redis returns a persona, it should be stored in L1 cache."""
    from app.middleware.rate_limiter import (
        _get_cached_persona_async,
        _persona_cache,
    )

    assert "user-backfill" not in _persona_cache

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=b"sme")

    mock_cache = MagicMock()
    mock_cache._ensure_connection = AsyncMock(return_value=mock_redis)

    with patch(
        "app.services.cache.get_cache_service", return_value=mock_cache
    ):
        result = await _get_cached_persona_async("user-backfill")

    assert result == "sme"
    # L1 cache should now contain the value
    assert "user-backfill" in _persona_cache
    persona, _ts = _persona_cache["user-backfill"]
    assert persona == "sme"


# ---------------------------------------------------------------------------
# Test 9: _set_cached_persona_async also writes local cache
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_set_cached_persona_async_writes_local_cache():
    """_set_cached_persona_async always writes to L1 local dict."""
    from app.middleware.rate_limiter import (
        _persona_cache,
        _set_cached_persona_async,
    )

    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()

    mock_cache = MagicMock()
    mock_cache._ensure_connection = AsyncMock(return_value=mock_redis)

    with patch(
        "app.services.cache.get_cache_service", return_value=mock_cache
    ):
        await _set_cached_persona_async("user-local", "startup")

    assert "user-local" in _persona_cache
    persona, _ts = _persona_cache["user-local"]
    assert persona == "startup"


# ---------------------------------------------------------------------------
# Test 10: warm_persona_cache delegates to _set_cached_persona_async
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_warm_persona_cache_sets_both_layers():
    """warm_persona_cache writes to both L1 and L2."""
    from app.middleware.rate_limiter import _persona_cache, warm_persona_cache

    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()

    mock_cache = MagicMock()
    mock_cache._ensure_connection = AsyncMock(return_value=mock_redis)

    with patch(
        "app.services.cache.get_cache_service", return_value=mock_cache
    ):
        await warm_persona_cache("user-warm", "enterprise")

    # L1 cache populated
    assert "user-warm" in _persona_cache
    # Redis was called
    mock_redis.setex.assert_awaited_once()
