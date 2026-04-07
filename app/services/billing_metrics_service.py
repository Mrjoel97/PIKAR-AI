# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""BillingMetricsService — DB-native revenue and churn computation.

Plan 50-03 / BILL-04. Replaces the placeholder churn metric in
``/admin/billing/summary`` (which was actually ``churn_pending / active`` —
a "will-not-renew ratio", not real churn) with a time-windowed approximation:

    churn_rate ≈ canceled_in_period / (current_active + canceled_in_period)

Computes MRR directly from the ``subscriptions`` table (the authoritative
state written by the Stripe webhook handler hardened in Plan 50-01) so the
admin dashboard shows meaningful numbers even when Stripe is unreachable.

NOTE: ``churn_rate`` here is explicitly an APPROXIMATION. Exact historical
churn requires a ``subscription_history`` table that we have not yet built —
deferred to v8.0. The approximation treats ``current_active + canceled`` as a
proxy for "active at start of window", which is correct as long as no NEW
subscriptions started inside the window. For 30-day windows on a low-volume
beta this drift is negligible; the field is documented as an approximation
in the API contract and the admin UI will not claim "true churn".

Inherits from :class:`~app.services.base_service.AdminService` because it
runs only inside admin-guarded routes and aggregates across every user, so
it requires the service-role client to bypass RLS.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar

from app.services.base_service import AdminService
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


class BillingMetricsService(AdminService):
    """DB-native MRR and approximated churn for the admin billing dashboard.

    All public methods are async and depend only on the ``subscriptions``
    table — there is no Stripe API dependency. The router that consumes
    this service can still cross-check the DB MRR against a live Stripe
    metrics fetch and log a warning on >10% variance, but the DB result is
    the source of truth.
    """

    #: Authoritative monthly tier prices in USD. Mirrors the values in
    #: ``frontend/src/app/dashboard/billing/page.tsx::PLAN_CONFIG``. The
    #: ``enterprise`` tier is custom-priced and intentionally excluded
    #: from MRR (price=0 means "do not contribute").
    TIER_PRICES: ClassVar[dict[str, float]] = {
        "free": 0.0,
        "solopreneur": 99.0,
        "startup": 297.0,
        "sme": 597.0,
        "enterprise": 0.0,  # Custom pricing — excluded from MRR
    }

    # ------------------------------------------------------------------
    # MRR
    # ------------------------------------------------------------------

    async def compute_mrr(self) -> dict[str, float]:
        """Sum monthly tier prices across all active subscriptions.

        Returns:
            ``{"mrr": float, "arr": float}`` rounded to 2 decimals.
            ``arr`` is simply ``mrr * 12``. Both fields are 0.0 when the
            ``subscriptions`` table is empty or contains only inactive rows
            (free/enterprise tiers contribute zero by design).
        """
        result = await execute_async(
            self.client.table("subscriptions").select("tier").eq("is_active", True),
            op_name="billing_metrics.compute_mrr",
        )
        rows = result.data or []
        mrr = sum(self.TIER_PRICES.get(row.get("tier", "free"), 0.0) for row in rows)
        return {"mrr": round(mrr, 2), "arr": round(mrr * 12, 2)}

    # ------------------------------------------------------------------
    # Churn rate (approximation)
    # ------------------------------------------------------------------

    async def compute_churn_rate(self, days: int = 30) -> dict[str, Any]:
        """Approximate churn rate over the trailing ``days`` window.

        Approximation formula::

            churn_rate ≈ canceled_in_period / (current_active + canceled_in_period)

        ``canceled_in_period`` counts rows with ``is_active=false`` whose
        ``updated_at`` falls inside the window — a proxy for "subscriptions
        that ended in the last N days" backed by the ``subscriptions``
        table updated_at trigger.

        ``active_at_start`` is approximated as ``current_active + canceled_in_period``
        — this drifts upward when new subscriptions started inside the
        window (those are not subtracted) but for low-volume beta traffic
        on a 30-day window the drift is negligible. Exact historical churn
        requires a ``subscription_history`` table; deferred to v8.0.

        Args:
            days: Trailing window in days (default 30).

        Returns:
            ``{"churn_rate": float, "canceled_in_period": int,
            "active_at_start": int, "window_days": int}``. ``churn_rate`` is
            rounded to 4 decimals and safely returns 0.0 when
            ``active_at_start`` is 0.
        """
        window_start = datetime.now(tz=timezone.utc) - timedelta(days=days)
        window_iso = window_start.isoformat()

        canceled_result = await execute_async(
            self.client.table("subscriptions")
            .select("user_id", count="exact")
            .eq("is_active", False)
            .gte("updated_at", window_iso),
            op_name="billing_metrics.compute_churn_rate.canceled",
        )
        canceled_in_period = canceled_result.count or 0

        active_result = await execute_async(
            self.client.table("subscriptions")
            .select("user_id", count="exact")
            .eq("is_active", True),
            op_name="billing_metrics.compute_churn_rate.active",
        )
        current_active = active_result.count or 0

        # Approximation: active_at_start ≈ current_active + canceled_in_period
        active_at_start = current_active + canceled_in_period

        churn_rate = (
            canceled_in_period / active_at_start if active_at_start > 0 else 0.0
        )

        return {
            "churn_rate": round(churn_rate, 4),
            "canceled_in_period": canceled_in_period,
            "active_at_start": active_at_start,
            "window_days": days,
        }

    # ------------------------------------------------------------------
    # Churn trend (per-day cancellation counts)
    # ------------------------------------------------------------------

    async def compute_churn_trend(self, days: int = 30) -> list[dict[str, Any]]:
        """Per-day cancellation counts for the trailing ``days`` window.

        Fetches every cancelled row in the window, buckets them by UTC date,
        and zero-fills any missing days so the returned list always has
        exactly ``days`` entries — suitable for direct rendering in a
        sparkline.

        Args:
            days: Trailing window in days (default 30).

        Returns:
            A list of ``{"date": "YYYY-MM-DD", "canceled": int}`` dicts,
            ordered chronologically (oldest first), with ``len == days``.
        """
        now = datetime.now(tz=timezone.utc)
        window_start = now - timedelta(days=days)
        window_iso = window_start.isoformat()

        result = await execute_async(
            self.client.table("subscriptions")
            .select("updated_at")
            .eq("is_active", False)
            .gte("updated_at", window_iso),
            op_name="billing_metrics.compute_churn_trend",
        )
        rows = result.data or []

        # Pre-build a zero-filled date index for the window. We use the UTC
        # date of (now - i days) for i in [days-1 .. 0] so the list is
        # ordered oldest -> newest.
        buckets: dict[str, int] = {}
        for i in range(days - 1, -1, -1):
            day = (now - timedelta(days=i)).date().isoformat()
            buckets[day] = 0

        # Count cancellations per day. Rows whose updated_at parses to a
        # day outside the constructed window (e.g. a clock skew edge case)
        # are silently dropped — they would not render anywhere anyway.
        for row in rows:
            updated_at = row.get("updated_at")
            if not updated_at:
                continue
            try:
                # Postgres returns ISO-8601 with offset; fromisoformat handles it.
                dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except (TypeError, ValueError):
                logger.debug(
                    "Skipping unparseable updated_at in churn_trend: %r",
                    updated_at,
                )
                continue
            day = dt.astimezone(timezone.utc).date().isoformat()
            if day in buckets:
                buckets[day] += 1

        return [{"date": day, "canceled": count} for day, count in buckets.items()]


__all__ = ["BillingMetricsService"]
