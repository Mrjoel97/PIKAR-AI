# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Health checker service for concurrent backend endpoint monitoring.

Polls all five /health/* endpoints concurrently via httpx, writes results
directly to Supabase (bypassing the monitored FastAPI service), detects
anomalies (down, latency_spike, error_spike), manages incident lifecycle,
and auto-prunes old records.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.services.admin_audit import log_admin_action
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Endpoint registry
# ---------------------------------------------------------------------------

HEALTH_ENDPOINTS: dict[str, str] = {
    "live": "/health/live",
    "connections": "/health/connections",
    "cache": "/health/cache",
    "embeddings": "/health/embeddings",
    "video": "/health/video",
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _check_one(
    client: httpx.AsyncClient,
    name: str,
    path: str,
) -> dict[str, Any]:
    """Ping a single health endpoint and return a result dict.

    Args:
        client: Shared httpx.AsyncClient with base_url already set.
        name: Short name used as the ``endpoint`` key (e.g. ``"live"``).
        path: URL path to GET (e.g. ``"/health/live"``).

    Returns:
        Dict with keys ``endpoint``, ``status``, ``status_code``,
        ``response_time_ms``, ``error_message``.
    """
    start = time.monotonic()
    try:
        resp = await client.get(
            path,
            timeout=httpx.Timeout(10.0, connect=5.0),
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        if resp.status_code == 200:
            # Parse canonical versioned response shape (OBS-05 Phase 51)
            # Map: "ok" -> "healthy", "degraded" -> "degraded", "down" -> "unhealthy"
            # Fallback to HTTP-status-only check if JSON parsing fails (defensive).
            try:
                body = resp.json()
                canonical_status = body.get("status", "ok")
                _CANONICAL_MAP = {"ok": "healthy", "degraded": "degraded", "down": "unhealthy"}
                status = _CANONICAL_MAP.get(canonical_status, "healthy")
            except Exception:
                status = "healthy"
        else:
            status = "unhealthy"
        return {
            "endpoint": name,
            "status": status,
            "status_code": resp.status_code,
            "response_time_ms": elapsed_ms,
            "error_message": None,
        }
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "endpoint": name,
            "status": "unhealthy",
            "status_code": None,
            "response_time_ms": elapsed_ms,
            "error_message": str(exc)[:500],
        }


async def _get_rolling_stats(
    supabase_client: Any,
    endpoint: str,
) -> dict[str, Any] | None:
    """Query rolling statistics for the last 10 checks of an endpoint.

    Returns None when fewer than 3 records exist (insufficient baseline for
    anomaly detection).

    Args:
        supabase_client: Supabase service-role client.
        endpoint: Endpoint name key (e.g. ``"live"``).

    Returns:
        Dict with ``avg_response_time_ms``, ``error_count``, ``total_count``,
        or None if not enough data.
    """
    query = (
        supabase_client.table("api_health_checks")
        .select("status, response_time_ms")
        .eq("endpoint", endpoint)
        .order("checked_at", desc=True)
        .limit(10)
    )
    result = await execute_async(query, op_name="health_checker.rolling_stats")
    rows: list[dict] = result.data or []

    if len(rows) < 3:
        return None

    times = [
        r["response_time_ms"]
        for r in rows
        if r.get("response_time_ms") is not None
    ]
    avg_rt = sum(times) / len(times) if times else 0.0
    error_count = sum(
        1 for r in rows if r.get("status") in ("unhealthy", "degraded")
    )
    return {
        "avg_response_time_ms": avg_rt,
        "error_count": error_count,
        "total_count": len(rows),
    }


def _detect_anomaly(
    check_result: dict[str, Any],
    rolling_stats: dict[str, Any] | None,
) -> str | None:
    """Determine the anomaly type (if any) for a health check result.

    Mutates ``check_result["status"]`` to ``"degraded"`` when a latency
    spike is detected (endpoint is up but slow).

    Args:
        check_result: Result dict from :func:`_check_one`.
        rolling_stats: Rolling stats from :func:`_get_rolling_stats`, or None.

    Returns:
        One of ``"down"``, ``"latency_spike"``, ``"error_spike"``, or None.
    """
    status_code = check_result.get("status_code")

    # Down: non-200 or no response at all
    if status_code is None or status_code != 200:
        return "down"

    # Not enough baseline data for anomaly detection
    if rolling_stats is None:
        return None

    avg_rt = rolling_stats["avg_response_time_ms"]
    response_time = check_result.get("response_time_ms") or 0

    # Latency spike: response time > 2x rolling average
    if avg_rt > 0 and response_time > 2 * avg_rt:
        check_result["status"] = "degraded"
        return "latency_spike"

    # Error spike: error rate > 5% across recent checks
    total = rolling_stats["total_count"]
    if total > 0 and rolling_stats["error_count"] / total > 0.05:
        return "error_spike"

    return None


async def _update_incidents(
    supabase_client: Any,
    endpoint: str,
    incident_type: str | None,
    checked_at: str,
) -> None:
    """Create or resolve an incident based on current anomaly detection.

    Rules:
    - anomaly detected, no open incident → create new incident
    - healthy, open incident exists → resolve it (set resolved_at)
    - anomaly detected, open incident with different type → resolve old, create new

    Uses ``.is_("resolved_at", "null")`` for PostgREST IS NULL compatibility.

    Args:
        supabase_client: Supabase service-role client.
        endpoint: Endpoint name key.
        incident_type: Detected anomaly type, or None if healthy.
        checked_at: ISO timestamp for incident timestamps.
    """
    # Query for any open incident on this endpoint
    open_query = (
        supabase_client.table("api_incidents")
        .select("id, incident_type")
        .eq("endpoint", endpoint)
        .is_("resolved_at", "null")
        .limit(1)
    )
    open_result = await execute_async(
        open_query, op_name="health_checker.query_open_incident"
    )
    open_incidents: list[dict] = open_result.data or []
    open_incident = open_incidents[0] if open_incidents else None

    if incident_type is not None:
        if open_incident is None:
            # No open incident — create a new one
            insert_query = supabase_client.table("api_incidents").insert(
                {
                    "endpoint": endpoint,
                    "incident_type": incident_type,
                    "started_at": checked_at,
                    "details": {"detection_method": "anomaly_detection"},
                }
            )
            await execute_async(
                insert_query, op_name="health_checker.create_incident"
            )
        elif open_incident["incident_type"] != incident_type:
            # Type escalation — resolve old incident, open new one
            resolve_query = (
                supabase_client.table("api_incidents")
                .update({"resolved_at": checked_at})
                .eq("id", open_incident["id"])
            )
            await execute_async(
                resolve_query, op_name="health_checker.resolve_old_incident"
            )
            insert_query = supabase_client.table("api_incidents").insert(
                {
                    "endpoint": endpoint,
                    "incident_type": incident_type,
                    "started_at": checked_at,
                    "details": {"detection_method": "anomaly_detection"},
                }
            )
            await execute_async(
                insert_query, op_name="health_checker.create_escalated_incident"
            )
        # else: same type still open — no change needed
    else:
        # Healthy — resolve open incident if one exists
        if open_incident is not None:
            resolve_query = (
                supabase_client.table("api_incidents")
                .update({"resolved_at": checked_at})
                .eq("id", open_incident["id"])
            )
            await execute_async(
                resolve_query, op_name="health_checker.resolve_incident"
            )


async def _prune_old_records(supabase_client: Any) -> None:
    """Remove stale health check records from api_health_checks.

    Two-pass pruning strategy:
    1. Delete all records older than 30 days.
    2. For each endpoint, if more than 1000 records remain, delete the oldest
       beyond the cap.

    Errors are caught and logged — prune failures must never abort the
    health check loop.

    Args:
        supabase_client: Supabase service-role client.
    """
    try:
        # Pass 1: age-based delete (30 days)
        cutoff = "now() - interval '30 days'"
        age_delete = (
            supabase_client.table("api_health_checks")
            .delete()
            .lte("checked_at", cutoff)
        )
        await execute_async(age_delete, op_name="health_checker.prune_old_age")

        # Pass 2: per-endpoint cap at 1000 records
        for name in HEALTH_ENDPOINTS:
            count_query = (
                supabase_client.table("api_health_checks")
                .select("id")
                .eq("endpoint", name)
                .order("checked_at", desc=True)
            )
            count_result = await execute_async(
                count_query, op_name=f"health_checker.count_{name}"
            )
            rows: list[dict] = count_result.data or []
            if len(rows) > 1000:
                excess_ids = [r["id"] for r in rows[1000:]]
                if excess_ids:
                    cap_delete = (
                        supabase_client.table("api_health_checks")
                        .delete()
                        .eq("endpoint", name)
                        .in_("id", excess_ids)
                    )
                    await execute_async(
                        cap_delete,
                        op_name=f"health_checker.cap_{name}",
                    )
    except Exception as exc:
        logger.warning(
            "health_checker._prune_old_records failed (non-fatal): %s", exc
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_health_checks() -> list[dict[str, Any]]:
    """Concurrently ping all health endpoints, write results, and detect anomalies.

    Workflow:
    1. Fire all five ``/health/*`` checks concurrently via ``asyncio.gather``.
    2. Batch-insert results into ``api_health_checks`` (direct Supabase write).
    3. For each result: fetch rolling stats, detect anomaly, update incidents.
    4. Prune old records (age cap + per-endpoint count cap).
    5. Log the run via ``log_admin_action``.

    Returns:
        List of result dicts, one per endpoint, each containing
        ``endpoint``, ``status``, ``status_code``, ``response_time_ms``,
        ``error_message``.
    """
    base_url = os.getenv("BACKEND_API_URL", "http://localhost:8000")
    checked_at = datetime.now(timezone.utc).isoformat()

    async with httpx.AsyncClient(base_url=base_url) as client:
        tasks = [
            _check_one(client, name, path)
            for name, path in HEALTH_ENDPOINTS.items()
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out any unexpected Exception objects (should not occur given _check_one
    # catches all exceptions internally, but guard defensively)
    results: list[dict[str, Any]] = [
        r for r in raw_results if isinstance(r, dict)
    ]

    if not results:
        logger.warning("health_checker: all checks returned exceptions — skipping write")
        return []

    # Write all results to api_health_checks
    supabase = get_service_client()
    insert_query = supabase.table("api_health_checks").insert(
        [
            {
                "endpoint": r["endpoint"],
                "status": r["status"],
                "status_code": r["status_code"],
                "response_time_ms": r["response_time_ms"],
                "error_message": r["error_message"],
                "checked_at": checked_at,
            }
            for r in results
        ]
    )
    await execute_async(insert_query, op_name="health_checker.batch_insert")

    # Per-result: anomaly detection + incident lifecycle
    for result in results:
        endpoint = result["endpoint"]
        rolling_stats = await _get_rolling_stats(supabase, endpoint)
        incident_type = _detect_anomaly(result, rolling_stats)
        await _update_incidents(supabase, endpoint, incident_type, checked_at)

    # Auto-prune stale records
    await _prune_old_records(supabase)

    # Audit trail
    await log_admin_action(
        admin_user_id=None,
        action="scheduled_health_check",
        target_type="system",
        target_id=None,
        details={"checked": len(results)},
        source="monitoring_loop",
    )

    return results
