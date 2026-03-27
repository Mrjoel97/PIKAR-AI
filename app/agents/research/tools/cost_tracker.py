# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Cost tracker for research intelligence operations.

Estimates and logs the cost of each research run to the kg_research_log
table. Designed for fire-and-forget usage: log_research_cost never raises
on failure, so a logging error cannot break the research pipeline.

Cost model (Tavily + Firecrawl, approximate):
  - COST_PER_SEARCH  = $0.01  per Tavily search call
  - COST_PER_SCRAPE  = $0.015 per Firecrawl scrape call
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Cost constants (USD)
COST_PER_SEARCH = 0.01
COST_PER_SCRAPE = 0.015


def _get_supabase():
    """Get Supabase client. Isolated for easy test patching."""
    from app.services.supabase_client import get_supabase_client

    return get_supabase_client()


def estimate_cost_usd(
    searches: int,
    scrapes: int,
) -> float:
    """Estimate the USD cost of a research run from operation counts.

    Args:
        searches: Number of Tavily search API calls.
        scrapes: Number of Firecrawl scrape API calls.

    Returns:
        Estimated cost in USD.
    """
    return round(searches * COST_PER_SEARCH + scrapes * COST_PER_SCRAPE, 4)


def log_research_cost(
    domain: str,
    query: str,
    depth: str,
    tracks_run: int,
    searches_used: int,
    scrapes_used: int,
    findings_count: int,
    graph_updates: int,
    triggered_by: str,
    duration_ms: int,
    requesting_agent: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Log a completed research run to kg_research_log.

    Fire-and-forget: never raises on failure. Returns a dict with
    success=False and an error message instead.

    Args:
        domain: Agent domain (e.g. 'financial').
        query: Original research query.
        depth: Research depth ('quick', 'standard', 'deep').
        tracks_run: Number of tracks executed.
        searches_used: Total Tavily search calls across all tracks.
        scrapes_used: Total Firecrawl scrape calls across all tracks.
        findings_count: Number of findings extracted.
        graph_updates: Number of graph writes (entities + findings).
        triggered_by: Trigger source ('agent_request', 'scheduled',
                      'event', 'user_initiated').
        duration_ms: Total research duration in milliseconds.
        requesting_agent: Optional name of the agent that requested research.
        user_id: Optional user ID for audit trail.

    Returns:
        Dict with success flag and the log row ID (or error details).
    """
    try:
        client = _get_supabase()

        cost_usd = estimate_cost_usd(searches_used, scrapes_used)

        row = {
            "domain": domain,
            "query": query,
            "depth": depth,
            "tracks_run": tracks_run,
            "searches_used": searches_used,
            "scrapes_used": scrapes_used,
            "cost_usd": cost_usd,
            "findings_count": findings_count,
            "graph_updates": graph_updates,
            "triggered_by": triggered_by,
            "duration_ms": duration_ms,
        }

        if requesting_agent:
            row["requesting_agent"] = requesting_agent
        if user_id:
            row["user_id"] = user_id

        result = client.table("kg_research_log").insert(row).execute()

        log_id = None
        if result.data:
            log_id = result.data[0].get("id")

        logger.info(
            "Research cost logged: domain=%s, cost=$%.4f, duration=%dms, log_id=%s",
            domain,
            cost_usd,
            duration_ms,
            log_id,
        )

        return {
            "success": True,
            "log_id": log_id,
            "cost_usd": cost_usd,
        }

    except Exception as e:
        logger.error("Failed to log research cost: %s", e)
        return {
            "success": False,
            "error": str(e),
        }


# ADK tool export
COST_TRACKER_TOOLS = [log_research_cost]
