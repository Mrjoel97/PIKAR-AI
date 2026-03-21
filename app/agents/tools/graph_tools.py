"""Knowledge Graph read tools for agents.

Provides a sync ADK tool for querying the knowledge graph with Redis
caching. All 10 specialized agents can use this tool to look up entities,
findings, and relationships without triggering live research.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any

from app.agents.research.config import DOMAIN_FRESHNESS, get_cache_ttl_seconds
from app.services.cache import CacheResult, get_cache_service
from app.services.graph_service import GraphService
from app.services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def _cache_key(domain: str, query: str) -> str:
    """Build a deterministic Redis cache key for a graph_read query.

    Args:
        domain: Agent domain scope.
        query: Raw user query string.

    Returns:
        Cache key string in the format ``kg:read:{domain}:{hash_prefix}``.
    """
    digest = hashlib.sha256(query.lower().encode()).hexdigest()[:16]
    return f"kg:read:{domain}:{digest}"


def _run_async(coro):
    """Run an async coroutine from a sync context.

    Attempts to use the running event loop; creates a new one if none exists.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def _get_cached_or_query(
    query: str,
    domain: str,
    freshness_hours: int | None = None,
) -> dict[str, Any]:
    """Check cache then fall back to GraphService query.

    This helper is the single function that tests can patch to control
    cache and DB behaviour without touching Redis or Supabase.

    Args:
        query: Entity name, topic, or search term.
        domain: Agent domain for scoping results.
        freshness_hours: Optional override for cache TTL in hours.

    Returns:
        Dictionary with graph query results.
    """
    cache = get_cache_service()
    key = _cache_key(domain, query)

    # 1. Try cache
    cache_result: CacheResult = _run_async(cache.get_generic(key))
    if cache_result.found and cache_result.value is not None:
        logger.debug("graph_read cache hit for key=%s", key)
        return cache_result.value

    # 2. Cache miss — query the graph
    logger.debug("graph_read cache miss for key=%s, querying graph", key)
    db = get_supabase_client()
    service = GraphService(db)
    result = service.query_entity(query, domain)

    # 3. Cache the result
    ttl = (freshness_hours * 3600) if freshness_hours else get_cache_ttl_seconds(domain)
    _run_async(cache.set_generic(key, result, ttl=ttl))

    return result


def graph_read(
    query: str,
    domain: str,
    freshness_hours: int | None = None,
) -> dict[str, Any]:
    """Read structured intelligence from the knowledge graph.

    Queries the knowledge graph for entities, their relationships, and
    recent findings. Uses Redis caching for sub-second repeated lookups.
    If the graph has no data for the query, returns found=False.

    This tool does NOT trigger live research. It only reads what is
    already in the graph. For fresh research, delegate to the Research Agent.

    Args:
        query: Entity name, topic, or search term to look up.
        domain: Agent domain for scoping results (e.g., 'financial', 'marketing').
        freshness_hours: Optional override for cache TTL in hours.

    Returns:
        Dictionary with success, found, entity, findings, relationships, and
        optional staleness warning.
    """
    try:
        result = _get_cached_or_query(query, domain, freshness_hours)

        found = result.get("found", False)
        entity = result.get("entity")
        findings = result.get("findings", [])
        relationships = result.get("relationships", [])

        response: dict[str, Any] = {
            "success": True,
            "found": found,
            "entity": entity,
            "findings": findings,
            "relationships": relationships,
        }

        # Check staleness against domain freshness threshold
        if found and findings:
            threshold_hours = float(
                DOMAIN_FRESHNESS.get(domain, {}).get("default_hours", 24)
            )
            stale_count = sum(
                1
                for f in findings
                if GraphService.is_stale(f.get("freshness_at", ""), threshold_hours)
            )
            if stale_count > 0:
                response["staleness_warning"] = (
                    f"{stale_count}/{len(findings)} findings exceed the "
                    f"{threshold_hours}h freshness threshold for '{domain}'. "
                    "Consider delegating to the Research Agent for an update."
                )

        return response
    except Exception as exc:
        logger.error(
            "graph_read failed for query='%s', domain='%s': %s", query, domain, exc
        )
        return {
            "success": False,
            "error": f"Graph read failed: {exc}",
            "found": False,
            "entity": None,
            "findings": [],
            "relationships": [],
        }


GRAPH_TOOLS = [graph_read]
