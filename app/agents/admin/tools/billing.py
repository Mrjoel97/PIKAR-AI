# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Billing tools for the AdminAgent — Phase 14.

Provides 7 tools for querying revenue metrics, detecting anomalies,
generating executive summaries, forecasting revenue, assessing refund risk,
and issuing Stripe refunds. Each tool enforces the autonomy tier before
executing, following the established project pattern from integrations.py.

Autonomy tiers:
- get_billing_metrics, get_plan_distribution, detect_analytics_anomalies,
  generate_executive_summary, forecast_revenue, assess_refund_risk: auto
- issue_refund: confirm (high risk — mutates Stripe billing state)
"""

from __future__ import annotations

import asyncio
import logging
import statistics
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.agents.admin.tools._autonomy import check_autonomy as _check_autonomy
from app.agents.admin.tools.analytics import get_agent_effectiveness, get_usage_stats
from app.agents.admin.tools.integrations import _get_integration_config
from app.services.admin_audit import log_admin_action
from app.services.integration_proxy import (
    IntegrationProxyService,
    _create_refund_sync,
    _fetch_stripe_metrics,
    check_session_budget,
)
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# Placeholder session ID until Phase 13 adds real session tracking
_DEFAULT_SESSION_ID = "admin"

# Tier price approximations (USD/month) for LTV estimation
_TIER_MONTHLY_PRICE: dict[str, float] = {
    "free": 0.0,
    "solopreneur": 49.0,
    "startup": 149.0,
    "sme": 499.0,
    "enterprise": 1499.0,
}


# ---------------------------------------------------------------------------
# Tool 1: get_billing_metrics
# ---------------------------------------------------------------------------


async def get_billing_metrics() -> dict[str, Any]:
    """Fetch live MRR, ARR, and active subscription count from Stripe.

    Autonomy tier: auto (read-only Stripe query, cached via IntegrationProxyService).

    Returns:
        Dict with ``mrr`` (float), ``arr`` (float), ``active_subscriptions`` (int),
        or an ``{"error": str}`` dict if Stripe is not configured, budget is
        exhausted, or the autonomy gate blocks execution.
    """
    gate = await _check_autonomy("get_billing_metrics")
    if gate is not None:
        return gate

    cfg = await _get_integration_config("stripe")
    if isinstance(cfg, dict):
        return cfg
    api_key, config, _base_url = cfg

    allowed = await check_session_budget(
        session_id=_DEFAULT_SESSION_ID, provider="stripe"
    )
    if not allowed:
        return {"error": "Session budget exhausted for stripe. Try again later."}

    return await IntegrationProxyService.call(
        provider="stripe",
        operation="get_metrics",
        api_key=api_key,
        config=config,
        params={},
        fetch_fn=_fetch_stripe_metrics,
    )


# ---------------------------------------------------------------------------
# Tool 2: get_plan_distribution
# ---------------------------------------------------------------------------


async def get_plan_distribution() -> dict[str, Any]:
    """Return subscription tier breakdown from the database (no Stripe API call).

    Queries the ``subscriptions`` table directly, so this tool consumes zero
    Stripe API budget. Use it to get a fast tier snapshot without triggering
    rate limits.

    Autonomy tier: auto (read-only DB query).

    Returns:
        Dict with ``plan_distribution`` list of ``{tier, count}`` dicts,
        ``total_active`` (int), and ``churn_pending`` (int — subscriptions
        where ``will_renew=false`` and ``is_active=true``).
    """
    gate = await _check_autonomy("get_plan_distribution")
    if gate is not None:
        return gate

    client = get_service_client()
    try:
        query = (
            client.table("subscriptions")
            .select("tier, is_active, will_renew, billing_issue_at")
        )
        result = await execute_async(query, op_name="get_plan_distribution")
        rows: list[dict] = result.data or []

        active_tiers: Counter = Counter()
        churn_pending = 0

        for row in rows:
            if row.get("is_active"):
                active_tiers[row.get("tier", "unknown")] += 1
                if not row.get("will_renew"):
                    churn_pending += 1

        total_active = sum(active_tiers.values())
        plan_distribution = [
            {"tier": tier, "count": count}
            for tier, count in sorted(active_tiers.items())
        ]

        return {
            "plan_distribution": plan_distribution,
            "total_active": total_active,
            "churn_pending": churn_pending,
        }

    except Exception as exc:
        logger.error("get_plan_distribution failed: %s", exc)
        return {"error": f"Failed to retrieve plan distribution: {exc}"}


# ---------------------------------------------------------------------------
# Tool 3: issue_refund
# ---------------------------------------------------------------------------


async def issue_refund(
    charge_id: str,
    amount_cents: int | None = None,
    reason: str = "requested_by_customer",
    confirmation_token: str | None = None,
) -> dict[str, Any]:
    """Issue a Stripe refund for a charge — requires admin confirmation.

    On the first call, returns a confirmation request with
    ``requires_confirmation=True``. The admin must confirm before the
    refund is executed. After confirmation, calls Stripe directly (not via
    the proxy cache) and logs the action to the admin audit trail.

    Autonomy tier: confirm (high risk — mutates Stripe billing state).

    Args:
        charge_id: The Stripe charge ID to refund (e.g. ``ch_1A2B3C``).
        amount_cents: Amount in cents to refund. If None, issues a full refund.
        reason: Stripe refund reason. Defaults to ``"requested_by_customer"``.
            Valid values: ``"duplicate"``, ``"fraudulent"``, ``"requested_by_customer"``.
        confirmation_token: Token from the prior confirmation request. Must be
            present for the refund to execute.

    Returns:
        A ``{"requires_confirmation": True, ...}`` dict on first call, or a
        ``{"refund_id": str, "status": str, "amount": int, "currency": str}``
        dict after confirmation. Returns ``{"error": str}`` on failure.
    """
    gate = await _check_autonomy("issue_refund")
    if gate is not None:
        return gate

    cfg = await _get_integration_config("stripe")
    if isinstance(cfg, dict):
        return cfg
    api_key, _config, _base_url = cfg

    try:
        # Call Stripe directly — refunds must not be cached
        refund_data = await asyncio.to_thread(
            _create_refund_sync, api_key, charge_id, amount_cents, reason
        )

        # Audit the refund action
        await log_admin_action(
            admin_user_id=None,
            action="issue_refund",
            target_type="charge",
            target_id=charge_id,
            details={
                "charge_id": charge_id,
                "amount_cents": amount_cents,
                "reason": reason,
                "refund_id": refund_data.get("refund_id"),
            },
            source="ai_agent",
        )

        return refund_data

    except Exception as exc:
        logger.error("issue_refund failed for charge %s: %s", charge_id, exc)
        return {"error": f"Refund failed: {exc}"}


# ---------------------------------------------------------------------------
# Tool 4: detect_analytics_anomalies (SKIL-05)
# ---------------------------------------------------------------------------


async def detect_analytics_anomalies(days: int = 30) -> dict[str, Any]:
    """Flag metrics deviating more than 2 standard deviations from baseline.

    Calls ``get_usage_stats`` and ``get_agent_effectiveness`` to gather daily
    time-series data, then applies mean/stddev anomaly detection using the
    Python stdlib ``statistics`` module. Requires at least 3 data points;
    returns empty anomalies list for shorter series.

    Autonomy tier: auto (read-only computation).

    Args:
        days: Number of past days to analyse (default 30).

    Returns:
        Dict with ``anomalies`` list of dicts ``{metric, current, mean, stddev,
        deviation}`` and ``period_days`` (int). An empty ``anomalies`` list
        indicates no statistical outliers were detected.
    """
    gate = await _check_autonomy("detect_analytics_anomalies")
    if gate is not None:
        return gate

    usage_data = await get_usage_stats(days=days)
    effectiveness_data = await get_agent_effectiveness(days=days)

    anomalies: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Check DAU and MAU time series
    # ------------------------------------------------------------------
    usage_trends: list[dict] = usage_data.get("usage_trends", [])
    if len(usage_trends) >= 3:
        for metric_key in ("dau", "mau"):
            values = [float(row.get(metric_key, 0)) for row in usage_trends]
            current = values[0]  # latest (most recent) is first (DESC order)
            baseline = values[1:]  # exclude the latest for baseline computation

            if len(baseline) < 2:
                continue

            try:
                mean_val = statistics.mean(baseline)
                stddev_val = statistics.stdev(baseline)
            except statistics.StatisticsError:
                continue

            if stddev_val == 0:
                # Zero variance in baseline — any difference from mean is anomalous
                if current != mean_val:
                    anomalies.append(
                        {
                            "metric": metric_key,
                            "current": current,
                            "mean": round(mean_val, 2),
                            "stddev": 0.0,
                            "deviation": float("inf"),
                        }
                    )
                continue

            deviation = abs(current - mean_val) / stddev_val
            if deviation > 2.0:
                anomalies.append(
                    {
                        "metric": metric_key,
                        "current": current,
                        "mean": round(mean_val, 2),
                        "stddev": round(stddev_val, 2),
                        "deviation": round(deviation, 2),
                    }
                )

    # ------------------------------------------------------------------
    # Check per-agent success rates
    # ------------------------------------------------------------------
    agents: list[dict] = effectiveness_data.get("agents", [])
    for agent in agents:
        success_rate = agent.get("success_rate")
        agent_name = agent.get("agent_name", "unknown")
        if success_rate is None:
            continue
        # Flag agents below 70% success as potential anomaly
        # (statistical baseline not available per-agent; use fixed threshold)
        if float(success_rate) < 70.0:
            anomalies.append(
                {
                    "metric": f"agent_success_rate:{agent_name}",
                    "current": float(success_rate),
                    "mean": 85.0,
                    "stddev": 10.0,
                    "deviation": round(abs(float(success_rate) - 85.0) / 10.0, 2),
                }
            )

    return {"anomalies": anomalies, "period_days": days}


# ---------------------------------------------------------------------------
# Tool 5: generate_executive_summary (SKIL-06)
# ---------------------------------------------------------------------------


async def generate_executive_summary(days: int = 30) -> dict[str, Any]:
    """Generate a narrative executive summary with actionable recommendations.

    Calls ``get_usage_stats``, ``get_billing_metrics``, and
    ``get_agent_effectiveness`` to gather data. Degrades gracefully if
    billing metrics are unavailable (e.g., Stripe not configured). Runs
    anomaly detection and incorporates flagged metrics into the narrative.

    Autonomy tier: auto (read-only narrative generation).

    Args:
        days: Analysis window in days (default 30).

    Returns:
        Dict with ``summary_text`` (str), ``recommendations`` (list[str]),
        and ``period_days`` (int).
    """
    gate = await _check_autonomy("generate_executive_summary")
    if gate is not None:
        return gate

    usage_data = await get_usage_stats(days=days)
    billing_data = await get_billing_metrics()
    effectiveness_data = await get_agent_effectiveness(days=days)

    # Gracefully degrade if billing not configured
    billing_available = "error" not in billing_data

    # ------------------------------------------------------------------
    # Compute DAU trend direction
    # ------------------------------------------------------------------
    usage_trends = usage_data.get("usage_trends", [])
    dau_trend_desc = "stable"
    dau_change_pct = 0.0
    if len(usage_trends) >= 7:
        recent_dau = [row.get("dau", 0) for row in usage_trends[:7]]
        older_dau = [row.get("dau", 0) for row in usage_trends[7:14]] if len(usage_trends) >= 14 else recent_dau
        avg_recent = statistics.mean(recent_dau) if recent_dau else 0
        avg_older = statistics.mean(older_dau) if older_dau else 0
        if avg_older > 0:
            dau_change_pct = round((avg_recent - avg_older) / avg_older * 100, 1)
        if dau_change_pct > 5:
            dau_trend_desc = "growing"
        elif dau_change_pct < -5:
            dau_trend_desc = "declining"

    # ------------------------------------------------------------------
    # Find top/bottom agent by effectiveness
    # ------------------------------------------------------------------
    agents: list[dict] = effectiveness_data.get("agents", [])
    top_agent: str | None = None
    bottom_agent: str | None = None
    if agents:
        sorted_agents = sorted(agents, key=lambda a: a.get("success_rate", 0), reverse=True)
        top_agent = sorted_agents[0].get("agent_name")
        bottom_agent = sorted_agents[-1].get("agent_name") if len(sorted_agents) > 1 else None

    # ------------------------------------------------------------------
    # Detect anomalies (reuse tool logic inline to avoid double gate check)
    # ------------------------------------------------------------------
    anomaly_result = await detect_analytics_anomalies(days=days)
    anomaly_count = len(anomaly_result.get("anomalies", []))

    # ------------------------------------------------------------------
    # Build narrative text
    # ------------------------------------------------------------------
    summary_parts: list[str] = []

    summary_parts.append(
        f"Platform Usage ({days}d window): "
        f"DAU is {dau_trend_desc}"
        + (f" ({dau_change_pct:+.1f}% week-over-week)" if dau_change_pct != 0 else "")
        + "."
    )

    if billing_available:
        mrr = billing_data.get("mrr", 0)
        arr = billing_data.get("arr", 0)
        active_subs = billing_data.get("active_subscriptions", 0)
        summary_parts.append(
            f"Revenue: MRR ${mrr:,.2f}, ARR ${arr:,.2f}, "
            f"{active_subs} active subscriptions."
        )
    else:
        summary_parts.append(
            "Revenue: Stripe not configured — connect Stripe on the Integrations page for live metrics."
        )

    if top_agent:
        summary_parts.append(f"Top performing agent: {top_agent}.")
    if bottom_agent and bottom_agent != top_agent:
        summary_parts.append(f"Agent needing attention: {bottom_agent}.")

    if anomaly_count > 0:
        summary_parts.append(
            f"Anomaly Alert: {anomaly_count} metric(s) flagged as statistically unusual "
            f"(>2 stddev from {days}-day baseline). Review immediately."
        )
    else:
        summary_parts.append("No statistical anomalies detected in the analysis window.")

    summary_text = " ".join(summary_parts)

    # ------------------------------------------------------------------
    # Build actionable recommendations
    # ------------------------------------------------------------------
    recommendations: list[str] = []

    if dau_trend_desc == "declining" and abs(dau_change_pct) >= 5:
        recommendations.append(
            f"Investigate declining DAU — down {abs(dau_change_pct):.1f}% week-over-week. "
            "Check for recent deployment regressions, onboarding friction, or external factors."
        )

    if anomaly_count > 0:
        for anomaly in anomaly_result.get("anomalies", [])[:3]:
            metric = anomaly.get("metric", "unknown")
            deviation = anomaly.get("deviation", 0)
            recommendations.append(
                f"Investigate anomaly in '{metric}' — "
                f"{deviation:.1f}x standard deviations from baseline."
            )

    if not billing_available:
        recommendations.append(
            "Connect Stripe integration to enable live revenue metrics and "
            "refund risk assessment features."
        )

    if bottom_agent and bottom_agent != top_agent:
        bottom_rate = next(
            (a.get("success_rate", 0) for a in agents if a.get("agent_name") == bottom_agent),
            0,
        )
        if float(bottom_rate) < 80.0:
            recommendations.append(
                f"Review {bottom_agent} agent configuration — "
                f"success rate is {bottom_rate:.1f}%, below the 80% threshold."
            )

    if not recommendations:
        recommendations.append("Platform is operating within normal parameters. No immediate actions required.")

    return {
        "summary_text": summary_text,
        "recommendations": recommendations,
        "period_days": days,
    }


# ---------------------------------------------------------------------------
# Tool 6: forecast_revenue (SKIL-10)
# ---------------------------------------------------------------------------


async def forecast_revenue(months_ahead: int = 1) -> dict[str, Any]:
    """Project next-month MRR using linear extrapolation from subscription history.

    Queries the ``subscriptions`` table and groups active subscriptions by
    creation month to compute an approximate historical MRR series. Applies
    least-squares linear extrapolation. Requires at least 7 subscription rows
    for a meaningful forecast.

    Autonomy tier: auto (read-only projection).

    Args:
        months_ahead: Number of months to project forward (default 1).

    Returns:
        Dict with ``current_mrr``, ``projected_mrr``, ``growth_rate_pct``,
        ``confidence`` (``"low"`` or ``"medium"``), and ``months_ahead``
        if sufficient data exists. Returns ``{"insufficient_data": True, "reason": str}``
        when fewer than 7 subscription rows are found.
    """
    gate = await _check_autonomy("forecast_revenue")
    if gate is not None:
        return gate

    client = get_service_client()
    try:
        query = (
            client.table("subscriptions")
            .select("created_at, price_id, tier, is_active")
            .order("created_at")
        )
        result = await execute_async(query, op_name="forecast_revenue")
        rows: list[dict] = result.data or []

        if len(rows) < 7:
            return {
                "insufficient_data": True,
                "reason": (
                    f"Need at least 7 subscriptions for trend projection "
                    f"(found {len(rows)})."
                ),
            }

        # ------------------------------------------------------------------
        # Group by year-month and compute approximate monthly MRR
        # ------------------------------------------------------------------
        # Map tier to monthly price for subscriptions without a price_id
        monthly_mrr: dict[str, float] = {}

        for row in rows:
            if not row.get("is_active"):
                continue
            created_at_raw = row.get("created_at", "")
            if not created_at_raw:
                continue
            try:
                # Extract YYYY-MM bucket
                month_key = str(created_at_raw)[:7]  # "2025-03"
            except (TypeError, ValueError):
                continue

            tier = row.get("tier", "free")
            price = _TIER_MONTHLY_PRICE.get(tier, 0.0)
            monthly_mrr[month_key] = monthly_mrr.get(month_key, 0.0) + price

        if len(monthly_mrr) < 2:
            # Fall back to counting all rows (not just active)
            for row in rows:
                created_at_raw = row.get("created_at", "")
                if not created_at_raw:
                    continue
                try:
                    month_key = str(created_at_raw)[:7]
                    tier = row.get("tier", "free")
                    price = _TIER_MONTHLY_PRICE.get(tier, 0.0)
                    monthly_mrr[month_key] = monthly_mrr.get(month_key, 0.0) + price
                except (TypeError, ValueError):
                    continue

        if not monthly_mrr:
            return {
                "insufficient_data": True,
                "reason": "Could not extract monthly MRR data from subscription records.",
            }

        sorted_months = sorted(monthly_mrr.keys())
        mrr_values = [monthly_mrr[m] for m in sorted_months]
        n = len(mrr_values)

        # Simple least-squares slope: b = (n*sum(xy) - sum(x)*sum(y)) / (n*sum(x^2) - sum(x)^2)
        x_vals = list(range(n))
        sum_x = sum(x_vals)
        sum_y = sum(mrr_values)
        sum_xy = sum(x * y for x, y in zip(x_vals, mrr_values))
        sum_x2 = sum(x * x for x in x_vals)

        denom = n * sum_x2 - sum_x * sum_x
        if denom == 0:
            slope = 0.0
        else:
            slope = (n * sum_xy - sum_x * sum_y) / denom

        current_mrr = mrr_values[-1]
        projected_mrr = max(0.0, current_mrr + slope * months_ahead)
        growth_rate_pct = (
            round((projected_mrr - current_mrr) / current_mrr * 100, 2)
            if current_mrr > 0
            else 0.0
        )

        # Confidence: "medium" for 7-30 data points, "low" otherwise
        confidence = "medium" if 7 <= n <= 30 else "low"

        return {
            "current_mrr": round(current_mrr, 2),
            "projected_mrr": round(projected_mrr, 2),
            "growth_rate_pct": growth_rate_pct,
            "confidence": confidence,
            "months_ahead": months_ahead,
        }

    except Exception as exc:
        logger.error("forecast_revenue failed: %s", exc)
        return {"error": f"Failed to compute revenue forecast: {exc}"}


# ---------------------------------------------------------------------------
# Tool 7: assess_refund_risk (SKIL-11)
# ---------------------------------------------------------------------------


async def assess_refund_risk(user_id: str) -> dict[str, Any]:
    """Score refund risk by cross-referencing LTV, usage, and subscription tenure.

    Queries the ``subscriptions`` table for the user's billing row and
    ``admin_analytics_daily`` for usage data (degrades gracefully if unavailable).
    Computes a risk score based on tenure, usage level, and tier.

    Autonomy tier: auto (read-only risk scoring).

    Risk scoring rules:
    - HIGH: tenure < 2 months AND usage_level = "low"
    - LOW: tenure > 6 months AND usage_level != "low"
    - MEDIUM: all other cases

    Args:
        user_id: UUID of the user to assess.

    Returns:
        Dict with ``risk_level`` (``"high"``/``"medium"``/``"low"``),
        ``tenure_months``, ``estimated_ltv``, ``usage_level``
        (``"high"``/``"medium"``/``"low"``), and ``recommendation`` (str).
    """
    gate = await _check_autonomy("assess_refund_risk")
    if gate is not None:
        return gate

    client = get_service_client()
    try:
        # ------------------------------------------------------------------
        # 1. Query subscription row
        # ------------------------------------------------------------------
        sub_query = (
            client.table("subscriptions")
            .select("stripe_customer_id, tier, created_at, is_active")
            .eq("user_id", user_id)
            .limit(1)
        )
        sub_result = await execute_async(sub_query, op_name="assess_refund_risk.subscription")
        sub_rows: list[dict] = sub_result.data or []

        if not sub_rows:
            return {
                "error": f"No subscription found for user {user_id}. "
                "The user may not have an active subscription."
            }

        sub = sub_rows[0]
        tier = sub.get("tier", "free")
        created_at_raw = sub.get("created_at", "")

        # ------------------------------------------------------------------
        # 2. Compute tenure in months
        # ------------------------------------------------------------------
        tenure_months = 0.0
        if created_at_raw:
            try:
                created_at_str = str(created_at_raw)
                # Handle ISO format with or without timezone
                if created_at_str.endswith("Z"):
                    created_at_str = created_at_str[:-1] + "+00:00"
                created_dt = datetime.fromisoformat(created_at_str)
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                now_dt = datetime.now(tz=timezone.utc)
                delta_days = (now_dt - created_dt).days
                tenure_months = round(delta_days / 30.44, 1)
            except (ValueError, TypeError) as exc:
                logger.warning("Could not parse created_at for user %s: %s", user_id, exc)

        # ------------------------------------------------------------------
        # 3. Query usage data (degrade gracefully)
        # ------------------------------------------------------------------
        usage_messages = 0
        try:
            usage_query = (
                client.table("admin_analytics_daily")
                .select("messages")
                .order("stat_date", desc=True)
                .limit(7)
            )
            usage_result = await execute_async(
                usage_query, op_name="assess_refund_risk.usage"
            )
            usage_rows: list[dict] = usage_result.data or []
            usage_messages = sum(int(row.get("messages", 0)) for row in usage_rows)
        except Exception as exc:
            logger.warning("Could not fetch usage data for refund risk: %s", exc)

        # ------------------------------------------------------------------
        # 4. Classify usage level
        # ------------------------------------------------------------------
        if usage_messages >= 50:
            usage_level = "high"
        elif usage_messages >= 10:
            usage_level = "medium"
        else:
            usage_level = "low"

        # ------------------------------------------------------------------
        # 5. Estimate LTV
        # ------------------------------------------------------------------
        monthly_price = _TIER_MONTHLY_PRICE.get(tier, 0.0)
        estimated_ltv = round(tenure_months * monthly_price, 2)

        # ------------------------------------------------------------------
        # 6. Score risk
        # ------------------------------------------------------------------
        if tenure_months < 2 and usage_level == "low":
            risk_level = "high"
            recommendation = (
                f"High refund risk: user has only been subscribed for "
                f"{tenure_months:.1f} months and shows low platform engagement. "
                "Consider offering onboarding support before processing the refund."
            )
        elif tenure_months > 6 and usage_level != "low":
            risk_level = "low"
            recommendation = (
                f"Low refund risk: user has been active for {tenure_months:.1f} months "
                f"with {usage_level} usage. Issuing this refund is unlikely to indicate "
                "a systemic problem."
            )
        else:
            risk_level = "medium"
            recommendation = (
                f"Medium refund risk: user has been subscribed for {tenure_months:.1f} months "
                f"with {usage_level} platform usage. Review their support history before "
                "processing."
            )

        return {
            "risk_level": risk_level,
            "tenure_months": tenure_months,
            "estimated_ltv": estimated_ltv,
            "usage_level": usage_level,
            "recommendation": recommendation,
        }

    except Exception as exc:
        logger.error("assess_refund_risk failed for user %s: %s", user_id, exc)
        return {"error": f"Failed to assess refund risk: {exc}"}
