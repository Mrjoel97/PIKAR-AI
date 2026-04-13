# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""BillingAlertService — proactive billing cost projection alerts.

Phase 69-02 / ADMIN-03.

Computes month-over-month AI cost projections by bridging the existing
ObservabilityMetricsService (which already provides project_monthly_ai_spend
and cost-by-agent/day methods) with the notification dispatcher.

Severity thresholds:
- >20% projected increase vs prior month → "warning"
- >50% projected increase vs prior month → "critical"

Plain-English summary explains the main cost driver for actionable insight.
"""

from __future__ import annotations

import logging
from calendar import monthrange
from datetime import datetime, timezone
from typing import Any, ClassVar

from app.services.base_service import AdminService
from app.services.notification_dispatcher import dispatch_notification
from app.services.observability_metrics_service import ObservabilityMetricsService
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


class BillingAlertService(AdminService):
    """Proactive billing cost projection and alerting service.

    Computes month-over-month AI spend comparisons and dispatches
    notifications when usage trends exceed configured thresholds.

    Thresholds are checked against projected_full_month vs prior_month_total:
    - ``COST_INCREASE_WARNING_THRESHOLD`` (20%): severity "warning"
    - ``COST_INCREASE_CRITICAL_THRESHOLD`` (50%): severity "critical"

    Uses :class:`~app.services.observability_metrics_service.ObservabilityMetricsService`
    for cost data and :func:`~app.services.notification_dispatcher.dispatch_notification`
    for fan-out delivery.
    """

    #: 20% projected increase triggers a warning alert.
    COST_INCREASE_WARNING_THRESHOLD: ClassVar[float] = 0.20

    #: 50% projected increase triggers a critical alert.
    COST_INCREASE_CRITICAL_THRESHOLD: ClassVar[float] = 0.50

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def compute_cost_projection(self) -> dict[str, Any]:
        """Compute AI cost projection with month-over-month comparison.

        Steps:
        1. Fetch current month projection via ObservabilityMetricsService.
        2. Compute prior month total from daily costs.
        3. Derive month-over-month change percentage.
        4. Identify top cost drivers for the current MTD window.
        5. Determine severity based on thresholds.
        6. Generate a plain-English summary.

        Returns:
            Dict with keys: ``mtd_actual``, ``projected_full_month``,
            ``prior_month_total``, ``month_over_month_change_pct``,
            ``top_cost_drivers``, ``alert_recommended``, ``severity``,
            ``plain_english_summary``.
        """
        obs = ObservabilityMetricsService()
        now = datetime.now(tz=timezone.utc)

        # ------------------------------------------------------------------
        # 1. Current month projection
        # ------------------------------------------------------------------
        projection = await obs.project_monthly_ai_spend()
        mtd_actual: float = projection["mtd_actual"]
        projected_full_month: float = projection["projected_full_month"]

        # ------------------------------------------------------------------
        # 2. Prior month total
        # ------------------------------------------------------------------
        if now.month == 1:
            prior_year = now.year - 1
            prior_month = 12
        else:
            prior_year = now.year
            prior_month = now.month - 1

        days_in_prior = monthrange(prior_year, prior_month)[1]
        prior_start = datetime(prior_year, prior_month, 1, tzinfo=timezone.utc)
        prior_end = datetime(prior_year, prior_month, days_in_prior, 23, 59, 59, tzinfo=timezone.utc)

        prior_daily = await obs.compute_ai_cost_by_day(prior_start, prior_end)
        prior_month_total: float = round(sum(entry["cost_usd"] for entry in prior_daily), 4)

        # ------------------------------------------------------------------
        # 3. Month-over-month change
        # ------------------------------------------------------------------
        if prior_month_total > 0:
            change_pct = (projected_full_month - prior_month_total) / prior_month_total * 100
        else:
            # New usage — treat as 100% increase for threshold purposes when projected > 0
            change_pct = 100.0 if projected_full_month > 0 else 0.0

        change_pct = round(change_pct, 2)

        # ------------------------------------------------------------------
        # 4. Top cost drivers (MTD)
        # ------------------------------------------------------------------
        mtd_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        agent_costs = await obs.compute_ai_cost_by_agent(mtd_start, now)

        total_agent_spend = sum(agent_costs.values()) or 1.0  # avoid div-by-zero
        sorted_agents = sorted(agent_costs.items(), key=lambda x: x[1], reverse=True)
        top_cost_drivers = [
            {
                "agent_name": agent_name,
                "cost_usd": round(cost, 4),
                "pct_of_total": round(cost / total_agent_spend * 100, 1),
            }
            for agent_name, cost in sorted_agents[:5]
        ]

        # ------------------------------------------------------------------
        # 5. Severity determination
        # ------------------------------------------------------------------
        alert_recommended = False
        severity: str | None = None

        change_fraction = change_pct / 100.0
        if change_fraction > self.COST_INCREASE_CRITICAL_THRESHOLD:
            alert_recommended = True
            severity = "critical"
        elif change_fraction > self.COST_INCREASE_WARNING_THRESHOLD:
            alert_recommended = True
            severity = "warning"

        # ------------------------------------------------------------------
        # 6. Plain-English summary
        # ------------------------------------------------------------------
        plain_english_summary = self._build_summary(
            projected_full_month=projected_full_month,
            prior_month_total=prior_month_total,
            change_pct=change_pct,
            top_cost_drivers=top_cost_drivers,
        )

        return {
            "mtd_actual": mtd_actual,
            "projected_full_month": projected_full_month,
            "prior_month_total": prior_month_total,
            "month_over_month_change_pct": change_pct,
            "top_cost_drivers": top_cost_drivers,
            "alert_recommended": alert_recommended,
            "severity": severity,
            "plain_english_summary": plain_english_summary,
        }

    async def check_and_alert(
        self,
        admin_user_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Check cost projection and dispatch notifications if thresholds are exceeded.

        When ``alert_recommended`` is True, dispatches a
        ``billing.cost_projection_alert`` event to each admin user via the
        notification dispatcher.  When ``admin_user_ids`` is not provided, the
        method queries ``user_executive_agents`` for admin-persona users.

        Args:
            admin_user_ids: Optional explicit list of admin user IDs to notify.
                If None, falls back to querying the DB for admin-persona users.

        Returns:
            Dict with keys: ``alerted`` (bool), ``projection`` (dict),
            ``notifications_sent`` (int).
        """
        projection = await self.compute_cost_projection()
        notifications_sent = 0

        if not projection["alert_recommended"]:
            return {
                "alerted": False,
                "projection": projection,
                "notifications_sent": 0,
            }

        # Resolve admin user IDs if not provided
        if admin_user_ids is None:
            admin_user_ids = await self._fetch_admin_user_ids()

        # Build notification payload
        payload = {
            "title": f"Billing Alert ({projection['severity']}): AI costs trending higher",
            "body": projection["plain_english_summary"],
            "severity": projection["severity"],
            "projected_full_month": projection["projected_full_month"],
            "prior_month_total": projection["prior_month_total"],
            "month_over_month_change_pct": projection["month_over_month_change_pct"],
        }

        for user_id in admin_user_ids:
            try:
                await dispatch_notification(
                    user_id,
                    "billing.cost_projection_alert",
                    payload,
                )
                notifications_sent += 1
            except Exception:
                logger.exception(
                    "Failed to dispatch billing alert to user_id=%s", user_id
                )

        logger.info(
            "Billing alert dispatched: severity=%s notifications_sent=%d",
            projection["severity"],
            notifications_sent,
        )
        return {
            "alerted": True,
            "projection": projection,
            "notifications_sent": notifications_sent,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_summary(
        self,
        projected_full_month: float,
        prior_month_total: float,
        change_pct: float,
        top_cost_drivers: list[dict[str, Any]],
    ) -> str:
        """Build a plain-English cost projection summary.

        Args:
            projected_full_month: Projected full-month AI spend in USD.
            prior_month_total: Prior month's total AI spend in USD.
            change_pct: Month-over-month change percentage (can be negative).
            top_cost_drivers: Sorted list of top cost driver dicts.

        Returns:
            Human-readable projection summary string.
        """
        direction = "higher" if change_pct >= 0 else "lower"
        abs_change = abs(change_pct)

        summary = (
            f"At current usage, this month's AI costs are projected to be "
            f"${projected_full_month:.2f} — {abs_change:.0f}% {direction} than "
            f"last month (${prior_month_total:.2f})."
        )

        if change_pct > 0 and top_cost_drivers:
            top = top_cost_drivers[0]
            summary += (
                f" The main cost driver is {top['agent_name']} at "
                f"${top['cost_usd']:.2f} ({top['pct_of_total']:.0f}% of total spend)."
            )
        elif change_pct <= 0:
            trend = "flat" if abs_change < 1 else "down"
            summary += f" Costs are trending {trend} compared to last month."

        return summary

    async def _fetch_admin_user_ids(self) -> list[str]:
        """Fetch admin persona user IDs from user_executive_agents.

        Returns:
            List of user ID strings for admin-persona users.
        """
        try:
            result = await execute_async(
                self.client.table("user_executive_agents")
                .select("user_id")
                .eq("persona", "admin"),
                op_name="billing_alert.fetch_admin_users",
            )
            rows = result.data or []
            return [row["user_id"] for row in rows if row.get("user_id")]
        except Exception:
            logger.exception("Could not fetch admin user IDs for billing alert")
            return []


__all__ = ["BillingAlertService"]
