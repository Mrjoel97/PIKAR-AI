# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Admin billing API endpoints — Phase 14.

Provides:
- GET /admin/billing/summary — aggregated billing data with graceful Stripe degradation

The endpoint is gated by require_admin middleware. When Stripe is not configured,
the endpoint degrades gracefully to DB-only mode (plan distribution from the
subscriptions table, MRR/ARR set to 0).
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.agents.admin.tools.integrations import _get_integration_config
from app.middleware.admin_auth import require_admin
from app.middleware.rate_limiter import limiter
from app.services.integration_proxy import (
    IntegrationProxyService,
    _fetch_stripe_metrics,
)
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/billing/summary")
@limiter.limit("120/minute")
async def get_billing_summary(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
    days: int = 30,
) -> dict[str, Any]:
    """Return aggregated billing data for the admin dashboard.

    Queries the ``subscriptions`` table for plan distribution, churn metrics,
    and billing issue counts. Optionally fetches live MRR/ARR from Stripe via
    :class:`~app.services.integration_proxy.IntegrationProxyService` when the
    Stripe integration is configured.

    Degrades gracefully: when Stripe is not configured or unavailable, returns
    ``mrr=0``, ``arr=0``, and ``data_source="db_only"`` while still providing
    full plan distribution from the local subscriptions table.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin; confirms caller is an admin.
        days: Reserved for future time-windowed queries (default 30).

    Returns:
        JSON with ``mrr``, ``arr``, ``churn_rate``, ``active_subscriptions``,
        ``plan_distribution``, ``churn_pending``, ``billing_issues``,
        ``data_source`` (``"live"``/``"db_only"``/``"no_data"``), and ``days``.

    Raises:
        HTTPException 500: If the subscriptions table query fails.
    """
    client = get_service_client()

    # ------------------------------------------------------------------
    # 1. Query subscriptions table for plan distribution
    # ------------------------------------------------------------------
    sub_query = (
        client.table("subscriptions")
        .select("tier, is_active, will_renew, billing_issue_at")
    )
    sub_result = await execute_async(sub_query, op_name="billing.summary.subscriptions")
    sub_rows: list[dict] = sub_result.data or []

    # ------------------------------------------------------------------
    # 2. Compute plan distribution and churn metrics
    # ------------------------------------------------------------------
    active_tiers: Counter = Counter()
    churn_pending = 0
    billing_issues = 0

    for row in sub_rows:
        if row.get("is_active"):
            active_tiers[row.get("tier", "unknown")] += 1
            if not row.get("will_renew"):
                churn_pending += 1
            if row.get("billing_issue_at") is not None:
                billing_issues += 1

    total_active = sum(active_tiers.values())
    churn_rate = churn_pending / max(total_active, 1)
    plan_distribution = [
        {"tier": tier, "count": count}
        for tier, count in sorted(active_tiers.items())
    ]

    has_subscriptions = bool(sub_rows)

    # ------------------------------------------------------------------
    # 3. Try to get live Stripe metrics
    # ------------------------------------------------------------------
    mrr: float = 0
    arr: float = 0
    stripe_configured = False

    cfg = await _get_integration_config("stripe")
    if not isinstance(cfg, dict):
        # cfg is a tuple (api_key, config, base_url) — Stripe is configured
        api_key, config, _base_url = cfg
        try:
            stripe_data = await IntegrationProxyService.call(
                provider="stripe",
                operation="get_metrics",
                api_key=api_key,
                config=config,
                params={},
                fetch_fn=_fetch_stripe_metrics,
            )
            mrr = stripe_data.get("mrr", 0)
            arr = stripe_data.get("arr", 0)
            stripe_configured = True
        except Exception as exc:
            logger.warning("Stripe metrics fetch failed in billing summary: %s", exc)

    # ------------------------------------------------------------------
    # 4. Determine data_source
    # ------------------------------------------------------------------
    if not has_subscriptions:
        data_source = "no_data"
    elif stripe_configured:
        data_source = "live"
    else:
        data_source = "db_only"

    return {
        "mrr": mrr,
        "arr": arr,
        "churn_rate": round(churn_rate, 4),
        "active_subscriptions": total_active,
        "plan_distribution": plan_distribution,
        "churn_pending": churn_pending,
        "billing_issues": billing_issues,
        "data_source": data_source,
        "days": days,
    }
