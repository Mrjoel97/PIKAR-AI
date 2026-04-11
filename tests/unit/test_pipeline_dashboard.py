# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for pipeline_dashboard tools.

Tests pipeline health classification (stalled/at_risk/healthy/won/lost),
action recommendation generation, and lead source attribution grouping.
All Supabase calls are mocked via execute_async patch.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _deal(
    *,
    deal_id: str = "deal-1",
    name: str = "Acme Corp",
    stage: str = "qualifiedtobuy",
    amount: float = 10_000.0,
    pipeline: str = "default",
    days_since_update: int = 5,
    close_days: int = 30,
    last_activity_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a minimal hubspot_deals row dict."""
    updated = _utc_now() - timedelta(days=days_since_update)
    close_date = (_utc_now() + timedelta(days=close_days)).date().isoformat()
    return {
        "id": deal_id,
        "user_id": "user-abc",
        "hubspot_deal_id": f"hs-{deal_id}",
        "deal_name": name,
        "pipeline": pipeline,
        "stage": stage,
        "amount": amount,
        "close_date": close_date,
        "associated_contacts": [],
        "properties": {},
        "created_at": (updated - timedelta(days=10)).isoformat(),
        "updated_at": updated.isoformat(),
        "last_activity_at": last_activity_at.isoformat() if last_activity_at else None,
    }


def _contact(
    *,
    contact_id: str = "c-1",
    source: str = "social",
    lifecycle_stage: str = "lead",
    created_days_ago: int = 30,
    utm_source: str | None = None,
    campaign_id: str | None = None,
) -> dict[str, Any]:
    """Build a minimal contacts row dict."""
    created_at = _utc_now() - timedelta(days=created_days_ago)
    return {
        "id": contact_id,
        "user_id": "user-abc",
        "source": source,
        "lifecycle_stage": lifecycle_stage,
        "created_at": created_at.isoformat(),
        "utm_source": utm_source,
        "campaign_id": campaign_id,
    }


# ---------------------------------------------------------------------------
# Test: get_pipeline_recommendations
# ---------------------------------------------------------------------------


class TestGetPipelineRecommendations:
    """Tests for the get_pipeline_recommendations tool."""

    @pytest.mark.asyncio
    async def test_returns_grouped_by_status(self) -> None:
        """Test 1: result contains stalled/at_risk/healthy/won/lost groups."""
        deals = [
            _deal(deal_id="d1", stage="qualifiedtobuy", days_since_update=20),  # stalled
            _deal(deal_id="d2", stage="qualifiedtobuy", days_since_update=3),   # healthy
            _deal(deal_id="d3", stage="closedwon", days_since_update=5),        # won
            _deal(deal_id="d4", stage="closedlost", days_since_update=5),       # lost
        ]
        mock_result = MagicMock()
        mock_result.data = deals

        with (
            patch(
                "app.agents.tools.pipeline_dashboard._get_user_id",
                return_value="user-abc",
            ),
            patch(
                "app.agents.tools.pipeline_dashboard.execute_async",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            from app.agents.tools.pipeline_dashboard import get_pipeline_recommendations

            result = await get_pipeline_recommendations()

        assert result["success"] is True
        health = result["pipeline_health"]
        assert set(health.keys()) >= {"stalled", "at_risk", "healthy", "won", "lost"}
        assert result["summary"]["total_deals"] == 4

    @pytest.mark.asyncio
    async def test_stalled_deals_get_reengagement_recommendations(self) -> None:
        """Test 2: stalled deals (>14 days no activity) get re-engagement actions."""
        stalled_deal = _deal(
            deal_id="stalled-1",
            stage="qualifiedtobuy",
            days_since_update=20,
        )
        mock_result = MagicMock()
        mock_result.data = [stalled_deal]

        with (
            patch(
                "app.agents.tools.pipeline_dashboard._get_user_id",
                return_value="user-abc",
            ),
            patch(
                "app.agents.tools.pipeline_dashboard.execute_async",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            from app.agents.tools.pipeline_dashboard import get_pipeline_recommendations

            result = await get_pipeline_recommendations(days_stalled_threshold=14)

        health = result["pipeline_health"]
        assert len(health["stalled"]) == 1
        assert result["summary"]["stalled_count"] == 1

        recommendations = result["recommendations"]
        stalled_recs = [r for r in recommendations if r["deal_id"] == "stalled-1"]
        assert stalled_recs, "Expected recommendations for stalled deal"
        actions = [r["action"] for r in stalled_recs]
        # At least one re-engagement action
        assert any(
            keyword in " ".join(actions).lower()
            for keyword in ("re-engagement", "email", "discount", "escalate", "manager")
        ), f"Expected re-engagement actions, got: {actions}"

    @pytest.mark.asyncio
    async def test_at_risk_deals_get_escalation_recommendations(self) -> None:
        """Test 3: at-risk deals (close_date within 14 days, early stage) get escalation."""
        at_risk_deal = _deal(
            deal_id="risk-1",
            stage="appointmentscheduled",
            days_since_update=3,
            close_days=7,  # closing in 7 days
        )
        mock_result = MagicMock()
        mock_result.data = [at_risk_deal]

        with (
            patch(
                "app.agents.tools.pipeline_dashboard._get_user_id",
                return_value="user-abc",
            ),
            patch(
                "app.agents.tools.pipeline_dashboard.execute_async",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            from app.agents.tools.pipeline_dashboard import get_pipeline_recommendations

            result = await get_pipeline_recommendations()

        health = result["pipeline_health"]
        assert len(health["at_risk"]) == 1
        assert result["summary"]["at_risk_count"] == 1

        recommendations = result["recommendations"]
        risk_recs = [r for r in recommendations if r["deal_id"] == "risk-1"]
        assert risk_recs, "Expected recommendations for at-risk deal"
        actions = [r["action"] for r in risk_recs]
        assert any(
            keyword in " ".join(actions).lower()
            for keyword in ("review", "call", "competitive", "trial", "urgent")
        ), f"Expected escalation actions, got: {actions}"

    @pytest.mark.asyncio
    async def test_no_user_id_returns_error(self) -> None:
        """Test 6 (part A): get_pipeline_recommendations returns error when no user_id."""
        with patch(
            "app.agents.tools.pipeline_dashboard._get_user_id",
            return_value=None,
        ):
            from app.agents.tools.pipeline_dashboard import get_pipeline_recommendations

            result = await get_pipeline_recommendations()

        assert "error" in result
        assert result.get("success") is not True


# ---------------------------------------------------------------------------
# Test: get_lead_attribution
# ---------------------------------------------------------------------------


class TestGetLeadAttribution:
    """Tests for the get_lead_attribution tool."""

    @pytest.mark.asyncio
    async def test_returns_source_breakdown_with_counts_and_conversion(self) -> None:
        """Test 4: attribution returns source breakdown with counts and conversion rates."""
        contacts = [
            _contact(contact_id="c1", source="social", lifecycle_stage="lead"),
            _contact(contact_id="c2", source="social", lifecycle_stage="customer"),
            _contact(contact_id="c3", source="referral", lifecycle_stage="customer"),
            _contact(contact_id="c4", source="email", lifecycle_stage="lead"),
        ]
        mock_result = MagicMock()
        mock_result.data = contacts

        with (
            patch(
                "app.agents.tools.pipeline_dashboard._get_user_id",
                return_value="user-abc",
            ),
            patch(
                "app.agents.tools.pipeline_dashboard.execute_async",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            from app.agents.tools.pipeline_dashboard import get_lead_attribution

            result = await get_lead_attribution(period_days=90)

        assert result["success"] is True
        attr = result["attribution"]

        assert result["period_days"] == 90
        assert attr["total_leads"] == 4
        assert attr["total_converted"] == 2

        by_source = {s["source"]: s for s in attr["by_source"]}
        assert "social" in by_source
        assert by_source["social"]["count"] == 2
        assert by_source["social"]["converted"] == 1
        assert abs(by_source["social"]["conversion_rate"] - 0.5) < 1e-6

        assert "referral" in by_source
        assert by_source["referral"]["converted"] == 1

    @pytest.mark.asyncio
    async def test_attribution_includes_campaign_detail_when_utm_available(self) -> None:
        """Test 5: attribution includes campaign-level breakdown when UTM data present."""
        contacts = [
            _contact(
                contact_id="c1",
                source="ad_campaign",
                lifecycle_stage="customer",
                utm_source="google",
                campaign_id="camp-1",
            ),
            _contact(
                contact_id="c2",
                source="ad_campaign",
                lifecycle_stage="lead",
                utm_source="google",
                campaign_id="camp-1",
            ),
            _contact(
                contact_id="c3",
                source="social",
                lifecycle_stage="lead",
                utm_source=None,
                campaign_id=None,
            ),
        ]
        mock_result = MagicMock()
        mock_result.data = contacts

        with (
            patch(
                "app.agents.tools.pipeline_dashboard._get_user_id",
                return_value="user-abc",
            ),
            patch(
                "app.agents.tools.pipeline_dashboard.execute_async",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            from app.agents.tools.pipeline_dashboard import get_lead_attribution

            result = await get_lead_attribution(period_days=90)

        attr = result["attribution"]
        # Campaign-level breakdown should be present when UTM data exists
        assert "by_campaign" in attr
        by_campaign = {c["utm_source"]: c for c in attr["by_campaign"]}
        assert "google" in by_campaign
        assert by_campaign["google"]["count"] == 2

    @pytest.mark.asyncio
    async def test_no_user_id_returns_error(self) -> None:
        """Test 6 (part B): get_lead_attribution returns error when no user_id."""
        with patch(
            "app.agents.tools.pipeline_dashboard._get_user_id",
            return_value=None,
        ):
            from app.agents.tools.pipeline_dashboard import get_lead_attribution

            result = await get_lead_attribution()

        assert "error" in result
        assert result.get("success") is not True


# ---------------------------------------------------------------------------
# Test: PIPELINE_DASHBOARD_TOOLS export
# ---------------------------------------------------------------------------


class TestPipelineDashboardToolsExport:
    """Verify module-level exports are correct."""

    def test_tools_list_exports_both_functions(self) -> None:
        """PIPELINE_DASHBOARD_TOOLS exports exactly the two tool functions."""
        from app.agents.tools.pipeline_dashboard import (
            PIPELINE_DASHBOARD_TOOLS,
            get_lead_attribution,
            get_pipeline_recommendations,
        )

        assert get_pipeline_recommendations in PIPELINE_DASHBOARD_TOOLS
        assert get_lead_attribution in PIPELINE_DASHBOARD_TOOLS
        assert len(PIPELINE_DASHBOARD_TOOLS) == 2
