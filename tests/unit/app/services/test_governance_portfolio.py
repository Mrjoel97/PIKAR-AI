# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for GovernanceService.compute_portfolio_health enriched metrics.

Tests verify:
1. initiative_breakdown dict with counts by status
2. workflow_success_rate as percentage of completed vs total executions
3. revenue_trend with current and prior month revenue
4. Graceful degradation when no initiatives exist (score=0, empty breakdowns)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.governance_service import GovernanceService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service() -> GovernanceService:
    """Return a GovernanceService with a mocked Supabase client."""
    with patch(
        "app.services.governance_service.get_service_client",
        return_value=MagicMock(),
    ):
        return GovernanceService()


def _make_execute_async_mock(table_data: dict[str, list[dict[str, Any]]]) -> AsyncMock:
    """Return an AsyncMock for execute_async that dispatches by op_name."""

    async def _execute(query: Any, *, op_name: str) -> MagicMock:
        result = MagicMock()
        result.data = table_data.get(op_name, [])
        return result

    return AsyncMock(side_effect=_execute)


# ---------------------------------------------------------------------------
# Test 1 — initiative_breakdown by status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initiative_breakdown_by_status() -> None:
    """compute_portfolio_health returns initiative_breakdown with status counts."""
    svc = _make_service()

    table_data: dict[str, list[dict[str, Any]]] = {
        "governance.health_initiatives": [
            {"id": "1", "status": "in_progress"},
            {"id": "2", "status": "completed"},
            {"id": "3", "status": "blocked"},
            {"id": "4", "status": "not_started"},
            {"id": "5", "status": "completed"},
        ],
        "governance.health_risks": [],
        "governance.health_allocation": [
            {"id": "1", "owner_user_id": "user-a"},
            {"id": "2", "owner_user_id": None},
        ],
        "governance.health_workflow_success": [
            {"id": "w1", "status": "completed"},
            {"id": "w2", "status": "failed"},
        ],
        "governance.health_revenue_current": [{"amount": 1000}],
        "governance.health_revenue_prior": [{"amount": 800}],
    }

    with patch(
        "app.services.governance_service.execute_async",
        side_effect=_make_execute_async_mock(table_data),
    ):
        result = await svc.compute_portfolio_health(user_id="user-1")

    breakdown = result["components"]["initiative_breakdown"]
    assert breakdown["in_progress"] == 1
    assert breakdown["completed"] == 2
    assert breakdown["blocked"] == 1
    assert breakdown["not_started"] == 1
    assert breakdown["total"] == 5


# ---------------------------------------------------------------------------
# Test 2 — workflow_success_rate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_workflow_success_rate() -> None:
    """compute_portfolio_health returns workflow_success_rate as integer percentage."""
    svc = _make_service()

    table_data: dict[str, list[dict[str, Any]]] = {
        "governance.health_initiatives": [],
        "governance.health_risks": [],
        "governance.health_allocation": [],
        "governance.health_workflow_success": [
            {"id": "w1", "status": "completed"},
            {"id": "w2", "status": "completed"},
            {"id": "w3", "status": "failed"},
            {"id": "w4", "status": "pending"},
        ],
        "governance.health_revenue_current": [],
        "governance.health_revenue_prior": [],
    }

    with patch(
        "app.services.governance_service.execute_async",
        side_effect=_make_execute_async_mock(table_data),
    ):
        result = await svc.compute_portfolio_health(user_id="user-1")

    # 2 completed of 4 total = 50%
    assert result["components"]["workflow_success_rate"] == 50


# ---------------------------------------------------------------------------
# Test 3 — revenue_trend with current and prior month
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revenue_trend() -> None:
    """compute_portfolio_health returns revenue_trend with current and prior month amounts."""
    svc = _make_service()

    table_data: dict[str, list[dict[str, Any]]] = {
        "governance.health_initiatives": [],
        "governance.health_risks": [],
        "governance.health_allocation": [],
        "governance.health_workflow_success": [],
        "governance.health_revenue_current": [{"amount": 5000}, {"amount": 3000}],
        "governance.health_revenue_prior": [{"amount": 2000}],
    }

    with patch(
        "app.services.governance_service.execute_async",
        side_effect=_make_execute_async_mock(table_data),
    ):
        result = await svc.compute_portfolio_health(user_id="user-1")

    trend = result["components"]["revenue_trend"]
    assert trend["current_month"] == 8000  # 5000 + 3000
    assert trend["prior_month"] == 2000


# ---------------------------------------------------------------------------
# Test 4 — graceful degradation when no data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_graceful_degradation_no_initiatives() -> None:
    """When no initiatives exist, score is 0 with empty/zero breakdowns."""
    svc = _make_service()

    table_data: dict[str, list[dict[str, Any]]] = {
        "governance.health_initiatives": [],
        "governance.health_risks": [],
        "governance.health_allocation": [],
        "governance.health_workflow_success": [],
        "governance.health_revenue_current": [],
        "governance.health_revenue_prior": [],
    }

    with patch(
        "app.services.governance_service.execute_async",
        side_effect=_make_execute_async_mock(table_data),
    ):
        result = await svc.compute_portfolio_health(user_id="user-1")

    assert result["score"] == 0
    breakdown = result["components"]["initiative_breakdown"]
    assert breakdown["in_progress"] == 0
    assert breakdown["completed"] == 0
    assert breakdown["blocked"] == 0
    assert breakdown["not_started"] == 0
    assert breakdown["total"] == 0
    assert result["components"]["workflow_success_rate"] == 0
    assert result["components"]["revenue_trend"]["current_month"] == 0
    assert result["components"]["revenue_trend"]["prior_month"] == 0
