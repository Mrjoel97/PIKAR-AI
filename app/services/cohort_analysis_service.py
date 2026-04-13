# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""CohortAnalysisService — SaaS cohort retention, LTV, and churn analysis.

Analyses Stripe transaction data from financial_records to compute cohort-level
metrics for SaaS businesses:

- Retention matrix: what % of each signup-month cohort returned in subsequent months
- LTV by cohort: average lifetime value per signup-month cohort
- Churn by cohort: churn rate per signup-month cohort

DATA-04 implementation. Used by the cohort_analysis tool in app/agents/data/tools.py.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.base_service import BaseService
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


class CohortAnalysisService(BaseService):
    """Service for SaaS cohort retention, LTV, and churn computation.

    Uses financial_records (Stripe-synced revenue transactions) to identify
    unique customers via source_id and group them by their first-transaction
    month (signup cohort proxy).
    """

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _month_key(self, dt: datetime) -> str:
        """Return YYYY-MM string for a datetime."""
        return dt.strftime("%Y-%m")

    def _parse_date(self, date_str: str) -> datetime:
        """Parse ISO date string into a timezone-aware datetime."""
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    async def _fetch_stripe_revenue(self, user_id: str, months: int) -> list[dict[str, Any]]:
        """Fetch Stripe revenue transactions for the given user and time window.

        Args:
            user_id: The user whose financial_records to query.
            months: Number of months of history to retrieve.

        Returns:
            List of financial_record dicts with source_id, amount, transaction_date.
        """
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=months * 31)
        result = await execute_async(
            self.client.table("financial_records")
            .select("source_id,amount,transaction_type,transaction_date")
            .eq("user_id", user_id)
            .eq("source_type", "stripe")
            .eq("transaction_type", "revenue")
            .gte("transaction_date", cutoff.isoformat()),
            op_name="cohort.fetch_revenue",
        )
        return result.data or []

    def _build_customer_timeline(
        self, rows: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Build per-customer timeline from raw financial_records rows.

        Returns:
            Dict keyed by source_id with:
                signup_month: str (YYYY-MM of first transaction)
                active_months: set of YYYY-MM strings when active
                total_revenue: float
                last_transaction: datetime
        """
        customers: dict[str, dict[str, Any]] = {}
        for row in rows:
            cid = row.get("source_id")
            if not cid:
                continue
            dt = self._parse_date(row["transaction_date"])
            month = self._month_key(dt)
            amount = float(row.get("amount") or 0)

            if cid not in customers:
                customers[cid] = {
                    "signup_month": month,
                    "signup_dt": dt,
                    "active_months": {month},
                    "total_revenue": amount,
                    "last_transaction": dt,
                }
            else:
                entry = customers[cid]
                if dt < entry["signup_dt"]:
                    entry["signup_month"] = month
                    entry["signup_dt"] = dt
                entry["active_months"].add(month)
                entry["total_revenue"] += amount
                if dt > entry["last_transaction"]:
                    entry["last_transaction"] = dt

        return customers

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def compute_cohort_retention(
        self, user_id: str, months: int = 6
    ) -> dict[str, Any]:
        """Compute monthly cohort retention from Stripe revenue data.

        Groups customers by signup month and tracks what percentage returned
        in each subsequent month (month_0 = 100%, month_1 = %, etc.).

        Args:
            user_id: The Pikar user whose financial_records to analyse.
            months: Number of months of history to analyse.

        Returns:
            Dict with:
                cohorts: {cohort_month: {month_0: 100.0, month_1: X, ...}}
                months_analyzed: int
                total_customers: int
        """
        rows = await self._fetch_stripe_revenue(user_id, months)
        if not rows:
            return {"cohorts": {}, "months_analyzed": months, "total_customers": 0}

        customers = self._build_customer_timeline(rows)
        total_customers = len(customers)

        # Group customers by signup month
        cohort_members: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entry in customers.values():
            cohort_members[entry["signup_month"]].append(entry)

        # Determine all months in our window (sorted)
        all_months = sorted({self._month_key(self._parse_date(r["transaction_date"])) for r in rows})

        cohorts: dict[str, dict[str, float]] = {}
        for cohort_month, members in sorted(cohort_members.items()):
            cohort_size = len(members)
            if cohort_size == 0:
                continue

            # Find months after cohort_month that are in our window
            cohort_months_in_window = [m for m in all_months if m >= cohort_month]
            retention: dict[str, float] = {}
            for idx, month in enumerate(cohort_months_in_window):
                active_count = sum(1 for m in members if month in m["active_months"])
                retention[f"month_{idx}"] = round(
                    active_count / cohort_size * 100.0, 1
                )

            cohorts[cohort_month] = retention

        return {
            "cohorts": cohorts,
            "months_analyzed": months,
            "total_customers": total_customers,
        }

    async def compute_ltv_by_cohort(
        self, user_id: str, months: int = 6
    ) -> dict[str, Any]:
        """Compute average LTV per signup-month cohort.

        Args:
            user_id: The Pikar user whose financial_records to analyse.
            months: Number of months of history to analyse.

        Returns:
            Dict with:
                cohorts: {month: {avg_ltv, total_revenue, customer_count}}
                overall_avg_ltv: float
        """
        rows = await self._fetch_stripe_revenue(user_id, months)
        if not rows:
            return {"cohorts": {}, "overall_avg_ltv": 0.0}

        customers = self._build_customer_timeline(rows)

        # Group by signup month
        cohort_revenue: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"total_revenue": 0.0, "customer_count": 0}
        )
        for entry in customers.values():
            cohort = entry["signup_month"]
            cohort_revenue[cohort]["total_revenue"] += entry["total_revenue"]
            cohort_revenue[cohort]["customer_count"] += 1

        cohorts: dict[str, dict[str, Any]] = {}
        total_revenue_all = 0.0
        total_customers = 0
        for month, data in sorted(cohort_revenue.items()):
            count = data["customer_count"]
            rev = data["total_revenue"]
            avg_ltv = rev / count if count > 0 else 0.0
            cohorts[month] = {
                "avg_ltv": round(avg_ltv, 2),
                "total_revenue": round(rev, 2),
                "customer_count": count,
            }
            total_revenue_all += rev
            total_customers += count

        overall_avg_ltv = (
            total_revenue_all / total_customers if total_customers > 0 else 0.0
        )

        return {
            "cohorts": cohorts,
            "overall_avg_ltv": round(overall_avg_ltv, 2),
        }

    async def compute_churn_by_cohort(
        self, user_id: str, months: int = 6
    ) -> dict[str, Any]:
        """Compute churn rate per signup-month cohort.

        A customer is churned if they had no revenue transactions in the most
        recent 30 days. Churn rate = churned_count / total per cohort.

        Args:
            user_id: The Pikar user whose financial_records to analyse.
            months: Number of months of history to analyse.

        Returns:
            Dict with:
                cohorts: {month: {churn_rate, churned, total}}
                overall_churn_rate: float
        """
        rows = await self._fetch_stripe_revenue(user_id, months)
        if not rows:
            return {"cohorts": {}, "overall_churn_rate": 0.0}

        customers = self._build_customer_timeline(rows)
        churn_cutoff = datetime.now(tz=timezone.utc) - timedelta(days=30)

        # Group by signup month and classify churn
        cohort_churn: dict[str, dict[str, int]] = defaultdict(
            lambda: {"churned": 0, "total": 0}
        )
        total_churned = 0
        for entry in customers.values():
            cohort = entry["signup_month"]
            cohort_churn[cohort]["total"] += 1
            if entry["last_transaction"] < churn_cutoff:
                cohort_churn[cohort]["churned"] += 1
                total_churned += 1

        cohorts: dict[str, dict[str, Any]] = {}
        for month, data in sorted(cohort_churn.items()):
            total = data["total"]
            churned = data["churned"]
            churn_rate = churned / total if total > 0 else 0.0
            cohorts[month] = {
                "churn_rate": round(churn_rate, 4),
                "churned": churned,
                "total": total,
            }

        total_customers = len(customers)
        overall_churn_rate = (
            total_churned / total_customers if total_customers > 0 else 0.0
        )

        return {
            "cohorts": cohorts,
            "overall_churn_rate": round(overall_churn_rate, 4),
        }

    async def _generate_summary(
        self,
        retention: dict[str, Any],
        ltv: dict[str, Any],
        churn: dict[str, Any],
    ) -> str:
        """Generate a plain-English executive summary using Gemini Flash.

        Falls back to a template if LLM is unavailable.

        Args:
            retention: Result from compute_cohort_retention.
            ltv: Result from compute_ltv_by_cohort.
            churn: Result from compute_churn_by_cohort.

        Returns:
            3-4 sentence plain-English summary of cohort findings.
        """
        overall_churn = churn.get("overall_churn_rate", 0.0)
        overall_ltv = ltv.get("overall_avg_ltv", 0.0)
        total_customers = retention.get("total_customers", 0)
        cohort_count = len(retention.get("cohorts", {}))

        # Build best/worst retention cohort description
        cohorts_ret = retention.get("cohorts", {})
        retention_notes = ""
        if cohorts_ret:
            # Find cohort with best month_1 retention (if available)
            best_cohort = None
            best_rate = -1.0
            worst_cohort = None
            worst_rate = 101.0
            for month, rates in cohorts_ret.items():
                m1 = rates.get("month_1")
                if m1 is not None:
                    if m1 > best_rate:
                        best_rate = m1
                        best_cohort = month
                    if m1 < worst_rate:
                        worst_rate = m1
                        worst_cohort = month
            if best_cohort and worst_cohort and best_cohort != worst_cohort:
                retention_notes = (
                    f" Best-performing cohort ({best_cohort}) retained "
                    f"{best_rate:.0f}% of customers in month 1; "
                    f"weakest cohort ({worst_cohort}) retained {worst_rate:.0f}%."
                )
            elif best_cohort:
                retention_notes = (
                    f" Cohort {best_cohort} retained {best_rate:.0f}% in month 1."
                )

        # Attempt LLM summary
        try:
            import google.generativeai as genai

            prompt = (
                f"You are a business analyst. Summarise these SaaS cohort metrics in 3-4 sentences "
                f"for a non-technical founder. Be specific, actionable, and upbeat where appropriate.\n\n"
                f"- Total customers analysed: {total_customers}\n"
                f"- Cohorts analysed: {cohort_count}\n"
                f"- Overall average LTV: ${overall_ltv:.2f}\n"
                f"- Overall churn rate: {overall_churn * 100:.1f}%\n"
                f"{retention_notes}\n"
                f"Focus on: best/worst retention cohorts, LTV trends, and churn concerns."
            )
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            text = response.text.strip()
            if text:
                return text
        except Exception:
            logger.debug("LLM summary unavailable, using template fallback")

        # Template fallback
        churn_pct = overall_churn * 100
        churn_level = "low" if churn_pct < 5 else "moderate" if churn_pct < 15 else "high"
        return (
            f"Analysis of {total_customers} customers across {cohort_count} cohort(s) shows "
            f"an average lifetime value of ${overall_ltv:.2f} and an overall churn rate of "
            f"{churn_pct:.1f}% ({churn_level} churn).{retention_notes} "
            f"Review individual cohort breakdowns to identify retention improvement opportunities."
        )

    async def full_cohort_analysis(
        self, user_id: str, months: int = 6
    ) -> dict[str, Any]:
        """Run full SaaS cohort analysis: retention, LTV, and churn.

        Combines all three analyses and generates an executive summary.

        Args:
            user_id: The Pikar user whose financial_records to analyse.
            months: Number of months of history to analyse.

        Returns:
            Dict with retention, ltv, churn, executive_summary, and chart_data.
        """
        retention = await self.compute_cohort_retention(user_id, months)
        ltv = await self.compute_ltv_by_cohort(user_id, months)
        churn = await self.compute_churn_by_cohort(user_id, months)

        executive_summary = await self._generate_summary(retention, ltv, churn)

        # Build chart_data for rendering
        cohort_months = sorted(retention.get("cohorts", {}).keys())
        chart_data = {
            "retention": {
                "type": "line",
                "title": "Cohort Retention by Month",
                "cohorts": dict(retention.get("cohorts", {}).items()),
            },
            "ltv": {
                "type": "bar",
                "title": "Average LTV by Signup Cohort",
                "labels": cohort_months,
                "values": [
                    ltv["cohorts"].get(m, {}).get("avg_ltv", 0.0)
                    for m in cohort_months
                ],
            },
            "churn": {
                "type": "bar",
                "title": "Churn Rate by Signup Cohort",
                "labels": cohort_months,
                "values": [
                    round(churn["cohorts"].get(m, {}).get("churn_rate", 0.0) * 100, 1)
                    for m in cohort_months
                ],
            },
        }

        return {
            "retention": retention,
            "ltv": ltv,
            "churn": churn,
            "executive_summary": executive_summary,
            "chart_data": chart_data,
        }
