# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""DataQueryService - Natural language data query routing and answer generation.

Routes NL questions to the correct data source (Supabase internal, Stripe,
Shopify, or external DB) and returns plain-English answers with chart-ready data.

Used by the nl_data_query tool in the Data Analysis Agent.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any

from app.services.base_service import BaseService
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Keyword maps for source routing
# ---------------------------------------------------------------------------

_FINANCIAL_KEYWORDS = frozenset(
    [
        "revenue",
        "income",
        "sales",
        "money",
        "earnings",
        "payment",
        "payments",
        "profit",
        "expense",
        "expenses",
        "invoice",
        "invoices",
        "billing",
        "charges",
        "cash",
        "financial",
        "finances",
        "cost",
        "costs",
        "spend",
        "spending",
        "budget",
    ]
)

_SUBSCRIPTION_KEYWORDS = frozenset(
    [
        "customer",
        "customers",
        "subscriber",
        "subscribers",
        "subscription",
        "subscriptions",
        "churn",
        "retention",
        "mrr",
        "arr",
        "plan",
        "plans",
        "tier",
        "tiers",
        "upgrade",
        "downgrade",
        "cancel",
        "cancellation",
    ]
)

_SHOPIFY_KEYWORDS = frozenset(
    [
        "order",
        "orders",
        "product",
        "products",
        "inventory",
        "shopify",
        "store",
        "checkout",
        "cart",
        "shipping",
        "fulfillment",
        "sku",
        "variant",
        "collection",
    ]
)

_EXTERNAL_DB_KEYWORDS = frozenset(
    [
        "sql",
        "database",
        "query my database",
        "bigquery",
        "postgres",
        "postgresql",
        "mysql",
        "snowflake",
        "redshift",
        "run a query",
        "execute",
        "select",
        "table",
    ]
)

_ANALYTICS_KEYWORDS = frozenset(
    [
        "event",
        "events",
        "tracking",
        "tracked",
        "analytics",
        "usage",
        "pageview",
        "pageviews",
        "click",
        "clicks",
        "session",
        "sessions",
        "funnel",
        "conversion",
        "activity",
        "activities",
    ]
)


def _count_keyword_matches(text: str, keywords: frozenset[str]) -> int:
    """Count how many keywords from a set appear in the lowercased text."""
    lower = text.lower()
    count = 0
    for kw in keywords:
        if re.search(r"\b" + re.escape(kw) + r"\b", lower):
            count += 1
    return count


def _parse_date_range(question: str) -> tuple[datetime | None, datetime | None]:
    """Parse natural language date expressions into start/end datetime pairs.

    Handles: "last month", "this month", "this week", "last week",
    "today", "Q1", "Q2", "Q3", "Q4", "this year", "last year".

    Returns:
        Tuple of (start_date, end_date) or (None, None) if no date found.
    """
    now = datetime.now()
    lower = question.lower()

    if "last month" in lower:
        end = now.replace(day=1) - timedelta(days=1)
        start = end.replace(day=1)
        return start, end

    if "this month" in lower or "current month" in lower:
        start = now.replace(day=1)
        next_month = (start + timedelta(days=32)).replace(day=1)
        end = next_month - timedelta(days=1)
        return start, end

    if "this week" in lower or "current week" in lower:
        start = now - timedelta(days=now.weekday())
        end = start + timedelta(days=6)
        return start, end

    if "last week" in lower:
        end = now - timedelta(days=now.weekday() + 1)
        start = end - timedelta(days=6)
        return start, end

    if "today" in lower:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
        return start, end

    if "this year" in lower or "current year" in lower:
        start = now.replace(month=1, day=1)
        end = now.replace(month=12, day=31)
        return start, end

    if "last year" in lower:
        last_year = now.year - 1
        start = datetime(last_year, 1, 1)
        end = datetime(last_year, 12, 31)
        return start, end

    for q_num, q_month in [(1, 1), (2, 4), (3, 7), (4, 10)]:
        if f"q{q_num}" in lower:
            start = now.replace(month=q_month, day=1)
            end_month = q_month + 2
            end = (start.replace(month=end_month) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            return start, end

    return None, None


class DataQueryService(BaseService):
    """Service for NL data query routing and plain-English answer generation.

    Routes natural language questions to the appropriate Supabase table or
    external data source, then formats results for the frontend.
    """

    def __init__(self, user_token: str | None = None):
        """Initialize the data query service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify_query(self, question: str) -> dict[str, Any]:
        """Classify a natural language question to the best data source.

        Uses keyword/pattern matching (not LLM) for fast, deterministic routing.

        Args:
            question: Natural language question about business data.

        Returns:
            Dictionary with source, confidence, and parsed_intent.
        """
        lower = question.lower()

        # Multi-word phrase checks first (higher specificity)
        if any(
            phrase in lower
            for phrase in (
                "sql",
                "run a query",
                "query my database",
                "my database",
                "postgres",
                "postgresql",
                "bigquery",
                "mysql",
                "snowflake",
                "redshift",
            )
        ):
            return {
                "source": "external_db",
                "confidence": 0.95,
                "parsed_intent": "external database query",
            }

        if any(
            phrase in lower
            for phrase in ("shopify", "my store", "my orders", "inventory")
        ):
            return {
                "source": "shopify",
                "confidence": 0.90,
                "parsed_intent": "shopify orders and products",
            }

        # Score each domain
        scores: dict[str, int] = {
            "financial_records": _count_keyword_matches(question, _FINANCIAL_KEYWORDS),
            "subscriptions": _count_keyword_matches(question, _SUBSCRIPTION_KEYWORDS),
            "shopify": _count_keyword_matches(question, _SHOPIFY_KEYWORDS),
            "external_db": _count_keyword_matches(question, _EXTERNAL_DB_KEYWORDS),
            "analytics_events": _count_keyword_matches(question, _ANALYTICS_KEYWORDS),
        }

        best_source = max(scores, key=lambda k: scores[k])
        best_score = scores[best_source]

        # Fallback to financial_records if no matches
        if best_score == 0:
            best_source = "financial_records"
            confidence = 0.4
        else:
            total = sum(scores.values())
            confidence = round(best_score / total, 2) if total > 0 else 0.5

        intent_map = {
            "financial_records": "revenue and financial records",
            "subscriptions": "customer subscriptions and churn",
            "shopify": "shopify orders and products",
            "external_db": "external database query",
            "analytics_events": "analytics events and usage",
        }

        return {
            "source": best_source,
            "confidence": confidence,
            "parsed_intent": intent_map.get(best_source, best_source),
        }

    async def query_internal_data(
        self, question: str, source: str, user_id: str
    ) -> dict[str, Any]:
        """Query the appropriate data source based on the classified source.

        Args:
            question: Original natural language question.
            source: Data source identifier from classify_query.
            user_id: Authenticated user's ID.

        Returns:
            Dictionary with rows, summary, chart_data, and optional message.
        """
        try:
            if source == "financial_records":
                return await self._query_financial_records(question, user_id)
            if source == "subscriptions":
                return await self._query_subscriptions(question, user_id)
            if source == "shopify":
                return await self._query_shopify(question, user_id)
            if source == "analytics_events":
                return await self._query_analytics_events(question, user_id)
            if source == "external_db":
                return await self._query_external_db(question)
            # Unknown source — fall back to financial_records
            return await self._query_financial_records(question, user_id)
        except Exception as exc:
            logger.warning("DataQueryService.query_internal_data failed: %s", exc)
            return {
                "rows": [],
                "summary": {},
                "chart_data": self.format_chart_data({}, source),
                "message": "No data found",
                "error": str(exc),
            }

    def format_nl_answer(self, raw_data: dict[str, Any], question: str) -> str:
        """Generate a plain-English answer from raw data and the original question.

        Extracts the key number from the summary and builds a 2-3 sentence
        plain-English response without calling a LLM (deterministic fallback).
        The agent itself will refine this using its generation capabilities.

        Args:
            raw_data: Structured data returned by query_internal_data.
            question: Original natural language question.

        Returns:
            Plain-English answer string with key numbers prominently displayed.
        """
        summary = raw_data.get("summary", {}) if raw_data else {}
        rows = raw_data.get("rows", []) if raw_data else []

        if not summary and not rows:
            return f"No data was found to answer: '{question}'. Please check that your data sources are connected."

        # Find the most relevant number from the summary
        key_number = None
        key_label = None

        priority_keys = [
            "total_revenue",
            "total_amount",
            "revenue",
            "total_orders",
            "order_count",
            "customer_count",
            "active_count",
            "active_subscriptions",
            "churned_count",
            "event_count",
            "total_events",
            "count",
            "total",
        ]
        for k in priority_keys:
            if k in summary and summary[k] is not None:
                key_number = summary[k]
                key_label = k.replace("_", " ").title()
                break

        if key_number is None and summary:
            first_key = next(iter(summary))
            key_number = summary[first_key]
            key_label = first_key.replace("_", " ").title()

        if key_number is None:
            key_number = len(rows)
            key_label = "records"

        # Format number nicely
        if isinstance(key_number, float):
            formatted = f"{key_number:,.2f}"
        elif isinstance(key_number, int):
            formatted = f"{key_number:,}"
        else:
            formatted = str(key_number)

        answer = f"Your {key_label} is {formatted}."

        # Add supporting detail from additional summary keys
        extra_keys = [k for k in summary if k not in priority_keys[:3] and summary[k] is not None]
        if extra_keys:
            extra_key = extra_keys[0]
            extra_val = summary[extra_key]
            if isinstance(extra_val, float):
                extra_formatted = f"{extra_val:,.2f}"
            elif isinstance(extra_val, int):
                extra_formatted = f"{extra_val:,}"
            else:
                extra_formatted = str(extra_val)
            extra_label = extra_key.replace("_", " ").title()
            answer += f" Additionally, your {extra_label} is {extra_formatted}."

        if len(rows) > 0:
            answer += f" This is based on {len(rows)} record(s) found."

        return answer

    def format_chart_data(self, raw_data: dict[str, Any], source: str) -> dict[str, Any]:
        """Extract chart-friendly data structure from raw query results.

        Chooses chart_type based on data shape:
        - Time series data -> line
        - Category comparisons -> bar
        - Proportional breakdown -> pie

        Args:
            raw_data: Structured data returned by query_internal_data.
            source: Data source identifier for chart type hints.

        Returns:
            Dictionary with chart_type, labels, values, and title.
        """
        rows = raw_data.get("rows", []) if raw_data else []
        summary = raw_data.get("summary", {}) if raw_data else {}

        title_map = {
            "financial_records": "Revenue Overview",
            "subscriptions": "Subscription Metrics",
            "shopify": "Order Summary",
            "analytics_events": "Event Analytics",
            "external_db": "Query Results",
        }
        title = title_map.get(source, "Data Overview")

        # Detect time series (rows with date-like field)
        date_fields = ["transaction_date", "created_at", "date", "period", "month"]
        value_fields = ["amount", "total", "count", "value", "revenue"]

        if rows:
            # Check for time series shape
            for df in date_fields:
                if df in (rows[0] if rows else {}):
                    for vf in value_fields:
                        if vf in (rows[0] if rows else {}):
                            labels = [str(r.get(df, "")) for r in rows]
                            values = [float(r.get(vf, 0) or 0) for r in rows]
                            return {
                                "chart_type": "line",
                                "labels": labels,
                                "values": values,
                                "title": title,
                            }

            # Category bar chart — use first string field as label, first numeric as value
            first_row = rows[0]
            str_keys = [k for k, v in first_row.items() if isinstance(v, str)]
            num_keys = [k for k, v in first_row.items() if isinstance(v, (int, float))]
            if str_keys and num_keys:
                labels = [str(r.get(str_keys[0], "")) for r in rows]
                values = [float(r.get(num_keys[0], 0) or 0) for r in rows]
                return {
                    "chart_type": "bar",
                    "labels": labels,
                    "values": values,
                    "title": title,
                }

        # Fall back to summary-based single bar chart
        if summary:
            labels = [k.replace("_", " ").title() for k in summary]
            values = [float(v) if isinstance(v, (int, float)) else 0.0 for v in summary.values()]
            chart_type = "pie" if len(labels) > 1 else "bar"
            return {
                "chart_type": chart_type,
                "labels": labels,
                "values": values,
                "title": title,
            }

        # Empty fallback
        return {
            "chart_type": "bar",
            "labels": [],
            "values": [],
            "title": title,
        }

    # ------------------------------------------------------------------
    # Private query methods
    # ------------------------------------------------------------------

    async def _query_financial_records(
        self, question: str, user_id: str
    ) -> dict[str, Any]:
        """Query financial_records table with date filtering."""
        start_date, end_date = _parse_date_range(question)

        query = self.client.table("financial_records").select(
            "amount, currency, transaction_type, transaction_date, description"
        )
        query = query.eq("user_id", user_id)

        if start_date:
            query = query.gte("transaction_date", start_date.isoformat())
        if end_date:
            query = query.lte("transaction_date", end_date.isoformat())

        response = await execute_async(query)
        rows = response.data or []

        # Aggregate revenue and expenses
        total_revenue = sum(
            float(r.get("amount", 0) or 0)
            for r in rows
            if r.get("transaction_type") == "revenue"
        )
        total_expenses = sum(
            float(r.get("amount", 0) or 0)
            for r in rows
            if r.get("transaction_type") in ("expense", "cost")
        )
        currency = rows[0].get("currency", "USD") if rows else "USD"

        summary: dict[str, Any] = {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "transaction_count": len(rows),
            "currency": currency,
        }

        if not rows:
            summary["message"] = "No data found"

        return {
            "rows": rows,
            "summary": summary,
            "chart_data": self.format_chart_data({"rows": rows, "summary": summary}, "financial_records"),
        }

    async def _query_subscriptions(
        self, question: str, user_id: str
    ) -> dict[str, Any]:
        """Query subscriptions table for customer/churn counts."""
        start_date, end_date = _parse_date_range(question)

        query = self.client.table("subscriptions").select(
            "id, status, created_at, plan_name"
        )
        query = query.eq("user_id", user_id)

        if start_date:
            query = query.gte("created_at", start_date.isoformat())
        if end_date:
            query = query.lte("created_at", end_date.isoformat())

        response = await execute_async(query)
        rows = response.data or []

        active_count = sum(1 for r in rows if r.get("status") == "active")
        churned_count = sum(1 for r in rows if r.get("status") in ("canceled", "cancelled", "churned"))
        customer_count = len(rows)

        summary: dict[str, Any] = {
            "customer_count": customer_count,
            "active_subscriptions": active_count,
            "churned_count": churned_count,
        }

        if not rows:
            summary["message"] = "No data found"

        return {
            "rows": rows,
            "summary": summary,
            "chart_data": self.format_chart_data({"rows": rows, "summary": summary}, "subscriptions"),
        }

    async def _query_shopify(
        self, question: str, user_id: str
    ) -> dict[str, Any]:
        """Query shopify_orders table with date filtering."""
        start_date, end_date = _parse_date_range(question)

        query = self.client.table("shopify_orders").select(
            "id, total_price, currency, created_at, financial_status, fulfillment_status"
        )
        query = query.eq("user_id", user_id)

        if start_date:
            query = query.gte("created_at", start_date.isoformat())
        if end_date:
            query = query.lte("created_at", end_date.isoformat())

        response = await execute_async(query)
        rows = response.data or []

        total_revenue = sum(float(r.get("total_price", 0) or 0) for r in rows)
        order_count = len(rows)
        currency = rows[0].get("currency", "USD") if rows else "USD"

        summary: dict[str, Any] = {
            "order_count": order_count,
            "total_amount": total_revenue,
            "currency": currency,
        }

        if not rows:
            summary["message"] = "No data found"

        return {
            "rows": rows,
            "summary": summary,
            "chart_data": self.format_chart_data({"rows": rows, "summary": summary}, "shopify"),
        }

    async def _query_analytics_events(
        self, question: str, user_id: str
    ) -> dict[str, Any]:
        """Query analytics_events table for event counts and top events."""
        start_date, end_date = _parse_date_range(question)

        query = self.client.table("analytics_events").select(
            "event_name, category, created_at, properties"
        )
        query = query.eq("user_id", user_id)

        if start_date:
            query = query.gte("created_at", start_date.isoformat())
        if end_date:
            query = query.lte("created_at", end_date.isoformat())

        response = await execute_async(query.order("created_at", desc=True).limit(200))
        rows = response.data or []

        # Count events by name
        event_counts: dict[str, int] = {}
        for r in rows:
            name = r.get("event_name", "unknown")
            event_counts[name] = event_counts.get(name, 0) + 1

        top_events = sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        summary: dict[str, Any] = {
            "total_events": len(rows),
            "unique_event_types": len(event_counts),
        }

        if not rows:
            summary["message"] = "No data found"

        chart_rows = [{"event": name, "count": cnt} for name, cnt in top_events]

        return {
            "rows": rows,
            "summary": summary,
            "chart_data": self.format_chart_data(
                {"rows": chart_rows, "summary": summary}, "analytics_events"
            ),
        }

    async def _query_external_db(self, question: str) -> dict[str, Any]:
        """Delegate to external_db_query for SQL-style questions."""
        from app.agents.tools.external_db_tools import external_db_query

        result = await external_db_query(question)
        rows = result.get("rows", [])
        columns = result.get("columns", [])

        # Convert to list of dicts if rows are plain lists
        if rows and isinstance(rows[0], list):
            rows = [dict(zip(columns, row)) for row in rows]

        summary = {
            "row_count": result.get("row_count", len(rows)),
            "nl_summary": result.get("nl_summary", ""),
        }

        return {
            "rows": rows,
            "summary": summary,
            "chart_data": self.format_chart_data(
                {"rows": rows, "summary": {}}, "external_db"
            ),
            "sql_generated": result.get("sql_generated", ""),
        }
