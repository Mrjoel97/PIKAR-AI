# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for KpiService — verifies 4 KPIs per persona tier with subtitles."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.kpi_service import KpiService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = {"label", "value", "unit", "subtitle"}


def _make_service() -> KpiService:
    """Return a KpiService with a mocked Supabase client."""
    with patch("app.services.kpi_service.get_service_client", return_value=MagicMock()):
        return KpiService()


def _assert_kpis(kpis: list[dict[str, Any]], expected_labels: list[str]) -> None:
    """Assert that *kpis* has exactly 4 items matching *expected_labels*."""
    assert len(kpis) == 4, f"Expected 4 KPIs, got {len(kpis)}: {[k['label'] for k in kpis]}"
    actual_labels = [k["label"] for k in kpis]
    assert actual_labels == expected_labels, f"Label mismatch: {actual_labels} != {expected_labels}"
    for kpi in kpis:
        missing = _REQUIRED_FIELDS - set(kpi.keys())
        assert not missing, f"KPI {kpi.get('label')} missing fields: {missing}"
        assert kpi["subtitle"], f"KPI {kpi.get('label')} has empty subtitle"


# ---------------------------------------------------------------------------
# Test 1 – Solopreneur: 4 KPIs, zero state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_solopreneur_returns_4_kpis_zero_state() -> None:
    """Solopreneur tier returns exactly 4 KPIs with $0/0 zero-state values."""
    svc = _make_service()

    async def empty_safe_rows(query: Any) -> list[dict[str, Any]]:
        return []

    svc._safe_rows = empty_safe_rows  # type: ignore[method-assign]
    result = await svc.compute_kpis(user_id="user-1", persona="solopreneur")
    kpis = result["kpis"]
    _assert_kpis(
        kpis,
        ["Revenue", "Weekly Pipeline", "Content Created", "Connected Integrations"],
    )
    assert kpis[0]["value"] == "$0"
    assert kpis[1]["value"] == "$0"
    assert kpis[2]["value"] == "0"
    assert kpis[3]["value"] == "0"


@pytest.mark.asyncio
async def test_solopreneur_returns_4_kpis_with_data() -> None:
    """Solopreneur tier computes correct values from populated data."""
    svc = _make_service()
    call_count = 0

    async def populated_safe_rows(query: Any) -> list[dict[str, Any]]:  # noqa: ARG001
        nonlocal call_count
        call_count += 1
        # Alternate return sets per call order:
        # 1=invoices (2 paid), 2=orders (total_amount), 3=pipeline contacts,
        # 4=content_bundles, 5=user_integrations
        if call_count == 1:
            return [{"order_id": "ord-1"}, {"order_id": "ord-2"}]
        if call_count == 2:
            return [{"total_amount": "500"}, {"total_amount": "250"}]
        if call_count == 3:
            return [{"estimated_value": "1000"}, {"estimated_value": "2000"}]
        if call_count == 4:
            return [{"id": "c1"}, {"id": "c2"}, {"id": "c3"}]
        if call_count == 5:
            return [{"id": "i1"}, {"id": "i2"}]
        return []

    svc._safe_rows = populated_safe_rows  # type: ignore[method-assign]
    result = await svc.compute_kpis(user_id="user-1", persona="solopreneur")
    kpis = result["kpis"]
    assert len(kpis) == 4
    assert kpis[0]["value"] == "$750"
    assert kpis[1]["value"] == "$3,000"
    assert kpis[2]["value"] == "3"
    assert kpis[3]["value"] == "2"


# ---------------------------------------------------------------------------
# Test 2 – Startup: 4 KPIs, zero state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_startup_returns_4_kpis_zero_state() -> None:
    """Startup tier returns exactly 4 KPIs with zero-state values."""
    svc = _make_service()

    async def empty_safe_rows(query: Any) -> list[dict[str, Any]]:
        return []

    svc._safe_rows = empty_safe_rows  # type: ignore[method-assign]
    result = await svc.compute_kpis(user_id="user-2", persona="startup")
    kpis = result["kpis"]
    _assert_kpis(kpis, ["Revenue", "Pipeline Value", "Team Size", "Growth Rate (MoM)"])
    assert kpis[0]["value"] == "$0"
    assert kpis[1]["value"] == "$0"
    assert kpis[2]["value"] == "0"
    assert kpis[3]["value"] == "+0%"


@pytest.mark.asyncio
async def test_startup_returns_4_kpis_with_data() -> None:
    """Startup tier computes correct values from populated data."""
    svc = _make_service()
    call_count = 0

    async def populated_safe_rows(query: Any) -> list[dict[str, Any]]:  # noqa: ARG001
        nonlocal call_count
        call_count += 1
        # 1=orders this month (revenue), 2=pipeline contacts,
        # 3=workspace_members, 4=orders current month (growth), 5=orders prior month
        if call_count == 1:
            return [{"total_amount": "1000"}, {"total_amount": "500"}]
        if call_count == 2:
            return [{"estimated_value": "5000"}]
        if call_count == 3:
            return [{"id": "m1"}, {"id": "m2"}, {"id": "m3"}]
        if call_count == 4:
            return [{"total_amount": "1500"}]
        if call_count == 5:
            return [{"total_amount": "1000"}]
        return []

    svc._safe_rows = populated_safe_rows  # type: ignore[method-assign]
    result = await svc.compute_kpis(user_id="user-2", persona="startup")
    kpis = result["kpis"]
    assert len(kpis) == 4
    assert kpis[0]["value"] == "$1,500"
    assert kpis[1]["value"] == "$5,000"
    assert kpis[2]["value"] == "3"
    assert "+50%" == kpis[3]["value"]


# ---------------------------------------------------------------------------
# Test 3 – SME: 4 KPIs, zero state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sme_returns_4_kpis_zero_state() -> None:
    """SME tier returns exactly 4 KPIs with zero-state values."""
    svc = _make_service()

    async def empty_safe_rows(query: Any) -> list[dict[str, Any]]:
        return []

    svc._safe_rows = empty_safe_rows  # type: ignore[method-assign]
    result = await svc.compute_kpis(user_id="user-3", persona="sme")
    kpis = result["kpis"]
    _assert_kpis(kpis, ["Revenue", "Active Departments", "Compliance Score", "Open Tasks"])
    assert kpis[0]["value"] == "$0"
    assert kpis[1]["value"] == "0"
    assert kpis[2]["value"] == "0%"
    assert kpis[3]["value"] == "0"


@pytest.mark.asyncio
async def test_sme_returns_4_kpis_with_data() -> None:
    """SME tier computes correct values from populated data."""
    svc = _make_service()
    call_count = 0

    async def populated_safe_rows(query: Any) -> list[dict[str, Any]]:  # noqa: ARG001
        nonlocal call_count
        call_count += 1
        # 1=orders this month (revenue), 2=departments, 3=compliance_risks, 4=tasks
        if call_count == 1:
            return [{"total_amount": "2000"}]
        if call_count == 2:
            return [{"id": "d1", "status": "RUNNING"}, {"id": "d2", "status": "RUNNING"}, {"id": "d3", "status": "STOPPED"}]
        if call_count == 3:
            return [
                {"id": "r1", "status": "mitigated"},
                {"id": "r2", "status": "resolved"},
                {"id": "r3", "status": "open"},
                {"id": "r4", "status": "resolved"},
            ]
        if call_count == 4:
            return [{"id": "t1"}, {"id": "t2"}, {"id": "t3"}, {"id": "t4"}, {"id": "t5"}]
        return []

    svc._safe_rows = populated_safe_rows  # type: ignore[method-assign]
    result = await svc.compute_kpis(user_id="user-3", persona="sme")
    kpis = result["kpis"]
    assert len(kpis) == 4
    assert kpis[0]["value"] == "$2,000"
    assert kpis[1]["value"] == "2"
    assert kpis[2]["value"] == "75%"
    assert kpis[3]["value"] == "5"


# ---------------------------------------------------------------------------
# Test 4 – Enterprise: 4 KPIs, zero state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enterprise_returns_4_kpis_zero_state() -> None:
    """Enterprise tier returns exactly 4 KPIs with zero-state values."""
    svc = _make_service()

    async def empty_safe_rows(query: Any) -> list[dict[str, Any]]:
        return []

    svc._safe_rows = empty_safe_rows  # type: ignore[method-assign]
    result = await svc.compute_kpis(user_id="user-4", persona="enterprise")
    kpis = result["kpis"]
    _assert_kpis(kpis, ["Portfolio Health %", "Risk Score", "Total Revenue", "Department Count"])
    assert kpis[0]["value"] == "0%"
    assert kpis[1]["value"] == "0%"
    assert kpis[2]["value"] == "$0"
    assert kpis[3]["value"] == "0"


@pytest.mark.asyncio
async def test_enterprise_returns_4_kpis_with_data() -> None:
    """Enterprise tier computes correct values from populated data."""
    svc = _make_service()
    call_count = 0

    async def populated_safe_rows(query: Any) -> list[dict[str, Any]]:  # noqa: ARG001
        nonlocal call_count
        call_count += 1
        # 1=initiatives, 2=compliance_risks, 3=all orders (total revenue), 4=departments
        if call_count == 1:
            return [
                {"id": "i1", "status": "in_progress", "progress": 60},
                {"id": "i2", "status": "in_progress", "progress": 30},
                {"id": "i3", "status": "not_started", "progress": 0},
            ]
        if call_count == 2:
            return [
                {"id": "r1", "mitigation_plan": "Plan A"},
                {"id": "r2", "mitigation_plan": None},
                {"id": "r3", "mitigation_plan": "Plan C"},
            ]
        if call_count == 3:
            return [{"total_amount": "10000"}, {"total_amount": "5000"}]
        if call_count == 4:
            return [{"id": "d1"}, {"id": "d2"}, {"id": "d3"}, {"id": "d4"}]
        return []

    svc._safe_rows = populated_safe_rows  # type: ignore[method-assign]
    result = await svc.compute_kpis(user_id="user-4", persona="enterprise")
    kpis = result["kpis"]
    assert len(kpis) == 4
    assert kpis[0]["value"] == "33%"
    assert kpis[1]["value"] == "67%"
    assert kpis[2]["value"] == "$15,000"
    assert kpis[3]["value"] == "4"


# ---------------------------------------------------------------------------
# Test 5 – Subtitle field present for all tiers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_tiers_have_subtitle_field() -> None:
    """All KPIs across all tiers must include a non-empty subtitle."""
    svc = _make_service()

    async def empty_safe_rows(query: Any) -> list[dict[str, Any]]:
        return []

    svc._safe_rows = empty_safe_rows  # type: ignore[method-assign]

    for persona in ("solopreneur", "startup", "sme", "enterprise"):
        result = await svc.compute_kpis(user_id="user-x", persona=persona)
        for kpi in result["kpis"]:
            assert "subtitle" in kpi, f"[{persona}] KPI '{kpi.get('label')}' missing subtitle"
            assert isinstance(kpi["subtitle"], str), f"[{persona}] subtitle not a string"
            assert len(kpi["subtitle"]) > 0, f"[{persona}] KPI '{kpi.get('label')}' has empty subtitle"
