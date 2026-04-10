# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""ScenarioModelingService - What-if financial projections.

Projects 6-month financials with arbitrary what-if parameters
(hire, churn, revenue change, new expense) on top of baseline
forecasts from ForecastService.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def _get_baseline_forecast(user_id: str, months: int) -> dict:
    """Get baseline forecast via lazy-imported ForecastService."""
    from app.services.forecast_service import ForecastService

    svc = ForecastService()
    return await svc.generate_forecast(user_id=user_id, months_ahead=months)


async def _get_cash_position() -> dict:
    """Get cash position via lazy-imported financial tools."""
    from app.agents.financial.tools import get_cash_position

    return await get_cash_position()


class ScenarioModelingService:
    """What-if financial projection engine.

    Builds on ``ForecastService`` baseline forecasts and applies
    scenario adjustments (hiring, revenue changes, new expenses)
    to project cumulative cash position and detect when cash turns
    negative.

    DB access is deferred to helper functions with lazy imports so this
    class can be instantiated in tests without the full Supabase chain.
    """

    async def run_scenario(
        self,
        user_id: str,
        scenario: dict,
        months: int = 6,
    ) -> dict:
        """Run a what-if scenario projection.

        Args:
            user_id: The user to model for.
            scenario: Dict of scenario parameters. Supported keys:
                - ``hire``: ``{"count": int, "salary_per_person": float}``
                - ``revenue_change_pct``: float (positive = growth)
                - ``new_expense``: ``{"description": str, "monthly_amount": float}``
                - ``lose_customers_pct``: float (reduces revenue)
                - ``price_increase_pct``: float (increases revenue)
            months: Number of months to project (default 6).

        Returns:
            Dict with baseline, projected, starting_cash, ending_cash,
            months_until_negative, warnings, and summary.
        """
        # Get baseline forecast
        baseline_result = await _get_baseline_forecast(user_id, months)
        baseline_months = baseline_result["forecast_months"]

        # Get current cash position
        cash_result = await _get_cash_position()
        starting_cash = float(cash_result.get("cash_position", 0.0))

        # Build projected months with scenario adjustments
        projected = []
        current_cash = starting_cash
        months_until_negative = None
        warnings: list[str] = []

        # Parse scenario modifiers
        hire = scenario.get("hire", {})
        hire_cost = float(hire.get("count", 0)) * float(
            hire.get("salary_per_person", 0)
        )

        revenue_change_pct = float(scenario.get("revenue_change_pct", 0))
        lose_customers_pct = float(scenario.get("lose_customers_pct", 0))
        price_increase_pct = float(scenario.get("price_increase_pct", 0))

        new_expense = scenario.get("new_expense", {})
        new_expense_amount = (
            float(new_expense.get("monthly_amount", 0)) if new_expense else 0.0
        )

        # Net revenue multiplier
        revenue_multiplier = 1.0
        if lose_customers_pct:
            revenue_multiplier *= 1 - lose_customers_pct / 100
        if price_increase_pct:
            revenue_multiplier *= 1 + price_increase_pct / 100
        if revenue_change_pct:
            revenue_multiplier *= 1 + revenue_change_pct / 100

        additional_expense = hire_cost + new_expense_amount

        for i, bm in enumerate(baseline_months):
            adj_revenue = round(bm["projected_revenue"] * revenue_multiplier, 2)
            adj_expenses = round(bm["projected_expenses"] + additional_expense, 2)
            adj_net = round(adj_revenue - adj_expenses, 2)
            current_cash = round(current_cash + adj_net, 2)

            projected.append({
                "month": bm["month"],
                "projected_revenue": adj_revenue,
                "projected_expenses": adj_expenses,
                "projected_net": adj_net,
                "cash_position": current_cash,
            })

            if current_cash < 0 and months_until_negative is None:
                months_until_negative = i + 1

        ending_cash = current_cash

        # Generate warnings
        if months_until_negative is not None:
            warnings.append(
                f"Cash position turns negative in month {months_until_negative} "
                f"of the projection."
            )

        # Build human-readable summary
        summary = self._build_summary(
            scenario=scenario,
            starting_cash=starting_cash,
            ending_cash=ending_cash,
            months=months,
            hire_cost=hire_cost,
            additional_expense=additional_expense,
            revenue_multiplier=revenue_multiplier,
            months_until_negative=months_until_negative,
        )

        # Baseline list (without scenario adjustments) for comparison
        baseline_list = []
        base_cash = starting_cash
        for bm in baseline_months:
            base_cash = round(base_cash + bm["projected_net"], 2)
            baseline_list.append({
                **bm,
                "cash_position": base_cash,
            })

        return {
            "scenario": scenario,
            "baseline": baseline_list,
            "projected": projected,
            "starting_cash": starting_cash,
            "ending_cash": ending_cash,
            "months_until_negative": months_until_negative,
            "warnings": warnings,
            "summary": summary,
        }

    @staticmethod
    def _build_summary(
        *,
        scenario: dict,
        starting_cash: float,
        ending_cash: float,
        months: int,
        hire_cost: float,
        additional_expense: float,
        revenue_multiplier: float,
        months_until_negative: int | None,
    ) -> str:
        """Build a plain-English summary of the scenario projection."""
        parts: list[str] = []

        hire = scenario.get("hire", {})
        if hire:
            count = hire.get("count", 0)
            salary = hire.get("salary_per_person", 0)
            parts.append(
                f"Hiring {count} {'person' if count == 1 else 'people'} "
                f"at ${salary:,.0f}/mo each would increase monthly expenses "
                f"by ${hire_cost:,.0f}."
            )

        new_exp = scenario.get("new_expense", {})
        if new_exp:
            amt = new_exp.get("monthly_amount", 0)
            desc = new_exp.get("description", "new expense")
            parts.append(
                f"Adding {desc} at ${amt:,.0f}/mo increases monthly costs."
            )

        if scenario.get("lose_customers_pct"):
            parts.append(
                f"Losing {scenario['lose_customers_pct']}% of customers "
                f"reduces projected revenue accordingly."
            )

        if scenario.get("price_increase_pct"):
            parts.append(
                f"A {scenario['price_increase_pct']}% price increase "
                f"boosts projected revenue."
            )

        if scenario.get("revenue_change_pct"):
            pct = scenario["revenue_change_pct"]
            direction = "growth" if pct > 0 else "decline"
            parts.append(
                f"A {abs(pct)}% revenue {direction} is applied to projections."
            )

        parts.append(
            f"Based on your current revenue trend, you would have "
            f"${ending_cash:,.0f} remaining after {months} months."
        )

        if months_until_negative is not None:
            parts.append(
                f"Warning: Cash is projected to turn negative in month "
                f"{months_until_negative}."
            )

        if not any(
            k in scenario
            for k in (
                "hire",
                "new_expense",
                "lose_customers_pct",
                "price_increase_pct",
                "revenue_change_pct",
            )
        ):
            parts.insert(
                0, "Baseline projection with no scenario changes applied."
            )

        return " ".join(parts)


async def run_scenario(
    user_id: str,
    scenario: dict,
    months: int = 6,
) -> dict:
    """Module-level convenience function for ScenarioModelingService.run_scenario."""
    svc = ScenarioModelingService()
    return await svc.run_scenario(
        user_id=user_id, scenario=scenario, months=months
    )
