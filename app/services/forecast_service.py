# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""ForecastService - Data-driven financial forecasting.

Replaces the degraded generate_forecast placeholder (Phase 60, FIN-06)
with real weighted linear regression on historical Stripe/Shopify data
from the financial_records table.

Uses lazy DB imports for testability without the full Supabase client chain.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _weighted_linear_regression(
    values: list[float],
    *,
    recent_weight: float = 2.0,
) -> tuple[float, float]:
    """Compute weighted linear regression (intercept, slope).

    More recent data points receive higher weight so the forecast
    tracks recent momentum rather than long-ago averages.

    Args:
        values: Ordered time-series values (oldest first).
        recent_weight: Weight multiplier for the most recent point.
            Weights scale linearly from 1.0 to *recent_weight*.

    Returns:
        Tuple of (intercept, slope).
    """
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    if n == 1:
        return values[0], 0.0

    # Linear weight ramp: 1.0 ... recent_weight
    weights = [1.0 + (recent_weight - 1.0) * i / (n - 1) for i in range(n)]

    sum_w = sum(weights)
    sum_wx = sum(w * i for i, w in enumerate(weights))
    sum_wy = sum(w * y for w, y in zip(weights, values, strict=True))
    sum_wxy = sum(w * i * y for i, (w, y) in enumerate(zip(weights, values, strict=True)))
    sum_wxx = sum(w * i * i for i, w in enumerate(weights))

    denom = sum_w * sum_wxx - sum_wx * sum_wx
    if abs(denom) < 1e-12:
        avg = sum_wy / sum_w if sum_w else 0.0
        return avg, 0.0

    slope = (sum_w * sum_wxy - sum_wx * sum_wy) / denom
    intercept = (sum_wy - slope * sum_wx) / sum_w
    return intercept, slope


class ForecastService:
    """Data-driven financial forecasting using historical records.

    Uses weighted linear regression on actual revenue and expense
    history from the ``financial_records`` table to project future
    months with a confidence level that reflects data quantity.

    DB access is deferred to method calls (lazy imports) so the class
    can be instantiated in test environments without Supabase.
    """

    def _get_client(self):
        """Lazily obtain a Supabase client."""
        from app.services.financial_service import FinancialService

        return FinancialService().client

    async def get_monthly_history(
        self,
        user_id: str,
        months: int = 12,
    ) -> list[dict]:
        """Fetch monthly aggregated revenue and expenses.

        Args:
            user_id: The user whose records to aggregate.
            months: How many months of history to fetch (default 12).

        Returns:
            List of ``{"month": "YYYY-MM", "revenue": float,
            "expenses": float, "net": float}`` sorted oldest-first.
        """
        from app.services.supabase_async import execute_async

        client = self._get_client()
        query = (
            client.table("financial_records")
            .select("amount, transaction_type, transaction_date")
            .eq("user_id", user_id)
            .order("transaction_date", desc=False)
            .limit(5000)
        )
        response = await execute_async(query, op_name="forecast.monthly_history")
        rows = response.data or []

        # Bucket by YYYY-MM
        buckets: dict[str, dict[str, float]] = {}
        revenue_types = {"revenue", "income", "credit", "payment", "payout"}
        expense_types = {"expense", "burn", "cost", "payroll", "debit", "fee"}

        for row in rows:
            tx_date = row.get("transaction_date", "")
            if not tx_date:
                continue
            month_key = tx_date[:7]  # "YYYY-MM"
            if month_key not in buckets:
                buckets[month_key] = {"revenue": 0.0, "expenses": 0.0}

            amount = float(row.get("amount") or 0)
            tx_type = str(row.get("transaction_type") or "").strip().lower()

            if tx_type in revenue_types:
                buckets[month_key]["revenue"] += abs(amount)
            elif tx_type in expense_types:
                buckets[month_key]["expenses"] += abs(amount)
            elif amount >= 0:
                buckets[month_key]["revenue"] += amount
            else:
                buckets[month_key]["expenses"] += abs(amount)

        # Sort and take last N months
        sorted_months = sorted(buckets.keys())[-months:]
        result = []
        for m in sorted_months:
            b = buckets[m]
            result.append({
                "month": m,
                "revenue": round(b["revenue"], 2),
                "expenses": round(b["expenses"], 2),
                "net": round(b["revenue"] - b["expenses"], 2),
            })
        return result

    async def generate_forecast(
        self,
        user_id: str,
        months_ahead: int = 6,
        title: str = "Forecast",
    ) -> dict:
        """Generate a data-driven financial forecast.

        Uses weighted linear regression on actual transaction history
        to project revenue and expenses for *months_ahead* months.

        Args:
            user_id: The user to forecast for.
            months_ahead: Number of months to project (default 6).
            title: Title for the forecast report.

        Returns:
            Dictionary with forecast_months, confidence, methodology, etc.
        """
        history = await self.get_monthly_history(user_id, months=12)
        data_months = len(history)

        if data_months < 3:
            # Flat projection from average of available data
            avg_rev = (
                sum(m["revenue"] for m in history) / data_months
                if data_months
                else 0.0
            )
            avg_exp = (
                sum(m["expenses"] for m in history) / data_months
                if data_months
                else 0.0
            )
            forecast_months = []
            now = datetime.now(timezone.utc)
            for i in range(months_ahead):
                year = now.year
                month = now.month + i + 1
                while month > 12:
                    month -= 12
                    year += 1
                forecast_months.append({
                    "month": f"{year}-{month:02d}",
                    "projected_revenue": round(avg_rev, 2),
                    "projected_expenses": round(avg_exp, 2),
                    "projected_net": round(avg_rev - avg_exp, 2),
                })
            return {
                "title": title,
                "forecast_months": forecast_months,
                "confidence": "low",
                "data_months_used": data_months,
                "methodology": "flat_average",
                "currency": "USD",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        # Determine confidence and regression type
        revenue_series = [m["revenue"] for m in history]
        expense_series = [m["expenses"] for m in history]

        if data_months >= 6:
            confidence = "high"
            methodology = "weighted_linear_regression"
            rev_intercept, rev_slope = _weighted_linear_regression(
                revenue_series, recent_weight=2.0
            )
            exp_intercept, exp_slope = _weighted_linear_regression(
                expense_series, recent_weight=2.0
            )
        else:
            confidence = "medium"
            methodology = "linear_regression"
            rev_intercept, rev_slope = _weighted_linear_regression(
                revenue_series, recent_weight=1.0
            )
            exp_intercept, exp_slope = _weighted_linear_regression(
                expense_series, recent_weight=1.0
            )

        # Project forward from end of historical period
        n = data_months  # index of first projected month
        forecast_months = []
        now = datetime.now(timezone.utc)
        for i in range(months_ahead):
            month_index = n + i
            proj_rev = max(0.0, rev_intercept + rev_slope * month_index)
            proj_exp = max(0.0, exp_intercept + exp_slope * month_index)

            year = now.year
            month = now.month + i + 1
            while month > 12:
                month -= 12
                year += 1

            forecast_months.append({
                "month": f"{year}-{month:02d}",
                "projected_revenue": round(proj_rev, 2),
                "projected_expenses": round(proj_exp, 2),
                "projected_net": round(proj_rev - proj_exp, 2),
            })

        return {
            "title": title,
            "forecast_months": forecast_months,
            "confidence": confidence,
            "data_months_used": data_months,
            "methodology": methodology,
            "currency": "USD",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


async def generate_forecast(
    user_id: str,
    months_ahead: int = 6,
    title: str = "Forecast",
) -> dict:
    """Module-level convenience function for ForecastService.generate_forecast."""
    svc = ForecastService()
    return await svc.generate_forecast(
        user_id=user_id, months_ahead=months_ahead, title=title
    )
