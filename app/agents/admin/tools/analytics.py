"""Analytics tools for the AdminAgent.

Provides 4 tools for querying usage analytics, agent effectiveness,
engagement data, and generating summary reports. Each tool enforces
the autonomy tier by querying admin_agent_permissions before executing.

All tools are read-only and default to ``auto`` tier.
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Autonomy enforcement helper (self-contained per project pattern)
# ---------------------------------------------------------------------------


async def _check_autonomy(action_name: str) -> dict | None:
    """Query admin_agent_permissions and return a gate dict if blocked/confirm.

    Returns None when execution should proceed (auto tier or unknown).

    Args:
        action_name: The tool function name registered in admin_agent_permissions.

    Returns:
        A ``{"error": ...}`` dict if blocked, a ``{"requires_confirmation": True, ...}``
        dict if confirmation is required, or None to proceed.
    """
    try:
        client = get_service_client()
        res = (
            client.table("admin_agent_permissions")
            .select("autonomy_level")
            .eq("action_name", action_name)
            .limit(1)
            .execute()
        )
        if res.data:
            level = res.data[0].get("autonomy_level", "auto")
            if level == "blocked":
                return {
                    "error": (
                        f"{action_name} is blocked by admin configuration. "
                        "Contact a super-admin to change the autonomy level."
                    )
                }
            if level == "confirm":
                token = str(uuid.uuid4())
                return {
                    "requires_confirmation": True,
                    "confirmation_token": token,
                    "action_details": {
                        "action": action_name,
                        "risk_level": "low",
                        "description": f"Read-only analytics operation: {action_name}",
                    },
                }
            # level == "auto" — proceed
    except Exception as exc:
        logger.warning(
            "Could not verify autonomy level for %s, defaulting to auto: %s",
            action_name,
            exc,
        )
    return None


# ---------------------------------------------------------------------------
# Tool 1: get_usage_stats
# ---------------------------------------------------------------------------


async def get_usage_stats(days: int = 30) -> dict[str, Any]:
    """Return daily usage statistics (DAU, MAU, messages, workflows).

    Queries ``admin_analytics_daily`` for the last ``days`` rows and builds
    a usage trends list plus a summary of key aggregate metrics.

    Autonomy tier: auto (read-only).

    Args:
        days: Number of past days to include (default 30).

    Returns:
        Dict with ``usage_trends`` list of daily stat dicts and ``summary``
        dict containing ``avg_dau``, ``latest_mau``, ``total_messages``,
        and ``total_workflows``. On confirm tier: returns confirmation
        request dict. On blocked tier: returns error dict.
    """
    gate = await _check_autonomy("get_usage_stats")
    if gate is not None:
        return gate

    client = get_service_client()

    try:
        query = (
            client.table("admin_analytics_daily")
            .select("stat_date, dau, mau, messages, workflows")
            .order("stat_date", desc=True)
            .limit(days)
        )
        result = await execute_async(query, op_name="get_usage_stats")
        rows: list[dict] = result.data or []

        usage_trends = [
            {
                "stat_date": row.get("stat_date"),
                "dau": row.get("dau", 0),
                "mau": row.get("mau", 0),
                "messages": row.get("messages", 0),
                "workflows": row.get("workflows", 0),
            }
            for row in rows
        ]

        if rows:
            avg_dau = round(
                sum(r.get("dau", 0) or 0 for r in rows) / len(rows), 1
            )
            latest_mau = rows[0].get("mau", 0) or 0
            total_messages = sum(r.get("messages", 0) or 0 for r in rows)
            total_workflows = sum(r.get("workflows", 0) or 0 for r in rows)
        else:
            avg_dau = 0
            latest_mau = 0
            total_messages = 0
            total_workflows = 0

        return {
            "usage_trends": usage_trends,
            "summary": {
                "avg_dau": avg_dau,
                "latest_mau": latest_mau,
                "total_messages": total_messages,
                "total_workflows": total_workflows,
            },
        }
    except Exception as exc:
        logger.error("get_usage_stats failed: %s", exc)
        return {"error": f"Failed to retrieve usage stats: {exc}"}


# ---------------------------------------------------------------------------
# Tool 2: get_agent_effectiveness
# ---------------------------------------------------------------------------


async def get_agent_effectiveness(days: int = 30) -> dict[str, Any]:
    """Return per-agent effectiveness metrics for the last ``days`` days.

    Queries ``admin_agent_stats_daily`` and aggregates success_rate and
    avg_duration_ms per agent across the requested date window.

    Autonomy tier: auto (read-only).

    Args:
        days: Number of past days to include (default 30).

    Returns:
        Dict with ``agents`` list, each entry containing ``agent_name``,
        ``success_rate``, ``avg_duration_ms``, and ``total_calls``.
        On confirm tier: returns confirmation request dict.
        On blocked tier: returns error dict.
    """
    gate = await _check_autonomy("get_agent_effectiveness")
    if gate is not None:
        return gate

    client = get_service_client()

    try:
        query = (
            client.table("admin_agent_stats_daily")
            .select(
                "agent_name, success_count, error_count, timeout_count, "
                "avg_duration_ms, total_calls, stat_date"
            )
            .order("stat_date", desc=True)
            .limit(days * 20)
        )
        result = await execute_async(query, op_name="get_agent_effectiveness")
        rows: list[dict] = result.data or []

        # Aggregate per-agent across all returned rows
        agent_buckets: dict[str, dict] = {}
        for row in rows:
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

        agents = []
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
            agents.append(
                {
                    "agent_name": agent_name,
                    "success_rate": success_rate,
                    "avg_duration_ms": avg_duration,
                    "total_calls": total,
                }
            )

        return {"agents": agents}
    except Exception as exc:
        logger.error("get_agent_effectiveness failed: %s", exc)
        return {"error": f"Failed to retrieve agent effectiveness: {exc}"}


# ---------------------------------------------------------------------------
# Tool 3: get_engagement_report
# ---------------------------------------------------------------------------


async def get_engagement_report(days: int = 30) -> dict[str, Any]:
    """Return feature usage breakdown by tool and event category.

    Queries ``tool_telemetry`` for the top 20 tools by call count and
    ``analytics_events`` by category for the last ``days`` days.

    Autonomy tier: auto (read-only).

    Args:
        days: Number of past days to include (default 30).

    Returns:
        Dict with ``top_tools`` list (tool_name, call_count), ``event_categories``
        list (category, event_count), and ``days`` int.
        On confirm tier: returns confirmation request dict.
        On blocked tier: returns error dict.
    """
    gate = await _check_autonomy("get_engagement_report")
    if gate is not None:
        return gate

    client = get_service_client()

    try:
        tool_query = (
            client.table("tool_telemetry")
            .select("tool_name")
            .order("tool_name")
            .limit(days * 100)
        )
        tool_result = await execute_async(tool_query, op_name="get_engagement_report.tools")
        tool_rows: list[dict] = tool_result.data or []

        tool_counter: Counter = Counter()
        for row in tool_rows:
            tool_name = row.get("tool_name")
            if tool_name:
                tool_counter[tool_name] += 1

        top_tools = [
            {"tool_name": name, "call_count": count}
            for name, count in tool_counter.most_common(20)
        ]

        event_query = (
            client.table("analytics_events")
            .select("category")
            .order("category")
            .limit(days * 500)
        )
        event_result = await execute_async(
            event_query, op_name="get_engagement_report.events"
        )
        event_rows: list[dict] = event_result.data or []

        event_counter: Counter = Counter()
        for row in event_rows:
            category = row.get("category")
            if category:
                event_counter[category] += 1

        event_categories = [
            {"category": cat, "event_count": count}
            for cat, count in event_counter.most_common()
        ]

        return {
            "top_tools": top_tools,
            "event_categories": event_categories,
            "days": days,
        }
    except Exception as exc:
        logger.error("get_engagement_report failed: %s", exc)
        return {"error": f"Failed to retrieve engagement report: {exc}"}


# ---------------------------------------------------------------------------
# Tool 4: generate_report
# ---------------------------------------------------------------------------


async def generate_report(days: int = 7) -> dict[str, Any]:
    """Generate a comprehensive analytics summary report.

    Calls ``get_usage_stats`` and ``get_agent_effectiveness`` internally and
    builds a human-readable ``summary_text`` alongside the raw data.

    Autonomy tier: auto (read-only).

    Args:
        days: Number of past days to cover (default 7).

    Returns:
        Dict with ``report`` containing ``period_days``, ``summary_text``,
        ``usage``, and ``agent_performance`` keys.
        On confirm tier: returns confirmation request dict.
        On blocked tier: returns error dict.
    """
    gate = await _check_autonomy("generate_report")
    if gate is not None:
        return gate

    try:
        usage_data = await get_usage_stats(days=days)
        agent_data = await get_agent_effectiveness(days=days)

        # Build summary text
        summary = usage_data.get("summary", {})
        agents = agent_data.get("agents", [])

        avg_dau = summary.get("avg_dau", 0)
        total_messages = summary.get("total_messages", 0)
        agent_count = len(agents)

        if agents:
            avg_success = round(
                sum(a.get("success_rate", 0) for a in agents) / agent_count, 1
            )
            best_agent = max(agents, key=lambda a: a.get("success_rate", 0))
            best_agent_name = best_agent.get("agent_name", "unknown")
            agent_summary = (
                f"{agent_count} agents tracked, avg success rate {avg_success}%. "
                f"Top performer: {best_agent_name} ({best_agent.get('success_rate', 0)}%)."
            )
        else:
            agent_summary = "No agent performance data available."

        summary_text = (
            f"Last {days} days: avg {avg_dau} DAU, {total_messages} messages. "
            f"{agent_summary}"
        )

        return {
            "report": {
                "period_days": days,
                "summary_text": summary_text,
                "usage": usage_data.get("summary", {}),
                "agent_performance": agents,
            }
        }
    except Exception as exc:
        logger.error("generate_report failed: %s", exc)
        return {"error": f"Failed to generate report: {exc}"}
