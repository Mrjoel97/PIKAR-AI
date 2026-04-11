# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for CampaignPerformanceSummarizer.

Tests cover:
- Plain-English summary generation with CPA and WoW trends
- Multi-platform and single-platform cases
- Zero-conversion and no-campaign edge cases
- Per-campaign breakdown formatting
- Numeric accuracy of WoW percentage calculations
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch):
    """Set required env vars for BaseService init."""
    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")


@pytest.fixture()
def summarizer():
    """Return a CampaignPerformanceSummarizer instance."""
    from app.services.campaign_performance_summarizer import (
        CampaignPerformanceSummarizer,
    )

    return CampaignPerformanceSummarizer()


def _make_spend_summary(
    total_spend: float,
    total_conversions: int,
    total_impressions: int = 1000,
    total_clicks: int = 100,
    total_conversion_value: float = 0.0,
) -> dict:
    """Build a synthetic spend_summary matching AdSpendTrackingService output."""
    return {
        "total_spend": round(total_spend, 2),
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "total_conversions": total_conversions,
        "total_conversion_value": round(total_conversion_value, 2),
        "avg_ctr": round(total_clicks / total_impressions, 4)
        if total_impressions
        else 0,
        "avg_cpc": round(total_spend / total_clicks, 2) if total_clicks else 0,
        "avg_cpa": round(total_spend / total_conversions, 2)
        if total_conversions
        else 0,
        "overall_roas": round(total_conversion_value / total_spend, 2)
        if total_spend
        else 0,
        "days_tracked": 7,
        "daily_breakdown": [],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMultiPlatformSummary:
    """Summaries for users with both Google Ads and Meta Ads active."""

    @pytest.mark.asyncio()
    async def test_plain_english_includes_dollars_customers_and_cpa(
        self, summarizer
    ):
        """summary_text mentions spend, customer count, and CPA for each platform."""
        campaigns = [
            {
                "id": "camp-google-1",
                "name": "Search - Brand Terms",
                "platform": "google_ads",
                "status": "active",
            },
            {
                "id": "camp-meta-1",
                "name": "Feed - Lookalike",
                "platform": "meta_ads",
                "status": "active",
            },
        ]

        # Current period: Google $340 -> 12 conv, Meta $200 -> 8 conv
        # Prior period: Google $296 -> 10 conv, Meta (no data -> empty)
        current_by_id = {
            "camp-google-1": _make_spend_summary(340.0, 12),
            "camp-meta-1": _make_spend_summary(200.0, 8),
        }
        prior_by_id = {
            "camp-google-1": _make_spend_summary(296.0, 10),
            "camp-meta-1": _make_spend_summary(0.0, 0, total_impressions=0, total_clicks=0),
        }

        async def mock_list(user_id=None):
            return campaigns

        async def mock_spend(
            ad_campaign_id, start_date=None, end_date=None, user_id=None
        ):
            # Heuristic: earlier start_date = prior period
            from datetime import date

            # prior period will have smaller start_date
            today = date.today().isoformat()
            if start_date and start_date < (date.today().replace(day=1).isoformat()):
                # Fallback -- use end_date to detect prior vs current
                pass
            # use end_date to decide: prior period end date < today
            if end_date and end_date < today:
                return prior_by_id[ad_campaign_id]
            return current_by_id[ad_campaign_id]

        with (
            patch(
                "app.services.campaign_performance_summarizer.AdCampaignService"
            ) as mock_camp_cls,
            patch(
                "app.services.campaign_performance_summarizer.AdSpendTrackingService"
            ) as mock_spend_cls,
        ):
            mock_camp_cls.return_value.list_ad_campaigns = AsyncMock(
                side_effect=mock_list
            )
            mock_spend_cls.return_value.get_spend_summary = AsyncMock(
                side_effect=mock_spend
            )

            result = await summarizer.summarize_all_platforms(
                user_id="user-123", days=7
            )

        assert "summary_text" in result
        text = result["summary_text"]
        assert "Google Ads" in text
        assert "Meta Ads" in text
        # Dollar amounts
        assert "$340" in text
        assert "$200" in text
        # Customer counts
        assert "12 customer" in text or "12 conversion" in text
        assert "8 customer" in text or "8 conversion" in text
        # CPA (Google: 340/12 = 28.33, Meta: 200/8 = 25.00)
        assert "$28.33" in text
        assert "$25" in text

    @pytest.mark.asyncio()
    async def test_wow_trend_shows_percentage_change(self, summarizer):
        """When prior week data exists, summary shows WoW percent change."""
        campaigns = [
            {
                "id": "camp-1",
                "name": "Brand Search",
                "platform": "google_ads",
                "status": "active",
            },
        ]
        # Current: $340 / 12 conv. Prior: $200 / 10 conv.
        # spend WoW: (340-200)/200 = 70% better (more spend)
        # conversions WoW: (12-10)/10 = 20% better
        current = _make_spend_summary(340.0, 12)
        prior = _make_spend_summary(200.0, 10)

        async def mock_list(user_id=None):
            return campaigns

        async def mock_spend(
            ad_campaign_id, start_date=None, end_date=None, user_id=None
        ):
            from datetime import date

            today = date.today().isoformat()
            if end_date and end_date < today:
                return prior
            return current

        with (
            patch(
                "app.services.campaign_performance_summarizer.AdCampaignService"
            ) as mock_camp_cls,
            patch(
                "app.services.campaign_performance_summarizer.AdSpendTrackingService"
            ) as mock_spend_cls,
        ):
            mock_camp_cls.return_value.list_ad_campaigns = AsyncMock(
                side_effect=mock_list
            )
            mock_spend_cls.return_value.get_spend_summary = AsyncMock(
                side_effect=mock_spend
            )

            result = await summarizer.summarize_all_platforms(
                user_id="user-123", days=7
            )

        # Conversions WoW should be "20% better" -- that's the marketing-meaningful number
        text = result["summary_text"]
        assert "%" in text
        assert "better" in text.lower() or "more" in text.lower()
        # Numeric verification
        assert result["wow_conversions_change_pct"] == pytest.approx(20.0, abs=0.01)
        assert result["wow_spend_change_pct"] == pytest.approx(70.0, abs=0.01)


class TestSinglePlatformSummary:
    """Summary handles the case where only one platform has active campaigns."""

    @pytest.mark.asyncio()
    async def test_google_only_no_meta(self, summarizer):
        """Only Google Ads campaigns -> summary should not mention Meta Ads."""
        campaigns = [
            {
                "id": "camp-1",
                "name": "Brand Search",
                "platform": "google_ads",
                "status": "active",
            },
        ]
        current = _make_spend_summary(150.0, 5)
        prior = _make_spend_summary(120.0, 4)

        async def mock_list(user_id=None):
            return campaigns

        async def mock_spend(
            ad_campaign_id, start_date=None, end_date=None, user_id=None
        ):
            from datetime import date

            today = date.today().isoformat()
            if end_date and end_date < today:
                return prior
            return current

        with (
            patch(
                "app.services.campaign_performance_summarizer.AdCampaignService"
            ) as mock_camp_cls,
            patch(
                "app.services.campaign_performance_summarizer.AdSpendTrackingService"
            ) as mock_spend_cls,
        ):
            mock_camp_cls.return_value.list_ad_campaigns = AsyncMock(
                side_effect=mock_list
            )
            mock_spend_cls.return_value.get_spend_summary = AsyncMock(
                side_effect=mock_spend
            )

            result = await summarizer.summarize_all_platforms(
                user_id="user-123", days=7
            )

        text = result["summary_text"]
        assert "Google Ads" in text
        assert "Meta Ads" not in text
        assert result["total_spend"] == pytest.approx(150.0)
        assert result["total_conversions"] == 5


class TestEmptyAndEdgeCases:
    """Edge cases: no campaigns, zero conversions, no prior data."""

    @pytest.mark.asyncio()
    async def test_no_campaigns_returns_no_active_message(self, summarizer):
        """When user has no campaigns, summary_text explains that."""

        async def mock_list(user_id=None):
            return []

        with patch(
            "app.services.campaign_performance_summarizer.AdCampaignService"
        ) as mock_camp_cls:
            mock_camp_cls.return_value.list_ad_campaigns = AsyncMock(
                side_effect=mock_list
            )

            result = await summarizer.summarize_all_platforms(
                user_id="user-123", days=7
            )

        assert "no active" in result["summary_text"].lower() or (
            "no ad campaigns" in result["summary_text"].lower()
        )
        assert result["total_spend"] == 0
        assert result["total_conversions"] == 0
        assert result["per_campaign"] == []

    @pytest.mark.asyncio()
    async def test_zero_conversions_phrasing(self, summarizer):
        """Campaign with spend but zero conversions gets special phrasing."""
        campaigns = [
            {
                "id": "camp-1",
                "name": "Display - Test",
                "platform": "google_ads",
                "status": "active",
            },
        ]
        current = _make_spend_summary(80.0, 0)
        prior = _make_spend_summary(0.0, 0, total_impressions=0, total_clicks=0)

        async def mock_list(user_id=None):
            return campaigns

        async def mock_spend(
            ad_campaign_id, start_date=None, end_date=None, user_id=None
        ):
            from datetime import date

            today = date.today().isoformat()
            if end_date and end_date < today:
                return prior
            return current

        with (
            patch(
                "app.services.campaign_performance_summarizer.AdCampaignService"
            ) as mock_camp_cls,
            patch(
                "app.services.campaign_performance_summarizer.AdSpendTrackingService"
            ) as mock_spend_cls,
        ):
            mock_camp_cls.return_value.list_ad_campaigns = AsyncMock(
                side_effect=mock_list
            )
            mock_spend_cls.return_value.get_spend_summary = AsyncMock(
                side_effect=mock_spend
            )

            result = await summarizer.summarize_all_platforms(
                user_id="user-123", days=7
            )

        text = result["summary_text"]
        assert "no conversions" in text.lower()
        assert "$80" in text


class TestPerCampaignBreakdown:
    """per_campaign list contains useful per-campaign detail."""

    @pytest.mark.asyncio()
    async def test_per_campaign_includes_name_platform_spend_cpa(self, summarizer):
        """Each entry has campaign name, platform, spend, conversions, CPA."""
        campaigns = [
            {
                "id": "camp-1",
                "name": "Brand Search",
                "platform": "google_ads",
                "status": "active",
            },
            {
                "id": "camp-2",
                "name": "Retargeting",
                "platform": "meta_ads",
                "status": "active",
            },
        ]
        current_by_id = {
            "camp-1": _make_spend_summary(300.0, 10),
            "camp-2": _make_spend_summary(150.0, 6),
        }
        prior_by_id = {
            "camp-1": _make_spend_summary(250.0, 8),
            "camp-2": _make_spend_summary(100.0, 4),
        }

        async def mock_list(user_id=None):
            return campaigns

        async def mock_spend(
            ad_campaign_id, start_date=None, end_date=None, user_id=None
        ):
            from datetime import date

            today = date.today().isoformat()
            if end_date and end_date < today:
                return prior_by_id[ad_campaign_id]
            return current_by_id[ad_campaign_id]

        with (
            patch(
                "app.services.campaign_performance_summarizer.AdCampaignService"
            ) as mock_camp_cls,
            patch(
                "app.services.campaign_performance_summarizer.AdSpendTrackingService"
            ) as mock_spend_cls,
        ):
            mock_camp_cls.return_value.list_ad_campaigns = AsyncMock(
                side_effect=mock_list
            )
            mock_spend_cls.return_value.get_spend_summary = AsyncMock(
                side_effect=mock_spend
            )

            result = await summarizer.summarize_all_platforms(
                user_id="user-123", days=7
            )

        per_camp = result["per_campaign"]
        assert len(per_camp) == 2
        names = {c["name"] for c in per_camp}
        assert names == {"Brand Search", "Retargeting"}
        for entry in per_camp:
            assert "platform" in entry
            assert "spend" in entry
            assert "conversions" in entry
            assert "cpa" in entry
        # Brand Search: 300/10 = 30.00 CPA
        brand = next(c for c in per_camp if c["name"] == "Brand Search")
        assert brand["cpa"] == pytest.approx(30.0, abs=0.01)
        assert brand["platform"] == "google_ads"
        assert brand["spend"] == pytest.approx(300.0)
        assert brand["conversions"] == 10


class TestWoWComputation:
    """Internal helper _compute_wow returns correct percentage changes."""

    def test_wow_positive_change(self, summarizer):
        """Current > prior returns positive percentage."""
        pct = summarizer._compute_wow(current=12, prior=10)
        assert pct == pytest.approx(20.0, abs=0.01)

    def test_wow_negative_change(self, summarizer):
        """Current < prior returns negative percentage."""
        pct = summarizer._compute_wow(current=8, prior=10)
        assert pct == pytest.approx(-20.0, abs=0.01)

    def test_wow_no_prior_returns_none(self, summarizer):
        """prior=0 with current>0 returns None (no baseline)."""
        pct = summarizer._compute_wow(current=5, prior=0)
        assert pct is None

    def test_wow_both_zero_returns_none(self, summarizer):
        """Both zero returns None."""
        pct = summarizer._compute_wow(current=0, prior=0)
        assert pct is None
