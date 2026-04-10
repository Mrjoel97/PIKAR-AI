# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tax Reminder Service.

Computes quarterly estimated tax payments from YTD revenue and determines
when reminders are due, for inclusion in the daily briefing (FIN-05).

Usage::

    from app.services.tax_reminder_service import TaxReminderService

    svc = TaxReminderService()
    if svc.is_reminder_due():
        estimate = await svc.get_quarterly_tax_estimate(user_id)
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.services.base_service import BaseService
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# Default estimated tax rate (25%)
DEFAULT_TAX_RATE: float = 0.25

# Quarterly estimated tax deadlines (month, day)
QUARTER_DEADLINES: list[tuple[int, int]] = [
    (3, 15),   # Q1: March 15
    (6, 15),   # Q2: June 15
    (9, 15),   # Q3: September 15
    (12, 15),  # Q4: December 15
]

# Number of days before a deadline to start showing reminders
REMINDER_WINDOW_DAYS: int = 14


class TaxReminderService(BaseService):
    """Service for computing quarterly estimated tax and reminder timing.

    Queries ``financial_records`` for YTD revenue and computes estimated
    quarterly tax payments. Also checks whether a reminder is due based
    on proximity to the next quarter deadline.
    """

    async def get_ytd_revenue(self, user_id: str) -> float:
        """Compute year-to-date revenue for a user.

        Queries financial_records WHERE user_id AND transaction_type = 'revenue'
        AND transaction_date >= Jan 1 of current year, then SUMs amounts.

        Args:
            user_id: The Supabase user ID.

        Returns:
            Total YTD revenue as a float.
        """
        today = date.today()
        year_start = date(today.year, 1, 1).isoformat()

        response = await execute_async(
            self.client.table("financial_records")
            .select("amount")
            .eq("user_id", user_id)
            .eq("transaction_type", "revenue")
            .gte("transaction_date", year_start),
            op_name="tax_reminder.ytd_revenue",
        )

        rows = response.data or []
        total = sum(float(row.get("amount", 0)) for row in rows)
        return total

    async def get_quarterly_tax_estimate(
        self, user_id: str, tax_rate: float | None = None
    ) -> dict[str, Any]:
        """Compute quarterly estimated tax from YTD revenue.

        Args:
            user_id: The Supabase user ID.
            tax_rate: Optional custom tax rate (defaults to 25%).

        Returns:
            Dict with ytd_revenue, estimated_annual_tax, quarterly_payment,
            tax_rate, next_deadline, currency, and explanation.
        """
        rate = tax_rate if tax_rate is not None else DEFAULT_TAX_RATE
        ytd_revenue = await self.get_ytd_revenue(user_id)

        estimated_annual_tax = ytd_revenue * rate
        quarterly_payment = estimated_annual_tax / 4

        next_deadline = self._get_next_deadline()

        rate_pct = round(rate * 100, 1)
        explanation = (
            f"Based on ${ytd_revenue:,.2f} YTD revenue at {rate_pct}% estimated rate, "
            f"your quarterly estimated tax payment is ${quarterly_payment:,.2f}. "
            f"Next deadline: {next_deadline}."
        )

        return {
            "ytd_revenue": ytd_revenue,
            "estimated_annual_tax": estimated_annual_tax,
            "quarterly_payment": quarterly_payment,
            "tax_rate": rate,
            "next_deadline": next_deadline,
            "currency": "USD",
            "explanation": explanation,
        }

    def is_reminder_due(self) -> bool:
        """Check if a tax reminder is currently due.

        Returns True if the current date is within REMINDER_WINDOW_DAYS
        of any quarter deadline (and not after the deadline).

        Returns:
            True if a reminder should be shown, False otherwise.
        """
        today = date.today()

        for month, day in QUARTER_DEADLINES:
            deadline = date(today.year, month, day)
            days_until = (deadline - today).days
            if 0 <= days_until <= REMINDER_WINDOW_DAYS:
                return True

        return False

    def _get_next_deadline(self) -> str:
        """Find the next upcoming quarterly tax deadline.

        Returns:
            ISO date string of the next deadline.
        """
        today = date.today()

        for month, day in QUARTER_DEADLINES:
            deadline = date(today.year, month, day)
            if deadline >= today:
                return deadline.isoformat()

        # All deadlines this year passed; return Q1 of next year
        return date(today.year + 1, 3, 15).isoformat()


def get_quarterly_tax_estimate():
    """Module-level convenience reference for the estimate method.

    Note: Actual usage should instantiate TaxReminderService
    and call get_quarterly_tax_estimate on the instance.
    """
    return TaxReminderService


__all__ = [
    "TaxReminderService",
    "get_quarterly_tax_estimate",
]
