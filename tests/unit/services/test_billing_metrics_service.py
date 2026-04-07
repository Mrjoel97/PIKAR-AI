# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for BillingMetricsService — DB-native MRR and approximated churn.

Plan 50-03 / BILL-04. Verifies:

- compute_mrr sums TIER_PRICES for active subscriptions only
- compute_mrr excludes inactive rows and the enterprise tier (custom-price)
- compute_mrr returns zero on empty table without raising
- compute_churn_rate returns the approximation
  canceled_in_period / (current_active + canceled_in_period)
- compute_churn_rate safely returns 0.0 when active_at_start == 0
- compute_churn_trend returns a zero-filled per-day cancellation list of
  length == window_days
- BillingMetricsService inherits from AdminService and exposes a service-role
  ``self.client`` (regression guard — Phase 41 decision)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service():
    """Return a BillingMetricsService with a stubbed Supabase service client.

    Patches ``app.services.supabase.get_service_client`` (the factory imported
    lazily inside ``AdminService.client``) so the lazy property resolves to a
    MagicMock without touching the real Supabase singleton or env vars.
    """
    with patch(
        "app.services.supabase.get_service_client",
        return_value=MagicMock(),
    ):
        from app.services.billing_metrics_service import BillingMetricsService

        svc = BillingMetricsService()
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
# compute_mrr
# ---------------------------------------------------------------------------


class TestComputeMrr:
    """compute_mrr sums TIER_PRICES across active subscriptions only."""

    @pytest.mark.asyncio
    async def test_compute_mrr_empty(self):
        """Empty subscriptions table returns mrr=0.0 / arr=0.0."""
        svc = _make_service()
        with patch(
            "app.services.billing_metrics_service.execute_async",
            return_value=_result(data=[]),
        ):
            result = await svc.compute_mrr()

        assert result == {"mrr": 0.0, "arr": 0.0}

    @pytest.mark.asyncio
    async def test_compute_mrr_sums_active_tiers(self):
        """3 solopreneur + 1 startup + 1 enterprise => mrr = 3*99 + 297 = 594."""
        svc = _make_service()
        rows = [
            {"tier": "solopreneur"},
            {"tier": "solopreneur"},
            {"tier": "solopreneur"},
            {"tier": "startup"},
            {"tier": "enterprise"},  # custom pricing — excluded
        ]
        with patch(
            "app.services.billing_metrics_service.execute_async",
            return_value=_result(data=rows),
        ):
            result = await svc.compute_mrr()

        assert result["mrr"] == pytest.approx(594.0)
        assert result["arr"] == pytest.approx(7128.0)


# ---------------------------------------------------------------------------
# compute_churn_rate
# ---------------------------------------------------------------------------


class TestComputeChurnRate:
    """compute_churn_rate returns the approximation churn ratio."""

    @pytest.mark.asyncio
    async def test_compute_churn_rate_zero_active(self):
        """active_at_start == 0 returns churn_rate=0.0 without ZeroDivisionError."""
        svc = _make_service()

        async def fake_execute(query, *, op_name=""):
            if "canceled" in op_name:
                return _result(count=0)
            return _result(count=0)

        with patch(
            "app.services.billing_metrics_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_churn_rate(days=30)

        assert result["churn_rate"] == 0.0
        assert result["canceled_in_period"] == 0
        assert result["active_at_start"] == 0
        assert result["window_days"] == 30

    @pytest.mark.asyncio
    async def test_compute_churn_rate_real(self):
        """10 canceled + 90 currently active => active_at_start=100, churn=0.10."""
        svc = _make_service()

        async def fake_execute(query, *, op_name=""):
            if "canceled" in op_name:
                return _result(count=10)
            return _result(count=90)

        with patch(
            "app.services.billing_metrics_service.execute_async",
            side_effect=fake_execute,
        ):
            result = await svc.compute_churn_rate(days=30)

        assert result["canceled_in_period"] == 10
        assert result["active_at_start"] == 100
        assert result["churn_rate"] == pytest.approx(0.10)
        assert result["window_days"] == 30


# ---------------------------------------------------------------------------
# compute_churn_trend
# ---------------------------------------------------------------------------


class TestComputeChurnTrend:
    """compute_churn_trend zero-fills the per-day window."""

    @pytest.mark.asyncio
    async def test_compute_churn_trend_zero_fill(self):
        """3-day window with 1 cancellation should return 3 entries."""
        svc = _make_service()

        # One cancellation that landed yesterday (day index N-2 in a 3-day window).
        yesterday = datetime.now(tz=timezone.utc) - timedelta(days=1)
        rows = [{"updated_at": yesterday.isoformat()}]

        with patch(
            "app.services.billing_metrics_service.execute_async",
            return_value=_result(data=rows),
        ):
            trend = await svc.compute_churn_trend(days=3)

        assert isinstance(trend, list)
        assert len(trend) == 3
        # All entries shaped {"date": "YYYY-MM-DD", "canceled": int}
        for entry in trend:
            assert "date" in entry
            assert "canceled" in entry
            assert isinstance(entry["canceled"], int)
        # Total cancellations across the window must equal the input
        total = sum(entry["canceled"] for entry in trend)
        assert total == 1


# ---------------------------------------------------------------------------
# Service shape regression
# ---------------------------------------------------------------------------


class TestServiceShape:
    """BillingMetricsService inherits from AdminService (Phase 41 regression guard)."""

    def test_billing_metrics_service_uses_admin_client(self):
        """Service must inherit from AdminService and expose ``self.client``."""
        from app.services.base_service import AdminService
        from app.services.billing_metrics_service import BillingMetricsService

        assert issubclass(BillingMetricsService, AdminService), (
            "BillingMetricsService must inherit from AdminService — it aggregates "
            "across all users under require_admin protection and needs the "
            "service-role client. Phase 41 decision."
        )

        with patch(
            "app.services.supabase.get_service_client",
            return_value=MagicMock(),
        ) as mocked:
            svc = BillingMetricsService()
            client = svc.client
            assert client is mocked.return_value
