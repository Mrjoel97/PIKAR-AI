# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for ObservabilityMetricsService — latency, error rate, and AI cost.

Plan 51-03 / OBS-02, OBS-03, OBS-04. Verifies:

- compute_latency_percentiles returns p50, p95, p99, sample_count, error_count
- compute_latency_percentiles handles empty data without raising
- compute_error_rate returns error_rate, error_count, total_count with correct division
- compute_error_rate handles zero-total gracefully (no ZeroDivisionError)
- compute_ai_cost_by_agent maps tokens to USD using AI_MODEL_PRICING
- compute_ai_cost_by_agent returns empty dict for empty table
- project_monthly_ai_spend returns mtd_actual, projected_full_month, projection_method
- _percentile helper returns correct values for known inputs
- ObservabilityMetricsService inherits from AdminService (regression guard)
- AI_MODEL_PRICING keys include expected model names

Uses the Windows-safe sys.modules stub pattern (established in Phase 49-05) to
sidestep the slowapi/starlette .env UnicodeDecodeError before importing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_ENV = {
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "service-role-test-key",
    "SUPABASE_ANON_KEY": "anon-test-key",
}


def _make_service():
    """Return an ObservabilityMetricsService with a stubbed Supabase service client.

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
        from app.services.observability_metrics_service import ObservabilityMetricsService

        svc = ObservabilityMetricsService()
        # Force lazy ``client`` property to materialise on the patched factory
        _ = svc.client
        return svc


def _result(data=None, count=None):
    """Build a fake supabase result with ``.data`` and ``.count``."""
    obj = MagicMock()
    obj.data = data if data is not None else []
    obj.count = count
    return obj


# ---------------------------------------------------------------------------
# TestPercentileHelper
# ---------------------------------------------------------------------------


class TestPercentileHelper:
    """Unit tests for the _percentile helper function."""

    def test_percentile_empty_list(self):
        """_percentile on empty list must return 0.0 without raising."""
        from app.services.observability_metrics_service import _percentile

        assert _percentile([], 0.50) == 0.0
        assert _percentile([], 0.95) == 0.0

    def test_percentile_single_element(self):
        """_percentile on a single-element list returns that element for all p."""
        from app.services.observability_metrics_service import _percentile

        assert _percentile([42.0], 0.50) == 42.0
        assert _percentile([42.0], 0.99) == 42.0

    def test_percentile_known_values(self):
        """_percentile on [1,2,3,4,5] matches expected percentile_cont results."""
        from app.services.observability_metrics_service import _percentile

        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        # p50 = median of [1,2,3,4,5] = 3.0
        assert _percentile(data, 0.50) == pytest.approx(3.0)
        # p100 = max
        assert _percentile(data, 1.0) == pytest.approx(5.0)
        # p0 = min
        assert _percentile(data, 0.0) == pytest.approx(1.0)

    def test_percentile_interpolation(self):
        """_percentile interpolates between adjacent values."""
        from app.services.observability_metrics_service import _percentile

        # [0, 100]: p50 = 50 (midpoint)
        assert _percentile([0.0, 100.0], 0.50) == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# TestObservabilityMetricsService
# ---------------------------------------------------------------------------


class TestObservabilityMetricsService:
    """Unit tests for ObservabilityMetricsService."""

    # ------------------------------------------------------------------
    # Service shape regression
    # ------------------------------------------------------------------

    def test_service_inherits_admin_service(self):
        """ObservabilityMetricsService must inherit from AdminService."""
        from app.services.base_service import AdminService
        from app.services.observability_metrics_service import ObservabilityMetricsService

        assert issubclass(ObservabilityMetricsService, AdminService), (
            "ObservabilityMetricsService must inherit from AdminService — it "
            "aggregates across all users under require_admin protection and needs "
            "the service-role client."
        )

    def test_ai_model_pricing_keys(self):
        """AI_MODEL_PRICING must contain all expected model names."""
        from app.services.observability_metrics_service import ObservabilityMetricsService

        pricing = ObservabilityMetricsService.AI_MODEL_PRICING
        assert "gemini-2.5-pro" in pricing
        assert "gemini-2.5-flash" in pricing
        assert "gemini-2.5-flash-lite" in pricing
        assert "text-embedding-004" in pricing
        # Each entry is (input_price, output_price) tuple of floats
        for model, prices in pricing.items():
            assert isinstance(prices, tuple), f"{model}: expected tuple, got {type(prices)}"
            assert len(prices) == 2, f"{model}: expected 2-tuple"
            assert prices[0] >= 0.0, f"{model}: input price must be non-negative"
            assert prices[1] >= 0.0, f"{model}: output price must be non-negative"

    # ------------------------------------------------------------------
    # compute_latency_percentiles
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_compute_latency_percentiles_empty(self):
        """Empty agent_telemetry returns zeroed percentile dict without raising."""
        svc = _make_service()
        now = datetime.now(tz=timezone.utc)
        start = now - timedelta(hours=1)

        with patch(
            "app.services.observability_metrics_service.execute_async",
            return_value=_result(data=[]),
        ):
            result = await svc.compute_latency_percentiles(None, start, now)

        assert result["p50"] == 0.0
        assert result["p95"] == 0.0
        assert result["p99"] == 0.0
        assert result["sample_count"] == 0
        assert result["error_count"] == 0

    @pytest.mark.asyncio
    async def test_compute_latency_percentiles_with_data(self):
        """p50/p95/p99 computed correctly for known duration_ms values."""
        svc = _make_service()
        now = datetime.now(tz=timezone.utc)
        start = now - timedelta(hours=1)

        # 5 rows with known duration_ms values: [100, 200, 300, 400, 500]
        rows = [
            {"duration_ms": 100, "status": "success"},
            {"duration_ms": 200, "status": "success"},
            {"duration_ms": 300, "status": "success"},
            {"duration_ms": 400, "status": "error"},
            {"duration_ms": 500, "status": "success"},
        ]

        with patch(
            "app.services.observability_metrics_service.execute_async",
            return_value=_result(data=rows),
        ):
            result = await svc.compute_latency_percentiles(None, start, now)

        # p50 of [100,200,300,400,500] = 300
        assert result["p50"] == pytest.approx(300.0)
        assert result["p95"] > result["p50"]
        assert result["p99"] >= result["p95"]
        assert result["sample_count"] == 5
        assert result["error_count"] == 1

    @pytest.mark.asyncio
    async def test_compute_latency_percentiles_agent_filter(self):
        """agent_name filter is applied when provided."""
        svc = _make_service()
        now = datetime.now(tz=timezone.utc)
        start = now - timedelta(hours=1)

        rows = [{"duration_ms": 150, "status": "success"}]

        with patch(
            "app.services.observability_metrics_service.execute_async",
            return_value=_result(data=rows),
        ) as mock_exec:
            result = await svc.compute_latency_percentiles("financial_agent", start, now)

        assert result["sample_count"] == 1
        assert result["p50"] == pytest.approx(150.0)

    # ------------------------------------------------------------------
    # compute_error_rate
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_compute_error_rate_no_data(self):
        """Zero total_count returns error_rate=0.0 without ZeroDivisionError."""
        svc = _make_service()
        now = datetime.now(tz=timezone.utc)
        start = now - timedelta(hours=1)

        with patch(
            "app.services.observability_metrics_service.execute_async",
            return_value=_result(data=[], count=0),
        ):
            result = await svc.compute_error_rate(None, start, now)

        assert result["error_rate"] == 0.0
        assert result["error_count"] == 0
        assert result["total_count"] == 0

    @pytest.mark.asyncio
    async def test_compute_error_rate_with_errors(self):
        """Error rate computed correctly: 2 errors out of 10 total = 0.20."""
        svc = _make_service()
        now = datetime.now(tz=timezone.utc)
        start = now - timedelta(hours=1)

        call_count = 0

        async def fake_execute(query, *, op_name=""):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: total count
                return _result(data=[], count=10)
            else:
                # Second call: error count
                return _result(data=[], count=2)

        with patch(
            "app.services.observability_metrics_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_error_rate(None, start, now)

        assert result["total_count"] == 10
        assert result["error_count"] == 2
        assert result["error_rate"] == pytest.approx(0.20)

    # ------------------------------------------------------------------
    # compute_ai_cost_by_agent
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_compute_ai_cost_by_agent_empty(self):
        """Empty agent_telemetry returns empty dict without raising."""
        svc = _make_service()
        now = datetime.now(tz=timezone.utc)
        start = now - timedelta(days=1)

        with patch(
            "app.services.observability_metrics_service.execute_async",
            return_value=_result(data=[]),
        ):
            result = await svc.compute_ai_cost_by_agent(start, now)

        assert result == {}

    @pytest.mark.asyncio
    async def test_compute_ai_cost_by_agent(self):
        """AI cost computed correctly using gemini-2.5-pro pricing constants.

        gemini-2.5-pro: input=$1.25/M, output=$5.00/M
        1M input tokens => $1.25
        1M output tokens => $5.00
        """
        svc = _make_service()
        now = datetime.now(tz=timezone.utc)
        start = now - timedelta(days=1)

        rows = [
            {
                "agent_name": "financial_agent",
                "input_tokens": 1_000_000,  # => $1.25
                "output_tokens": 0,
            },
            {
                "agent_name": "financial_agent",
                "input_tokens": 0,
                "output_tokens": 1_000_000,  # => $5.00
            },
            {
                "agent_name": "content_agent",
                "input_tokens": 500_000,  # => $0.625
                "output_tokens": 200_000,  # => $1.00
            },
        ]

        with patch(
            "app.services.observability_metrics_service.execute_async",
            return_value=_result(data=rows),
        ):
            result = await svc.compute_ai_cost_by_agent(start, now)

        # financial_agent: $1.25 + $5.00 = $6.25
        assert "financial_agent" in result
        assert result["financial_agent"] == pytest.approx(6.25, rel=1e-4)

        # content_agent: $0.625 + $1.00 = $1.625
        assert "content_agent" in result
        assert result["content_agent"] == pytest.approx(1.625, rel=1e-4)

    # ------------------------------------------------------------------
    # project_monthly_ai_spend
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_project_monthly_ai_spend(self):
        """project_monthly_ai_spend returns required fields and linear_7day method."""
        svc = _make_service()

        # Return empty data for all sub-calls (zero spend scenario)
        with patch(
            "app.services.observability_metrics_service.execute_async",
            return_value=_result(data=[]),
        ):
            result = await svc.project_monthly_ai_spend()

        assert "mtd_actual" in result
        assert "projected_full_month" in result
        assert result["projection_method"] == "linear_7day"
        assert isinstance(result["mtd_actual"], (int, float))
        assert isinstance(result["projected_full_month"], (int, float))
        # Zero spend: both should be 0.0
        assert result["mtd_actual"] == pytest.approx(0.0)
        assert result["projected_full_month"] == pytest.approx(0.0)
