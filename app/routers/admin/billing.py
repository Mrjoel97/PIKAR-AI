# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Admin billing API endpoints — Phase 14, hardened in Plan 50-03 (BILL-04).

Provides:
- GET /admin/billing/summary — aggregated billing data with graceful Stripe degradation

The endpoint is gated by ``require_admin`` middleware. MRR and churn are now
computed DB-natively from the ``subscriptions`` table via
:class:`~app.services.billing_metrics_service.BillingMetricsService`, so the
admin dashboard shows meaningful numbers even when Stripe is unreachable.

The Stripe integration call is retained as a non-fatal cross-check: if live
Stripe MRR drifts more than 10% from the DB MRR, a warning is logged and the
DB value still wins.

NOTE: ``churn_rate`` is an APPROXIMATION — see ``BillingMetricsService`` for
the exact formula and limitations. Exact historical churn requires a
``subscription_history`` table; deferred to v8.0.
"""


import logging
from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.agents.admin.tools.integrations import _get_integration_config
from app.middleware.admin_auth import require_admin
from app.middleware.rate_limiter import limiter
from app.services.billing_metrics_service import BillingMetricsService
from app.services.integration_proxy import (
    IntegrationProxyService,
    _fetch_stripe_metrics,
)
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter()

#: When live Stripe MRR differs from DB MRR by more than this fraction
#: (default 10%), the cross-check logs a warning. Non-fatal — DB wins.
_STRIPE_MRR_VARIANCE_THRESHOLD: float = 0.10


@router.get("/billing/summary")
@limiter.limit("120/minute")
async def get_billing_summary(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
    days: int = 30,
    include_trend: bool = False,
) -> dict[str, Any]:
    """Return aggregated billing data for the admin dashboard.

    Queries the ``subscriptions`` table for plan distribution, billing-issue
    counts, and the legacy "will-not-renew" pending count. Computes MRR and
    real (approximated) churn from the same table via
    :class:`~app.services.billing_metrics_service.BillingMetricsService`.
    Optionally cross-checks the DB MRR against a live Stripe metrics call,
    logging a warning on >10% variance — the cross-check is non-fatal.

    Degrades gracefully:
        - Stripe not configured / unreachable → ``data_source="db_only"``
          but MRR is still populated from the DB.
        - Empty subscriptions table → ``data_source="no_data"`` and zero
          metrics across the board.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin; confirms caller is an admin.
        days: Trailing window in days for churn rate / trend (default 30).
        include_trend: When true, include a ``churn_trend`` array of length
            ``days`` (per-day cancellation counts) in the response. Default
            false to keep the standard payload small.

    Returns:
        JSON with ``mrr``, ``arr``, ``churn_rate`` (approximation),
        ``canceled_in_period``, ``active_subscriptions``, ``plan_distribution``,
        ``churn_pending`` (legacy will-not-renew count, retained alongside
        the new churn_rate), ``billing_issues``, ``data_source``
        (``"live"``/``"db_only"``/``"no_data"``), ``days``, and optionally
        ``churn_trend``.

    Raises:
        HTTPException 500: If the subscriptions table query fails.
    """
    client = get_service_client()

    # ------------------------------------------------------------------
    # 1. Plan distribution + legacy churn_pending + billing_issues
    # ------------------------------------------------------------------
    sub_query = client.table("subscriptions").select(
        "tier, is_active, will_renew, billing_issue_at"
    )
    sub_result = await execute_async(sub_query, op_name="billing.summary.subscriptions")
    sub_rows: list[dict] = sub_result.data or []

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
    plan_distribution = [
        {"tier": tier, "count": count} for tier, count in sorted(active_tiers.items())
    ]
    has_subscriptions = bool(sub_rows)

    # ------------------------------------------------------------------
    # 2. DB-native MRR + approximated churn via BillingMetricsService
    # ------------------------------------------------------------------
    metrics_svc = BillingMetricsService()
    mrr_data = await metrics_svc.compute_mrr()
    churn_data = await metrics_svc.compute_churn_rate(days=days)

    mrr: float = mrr_data["mrr"]
    arr: float = mrr_data["arr"]
    churn_rate: float = churn_data["churn_rate"]
    canceled_in_period: int = churn_data["canceled_in_period"]

    # ------------------------------------------------------------------
    # 3. Stripe cross-check (non-fatal)
    # ------------------------------------------------------------------
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
            stripe_configured = True
            live_mrr = stripe_data.get("mrr", 0) or 0
            # Variance check: warn if Stripe and DB disagree by >10%.
            # Non-fatal — DB MRR remains the source of truth.
            if live_mrr and abs(live_mrr - mrr) / max(live_mrr, 1) > (
                _STRIPE_MRR_VARIANCE_THRESHOLD
            ):
                logger.warning(
                    "Billing MRR variance detected: db_mrr=%s stripe_mrr=%s "
                    "(threshold=%s) — DB value used",
                    mrr,
                    live_mrr,
                    _STRIPE_MRR_VARIANCE_THRESHOLD,
                )
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

    # ------------------------------------------------------------------
    # 5. Build response
    # ------------------------------------------------------------------
    response: dict[str, Any] = {
        "mrr": mrr,
        "arr": arr,
        "churn_rate": churn_rate,
        "canceled_in_period": canceled_in_period,
        "active_subscriptions": total_active,
        "plan_distribution": plan_distribution,
        "churn_pending": churn_pending,
        "billing_issues": billing_issues,
        "data_source": data_source,
        "days": days,
    }
    if include_trend:
        response["churn_trend"] = await metrics_svc.compute_churn_trend(days=days)
    return response
