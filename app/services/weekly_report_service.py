# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""WeeklyReportService — automated weekly business report generation and data catalog.

Generates a 1-page weekly business report every Monday (DATA-02) and provides
integration-aware data catalog suggestions when a new integration is connected
(DATA-03).

Used by:
- app/routers/briefing.py (GET /briefing/weekly-report)
- app/agents/data/tools.py (suggest_data_reports, generate_weekly_report)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.base_service import AdminService
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data catalog: provider → suggested reports
# ---------------------------------------------------------------------------

_CATALOG: dict[str, list[dict[str, Any]]] = {
    "stripe": [
        {
            "title": "Monthly Revenue Trend",
            "description": "Track revenue over time and identify seasonal patterns.",
            "report_type": "revenue_trend",
            "required_data_sources": ["stripe"],
        },
        {
            "title": "Customer Churn Analysis",
            "description": "Identify churned customers and analyse patterns to reduce churn.",
            "report_type": "churn_analysis",
            "required_data_sources": ["stripe"],
        },
        {
            "title": "Payment Success Rate",
            "description": "Monitor payment success vs failure rates and surface decline reasons.",
            "report_type": "payment_success_rate",
            "required_data_sources": ["stripe"],
        },
    ],
    "shopify": [
        {
            "title": "Sales by Product",
            "description": "Break down revenue and volume by individual product SKU.",
            "report_type": "sales_by_product",
            "required_data_sources": ["shopify"],
        },
        {
            "title": "Order Volume Trend",
            "description": "Visualise daily and weekly order volume over time.",
            "report_type": "order_volume_trend",
            "required_data_sources": ["shopify"],
        },
        {
            "title": "Average Order Value",
            "description": "Track average order value (AOV) and monitor for price sensitivity.",
            "report_type": "average_order_value",
            "required_data_sources": ["shopify"],
        },
    ],
    "google_ads": [
        {
            "title": "Ad Spend vs Revenue",
            "description": "Compare ad spend against attributed revenue to measure ROAS.",
            "report_type": "ad_spend_vs_revenue",
            "required_data_sources": ["google_ads"],
        },
        {
            "title": "Campaign ROI",
            "description": "Measure return on investment for each Google Ads campaign.",
            "report_type": "campaign_roi",
            "required_data_sources": ["google_ads"],
        },
    ],
    "meta_ads": [
        {
            "title": "Ad Spend vs Revenue",
            "description": "Compare Meta ad spend against attributed revenue to measure ROAS.",
            "report_type": "ad_spend_vs_revenue",
            "required_data_sources": ["meta_ads"],
        },
        {
            "title": "Campaign ROI",
            "description": "Measure return on investment for each Meta Ads campaign.",
            "report_type": "campaign_roi",
            "required_data_sources": ["meta_ads"],
        },
    ],
    "postgresql": [
        {
            "title": "Custom SQL Reports",
            "description": "Write custom SQL queries to extract and visualise any data.",
            "report_type": "custom_sql",
            "required_data_sources": ["postgresql"],
        },
        {
            "title": "Table Summary",
            "description": "Profile your database tables: row counts, null rates, and distributions.",
            "report_type": "table_summary",
            "required_data_sources": ["postgresql"],
        },
    ],
    "bigquery": [
        {
            "title": "Custom SQL Reports",
            "description": "Write custom SQL queries against your BigQuery datasets.",
            "report_type": "custom_sql",
            "required_data_sources": ["bigquery"],
        },
        {
            "title": "Table Summary",
            "description": "Profile BigQuery tables: row counts, null rates, and distributions.",
            "report_type": "table_summary",
            "required_data_sources": ["bigquery"],
        },
    ],
}

_DEFAULT_CATALOG: list[dict[str, Any]] = [
    {
        "title": "Activity Summary",
        "description": "Summarise recent activity across all connected data sources.",
        "report_type": "activity_summary",
        "required_data_sources": [],
    },
]

# Anomaly threshold: flag any metric changing >25% week-over-week
_ANOMALY_THRESHOLD_PCT = 25.0


def _week_boundaries(
    reference: datetime,
) -> tuple[datetime, datetime, datetime, datetime]:
    """Return Monday-start and Sunday-end boundaries for the current and prior weeks.

    Args:
        reference: Reference datetime (typically now in UTC).

    Returns:
        Tuple of (current_start, current_end, prev_start, prev_end) as UTC datetimes.
    """
    current_monday = reference - timedelta(days=reference.weekday())
    current_monday = current_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    current_sunday = current_monday + timedelta(
        days=6, hours=23, minutes=59, seconds=59
    )

    prev_monday = current_monday - timedelta(weeks=1)
    prev_sunday = current_monday - timedelta(seconds=1)

    return current_monday, current_sunday, prev_monday, prev_sunday


def _aggregate_financials(rows: list[dict[str, Any]]) -> tuple[float, float, str]:
    """Aggregate revenue and expenses from financial_records rows.

    Args:
        rows: Raw rows from financial_records table.

    Returns:
        Tuple of (revenue, expenses, currency).
    """
    revenue = 0.0
    expenses = 0.0
    currency = "USD"

    for row in rows:
        amount = float(row.get("amount") or 0)
        tx_type = (row.get("transaction_type") or "").lower()
        row_currency = row.get("currency") or "USD"
        if row_currency:
            currency = row_currency

        if tx_type in ("income", "revenue", "sale"):
            revenue += amount
        elif tx_type in ("expense", "cost", "refund"):
            expenses += amount

    return revenue, expenses, currency


def _pct_change(current: float, previous: float) -> float:
    """Calculate percentage change from previous to current.

    Args:
        current: Current period value.
        previous: Previous period value.

    Returns:
        Percentage change, or 0.0 if previous is zero.
    """
    if previous == 0.0:
        return 0.0
    return round(((current - previous) / abs(previous)) * 100, 2)


def _trend(change_pct: float) -> str:
    """Determine trend direction from percentage change.

    Args:
        change_pct: Percentage change value.

    Returns:
        'up', 'down', or 'stable'.
    """
    if change_pct > 1.0:
        return "up"
    if change_pct < -1.0:
        return "down"
    return "stable"


class WeeklyReportService(AdminService):
    """Service for automated weekly business report generation.

    Generates a structured weekly business report with revenue summaries,
    key metrics, anomalies, and an AI-generated executive summary.

    Also provides integration-aware data catalog suggestions for users who
    connect new integrations.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_weekly_report(self, user_id: str) -> dict[str, Any]:
        """Compile a 1-page weekly business report for the user.

        Queries financial_records for current and previous week, aggregates
        revenue and expenses, flags anomalies (>25% WoW change), and uses
        Gemini Flash to generate a plain-English executive summary.

        Args:
            user_id: Authenticated user UUID.

        Returns:
            Structured report dict with period, revenue_summary, top_metrics,
            anomalies, executive_summary, and generated_at.
        """
        now = datetime.now(tz=timezone.utc)
        curr_start, curr_end, prev_start, prev_end = _week_boundaries(now)

        # ---- current week financials ----
        curr_rows = await self._fetch_financials(user_id, curr_start, curr_end)
        curr_revenue, curr_expenses, currency = _aggregate_financials(curr_rows)

        # ---- previous week financials ----
        prev_rows = await self._fetch_financials(user_id, prev_start, prev_end)
        prev_revenue, prev_expenses, _ = _aggregate_financials(prev_rows)

        # ---- week-over-week ----
        rev_change = _pct_change(curr_revenue, prev_revenue)
        exp_change = _pct_change(curr_expenses, prev_expenses)

        # ---- top metrics list ----
        top_metrics = [
            {
                "name": "Revenue",
                "value": curr_revenue,
                "change_pct": rev_change,
                "trend": _trend(rev_change),
            },
            {
                "name": "Expenses",
                "value": curr_expenses,
                "change_pct": exp_change,
                "trend": _trend(exp_change),
            },
        ]

        # ---- anomaly detection ----
        anomalies: list[dict[str, Any]] = []
        for metric in top_metrics:
            if abs(metric["change_pct"]) > _ANOMALY_THRESHOLD_PCT:
                anomalies.append(
                    {
                        "metric": metric["name"],
                        "expected": prev_revenue
                        if metric["name"] == "Revenue"
                        else prev_expenses,
                        "actual": metric["value"],
                        "severity": "high"
                        if abs(metric["change_pct"]) > 50
                        else "medium",
                    }
                )

        # ---- executive summary ----
        executive_summary = await self._generate_executive_summary(
            curr_revenue=curr_revenue,
            prev_revenue=prev_revenue,
            rev_change=rev_change,
            curr_expenses=curr_expenses,
            anomalies=anomalies,
            currency=currency,
        )

        return {
            "period": {
                "start": curr_start.date().isoformat(),
                "end": curr_end.date().isoformat(),
                "label": f"Week of {curr_start.strftime('%b')} {curr_start.day}",
            },
            "revenue_summary": {
                "current": curr_revenue,
                "previous": prev_revenue,
                "change_pct": rev_change,
                "currency": currency,
            },
            "top_metrics": top_metrics,
            "anomalies": anomalies,
            "executive_summary": executive_summary,
            "generated_at": now.isoformat(),
        }

    def get_data_catalog_suggestions(self, provider: str) -> list[dict[str, Any]]:
        """Return report suggestions based on integration type.

        Args:
            provider: Integration provider name (e.g. 'stripe', 'shopify').

        Returns:
            List of report suggestion dicts with title, description,
            report_type, and required_data_sources.
        """
        return list(_CATALOG.get(provider.lower(), _DEFAULT_CATALOG))

    async def get_available_integrations(self, user_id: str) -> list[dict[str, Any]]:
        """Return the user's connected integrations from integration_credentials.

        Args:
            user_id: Authenticated user UUID.

        Returns:
            List of dicts with provider, account_name, connected_at.
        """
        try:
            response = await execute_async(
                self.client.table("integration_credentials")
                .select("provider, account_name, connected_at")
                .eq("user_id", user_id),
                op_name="weekly_report.get_integrations",
            )
            return [
                {
                    "provider": row.get("provider", ""),
                    "account_name": row.get("account_name", ""),
                    "connected_at": row.get("connected_at", ""),
                }
                for row in (response.data or [])
            ]
        except Exception:
            logger.exception(
                "Failed to fetch available integrations for user %s", user_id
            )
            return []

    def format_report_as_briefing_card(self, report: dict[str, Any]) -> dict[str, Any]:
        """Format the weekly report as a briefing-compatible card.

        Args:
            report: Structured report dict from generate_weekly_report.

        Returns:
            Briefing card dict with type, title, summary, generated_at, sections.
        """
        revenue = report.get("revenue_summary", {})
        anomalies = report.get("anomalies", [])

        sections = [
            {
                "id": "revenue",
                "label": "Revenue",
                "current": revenue.get("current", 0.0),
                "previous": revenue.get("previous", 0.0),
                "change_pct": revenue.get("change_pct", 0.0),
                "currency": revenue.get("currency", "USD"),
            },
        ]

        top_metrics = report.get("top_metrics", [])
        if top_metrics:
            sections.append(
                {
                    "id": "metrics",
                    "label": "Key Metrics",
                    "items": top_metrics,
                }
            )

        if anomalies:
            sections.append(
                {
                    "id": "anomalies",
                    "label": "Anomalies",
                    "items": anomalies,
                }
            )

        return {
            "type": "weekly_report",
            "title": "Weekly Business Report",
            "summary": report.get("executive_summary", ""),
            "generated_at": report.get("generated_at", ""),
            "sections": sections,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_financials(
        self,
        user_id: str,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch financial_records rows for a user within a date range.

        Args:
            user_id: Authenticated user UUID.
            start: Range start (inclusive).
            end: Range end (inclusive).

        Returns:
            List of raw row dicts.
        """
        try:
            response = await execute_async(
                self.client.table("financial_records")
                .select("transaction_type, amount, currency, transaction_date")
                .eq("user_id", user_id)
                .gte("transaction_date", start.date().isoformat())
                .lte("transaction_date", end.date().isoformat()),
                op_name="weekly_report.fetch_financials",
            )
            return response.data or []
        except Exception:
            logger.exception(
                "Failed to fetch financials for user %s (%s - %s)",
                user_id,
                start.date(),
                end.date(),
            )
            return []

    async def _generate_executive_summary(
        self,
        curr_revenue: float,
        prev_revenue: float,
        rev_change: float,
        curr_expenses: float,
        anomalies: list[dict[str, Any]],
        currency: str,
    ) -> str:
        """Generate a plain-English 3-sentence executive summary using Gemini Flash.

        Falls back to a template-based summary if the API call fails.

        Args:
            curr_revenue: Current week revenue.
            prev_revenue: Previous week revenue.
            rev_change: Week-over-week revenue change percentage.
            curr_expenses: Current week expenses.
            anomalies: List of detected anomaly dicts.
            currency: Currency code.

        Returns:
            3-sentence executive summary string.
        """
        try:
            import google.generativeai as genai

            direction = "up" if rev_change > 0 else "down" if rev_change < 0 else "flat"
            anomaly_text = (
                f" {len(anomalies)} anomalies detected requiring attention."
                if anomalies
                else " No significant anomalies this week."
            )

            prompt = (
                f"Write a concise 3-sentence executive summary for a weekly business report.\n"
                f"Revenue this week: {currency} {curr_revenue:,.2f} ({direction} {abs(rev_change):.1f}% from last week).\n"
                f"Expenses this week: {currency} {curr_expenses:,.2f}.\n"
                f"{anomaly_text}\n"
                f"Focus on the most important takeaways. Be direct and professional."
            )

            model = genai.GenerativeModel("gemini-2.5-flash")
            response = await model.generate_content_async(prompt)
            return response.text.strip()
        except Exception:
            logger.warning(
                "Gemini executive summary generation failed; using template fallback"
            )
            direction = (
                "increased"
                if rev_change > 0
                else "decreased"
                if rev_change < 0
                else "remained flat"
            )
            return (
                f"Revenue {direction} by {abs(rev_change):.1f}% this week to "
                f"{currency} {curr_revenue:,.2f}. "
                f"Total expenses were {currency} {curr_expenses:,.2f}. "
                f"{'Review the ' + str(len(anomalies)) + ' flagged anomalies for follow-up action.' if anomalies else 'No anomalies detected this week.'}"
            )
