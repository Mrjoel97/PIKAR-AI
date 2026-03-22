"""Intelligence scheduler for continuous domain research.

Maintains baseline freshness per domain on a configurable cadence.
Triggered by Cloud Scheduler endpoint (POST /scheduled/intelligence-tick).

For each domain due for refresh:
1. Find stale high-value entities (ordered by source_count)
2. Check admin-configured watch topics
3. Build prioritized, deduplicated research queue
4. Execute research within domain budget ceiling
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_supabase():
    from app.services.supabase_client import get_supabase_client

    return get_supabase_client()


def get_domains_due_for_refresh() -> list[dict[str, Any]]:
    """Get domains that are active and due for scheduled research.

    Queries kg_domain_budgets for active domains. The actual cron
    schedule check is done by the Cloud Scheduler -- this endpoint
    just processes whatever domains are active.

    Returns:
        List of domain config dicts with domain, monthly_budget, schedule_cron.
    """
    try:
        client = _get_supabase()
        response = (
            client.table("kg_domain_budgets")
            .select("domain, monthly_budget, schedule_cron, is_active")
            .eq("is_active", True)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error("Failed to get domain schedules: %s", e)
        return []


def build_research_queue(
    domain: str,
    max_items: int = 10,
) -> list[dict[str, Any]]:
    """Build a prioritized research queue for a domain.

    Combines:
    1. Stale high-value entities (by source_count descending)
    2. Admin-configured watch topics
    3. Unresolved coverage gaps for this domain

    Args:
        domain: Agent domain.
        max_items: Max items in the queue.

    Returns:
        List of research job dicts with query and depth.
    """
    try:
        client = _get_supabase()
        queue = []

        # 1. Find stale entities
        import datetime

        from app.agents.research.config import DOMAIN_FRESHNESS

        threshold_hours = DOMAIN_FRESHNESS.get(domain, {}).get("default_hours", 24)
        stale_cutoff = (
            datetime.datetime.now(tz=datetime.timezone.utc)
            - datetime.timedelta(hours=threshold_hours)
        ).isoformat()

        stale_resp = (
            client.table("kg_entities")
            .select("canonical_name, source_count, freshness_at")
            .contains("domains", [domain])
            .lt("freshness_at", stale_cutoff)
            .order("source_count", desc=True)
            .limit(max_items)
            .execute()
        )
        for entity in stale_resp.data or []:
            queue.append(
                {
                    "query": entity["canonical_name"],
                    "depth": "standard",
                    "source": "stale_entity",
                    "priority": entity.get("source_count", 1),
                }
            )

        # 2. Watch topics
        watch_resp = (
            client.table("kg_watch_topics")
            .select("topic, priority")
            .eq("domain", domain)
            .eq("is_active", True)
            .execute()
        )
        priority_map = {"critical": 100, "high": 50, "medium": 20, "low": 5}
        for topic in watch_resp.data or []:
            queue.append(
                {
                    "query": topic["topic"],
                    "depth": "deep" if topic["priority"] == "critical" else "standard",
                    "source": "watch_topic",
                    "priority": priority_map.get(topic["priority"], 10),
                }
            )

        # 3. Unresolved coverage gaps
        gaps_resp = (
            client.table("coverage_gaps")
            .select("user_query, occurrence_count")
            .eq("agent_id", _domain_to_agent_id(domain))
            .eq("resolved", False)
            .order("occurrence_count", desc=True)
            .limit(5)
            .execute()
        )
        for gap in gaps_resp.data or []:
            queue.append(
                {
                    "query": gap["user_query"],
                    "depth": "deep",
                    "source": "coverage_gap",
                    "priority": gap.get("occurrence_count", 1) * 10,
                }
            )

        # Deduplicate by query (keep highest priority)
        seen: dict[str, dict] = {}
        for item in queue:
            key = item["query"].lower().strip()
            if key not in seen or item["priority"] > seen[key]["priority"]:
                seen[key] = item
        queue = sorted(seen.values(), key=lambda x: x["priority"], reverse=True)

        return queue[:max_items]

    except Exception as e:
        logger.error("Failed to build research queue for %s: %s", domain, e)
        return []


async def run_scheduled_research(domain: str) -> dict[str, Any]:
    """Execute scheduled research for a domain.

    Builds the research queue and executes each job through the
    Research Agent's pipeline.

    Args:
        domain: Agent domain to research.

    Returns:
        Dict with success, jobs_executed, total_cost.
    """
    queue = build_research_queue(domain)
    if not queue:
        return {
            "success": True,
            "jobs_executed": 0,
            "message": f"No research needed for {domain}",
        }

    jobs_executed = 0
    total_cost = 0.0

    from app.agents.research.tools.adaptive_router import _check_budget

    for item in queue:
        # Budget check before each job
        if not _check_budget(domain):
            logger.info("Budget exhausted for %s after %d jobs", domain, jobs_executed)
            break

        result = await _execute_research_job(
            query=item["query"],
            domain=domain,
            depth=item["depth"],
            triggered_by="scheduled",
        )

        if result.get("success"):
            jobs_executed += 1
            total_cost += result.get("cost_usd", 0)

    return {
        "success": True,
        "domain": domain,
        "jobs_executed": jobs_executed,
        "total_cost": round(total_cost, 4),
        "queue_size": len(queue),
    }


async def _execute_research_job(
    query: str,
    domain: str,
    depth: str,
    triggered_by: str = "scheduled",
) -> dict[str, Any]:
    """Execute a single research job through the full pipeline.

    Pipeline: plan_queries -> run_tracks_parallel -> synthesize_tracks
              -> write_to_graph -> write_to_vault -> log_research_cost

    Args:
        query: Research query.
        domain: Agent domain.
        depth: Research depth (quick/standard/deep).
        triggered_by: What triggered this research.

    Returns:
        Dict with success and research metadata.
    """
    import time

    start = time.monotonic()

    try:
        from app.agents.research.tools.cost_tracker import (
            estimate_cost_usd,
            log_research_cost,
        )
        from app.agents.research.tools.graph_writer import (
            write_to_graph,
            write_to_vault,
        )
        from app.agents.research.tools.query_planner import plan_queries
        from app.agents.research.tools.synthesizer import synthesize_tracks
        from app.agents.research.tools.track_runner import run_tracks_parallel

        # Step 1: Plan queries
        plan = plan_queries(query=query, domain=domain, depth=depth)
        if not plan["success"]:
            return {"success": False, "error": "Query planning failed"}

        # Step 2: Run tracks in parallel
        track_results = await run_tracks_parallel(
            tracks=plan["tracks"],
            scrape_top_n=3 if depth != "quick" else 0,
        )

        # Step 3: Synthesize
        synthesis = synthesize_tracks(
            track_results=track_results,
            original_query=query,
            domain=domain,
        )

        if not synthesis["success"]:
            return {"success": False, "error": "Synthesis failed"}

        # Step 4: Write to graph
        graph_result = write_to_graph(synthesis=synthesis, domain=domain)

        # Step 5: Write to vault
        await write_to_vault(synthesis=synthesis, topic=query)

        # Step 6: Log cost
        duration_ms = int((time.monotonic() - start) * 1000)
        cost = estimate_cost_usd(
            searches=synthesis.get("search_count", 0),
            scrapes=synthesis.get("scrape_count", 0),
        )
        log_research_cost(
            domain=domain,
            query=query,
            depth=depth,
            tracks_run=len(plan["tracks"]),
            searches_used=synthesis.get("search_count", 0),
            scrapes_used=synthesis.get("scrape_count", 0),
            findings_count=len(synthesis.get("findings", [])),
            graph_updates=graph_result.get("entities_written", 0)
            + graph_result.get("findings_written", 0),
            triggered_by=triggered_by,
            duration_ms=duration_ms,
        )

        return {
            "success": True,
            "query": query,
            "domain": domain,
            "depth": depth,
            "findings": len(synthesis.get("findings", [])),
            "confidence": synthesis.get("confidence", 0),
            "cost_usd": cost,
            "duration_ms": duration_ms,
        }

    except Exception as e:
        logger.error("Research job failed for '%s' in %s: %s", query, domain, e)
        return {"success": False, "error": str(e)}


def _domain_to_agent_id(domain: str) -> str:
    """Map domain name to agent_id used in coverage_gaps table."""
    mapping = {
        "financial": "FIN",
        "content": "CON",
        "strategic": "STR",
        "sales": "SAL",
        "marketing": "MKT",
        "operations": "OPS",
        "hr": "HR",
        "compliance": "CMP",
        "customer_support": "CUS",
        "data": "DAT",
    }
    return mapping.get(domain, domain.upper()[:3])
