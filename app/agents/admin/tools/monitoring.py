# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Monitoring tools for the AdminAgent.

Provides 7 read-only tools for querying API health status, incident history,
and diagnostics. Each tool enforces the autonomy tier by querying
admin_agent_permissions before executing.

All tools are read-only and default to ``auto`` tier.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Autonomy enforcement helper
# ---------------------------------------------------------------------------


from app.agents.admin.tools._autonomy import check_autonomy as _check_autonomy

# ---------------------------------------------------------------------------
# Tool 1: get_api_health_summary
# ---------------------------------------------------------------------------


async def get_api_health_summary() -> dict[str, Any]:
    """Return a summary of current health status for all monitored endpoints.

    Queries the latest row per endpoint from ``api_health_checks`` and builds
    a plain-language summary string indicating overall platform health.

    Autonomy tier: auto (read-only).

    Returns:
        Dict with ``endpoints`` list (name, status, response_time_ms),
        ``overall_health`` string (``healthy``, ``degraded``, ``unhealthy``),
        and ``summary`` string suitable for display in the admin chat.
        On confirm tier: returns confirmation request dict.
        On blocked tier: returns error dict.
    """
    gate = await _check_autonomy("get_api_health_summary")
    if gate is not None:
        return gate

    _ACTION_NAME = "get_api_health_summary"
    _ENDPOINT_NAMES = ["live", "connections", "cache", "embeddings", "video"]

    client = get_service_client()
    endpoint_statuses: list[dict] = []

    try:
        # Fetch all endpoints in parallel instead of sequentially
        async def _fetch_endpoint(name: str) -> dict:
            query = (
                client.table("api_health_checks")
                .select("status, response_time_ms, checked_at")
                .eq("endpoint", name)
                .order("checked_at", desc=True)
                .limit(1)
            )
            result = await execute_async(query, op_name=f"{_ACTION_NAME}.{name}")
            rows: list[dict] = result.data or []
            if rows:
                row = rows[0]
                return {
                    "name": name,
                    "status": row.get("status", "unknown"),
                    "response_time_ms": row.get("response_time_ms"),
                    "checked_at": row.get("checked_at"),
                }
            return {
                "name": name,
                "status": "unknown",
                "response_time_ms": None,
                "checked_at": None,
            }

        import asyncio

        endpoint_statuses = list(
            await asyncio.gather(*[_fetch_endpoint(name) for name in _ENDPOINT_NAMES])
        )

        # Determine overall health
        statuses = [ep["status"] for ep in endpoint_statuses]
        if all(s == "healthy" for s in statuses):
            overall = "healthy"
        elif any(s in ("unhealthy", "unknown") for s in statuses):
            overall = "unhealthy"
        else:
            overall = "degraded"

        healthy_count = sum(1 for s in statuses if s == "healthy")
        total_count = len(statuses)
        summary = f"{healthy_count}/{total_count} endpoints healthy"

        unhealthy = [
            ep["name"] for ep in endpoint_statuses if ep["status"] not in ("healthy",)
        ]
        if unhealthy:
            summary += f". Issues: {', '.join(unhealthy)}"

        return {
            "endpoints": endpoint_statuses,
            "overall_health": overall,
            "summary": summary,
        }
    except Exception as exc:
        logger.error("get_api_health_summary failed: %s", exc)
        return {"error": f"Failed to retrieve health summary: {exc}"}


# ---------------------------------------------------------------------------
# Tool 2: get_api_health_history
# ---------------------------------------------------------------------------


async def get_api_health_history(
    endpoint: str,
    period: str = "24h",
) -> dict[str, Any]:
    """Return trend data for a specific monitored endpoint over a time window.

    Args:
        endpoint: Endpoint name key — one of ``live``, ``connections``,
            ``cache``, ``embeddings``, ``video``.
        period: Time window — ``"24h"`` (default), ``"7d"``, or ``"30d"``.

    Returns:
        Dict with ``endpoint``, ``period``, and ``history`` list of
        ``{checked_at, status, response_time_ms}`` dicts, ordered by
        ``checked_at`` descending. On error, returns error dict.
    """
    gate = await _check_autonomy("get_api_health_history")
    if gate is not None:
        return gate

    _PERIOD_MAP: dict[str, int] = {"24h": 1, "7d": 7, "30d": 30}
    days = _PERIOD_MAP.get(period, 1)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    client = get_service_client()

    try:
        query = (
            client.table("api_health_checks")
            .select("checked_at, status, response_time_ms")
            .eq("endpoint", endpoint)
            .gte("checked_at", since)
            .order("checked_at", desc=True)
        )
        result = await execute_async(query, op_name="get_api_health_history")
        rows: list[dict] = result.data or []

        return {
            "endpoint": endpoint,
            "period": period,
            "history": rows,
        }
    except Exception as exc:
        logger.error("get_api_health_history failed: %s", exc)
        return {"error": f"Failed to retrieve health history for {endpoint}: {exc}"}


# ---------------------------------------------------------------------------
# Tool 3: get_active_incidents
# ---------------------------------------------------------------------------


async def get_active_incidents() -> dict[str, Any]:
    """Return all currently unresolved incidents.

    Queries ``api_incidents`` where ``resolved_at IS NULL``, ordered by
    ``started_at`` descending.

    Returns:
        Dict with ``incidents`` list (all open incident rows) and ``count`` int.
        On error, returns error dict.
    """
    gate = await _check_autonomy("get_active_incidents")
    if gate is not None:
        return gate

    client = get_service_client()

    try:
        query = (
            client.table("api_incidents")
            .select("*")
            .is_("resolved_at", "null")
            .order("started_at", desc=True)
        )
        result = await execute_async(query, op_name="get_active_incidents")
        incidents: list[dict] = result.data or []

        return {
            "incidents": incidents,
            "count": len(incidents),
        }
    except Exception as exc:
        logger.error("get_active_incidents failed: %s", exc)
        return {"error": f"Failed to retrieve active incidents: {exc}"}


# ---------------------------------------------------------------------------
# Tool 4: get_incident_detail
# ---------------------------------------------------------------------------


async def get_incident_detail(incident_id: str) -> dict[str, Any]:
    """Return full details for a specific incident by ID.

    Args:
        incident_id: UUID of the incident to retrieve.

    Returns:
        Dict with ``incident`` data, or ``{"error": "..."}`` if not found or
        on query failure.
    """
    gate = await _check_autonomy("get_incident_detail")
    if gate is not None:
        return gate

    client = get_service_client()

    try:
        query = client.table("api_incidents").select("*").eq("id", incident_id).limit(1)
        result = await execute_async(query, op_name="get_incident_detail")
        rows: list[dict] = result.data or []

        if not rows:
            return {"error": f"Incident {incident_id} not found"}

        return {"incident": rows[0]}
    except Exception as exc:
        logger.error("get_incident_detail failed: %s", exc)
        return {"error": f"Failed to retrieve incident {incident_id}: {exc}"}


# ---------------------------------------------------------------------------
# Tool 5: run_diagnostic
# ---------------------------------------------------------------------------


async def run_diagnostic(endpoint: str) -> dict[str, Any]:
    """Perform a fresh health check on a single endpoint (diagnostic only, not persisted).

    Pings the named endpoint via httpx and returns the result immediately.
    Does NOT write to ``api_health_checks`` — use the Cloud Scheduler trigger for
    persisted checks.

    Args:
        endpoint: Endpoint name key — one of ``live``, ``connections``,
            ``cache``, ``embeddings``, ``video``.

    Returns:
        Dict with ``endpoint``, ``status``, ``response_time_ms``, ``status_code``,
        and ``error_message``. On unknown endpoint or error, returns error dict.
    """
    gate = await _check_autonomy("run_diagnostic")
    if gate is not None:
        return gate

    import os

    import httpx

    from app.services.health_checker import HEALTH_ENDPOINTS, _check_one

    path = HEALTH_ENDPOINTS.get(endpoint)
    if path is None:
        return {
            "error": (
                f"Unknown endpoint '{endpoint}'. "
                f"Valid options: {', '.join(HEALTH_ENDPOINTS)}"
            )
        }

    base_url = os.getenv("BACKEND_API_URL", "http://localhost:8000")

    try:
        async with httpx.AsyncClient(base_url=base_url) as client:
            result = await _check_one(client, endpoint, path)
        return result
    except Exception as exc:
        logger.error("run_diagnostic failed for %s: %s", endpoint, exc)
        return {"error": f"Diagnostic failed for {endpoint}: {exc}"}


# ---------------------------------------------------------------------------
# Tool 6: check_error_logs
# ---------------------------------------------------------------------------


async def check_error_logs(
    endpoint: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Return recent health check failures from api_health_checks.

    Queries rows where ``status != 'healthy'``, optionally filtered by endpoint,
    ordered by ``checked_at`` descending.

    Args:
        endpoint: Optional endpoint name to filter. If None, returns failures
            across all endpoints.
        limit: Maximum number of failure records to return (default 20).

    Returns:
        Dict with ``failures`` list of health check rows and ``count`` int.
        On error, returns error dict.
    """
    gate = await _check_autonomy("check_error_logs")
    if gate is not None:
        return gate

    client = get_service_client()

    try:
        query = (
            client.table("api_health_checks")
            .select("*")
            .neq("status", "healthy")
            .order("checked_at", desc=True)
            .limit(limit)
        )
        if endpoint is not None:
            query = (
                client.table("api_health_checks")
                .select("*")
                .eq("endpoint", endpoint)
                .neq("status", "healthy")
                .order("checked_at", desc=True)
                .limit(limit)
            )

        result = await execute_async(query, op_name="check_error_logs")
        failures: list[dict] = result.data or []

        return {
            "failures": failures,
            "count": len(failures),
        }
    except Exception as exc:
        logger.error("check_error_logs failed: %s", exc)
        return {"error": f"Failed to retrieve error logs: {exc}"}


# ---------------------------------------------------------------------------
# Tool 7: check_rate_limits
# ---------------------------------------------------------------------------


async def check_rate_limits() -> dict[str, Any]:
    """Return a summary of API usage patterns over the last hour.

    Queries ``api_health_checks`` for the last 60 minutes and computes
    per-endpoint average response time and failure counts.

    Returns:
        Dict with ``period`` (``"1h"``), ``per_endpoint`` stats dict mapping
        endpoint name to ``{avg_response_time_ms, total_checks, failure_count,
        failure_rate}``, and ``summary`` string. On error, returns error dict.
    """
    gate = await _check_autonomy("check_rate_limits")
    if gate is not None:
        return gate

    client = get_service_client()
    since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    try:
        query = (
            client.table("api_health_checks")
            .select("endpoint, status, response_time_ms, checked_at")
            .gte("checked_at", since)
            .order("checked_at", desc=True)
        )
        result = await execute_async(query, op_name="check_rate_limits")
        rows: list[dict] = result.data or []

        # Group by endpoint and compute stats
        per_endpoint: dict[str, dict] = {}
        for row in rows:
            name: str = row.get("endpoint", "unknown")
            if name not in per_endpoint:
                per_endpoint[name] = {
                    "response_times": [],
                    "total_checks": 0,
                    "failure_count": 0,
                }
            per_endpoint[name]["total_checks"] += 1
            rt = row.get("response_time_ms")
            if rt is not None:
                per_endpoint[name]["response_times"].append(rt)
            if row.get("status") not in ("healthy",):
                per_endpoint[name]["failure_count"] += 1

        # Summarise
        stats: dict[str, dict] = {}
        for name, data in per_endpoint.items():
            times = data["response_times"]
            avg_rt = round(sum(times) / len(times), 1) if times else None
            total = data["total_checks"]
            failures = data["failure_count"]
            stats[name] = {
                "avg_response_time_ms": avg_rt,
                "total_checks": total,
                "failure_count": failures,
                "failure_rate": round(failures / total, 3) if total > 0 else 0.0,
            }

        total_checks = sum(s["total_checks"] for s in stats.values())
        total_failures = sum(s["failure_count"] for s in stats.values())
        summary = (
            f"Last 1h: {total_checks} checks, {total_failures} failures "
            f"across {len(stats)} endpoints"
        )

        return {
            "period": "1h",
            "per_endpoint": stats,
            "summary": summary,
        }
    except Exception as exc:
        logger.error("check_rate_limits failed: %s", exc)
        return {"error": f"Failed to retrieve rate limit stats: {exc}"}
