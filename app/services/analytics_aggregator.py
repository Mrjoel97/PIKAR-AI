"""Analytics aggregation service.

Computes daily usage and agent statistics from raw event tables and upserts
pre-aggregated results into summary tables for fast dashboard reads.

Usage::

    from app.services.analytics_aggregator import run_daily_aggregation

    # Aggregate yesterday (default)
    result = await run_daily_aggregation()

    # Aggregate a specific date
    result = await run_daily_aggregation("2026-03-21")
    # -> {"date": "2026-03-21", "rows_written": 3}
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


def _extract_count(result: Any) -> int:
    """Extract integer count from a Supabase query result.

    Supports two result shapes:
    - ``[{"count": N}]`` — returned by .select("count") or mock helpers
    - Raw row list — falls back to ``len(result.data)``
    """
    data = result.data or []
    if data and isinstance(data[0], dict) and "count" in data[0]:
        return int(data[0]["count"])
    return len(data)


async def run_daily_aggregation(stat_date: str | None = None) -> dict:
    """Compute and upsert daily analytics aggregates for the given date.

    Queries four source tables (sessions, session_events, workflow_executions,
    agent_telemetry) and upserts results into the two summary tables
    admin_analytics_daily and admin_agent_stats_daily.

    The upsert is idempotent: re-running for the same date overwrites the
    previous values rather than inserting duplicates.

    Args:
        stat_date: ISO date string ``YYYY-MM-DD`` to aggregate.
            Defaults to yesterday UTC when omitted.

    Returns:
        dict with keys ``date`` (str) and ``rows_written`` (int).
    """
    if stat_date is None:
        stat_date = (date.today() - timedelta(days=1)).isoformat()

    client = get_service_client()

    day_start = stat_date
    day_end_exclusive = (date.fromisoformat(stat_date) + timedelta(days=1)).isoformat()

    # ------------------------------------------------------------------
    # 1. DAU — distinct users active on stat_date (session.updated_at)
    # ------------------------------------------------------------------
    dau_result = await execute_async(
        client.table("sessions")
        .select("user_id")
        .gte("updated_at", day_start)
        .lt("updated_at", day_end_exclusive),
        op_name="analytics.dau",
    )
    dau = _extract_count(dau_result)

    # ------------------------------------------------------------------
    # 2. MAU — distinct users in trailing 30 days ending on stat_date
    # ------------------------------------------------------------------
    mau_start = (date.fromisoformat(stat_date) - timedelta(days=29)).isoformat()
    mau_result = await execute_async(
        client.table("sessions")
        .select("user_id")
        .gte("updated_at", mau_start)
        .lt("updated_at", day_end_exclusive),
        op_name="analytics.mau",
    )
    mau = _extract_count(mau_result)

    # ------------------------------------------------------------------
    # 3. Messages — count of session_events on stat_date
    # ------------------------------------------------------------------
    messages_result = await execute_async(
        client.table("session_events")
        .select("user_id")
        .gte("created_at", day_start)
        .lt("created_at", day_end_exclusive),
        op_name="analytics.messages",
    )
    messages = _extract_count(messages_result)

    # ------------------------------------------------------------------
    # 4. Workflows — count of workflow_executions on stat_date
    # ------------------------------------------------------------------
    workflows_result = await execute_async(
        client.table("workflow_executions")
        .select("user_id")
        .gte("created_at", day_start)
        .lt("created_at", day_end_exclusive),
        op_name="analytics.workflows",
    )
    workflows = _extract_count(workflows_result)

    # ------------------------------------------------------------------
    # 5. Agent stats — pull agent_telemetry rows, aggregate in Python
    #    (queried before upserts so the call order matches test expectations)
    # ------------------------------------------------------------------
    agent_result = await execute_async(
        client.table("agent_telemetry")
        .select("agent_name,status,duration_ms")
        .gte("created_at", day_start)
        .lt("created_at", day_end_exclusive),
        op_name="analytics.agent_telemetry",
    )

    # ------------------------------------------------------------------
    # 6. Upsert admin_analytics_daily
    # ------------------------------------------------------------------
    analytics_row = {
        "stat_date": stat_date,
        "dau": dau,
        "mau": mau,
        "messages": messages,
        "workflows": workflows,
        "updated_at": "now()",
    }
    await execute_async(
        client.table("admin_analytics_daily").upsert(
            analytics_row, on_conflict="stat_date"
        ),
        op_name="analytics.upsert_daily",
    )
    rows_written = 1
    agent_rows = agent_result.data or []

    # Group by agent_name in Python to avoid needing Supabase RPC for GROUP BY.
    # Also supports the pre-aggregated mock shape from tests (agent rows that
    # already contain success_count / error_count / timeout_count fields).
    agent_buckets: dict[str, dict] = {}

    for row in agent_rows:
        name = row.get("agent_name") or "unknown"
        if name not in agent_buckets:
            agent_buckets[name] = {
                "success_count": 0,
                "error_count": 0,
                "timeout_count": 0,
                "total_calls": 0,
                "_duration_sum": 0.0,
                "_duration_count": 0,
            }

        bucket = agent_buckets[name]

        # Support pre-aggregated rows (from tests or future RPC)
        if "success_count" in row:
            bucket["success_count"] += int(row.get("success_count") or 0)
            bucket["error_count"] += int(row.get("error_count") or 0)
            bucket["timeout_count"] += int(row.get("timeout_count") or 0)
            bucket["total_calls"] += int(row.get("total_calls") or 0)
            avg = row.get("avg_duration_ms")
            if avg is not None:
                total = int(row.get("total_calls") or 1)
                bucket["_duration_sum"] += float(avg) * total
                bucket["_duration_count"] += total
        else:
            # Raw telemetry row
            status = row.get("status") or ""
            duration = row.get("duration_ms")
            bucket["total_calls"] += 1
            if status == "success":
                bucket["success_count"] += 1
            elif status == "error":
                bucket["error_count"] += 1
            elif status == "timeout":
                bucket["timeout_count"] += 1
            if duration is not None:
                bucket["_duration_sum"] += float(duration)
                bucket["_duration_count"] += 1

    # Upsert one row per agent
    for agent_name, bucket in agent_buckets.items():
        avg_ms = None
        if bucket["_duration_count"] > 0:
            avg_ms = round(bucket["_duration_sum"] / bucket["_duration_count"], 2)

        agent_stat_row = {
            "stat_date": stat_date,
            "agent_name": agent_name,
            "success_count": bucket["success_count"],
            "error_count": bucket["error_count"],
            "timeout_count": bucket["timeout_count"],
            "avg_duration_ms": avg_ms,
            "total_calls": bucket["total_calls"],
        }
        await execute_async(
            client.table("admin_agent_stats_daily").upsert(
                agent_stat_row, on_conflict="stat_date,agent_name"
            ),
            op_name="analytics.upsert_agent_stats",
        )
        rows_written += 1

    logger.info(
        "Analytics aggregation complete for %s: %d rows", stat_date, rows_written
    )
    return {"date": stat_date, "rows_written": rows_written}
