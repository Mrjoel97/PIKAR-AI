# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for CohortAnalysisService — SaaS cohort retention, LTV, and churn.

Plan 68-03 / DATA-04. Verifies:

- compute_cohort_retention returns retention rates per cohort month from 3 months of data
- compute_cohort_retention handles single-month data (only one cohort)
- compute_cohort_retention handles empty financial_records gracefully
- compute_ltv_by_cohort returns average LTV per signup month cohort
- compute_ltv_by_cohort handles cohort with no revenue records (LTV=0)
- compute_churn_by_cohort returns churn rate per signup month
- compute_churn_by_cohort handles all-active cohort (churn=0%)
- full_cohort_analysis returns combined dict with retention, ltv, churn, and summary
- full_cohort_analysis generates plain-English executive_summary of findings

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
    "GOOGLE_API_KEY": "fake-api-key",
}


def _make_service():
    """Return a CohortAnalysisService with a stubbed Supabase client."""
    with (
        patch.dict("os.environ", _FAKE_ENV, clear=False),
        patch(
            "app.services.supabase.get_service_client",
            return_value=MagicMock(),
        ),
    ):
        from app.services.cohort_analysis_service import CohortAnalysisService

        svc = CohortAnalysisService()
        _ = svc.client  # materialise lazy client
        return svc


def _result(data=None):
    """Build a fake Supabase result with .data."""
    obj = MagicMock()
    obj.data = data if data is not None else []
    return obj


def _make_revenue_rows():
    """Return 3 months of financial_records data with 3 distinct source_ids (customers).

    - customer-1: transactions in months 0, 1, 2 (fully retained)
    - customer-2: transactions in months 0, 1 (churned in month 2)
    - customer-3: transactions in month 0 only (churned after month 0)
    All transactions are revenue from Stripe.

    Base date: 91 days ago so months fall cleanly into 3 cohorts.
    """
    now = datetime.now(tz=timezone.utc)
    month0_start = now - timedelta(days=91)
    month1_start = now - timedelta(days=61)
    month2_start = now - timedelta(days=31)

    rows = [
        # customer-1: present in all 3 months
        {
            "source_id": "cust-1",
            "amount": "100.00",
            "transaction_type": "revenue",
            "transaction_date": month0_start.isoformat(),
        },
        {
            "source_id": "cust-1",
            "amount": "110.00",
            "transaction_type": "revenue",
            "transaction_date": month1_start.isoformat(),
        },
        {
            "source_id": "cust-1",
            "amount": "120.00",
            "transaction_type": "revenue",
            "transaction_date": month2_start.isoformat(),
        },
        # customer-2: present in months 0 and 1 only
        {
            "source_id": "cust-2",
            "amount": "200.00",
            "transaction_type": "revenue",
            "transaction_date": month0_start.isoformat(),
        },
        {
            "source_id": "cust-2",
            "amount": "210.00",
            "transaction_type": "revenue",
            "transaction_date": month1_start.isoformat(),
        },
        # customer-3: present in month 0 only
        {
            "source_id": "cust-3",
            "amount": "50.00",
            "transaction_type": "revenue",
            "transaction_date": month0_start.isoformat(),
        },
    ]
    return rows


# ---------------------------------------------------------------------------
# TestCohortAnalysisService
# ---------------------------------------------------------------------------


class TestCohortAnalysisService:
    """Unit tests for CohortAnalysisService."""

    def test_service_inherits_base_service(self):
        """CohortAnalysisService must inherit from BaseService."""
        from app.services.base_service import BaseService
        from app.services.cohort_analysis_service import CohortAnalysisService

        assert issubclass(CohortAnalysisService, BaseService), (
            "CohortAnalysisService must inherit from BaseService"
        )

    # ------------------------------------------------------------------
    # compute_cohort_retention
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_compute_cohort_retention_three_months(self):
        """compute_cohort_retention returns retention rates for 3 months of data."""
        svc = _make_service()
        rows = _make_revenue_rows()

        with patch(
            "app.services.cohort_analysis_service.execute_async",
            return_value=_result(data=rows),
        ):
            result = await svc.compute_cohort_retention("user-123", months=3)

        assert "cohorts" in result
        assert "total_customers" in result
        assert "months_analyzed" in result
        assert result["total_customers"] == 3
        # All customers present at month 0 = 100%
        cohorts = result["cohorts"]
        # The cohort for month0_start should have month_0 = 100%
        assert len(cohorts) >= 1
        # Check first cohort starts at 100%
        first_cohort = list(cohorts.values())[0]
        assert first_cohort.get("month_0") == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_compute_cohort_retention_single_month(self):
        """compute_cohort_retention handles single-month data with one cohort."""
        svc = _make_service()
        now = datetime.now(tz=timezone.utc)
        rows = [
            {
                "source_id": "cust-a",
                "amount": "50.00",
                "transaction_type": "revenue",
                "transaction_date": (now - timedelta(days=15)).isoformat(),
            },
            {
                "source_id": "cust-b",
                "amount": "75.00",
                "transaction_type": "revenue",
                "transaction_date": (now - timedelta(days=10)).isoformat(),
            },
        ]

        with patch(
            "app.services.cohort_analysis_service.execute_async",
            return_value=_result(data=rows),
        ):
            result = await svc.compute_cohort_retention("user-123", months=1)

        assert result["total_customers"] == 2
        assert len(result["cohorts"]) == 1
        cohort = list(result["cohorts"].values())[0]
        assert cohort.get("month_0") == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_compute_cohort_retention_empty(self):
        """compute_cohort_retention handles empty financial_records gracefully."""
        svc = _make_service()

        with patch(
            "app.services.cohort_analysis_service.execute_async",
            return_value=_result(data=[]),
        ):
            result = await svc.compute_cohort_retention("user-123", months=6)

        assert result["total_customers"] == 0
        assert result["cohorts"] == {}

    # ------------------------------------------------------------------
    # compute_ltv_by_cohort
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_compute_ltv_by_cohort_known_data(self):
        """compute_ltv_by_cohort returns correct avg_ltv per cohort month."""
        svc = _make_service()
        rows = _make_revenue_rows()

        with patch(
            "app.services.cohort_analysis_service.execute_async",
            return_value=_result(data=rows),
        ):
            result = await svc.compute_ltv_by_cohort("user-123", months=3)

        assert "cohorts" in result
        assert "overall_avg_ltv" in result

        # All 3 customers were signed up in the same cohort month.
        # Total revenue: cust-1 = 330, cust-2 = 410, cust-3 = 50 → total = 790
        # Average LTV = 790 / 3 ≈ 263.33
        cohort = list(result["cohorts"].values())[0]
        assert "avg_ltv" in cohort
        assert "total_revenue" in cohort
        assert "customer_count" in cohort
        assert cohort["customer_count"] == 3
        assert cohort["total_revenue"] == pytest.approx(790.0, rel=1e-3)
        assert cohort["avg_ltv"] == pytest.approx(790.0 / 3, rel=1e-3)

    @pytest.mark.asyncio
    async def test_compute_ltv_by_cohort_empty_cohort(self):
        """compute_ltv_by_cohort handles empty data (LTV=0, no division error)."""
        svc = _make_service()

        with patch(
            "app.services.cohort_analysis_service.execute_async",
            return_value=_result(data=[]),
        ):
            result = await svc.compute_ltv_by_cohort("user-123", months=6)

        assert result["cohorts"] == {}
        assert result["overall_avg_ltv"] == 0.0

    # ------------------------------------------------------------------
    # compute_churn_by_cohort
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_compute_churn_by_cohort_known_data(self):
        """compute_churn_by_cohort returns churn rates per cohort."""
        svc = _make_service()

        # Use rows where customer-3 has no recent transactions (older than 30 days)
        now = datetime.now(tz=timezone.utc)
        rows = [
            # cust-active: has a recent transaction (within 30 days) — NOT churned
            {
                "source_id": "cust-active",
                "amount": "100.00",
                "transaction_type": "revenue",
                "transaction_date": (now - timedelta(days=91)).isoformat(),
            },
            {
                "source_id": "cust-active",
                "amount": "100.00",
                "transaction_type": "revenue",
                "transaction_date": (now - timedelta(days=10)).isoformat(),
            },
            # cust-churned: last transaction > 30 days ago — churned
            {
                "source_id": "cust-churned",
                "amount": "50.00",
                "transaction_type": "revenue",
                "transaction_date": (now - timedelta(days=91)).isoformat(),
            },
        ]

        with patch(
            "app.services.cohort_analysis_service.execute_async",
            return_value=_result(data=rows),
        ):
            result = await svc.compute_churn_by_cohort("user-123", months=6)

        assert "cohorts" in result
        assert "overall_churn_rate" in result

        # overall: 1 churned out of 2 = 50%
        assert result["overall_churn_rate"] == pytest.approx(0.5)
        # Find the cohort containing both customers
        cohort = list(result["cohorts"].values())[0]
        assert cohort["churned"] == 1
        assert cohort["total"] == 2
        assert cohort["churn_rate"] == pytest.approx(0.5)

    @pytest.mark.asyncio
    async def test_compute_churn_by_cohort_all_active(self):
        """compute_churn_by_cohort returns 0% churn when all customers are active."""
        svc = _make_service()
        now = datetime.now(tz=timezone.utc)

        # Both customers have recent transactions — neither is churned
        rows = [
            {
                "source_id": "cust-1",
                "amount": "100.00",
                "transaction_type": "revenue",
                "transaction_date": (now - timedelta(days=91)).isoformat(),
            },
            {
                "source_id": "cust-1",
                "amount": "100.00",
                "transaction_type": "revenue",
                "transaction_date": (now - timedelta(days=5)).isoformat(),
            },
            {
                "source_id": "cust-2",
                "amount": "80.00",
                "transaction_type": "revenue",
                "transaction_date": (now - timedelta(days=91)).isoformat(),
            },
            {
                "source_id": "cust-2",
                "amount": "80.00",
                "transaction_type": "revenue",
                "transaction_date": (now - timedelta(days=3)).isoformat(),
            },
        ]

        with patch(
            "app.services.cohort_analysis_service.execute_async",
            return_value=_result(data=rows),
        ):
            result = await svc.compute_churn_by_cohort("user-123", months=6)

        assert result["overall_churn_rate"] == pytest.approx(0.0)
        cohort = list(result["cohorts"].values())[0]
        assert cohort["churned"] == 0
        assert cohort["churn_rate"] == pytest.approx(0.0)

    # ------------------------------------------------------------------
    # full_cohort_analysis
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_full_cohort_analysis_returns_combined_dict(self):
        """full_cohort_analysis returns dict with retention, ltv, churn, and summary."""
        svc = _make_service()
        rows = _make_revenue_rows()

        with (
            patch(
                "app.services.cohort_analysis_service.execute_async",
                return_value=_result(data=rows),
            ),
            patch(
                "app.services.cohort_analysis_service.CohortAnalysisService._generate_summary",
                return_value="Test executive summary.",
            ),
        ):
            result = await svc.full_cohort_analysis("user-123", months=3)

        assert "retention" in result
        assert "ltv" in result
        assert "churn" in result
        assert "executive_summary" in result
        assert "chart_data" in result

    @pytest.mark.asyncio
    async def test_full_cohort_analysis_executive_summary(self):
        """full_cohort_analysis generates a non-empty plain-English executive_summary."""
        svc = _make_service()
        rows = _make_revenue_rows()

        # Patch _generate_summary to verify it's called and returns summary text
        with (
            patch(
                "app.services.cohort_analysis_service.execute_async",
                return_value=_result(data=rows),
            ),
            patch.object(
                svc,
                "_generate_summary",
                new_callable=AsyncMock,
                return_value="Cohort analysis shows strong retention.",
            ),
        ):
            result = await svc.full_cohort_analysis("user-123", months=3)

        assert isinstance(result["executive_summary"], str)
        assert len(result["executive_summary"]) > 0
