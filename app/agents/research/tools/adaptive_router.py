"""Adaptive research depth router.

Determines the appropriate research depth for each query using a
priority-ordered decision chain:

1. If graph has fresh data -> CACHE_ONLY
2. If domain budget exhausted -> CACHE_ONLY (fallback)
3. Heuristic scoring based on domain priority + query complexity -> depth

In Phase 5, the self-improvement system will generate skills like
"pre_research_investment_queries" and "skip_research_hr_policy" that
override these heuristics. For now, we use domain priority as the
primary signal.
"""

from __future__ import annotations

import enum
import logging

logger = logging.getLogger(__name__)


class ResearchDepth(enum.IntEnum):
    """Research depth levels, ordered by intensity.

    IntEnum so depths can be compared: DEEP > STANDARD > QUICK > CACHE_ONLY.
    """

    CACHE_ONLY = 0
    QUICK = 1
    STANDARD = 2
    DEEP = 3


# Domain priority scores (higher = more research-intensive)
DOMAIN_PRIORITY: dict[str, float] = {
    "financial": 0.9,
    "compliance": 0.85,
    "strategic": 0.8,
    "sales": 0.7,
    "marketing": 0.7,
    "customer_support": 0.65,
    "data": 0.6,
    "content": 0.5,
    "operations": 0.45,
    "hr": 0.3,
}


def determine_depth(
    query: str,
    domain: str,
    agent_id: str,
    graph_freshness_hours: float | None = None,
) -> ResearchDepth:
    """Determine the appropriate research depth for a query.

    Decision chain (priority order):
    1. If graph data is fresh (within domain threshold) -> CACHE_ONLY
    2. If domain budget is exhausted -> CACHE_ONLY
    3. Heuristic: domain priority + staleness -> QUICK/STANDARD/DEEP

    In Phase 5, self-improvement skills will be checked first:
    - skip_research_* skills -> force CACHE_ONLY
    - pre_research_* skills -> force minimum depth

    Args:
        query: The research query text.
        domain: Agent domain (e.g., 'financial', 'hr').
        agent_id: Which agent is requesting.
        graph_freshness_hours: Hours since last relevant graph data.
            None means no graph data exists.

    Returns:
        ResearchDepth enum value.
    """
    # Step 1: Check graph freshness
    if graph_freshness_hours is not None:
        from app.agents.research.config import DOMAIN_FRESHNESS

        threshold = DOMAIN_FRESHNESS.get(domain, {}).get("default_hours", 24)
        if graph_freshness_hours <= threshold:
            logger.debug(
                "Graph data fresh (%.1fh <= %dh threshold) for %s — CACHE_ONLY",
                graph_freshness_hours,
                threshold,
                domain,
            )
            return ResearchDepth.CACHE_ONLY

    # Step 2: Check budget
    if not _check_budget(domain):
        logger.info("Budget exhausted for %s — falling back to CACHE_ONLY", domain)
        return ResearchDepth.CACHE_ONLY

    # Step 3: Heuristic depth based on domain priority
    priority = DOMAIN_PRIORITY.get(domain, 0.5)

    if priority >= 0.8:
        depth = ResearchDepth.DEEP
    elif priority >= 0.6:
        depth = ResearchDepth.STANDARD
    else:
        depth = ResearchDepth.QUICK

    # Boost depth if no graph data at all (first research on topic)
    if graph_freshness_hours is None and depth.value < ResearchDepth.STANDARD.value:
        depth = ResearchDepth.STANDARD

    logger.debug(
        "Adaptive depth for %s (priority=%.2f, freshness=%s): %s",
        domain,
        priority,
        graph_freshness_hours,
        depth.name,
    )
    return depth


def _check_budget(domain: str) -> bool:
    """Check if the domain has remaining research budget this month.

    Queries kg_domain_budgets and kg_research_log to compare
    spend vs ceiling.

    Args:
        domain: Agent domain.

    Returns:
        True if budget is available, False if exhausted.
    """
    try:
        from app.services.supabase_client import get_supabase_client

        client = get_supabase_client()

        # Get domain budget ceiling
        budget_resp = (
            client.table("kg_domain_budgets")
            .select("monthly_budget, auto_pause, is_active")
            .eq("domain", domain)
            .execute()
        )
        if not budget_resp.data:
            return True  # No budget configured = unlimited
        budget = budget_resp.data[0]
        if not budget.get("is_active"):
            return True  # Inactive = no enforcement

        if not budget.get("auto_pause"):
            return True  # Auto-pause disabled

        ceiling = float(budget["monthly_budget"])

        # Get current month spend
        import datetime

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        month_start = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        ).isoformat()

        spend_resp = (
            client.table("kg_research_log")
            .select("cost_usd")
            .eq("domain", domain)
            .gte("created_at", month_start)
            .execute()
        )
        total_spend = sum(float(row["cost_usd"]) for row in (spend_resp.data or []))

        return total_spend < ceiling

    except Exception as e:
        logger.warning("Budget check failed for %s (allowing research): %s", domain, e)
        return True  # Fail open — allow research if check fails


# ADK tool export
ADAPTIVE_ROUTER_TOOLS = [determine_depth]
