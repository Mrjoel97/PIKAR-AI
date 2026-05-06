# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Admin overview API — aggregate KPI metrics for the /admin landing page.

Provides:
- GET /admin/overview — six KPI cards (system status, active users,
  pending approvals, agent health, workflow queue, recent alerts)

Six independent queries fan out concurrently via ``asyncio.gather`` with
``return_exceptions=True``, so one card failing (e.g. Stripe outage, missing
table on a fresh deploy) does not blank the entire dashboard. Each card has
``status`` set to ``neutral`` when its source query fails.

Gated by ``require_admin``.
"""


import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request

from app.middleware.admin_auth import require_admin
from app.middleware.rate_limiter import limiter
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter()

CardStatus = Literal["ok", "warn", "error", "neutral"]


def _card(title: str, value: str, status: CardStatus) -> dict[str, Any]:
    """Build a single overview card payload matching the frontend's `StatusCardProps`."""
    return {"title": title, "value": value, "status": status}


# ---------------------------------------------------------------------------
# Per-card data sources — one coroutine each.
# Each returns a finished card dict; exceptions bubble to gather() and are
# caught at the aggregator boundary so a partial outage degrades gracefully.
# ---------------------------------------------------------------------------


async def _system_status_card() -> dict[str, Any]:
    """Roll up api_health_checks into a single 'Operational/Degraded/Down' card.

    Reads the latest row per monitored endpoint from api_health_checks.
    Any 'unhealthy' → "Down". Any 'degraded' → "Degraded". All 'healthy' →
    "Operational". Empty table (cold deploy) → "No data" / neutral.
    """
    client = get_service_client()
    endpoints = ["live", "connections", "cache", "embeddings", "video"]

    statuses: list[str] = []
    for name in endpoints:
        row = await execute_async(
            client.table("api_health_checks")
            .select("status")
            .eq("endpoint", name)
            .order("checked_at", desc=True)
            .limit(1),
            op_name=f"overview.system_status.{name}",
        )
        if row.data:
            statuses.append(row.data[0].get("status", "unknown"))

    if not statuses:
        return _card("System Status", "No data", "neutral")
    if any(s == "unhealthy" for s in statuses):
        return _card("System Status", "Down", "error")
    if any(s == "degraded" for s in statuses):
        return _card("System Status", "Degraded", "warn")
    return _card("System Status", "Operational", "ok")


async def _active_users_card() -> dict[str, Any]:
    """24-hour distinct-session active-user count.

    Uses sessions.updated_at as the activity signal; the daily aggregator
    upserts a stable DAU into admin_analytics_daily, but that row only
    exists after tomorrow's scheduler run, so we count live here for a
    real-time card.
    """
    client = get_service_client()
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(hours=24)).isoformat()

    result = await execute_async(
        client.table("sessions")
        .select("*", count="exact")
        .gte("updated_at", cutoff)
        .limit(0),
        op_name="overview.active_users",
    )
    count = getattr(result, "count", None)
    if count is None:
        count = len(result.data or [])
    return _card("Active Users", str(count), "ok" if count > 0 else "neutral")


async def _pending_approvals_card() -> dict[str, Any]:
    """Count of approval_requests rows with status='pending'."""
    client = get_service_client()
    result = await execute_async(
        client.table("approval_requests")
        .select("*", count="exact")
        .eq("status", "pending")
        .limit(0),
        op_name="overview.pending_approvals",
    )
    count = getattr(result, "count", None)
    if count is None:
        count = len(result.data or [])
    # warn when there's a backlog so admins see it on the landing page
    status: CardStatus = "warn" if count > 0 else "ok"
    return _card("Pending Approvals", str(count), status)


async def _agent_health_card() -> dict[str, Any]:
    """24-hour error-rate-derived agent health.

    >5% error rate → Degraded, 2-5% → Warning, <2% → Healthy. No samples
    in window → "No data" / neutral so a quiet system doesn't show red.
    """
    from app.services.observability_metrics_service import ObservabilityMetricsService

    svc = ObservabilityMetricsService()
    now = datetime.now(tz=timezone.utc)
    data = await svc.compute_error_rate(None, now - timedelta(hours=24), now)

    total = int(data.get("total_count") or 0)
    if total == 0:
        return _card("Agent Health", "No data", "neutral")

    rate = float(data.get("error_rate") or 0.0)
    if rate >= 0.05:
        return _card("Agent Health", "Degraded", "error")
    if rate >= 0.02:
        return _card("Agent Health", "Warning", "warn")
    return _card("Agent Health", "Healthy", "ok")


async def _workflow_queue_card() -> dict[str, Any]:
    """Count of ai_jobs rows with status='pending'."""
    client = get_service_client()
    result = await execute_async(
        client.table("ai_jobs")
        .select("*", count="exact")
        .eq("status", "pending")
        .limit(0),
        op_name="overview.workflow_queue",
    )
    count = getattr(result, "count", None)
    if count is None:
        count = len(result.data or [])
    return _card("Workflow Queue", str(count), "ok" if count >= 0 else "neutral")


async def _recent_alerts_card() -> dict[str, Any]:
    """Count of api_incidents rows where resolved_at IS NULL."""
    client = get_service_client()
    result = await execute_async(
        client.table("api_incidents")
        .select("*", count="exact")
        .is_("resolved_at", "null")
        .limit(0),
        op_name="overview.recent_alerts",
    )
    count = getattr(result, "count", None)
    if count is None:
        count = len(result.data or [])
    status: CardStatus = "error" if count > 0 else "ok"
    return _card("Recent Alerts", str(count), status)


# Card key → (display title, coroutine factory). Order is the render order
# the frontend uses so the page can iterate the response without re-sorting.
_CARDS: list[tuple[str, str, Any]] = [
    ("system_status", "System Status", _system_status_card),
    ("active_users", "Active Users", _active_users_card),
    ("pending_approvals", "Pending Approvals", _pending_approvals_card),
    ("agent_health", "Agent Health", _agent_health_card),
    ("workflow_queue", "Workflow Queue", _workflow_queue_card),
    ("recent_alerts", "Recent Alerts", _recent_alerts_card),
]


@router.get("/overview")
@limiter.limit("120/minute")
async def get_admin_overview(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict[str, Any]:
    """Return six aggregated KPI cards for the /admin landing page.

    Cards fan out concurrently with ``asyncio.gather(return_exceptions=True)``
    so a single source failure (table missing, downstream service down)
    degrades only the affected card to ``status='neutral'`` and ``value='—'``
    instead of blanking the whole dashboard.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin; confirms caller is an admin.

    Returns:
        ``{"cards": [{title, value, status}, ...]}`` in stable render order.
    """
    results = await asyncio.gather(
        *(factory() for _, _, factory in _CARDS),
        return_exceptions=True,
    )

    cards: list[dict[str, Any]] = []
    for (key, title, _factory), outcome in zip(_CARDS, results, strict=True):
        if isinstance(outcome, BaseException):
            logger.warning(
                "Overview card '%s' failed: %s", key, outcome, exc_info=outcome
            )
            cards.append(_card(title, "—", "neutral"))
        else:
            cards.append(outcome)

    return {"cards": cards}
