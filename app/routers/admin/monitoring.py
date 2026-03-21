"""Admin monitoring status API endpoints.

Provides:
- GET /admin/monitoring/status — endpoint health list with sparkline history and open incidents
- POST /admin/monitoring/run-check — Cloud Scheduler entry point to trigger all health checks

The GET endpoint is gated by require_admin middleware.
The POST endpoint authenticates via WORKFLOW_SERVICE_SECRET (X-Service-Secret header),
NOT via require_admin, as it is called by Cloud Scheduler (service-to-service).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.app_utils.auth import verify_service_auth
from app.middleware.admin_auth import require_admin
from app.middleware.rate_limiter import limiter
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter()

# All monitored endpoint names — must match keys in HEALTH_ENDPOINTS in health_checker.py
_ENDPOINT_NAMES = ["live", "connections", "cache", "embeddings", "video"]

# Number of recent checks to include in the sparkline history per endpoint
_HISTORY_DEPTH = 20


@router.get("/monitoring/status")
@limiter.limit("120/minute")
async def get_monitoring_status(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Return current health status for all monitored endpoints with sparkline history.

    Queries ``api_health_checks`` for the last ``_HISTORY_DEPTH`` rows per endpoint
    and ``api_incidents`` for all open (unresolved) incidents.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin; confirms caller is an admin.

    Returns:
        JSON with ``endpoints`` list, ``open_incidents`` list, and ``latest_check_at``.
        Each endpoint object contains ``name``, ``current_status``, ``latest_check_at``,
        ``response_time_ms``, and ``history`` (list of last N check snapshots).
        ``latest_check_at`` is null when no health check data exists.

    Raises:
        HTTPException 500: If the Supabase query fails.
    """
    client = get_service_client()

    try:
        endpoints: list[dict] = []
        global_latest: str | None = None

        # Build per-endpoint status and history
        for name in _ENDPOINT_NAMES:
            query = (
                client.table("api_health_checks")
                .select("status, response_time_ms, checked_at")
                .eq("endpoint", name)
                .order("checked_at", desc=True)
                .limit(_HISTORY_DEPTH)
            )
            result = await execute_async(query, op_name=f"monitoring.status.{name}")
            rows: list[dict] = result.data or []

            if rows:
                latest_row = rows[0]
                current_status: str = latest_row.get("status", "unknown")
                latest_check_at: str | None = latest_row.get("checked_at")
                response_time_ms: int | None = latest_row.get("response_time_ms")

                # Track global latest across all endpoints
                if latest_check_at is not None:
                    if global_latest is None or latest_check_at > global_latest:
                        global_latest = latest_check_at

                history = [
                    {
                        "checked_at": r.get("checked_at"),
                        "response_time_ms": r.get("response_time_ms"),
                        "status": r.get("status"),
                    }
                    for r in rows
                ]
            else:
                current_status = "unknown"
                latest_check_at = None
                response_time_ms = None
                history = []

            endpoints.append(
                {
                    "name": name,
                    "current_status": current_status,
                    "latest_check_at": latest_check_at,
                    "response_time_ms": response_time_ms,
                    "history": history,
                }
            )

        # Query open (unresolved) incidents
        incident_query = (
            client.table("api_incidents")
            .select("*")
            .is_("resolved_at", "null")
            .order("started_at", desc=True)
        )
        incident_result = await execute_async(
            incident_query, op_name="monitoring.status.incidents"
        )
        open_incidents: list[dict] = incident_result.data or []

        return {
            "endpoints": endpoints,
            "open_incidents": open_incidents,
            "latest_check_at": global_latest,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to query monitoring status: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve monitoring status",
        ) from exc


@router.post("/monitoring/run-check")
@limiter.limit("2/minute")
async def trigger_health_check(
    request: Request,
    _auth: bool = Depends(verify_service_auth),  # noqa: B008
) -> dict:
    """Cloud Scheduler entry point — runs all health checks, writes to Supabase.

    Triggered every 60 seconds by Cloud Scheduler. Authenticates via
    X-Service-Secret header (WORKFLOW_SERVICE_SECRET), then delegates to
    run_health_checks() which concurrently pings all /health/* endpoints
    and persists results.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        _auth: Injected by verify_service_auth; confirms X-Service-Secret is valid.

    Returns:
        JSON with ``status`` ("ok") and ``checks_written`` count.

    Raises:
        HTTPException 401: If X-Service-Secret header is missing or invalid.
        HTTPException 500: If WORKFLOW_SERVICE_SECRET is not configured.
    """
    from app.services.health_checker import run_health_checks

    results = await run_health_checks()
    return {"status": "ok", "checks_written": len(results)}
