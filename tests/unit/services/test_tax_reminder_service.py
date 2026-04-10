# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for TaxReminderService.

Tests cover:
- YTD revenue aggregation from financial_records
- Quarterly tax estimation with default 25% rate
- Custom tax rate support
- Zero revenue returns $0 with explanation
- is_reminder_due within 14 days of quarter end
- is_reminder_due returns False when not near quarter boundary
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

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
def tax_service():
    """Return a TaxReminderService instance."""
    from app.services.tax_reminder_service import TaxReminderService

    return TaxReminderService()


# ---------------------------------------------------------------------------
# YTD Revenue Tests
# ---------------------------------------------------------------------------


class TestYTDRevenue:
    """Tests for get_ytd_revenue aggregation."""

    @pytest.mark.asyncio()
    async def test_sums_revenue_records(self, tax_service):
        """Revenue records for the current year are summed correctly."""
        mock_data = [
            {"amount": 5000.00},
            {"amount": 3000.00},
            {"amount": 2000.00},
        ]
        mock_response = MagicMock()
        mock_response.data = mock_data

        with patch(
            "app.services.tax_reminder_service.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await tax_service.get_ytd_revenue("user-123")

        assert result == 10000.00

    @pytest.mark.asyncio()
    async def test_zero_revenue_when_no_records(self, tax_service):
        """Returns 0.0 when no revenue records exist."""
        mock_response = MagicMock()
        mock_response.data = []

        with patch(
            "app.services.tax_reminder_service.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await tax_service.get_ytd_revenue("user-123")

        assert result == 0.0


# ---------------------------------------------------------------------------
# Quarterly Tax Estimate Tests
# ---------------------------------------------------------------------------


class TestQuarterlyTaxEstimate:
    """Tests for get_quarterly_tax_estimate computation."""

    @pytest.mark.asyncio()
    async def test_default_tax_rate_is_25_percent(self, tax_service):
        """Default rate of 25% is applied to YTD revenue."""
        mock_data = [
            {"amount": 40000.00},
        ]
        mock_response = MagicMock()
        mock_response.data = mock_data

        with patch(
            "app.services.tax_reminder_service.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await tax_service.get_quarterly_tax_estimate("user-123")

        assert result["ytd_revenue"] == 40000.00
        assert result["estimated_annual_tax"] == 10000.00  # 40000 * 0.25
        assert result["quarterly_payment"] == 2500.00  # 10000 / 4
        assert result["tax_rate"] == 0.25
        assert result["currency"] == "USD"
        assert "explanation" in result

    @pytest.mark.asyncio()
    async def test_custom_tax_rate(self, tax_service):
        """Custom tax rate overrides the default 25%."""
        mock_data = [
            {"amount": 20000.00},
        ]
        mock_response = MagicMock()
        mock_response.data = mock_data

        with patch(
            "app.services.tax_reminder_service.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await tax_service.get_quarterly_tax_estimate(
                "user-123", tax_rate=0.30
            )

        assert result["estimated_annual_tax"] == 6000.00  # 20000 * 0.30
        assert result["quarterly_payment"] == 1500.00  # 6000 / 4
        assert result["tax_rate"] == 0.30

    @pytest.mark.asyncio()
    async def test_zero_revenue_returns_zero_tax(self, tax_service):
        """Zero revenue returns $0 estimated tax with explanation."""
        mock_response = MagicMock()
        mock_response.data = []

        with patch(
            "app.services.tax_reminder_service.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await tax_service.get_quarterly_tax_estimate("user-123")

        assert result["ytd_revenue"] == 0.0
        assert result["estimated_annual_tax"] == 0.0
        assert result["quarterly_payment"] == 0.0
        assert "explanation" in result
        assert "$0" in result["explanation"] or "0.00" in result["explanation"]

    @pytest.mark.asyncio()
    async def test_next_deadline_is_present(self, tax_service):
        """Result includes the next quarter deadline date."""
        mock_response = MagicMock()
        mock_response.data = [{"amount": 1000.00}]

        with patch(
            "app.services.tax_reminder_service.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await tax_service.get_quarterly_tax_estimate("user-123")

        assert "next_deadline" in result
        assert result["next_deadline"]  # not empty


# ---------------------------------------------------------------------------
# Reminder Due Tests
# ---------------------------------------------------------------------------


class TestIsReminderDue:
    """Tests for is_reminder_due boundary detection."""

    def test_reminder_due_within_14_days_of_quarter_end(self, tax_service):
        """Returns True within 14 days of any quarter deadline."""
        # March 15 deadline: test March 5 (10 days before)
        test_date = date(2026, 3, 5)
        with patch("app.services.tax_reminder_service.date") as mock_date:
            mock_date.today.return_value = test_date
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            result = tax_service.is_reminder_due()

        assert result is True

    def test_reminder_due_on_deadline_day(self, tax_service):
        """Returns True on the deadline day itself."""
        test_date = date(2026, 6, 15)
        with patch("app.services.tax_reminder_service.date") as mock_date:
            mock_date.today.return_value = test_date
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            result = tax_service.is_reminder_due()

        assert result is True

    def test_reminder_not_due_when_far_from_deadline(self, tax_service):
        """Returns False when more than 14 days from any quarter deadline."""
        # Feb 1 is 42 days from March 15
        test_date = date(2026, 2, 1)
        with patch("app.services.tax_reminder_service.date") as mock_date:
            mock_date.today.return_value = test_date
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            result = tax_service.is_reminder_due()

        assert result is False

    def test_reminder_due_near_december_deadline(self, tax_service):
        """Returns True within 14 days of Dec 15 deadline."""
        test_date = date(2026, 12, 10)
        with patch("app.services.tax_reminder_service.date") as mock_date:
            mock_date.today.return_value = test_date
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            result = tax_service.is_reminder_due()

        assert result is True

    def test_reminder_not_due_after_deadline_passed(self, tax_service):
        """Returns False right after a deadline passes (e.g., Mar 20)."""
        test_date = date(2026, 3, 20)
        with patch("app.services.tax_reminder_service.date") as mock_date:
            mock_date.today.return_value = test_date
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            result = tax_service.is_reminder_due()

        assert result is False
