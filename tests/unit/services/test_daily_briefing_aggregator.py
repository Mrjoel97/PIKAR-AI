# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for DailyBriefingAggregator -- pending approvals, KPI changes, stalled initiatives, deadlines."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

USER_ID = "test-user-00000000-0000-0000-0000-000000000001"


def _make_mock_client() -> MagicMock:
    """Build a mock Supabase service client with a chainable query interface."""
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.in_.return_value = mock_chain
    mock_chain.gte.return_value = mock_chain
    mock_chain.lte.return_value = mock_chain
    mock_chain.lt.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.limit.return_value = mock_chain
    mock_chain.insert.return_value = mock_chain
    mock_chain.upsert.return_value = mock_chain
    mock_chain.delete.return_value = mock_chain
    mock_chain.update.return_value = mock_chain
    mock_chain.neq.return_value = mock_chain

    mock_table = MagicMock()
    mock_table.select.return_value = mock_chain
    mock_table.insert.return_value = mock_chain

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    return mock_client


# ---------------------------------------------------------------------------
# aggregate_daily_briefing
# ---------------------------------------------------------------------------


class TestAggregateDailyBriefing:
    """Tests for aggregate_daily_briefing function."""

    @pytest.mark.asyncio
    async def test_returns_all_four_sections(self):
        """Result dict has keys: pending_approvals, kpi_changes, stalled_initiatives, upcoming_deadlines."""
        mock_client = _make_mock_client()

        # Approvals count
        approvals_result = MagicMock()
        approvals_result.count = 3

        # KPI: two dashboard snapshots
        kpi_result = MagicMock()
        kpi_result.data = [
            {"metrics": {"revenue": 5000, "customers": 120}, "created_at": "2026-04-09T08:00:00+00:00"},
            {"metrics": {"revenue": 4500, "customers": 118}, "created_at": "2026-04-08T08:00:00+00:00"},
        ]

        # Stalled initiatives
        now = datetime.now(timezone.utc)
        stalled_result = MagicMock()
        stalled_result.data = [
            {
                "title": "Q2 Marketing Campaign",
                "updated_at": (now - timedelta(days=10)).isoformat(),
            },
        ]

        # Upcoming deadlines
        deadlines_result = MagicMock()
        deadlines_result.data = [
            {
                "title": "Submit report",
                "due_date": (now + timedelta(days=3)).isoformat(),
            },
        ]

        with (
            patch(
                "app.services.daily_briefing_aggregator.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.daily_briefing_aggregator.execute_async",
                new_callable=AsyncMock,
                side_effect=[approvals_result, kpi_result, stalled_result, deadlines_result],
            ),
        ):
            from app.services.daily_briefing_aggregator import aggregate_daily_briefing

            result = await aggregate_daily_briefing(USER_ID)

            assert "pending_approvals" in result
            assert "kpi_changes" in result
            assert "stalled_initiatives" in result
            assert "upcoming_deadlines" in result
            assert result["pending_approvals"] == 3

    @pytest.mark.asyncio
    async def test_stalled_initiatives_older_than_7_days(self):
        """Initiatives with updated_at > 7 days ago and active/in_progress status are stalled."""
        mock_client = _make_mock_client()
        now = datetime.now(timezone.utc)

        approvals_result = MagicMock()
        approvals_result.count = 0

        kpi_result = MagicMock()
        kpi_result.data = []

        stalled_result = MagicMock()
        stalled_result.data = [
            {
                "title": "Stale Project Alpha",
                "updated_at": (now - timedelta(days=14)).isoformat(),
            },
            {
                "title": "Stale Project Beta",
                "updated_at": (now - timedelta(days=8)).isoformat(),
            },
        ]

        deadlines_result = MagicMock()
        deadlines_result.data = []

        with (
            patch(
                "app.services.daily_briefing_aggregator.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.daily_briefing_aggregator.execute_async",
                new_callable=AsyncMock,
                side_effect=[approvals_result, kpi_result, stalled_result, deadlines_result],
            ),
        ):
            from app.services.daily_briefing_aggregator import aggregate_daily_briefing

            result = await aggregate_daily_briefing(USER_ID)

            assert len(result["stalled_initiatives"]) == 2
            assert result["stalled_initiatives"][0]["title"] == "Stale Project Alpha"
            assert result["stalled_initiatives"][0]["days_stalled"] >= 14

    @pytest.mark.asyncio
    async def test_kpi_changes_computes_direction_and_delta(self):
        """KPI changes compare latest vs previous dashboard_summaries.metrics, showing >5% changes."""
        mock_client = _make_mock_client()

        approvals_result = MagicMock()
        approvals_result.count = 0

        # Revenue: 5000 -> 4500 = -10% (should appear), customers: 120 -> 118 = -1.7% (should NOT appear)
        kpi_result = MagicMock()
        kpi_result.data = [
            {"metrics": {"revenue": 5000, "customers": 120}, "created_at": "2026-04-09T08:00:00+00:00"},
            {"metrics": {"revenue": 4500, "customers": 118}, "created_at": "2026-04-08T08:00:00+00:00"},
        ]

        stalled_result = MagicMock()
        stalled_result.data = []

        deadlines_result = MagicMock()
        deadlines_result.data = []

        with (
            patch(
                "app.services.daily_briefing_aggregator.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.daily_briefing_aggregator.execute_async",
                new_callable=AsyncMock,
                side_effect=[approvals_result, kpi_result, stalled_result, deadlines_result],
            ),
        ):
            from app.services.daily_briefing_aggregator import aggregate_daily_briefing

            result = await aggregate_daily_briefing(USER_ID)

            kpi_changes = result["kpi_changes"]
            # Only revenue should appear (>5% change)
            assert len(kpi_changes) >= 1
            revenue_change = next(
                (c for c in kpi_changes if c["metric"] == "revenue"), None
            )
            assert revenue_change is not None
            assert revenue_change["previous"] == 4500
            assert revenue_change["current"] == 5000
            assert revenue_change["direction"] == "up"

            # Customers should NOT appear (< 5% change)
            customer_change = next(
                (c for c in kpi_changes if c["metric"] == "customers"), None
            )
            assert customer_change is None

    @pytest.mark.asyncio
    async def test_upcoming_deadlines_within_7_days(self):
        """Tasks due within 7 days are included with title, due_date, and days_until."""
        mock_client = _make_mock_client()
        now = datetime.now(timezone.utc)

        approvals_result = MagicMock()
        approvals_result.count = 0

        kpi_result = MagicMock()
        kpi_result.data = []

        stalled_result = MagicMock()
        stalled_result.data = []

        deadlines_result = MagicMock()
        deadlines_result.data = [
            {
                "title": "Submit Q2 Report",
                "due_date": (now + timedelta(days=2)).isoformat(),
            },
            {
                "title": "Client Presentation",
                "due_date": (now + timedelta(days=5)).isoformat(),
            },
        ]

        with (
            patch(
                "app.services.daily_briefing_aggregator.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.daily_briefing_aggregator.execute_async",
                new_callable=AsyncMock,
                side_effect=[approvals_result, kpi_result, stalled_result, deadlines_result],
            ),
        ):
            from app.services.daily_briefing_aggregator import aggregate_daily_briefing

            result = await aggregate_daily_briefing(USER_ID)

            deadlines = result["upcoming_deadlines"]
            assert len(deadlines) == 2
            assert deadlines[0]["title"] == "Submit Q2 Report"
            assert "days_until" in deadlines[0]
            assert deadlines[0]["days_until"] >= 1
            assert deadlines[0]["days_until"] <= 3
