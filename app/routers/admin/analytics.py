"""Admin analytics API endpoints.

Provides:
- GET /admin/analytics/summary — aggregated usage, agent, feature, and config data
- POST /admin/analytics/aggregate — Cloud Scheduler entry point to run daily aggregation

The GET endpoint is gated by require_admin middleware.
The POST endpoint authenticates via WORKFLOW_SERVICE_SECRET (X-Service-Secret header),
NOT via require_admin, as it is called by Cloud Scheduler (service-to-service).
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.app_utils.auth import verify_service_auth
from app.middleware.admin_auth import require_admin
from app.middleware.rate_limiter import limiter
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/analytics/summary")
@limiter.limit("120/minute")
async def get_analytics_summary(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
    days: int = 30,
) -> dict[str, Any]:
    """Return aggregated analytics data for the admin dashboard.

    Reads from pre-aggregated summary tables (admin_analytics_daily,
    admin_agent_stats_daily) and live tables (tool_telemetry,
    analytics_events, admin_agent_permissions, admin_config_history)
    to build four sections: usage trends, agent effectiveness, feature
    usage, and config status.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin; confirms caller is an admin.
        days: Number of past days to include (default 30, max 365).

    Returns:
        JSON with ``usage_trends``, ``agent_effectiveness``,
        ``feature_usage``, ``config_status``, ``days``, and
        ``data_source`` fields. ``data_source`` is ``"aggregated"`` when
        summary tables have data, or ``"no_data"`` when empty.

    Raises:
        HTTPException 500: If a Supabase query fails.
    """
    client = get_service_client()

    try:
        # ------------------------------------------------------------------
        # 1. Usage trends — from admin_analytics_daily
        # ------------------------------------------------------------------
        usage_query = (
            client.table("admin_analytics_daily")
            .select("stat_date, dau, mau, messages, workflows")
            .order("stat_date", desc=True)
            .limit(days)
        )
        usage_result = await execute_async(usage_query, op_name="analytics.summary.usage")
        usage_rows: list[dict] = usage_result.data or []

        has_data = bool(usage_rows)

        usage_trends = [
            {
                "stat_date": row.get("stat_date"),
                "dau": row.get("dau", 0),
                "mau": row.get("mau", 0),
                "messages": row.get("messages", 0),
                "workflows": row.get("workflows", 0),
            }
            for row in usage_rows
        ]

        # ------------------------------------------------------------------
        # 2. Agent effectiveness — from admin_agent_stats_daily
        # ------------------------------------------------------------------
        agent_query = (
            client.table("admin_agent_stats_daily")
            .select(
                "agent_name, success_count, error_count, timeout_count, "
                "avg_duration_ms, total_calls, stat_date"
            )
            .order("stat_date", desc=True)
            .limit(days * 20)  # up to 20 agents per day
        )
        agent_result = await execute_async(agent_query, op_name="analytics.summary.agents")
        agent_rows: list[dict] = agent_result.data or []

        # Aggregate per-agent across all returned rows
        agent_buckets: dict[str, dict] = {}
        for row in agent_rows:
            name = row.get("agent_name") or "unknown"
            if name not in agent_buckets:
                agent_buckets[name] = {
                    "success_count": 0,
                    "total_calls": 0,
                    "_duration_sum": 0.0,
                    "_duration_count": 0,
                }
            bucket = agent_buckets[name]
            bucket["success_count"] += int(row.get("success_count") or 0)
            bucket["total_calls"] += int(row.get("total_calls") or 0)
            avg_ms = row.get("avg_duration_ms")
            total = int(row.get("total_calls") or 1)
            if avg_ms is not None:
                bucket["_duration_sum"] += float(avg_ms) * total
                bucket["_duration_count"] += total

        agent_effectiveness = []
        for agent_name, bucket in agent_buckets.items():
            total = bucket["total_calls"]
            success_rate = (
                round(bucket["success_count"] / total * 100, 2) if total > 0 else 0.0
            )
            avg_duration: float | None = None
            if bucket["_duration_count"] > 0:
                avg_duration = round(
                    bucket["_duration_sum"] / bucket["_duration_count"], 2
                )
            agent_effectiveness.append(
                {
                    "agent_name": agent_name,
                    "success_rate": success_rate,
                    "avg_duration_ms": avg_duration,
                    "total_calls": total,
                }
            )

        # ------------------------------------------------------------------
        # 3. Feature usage — tool_telemetry and analytics_events
        # ------------------------------------------------------------------
        tool_query = (
            client.table("tool_telemetry")
            .select("tool_name")
            .order("tool_name")
            .limit(days * 100)
        )
        tool_result = await execute_async(tool_query, op_name="analytics.summary.tools")
        tool_rows: list[dict] = tool_result.data or []

        # Count occurrences per tool_name in Python
        tool_counter: Counter = Counter()
        for row in tool_rows:
            tool_name = row.get("tool_name")
            if tool_name:
                tool_counter[tool_name] += 1

        # If the result already contains call_count (pre-aggregated mock), use it
        if tool_rows and "call_count" in tool_rows[0]:
            by_tool = [
                {"tool_name": r.get("tool_name"), "call_count": r.get("call_count", 0)}
                for r in tool_rows
            ]
        else:
            by_tool = [
                {"tool_name": name, "call_count": count}
                for name, count in tool_counter.most_common(20)
            ]

        max_event_rows = min(days * 500, 10_000)  # Cap to prevent OOM on large date ranges
        event_query = (
            client.table("analytics_events")
            .select("category")
            .order("category")
            .limit(max_event_rows)
        )
        event_result = await execute_async(
            event_query, op_name="analytics.summary.events"
        )
        event_rows: list[dict] = event_result.data or []

        # Count occurrences per category in Python
        event_counter: Counter = Counter()
        for row in event_rows:
            category = row.get("category")
            if category:
                event_counter[category] += 1

        # If the result already contains event_count (pre-aggregated mock), use it
        if event_rows and "event_count" in event_rows[0]:
            by_category = [
                {
                    "category": r.get("category"),
                    "event_count": r.get("event_count", 0),
                }
                for r in event_rows
            ]
        else:
            by_category = [
                {"category": cat, "event_count": count}
                for cat, count in event_counter.most_common()
            ]

        feature_usage = {
            "by_tool": by_tool,
            "by_category": by_category,
        }

        # ------------------------------------------------------------------
        # 4. Config status — admin_agent_permissions + admin_config_history
        # ------------------------------------------------------------------
        perm_query = (
            client.table("admin_agent_permissions")
            .select("autonomy_level")
            .order("autonomy_level")
        )
        perm_result = await execute_async(
            perm_query, op_name="analytics.summary.permissions"
        )
        perm_rows: list[dict] = perm_result.data or []

        # Count permissions by autonomy_level
        perm_counts: dict[str, int] = {}
        for row in perm_rows:
            level = row.get("autonomy_level", "auto")
            perm_counts[level] = perm_counts.get(level, 0) + 1

        config_history_query = (
            client.table("admin_config_history")
            .select("created_at")
            .order("created_at", desc=True)
            .limit(1)
        )
        config_result = await execute_async(
            config_history_query, op_name="analytics.summary.config_history"
        )
        config_rows: list[dict] = config_result.data or []
        last_config_change: str | None = (
            config_rows[0].get("created_at") if config_rows else None
        )

        config_status = {
            "permission_counts": perm_counts,
            "last_config_change": last_config_change,
        }

        # ------------------------------------------------------------------
        # Build and return response
        # ------------------------------------------------------------------
        data_source = "aggregated" if has_data else "no_data"

        return {
            "usage_trends": usage_trends,
            "agent_effectiveness": agent_effectiveness,
            "feature_usage": feature_usage,
            "config_status": config_status,
            "days": days,
            "data_source": data_source,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to query analytics summary: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve analytics summary",
        ) from exc


@router.post("/analytics/aggregate")
@limiter.limit("5/minute")
async def trigger_analytics_aggregate(
    request: Request,
    _auth: bool = Depends(verify_service_auth),
) -> dict[str, Any]:
    """Cloud Scheduler entry point — runs daily analytics aggregation.

    Triggered by Cloud Scheduler. Authenticates via X-Service-Secret
    header (WORKFLOW_SERVICE_SECRET), then delegates to
    run_daily_aggregation() which computes and upserts analytics
    aggregates into summary tables.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        _auth: Injected by verify_service_auth; confirms X-Service-Secret is valid.

    Returns:
        JSON with ``status`` ("ok"), ``date`` (str), and
        ``rows_written`` (int).

    Raises:
        HTTPException 401: If X-Service-Secret header is missing or invalid.
        HTTPException 500: If WORKFLOW_SERVICE_SECRET is not configured.
    """
    from app.services.analytics_aggregator import run_daily_aggregation

    result = await run_daily_aggregation()
    return {
        "status": "ok",
        "date": result["date"],
        "rows_written": result["rows_written"],
    }
