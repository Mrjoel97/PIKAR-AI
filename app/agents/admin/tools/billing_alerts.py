# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Billing alert tools for the AdminAgent — Phase 69-02.

Provides two tools for proactive billing cost projection alerting:

- ``get_billing_cost_projection``: On-demand cost projection with
  month-over-month comparison and top cost drivers. Auto tier.
- ``check_billing_alerts``: Scheduled tick that checks projections and
  dispatches notifications when thresholds are breached. Auto tier.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.admin.tools._autonomy import check_autonomy as _check_autonomy
from app.services.billing_alert_service import BillingAlertService

logger = logging.getLogger(__name__)


async def get_billing_cost_projection() -> dict[str, Any]:
    """Get current AI cost projection with month-over-month comparison.

    Computes the projected full-month AI spend based on the 7-day linear
    extrapolation, compares against the prior month's total, identifies top
    cost drivers by agent, and generates a plain-English explanation.

    Autonomy tier: auto (read-only computation).

    Returns:
        Dict with ``mtd_actual``, ``projected_full_month``, ``prior_month_total``,
        ``month_over_month_change_pct``, ``top_cost_drivers`` (list),
        ``alert_recommended`` (bool), ``severity`` (str or None), and
        ``plain_english_summary`` (str). Returns ``{"error": str}`` on failure.
    """
    gate = await _check_autonomy("get_billing_cost_projection")
    if gate is not None:
        return gate

    try:
        svc = BillingAlertService()
        return await svc.compute_cost_projection()
    except Exception as exc:
        logger.error("get_billing_cost_projection failed: %s", exc)
        return {"error": f"Failed to compute billing cost projection: {exc}"}


async def check_billing_alerts() -> dict[str, Any]:
    """Check billing cost projections and dispatch alerts when thresholds are breached.

    This tool is intended for the scheduled monitoring tick (Cloud Scheduler),
    NOT for normal conversation use. It checks the current cost projection and
    dispatches ``billing.cost_projection_alert`` notifications to admin users
    when projected spend exceeds 20% (warning) or 50% (critical) of the prior
    month's total.

    Autonomy tier: auto (read-only check + conditional notification dispatch).

    Returns:
        Dict with ``alerted`` (bool), ``projection`` (dict), and
        ``notifications_sent`` (int). Returns ``{"error": str}`` on failure.
    """
    gate = await _check_autonomy("check_billing_alerts")
    if gate is not None:
        return gate

    try:
        svc = BillingAlertService()
        return await svc.check_and_alert()
    except Exception as exc:
        logger.error("check_billing_alerts failed: %s", exc)
        return {"error": f"Failed to run billing alert check: {exc}"}


__all__ = ["check_billing_alerts", "get_billing_cost_projection"]
