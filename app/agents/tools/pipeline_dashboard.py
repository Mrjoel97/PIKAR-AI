# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Pipeline health dashboard and lead source attribution tools.

Phase 62-02 — SALES-02 / SALES-04.

Provides two agent-callable tools:

* ``get_pipeline_recommendations`` — Classify deals as stalled, at-risk,
  healthy, won, or lost and generate specific action recommendations for
  each stalled or at-risk deal.

* ``get_lead_attribution`` — Break down contacts by source (social, email,
  referral, ad_campaign, …) with conversion rates, plus optional campaign-
  level grouping when UTM data is present.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Stages considered "closed" — skip from active classification.
_CLOSED_WON_STAGES = frozenset({"closedwon", "won", "closed won"})
_CLOSED_LOST_STAGES = frozenset({"closedlost", "lost", "closed lost"})

# Early stages where an imminent close date is a risk signal.
_EARLY_STAGES = frozenset({
    "appointmentscheduled",
    "qualifiedtobuy",
    "presentationscheduled",
    "decisionmakerboughtin",
})


def _get_user_id() -> str | None:
    """Extract the current user ID from the request-scoped context."""
    from app.services.request_context import get_current_user_id

    return get_current_user_id()


def _utc_now() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def _parse_dt(value: str | None) -> datetime | None:
    """Parse an ISO-8601 string into a UTC-aware datetime, returning None on failure."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _days_since(dt_str: str | None) -> int | None:
    """Return days elapsed since an ISO-8601 datetime string, or None."""
    dt = _parse_dt(dt_str)
    if dt is None:
        return None
    return (_utc_now() - dt).days


def _days_until(date_str: str | None) -> int | None:
    """Return days until an ISO-8601 date string, or None."""
    if not date_str:
        return None
    try:
        from datetime import date

        target = date.fromisoformat(date_str[:10])
        return (target - _utc_now().date()).days
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Deal classification helpers
# ---------------------------------------------------------------------------


def _classify_deal(
    deal: dict[str, Any],
    *,
    days_stalled_threshold: int,
    avg_amount: float,
) -> str:
    """Return classification bucket for a single deal row."""
    stage = (deal.get("stage") or "").lower()

    if stage in _CLOSED_WON_STAGES:
        return "won"
    if stage in _CLOSED_LOST_STAGES:
        return "lost"

    # Prefer last_activity_at when available; fall back to updated_at.
    activity_str = deal.get("last_activity_at") or deal.get("updated_at")
    days_inactive = _days_since(activity_str)

    if days_inactive is not None and days_inactive >= days_stalled_threshold:
        return "stalled"

    days_to_close = _days_until(deal.get("close_date"))
    amount = float(deal.get("amount") or 0)

    is_early_stage = stage in _EARLY_STAGES or stage == ""
    close_soon = days_to_close is not None and 0 <= days_to_close <= 14
    low_amount = avg_amount > 0 and amount < avg_amount * 0.5

    if is_early_stage and (close_soon or low_amount):
        return "at_risk"

    return "healthy"


def _build_stalled_actions(deal: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate re-engagement recommendations for a stalled deal."""
    name = deal.get("deal_name", "this deal")
    return [
        {
            "deal_id": deal["id"],
            "deal_name": name,
            "action": f"Send re-engagement email to contact associated with '{name}'",
            "priority": "high",
        },
        {
            "deal_id": deal["id"],
            "deal_name": name,
            "action": "Offer limited-time discount to re-activate interest",
            "priority": "medium",
        },
        {
            "deal_id": deal["id"],
            "deal_name": name,
            "action": "Escalate to manager for strategic review",
            "priority": "medium",
        },
    ]


def _build_at_risk_actions(deal: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate escalation recommendations for an at-risk deal."""
    name = deal.get("deal_name", "this deal")
    return [
        {
            "deal_id": deal["id"],
            "deal_name": name,
            "action": "Schedule urgent review call with decision-maker",
            "priority": "high",
        },
        {
            "deal_id": deal["id"],
            "deal_name": name,
            "action": "Prepare competitive comparison to strengthen position",
            "priority": "medium",
        },
        {
            "deal_id": deal["id"],
            "deal_name": name,
            "action": "Offer extended trial or proof-of-concept to accelerate decision",
            "priority": "medium",
        },
    ]


# ---------------------------------------------------------------------------
# Tool 1: get_pipeline_recommendations
# ---------------------------------------------------------------------------


async def get_pipeline_recommendations(
    days_stalled_threshold: int = 14,
    pipeline: str | None = None,
) -> dict[str, Any]:
    """Classify pipeline deals and return actionable recommendations.

    Queries the hubspot_deals table, classifies each active deal as stalled,
    at_risk, healthy, won, or lost, and generates specific next-action
    recommendations for stalled and at-risk deals.

    Args:
        days_stalled_threshold: Number of days without activity before a deal
            is considered stalled (default: 14).
        pipeline: Optional pipeline name to filter results.

    Returns:
        Dict with ``success``, ``pipeline_health`` (grouped deals),
        ``recommendations`` (action items), and ``summary`` keys.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required", "success": False}

    from app.services.base_service import AdminService
    from app.services.supabase_async import execute_async

    admin = AdminService()

    try:
        query = (
            admin.client.table("hubspot_deals")
            .select("*")
            .eq("user_id", user_id)
        )
        if pipeline:
            query = query.eq("pipeline", pipeline)

        result = await execute_async(
            query.order("updated_at", desc=True),
            op_name="pipeline_dashboard.get_recommendations",
        )
        deals = result.data or []

        # Compute average deal amount for at-risk detection.
        amounts = [float(d.get("amount") or 0) for d in deals]
        avg_amount = sum(amounts) / len(amounts) if amounts else 0.0

        buckets: dict[str, list[dict[str, Any]]] = {
            "stalled": [],
            "at_risk": [],
            "healthy": [],
            "won": [],
            "lost": [],
        }
        recommendations: list[dict[str, Any]] = []

        for deal in deals:
            bucket = _classify_deal(
                deal,
                days_stalled_threshold=days_stalled_threshold,
                avg_amount=avg_amount,
            )
            buckets[bucket].append(deal)

            if bucket == "stalled":
                recommendations.extend(_build_stalled_actions(deal))
            elif bucket == "at_risk":
                recommendations.extend(_build_at_risk_actions(deal))

        total_value = sum(
            float(d.get("amount") or 0)
            for d in deals
            if (d.get("stage") or "").lower() not in _CLOSED_LOST_STAGES
        )

        return {
            "success": True,
            "pipeline_health": buckets,
            "recommendations": recommendations,
            "summary": {
                "total_deals": len(deals),
                "total_value": round(total_value, 2),
                "stalled_count": len(buckets["stalled"]),
                "at_risk_count": len(buckets["at_risk"]),
                "healthy_count": len(buckets["healthy"]),
                "won_count": len(buckets["won"]),
                "lost_count": len(buckets["lost"]),
            },
        }
    except Exception as exc:
        logger.exception("get_pipeline_recommendations failed for user=%s", user_id)
        return {"error": f"Failed to load pipeline recommendations: {exc}", "success": False}


# ---------------------------------------------------------------------------
# Tool 2: get_lead_attribution
# ---------------------------------------------------------------------------


async def get_lead_attribution(
    period_days: int = 90,
) -> dict[str, Any]:
    """Return lead source attribution with conversion rates.

    Queries contacts created in the last ``period_days`` days, groups them by
    source, calculates conversion rates (contacts who reached customer lifecycle
    stage), and includes campaign-level breakdowns when UTM data is present.

    Args:
        period_days: Look-back window in days (default: 90).

    Returns:
        Dict with ``success``, ``attribution`` (by_source, by_campaign,
        totals), and ``period_days`` keys.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required", "success": False}

    from datetime import timedelta

    from app.services.base_service import AdminService
    from app.services.supabase_async import execute_async

    admin = AdminService()

    try:
        cutoff = (_utc_now() - timedelta(days=period_days)).isoformat()
        result = await execute_async(
            admin.client.table("contacts")
            .select("id, source, lifecycle_stage, utm_source, campaign_id")
            .eq("user_id", user_id)
            .gte("created_at", cutoff)
            .order("created_at", desc=True),
            op_name="pipeline_dashboard.get_lead_attribution",
        )
        contacts = result.data or []

        # --- By-source aggregation ---
        source_counts: dict[str, dict[str, int]] = {}
        for contact in contacts:
            src = contact.get("source") or "unknown"
            if src not in source_counts:
                source_counts[src] = {"count": 0, "converted": 0}
            source_counts[src]["count"] += 1
            if (contact.get("lifecycle_stage") or "").lower() == "customer":
                source_counts[src]["converted"] += 1

        by_source = [
            {
                "source": src,
                "count": data["count"],
                "converted": data["converted"],
                "conversion_rate": (
                    round(data["converted"] / data["count"], 4)
                    if data["count"] > 0
                    else 0.0
                ),
            }
            for src, data in sorted(source_counts.items(), key=lambda x: -x[1]["count"])
        ]

        total_leads = len(contacts)
        total_converted = sum(d["converted"] for d in by_source)
        overall_rate = round(total_converted / total_leads, 4) if total_leads > 0 else 0.0

        # --- By-campaign (UTM) aggregation ---
        campaign_counts: dict[str, dict[str, int]] = {}
        for contact in contacts:
            utm = contact.get("utm_source")
            if not utm:
                continue
            if utm not in campaign_counts:
                campaign_counts[utm] = {"count": 0, "converted": 0}
            campaign_counts[utm]["count"] += 1
            if (contact.get("lifecycle_stage") or "").lower() == "customer":
                campaign_counts[utm]["converted"] += 1

        by_campaign = [
            {
                "utm_source": utm,
                "count": data["count"],
                "converted": data["converted"],
                "conversion_rate": (
                    round(data["converted"] / data["count"], 4)
                    if data["count"] > 0
                    else 0.0
                ),
            }
            for utm, data in sorted(campaign_counts.items(), key=lambda x: -x[1]["count"])
        ]

        return {
            "success": True,
            "attribution": {
                "by_source": by_source,
                "by_campaign": by_campaign,
                "total_leads": total_leads,
                "total_converted": total_converted,
                "overall_conversion_rate": overall_rate,
            },
            "period_days": period_days,
        }
    except Exception as exc:
        logger.exception("get_lead_attribution failed for user=%s", user_id)
        return {"error": f"Failed to load lead attribution: {exc}", "success": False}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

PIPELINE_DASHBOARD_TOOLS = [
    get_pipeline_recommendations,
    get_lead_attribution,
]
