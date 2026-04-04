# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Stripe agent tools -- revenue summary and manual sync trigger.

Provides two agent-callable functions that wire into the StripeSyncService
and financial_records table created in Phase 41 Plan 01.  Tools extract the
current user from request context and return structured dicts for the agent.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user_id() -> str | None:
    """Extract the current user ID from the request-scoped context."""
    from app.services.request_context import get_current_user_id

    return get_current_user_id()


# ---------------------------------------------------------------------------
# Period date calculation
# ---------------------------------------------------------------------------

_PERIOD_OFFSETS: dict[str, int] = {
    "current_month": 30,
    "last_month": 60,
    "last_3_months": 90,
    "last_6_months": 180,
    "last_year": 365,
}


def _period_start_date(period: str) -> str | None:
    """Return an ISO-8601 date string for the start of *period*.

    Returns None for all_time.
    """
    days = _PERIOD_OFFSETS.get(period)
    if days is None:
        return None  # all_time
    return (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# Tool: get_stripe_revenue_summary
# ---------------------------------------------------------------------------


async def get_stripe_revenue_summary(
    period: str = "current_month",
) -> dict[str, Any]:
    """Get revenue summary from Stripe transactions.

    Queries financial_records filtered to source_type='stripe' and
    transaction_type='revenue' for the given period.

    Period can be 'current_month', 'last_month', 'last_3_months',
    'last_6_months', 'last_year', or 'all_time'.

    Args:
        period: Time range for the revenue summary.

    Returns:
        Dict with total_revenue, transaction_count, period, and
        avg_transaction_value.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.base_service import BaseService

    svc = BaseService()

    try:
        query = (
            svc.client.table("financial_records")
            .select("amount, currency, transaction_date")
            .eq("user_id", user_id)
            .eq("transaction_type", "revenue")
            .eq("source_type", "stripe")
        )

        start_date = _period_start_date(period)
        if start_date:
            query = query.gte("transaction_date", start_date)

        from app.services.supabase_async import execute_async

        result = await execute_async(query, op_name="stripe_tools.revenue_summary")
        records = result.data or []

        total_revenue = sum(float(r.get("amount", 0)) for r in records)
        count = len(records)
        avg_value = round(total_revenue / count, 2) if count else 0

        return {
            "total_revenue": round(total_revenue, 2),
            "transaction_count": count,
            "period": period,
            "avg_transaction_value": avg_value,
            "currency": records[0].get("currency", "USD") if records else "USD",
        }
    except Exception as exc:
        logger.exception("stripe_tools.revenue_summary failed for user=%s", user_id)
        return {"error": f"Failed to retrieve Stripe revenue: {exc}"}


# ---------------------------------------------------------------------------
# Tool: trigger_stripe_sync
# ---------------------------------------------------------------------------


async def trigger_stripe_sync() -> dict[str, Any]:
    """Trigger a manual sync of Stripe transaction history (last 12 months).

    Use when the user suspects missing transactions or wants to force
    a fresh import from Stripe.

    Returns:
        Dict with imported and skipped counts, or an error message.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.stripe_sync_service import StripeSyncService

    svc = StripeSyncService()

    try:
        result = await svc.sync_history(user_id)
        return {
            "status": "success",
            "imported": result.get("imported", 0),
            "skipped": result.get("skipped", 0),
            "message": (
                f"Stripe sync complete: {result.get('imported', 0)} new transactions "
                f"imported, {result.get('skipped', 0)} duplicates skipped."
            ),
        }
    except Exception as exc:
        logger.exception("trigger_stripe_sync failed for user=%s", user_id)
        return {"error": f"Stripe sync failed: {exc}"}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

STRIPE_TOOLS = [get_stripe_revenue_summary, trigger_stripe_sync]
