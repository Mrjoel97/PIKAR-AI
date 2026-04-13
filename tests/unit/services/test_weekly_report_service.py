# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for WeeklyReportService — weekly business report generation and data catalog.

Plan 68-02 / DATA-02, DATA-03. Verifies:

- generate_weekly_report returns dict with required sections: period, revenue_summary,
  top_metrics, anomalies, executive_summary, generated_at
- generate_weekly_report handles empty financial_records gracefully
- generate_weekly_report includes week-over-week comparison when prior week data exists
- get_data_catalog_suggestions("stripe") returns Stripe-specific report suggestions
- get_data_catalog_suggestions("shopify") returns Shopify-specific report suggestions
- get_data_catalog_suggestions("unknown_provider") returns generic suggestions
- get_available_integrations returns list of connected providers for user
- format_report_as_briefing_card returns dict with type, title, summary, generated_at, sections

Uses the Windows-safe sys.modules stub pattern to sidestep the slowapi/starlette
.env UnicodeDecodeError before importing.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_ENV = {
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "service-role-test-key",
    "SUPABASE_ANON_KEY": "anon-test-key",
    "GOOGLE_API_KEY": "fake-api-key",
}


def _make_service():
    """Return a WeeklyReportService with a stubbed Supabase client.

    Patches ``app.services.supabase.get_service_client`` (the factory imported
    lazily inside ``AdminService.client``) so the lazy property resolves to a
    MagicMock without touching the real Supabase singleton.
    """
    with (
        patch.dict("os.environ", _FAKE_ENV, clear=False),
        patch(
            "app.services.supabase.get_service_client",
            return_value=MagicMock(),
        ),
    ):
        from app.services.weekly_report_service import WeeklyReportService

        svc = WeeklyReportService()
        # Force lazy ``client`` property to materialise on the patched factory
        _ = svc.client
        return svc


def _result(data=None):
    """Build a fake supabase result with ``.data``."""
    obj = MagicMock()
    obj.data = data if data is not None else []
    return obj


# ---------------------------------------------------------------------------
# TestWeeklyReportGeneration
# ---------------------------------------------------------------------------


class TestWeeklyReportGeneration:
    """Tests for generate_weekly_report method."""

    @pytest.mark.asyncio
    async def test_generate_weekly_report_returns_required_sections(self):
        """generate_weekly_report must return dict with all required top-level keys."""
        svc = _make_service()

        revenue_rows = [
            {
                "transaction_type": "income",
                "amount": 1500.0,
                "currency": "USD",
                "transaction_date": "2026-04-07",
            },
            {
                "transaction_type": "income",
                "amount": 2000.0,
                "currency": "USD",
                "transaction_date": "2026-04-08",
            },
        ]

        async def fake_execute(query, *, op_name=""):
            return _result(data=revenue_rows)

        with (
            patch(
                "app.services.weekly_report_service.execute_async",
                side_effect=fake_execute,
            ),
            patch(
                "app.services.weekly_report_service.WeeklyReportService._generate_executive_summary",
                new_callable=AsyncMock,
                return_value="Strong week with $3,500 total revenue.",
            ),
        ):
            result = await svc.generate_weekly_report("user-123")

        assert "period" in result
        assert "revenue_summary" in result
        assert "top_metrics" in result
        assert "anomalies" in result
        assert "executive_summary" in result
        assert "generated_at" in result

    @pytest.mark.asyncio
    async def test_generate_weekly_report_empty_financial_records(self):
        """generate_weekly_report handles empty financial_records gracefully."""
        svc = _make_service()

        async def fake_execute(query, *, op_name=""):
            return _result(data=[])

        with (
            patch(
                "app.services.weekly_report_service.execute_async",
                side_effect=fake_execute,
            ),
            patch(
                "app.services.weekly_report_service.WeeklyReportService._generate_executive_summary",
                new_callable=AsyncMock,
                return_value="No revenue data available for this week.",
            ),
        ):
            result = await svc.generate_weekly_report("user-123")

        assert result["revenue_summary"]["current"] == 0.0
        assert result["revenue_summary"]["previous"] == 0.0

    @pytest.mark.asyncio
    async def test_generate_weekly_report_week_over_week_comparison(self):
        """generate_weekly_report includes week-over-week comparison when prior week data exists."""
        svc = _make_service()

        call_count = 0

        async def fake_execute(query, *, op_name=""):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Current week revenue
                return _result(data=[
                    {"transaction_type": "income", "amount": 2000.0, "currency": "USD", "transaction_date": "2026-04-07"},
                ])
            elif call_count == 2:
                # Previous week revenue
                return _result(data=[
                    {"transaction_type": "income", "amount": 1000.0, "currency": "USD", "transaction_date": "2026-03-31"},
                ])
            return _result(data=[])

        with (
            patch(
                "app.services.weekly_report_service.execute_async",
                side_effect=fake_execute,
            ),
            patch(
                "app.services.weekly_report_service.WeeklyReportService._generate_executive_summary",
                new_callable=AsyncMock,
                return_value="Revenue up 100% week-over-week.",
            ),
        ):
            result = await svc.generate_weekly_report("user-123")

        rev = result["revenue_summary"]
        assert rev["current"] == 2000.0
        assert rev["previous"] == 1000.0
        assert rev["change_pct"] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# TestDataCatalogSuggestions
# ---------------------------------------------------------------------------


class TestDataCatalogSuggestions:
    """Tests for get_data_catalog_suggestions method."""

    def test_get_data_catalog_suggestions_stripe(self):
        """get_data_catalog_suggestions('stripe') returns Stripe-specific suggestions."""
        svc = _make_service()
        suggestions = svc.get_data_catalog_suggestions("stripe")

        assert isinstance(suggestions, list)
        assert len(suggestions) >= 1
        titles = [s["title"] for s in suggestions]
        # At least one Stripe-specific report title expected
        assert any("Revenue" in t or "Churn" in t or "Payment" in t for t in titles)
        # Each suggestion has required keys
        for s in suggestions:
            assert "title" in s
            assert "description" in s
            assert "report_type" in s

    def test_get_data_catalog_suggestions_shopify(self):
        """get_data_catalog_suggestions('shopify') returns Shopify-specific suggestions."""
        svc = _make_service()
        suggestions = svc.get_data_catalog_suggestions("shopify")

        assert isinstance(suggestions, list)
        assert len(suggestions) >= 1
        titles = [s["title"] for s in suggestions]
        assert any("Sales" in t or "Order" in t or "Product" in t for t in titles)
        for s in suggestions:
            assert "title" in s
            assert "description" in s
            assert "report_type" in s

    def test_get_data_catalog_suggestions_unknown_provider(self):
        """get_data_catalog_suggestions('unknown_provider') returns generic suggestions."""
        svc = _make_service()
        suggestions = svc.get_data_catalog_suggestions("unknown_provider")

        assert isinstance(suggestions, list)
        assert len(suggestions) >= 1
        for s in suggestions:
            assert "title" in s
            assert "description" in s
            assert "report_type" in s


# ---------------------------------------------------------------------------
# TestGetAvailableIntegrations
# ---------------------------------------------------------------------------


class TestGetAvailableIntegrations:
    """Tests for get_available_integrations method."""

    @pytest.mark.asyncio
    async def test_get_available_integrations_returns_list(self):
        """get_available_integrations returns list of connected providers."""
        svc = _make_service()

        rows = [
            {"provider": "stripe", "account_name": "Acme Corp", "connected_at": "2026-01-01T00:00:00Z"},
            {"provider": "shopify", "account_name": "Acme Shop", "connected_at": "2026-01-15T00:00:00Z"},
        ]

        with patch(
            "app.services.weekly_report_service.execute_async",
            return_value=_result(data=rows),
        ):
            integrations = await svc.get_available_integrations("user-123")

        assert isinstance(integrations, list)
        assert len(integrations) == 2
        assert integrations[0]["provider"] == "stripe"
        assert integrations[1]["provider"] == "shopify"
        for integ in integrations:
            assert "provider" in integ
            assert "account_name" in integ
            assert "connected_at" in integ

    @pytest.mark.asyncio
    async def test_get_available_integrations_empty(self):
        """get_available_integrations returns empty list when no integrations connected."""
        svc = _make_service()

        with patch(
            "app.services.weekly_report_service.execute_async",
            return_value=_result(data=[]),
        ):
            integrations = await svc.get_available_integrations("user-123")

        assert integrations == []


# ---------------------------------------------------------------------------
# TestFormatReportAsBriefingCard
# ---------------------------------------------------------------------------


class TestFormatReportAsBriefingCard:
    """Tests for format_report_as_briefing_card method."""

    def test_format_report_as_briefing_card_structure(self):
        """format_report_as_briefing_card returns dict with required keys."""
        svc = _make_service()

        sample_report = {
            "period": {"start": "2026-04-07", "end": "2026-04-13", "label": "Week of Apr 7"},
            "revenue_summary": {"current": 3500.0, "previous": 2000.0, "change_pct": 75.0, "currency": "USD"},
            "top_metrics": [{"name": "Revenue", "value": 3500.0, "change_pct": 75.0, "trend": "up"}],
            "anomalies": [],
            "executive_summary": "Revenue up 75% this week.",
            "generated_at": "2026-04-13T10:00:00Z",
        }

        card = svc.format_report_as_briefing_card(sample_report)

        assert card["type"] == "weekly_report"
        assert card["title"] == "Weekly Business Report"
        assert "summary" in card
        assert card["summary"] == "Revenue up 75% this week."
        assert "generated_at" in card
        assert "sections" in card
        assert isinstance(card["sections"], list)
