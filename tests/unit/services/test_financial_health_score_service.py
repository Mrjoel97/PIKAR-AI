# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for FinancialHealthScoreService -- composite 0-100 health score computation."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

USER_ID = "test-user-00000000-0000-0000-0000-000000000001"

# Ensure BaseService can initialize without real Supabase credentials
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _revenue_stats(revenue: float, status: str = "connected") -> dict:
    """Build a FinancialService.get_revenue_stats return value."""
    return {
        "revenue": revenue,
        "currency": "USD",
        "period": "current_month",
        "transaction_count": 5,
        "status": status,
    }


def _cash_position(cash: float, inflows: float, outflows: float) -> dict:
    """Build a get_cash_position return value."""
    return {
        "success": True,
        "cash_position": cash,
        "currency": "USD",
        "inflows": inflows,
        "outflows": outflows,
        "record_count": 10,
    }


def _burn_runway(cash: float, burn: float, runway: float | None) -> dict:
    """Build a get_burn_runway_report return value."""
    return {
        "success": True,
        "cash_position": cash,
        "monthly_burn": burn,
        "runway_months": runway,
        "currency": "USD",
        "calculation_window_days": 90,
    }


def _invoice_rows(paid: int, total: int) -> list[dict]:
    """Build mock invoice query rows."""
    rows = []
    for i in range(paid):
        rows.append({"id": f"inv-{i}", "status": "paid"})
    for i in range(total - paid):
        rows.append({"id": f"inv-unpaid-{i}", "status": "sent"})
    return rows


def _patch_dependencies(
    current_revenue: float = 10000.0,
    last_revenue: float = 8000.0,
    cash: float = 50000.0,
    inflows: float = 12000.0,
    outflows: float = 8000.0,
    burn: float = 8000.0,
    runway: float | None = 12.0,
    paid_invoices: int = 8,
    total_invoices: int = 10,
):
    """Return a context manager that patches all external dependencies for compute_health_score."""
    mock_financial_service = MagicMock()
    mock_financial_service.get_revenue_stats = AsyncMock(
        side_effect=lambda period="current_month": (
            _revenue_stats(current_revenue)
            if period == "current_month"
            else _revenue_stats(last_revenue)
        )
    )

    mock_get_cash = AsyncMock(
        return_value=_cash_position(cash, inflows, outflows)
    )
    mock_get_burn = AsyncMock(
        return_value=_burn_runway(cash, burn, runway)
    )

    invoice_data = _invoice_rows(paid_invoices, total_invoices)

    mock_execute = AsyncMock(
        return_value=MagicMock(data=invoice_data)
    )

    # Mock the Supabase client chain used for invoice queries
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.neq.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.limit.return_value = mock_chain
    mock_chain.insert.return_value = mock_chain

    mock_table = MagicMock()
    mock_table.select.return_value = mock_chain
    mock_table.insert.return_value = mock_chain

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    return (
        patch(
            "app.services.financial_health_score_service.FinancialService",
            return_value=mock_financial_service,
        ),
        patch(
            "app.services.financial_health_score_service.get_cash_position",
            mock_get_cash,
        ),
        patch(
            "app.services.financial_health_score_service.get_burn_runway_report",
            mock_get_burn,
        ),
        patch(
            "app.services.financial_health_score_service.execute_async",
            mock_execute,
        ),
        patch(
            "app.services.financial_health_score_service.FinancialHealthScoreService.client",
            new_callable=lambda: property(lambda self: mock_client),
        ),
    )


# ---------------------------------------------------------------------------
# compute_health_score: Green scenario (score >= 70)
# ---------------------------------------------------------------------------


class TestHealthScoreGreen:
    """High revenue growth, long runway, good cash flow, high collection rate -> green."""

    @pytest.mark.asyncio
    async def test_high_financials_produce_green_score(self):
        """Score >= 70 when revenue growing, runway >= 12mo, cash flow ratio > 1.5, collection >= 80%."""
        patches = _patch_dependencies(
            current_revenue=15000.0,
            last_revenue=10000.0,
            cash=100000.0,
            inflows=15000.0,
            outflows=8000.0,
            burn=8000.0,
            runway=12.5,
            paid_invoices=9,
            total_invoices=10,
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            from app.services.financial_health_score_service import (
                FinancialHealthScoreService,
            )

            svc = FinancialHealthScoreService()
            result = await svc.compute_health_score(USER_ID)

        assert result["score"] >= 70
        assert result["color"] == "green"
        assert isinstance(result["explanation"], str)
        assert len(result["explanation"]) > 10
        assert "factors" in result
        assert "computed_at" in result

    @pytest.mark.asyncio
    async def test_score_is_integer_between_0_and_100(self):
        """Score is always an integer in [0, 100]."""
        patches = _patch_dependencies()
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            from app.services.financial_health_score_service import (
                FinancialHealthScoreService,
            )

            svc = FinancialHealthScoreService()
            result = await svc.compute_health_score(USER_ID)

        assert isinstance(result["score"], int)
        assert 0 <= result["score"] <= 100


# ---------------------------------------------------------------------------
# compute_health_score: Red scenario (score < 40)
# ---------------------------------------------------------------------------


class TestHealthScoreRed:
    """Zero revenue, high burn, short runway -> red."""

    @pytest.mark.asyncio
    async def test_poor_financials_produce_red_score(self):
        """Score < 40 when zero revenue, high burn, short runway, low collection rate."""
        patches = _patch_dependencies(
            current_revenue=0.0,
            last_revenue=5000.0,
            cash=5000.0,
            inflows=1000.0,
            outflows=10000.0,
            burn=10000.0,
            runway=0.5,
            paid_invoices=1,
            total_invoices=10,
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            from app.services.financial_health_score_service import (
                FinancialHealthScoreService,
            )

            svc = FinancialHealthScoreService()
            result = await svc.compute_health_score(USER_ID)

        assert result["score"] < 40
        assert result["color"] == "red"


# ---------------------------------------------------------------------------
# compute_health_score: Yellow scenario (score 40-69)
# ---------------------------------------------------------------------------


class TestHealthScoreYellow:
    """Moderate financials -> yellow."""

    @pytest.mark.asyncio
    async def test_moderate_financials_produce_yellow_score(self):
        """Score 40-69 with moderate revenue, moderate runway, average cash flow."""
        patches = _patch_dependencies(
            current_revenue=8000.0,
            last_revenue=8000.0,
            cash=30000.0,
            inflows=8000.0,
            outflows=7000.0,
            burn=7000.0,
            runway=4.3,
            paid_invoices=6,
            total_invoices=10,
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            from app.services.financial_health_score_service import (
                FinancialHealthScoreService,
            )

            svc = FinancialHealthScoreService()
            result = await svc.compute_health_score(USER_ID)

        assert 40 <= result["score"] <= 69
        assert result["color"] == "yellow"


# ---------------------------------------------------------------------------
# compute_health_score: Insufficient data fallback
# ---------------------------------------------------------------------------


class TestHealthScoreInsufficientData:
    """Missing data produces fallback with 'insufficient data' explanation."""

    @pytest.mark.asyncio
    async def test_no_data_produces_fallback(self):
        """When all financial data returns zero/empty, score includes insufficient data note."""
        patches = _patch_dependencies(
            current_revenue=0.0,
            last_revenue=0.0,
            cash=0.0,
            inflows=0.0,
            outflows=0.0,
            burn=0.0,
            runway=None,
            paid_invoices=0,
            total_invoices=0,
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            from app.services.financial_health_score_service import (
                FinancialHealthScoreService,
            )

            svc = FinancialHealthScoreService()
            result = await svc.compute_health_score(USER_ID)

        assert isinstance(result["score"], int)
        assert 0 <= result["score"] <= 100
        assert "insufficient data" in result["explanation"].lower()


# ---------------------------------------------------------------------------
# Factor weights verification
# ---------------------------------------------------------------------------


class TestFactorWeights:
    """Score factors include expected keys with correct weight semantics."""

    @pytest.mark.asyncio
    async def test_factors_contain_all_five_components(self):
        """Factors dict contains revenue_trend, runway_months, cash_flow_ratio, collection_rate, burn_stability."""
        patches = _patch_dependencies()
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            from app.services.financial_health_score_service import (
                FinancialHealthScoreService,
            )

            svc = FinancialHealthScoreService()
            result = await svc.compute_health_score(USER_ID)

        factors = result["factors"]
        expected_keys = {
            "revenue_trend",
            "runway_months",
            "cash_flow_ratio",
            "collection_rate",
            "burn_stability",
        }
        assert set(factors.keys()) == expected_keys
        # Each factor value should be a number
        for key in expected_keys:
            assert isinstance(factors[key], (int, float)), f"{key} should be numeric"

    @pytest.mark.asyncio
    async def test_weighted_score_matches_factor_weights(self):
        """Weighted sum: revenue_trend(0.25) + runway_months(0.25) + cash_flow_ratio(0.20) + collection_rate(0.15) + burn_stability(0.15) ~ score."""
        patches = _patch_dependencies()
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            from app.services.financial_health_score_service import (
                FinancialHealthScoreService,
            )

            svc = FinancialHealthScoreService()
            result = await svc.compute_health_score(USER_ID)

        factors = result["factors"]
        weighted = (
            factors["revenue_trend"] * 0.25
            + factors["runway_months"] * 0.25
            + factors["cash_flow_ratio"] * 0.20
            + factors["collection_rate"] * 0.15
            + factors["burn_stability"] * 0.15
        )
        # Score should match the weighted sum (rounded to int)
        assert abs(result["score"] - round(weighted)) <= 1
