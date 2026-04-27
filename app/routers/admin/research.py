# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Admin endpoints for Research Intelligence monitoring and management.

Provides:
- Overview dashboard stats (graph size, freshness, cost MTD)
- Cost breakdown by service, domain, trigger type
- Knowledge graph entity search and detail
- Scheduler management (watch topics, budgets)
- Research history log with CSV export
"""

import csv
import logging
from datetime import datetime, timedelta, timezone
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.middleware.admin_auth import require_admin
from app.middleware.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_client():
    """Get Supabase service client (bypasses RLS)."""
    from app.services.supabase import get_service_client

    return get_service_client()


async def _exec(query, op_name: str):
    """Execute async Supabase query."""
    from app.services.supabase_async import execute_async

    return await execute_async(query, op_name=op_name)


# ─── OVERVIEW ────────────────────────────────────────────────────────


@router.get("/research/overview")
@limiter.limit("120/minute")
async def get_research_overview(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Dashboard overview: graph size, freshness score, cost MTD, research jobs today.

    Returns:
        JSON with kpi_cards, domain_health, and recent_events.
    """
    client = _get_client()

    try:
        # Graph size
        entities = await _exec(
            client.table("kg_entities").select("id", count="exact").limit(0),
            "research.overview.entities",
        )
        edges = await _exec(
            client.table("kg_edges").select("id", count="exact").limit(0),
            "research.overview.edges",
        )
        findings = await _exec(
            client.table("kg_findings").select("id", count="exact").limit(0),
            "research.overview.findings",
        )

        # Cost MTD
        now = datetime.now(tz=timezone.utc)
        month_start = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        cost_resp = await _exec(
            client.table("kg_research_log")
            .select("cost_usd")
            .gte("created_at", month_start),
            "research.overview.cost_mtd",
        )
        cost_mtd = sum(float(r["cost_usd"]) for r in (cost_resp.data or []))

        # Budget
        budget_resp = await _exec(
            client.table("kg_domain_budgets")
            .select("monthly_budget")
            .eq("is_active", True),
            "research.overview.budget",
        )
        total_budget = sum(float(r["monthly_budget"]) for r in (budget_resp.data or []))

        # Research jobs today
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        jobs_today = await _exec(
            client.table("kg_research_log")
            .select("id", count="exact")
            .gte("created_at", today_start)
            .limit(0),
            "research.overview.jobs_today",
        )

        # Domain health
        from app.agents.research.config import DOMAIN_FRESHNESS

        domain_health = []
        for domain, config in DOMAIN_FRESHNESS.items():
            threshold = config["default_hours"]
            stale_cutoff = (now - timedelta(hours=threshold)).isoformat()

            total_resp = await _exec(
                client.table("kg_entities")
                .select("id", count="exact")
                .contains("domains", [domain])
                .limit(0),
                f"research.overview.domain.{domain}.total",
            )
            fresh_resp = await _exec(
                client.table("kg_entities")
                .select("id", count="exact")
                .contains("domains", [domain])
                .gte("freshness_at", stale_cutoff)
                .limit(0),
                f"research.overview.domain.{domain}.fresh",
            )
            total_count = total_resp.count or 0
            fresh_count = fresh_resp.count or 0
            freshness_pct = (
                (fresh_count / total_count * 100) if total_count > 0 else 100
            )

            # Last research
            last_resp = await _exec(
                client.table("kg_research_log")
                .select("created_at")
                .eq("domain", domain)
                .order("created_at", desc=True)
                .limit(1),
                f"research.overview.domain.{domain}.last",
            )
            last_research = last_resp.data[0]["created_at"] if last_resp.data else None

            domain_health.append(
                {
                    "domain": domain,
                    "total_entities": total_count,
                    "fresh_entities": fresh_count,
                    "freshness_pct": round(freshness_pct, 1),
                    "last_research": last_research,
                }
            )

        return {
            "graph_size": {
                "entities": entities.count or 0,
                "edges": edges.count or 0,
                "findings": findings.count or 0,
            },
            "cost_mtd": round(cost_mtd, 2),
            "total_budget": round(total_budget, 2),
            "jobs_today": jobs_today.count or 0,
            "domain_health": domain_health,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Research overview failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to load research overview"
        ) from exc


# ─── COSTS ───────────────────────────────────────────────────────────


@router.get("/research/costs")
@limiter.limit("120/minute")
async def get_research_costs(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    """Cost breakdown by service, domain, and trigger type.

    Args:
        days: Analysis window in days (default 30).

    Returns:
        JSON with by_domain, by_trigger, total_cost, total_searches, total_scrapes.
    """
    client = _get_client()

    try:
        cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()
        resp = await _exec(
            client.table("kg_research_log")
            .select(
                "domain, triggered_by, cost_usd, searches_used, scrapes_used, depth"
            )
            .gte("created_at", cutoff),
            "research.costs",
        )
        logs = resp.data or []

        # Aggregate by domain
        by_domain: dict[str, dict] = {}
        for log in logs:
            domain = log["domain"]
            if domain not in by_domain:
                by_domain[domain] = {
                    "cost": 0,
                    "searches": 0,
                    "scrapes": 0,
                    "jobs": 0,
                }
            by_domain[domain]["cost"] += float(log["cost_usd"])
            by_domain[domain]["searches"] += log["searches_used"]
            by_domain[domain]["scrapes"] += log["scrapes_used"]
            by_domain[domain]["jobs"] += 1

        # Aggregate by trigger
        by_trigger: dict[str, dict] = {}
        for log in logs:
            trigger = log["triggered_by"]
            if trigger not in by_trigger:
                by_trigger[trigger] = {"cost": 0, "jobs": 0}
            by_trigger[trigger]["cost"] += float(log["cost_usd"])
            by_trigger[trigger]["jobs"] += 1

        total_cost = sum(float(log["cost_usd"]) for log in logs)
        total_searches = sum(log["searches_used"] for log in logs)
        total_scrapes = sum(log["scrapes_used"] for log in logs)

        return {
            "days": days,
            "by_domain": {
                k: {**v, "cost": round(v["cost"], 4)} for k, v in by_domain.items()
            },
            "by_trigger": {
                k: {**v, "cost": round(v["cost"], 4)} for k, v in by_trigger.items()
            },
            "total_cost": round(total_cost, 4),
            "total_searches": total_searches,
            "total_scrapes": total_scrapes,
            "total_jobs": len(logs),
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Research costs query failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to load research costs"
        ) from exc


@router.get("/research/costs/daily")
@limiter.limit("120/minute")
async def get_daily_cost_trend(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
    days: int = Query(default=14, ge=1, le=90),
) -> dict:
    """Daily cost trend for chart display.

    Returns:
        JSON with list of {date, cost, searches, scrapes, jobs} per day.
    """
    client = _get_client()

    try:
        cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()
        resp = await _exec(
            client.table("kg_research_log")
            .select("created_at, cost_usd, searches_used, scrapes_used")
            .gte("created_at", cutoff)
            .order("created_at"),
            "research.costs.daily",
        )

        # Group by date
        daily: dict[str, dict] = {}
        for log in resp.data or []:
            date = log["created_at"][:10]  # YYYY-MM-DD
            if date not in daily:
                daily[date] = {
                    "date": date,
                    "cost": 0,
                    "searches": 0,
                    "scrapes": 0,
                    "jobs": 0,
                }
            daily[date]["cost"] += float(log["cost_usd"])
            daily[date]["searches"] += log["searches_used"]
            daily[date]["scrapes"] += log["scrapes_used"]
            daily[date]["jobs"] += 1

        trend = sorted(daily.values(), key=lambda d: d["date"])
        for d in trend:
            d["cost"] = round(d["cost"], 4)

        return {"days": days, "trend": trend}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Daily cost trend failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to load daily cost trend"
        ) from exc


# ─── GRAPH EXPLORER ──────────────────────────────────────────────────


@router.get("/research/graph/stats")
@limiter.limit("120/minute")
async def get_graph_stats(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Knowledge graph statistics per domain."""
    client = _get_client()

    try:
        from app.agents.research.config import DOMAIN_FRESHNESS

        stats = []
        for domain in DOMAIN_FRESHNESS:
            entities_resp = await _exec(
                client.table("kg_entities")
                .select("id", count="exact")
                .contains("domains", [domain])
                .limit(0),
                f"research.graph.stats.{domain}",
            )
            findings_resp = await _exec(
                client.table("kg_findings")
                .select("id", count="exact")
                .eq("domain", domain)
                .limit(0),
                f"research.graph.findings.{domain}",
            )
            stats.append(
                {
                    "domain": domain,
                    "entities": entities_resp.count or 0,
                    "findings": findings_resp.count or 0,
                }
            )

        return {"domains": stats}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Graph stats failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to load graph stats"
        ) from exc


@router.get("/research/graph/entity/{entity_id}")
@limiter.limit("120/minute")
async def get_entity_detail(
    request: Request,
    entity_id: str,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Full entity detail with relationships and findings."""
    client = _get_client()

    try:
        entity_resp = await _exec(
            client.table("kg_entities").select("*").eq("id", entity_id),
            "research.graph.entity",
        )
        if not entity_resp.data:
            raise HTTPException(status_code=404, detail="Entity not found")

        entity = entity_resp.data[0]

        # Get aliases
        aliases_resp = await _exec(
            client.table("kg_aliases")
            .select("alias, confidence")
            .eq("entity_id", entity_id),
            "research.graph.aliases",
        )

        # Get relationships
        edges_resp = await _exec(
            client.table("kg_edges")
            .select("id, relationship, target_id, domain, confidence, evidence")
            .eq("source_id", entity_id),
            "research.graph.edges",
        )

        # Get findings across all domains
        findings_resp = await _exec(
            client.table("kg_findings")
            .select("id, domain, finding_text, confidence, sources, freshness_at")
            .eq("entity_id", entity_id)
            .order("confidence", desc=True)
            .limit(20),
            "research.graph.findings",
        )

        return {
            "entity": entity,
            "aliases": aliases_resp.data or [],
            "relationships": edges_resp.data or [],
            "findings": findings_resp.data or [],
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Entity detail failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load entity") from exc


@router.post("/research/graph/search")
@limiter.limit("60/minute")
async def search_entities(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Search entities by name (case-insensitive)."""
    body = await request.json()
    query = body.get("query", "")
    limit = min(body.get("limit", 20), 50)

    if not query:
        raise HTTPException(status_code=400, detail="Query required")

    client = _get_client()

    try:
        resp = await _exec(
            client.table("kg_entities")
            .select(
                "id, canonical_name, entity_type, domains, source_count, freshness_at"
            )
            .ilike("canonical_name", f"%{query}%")
            .order("source_count", desc=True)
            .limit(limit),
            "research.graph.search",
        )

        return {"results": resp.data or [], "query": query}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Entity search failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Search failed") from exc


@router.post("/research/graph/refresh")
@limiter.limit("10/minute")
async def force_refresh_entity(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Force a research refresh for a specific entity."""
    body = await request.json()
    entity_id = body.get("entity_id")
    if not entity_id:
        raise HTTPException(status_code=400, detail="entity_id required")

    client = _get_client()

    try:
        entity_resp = await _exec(
            client.table("kg_entities")
            .select("canonical_name, domains")
            .eq("id", entity_id),
            "research.graph.refresh.lookup",
        )
        if not entity_resp.data:
            raise HTTPException(status_code=404, detail="Entity not found")

        entity = entity_resp.data[0]
        domain = entity["domains"][0] if entity["domains"] else "strategic"

        from app.services.research_event_bus import get_event_bus

        bus = get_event_bus()
        result = await bus.emit(
            topic=entity["canonical_name"],
            domain=domain,
            trigger_type="stale_access",
            suggested_depth="deep",
            priority="critical",
            source_agent="admin",
        )

        from app.services.admin_audit import log_admin_action

        await log_admin_action(
            admin_user_id=admin_user["id"],
            action="force_refresh_entity",
            target_type="kg_entity",
            target_id=entity_id,
            source="manual",
            changes={
                "entity": entity["canonical_name"],
                "domain": domain,
            },
            admin_user_email=admin_user.get("email", ""),
        )

        return {
            "success": True,
            "entity": entity["canonical_name"],
            "event": result,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Force refresh failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Refresh failed") from exc


@router.delete("/research/graph/entity/{entity_id}")
@limiter.limit("10/minute")
async def delete_entity(
    request: Request,
    entity_id: str,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Delete an entity and its associated findings/edges (CASCADE)."""
    client = _get_client()

    try:
        entity_resp = await _exec(
            client.table("kg_entities").select("canonical_name").eq("id", entity_id),
            "research.graph.delete.lookup",
        )
        if not entity_resp.data:
            raise HTTPException(status_code=404, detail="Entity not found")

        entity_name = entity_resp.data[0]["canonical_name"]

        await _exec(
            client.table("kg_entities").delete().eq("id", entity_id),
            "research.graph.delete",
        )

        from app.services.admin_audit import log_admin_action

        await log_admin_action(
            admin_user_id=admin_user["id"],
            action="delete_entity",
            target_type="kg_entity",
            target_id=entity_id,
            source="manual",
            changes={"entity": entity_name},
            admin_user_email=admin_user.get("email", ""),
        )

        return {"success": True, "deleted": entity_name}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Entity delete failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Delete failed") from exc


# ─── SCHEDULER MANAGEMENT ───────────────────────────────────────────


@router.get("/research/scheduler")
@limiter.limit("120/minute")
async def get_scheduler_status(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Scheduler status: domain schedules, event bus status."""
    client = _get_client()

    try:
        budgets_resp = await _exec(
            client.table("kg_domain_budgets")
            .select("*")
            .order("monthly_budget", desc=True),
            "research.scheduler.budgets",
        )

        return {"schedules": budgets_resp.data or []}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Scheduler status failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load scheduler") from exc


@router.put("/research/scheduler/{domain}")
@limiter.limit("30/minute")
async def update_domain_schedule(
    request: Request,
    domain: str,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Update a domain's schedule configuration."""
    body = await request.json()
    client = _get_client()

    try:
        updates = {}
        if "schedule_cron" in body:
            updates["schedule_cron"] = body["schedule_cron"]
        if "is_active" in body:
            updates["is_active"] = body["is_active"]

        if not updates:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        await _exec(
            client.table("kg_domain_budgets").update(updates).eq("domain", domain),
            "research.scheduler.update",
        )

        return {"success": True, "domain": domain, "updated": updates}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Schedule update failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Update failed") from exc


# ─── WATCH TOPICS ────────────────────────────────────────────────────


@router.get("/research/watch-topics")
@limiter.limit("120/minute")
async def list_watch_topics(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
    domain: str | None = Query(default=None),
) -> dict:
    """List watch topics, optionally filtered by domain."""
    client = _get_client()

    try:
        query = client.table("kg_watch_topics").select("*").order("priority")
        if domain:
            query = query.eq("domain", domain)

        resp = await _exec(query, "research.watch_topics.list")
        return {"topics": resp.data or []}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Watch topics list failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to load watch topics"
        ) from exc


@router.post("/research/watch-topics")
@limiter.limit("30/minute")
async def create_watch_topic(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Create a new watch topic."""
    body = await request.json()
    client = _get_client()

    topic = body.get("topic", "").strip()
    domain = body.get("domain", "").strip()
    priority = body.get("priority", "medium")

    if not topic or not domain:
        raise HTTPException(status_code=400, detail="topic and domain required")

    try:
        resp = await _exec(
            client.table("kg_watch_topics").insert(
                {
                    "topic": topic,
                    "domain": domain,
                    "priority": priority,
                    "created_by": admin_user["id"],
                }
            ),
            "research.watch_topics.create",
        )

        return {
            "success": True,
            "topic": resp.data[0] if resp.data else None,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Watch topic create failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to create watch topic"
        ) from exc


@router.put("/research/watch-topics/{topic_id}")
@limiter.limit("30/minute")
async def update_watch_topic(
    request: Request,
    topic_id: str,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Update a watch topic (priority, is_active)."""
    body = await request.json()
    client = _get_client()

    try:
        updates = {}
        for field in ("topic", "priority", "is_active"):
            if field in body:
                updates[field] = body[field]

        if not updates:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        await _exec(
            client.table("kg_watch_topics").update(updates).eq("id", topic_id),
            "research.watch_topics.update",
        )

        return {"success": True, "updated": updates}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Watch topic update failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Update failed") from exc


@router.delete("/research/watch-topics/{topic_id}")
@limiter.limit("10/minute")
async def delete_watch_topic(
    request: Request,
    topic_id: str,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Delete a watch topic."""
    client = _get_client()

    try:
        await _exec(
            client.table("kg_watch_topics").delete().eq("id", topic_id),
            "research.watch_topics.delete",
        )
        return {"success": True, "deleted": topic_id}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Watch topic delete failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Delete failed") from exc


# ─── BUDGETS ─────────────────────────────────────────────────────────


@router.get("/research/budgets")
@limiter.limit("120/minute")
async def get_budgets(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Get budget configuration per domain with current spend."""
    client = _get_client()

    try:
        budgets_resp = await _exec(
            client.table("kg_domain_budgets").select("*"),
            "research.budgets",
        )
        budgets = budgets_resp.data or []

        # Get current month spend per domain
        now = datetime.now(tz=timezone.utc)
        month_start = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        ).isoformat()

        spend_resp = await _exec(
            client.table("kg_research_log")
            .select("domain, cost_usd")
            .gte("created_at", month_start),
            "research.budgets.spend",
        )

        spend_by_domain: dict[str, float] = {}
        for log in spend_resp.data or []:
            d = log["domain"]
            spend_by_domain[d] = spend_by_domain.get(d, 0) + float(log["cost_usd"])

        for budget in budgets:
            budget["current_spend"] = round(spend_by_domain.get(budget["domain"], 0), 4)
            budget["budget_pct"] = (
                round(
                    budget["current_spend"] / float(budget["monthly_budget"]) * 100,
                    1,
                )
                if float(budget["monthly_budget"]) > 0
                else 0
            )

        return {"budgets": budgets}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Budgets query failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load budgets") from exc


@router.put("/research/budgets/{domain}")
@limiter.limit("30/minute")
async def update_budget(
    request: Request,
    domain: str,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Update a domain's budget configuration."""
    body = await request.json()
    client = _get_client()

    try:
        updates = {}
        for field in ("monthly_budget", "alert_threshold", "auto_pause"):
            if field in body:
                updates[field] = body[field]

        if not updates:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        await _exec(
            client.table("kg_domain_budgets").update(updates).eq("domain", domain),
            "research.budgets.update",
        )

        from app.services.admin_audit import log_admin_action

        await log_admin_action(
            admin_user_id=admin_user["id"],
            action="update_research_budget",
            target_type="kg_domain_budget",
            target_id=domain,
            source="manual",
            changes=updates,
            admin_user_email=admin_user.get("email", ""),
        )

        return {"success": True, "domain": domain, "updated": updates}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Budget update failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Update failed") from exc


# ─── RESEARCH HISTORY ────────────────────────────────────────────────


@router.get("/research/history")
@limiter.limit("120/minute")
async def get_research_history(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
    domain: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Research execution log with pagination and optional domain filter."""
    client = _get_client()

    try:
        query = (
            client.table("kg_research_log")
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if domain:
            query = query.eq("domain", domain)

        resp = await _exec(query, "research.history")

        return {
            "history": resp.data or [],
            "limit": limit,
            "offset": offset,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Research history failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load history") from exc


@router.get("/research/history/export", response_class=StreamingResponse)
@limiter.limit("5/minute")
async def export_research_history(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
    days: int = Query(default=30, ge=1, le=365),
):
    """Export research history as CSV."""
    client = _get_client()

    try:
        cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()
        resp = await _exec(
            client.table("kg_research_log")
            .select("*")
            .gte("created_at", cutoff)
            .order("created_at", desc=True),
            "research.history.export",
        )
        rows = resp.data or []

        if not rows:
            raise HTTPException(status_code=204, detail="No data to export")

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=research_history_{days}d.csv"
            },
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("History export failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Export failed") from exc


# ─── FLYWHEEL HEALTH ─────────────────────────────────────────────────


@router.get("/research/flywheel")
@limiter.limit("120/minute")
async def get_flywheel_health(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Research impact analysis: research vs non-research scores per domain."""
    try:
        from app.services.research_impact_analyzer import (
            analyze_research_impact,
            generate_skill_recommendations,
        )

        analysis = analyze_research_impact(days=30)
        recommendations = []
        if analysis.get("success") and analysis.get("domains"):
            recommendations = generate_skill_recommendations(analysis["domains"])

        return {
            "impact": analysis.get("domains", {}),
            "recommendations": recommendations,
        }

    except Exception as exc:
        logger.error("Flywheel health failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to load flywheel health"
        ) from exc
