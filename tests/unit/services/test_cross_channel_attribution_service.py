# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for CrossChannelAttributionService.

Covers unified cross-channel attribution aggregation (Google Ads, Meta Ads,
email, organic) and ROAS-based budget reallocation recommendations.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest

# Ensure BaseService can initialize without real Supabase credentials
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")

USER_ID = "test-user-00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_google_spend() -> dict:
    """AdSpendTrackingService.get_spend_summary return value for Google Ads."""
    return {
        "total_spend": 1200.0,
        "total_impressions": 30000,
        "total_clicks": 900,
        "total_conversions": 40,
        "total_conversion_value": 3600.0,
        "avg_ctr": 0.03,
        "avg_cpc": 1.33,
        "avg_cpa": 30.0,
        "overall_roas": 3.0,
        "days_tracked": 30,
        "daily_breakdown": [],
    }


def _make_meta_spend() -> dict:
    """AdSpendTrackingService.get_spend_summary return value for Meta Ads."""
    return {
        "total_spend": 800.0,
        "total_impressions": 40000,
        "total_clicks": 1200,
        "total_conversions": 50,
        "total_conversion_value": 4000.0,
        "avg_ctr": 0.03,
        "avg_cpc": 0.67,
        "avg_cpa": 16.0,
        "overall_roas": 5.0,
        "days_tracked": 30,
        "daily_breakdown": [],
    }


def _make_zero_spend() -> dict:
    """Empty spend summary for a platform with no activity."""
    return {
        "total_spend": 0,
        "total_impressions": 0,
        "total_clicks": 0,
        "total_conversions": 0,
        "total_conversion_value": 0,
        "avg_ctr": 0,
        "avg_cpc": 0,
        "avg_cpa": 0,
        "overall_roas": 0,
        "days_tracked": 0,
        "daily_breakdown": [],
    }


def _patch_channel_sources(
    google_spend: dict | None = None,
    meta_spend: dict | None = None,
    google_campaigns: list | None = None,
    meta_campaigns: list | None = None,
    email_revenue: float = 800.0,
    email_spend: float = 200.0,
    email_conversions: int = 20,
    shopify_total_revenue: float = 10000.0,
):
    """Build patch context managers for all data sources used by the service.

    Default channel ROAS layout (so tests reason about a clear winner/loser):
      - Google Ads: ROAS 3.0 (worst paid channel)
      - Email:      ROAS 4.0 (middle)
      - Meta Ads:   ROAS 5.0 (best paid channel)

    Returns a tuple of context managers plus the side-effect fns that
    MockCampaign.list_ad_campaigns and MockSpend.get_spend_summary should use.
    """
    google_spend = google_spend if google_spend is not None else _make_google_spend()
    meta_spend = meta_spend if meta_spend is not None else _make_meta_spend()

    google_campaigns_list = (
        google_campaigns
        if google_campaigns is not None
        else [{"id": "g-1"}, {"id": "g-2"}]
    )
    meta_campaigns_list = (
        meta_campaigns
        if meta_campaigns is not None
        else [{"id": "m-1"}]
    )

    async def _list_campaigns(platform=None, user_id=None, **kwargs):
        if platform == "google_ads":
            return google_campaigns_list
        if platform == "meta_ads":
            return meta_campaigns_list
        return []

    # Spend summaries respond based on campaign id
    async def _get_spend_summary(ad_campaign_id, **kwargs):
        if ad_campaign_id.startswith("g"):
            # Return half spend per google campaign so total matches fixture
            half = dict(google_spend)
            for key in (
                "total_spend",
                "total_impressions",
                "total_clicks",
                "total_conversions",
                "total_conversion_value",
            ):
                half[key] = half[key] / len(google_campaigns_list)
            return half
        if ad_campaign_id.startswith("m"):
            half = dict(meta_spend)
            for key in (
                "total_spend",
                "total_impressions",
                "total_clicks",
                "total_conversions",
                "total_conversion_value",
            ):
                half[key] = half[key] / len(meta_campaigns_list)
            return half
        return _make_zero_spend()

    # Email attribution: simulate campaigns table query and Shopify orders with UTM
    email_attribution = {
        "spend": email_spend,
        "revenue": email_revenue,
        "conversions": email_conversions,
    }

    # Organic: Shopify analytics total
    shopify_analytics = {
        "revenue_total": shopify_total_revenue,
        "order_count": 100,
        "average_order_value": 100.0,
    }

    ad_campaign_patch = patch(
        "app.services.cross_channel_attribution_service.AdCampaignService"
    )
    ad_spend_patch = patch(
        "app.services.cross_channel_attribution_service.AdSpendTrackingService"
    )
    email_patch = patch(
        "app.services.cross_channel_attribution_service.CrossChannelAttributionService._get_email_attribution",
        new=AsyncMock(return_value=email_attribution),
    )
    shopify_patch = patch(
        "app.services.cross_channel_attribution_service.get_shopify_analytics",
        new=AsyncMock(return_value=shopify_analytics),
    )

    return (
        ad_campaign_patch,
        ad_spend_patch,
        email_patch,
        shopify_patch,
        _list_campaigns,
        _get_spend_summary,
    )


# ---------------------------------------------------------------------------
# get_attribution tests
# ---------------------------------------------------------------------------


class TestGetAttribution:
    """get_attribution returns unified per-channel breakdown."""

    @pytest.mark.asyncio
    async def test_returns_per_channel_breakdown(self):
        """Returns channels with spend, conversions, revenue, ROAS, cpa, share_of_revenue_pct."""
        (
            ad_campaign_patch,
            ad_spend_patch,
            email_patch,
            shopify_patch,
            list_campaigns_fn,
            get_spend_fn,
        ) = _patch_channel_sources()

        with ad_campaign_patch as MockCampaign, ad_spend_patch as MockSpend, email_patch, shopify_patch:
            MockCampaign.return_value.list_ad_campaigns = AsyncMock(
                side_effect=list_campaigns_fn
            )
            MockSpend.return_value.get_spend_summary = AsyncMock(
                side_effect=get_spend_fn
            )

            from app.services.cross_channel_attribution_service import (
                CrossChannelAttributionService,
            )

            svc = CrossChannelAttributionService()
            result = await svc.get_attribution(USER_ID, days=30)

        assert "channels" in result
        assert "totals" in result
        assert "period" in result
        assert "summary_text" in result
        assert isinstance(result["channels"], list)
        assert len(result["channels"]) >= 2

        # Every channel must have required fields
        for ch in result["channels"]:
            assert "channel" in ch
            assert "spend" in ch
            assert "conversions" in ch
            assert "revenue" in ch
            assert "roas" in ch
            assert "cpa" in ch
            assert "share_of_revenue_pct" in ch

    @pytest.mark.asyncio
    async def test_includes_all_four_channels(self):
        """Channels include google_ads, meta_ads, email, and organic."""
        (
            ad_campaign_patch,
            ad_spend_patch,
            email_patch,
            shopify_patch,
            list_campaigns_fn,
            get_spend_fn,
        ) = _patch_channel_sources()

        with ad_campaign_patch as MockCampaign, ad_spend_patch as MockSpend, email_patch, shopify_patch:
            MockCampaign.return_value.list_ad_campaigns = AsyncMock(
                side_effect=list_campaigns_fn
            )
            MockSpend.return_value.get_spend_summary = AsyncMock(
                side_effect=get_spend_fn
            )

            from app.services.cross_channel_attribution_service import (
                CrossChannelAttributionService,
            )

            svc = CrossChannelAttributionService()
            result = await svc.get_attribution(USER_ID, days=30)

        channel_names = {c["channel"] for c in result["channels"]}
        assert "google_ads" in channel_names
        assert "meta_ads" in channel_names
        assert "email" in channel_names
        assert "organic" in channel_names

    @pytest.mark.asyncio
    async def test_google_ads_aggregation_correct(self):
        """google_ads channel sums all google campaigns: $1200 spend, 40 conv, $3600 rev, ROAS 3.0."""
        (
            ad_campaign_patch,
            ad_spend_patch,
            email_patch,
            shopify_patch,
            list_campaigns_fn,
            get_spend_fn,
        ) = _patch_channel_sources()

        with ad_campaign_patch as MockCampaign, ad_spend_patch as MockSpend, email_patch, shopify_patch:
            MockCampaign.return_value.list_ad_campaigns = AsyncMock(
                side_effect=list_campaigns_fn
            )
            MockSpend.return_value.get_spend_summary = AsyncMock(
                side_effect=get_spend_fn
            )

            from app.services.cross_channel_attribution_service import (
                CrossChannelAttributionService,
            )

            svc = CrossChannelAttributionService()
            result = await svc.get_attribution(USER_ID, days=30)

        google = next(c for c in result["channels"] if c["channel"] == "google_ads")
        assert google["spend"] == pytest.approx(1200.0, rel=0.01)
        assert google["conversions"] == 40
        assert google["revenue"] == pytest.approx(3600.0, rel=0.01)
        assert google["roas"] == pytest.approx(3.0, rel=0.01)
        assert google["cpa"] == pytest.approx(30.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_share_of_revenue_percentages_sum_to_100(self):
        """share_of_revenue_pct across all channels should sum to ~100%."""
        (
            ad_campaign_patch,
            ad_spend_patch,
            email_patch,
            shopify_patch,
            list_campaigns_fn,
            get_spend_fn,
        ) = _patch_channel_sources()

        with ad_campaign_patch as MockCampaign, ad_spend_patch as MockSpend, email_patch, shopify_patch:
            MockCampaign.return_value.list_ad_campaigns = AsyncMock(
                side_effect=list_campaigns_fn
            )
            MockSpend.return_value.get_spend_summary = AsyncMock(
                side_effect=get_spend_fn
            )

            from app.services.cross_channel_attribution_service import (
                CrossChannelAttributionService,
            )

            svc = CrossChannelAttributionService()
            result = await svc.get_attribution(USER_ID, days=30)

        total_share = sum(c["share_of_revenue_pct"] for c in result["channels"])
        # Allow small rounding tolerance
        assert 99.0 <= total_share <= 101.0


# ---------------------------------------------------------------------------
# get_budget_recommendation tests
# ---------------------------------------------------------------------------


class TestGetBudgetRecommendation:
    """get_budget_recommendation returns ROAS-based reallocation."""

    @pytest.mark.asyncio
    async def test_recommends_shift_from_lowest_to_highest_roas(self):
        """Meta ROAS 5.0 > Google ROAS 3.0 -> shift from google_ads to meta_ads."""
        (
            ad_campaign_patch,
            ad_spend_patch,
            email_patch,
            shopify_patch,
            list_campaigns_fn,
            get_spend_fn,
        ) = _patch_channel_sources()

        with ad_campaign_patch as MockCampaign, ad_spend_patch as MockSpend, email_patch, shopify_patch:
            MockCampaign.return_value.list_ad_campaigns = AsyncMock(
                side_effect=list_campaigns_fn
            )
            MockSpend.return_value.get_spend_summary = AsyncMock(
                side_effect=get_spend_fn
            )

            from app.services.cross_channel_attribution_service import (
                CrossChannelAttributionService,
            )

            svc = CrossChannelAttributionService()
            result = await svc.get_budget_recommendation(USER_ID, days=30)

        assert result["action_available"] is True
        assert result["shift_from"]["channel"] == "google_ads"
        assert result["shift_to"]["channel"] == "meta_ads"
        # Recommended daily should be lower than current for source, higher for destination
        assert (
            result["shift_from"]["recommended_daily"]
            < result["shift_from"]["current_daily"]
        )
        assert (
            result["shift_to"]["recommended_daily"]
            > result["shift_to"]["current_daily"]
        )

    @pytest.mark.asyncio
    async def test_recommendation_includes_plain_english_text(self):
        """recommendation_text mentions channel names, ROAS comparison, and dollar shift."""
        (
            ad_campaign_patch,
            ad_spend_patch,
            email_patch,
            shopify_patch,
            list_campaigns_fn,
            get_spend_fn,
        ) = _patch_channel_sources()

        with ad_campaign_patch as MockCampaign, ad_spend_patch as MockSpend, email_patch, shopify_patch:
            MockCampaign.return_value.list_ad_campaigns = AsyncMock(
                side_effect=list_campaigns_fn
            )
            MockSpend.return_value.get_spend_summary = AsyncMock(
                side_effect=get_spend_fn
            )

            from app.services.cross_channel_attribution_service import (
                CrossChannelAttributionService,
            )

            svc = CrossChannelAttributionService()
            result = await svc.get_budget_recommendation(USER_ID, days=30)

        text = result["recommendation_text"]
        assert isinstance(text, str)
        assert len(text) > 10
        # Should mention at least one channel name readably
        lower = text.lower()
        assert "meta" in lower or "google" in lower
        # Should reference dollars or shift
        assert "$" in text or "shift" in lower or "return" in lower

    @pytest.mark.asyncio
    async def test_single_channel_no_reallocation_possible(self):
        """When only one channel has spend, no reallocation is suggested."""
        (
            ad_campaign_patch,
            ad_spend_patch,
            email_patch,
            shopify_patch,
            list_campaigns_fn,
            get_spend_fn,
        ) = _patch_channel_sources(
            meta_spend=_make_zero_spend(),
            meta_campaigns=[],
            email_spend=0.0,
            email_revenue=0.0,
            email_conversions=0,
        )

        with ad_campaign_patch as MockCampaign, ad_spend_patch as MockSpend, email_patch, shopify_patch:
            MockCampaign.return_value.list_ad_campaigns = AsyncMock(
                side_effect=list_campaigns_fn
            )
            MockSpend.return_value.get_spend_summary = AsyncMock(
                side_effect=get_spend_fn
            )

            from app.services.cross_channel_attribution_service import (
                CrossChannelAttributionService,
            )

            svc = CrossChannelAttributionService()
            result = await svc.get_budget_recommendation(USER_ID, days=30)

        assert result["action_available"] is False
        assert "balanced" in result["recommendation_text"].lower() or (
            "only one channel" in result["recommendation_text"].lower()
            or "single" in result["recommendation_text"].lower()
        )

    @pytest.mark.asyncio
    async def test_zero_spend_channels_excluded_from_reallocation_source(self):
        """Channels with zero spend are not used as the 'shift from' source."""
        # Meta has zero spend, google has spend, email has spend -> shift should NOT be from meta
        (
            ad_campaign_patch,
            ad_spend_patch,
            email_patch,
            shopify_patch,
            list_campaigns_fn,
            get_spend_fn,
        ) = _patch_channel_sources(
            meta_spend=_make_zero_spend(),
            meta_campaigns=[],
        )

        with ad_campaign_patch as MockCampaign, ad_spend_patch as MockSpend, email_patch, shopify_patch:
            MockCampaign.return_value.list_ad_campaigns = AsyncMock(
                side_effect=list_campaigns_fn
            )
            MockSpend.return_value.get_spend_summary = AsyncMock(
                side_effect=get_spend_fn
            )

            from app.services.cross_channel_attribution_service import (
                CrossChannelAttributionService,
            )

            svc = CrossChannelAttributionService()
            result = await svc.get_budget_recommendation(USER_ID, days=30)

        if result["action_available"]:
            assert result["shift_from"]["channel"] != "meta_ads"

    @pytest.mark.asyncio
    async def test_balanced_roas_returns_no_reallocation(self):
        """When all channels have ROAS within 10%, recommendation is 'balanced'."""
        # Both platforms at the same ROAS
        google_similar = _make_google_spend()
        google_similar["overall_roas"] = 5.0
        google_similar["total_conversion_value"] = 6000.0  # 1200 * 5.0

        (
            ad_campaign_patch,
            ad_spend_patch,
            email_patch,
            shopify_patch,
            list_campaigns_fn,
            get_spend_fn,
        ) = _patch_channel_sources(
            google_spend=google_similar,
            # make email ROAS also ~5x so nothing has a meaningful edge
            email_spend=100.0,
            email_revenue=500.0,
            email_conversions=5,
            shopify_total_revenue=200.0,  # tiny organic so we don't dominate
        )

        with ad_campaign_patch as MockCampaign, ad_spend_patch as MockSpend, email_patch, shopify_patch:
            MockCampaign.return_value.list_ad_campaigns = AsyncMock(
                side_effect=list_campaigns_fn
            )
            MockSpend.return_value.get_spend_summary = AsyncMock(
                side_effect=get_spend_fn
            )

            from app.services.cross_channel_attribution_service import (
                CrossChannelAttributionService,
            )

            svc = CrossChannelAttributionService()
            result = await svc.get_budget_recommendation(USER_ID, days=30)

        assert result["action_available"] is False
        assert "balanced" in result["recommendation_text"].lower()
