"""Unit tests for app.services.intelligence.cache."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# should_query_graph
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_should_query_graph_fresh():
    """When a fresh claim exists within threshold, verdict='fresh'."""
    from app.services.intelligence.cache import should_query_graph

    entity_id = uuid4()
    with patch(
        "app.services.intelligence.cache.claim_freshness_hours",
        new=AsyncMock(return_value=2.0),
    ):
        decision = await should_query_graph(
            entity_id=entity_id,
            claim_type="cohort_retention",
            agent_id="data",
            freshness_threshold_hours=24.0,
        )
    assert decision.tier == "graph"
    assert decision.verdict == "fresh"
    assert decision.freshness_hours == 2.0


@pytest.mark.asyncio
async def test_should_query_graph_stale():
    """When claim exists but exceeds threshold, verdict='stale'."""
    from app.services.intelligence.cache import should_query_graph

    with patch(
        "app.services.intelligence.cache.claim_freshness_hours",
        new=AsyncMock(return_value=48.0),
    ):
        decision = await should_query_graph(
            entity_id=uuid4(),
            claim_type="cohort_retention",
            agent_id="data",
            freshness_threshold_hours=24.0,
        )
    assert decision.verdict == "stale"
    assert decision.freshness_hours == 48.0


@pytest.mark.asyncio
async def test_should_query_graph_miss():
    """When no matching claim exists, verdict='miss'."""
    from app.services.intelligence.cache import should_query_graph

    with patch(
        "app.services.intelligence.cache.claim_freshness_hours",
        new=AsyncMock(return_value=None),
    ):
        decision = await should_query_graph(
            entity_id=uuid4(),
            claim_type="x",
            agent_id="y",
            freshness_threshold_hours=12.0,
        )
    assert decision.verdict == "miss"
    assert decision.freshness_hours is None


@pytest.mark.asyncio
async def test_should_query_graph_db_failure_returns_miss():
    """When claim_freshness_hours raises, verdict='miss' (degrades silently)."""
    from app.services.intelligence.cache import should_query_graph

    with patch(
        "app.services.intelligence.cache.claim_freshness_hours",
        new=AsyncMock(side_effect=Exception("DB down")),
    ):
        decision = await should_query_graph(
            entity_id=uuid4(),
            claim_type="x",
            agent_id="y",
            freshness_threshold_hours=12.0,
        )
    assert decision.verdict == "miss"
    assert decision.freshness_hours is None


# ---------------------------------------------------------------------------
# should_call_external
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_should_call_external_fresh():
    """Fresh Redis entry (age <= ttl) returns verdict='fresh'."""
    from app.services.intelligence.cache import should_call_external

    fake_cache = AsyncMock()
    fake_cache.get_with_age = AsyncMock(return_value=("cached value", 60.0))

    with patch(
        "app.services.intelligence.cache.get_cache_service",
        return_value=fake_cache,
    ):
        decision = await should_call_external(
            cache_key="test:key",
            ttl_seconds=300,
        )
    assert decision.tier == "redis"
    assert decision.verdict == "fresh"
    assert decision.freshness_hours == pytest.approx(60.0 / 3600.0, rel=1e-6)


@pytest.mark.asyncio
async def test_should_call_external_stale():
    """Stale Redis entry (age > ttl, but present) returns verdict='stale'."""
    from app.services.intelligence.cache import should_call_external

    fake_cache = AsyncMock()
    fake_cache.get_with_age = AsyncMock(return_value=("cached value", 600.0))

    with patch(
        "app.services.intelligence.cache.get_cache_service",
        return_value=fake_cache,
    ):
        decision = await should_call_external(
            cache_key="test:key",
            ttl_seconds=300,
        )
    assert decision.verdict == "stale"


@pytest.mark.asyncio
async def test_should_call_external_miss():
    """No Redis entry returns verdict='miss'."""
    from app.services.intelligence.cache import should_call_external

    fake_cache = AsyncMock()
    fake_cache.get_with_age = AsyncMock(return_value=(None, None))

    with patch(
        "app.services.intelligence.cache.get_cache_service",
        return_value=fake_cache,
    ):
        decision = await should_call_external(
            cache_key="test:key",
            ttl_seconds=300,
        )
    assert decision.verdict == "miss"
    assert decision.freshness_hours is None


@pytest.mark.asyncio
async def test_should_call_external_redis_down_returns_miss():
    """Redis backend exception returns verdict='miss' (degrades silently)."""
    from app.services.intelligence.cache import should_call_external

    fake_cache = AsyncMock()
    fake_cache.get_with_age = AsyncMock(side_effect=Exception("Redis down"))

    with patch(
        "app.services.intelligence.cache.get_cache_service",
        return_value=fake_cache,
    ):
        decision = await should_call_external(
            cache_key="test:key",
            ttl_seconds=300,
        )
    assert decision.verdict == "miss"
    assert decision.freshness_hours is None
