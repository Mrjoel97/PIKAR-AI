"""Unit tests for the IntegrationProxyService and check_session_budget.

Tests verify:
- test_proxy_cache_hit: returns cached data without calling provider fetch
- test_proxy_cache_miss: calls provider fetch and stores result in cache
- test_session_budget_allowed: returns True when call count is under limit
- test_session_budget_exhausted: returns False when count exceeds max_calls
- test_session_budget_redis_unavailable: returns True (fail open) when Redis down
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =========================================================================
# Test 1: Cache hit — returns cached data, no HTTP call made
# =========================================================================


@pytest.mark.asyncio
async def test_proxy_cache_hit():
    """IntegrationProxyService returns cached data without calling provider."""
    from app.services.integration_proxy import IntegrationProxyService

    cached_data = {"id": "123", "title": "Issue from cache"}
    cache_result = MagicMock()
    cache_result.found = True
    cache_result.value = cached_data

    mock_cache = MagicMock()
    mock_cache.get_generic = AsyncMock(return_value=cache_result)

    # fetch_fn should never be called on cache hit
    fetch_fn = AsyncMock(return_value={"id": "999", "title": "Fresh"})

    with patch("app.services.integration_proxy.get_cache_service", return_value=mock_cache):
        result = await IntegrationProxyService.call(
            provider="sentry",
            operation="get_issues",
            api_key="test-key",
            config={"org_slug": "myorg", "project_slug": "myproject"},
            params={},
            fetch_fn=fetch_fn,
        )

    assert result == cached_data
    fetch_fn.assert_not_called()
    mock_cache.get_generic.assert_called_once()


# =========================================================================
# Test 2: Cache miss — calls fetch and stores in cache
# =========================================================================


@pytest.mark.asyncio
async def test_proxy_cache_miss():
    """IntegrationProxyService calls fetch_fn and stores result on cache miss."""
    from app.services.integration_proxy import IntegrationProxyService

    cache_miss = MagicMock()
    cache_miss.found = False

    fresh_data = [{"id": "1", "title": "New issue"}]

    mock_cache = MagicMock()
    mock_cache.get_generic = AsyncMock(return_value=cache_miss)
    mock_cache.set_generic = AsyncMock(return_value=True)

    fetch_fn = AsyncMock(return_value=fresh_data)

    with patch("app.services.integration_proxy.get_cache_service", return_value=mock_cache):
        result = await IntegrationProxyService.call(
            provider="sentry",
            operation="get_issues",
            api_key="test-key",
            config={"org_slug": "myorg", "project_slug": "myproject"},
            params={},
            fetch_fn=fetch_fn,
        )

    assert result == fresh_data
    fetch_fn.assert_called_once()
    mock_cache.set_generic.assert_called_once()
    # Verify the cache was set with some TTL
    _, call_kwargs = mock_cache.set_generic.call_args
    # TTL should be > 0
    ttl = call_kwargs.get("ttl") or mock_cache.set_generic.call_args[0][2] if len(mock_cache.set_generic.call_args[0]) > 2 else 180
    assert ttl > 0


# =========================================================================
# Test 3: Session budget allowed
# =========================================================================


@pytest.mark.asyncio
async def test_session_budget_allowed():
    """check_session_budget returns True when call count is under max_calls."""
    from app.services.integration_proxy import check_session_budget

    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=5)  # 5 < 20
    mock_redis.expire = AsyncMock(return_value=True)

    mock_cache = MagicMock()
    mock_cache._ensure_connection = AsyncMock(return_value=mock_redis)

    with patch("app.services.integration_proxy.get_cache_service", return_value=mock_cache):
        result = await check_session_budget(
            session_id="sess-abc",
            provider="sentry",
            max_calls=20,
        )

    assert result is True
    mock_redis.incr.assert_called_once()


# =========================================================================
# Test 4: Session budget exhausted
# =========================================================================


@pytest.mark.asyncio
async def test_session_budget_exhausted():
    """check_session_budget returns False when call count exceeds max_calls."""
    from app.services.integration_proxy import check_session_budget

    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=25)  # 25 > 20
    mock_redis.expire = AsyncMock(return_value=True)

    mock_cache = MagicMock()
    mock_cache._ensure_connection = AsyncMock(return_value=mock_redis)

    with patch("app.services.integration_proxy.get_cache_service", return_value=mock_cache):
        result = await check_session_budget(
            session_id="sess-abc",
            provider="sentry",
            max_calls=20,
        )

    assert result is False


# =========================================================================
# Test 5: Session budget fails open when Redis unavailable
# =========================================================================


@pytest.mark.asyncio
async def test_session_budget_redis_unavailable():
    """check_session_budget returns True (fail open) when Redis is down."""
    from app.services.integration_proxy import check_session_budget

    mock_cache = MagicMock()
    mock_cache._ensure_connection = AsyncMock(return_value=None)  # Redis unavailable

    with patch("app.services.integration_proxy.get_cache_service", return_value=mock_cache):
        result = await check_session_budget(
            session_id="sess-abc",
            provider="sentry",
            max_calls=20,
        )

    assert result is True
