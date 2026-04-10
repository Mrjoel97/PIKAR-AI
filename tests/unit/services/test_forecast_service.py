# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for ForecastService - data-driven financial forecasting."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

# Ensure BaseService can initialize without real Supabase credentials
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")

from app.services.forecast_service import ForecastService


@pytest.fixture()
def service():
    """Create a ForecastService instance."""
    return ForecastService()


def _monthly_history(months: int, base_revenue: float = 10000.0, revenue_growth: float = 0.0, base_expenses: float = 7000.0) -> list[dict]:
    """Generate synthetic monthly history data."""
    now = datetime.now(timezone.utc)
    history = []
    for i in range(months):
        month_offset = months - 1 - i
        month_date = now.replace(day=1)
        # Simple month subtraction
        year = month_date.year
        month = month_date.month - month_offset
        while month <= 0:
            month += 12
            year -= 1
        month_str = f"{year}-{month:02d}"
        revenue = base_revenue + (revenue_growth * (i))
        history.append({
            "month": month_str,
            "revenue": round(revenue, 2),
            "expenses": round(base_expenses, 2),
            "net": round(revenue - base_expenses, 2),
        })
    return history


class TestForecastServiceGenerateForecast:
    """Tests for generate_forecast method."""

    @pytest.mark.asyncio()
    async def test_forecast_with_sufficient_data_produces_six_months(self, service):
        """With 6+ months of history, forecast produces 6-month projection."""
        history = _monthly_history(8, base_revenue=10000, revenue_growth=500)
        with patch.object(service, "get_monthly_history", new_callable=AsyncMock, return_value=history):
            result = await service.generate_forecast(user_id="user-1")

        assert "forecast_months" in result
        assert len(result["forecast_months"]) == 6
        assert result["confidence"] == "high"
        assert result["data_months_used"] == 8

    @pytest.mark.asyncio()
    async def test_growing_revenue_extrapolates_upward(self, service):
        """Growing revenue trend should produce upward projections."""
        history = _monthly_history(8, base_revenue=10000, revenue_growth=1000)
        with patch.object(service, "get_monthly_history", new_callable=AsyncMock, return_value=history):
            result = await service.generate_forecast(user_id="user-1")

        forecasts = result["forecast_months"]
        # Each projected month should have higher revenue than the last historical month
        last_historical_revenue = history[-1]["revenue"]
        assert forecasts[0]["projected_revenue"] >= last_historical_revenue

    @pytest.mark.asyncio()
    async def test_declining_revenue_extrapolates_downward(self, service):
        """Declining revenue trend should produce downward projections."""
        history = _monthly_history(8, base_revenue=20000, revenue_growth=-1000)
        with patch.object(service, "get_monthly_history", new_callable=AsyncMock, return_value=history):
            result = await service.generate_forecast(user_id="user-1")

        forecasts = result["forecast_months"]
        last_historical_revenue = history[-1]["revenue"]
        # First projected month should be at or below last historical
        assert forecasts[0]["projected_revenue"] <= last_historical_revenue + 500  # some tolerance

    @pytest.mark.asyncio()
    async def test_limited_data_returns_flat_projection(self, service):
        """With < 3 months of data, returns flat projection with low confidence."""
        history = _monthly_history(2, base_revenue=10000)
        with patch.object(service, "get_monthly_history", new_callable=AsyncMock, return_value=history):
            result = await service.generate_forecast(user_id="user-1")

        assert result["confidence"] == "low"
        forecasts = result["forecast_months"]
        assert len(forecasts) == 6
        # Flat projection: all months should have roughly the same revenue
        revenues = [m["projected_revenue"] for m in forecasts]
        assert max(revenues) - min(revenues) < 1.0

    @pytest.mark.asyncio()
    async def test_medium_data_returns_medium_confidence(self, service):
        """With 3-5 months of data, returns medium confidence."""
        history = _monthly_history(4, base_revenue=10000, revenue_growth=500)
        with patch.object(service, "get_monthly_history", new_callable=AsyncMock, return_value=history):
            result = await service.generate_forecast(user_id="user-1")

        assert result["confidence"] == "medium"

    @pytest.mark.asyncio()
    async def test_forecast_includes_metadata(self, service):
        """Forecast result includes title, currency, generated_at, methodology."""
        history = _monthly_history(8, base_revenue=10000, revenue_growth=500)
        with patch.object(service, "get_monthly_history", new_callable=AsyncMock, return_value=history):
            result = await service.generate_forecast(user_id="user-1", title="Q2 Forecast")

        assert result["title"] == "Q2 Forecast"
        assert result["currency"] == "USD"
        assert "generated_at" in result
        assert "methodology" in result

    @pytest.mark.asyncio()
    async def test_revenue_clamped_to_zero(self, service):
        """Projected revenue should never go below zero."""
        history = _monthly_history(8, base_revenue=5000, revenue_growth=-2000)
        with patch.object(service, "get_monthly_history", new_callable=AsyncMock, return_value=history):
            result = await service.generate_forecast(user_id="user-1", months_ahead=12)

        for month in result["forecast_months"]:
            assert month["projected_revenue"] >= 0.0
            assert month["projected_expenses"] >= 0.0
