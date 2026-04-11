# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""CrossChannelAttributionService - unified marketing channel attribution.

Aggregates spend and revenue across four channels -- Google Ads, Meta Ads,
email campaigns (UTM-tracked), and Shopify organic -- into a single
ROAS-comparable view, then derives budget reallocation recommendations from
the relative performance of those channels.

Used by the Marketing Agent to answer questions like "which channel should
I shift more budget to?" without requiring the user to reconcile platform
dashboards manually.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from app.agents.tools.shopify_tools import get_shopify_analytics
from app.services.ad_management_service import (
    AdCampaignService,
    AdSpendTrackingService,
)
from app.services.base_service import BaseService
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


class CrossChannelAttributionService(BaseService):
    """Unified cross-channel attribution and ROAS-based budget optimizer."""

    def __init__(self, user_token: str | None = None):
        """Initialize the attribution service.

        Args:
            user_token: Optional user JWT for RLS-scoped queries.
        """
        super().__init__(user_token)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_attribution(self, user_id: str, days: int = 30) -> dict[str, Any]:
        """Return unified per-channel attribution for the given window.

        Args:
            user_id: Owner of the campaigns / Shopify store.
            days: Lookback window in days (default 30).

        Returns:
            Dict with channels, totals, period, and summary_text.
        """
        start_date = date.today() - timedelta(days=days)
        end_date = date.today()

        # Fetch per-platform ad data
        google_data = await self._aggregate_ad_channel(user_id, "google_ads", days)
        meta_data = await self._aggregate_ad_channel(user_id, "meta_ads", days)

        # Email attribution (platform subclasses can override _get_email_attribution)
        email_data = await self._get_email_attribution(user_id, days)

        # Organic = total Shopify revenue minus attributed paid/email revenue
        attributed_revenue = (
            google_data.get("revenue", 0.0)
            + meta_data.get("revenue", 0.0)
            + email_data.get("revenue", 0.0)
        )
        organic_data = await self._get_organic_revenue(
            user_id, days, attributed_revenue
        )

        channels_raw = [
            self._build_channel_dict("google_ads", google_data),
            self._build_channel_dict("meta_ads", meta_data),
            self._build_channel_dict("email", email_data),
            self._build_channel_dict("organic", organic_data),
        ]

        total_revenue = sum(c["revenue"] for c in channels_raw)
        total_spend = sum(c["spend"] for c in channels_raw)
        total_conversions = sum(c["conversions"] for c in channels_raw)

        # Compute share_of_revenue_pct for each channel
        channels = []
        for ch in channels_raw:
            share = (
                round((ch["revenue"] / total_revenue) * 100, 1)
                if total_revenue > 0
                else 0.0
            )
            ch["share_of_revenue_pct"] = share
            channels.append(ch)

        # Normalize share rounding drift -- assign residual to the largest channel
        share_sum = sum(c["share_of_revenue_pct"] for c in channels)
        if channels and total_revenue > 0 and share_sum != 100.0:
            drift = round(100.0 - share_sum, 1)
            largest = max(channels, key=lambda c: c["revenue"])
            largest["share_of_revenue_pct"] = round(
                largest["share_of_revenue_pct"] + drift, 1
            )

        blended_roas = (
            round(total_revenue / total_spend, 2) if total_spend > 0 else 0.0
        )

        summary_text = self._build_summary_text(channels)

        return {
            "channels": channels,
            "totals": {
                "total_spend": round(total_spend, 2),
                "total_revenue": round(total_revenue, 2),
                "total_conversions": total_conversions,
                "blended_roas": blended_roas,
            },
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days,
            },
            "summary_text": summary_text,
        }

    async def get_budget_recommendation(
        self, user_id: str, days: int = 30
    ) -> dict[str, Any]:
        """Return a ROAS-based budget reallocation recommendation.

        Args:
            user_id: Owner of the campaigns.
            days: Lookback window in days (default 30).

        Returns:
            Dict with recommendation_text, shift_from, shift_to,
            expected_impact, channels, and action_available.
        """
        attribution = await self.get_attribution(user_id, days)
        channels = attribution["channels"]

        # Eligible channels for reallocation: must have spend > 0 (organic has no spend
        # lever, so it is excluded). Email is included when it has recorded spend.
        eligible = [
            c
            for c in channels
            if c["channel"] != "organic" and c["spend"] > 0
        ]

        if len(eligible) < 2:
            return {
                "recommendation_text": (
                    "Only one paid channel has spend right now, so there is no "
                    "reallocation to suggest. Budget allocation is well-balanced "
                    "across what you are running."
                ),
                "shift_from": None,
                "shift_to": None,
                "expected_impact": None,
                "channels": channels,
                "action_available": False,
            }

        # Sort by ROAS descending: highest first, lowest last
        sorted_by_roas = sorted(eligible, key=lambda c: c["roas"], reverse=True)
        best = sorted_by_roas[0]
        worst = sorted_by_roas[-1]

        # If best and worst ROAS are within 10% of each other, call it balanced
        if worst["roas"] <= 0 or best["roas"] <= 0:
            roas_ratio = 0.0
        else:
            roas_ratio = (best["roas"] - worst["roas"]) / worst["roas"]

        if roas_ratio < 0.10:
            return {
                "recommendation_text": (
                    "Budget allocation is well-balanced across channels "
                    f"(ROAS within 10%). Blended ROAS is "
                    f"{attribution['totals']['blended_roas']}x."
                ),
                "shift_from": None,
                "shift_to": None,
                "expected_impact": None,
                "channels": channels,
                "action_available": False,
            }

        # Daily spend for source and destination
        from_daily = round(worst["spend"] / days, 2) if days > 0 else 0.0
        to_daily = round(best["spend"] / days, 2) if days > 0 else 0.0

        # Shift 20% of source's daily spend, capped at $50/day for safety
        shift_amount = round(min(from_daily * 0.20, 50.0), 2)
        if shift_amount <= 0:
            shift_amount = round(from_daily, 2)

        from_recommended = round(max(from_daily - shift_amount, 0.0), 2)
        to_recommended = round(to_daily + shift_amount, 2)

        # Expected impact: at destination channel's current CPA, shift_amount/day
        # over a 7-day window yields shift_amount * 7 / cpa extra conversions
        if best["cpa"] > 0:
            expected_conversions = round((shift_amount * 7) / best["cpa"], 1)
            expected_impact = (
                f"Could gain ~{expected_conversions} more conversions/week at "
                f"current {self._channel_label(best['channel'])} ROAS"
            )
        else:
            expected_impact = (
                f"Shifting to {self._channel_label(best['channel'])} should "
                f"improve blended ROAS"
            )

        # Plain-English recommendation
        roas_multiple = round(best["roas"] / worst["roas"], 1) if worst["roas"] > 0 else 0
        recommendation_text = (
            f"{self._channel_label(best['channel'])} gives "
            f"{roas_multiple}x better return than "
            f"{self._channel_label(worst['channel'])} "
            f"(${best['roas']} vs ${worst['roas']} per $1 spent) -- "
            f"shift ${shift_amount}/day from "
            f"{self._channel_label(worst['channel'])} to "
            f"{self._channel_label(best['channel'])}?"
        )

        return {
            "recommendation_text": recommendation_text,
            "shift_from": {
                "channel": worst["channel"],
                "current_daily": from_daily,
                "recommended_daily": from_recommended,
            },
            "shift_to": {
                "channel": best["channel"],
                "current_daily": to_daily,
                "recommended_daily": to_recommended,
            },
            "expected_impact": expected_impact,
            "channels": channels,
            "action_available": True,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _aggregate_ad_channel(
        self, user_id: str, platform: str, days: int
    ) -> dict[str, Any]:
        """Aggregate spend and conversion data for all campaigns on a platform.

        Args:
            user_id: Owner of the campaigns.
            platform: Ad platform key (``google_ads`` or ``meta_ads``).
            days: Lookback window in days.

        Returns:
            Dict with spend, conversions, revenue (numeric totals).
        """
        campaigns_service = AdCampaignService(self._user_token)
        spend_service = AdSpendTrackingService(self._user_token)

        try:
            campaigns = await campaigns_service.list_ad_campaigns(
                platform=platform, user_id=user_id
            )
        except Exception as exc:
            logger.warning(
                "Failed to list %s campaigns for user=%s: %s", platform, user_id, exc
            )
            return {"spend": 0.0, "conversions": 0, "revenue": 0.0}

        if not campaigns:
            return {"spend": 0.0, "conversions": 0, "revenue": 0.0}

        start_iso = (date.today() - timedelta(days=days)).isoformat()
        end_iso = date.today().isoformat()

        total_spend = 0.0
        total_conversions = 0
        total_revenue = 0.0

        for campaign in campaigns:
            campaign_id = campaign.get("id")
            if not campaign_id:
                continue
            try:
                summary = await spend_service.get_spend_summary(
                    ad_campaign_id=campaign_id,
                    start_date=start_iso,
                    end_date=end_iso,
                    user_id=user_id,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to get spend summary for campaign=%s: %s",
                    campaign_id,
                    exc,
                )
                continue

            total_spend += float(summary.get("total_spend", 0) or 0)
            total_conversions += int(summary.get("total_conversions", 0) or 0)
            total_revenue += float(summary.get("total_conversion_value", 0) or 0)

        return {
            "spend": round(total_spend, 2),
            "conversions": total_conversions,
            "revenue": round(total_revenue, 2),
        }

    async def _get_email_attribution(
        self, user_id: str, days: int
    ) -> dict[str, Any]:
        """Aggregate email campaign metrics from the campaigns table.

        Reads ``campaigns`` rows where ``campaign_type = 'email'`` and sums
        their stored ``metrics`` payloads. Metrics are expected to include
        ``spend``, ``conversions``, and ``revenue`` keys populated by the
        email-sequence sync job; missing keys default to 0.

        Args:
            user_id: Owner of the campaigns.
            days: Lookback window in days (unused here but reserved for future
                date-scoped queries).

        Returns:
            Dict with spend, conversions, revenue numeric totals.
        """
        try:
            client = self.client if self.is_authenticated else None
            if client is None:
                from app.services.base_service import AdminService

                client = AdminService().client

            query = (
                client.table("campaigns")
                .select("id, name, campaign_type, metrics, status")
                .eq("user_id", user_id)
                .eq("campaign_type", "email")
            )
            response = await execute_async(query)
            rows = response.data or []
        except Exception as exc:
            logger.warning(
                "Failed to fetch email campaigns for user=%s: %s", user_id, exc
            )
            return {"spend": 0.0, "conversions": 0, "revenue": 0.0}

        total_spend = 0.0
        total_conversions = 0
        total_revenue = 0.0
        for row in rows:
            metrics = row.get("metrics") or {}
            if not isinstance(metrics, dict):
                continue
            total_spend += float(metrics.get("spend", 0) or 0)
            total_conversions += int(metrics.get("conversions", 0) or 0)
            total_revenue += float(metrics.get("revenue", 0) or 0)

        return {
            "spend": round(total_spend, 2),
            "conversions": total_conversions,
            "revenue": round(total_revenue, 2),
        }

    async def _get_organic_revenue(
        self, user_id: str, days: int, attributed_revenue: float
    ) -> dict[str, Any]:
        """Compute organic/direct revenue by subtracting attributed revenue from Shopify total.

        Args:
            user_id: Owner of the Shopify store (unused -- request context
                handles this inside ``get_shopify_analytics``).
            days: Lookback window -- mapped to a shopify period string if
                possible.
            attributed_revenue: Sum of revenue attributed to paid + email
                channels, subtracted from Shopify total to estimate organic.

        Returns:
            Dict with spend (always 0 for organic), conversions (0 -- untracked),
            revenue (organic total).
        """
        try:
            # Map days to closest supported shopify period
            if days <= 7:
                period = "last_7_days"
            elif days <= 30:
                period = "last_30_days"
            else:
                period = "last_3_months"
            analytics = await get_shopify_analytics(period=period)
        except Exception as exc:
            logger.warning(
                "Failed to fetch shopify analytics for user=%s: %s", user_id, exc
            )
            return {"spend": 0.0, "conversions": 0, "revenue": 0.0}

        if not isinstance(analytics, dict) or "error" in analytics:
            return {"spend": 0.0, "conversions": 0, "revenue": 0.0}

        total_shopify_revenue = float(analytics.get("revenue_total", 0) or 0)
        organic_revenue = max(total_shopify_revenue - attributed_revenue, 0.0)

        return {
            "spend": 0.0,
            "conversions": 0,
            "revenue": round(organic_revenue, 2),
        }

    @staticmethod
    def _build_channel_dict(channel: str, data: dict[str, Any]) -> dict[str, Any]:
        """Build a normalized channel row with ROAS and CPA derived."""
        spend = float(data.get("spend", 0) or 0)
        conversions = int(data.get("conversions", 0) or 0)
        revenue = float(data.get("revenue", 0) or 0)
        roas = round(revenue / spend, 2) if spend > 0 else 0.0
        cpa = round(spend / conversions, 2) if conversions > 0 else 0.0
        return {
            "channel": channel,
            "spend": round(spend, 2),
            "conversions": conversions,
            "revenue": round(revenue, 2),
            "roas": roas,
            "cpa": cpa,
            "share_of_revenue_pct": 0.0,  # filled in by caller
        }

    @staticmethod
    def _channel_label(channel: str) -> str:
        """Human-readable label for a channel key."""
        return {
            "google_ads": "Google Ads",
            "meta_ads": "Meta Ads",
            "email": "Email",
            "organic": "Organic",
        }.get(channel, channel.replace("_", " ").title())

    def _build_summary_text(self, channels: list[dict[str, Any]]) -> str:
        """Build a plain-English summary of channel performance.

        Args:
            channels: List of channel dicts with roas and cpa.

        Returns:
            Plain-English sentence identifying the best paid channel, or a
            neutral note if no paid channel has spend.
        """
        paid = [c for c in channels if c["channel"] != "organic" and c["spend"] > 0]
        if not paid:
            return "No paid channel spend in the selected window."
        best = max(paid, key=lambda c: c["roas"])
        parts = [
            f"{self._channel_label(best['channel'])} is your best performer at "
            f"{best['roas']}x ROAS (${best['cpa']}/customer)."
        ]
        others = [c for c in paid if c["channel"] != best["channel"]]
        for other in others:
            parts.append(
                f"{self._channel_label(other['channel'])} returns "
                f"{other['roas']}x (${other['cpa']}/customer)."
            )
        return " ".join(parts)


__all__ = ["CrossChannelAttributionService"]
