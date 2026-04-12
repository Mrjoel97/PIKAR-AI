# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for WorkflowBottleneckService.

Tests cover:
- Step-level duration stats aggregation (avg, max, count, failure_rate)
- Bottleneck flagging thresholds (> 24h slow, > 20% failure, > 48h approval wait)
- Plain-English recommendation generation with specific numbers
- get_workflow_health_summary aggregation (completion rate, avg execution time, top 3)
- Graceful empty result when user has no workflow executions
- Steps without timestamps are skipped in duration calculations
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

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
def service():
    """Return a WorkflowBottleneckService instance."""
    from app.services.workflow_bottleneck_service import WorkflowBottleneckService

    return WorkflowBottleneckService()


def _make_dt(hours_ago: float = 0) -> str:
    """Return ISO-format UTC timestamp offset by hours_ago from now."""
    return (
        datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago)
    ).isoformat()


def _make_step(
    step_name: str,
    status: str = "completed",
    duration_hours: float | None = 2.0,
    execution_id: str = "exec-1",
) -> dict:
    """Build a synthetic workflow_steps row."""
    now = datetime.now(tz=timezone.utc)
    if duration_hours is not None:
        started_at = (now - timedelta(hours=duration_hours)).isoformat()
        completed_at = now.isoformat()
    else:
        started_at = None
        completed_at = None
    return {
        "id": f"step-{step_name}-{execution_id}",
        "execution_id": execution_id,
        "step_name": step_name,
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
    }


def _make_execution(
    execution_id: str = "exec-1",
    status: str = "completed",
    duration_hours: float | None = 4.0,
) -> dict:
    """Build a synthetic workflow_executions row."""
    now = datetime.now(tz=timezone.utc)
    created_at = (now - timedelta(hours=duration_hours or 0)).isoformat()
    completed_at = now.isoformat() if status == "completed" else None
    return {
        "id": execution_id,
        "user_id": "user-123",
        "status": status,
        "created_at": created_at,
        "completed_at": completed_at,
    }


# ---------------------------------------------------------------------------
# Tests: analyze_bottlenecks — step-level aggregation
# ---------------------------------------------------------------------------


class TestAnalyzeBottlenecks:
    """Tests for the primary analyze_bottlenecks method."""

    @pytest.mark.asyncio()
    async def test_returns_step_level_stats(self, service):
        """analyze_bottlenecks returns avg_duration_hours, max_duration_hours,
        execution_count, and failure_rate per step_name."""
        steps = [
            _make_step("Document Review", status="completed", duration_hours=2.0),
            _make_step(
                "Document Review",
                status="completed",
                duration_hours=4.0,
                execution_id="exec-2",
            ),
            _make_step("Approval", status="completed", duration_hours=6.0),
        ]
        executions = [
            _make_execution("exec-1"),
            _make_execution("exec-2"),
        ]

        with patch(
            "app.services.workflow_bottleneck_service.WorkflowBottleneckService._fetch_steps_and_executions",
            new_callable=AsyncMock,
            return_value=(steps, executions),
        ):
            result = await service.analyze_bottlenecks("user-123")

        assert "step_stats" in result
        step_stats = {s["step_name"]: s for s in result["step_stats"]}
        assert "Document Review" in step_stats
        dr = step_stats["Document Review"]
        assert dr["avg_duration_hours"] == pytest.approx(3.0, abs=0.01)
        assert dr["max_duration_hours"] == pytest.approx(4.0, abs=0.01)
        assert dr["execution_count"] == 2
        assert dr["failure_rate"] == pytest.approx(0.0, abs=0.01)

    @pytest.mark.asyncio()
    async def test_flags_slow_steps_over_24h(self, service):
        """Steps with avg_duration_hours > 24 are flagged as bottlenecks."""
        steps = [
            _make_step("Content Approval", status="completed", duration_hours=72.0),
        ]
        executions = [_make_execution("exec-1")]

        with patch(
            "app.services.workflow_bottleneck_service.WorkflowBottleneckService._fetch_steps_and_executions",
            new_callable=AsyncMock,
            return_value=(steps, executions),
        ):
            result = await service.analyze_bottlenecks("user-123")

        assert result["bottleneck_count"] >= 1
        step_stats = {s["step_name"]: s for s in result["step_stats"]}
        assert step_stats["Content Approval"]["is_bottleneck"] is True

    @pytest.mark.asyncio()
    async def test_does_not_flag_fast_steps(self, service):
        """Steps with avg_duration_hours <= 24 are not flagged as bottlenecks (no other trigger)."""
        steps = [
            _make_step("Quick Check", status="completed", duration_hours=1.0),
        ]
        executions = [_make_execution("exec-1")]

        with patch(
            "app.services.workflow_bottleneck_service.WorkflowBottleneckService._fetch_steps_and_executions",
            new_callable=AsyncMock,
            return_value=(steps, executions),
        ):
            result = await service.analyze_bottlenecks("user-123")

        step_stats = {s["step_name"]: s for s in result["step_stats"]}
        assert step_stats["Quick Check"]["is_bottleneck"] is False

    @pytest.mark.asyncio()
    async def test_flags_high_failure_rate_steps(self, service):
        """Steps with failure_rate > 0.2 are flagged as bottlenecks."""
        steps = [
            _make_step("API Call", status="failed", duration_hours=0.5),
            _make_step(
                "API Call", status="failed", duration_hours=0.5, execution_id="exec-2"
            ),
            _make_step(
                "API Call",
                status="completed",
                duration_hours=0.5,
                execution_id="exec-3",
            ),
        ]
        executions = [
            _make_execution("exec-1"),
            _make_execution("exec-2"),
            _make_execution("exec-3"),
        ]

        with patch(
            "app.services.workflow_bottleneck_service.WorkflowBottleneckService._fetch_steps_and_executions",
            new_callable=AsyncMock,
            return_value=(steps, executions),
        ):
            result = await service.analyze_bottlenecks("user-123")

        step_stats = {s["step_name"]: s for s in result["step_stats"]}
        api_stat = step_stats["API Call"]
        # failure_rate = 2/3 ~ 0.667 > 0.2
        assert api_stat["failure_rate"] == pytest.approx(2 / 3, abs=0.01)
        assert api_stat["is_bottleneck"] is True

    @pytest.mark.asyncio()
    async def test_flags_approval_blocked_steps_over_48h(self, service):
        """Steps with status=waiting_approval and avg > 48h are flagged."""
        steps = [
            _make_step(
                "Manager Sign-off",
                status="waiting_approval",
                duration_hours=60.0,
            ),
        ]
        executions = [_make_execution("exec-1")]

        with patch(
            "app.services.workflow_bottleneck_service.WorkflowBottleneckService._fetch_steps_and_executions",
            new_callable=AsyncMock,
            return_value=(steps, executions),
        ):
            result = await service.analyze_bottlenecks("user-123")

        step_stats = {s["step_name"]: s for s in result["step_stats"]}
        assert step_stats["Manager Sign-off"]["is_bottleneck"] is True

    @pytest.mark.asyncio()
    async def test_empty_executions_returns_gracefully(self, service):
        """When user has no executions, analyze_bottlenecks returns empty but valid result."""
        with patch(
            "app.services.workflow_bottleneck_service.WorkflowBottleneckService._fetch_steps_and_executions",
            new_callable=AsyncMock,
            return_value=([], []),
        ):
            result = await service.analyze_bottlenecks("user-123")

        assert result["step_stats"] == []
        assert result["bottleneck_count"] == 0
        assert result["recommendations"] == []

    @pytest.mark.asyncio()
    async def test_steps_without_timestamps_skipped(self, service):
        """Steps where started_at or completed_at is None are not included in duration calc."""
        steps = [
            _make_step(
                "Pending Step", status="pending", duration_hours=None
            ),  # no timestamps
            _make_step(
                "Done Step", status="completed", duration_hours=3.0
            ),  # has timestamps
        ]
        executions = [_make_execution("exec-1")]

        with patch(
            "app.services.workflow_bottleneck_service.WorkflowBottleneckService._fetch_steps_and_executions",
            new_callable=AsyncMock,
            return_value=(steps, executions),
        ):
            result = await service.analyze_bottlenecks("user-123")

        step_stats = {s["step_name"]: s for s in result["step_stats"]}
        # Pending Step has no duration -> execution_count may still be 1 but avg=0 or excluded
        # Done Step should be present with duration 3.0
        assert "Done Step" in step_stats
        assert step_stats["Done Step"]["avg_duration_hours"] == pytest.approx(
            3.0, abs=0.01
        )


# ---------------------------------------------------------------------------
# Tests: _generate_recommendations — plain-English messages
# ---------------------------------------------------------------------------


class TestGenerateRecommendations:
    """Tests for the _generate_recommendations private method."""

    def test_slow_step_recommendation_includes_days_and_name(self, service):
        """Slow step (avg > 24h) generates message with step name and day count."""
        step_stats = [
            {
                "step_name": "Content Approval",
                "avg_duration_hours": 76.8,  # 3.2 days
                "max_duration_hours": 120.0,
                "execution_count": 5,
                "failure_count": 0,
                "failure_rate": 0.0,
                "approval_wait_count": 0,
                "approval_wait_rate": 0.0,
                "is_bottleneck": True,
            }
        ]
        recs = service._generate_recommendations(step_stats)
        assert len(recs) >= 1
        rec = recs[0]
        assert "Content Approval" in rec["message"]
        assert "3.2" in rec["message"] or "3.20" in rec["message"]

    def test_failing_step_recommendation_includes_percent(self, service):
        """Failing step (failure_rate > 0.2) generates message with percentage."""
        step_stats = [
            {
                "step_name": "Data Sync",
                "avg_duration_hours": 0.5,
                "max_duration_hours": 1.0,
                "execution_count": 10,
                "failure_count": 4,
                "failure_rate": 0.4,
                "approval_wait_count": 0,
                "approval_wait_rate": 0.0,
                "is_bottleneck": True,
            }
        ]
        recs = service._generate_recommendations(step_stats)
        assert len(recs) >= 1
        rec_messages = [r["message"] for r in recs]
        assert any("Data Sync" in m for m in rec_messages)
        assert any("40%" in m or "40" in m for m in rec_messages)

    def test_approval_blocked_recommendation_mentions_approval(self, service):
        """Approval-blocked step generates message mentioning approval."""
        step_stats = [
            {
                "step_name": "Manager Sign-off",
                "avg_duration_hours": 72.0,
                "max_duration_hours": 96.0,
                "execution_count": 3,
                "failure_count": 0,
                "failure_rate": 0.0,
                "approval_wait_count": 3,
                "approval_wait_rate": 1.0,
                "is_bottleneck": True,
            }
        ]
        recs = service._generate_recommendations(step_stats)
        assert len(recs) >= 1
        rec_messages = [r["message"] for r in recs]
        assert any("Manager Sign-off" in m for m in rec_messages)
        assert any("approval" in m.lower() for m in rec_messages)

    def test_outlier_step_recommendation_for_very_long_max(self, service):
        """Step with max_duration_hours > 7*24 generates outlier recommendation."""
        step_stats = [
            {
                "step_name": "Background Check",
                "avg_duration_hours": 12.0,
                "max_duration_hours": 200.0,  # > 168h (1 week)
                "execution_count": 5,
                "failure_count": 0,
                "failure_rate": 0.0,
                "approval_wait_count": 0,
                "approval_wait_rate": 0.0,
                "is_bottleneck": True,
            }
        ]
        recs = service._generate_recommendations(step_stats)
        assert any("Background Check" in r["message"] for r in recs)

    def test_recommendations_have_required_fields(self, service):
        """Each recommendation has step_name, type, severity, message, avg_duration_hours."""
        step_stats = [
            {
                "step_name": "Slow Step",
                "avg_duration_hours": 50.0,
                "max_duration_hours": 60.0,
                "execution_count": 2,
                "failure_count": 0,
                "failure_rate": 0.0,
                "approval_wait_count": 0,
                "approval_wait_rate": 0.0,
                "is_bottleneck": True,
            }
        ]
        recs = service._generate_recommendations(step_stats)
        assert len(recs) >= 1
        for rec in recs:
            assert "step_name" in rec
            assert "type" in rec
            assert "severity" in rec
            assert "message" in rec
            assert "avg_duration_hours" in rec
            assert rec["severity"] in ("high", "medium")
            assert rec["type"] in ("slow", "failing", "approval_blocked", "outlier")

    def test_high_severity_sorted_first(self, service):
        """Recommendations are sorted: high severity before medium."""
        step_stats = [
            {
                "step_name": "Medium Step",
                "avg_duration_hours": 30.0,
                "max_duration_hours": 40.0,
                "execution_count": 2,
                "failure_count": 0,
                "failure_rate": 0.0,
                "approval_wait_count": 0,
                "approval_wait_rate": 0.0,
                "is_bottleneck": True,
            },
            {
                "step_name": "Failing Step",
                "avg_duration_hours": 1.0,
                "max_duration_hours": 2.0,
                "execution_count": 5,
                "failure_count": 3,
                "failure_rate": 0.6,
                "approval_wait_count": 0,
                "approval_wait_rate": 0.0,
                "is_bottleneck": True,
            },
        ]
        recs = service._generate_recommendations(step_stats)
        assert len(recs) >= 2
        # High severity items should come before medium
        severities = [r["severity"] for r in recs]
        high_indices = [i for i, s in enumerate(severities) if s == "high"]
        medium_indices = [i for i, s in enumerate(severities) if s == "medium"]
        if high_indices and medium_indices:
            assert max(high_indices) < min(medium_indices)

    def test_no_recommendations_for_healthy_steps(self, service):
        """Steps that are fast, rarely failing, and not approval-blocked get no recommendations."""
        step_stats = [
            {
                "step_name": "Fast Step",
                "avg_duration_hours": 1.0,
                "max_duration_hours": 2.0,
                "execution_count": 10,
                "failure_count": 1,
                "failure_rate": 0.1,
                "approval_wait_count": 0,
                "approval_wait_rate": 0.0,
                "is_bottleneck": False,
            }
        ]
        recs = service._generate_recommendations(step_stats)
        assert recs == []


# ---------------------------------------------------------------------------
# Tests: get_workflow_health_summary
# ---------------------------------------------------------------------------


class TestGetWorkflowHealthSummary:
    """Tests for the get_workflow_health_summary method."""

    @pytest.mark.asyncio()
    async def test_returns_completion_rate_and_avg_execution_time(self, service):
        """Health summary includes total_executions, completion_rate, avg_execution_hours."""
        steps = [
            _make_step("Step A", duration_hours=2.0),
        ]
        executions = [
            _make_execution("exec-1", status="completed", duration_hours=4.0),
            _make_execution("exec-2", status="completed", duration_hours=6.0),
            _make_execution("exec-3", status="failed", duration_hours=1.0),
        ]

        with patch(
            "app.services.workflow_bottleneck_service.WorkflowBottleneckService._fetch_steps_and_executions",
            new_callable=AsyncMock,
            return_value=(steps, executions),
        ):
            result = await service.get_workflow_health_summary("user-123")

        assert result["total_executions"] == 3
        assert result["completion_rate"] == pytest.approx(2 / 3, abs=0.01)
        # avg execution hours for completed: (4 + 6) / 2 = 5.0
        assert result["avg_execution_hours"] == pytest.approx(5.0, abs=0.1)

    @pytest.mark.asyncio()
    async def test_top_bottlenecks_limited_to_three(self, service):
        """Health summary returns at most 3 top_bottlenecks."""
        # Create 4 slow steps
        steps = [
            _make_step("Step A", duration_hours=48.0),
            _make_step("Step B", duration_hours=36.0, execution_id="exec-2"),
            _make_step("Step C", duration_hours=30.0, execution_id="exec-3"),
            _make_step("Step D", duration_hours=26.0, execution_id="exec-4"),
        ]
        executions = [
            _make_execution("exec-1"),
            _make_execution("exec-2"),
            _make_execution("exec-3"),
            _make_execution("exec-4"),
        ]

        with patch(
            "app.services.workflow_bottleneck_service.WorkflowBottleneckService._fetch_steps_and_executions",
            new_callable=AsyncMock,
            return_value=(steps, executions),
        ):
            result = await service.get_workflow_health_summary("user-123")

        assert len(result["top_bottlenecks"]) <= 3

    @pytest.mark.asyncio()
    async def test_includes_period_days(self, service):
        """Health summary includes period_days field."""
        with patch(
            "app.services.workflow_bottleneck_service.WorkflowBottleneckService._fetch_steps_and_executions",
            new_callable=AsyncMock,
            return_value=([], []),
        ):
            result = await service.get_workflow_health_summary("user-123", days=14)

        assert result["period_days"] == 14

    @pytest.mark.asyncio()
    async def test_empty_returns_zero_stats(self, service):
        """Empty executions returns zero completion_rate and empty top_bottlenecks."""
        with patch(
            "app.services.workflow_bottleneck_service.WorkflowBottleneckService._fetch_steps_and_executions",
            new_callable=AsyncMock,
            return_value=([], []),
        ):
            result = await service.get_workflow_health_summary("user-123")

        assert result["total_executions"] == 0
        assert result["completion_rate"] == 0.0
        assert result["top_bottlenecks"] == []


# ---------------------------------------------------------------------------
# Tests: module-level convenience function
# ---------------------------------------------------------------------------


class TestModuleLevelConvenienceFunction:
    """analyze_bottlenecks module-level function delegates to service."""

    @pytest.mark.asyncio()
    async def test_module_function_returns_same_structure(self):
        """Module-level analyze_bottlenecks returns same keys as service method."""
        with patch(
            "app.services.workflow_bottleneck_service.WorkflowBottleneckService._fetch_steps_and_executions",
            new_callable=AsyncMock,
            return_value=([], []),
        ):
            from app.services.workflow_bottleneck_service import (
                analyze_bottlenecks,
            )

            result = await analyze_bottlenecks("user-123")

        assert "step_stats" in result
        assert "bottleneck_count" in result
        assert "recommendations" in result
