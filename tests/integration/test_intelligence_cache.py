"""Integration smoke tests for the two-tier adaptive cache."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var) for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
        ),
        reason="Supabase credentials not provided in environment variables.",
    ),
]


@pytest.mark.asyncio
async def test_graph_tier_miss_then_fresh():
    """Write a claim, then should_query_graph reports it as fresh."""
    from app.services.intelligence import (
        get_or_create_entity,
        should_query_graph,
        write_claim,
    )

    entity_id = await get_or_create_entity(
        canonical_name=f"Cache Integ {uuid4()}",
        entity_type="topic",
        domains=["test"],
    )

    # Miss before any claim
    decision = await should_query_graph(
        entity_id=entity_id,
        claim_type="probe",
        agent_id="test",
        freshness_threshold_hours=24.0,
    )
    assert decision.verdict == "miss"

    await write_claim(
        entity_id=entity_id,
        domain="test",
        finding_text="cache probe claim",
        confidence=0.7,
        sources=[],
        agent_id="test",
        claim_type="probe",
    )

    decision = await should_query_graph(
        entity_id=entity_id,
        claim_type="probe",
        agent_id="test",
        freshness_threshold_hours=24.0,
    )
    assert decision.verdict == "fresh"
    assert decision.freshness_hours is not None and decision.freshness_hours < 0.01


@pytest.mark.asyncio
async def test_redis_tier_miss_then_fresh_then_stale():
    """Lifecycle of a Redis-tier cached entry: miss -> fresh -> stale."""
    import asyncio

    from app.services.cache import get_cache_service
    from app.services.intelligence import should_call_external

    cache = get_cache_service()
    key = f"test:plan-112-04:integ:{uuid4()}"

    # Miss
    decision = await should_call_external(cache_key=key, ttl_seconds=300)
    assert decision.verdict == "miss"

    # Fresh after set_with_age
    await cache.set_with_age(key, {"data": "payload"}, ttl=600)
    decision = await should_call_external(cache_key=key, ttl_seconds=300)
    assert decision.verdict == "fresh"

    # Stale after waiting longer than ttl_seconds
    # (ttl_seconds=1 forces stale after a brief sleep)
    await asyncio.sleep(1.2)
    decision = await should_call_external(cache_key=key, ttl_seconds=1)
    assert decision.verdict == "stale"
