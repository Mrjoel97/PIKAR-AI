# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""CampaignPerformanceSummarizer - plain-English ad performance reports.

Aggregates spend, conversions, CPA, and week-over-week trends across both
Google Ads and Meta Ads into a single human-readable summary. Used by
the Marketing Agent's summarize_campaign_performance tool so the agent
can explain performance the way a marketing consultant would:

    "Your Google Ads spent $340 this week and brought 12 customers at
     $28.33 each -- 15% better than last week."

Reads from AdCampaignService and AdSpendTrackingService; does not hit any
ad platform API directly (relies on local ad_spend_tracking rows that
AdPerformanceSyncService keeps up-to-date).
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from app.services.ad_management_service import (
    AdCampaignService,
    AdSpendTrackingService,
)

logger = logging.getLogger(__name__)


# Friendly display names for ad platforms in summary text.
_PLATFORM_LABELS: dict[str, str] = {
    "google_ads": "Google Ads",
    "meta_ads": "Meta Ads",
}


class CampaignPerformanceSummarizer:
    """Build plain-English performance summaries across all ad platforms."""

    async def summarize_all_platforms(
        self, user_id: str, days: int = 7
    ) -> dict[str, Any]:
        """Summarize ad performance for a user across every active platform.

        Args:
            user_id: The user whose campaigns should be summarized.
            days: Size of the reporting window in days (default 7 = this week).

        Returns:
            Dict with keys:
              - summary_text: plain-English paragraph
              - total_spend: float (sum across all campaigns)
              - total_conversions: int
              - overall_cpa: float (0 when no conversions)
              - wow_spend_change_pct: float | None
              - wow_conversions_change_pct: float | None
              - per_campaign: list of campaign-level breakdown dicts
              - period: {"start": str, "end": str, "days": int}
              - prior_period: {"start": str, "end": str, "days": int}
        """
        campaign_svc = AdCampaignService()
        campaigns = await campaign_svc.list_ad_campaigns(user_id=user_id)

        today = date.today()
        current_end = today
        current_start = today - timedelta(days=days - 1) if days > 0 else today
        prior_end = current_start - timedelta(days=1)
        prior_start = prior_end - timedelta(days=days - 1) if days > 0 else prior_end

        period = {
            "start": current_start.isoformat(),
            "end": current_end.isoformat(),
            "days": days,
        }
        prior_period = {
            "start": prior_start.isoformat(),
            "end": prior_end.isoformat(),
            "days": days,
        }

        if not campaigns:
            return {
                "summary_text": (
                    "No active ad campaigns found. "
                    "Create a Google Ads or Meta Ads campaign to start "
                    "getting performance reports."
                ),
                "total_spend": 0.0,
                "total_conversions": 0,
                "overall_cpa": 0.0,
                "wow_spend_change_pct": None,
                "wow_conversions_change_pct": None,
                "per_campaign": [],
                "period": period,
                "prior_period": prior_period,
            }

        spend_svc = AdSpendTrackingService()

        # Per-platform accumulators for summary text.
        platform_totals: dict[str, dict[str, float]] = {}
        per_campaign: list[dict[str, Any]] = []

        for camp in campaigns:
            camp_id = camp.get("id")
            if not camp_id:
                continue
            platform = camp.get("platform", "unknown")
            name = camp.get("name", "Unnamed campaign")

            try:
                current = await spend_svc.get_spend_summary(
                    ad_campaign_id=camp_id,
                    start_date=period["start"],
                    end_date=period["end"],
                    user_id=user_id,
                )
                prior = await spend_svc.get_spend_summary(
                    ad_campaign_id=camp_id,
                    start_date=prior_period["start"],
                    end_date=prior_period["end"],
                    user_id=user_id,
                )
            except Exception:
                logger.exception("Spend summary lookup failed for campaign %s", camp_id)
                continue

            cur_spend = float(current.get("total_spend") or 0)
            cur_conv = int(current.get("total_conversions") or 0)
            prior_spend = float(prior.get("total_spend") or 0)
            prior_conv = int(prior.get("total_conversions") or 0)
            cpa = round(cur_spend / cur_conv, 2) if cur_conv else 0.0

            per_campaign.append(
                {
                    "id": camp_id,
                    "name": name,
                    "platform": platform,
                    "spend": round(cur_spend, 2),
                    "conversions": cur_conv,
                    "cpa": cpa,
                    "prior_spend": round(prior_spend, 2),
                    "prior_conversions": prior_conv,
                    "wow_conversions_change_pct": self._compute_wow(
                        cur_conv, prior_conv
                    ),
                    "wow_spend_change_pct": self._compute_wow(cur_spend, prior_spend),
                }
            )

            acc = platform_totals.setdefault(
                platform,
                {
                    "spend": 0.0,
                    "conversions": 0,
                    "prior_spend": 0.0,
                    "prior_conversions": 0,
                },
            )
            acc["spend"] += cur_spend
            acc["conversions"] += cur_conv
            acc["prior_spend"] += prior_spend
            acc["prior_conversions"] += prior_conv

        total_spend = sum(acc["spend"] for acc in platform_totals.values())
        total_conversions = int(
            sum(acc["conversions"] for acc in platform_totals.values())
        )
        total_prior_spend = sum(acc["prior_spend"] for acc in platform_totals.values())
        total_prior_conversions = sum(
            acc["prior_conversions"] for acc in platform_totals.values()
        )
        overall_cpa = (
            round(total_spend / total_conversions, 2) if total_conversions else 0.0
        )
        wow_spend_change_pct = self._compute_wow(total_spend, total_prior_spend)
        wow_conversions_change_pct = self._compute_wow(
            total_conversions, total_prior_conversions
        )

        totals = {
            "total_spend": round(total_spend, 2),
            "total_conversions": total_conversions,
            "overall_cpa": overall_cpa,
        }
        wow = {
            "wow_spend_change_pct": wow_spend_change_pct,
            "wow_conversions_change_pct": wow_conversions_change_pct,
        }

        summary_text = self._format_summary_text(platform_totals, totals, wow)

        return {
            "summary_text": summary_text,
            "total_spend": round(total_spend, 2),
            "total_conversions": total_conversions,
            "overall_cpa": overall_cpa,
            "wow_spend_change_pct": wow_spend_change_pct,
            "wow_conversions_change_pct": wow_conversions_change_pct,
            "per_campaign": per_campaign,
            "period": period,
            "prior_period": prior_period,
        }

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    def _compute_wow(
        self,
        current: float | int,
        prior: float | int,
    ) -> float | None:
        """Return percentage change from prior to current, or None if undefined.

        Rules:
        - If both values are zero, returns None (no activity either period).
        - If prior is zero but current is non-zero, returns None -- we cannot
          compute a meaningful percentage without a baseline, so callers render
          "new this week" instead.
        - Otherwise returns ((current - prior) / prior) * 100, rounded to
          one decimal place.
        """
        if not prior:
            return None
        if current == 0 and prior == 0:
            return None
        pct = ((float(current) - float(prior)) / float(prior)) * 100.0
        return round(pct, 1)

    def _format_summary_text(
        self,
        platform_totals: dict[str, dict[str, float]],
        totals: dict[str, Any],
        wow: dict[str, float | None],
    ) -> str:
        """Build the plain-English paragraph users see in the chat response.

        Example output:
            "Your Google Ads spent $340.00 this week and brought 12 customers
             at $28.33 each -- 20% better than last week (conversions).
             Meta Ads spent $200.00 and brought 8 customers at $25.00 each --
             new this week."
        """
        if not platform_totals:
            return (
                "No active ad campaigns found. "
                "Create a Google Ads or Meta Ads campaign to start "
                "getting performance reports."
            )

        parts: list[str] = []

        # Deterministic order: Google Ads first, then Meta Ads, then anything else.
        ordered_platforms = sorted(
            platform_totals.keys(),
            key=lambda p: (
                0 if p == "google_ads" else 1 if p == "meta_ads" else 2,
                p,
            ),
        )

        is_first = True
        for platform in ordered_platforms:
            acc = platform_totals[platform]
            label = _PLATFORM_LABELS.get(platform, platform.replace("_", " ").title())
            spend = acc["spend"]
            conversions = int(acc["conversions"])
            prior_conv = int(acc["prior_conversions"])
            cpa = spend / conversions if conversions else 0.0

            prefix = "Your " if is_first else ""
            is_first = False

            if conversions == 0:
                # Spent money but no tracked conversions yet.
                sentence = (
                    f"{prefix}{label} spent ${spend:,.2f} this week "
                    f"but no conversions tracked yet."
                )
            else:
                wow_conv_pct = self._compute_wow(conversions, prior_conv)
                if wow_conv_pct is None:
                    trend = "new this week"
                elif wow_conv_pct > 0:
                    trend = f"{abs(wow_conv_pct):.0f}% better than last week"
                elif wow_conv_pct < 0:
                    trend = f"{abs(wow_conv_pct):.0f}% worse than last week"
                else:
                    trend = "flat vs. last week"

                sentence = (
                    f"{prefix}{label} spent ${spend:,.2f} this week and "
                    f"brought {conversions} customers at ${cpa:,.2f} each "
                    f"-- {trend}."
                )
            parts.append(sentence)

        summary = " ".join(parts)

        # Append overall roll-up when more than one platform is active.
        if len(platform_totals) > 1 and totals["total_conversions"]:
            overall_trend = ""
            wow_conv = wow.get("wow_conversions_change_pct")
            if wow_conv is not None:
                direction = "better" if wow_conv >= 0 else "worse"
                overall_trend = (
                    f" Overall, that's {abs(wow_conv):.0f}% {direction} than "
                    f"last week across all platforms."
                )
            summary += (
                f" Combined: ${totals['total_spend']:,.2f} spent, "
                f"{totals['total_conversions']} customers, "
                f"${totals['overall_cpa']:,.2f} cost per customer."
                f"{overall_trend}"
            )

        return summary
