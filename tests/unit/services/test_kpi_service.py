# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for KpiService — per-persona KPI computation and empty-data edge cases."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = "test-user-123"


def _make_service():
    """Return a KpiService instance with a mocked Supabase client."""
    with patch("app.services.kpi_service.get_service_client", return_value=MagicMock()):
        from app.services.kpi_service import KpiService

        svc = KpiService()
    return svc


# ---------------------------------------------------------------------------
# Structure tests — each persona returns exactly 3 KPIs with correct labels
# ---------------------------------------------------------------------------


class TestSolopreneurKpis:
    """Solopreneur persona returns Cash Collected, Weekly Pipeline, Content Consistency."""

    @pytest.mark.asyncio
    async def test_returns_three_kpis(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="solopreneur")
        assert result["persona"] == "solopreneur"
        assert len(result["kpis"]) == 3

    @pytest.mark.asyncio
    async def test_correct_labels(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="solopreneur")
        labels = [k["label"] for k in result["kpis"]]
        assert labels == ["Cash Collected", "Weekly Pipeline", "Content Consistency"]

    @pytest.mark.asyncio
    async def test_kpi_items_have_required_keys(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="solopreneur")
        for kpi in result["kpis"]:
            assert "label" in kpi
            assert "value" in kpi
            assert "unit" in kpi
            assert isinstance(kpi["label"], str)
            assert isinstance(kpi["value"], str)
            assert isinstance(kpi["unit"], str)

    @pytest.mark.asyncio
    async def test_empty_data_no_exception(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="solopreneur")
        # values should be safe defaults
        for kpi in result["kpis"]:
            assert kpi["value"] is not None

    @pytest.mark.asyncio
    async def test_cash_collected_with_paid_order(self):
        svc = _make_service()
        call_count = 0

        async def fake_execute(query, *, op_name=""):
            nonlocal call_count
            call_count += 1
            # First call: invoices query, return a paid invoice
            if call_count == 1:
                return MagicMock(data=[{"order_id": "ord-1", "status": "paid"}])
            # Second call: orders query for sum
            return MagicMock(data=[{"total_amount": 5000.0}])

        with patch("app.services.kpi_service.execute_async", side_effect=fake_execute):
            result = await svc.compute_kpis(user_id=USER_ID, persona="solopreneur")

        cash_kpi = next(k for k in result["kpis"] if k["label"] == "Cash Collected")
        assert cash_kpi["unit"] == "currency"
        assert "$" in cash_kpi["value"]


class TestStartupKpis:
    """Startup persona returns MRR Growth, Activation & Conversion, Experiment Velocity."""

    @pytest.mark.asyncio
    async def test_returns_three_kpis(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="startup")
        assert result["persona"] == "startup"
        assert len(result["kpis"]) == 3

    @pytest.mark.asyncio
    async def test_correct_labels(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="startup")
        labels = [k["label"] for k in result["kpis"]]
        assert labels == ["MRR Growth", "Activation & Conversion", "Experiment Velocity"]

    @pytest.mark.asyncio
    async def test_empty_data_no_exception(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="startup")
        for kpi in result["kpis"]:
            assert kpi["value"] is not None

    @pytest.mark.asyncio
    async def test_mrr_growth_unit_is_percent(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="startup")
        mrr_kpi = next(k for k in result["kpis"] if k["label"] == "MRR Growth")
        assert mrr_kpi["unit"] == "percent"


class TestSmeKpis:
    """SME persona returns Department Performance, Process Cycle Time, Margin & Compliance."""

    @pytest.mark.asyncio
    async def test_returns_three_kpis(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="sme")
        assert result["persona"] == "sme"
        assert len(result["kpis"]) == 3

    @pytest.mark.asyncio
    async def test_correct_labels(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="sme")
        labels = [k["label"] for k in result["kpis"]]
        assert labels == [
            "Department Performance",
            "Process Cycle Time",
            "Margin & Compliance",
        ]

    @pytest.mark.asyncio
    async def test_empty_data_no_exception(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="sme")
        for kpi in result["kpis"]:
            assert kpi["value"] is not None

    @pytest.mark.asyncio
    async def test_department_performance_unit(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="sme")
        dept_kpi = next(k for k in result["kpis"] if k["label"] == "Department Performance")
        assert dept_kpi["unit"] == "percent"


class TestEnterpriseKpis:
    """Enterprise persona returns Portfolio Health, Risk & Control Coverage, Reporting Quality."""

    @pytest.mark.asyncio
    async def test_returns_three_kpis(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="enterprise")
        assert result["persona"] == "enterprise"
        assert len(result["kpis"]) == 3

    @pytest.mark.asyncio
    async def test_correct_labels(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="enterprise")
        labels = [k["label"] for k in result["kpis"]]
        assert labels == [
            "Portfolio Health",
            "Risk & Control Coverage",
            "Reporting Quality",
        ]

    @pytest.mark.asyncio
    async def test_empty_data_no_exception(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="enterprise")
        for kpi in result["kpis"]:
            assert kpi["value"] is not None

    @pytest.mark.asyncio
    async def test_reporting_quality_unit(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="enterprise")
        rq_kpi = next(k for k in result["kpis"] if k["label"] == "Reporting Quality")
        assert rq_kpi["unit"] == "reports"


class TestUnknownPersonaFallback:
    """Unknown persona falls back to solopreneur KPIs."""

    @pytest.mark.asyncio
    async def test_unknown_persona_fallback(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="unknown_persona")
        labels = [k["label"] for k in result["kpis"]]
        assert labels == ["Cash Collected", "Weekly Pipeline", "Content Consistency"]

    @pytest.mark.asyncio
    async def test_none_persona_fallback(self):
        svc = _make_service()
        with patch("app.services.kpi_service.execute_async", new_callable=AsyncMock) as m:
            m.return_value = MagicMock(data=[])
            result = await svc.compute_kpis(user_id=USER_ID, persona="")
        labels = [k["label"] for k in result["kpis"]]
        assert labels == ["Cash Collected", "Weekly Pipeline", "Content Consistency"]


class TestErrorIsolation:
    """Execute_async failures are caught and return safe defaults."""

    @pytest.mark.asyncio
    async def test_execute_async_exception_returns_safe_defaults(self):
        svc = _make_service()
        with patch(
            "app.services.kpi_service.execute_async",
            side_effect=Exception("DB down"),
        ):
            result = await svc.compute_kpis(user_id=USER_ID, persona="solopreneur")
        assert len(result["kpis"]) == 3
        for kpi in result["kpis"]:
            assert kpi["value"] is not None

    @pytest.mark.asyncio
    async def test_all_personas_safe_on_exception(self):
        svc = _make_service()
        personas = ["solopreneur", "startup", "sme", "enterprise"]
        for persona in personas:
            with patch(
                "app.services.kpi_service.execute_async",
                side_effect=Exception("DB down"),
            ):
                result = await svc.compute_kpis(user_id=USER_ID, persona=persona)
            assert len(result["kpis"]) == 3, f"{persona} should return 3 KPIs on error"
