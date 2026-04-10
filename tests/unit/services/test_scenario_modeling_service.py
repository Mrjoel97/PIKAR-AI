# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for ScenarioModelingService - what-if financial projections."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.scenario_modeling_service import ScenarioModelingService


def _make_baseline_forecast(months: int = 6, revenue: float = 15000.0, expenses: float = 10000.0) -> dict:
    """Create a synthetic baseline forecast for testing."""
    forecast_months = []
    for i in range(months):
        forecast_months.append({
            "month": f"2026-{(i + 5):02d}",
            "projected_revenue": revenue,
            "projected_expenses": expenses,
            "projected_net": revenue - expenses,
        })
    return {
        "title": "Baseline",
        "forecast_months": forecast_months,
        "confidence": "high",
        "data_months_used": 8,
        "methodology": "weighted_linear_regression",
        "currency": "USD",
        "generated_at": "2026-04-10T00:00:00Z",
    }


@pytest.fixture()
def service():
    """Create a ScenarioModelingService with mocked Supabase."""
    with patch("app.services.base_service.os.environ.get") as mock_env:
        mock_env.side_effect = lambda k, *a: {
            "SUPABASE_URL": "http://localhost:54321",
            "SUPABASE_ANON_KEY": "test-key",
        }.get(k, a[0] if a else None)
        return ScenarioModelingService()


class TestScenarioModelingService:
    """Tests for run_scenario method."""

    @pytest.mark.asyncio()
    async def test_hire_scenario_increases_expenses(self, service):
        """Hiring 2 people at $5000/mo adds $10,000/mo to expenses."""
        baseline = _make_baseline_forecast(revenue=15000, expenses=10000)

        with (
            patch("app.services.scenario_modeling_service.ForecastService") as MockFS,
            patch("app.services.scenario_modeling_service.get_cash_position", new_callable=AsyncMock, return_value={"cash_position": 50000.0}),
        ):
            MockFS.return_value.generate_forecast = AsyncMock(return_value=baseline)
            result = await service.run_scenario(
                user_id="user-1",
                scenario={"hire": {"count": 2, "salary_per_person": 5000}},
            )

        projected = result["projected"]
        assert len(projected) == 6
        # Each month's expenses should be baseline (10000) + hire cost (10000) = 20000
        for month in projected:
            assert month["projected_expenses"] == 20000.0

    @pytest.mark.asyncio()
    async def test_revenue_change_reduces_revenue(self, service):
        """Losing 10% revenue reduces projected revenue by 10%."""
        baseline = _make_baseline_forecast(revenue=20000, expenses=10000)

        with (
            patch("app.services.scenario_modeling_service.ForecastService") as MockFS,
            patch("app.services.scenario_modeling_service.get_cash_position", new_callable=AsyncMock, return_value={"cash_position": 50000.0}),
        ):
            MockFS.return_value.generate_forecast = AsyncMock(return_value=baseline)
            result = await service.run_scenario(
                user_id="user-1",
                scenario={"lose_customers_pct": 10},
            )

        projected = result["projected"]
        for month in projected:
            assert month["projected_revenue"] == 18000.0  # 20000 * 0.9

    @pytest.mark.asyncio()
    async def test_new_expense_adds_flat_cost(self, service):
        """Adding a $3000/mo expense increases expenses by that amount."""
        baseline = _make_baseline_forecast(revenue=15000, expenses=10000)

        with (
            patch("app.services.scenario_modeling_service.ForecastService") as MockFS,
            patch("app.services.scenario_modeling_service.get_cash_position", new_callable=AsyncMock, return_value={"cash_position": 50000.0}),
        ):
            MockFS.return_value.generate_forecast = AsyncMock(return_value=baseline)
            result = await service.run_scenario(
                user_id="user-1",
                scenario={"new_expense": {"description": "New SaaS tool", "monthly_amount": 3000}},
            )

        projected = result["projected"]
        for month in projected:
            assert month["projected_expenses"] == 13000.0

    @pytest.mark.asyncio()
    async def test_baseline_projection_no_changes(self, service):
        """Baseline scenario (empty scenario dict) should match forecast."""
        baseline = _make_baseline_forecast(revenue=15000, expenses=10000)

        with (
            patch("app.services.scenario_modeling_service.ForecastService") as MockFS,
            patch("app.services.scenario_modeling_service.get_cash_position", new_callable=AsyncMock, return_value={"cash_position": 50000.0}),
        ):
            MockFS.return_value.generate_forecast = AsyncMock(return_value=baseline)
            result = await service.run_scenario(
                user_id="user-1",
                scenario={},
            )

        projected = result["projected"]
        for i, month in enumerate(projected):
            assert month["projected_revenue"] == 15000.0
            assert month["projected_expenses"] == 10000.0

    @pytest.mark.asyncio()
    async def test_projection_returns_six_monthly_data_points(self, service):
        """Projection returns 6 monthly data points with all required fields."""
        baseline = _make_baseline_forecast(revenue=15000, expenses=10000)

        with (
            patch("app.services.scenario_modeling_service.ForecastService") as MockFS,
            patch("app.services.scenario_modeling_service.get_cash_position", new_callable=AsyncMock, return_value={"cash_position": 50000.0}),
        ):
            MockFS.return_value.generate_forecast = AsyncMock(return_value=baseline)
            result = await service.run_scenario(
                user_id="user-1",
                scenario={"hire": {"count": 1, "salary_per_person": 5000}},
            )

        projected = result["projected"]
        assert len(projected) == 6
        for month in projected:
            assert "projected_revenue" in month
            assert "projected_expenses" in month
            assert "projected_net" in month
            assert "cash_position" in month
            assert "month" in month

    @pytest.mark.asyncio()
    async def test_cumulative_cash_position(self, service):
        """Each month shows cumulative cash position starting from current."""
        baseline = _make_baseline_forecast(revenue=15000, expenses=10000)

        with (
            patch("app.services.scenario_modeling_service.ForecastService") as MockFS,
            patch("app.services.scenario_modeling_service.get_cash_position", new_callable=AsyncMock, return_value={"cash_position": 50000.0}),
        ):
            MockFS.return_value.generate_forecast = AsyncMock(return_value=baseline)
            result = await service.run_scenario(
                user_id="user-1",
                scenario={},
            )

        projected = result["projected"]
        # First month: 50000 + (15000 - 10000) = 55000
        assert projected[0]["cash_position"] == 55000.0
        # Second month: 55000 + 5000 = 60000
        assert projected[1]["cash_position"] == 60000.0
        assert result["starting_cash"] == 50000.0

    @pytest.mark.asyncio()
    async def test_negative_cash_warning(self, service):
        """If scenario leads to negative cash, a warning is included."""
        baseline = _make_baseline_forecast(revenue=5000, expenses=10000)

        with (
            patch("app.services.scenario_modeling_service.ForecastService") as MockFS,
            patch("app.services.scenario_modeling_service.get_cash_position", new_callable=AsyncMock, return_value={"cash_position": 10000.0}),
        ):
            MockFS.return_value.generate_forecast = AsyncMock(return_value=baseline)
            result = await service.run_scenario(
                user_id="user-1",
                scenario={},
            )

        assert result["months_until_negative"] is not None
        assert len(result["warnings"]) > 0
        assert any("negative" in w.lower() or "cash" in w.lower() for w in result["warnings"])

    @pytest.mark.asyncio()
    async def test_price_increase_raises_revenue(self, service):
        """Price increase of 20% raises revenue by 20%."""
        baseline = _make_baseline_forecast(revenue=10000, expenses=7000)

        with (
            patch("app.services.scenario_modeling_service.ForecastService") as MockFS,
            patch("app.services.scenario_modeling_service.get_cash_position", new_callable=AsyncMock, return_value={"cash_position": 50000.0}),
        ):
            MockFS.return_value.generate_forecast = AsyncMock(return_value=baseline)
            result = await service.run_scenario(
                user_id="user-1",
                scenario={"price_increase_pct": 20},
            )

        projected = result["projected"]
        for month in projected:
            assert month["projected_revenue"] == 12000.0  # 10000 * 1.2

    @pytest.mark.asyncio()
    async def test_result_includes_summary(self, service):
        """Result includes a human-readable summary string."""
        baseline = _make_baseline_forecast(revenue=15000, expenses=10000)

        with (
            patch("app.services.scenario_modeling_service.ForecastService") as MockFS,
            patch("app.services.scenario_modeling_service.get_cash_position", new_callable=AsyncMock, return_value={"cash_position": 50000.0}),
        ):
            MockFS.return_value.generate_forecast = AsyncMock(return_value=baseline)
            result = await service.run_scenario(
                user_id="user-1",
                scenario={"hire": {"count": 2, "salary_per_person": 5000}},
            )

        assert "summary" in result
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 20
