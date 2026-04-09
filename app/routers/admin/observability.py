# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Admin observability API endpoints — Phase 51 (OBS-02, OBS-03, OBS-04).

Provides:
- GET /observability/summary — hero metrics (error rate 24h, MTD AI spend,
  p95 latency, health status) — requires require_admin
- GET /observability/latency — agent latency percentiles for configurable
  time window — requires require_admin
- GET /observability/errors — error rate trends by agent/endpoint/time
  — requires require_admin
- GET /observability/cost — AI token cost breakdown by agent, user, day
  — requires require_admin
- POST /observability/run-rollup — Cloud Scheduler entry point for hourly
  latency rollup into agent_latency_rollups — requires verify_service_auth

All GET endpoints are gated by require_admin (admin-only).
The POST run-rollup endpoint is gated by verify_service_auth (service-to-service).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.app_utils.auth import verify_service_auth
from app.middleware.admin_auth import require_admin
from app.middleware.rate_limiter import limiter
from app.services.observability_metrics_service import ObservabilityMetricsService

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Window parsing helper
# ---------------------------------------------------------------------------


def _parse_window(window: str) -> tuple[datetime, datetime]:
    """Parse a window string (1h, 24h, 7d, 30d) to (start, end) datetimes.

    Args:
        window: One of "1h", "24h", "7d", "30d".

    Returns:
        ``(start, end)`` as UTC-aware datetimes. Defaults to 24h for unknown values.
    """
    now = datetime.now(tz=timezone.utc)
    if window == "1h":
        return (now - timedelta(hours=1), now)
    if window == "24h":
        return (now - timedelta(hours=24), now)
    if window == "7d":
        return (now - timedelta(days=7), now)
    if window == "30d":
        return (now - timedelta(days=30), now)
    # Default: 24h
    return (now - timedelta(hours=24), now)


# ---------------------------------------------------------------------------
# GET /observability/summary
# ---------------------------------------------------------------------------


@router.get("/observability/summary")
@limiter.limit("120/minute")
async def get_observability_summary(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict[str, Any]:
    """Return hero observability metrics for the admin dashboard.

    Aggregates the last 24 hours of agent telemetry into summary form:
    error rate, MTD AI spend, p95 latency, and any active threshold breach.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin; confirms caller is an admin.

    Returns:
        JSON with ``error_rate_24h``, ``mtd_ai_spend``,
        ``projected_monthly_spend``, ``p95_latency_24h``,
        ``threshold_breach`` (null or breach details dict).

    Raises:
        HTTPException 500: If any sub-query fails.
    """
    svc = ObservabilityMetricsService()
    now = datetime.now(tz=timezone.utc)
    start_24h = now - timedelta(hours=24)

    error_data = await svc.compute_error_rate(None, start_24h, now)
    spend_data = await svc.project_monthly_ai_spend()
    latency_data = await svc.compute_latency_percentiles(None, start_24h, now)
    threshold_breach = await svc.check_error_threshold()

    return {
        "error_rate_24h": error_data["error_rate"],
        "mtd_ai_spend": spend_data["mtd_actual"],
        "projected_monthly_spend": spend_data["projected_full_month"],
        "p95_latency_24h": latency_data["p95"],
        "threshold_breach": threshold_breach,
    }


# ---------------------------------------------------------------------------
# GET /observability/latency
# ---------------------------------------------------------------------------


@router.get("/observability/latency")
@limiter.limit("120/minute")
async def get_observability_latency(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
    agent_name: str | None = None,
    window: str = "24h",
) -> dict[str, Any]:
    """Return agent latency percentiles for the given time window.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin; confirms caller is an admin.
        agent_name: Optional agent filter (e.g. "financial_agent"). None for all.
        window: Time window — one of "1h", "24h", "7d", "30d" (default "24h").

    Returns:
        JSON with ``p50``, ``p95``, ``p99``, ``sample_count``, ``error_count``,
        ``agent_name``, and ``window``.
    """
    svc = ObservabilityMetricsService()
    start, end = _parse_window(window)
    data = await svc.compute_latency_percentiles(agent_name, start, end)
    return {**data, "agent_name": agent_name, "window": window}


# ---------------------------------------------------------------------------
# GET /observability/errors
# ---------------------------------------------------------------------------


@router.get("/observability/errors")
@limiter.limit("120/minute")
async def get_observability_errors(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
    agent_name: str | None = None,
    window: str = "24h",
) -> dict[str, Any]:
    """Return error rate trends for the given time window.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin; confirms caller is an admin.
        agent_name: Optional agent filter. None for all agents.
        window: Time window — one of "1h", "24h", "7d", "30d" (default "24h").

    Returns:
        JSON with ``error_rate``, ``error_count``, ``total_count``,
        ``agent_name``, and ``window``.
    """
    svc = ObservabilityMetricsService()
    start, end = _parse_window(window)
    data = await svc.compute_error_rate(agent_name, start, end)
    return {**data, "agent_name": agent_name, "window": window}


# ---------------------------------------------------------------------------
# GET /observability/cost
# ---------------------------------------------------------------------------


@router.get("/observability/cost")
@limiter.limit("120/minute")
async def get_observability_cost(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
    window: str = "30d",
    group_by: str = "agent",
) -> dict[str, Any]:
    """Return AI token cost breakdown for the given time window.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin; confirms caller is an admin.
        window: Time window — one of "1h", "24h", "7d", "30d" (default "30d").
        group_by: Dimension for cost breakdown — "agent", "user", or "day"
            (default "agent").

    Returns:
        JSON with ``data`` (cost breakdown list or dict), ``group_by``,
        and ``window``.
    """
    svc = ObservabilityMetricsService()
    start, end = _parse_window(window)

    if group_by == "user":
        data = await svc.compute_ai_cost_by_user(start, end)
    elif group_by == "day":
        data = await svc.compute_ai_cost_by_day(start, end)
    else:
        # Default: group by agent
        data = await svc.compute_ai_cost_by_agent(start, end)

    return {"data": data, "group_by": group_by, "window": window}


# ---------------------------------------------------------------------------
# POST /observability/run-rollup
# ---------------------------------------------------------------------------


@router.post("/observability/run-rollup")
@limiter.limit("2/minute")
async def trigger_observability_rollup(
    request: Request,
    _auth: bool = Depends(verify_service_auth),
) -> dict[str, Any]:
    """Cloud Scheduler entry point — runs the hourly latency rollup job.

    Triggered every hour by Cloud Scheduler. Authenticates via
    X-Service-Secret header (WORKFLOW_SERVICE_SECRET), then delegates to
    ObservabilityMetricsService.run_hourly_rollup() which aggregates the
    previous hour's agent_telemetry rows into agent_latency_rollups.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        _auth: Injected by verify_service_auth; confirms X-Service-Secret is valid.

    Returns:
        JSON with ``status`` ("ok") and ``buckets_written`` count.

    Raises:
        HTTPException 401: If X-Service-Secret header is missing or invalid.
        HTTPException 500: If WORKFLOW_SERVICE_SECRET is not configured.
    """
    svc = ObservabilityMetricsService()
    result = await svc.run_hourly_rollup()
    return {"status": "ok", "buckets_written": result["buckets_written"]}
