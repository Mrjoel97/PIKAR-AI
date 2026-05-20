"""Verify each Financial tool returns confidence + band derived from real signals.

These tests mock the underlying service layer so they run fast and isolated.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_revenue_stats_returns_confidence_and_band():
    from app.agents.financial.tools import get_revenue_stats

    fake_stats = {
        "revenue": 12345.67, "currency": "USD", "transaction_count": 42,
        "data_age_hours": 1.5, "source_breakdown": {"stripe": 42, "manual": 0},
    }
    fake_service = MagicMock()
    fake_service.get_revenue_stats = AsyncMock(return_value=fake_stats)

    with patch("app.services.financial_service.FinancialService", return_value=fake_service):
        result = await get_revenue_stats(period="current_month")

    assert result["success"] is True
    assert "confidence" in result
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["band"] in {"low", "medium", "high"}


@pytest.mark.asyncio
async def test_get_revenue_stats_error_path_has_low_band():
    from app.agents.financial.tools import get_revenue_stats

    fake_service = MagicMock()
    fake_service.get_revenue_stats = AsyncMock(side_effect=RuntimeError("boom"))

    with patch("app.services.financial_service.FinancialService", return_value=fake_service):
        result = await get_revenue_stats(period="current_month")

    assert result["success"] is False
    assert result["confidence"] == 0.0
    assert result["band"] == "low"


@pytest.mark.asyncio
async def test_get_cash_position_confidence_uses_reconciliation_signal():
    from app.agents.financial.tools import get_cash_position

    with patch("app.agents.financial.tools._query_financial_records",
               new=AsyncMock(return_value=[
                   {"amount": 100.0, "transaction_type": "revenue", "currency": "USD"},
                   {"amount": 50.0, "transaction_type": "expense", "currency": "USD"},
               ])), patch("app.agents.financial.tools._get_current_user_id", return_value="user-abc"):
        result = await get_cash_position()

    assert result["success"] is True
    assert "confidence" in result and "band" in result
    assert result["confidence"] > 0.0


@pytest.mark.asyncio
async def test_get_burn_runway_report_carries_confidence():
    from app.agents.financial.tools import get_burn_runway_report

    sample = [
        {"amount": 100.0, "transaction_type": "expense", "currency": "USD"}
        for _ in range(20)
    ]
    with patch("app.agents.financial.tools._get_current_user_id", return_value="user-abc"), \
         patch("app.agents.financial.tools.get_cash_position",
               new=AsyncMock(return_value={
                   "success": True, "cash_position": 5000.0, "currency": "USD",
                   "inflows": 8000.0, "outflows": 3000.0, "record_count": 20,
                   "confidence": 0.9, "band": "high",
               })), patch("app.agents.financial.tools._query_financial_records",
                          new=AsyncMock(return_value=sample)):
        result = await get_burn_runway_report()

    assert result["success"] is True
    assert "confidence" in result and "band" in result
    assert 0.0 <= result["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_generate_financial_forecast_horizon_decays_confidence():
    from app.agents.financial.tools import generate_financial_forecast

    fake_result = {
        "monthly_projections": [{"month": "2026-06", "revenue": 1000.0}],
        "methodology": "weighted_linear_regression", "sample_size": 200,
        "data_completeness": 0.95, "source_breakdown": {"stripe": 0.9, "manual": 0.1},
    }
    fake_svc = MagicMock()
    fake_svc.generate_forecast = AsyncMock(return_value=fake_result)

    with patch("app.services.forecast_service.ForecastService", return_value=fake_svc), \
         patch("app.agents.financial.tools._get_current_user_id", return_value="user-abc"):
        near = await generate_financial_forecast(months_ahead=1)
        far = await generate_financial_forecast(months_ahead=12)

    assert near["success"] is True and far["success"] is True
    assert near["confidence"] > far["confidence"]


@pytest.mark.asyncio
async def test_get_financial_health_score_includes_band():
    from app.agents.financial.tools import get_financial_health_score

    fake_svc = MagicMock()
    fake_svc.compute_health_score = AsyncMock(return_value={
        "score": 78, "color": "green", "explanation": "Healthy runway and stable burn.",
        "factors": {
            "revenue_trend": "positive", "runway_months": 14.2, "cash_flow_ratio": 1.3,
            "collection_rate": 0.92, "burn_stability": 0.88,
        },
        "data_completeness": 0.9, "reconciliation_signal": 0.95, "source_authority": 0.85,
    })

    with patch("app.services.financial_health_score_service.FinancialHealthScoreService",
               return_value=fake_svc), \
         patch("app.agents.financial.tools._get_current_user_id", return_value="user-abc"):
        result = await get_financial_health_score()

    assert result["success"] is True
    assert "confidence" in result and "band" in result
    assert result["band"] in {"low", "medium", "high"}


@pytest.mark.asyncio
async def test_no_hardcoded_confidence_constants():
    from app.agents.financial.tools import get_revenue_stats

    fake_svc = MagicMock()
    fake_svc.get_revenue_stats = AsyncMock(return_value={
        "revenue": 1.0, "currency": "USD", "transaction_count": 1,
        "data_age_hours": 0.5, "source_breakdown": {"stripe": 1},
    })
    with patch("app.services.financial_service.FinancialService", return_value=fake_svc):
        low_data = await get_revenue_stats(period="current_month")

    fake_svc.get_revenue_stats = AsyncMock(return_value={
        "revenue": 99999.0, "currency": "USD", "transaction_count": 500,
        "data_age_hours": 0.5, "source_breakdown": {"stripe": 500},
    })
    with patch("app.services.financial_service.FinancialService", return_value=fake_svc):
        high_data = await get_revenue_stats(period="current_month")

    assert low_data["confidence"] != high_data["confidence"]
