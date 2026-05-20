"""Two-tier adaptive cache: graph for claims, Redis for raw external calls.

Public surface:
- should_query_graph   — consult kg_findings freshness
- should_call_external — consult Redis with age tracking

Both return CacheDecision(tier, verdict, freshness_hours). Reads degrade
silently — backend failure returns verdict='miss' forcing a fresh fetch.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.services.cache import get_cache_service
from app.services.intelligence.claims import claim_freshness_hours
from app.services.intelligence.schemas import CacheDecision

logger = logging.getLogger(__name__)


async def should_query_graph(
    *,
    entity_id: UUID,
    claim_type: str | None,
    agent_id: str | None,
    freshness_threshold_hours: float,
) -> CacheDecision:
    """Graph-tier cache decision: is there a fresh-enough claim in kg_findings?

    Args:
        entity_id: kg_entities row to check.
        claim_type: Restrict to this claim_type, or None for any.
        agent_id: Restrict to claims from this agent, or None for any.
        freshness_threshold_hours: Maximum age in hours for "fresh".

    Returns:
        CacheDecision with tier='graph'. On DB failure, returns
        verdict='miss' so caller forces fresh fetch.
    """
    try:
        age = await claim_freshness_hours(
            entity_id=entity_id,
            claim_type=claim_type,
            agent_id=agent_id,
        )
    except Exception as e:
        logger.warning("should_query_graph: freshness lookup failed: %s", e)
        return CacheDecision(tier="graph", verdict="miss", freshness_hours=None)

    if age is None:
        return CacheDecision(tier="graph", verdict="miss", freshness_hours=None)
    if age <= freshness_threshold_hours:
        return CacheDecision(tier="graph", verdict="fresh", freshness_hours=age)
    return CacheDecision(tier="graph", verdict="stale", freshness_hours=age)


async def should_call_external(
    *,
    cache_key: str,
    ttl_seconds: int,
) -> CacheDecision:
    """Redis-tier cache decision: is there a fresh-enough cached value?

    Wraps the existing CacheService.get_with_age. Age is converted to hours
    in the returned CacheDecision so consumers always have a uniform unit
    across graph-tier and redis-tier decisions.

    Args:
        cache_key: Redis key — caller is responsible for namespacing.
        ttl_seconds: Freshness threshold in seconds.

    Returns:
        CacheDecision with tier='redis'. On Redis failure, returns
        verdict='miss' so caller forces fresh fetch.
    """
    try:
        cache = get_cache_service()
        value, age_seconds = await cache.get_with_age(cache_key)
    except Exception as e:
        logger.warning("should_call_external: Redis lookup failed: %s", e)
        return CacheDecision(tier="redis", verdict="miss", freshness_hours=None)

    if value is None or age_seconds is None:
        return CacheDecision(tier="redis", verdict="miss", freshness_hours=None)

    age_hours = age_seconds / 3600.0
    if age_seconds <= ttl_seconds:
        return CacheDecision(tier="redis", verdict="fresh", freshness_hours=age_hours)
    return CacheDecision(tier="redis", verdict="stale", freshness_hours=age_hours)
