# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for ComplianceHealthService -- compliance health score 0-100.

Plan 66-01 / LEGAL-01. Verifies:

- compute_health_score returns 100 when user has no risks, audits, or deadlines
- compute_health_score deducts for active risks by severity
- compute_health_score deducts for overdue audits
- compute_health_score deducts for overdue compliance deadlines
- compute_health_score clamps to 0-100 range
- compute_health_score returns plain-English explanation string
- compute_health_score handles empty data gracefully
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_ENV = {
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "service-role-test-key",
    "SUPABASE_ANON_KEY": "anon-test-key",
}


def _result(data=None):
    """Build a fake supabase result with ``.data``."""
    obj = MagicMock()
    obj.data = data if data is not None else []
    return obj


def _make_service():
    """Return a ComplianceHealthService with stubbed Supabase client."""
    with patch.dict("os.environ", _FAKE_ENV, clear=False):
        from app.services.compliance_health_service import ComplianceHealthService

        return ComplianceHealthService()


# ---------------------------------------------------------------------------
# Perfect score -- no issues
# ---------------------------------------------------------------------------


class TestPerfectScore:
    """User with no risks, no overdue audits, no overdue deadlines = 100."""

    @pytest.mark.asyncio
    async def test_empty_data_returns_100(self):
        """No risks, no overdue audits, no overdue deadlines => score 100."""
        svc = _make_service()

        async def fake_execute(query, **kwargs):
            return _result(data=[])

        with patch(
            "app.services.compliance_health_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_health_score(user_id="user-1")

        assert result["score"] == 100
        assert result["factors"]["active_risks"] == 0
        assert result["factors"]["overdue_audits"] == 0
        assert result["factors"]["overdue_deadlines"] == 0
        assert isinstance(result["explanation"], str)
        assert isinstance(result["deductions"], list)
        assert len(result["deductions"]) == 0

    @pytest.mark.asyncio
    async def test_no_issues_explanation_positive(self):
        """Perfect score explanation should be congratulatory."""
        svc = _make_service()

        async def fake_execute(query, **kwargs):
            return _result(data=[])

        with patch(
            "app.services.compliance_health_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_health_score(user_id="user-1")

        assert "100" in result["explanation"]


# ---------------------------------------------------------------------------
# Risk deductions
# ---------------------------------------------------------------------------


class TestRiskDeductions:
    """Active risks deduct points based on severity."""

    @pytest.mark.asyncio
    async def test_high_severity_risk_deduction(self):
        """2 high-severity risks => -30 points (15 each)."""
        svc = _make_service()
        call_count = 0

        async def fake_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            # First call = risks, second = audits, third = deadlines
            if call_count == 1:
                return _result(data=[
                    {"severity": "high", "title": "GDPR gap"},
                    {"severity": "high", "title": "SOX gap"},
                ])
            return _result(data=[])

        with patch(
            "app.services.compliance_health_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_health_score(user_id="user-1")

        assert result["score"] == 70
        assert result["factors"]["active_risks"] == 2

    @pytest.mark.asyncio
    async def test_critical_severity_risk_deduction(self):
        """1 critical-severity risk => -20 points."""
        svc = _make_service()
        call_count = 0

        async def fake_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _result(data=[
                    {"severity": "critical", "title": "Data breach risk"},
                ])
            return _result(data=[])

        with patch(
            "app.services.compliance_health_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_health_score(user_id="user-1")

        assert result["score"] == 80

    @pytest.mark.asyncio
    async def test_medium_and_low_severity_deductions(self):
        """1 medium (-5) + 1 low (-2) => score 93."""
        svc = _make_service()
        call_count = 0

        async def fake_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _result(data=[
                    {"severity": "medium", "title": "Policy gap"},
                    {"severity": "low", "title": "Minor issue"},
                ])
            return _result(data=[])

        with patch(
            "app.services.compliance_health_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_health_score(user_id="user-1")

        assert result["score"] == 93

    @pytest.mark.asyncio
    async def test_mixed_severity_risks(self):
        """1 critical (-20) + 1 high (-15) + 1 medium (-5) => score 60."""
        svc = _make_service()
        call_count = 0

        async def fake_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _result(data=[
                    {"severity": "critical", "title": "Breach risk"},
                    {"severity": "high", "title": "GDPR gap"},
                    {"severity": "medium", "title": "Policy issue"},
                ])
            return _result(data=[])

        with patch(
            "app.services.compliance_health_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_health_score(user_id="user-1")

        assert result["score"] == 60
        assert result["factors"]["active_risks"] == 3


# ---------------------------------------------------------------------------
# Overdue audit deductions
# ---------------------------------------------------------------------------


class TestOverdueAuditDeductions:
    """Overdue audits deduct 10 points each."""

    @pytest.mark.asyncio
    async def test_overdue_audit_deduction(self):
        """1 overdue audit => -10 points."""
        svc = _make_service()
        call_count = 0

        async def fake_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return _result(data=[
                    {"title": "GDPR Annual Review", "scheduled_date": "2026-01-01", "status": "scheduled"},
                ])
            return _result(data=[])

        with patch(
            "app.services.compliance_health_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_health_score(user_id="user-1")

        assert result["score"] == 90
        assert result["factors"]["overdue_audits"] == 1

    @pytest.mark.asyncio
    async def test_multiple_overdue_audits(self):
        """3 overdue audits => -30 points."""
        svc = _make_service()
        call_count = 0

        async def fake_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return _result(data=[
                    {"title": "GDPR Review", "scheduled_date": "2026-01-01", "status": "scheduled"},
                    {"title": "SOX Review", "scheduled_date": "2026-02-01", "status": "in_progress"},
                    {"title": "HIPAA Review", "scheduled_date": "2025-12-01", "status": "scheduled"},
                ])
            return _result(data=[])

        with patch(
            "app.services.compliance_health_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_health_score(user_id="user-1")

        assert result["score"] == 70
        assert result["factors"]["overdue_audits"] == 3


# ---------------------------------------------------------------------------
# Overdue deadline deductions
# ---------------------------------------------------------------------------


class TestOverdueDeadlineDeductions:
    """Overdue compliance deadlines deduct 10 points each."""

    @pytest.mark.asyncio
    async def test_overdue_deadline_deduction(self):
        """1 overdue deadline => -10 points."""
        svc = _make_service()
        call_count = 0

        async def fake_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                return _result(data=[
                    {"title": "Privacy policy review", "due_date": "2026-01-15", "status": "upcoming"},
                ])
            return _result(data=[])

        with patch(
            "app.services.compliance_health_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_health_score(user_id="user-1")

        assert result["score"] == 90
        assert result["factors"]["overdue_deadlines"] == 1

    @pytest.mark.asyncio
    async def test_multiple_overdue_deadlines(self):
        """2 overdue deadlines => -20 points."""
        svc = _make_service()
        call_count = 0

        async def fake_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                return _result(data=[
                    {"title": "GDPR annual filing", "due_date": "2026-02-01", "status": "upcoming"},
                    {"title": "License renewal", "due_date": "2026-03-01", "status": "overdue"},
                ])
            return _result(data=[])

        with patch(
            "app.services.compliance_health_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_health_score(user_id="user-1")

        assert result["score"] == 80
        assert result["factors"]["overdue_deadlines"] == 2


# ---------------------------------------------------------------------------
# Clamping
# ---------------------------------------------------------------------------


class TestScoreClamping:
    """Score must be clamped to 0-100 range."""

    @pytest.mark.asyncio
    async def test_massive_deductions_clamp_to_zero(self):
        """Many risks + audits + deadlines => clamp at 0, never negative."""
        svc = _make_service()
        call_count = 0

        async def fake_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # 6 critical risks = -120 alone
                return _result(data=[
                    {"severity": "critical", "title": f"Critical risk {i}"} for i in range(6)
                ])
            if call_count == 2:
                return _result(data=[
                    {"title": f"Overdue audit {i}", "scheduled_date": "2025-01-01", "status": "scheduled"} for i in range(5)
                ])
            if call_count == 3:
                return _result(data=[
                    {"title": f"Overdue deadline {i}", "due_date": "2025-01-01", "status": "upcoming"} for i in range(5)
                ])
            return _result(data=[])

        with patch(
            "app.services.compliance_health_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_health_score(user_id="user-1")

        assert result["score"] == 0
        assert result["score"] >= 0


# ---------------------------------------------------------------------------
# Explanation content
# ---------------------------------------------------------------------------


class TestExplanation:
    """Explanation string must list deduction reasons in plain English."""

    @pytest.mark.asyncio
    async def test_explanation_mentions_risks(self):
        """Explanation should mention risk deductions."""
        svc = _make_service()
        call_count = 0

        async def fake_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _result(data=[
                    {"severity": "high", "title": "GDPR gap"},
                ])
            return _result(data=[])

        with patch(
            "app.services.compliance_health_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_health_score(user_id="user-1")

        assert "high-severity" in result["explanation"].lower() or "high" in result["explanation"].lower()
        assert "risk" in result["explanation"].lower()

    @pytest.mark.asyncio
    async def test_explanation_mentions_overdue_audits(self):
        """Explanation should mention overdue audit."""
        svc = _make_service()
        call_count = 0

        async def fake_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return _result(data=[
                    {"title": "GDPR Annual Review", "scheduled_date": "2026-01-01", "status": "scheduled"},
                ])
            return _result(data=[])

        with patch(
            "app.services.compliance_health_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_health_score(user_id="user-1")

        assert "overdue audit" in result["explanation"].lower() or "audit" in result["explanation"].lower()
        assert "GDPR Annual Review" in result["explanation"]

    @pytest.mark.asyncio
    async def test_explanation_mentions_overdue_deadlines(self):
        """Explanation should mention overdue deadline."""
        svc = _make_service()
        call_count = 0

        async def fake_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                return _result(data=[
                    {"title": "Privacy policy review", "due_date": "2026-01-15", "status": "upcoming"},
                ])
            return _result(data=[])

        with patch(
            "app.services.compliance_health_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_health_score(user_id="user-1")

        assert "overdue deadline" in result["explanation"].lower() or "deadline" in result["explanation"].lower()
        assert "Privacy policy review" in result["explanation"]


# ---------------------------------------------------------------------------
# Combined deductions
# ---------------------------------------------------------------------------


class TestCombinedDeductions:
    """Multiple deduction categories combine correctly."""

    @pytest.mark.asyncio
    async def test_risks_plus_audits_plus_deadlines(self):
        """1 high risk (-15) + 1 overdue audit (-10) + 1 overdue deadline (-10) => 65."""
        svc = _make_service()
        call_count = 0

        async def fake_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _result(data=[
                    {"severity": "high", "title": "GDPR gap"},
                ])
            if call_count == 2:
                return _result(data=[
                    {"title": "Annual audit", "scheduled_date": "2025-06-01", "status": "scheduled"},
                ])
            if call_count == 3:
                return _result(data=[
                    {"title": "License renewal", "due_date": "2026-01-01", "status": "upcoming"},
                ])
            return _result(data=[])

        with patch(
            "app.services.compliance_health_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_health_score(user_id="user-1")

        assert result["score"] == 65
        assert result["factors"]["active_risks"] == 1
        assert result["factors"]["overdue_audits"] == 1
        assert result["factors"]["overdue_deadlines"] == 1
        assert len(result["deductions"]) == 3
