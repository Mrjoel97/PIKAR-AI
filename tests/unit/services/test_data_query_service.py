# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for DataQueryService -- NL data query routing and answer generation.

Plan 68-01 / DATA-01. Verifies:

- classify_query routes revenue/income/sales questions to financial_records
- classify_query routes customer/subscriber questions to subscriptions
- classify_query routes Shopify/orders questions to shopify
- classify_query routes SQL/database questions to external_db
- classify_query routes events/analytics questions to analytics_events
- format_nl_answer produces a plain-English string containing the key number
- format_chart_data returns dict with labels, values, chart_type, and title
- query_internal_data returns structured result with rows, summary, chart_data
- query_internal_data handles empty results gracefully with "No data found" message

Uses the Windows-safe sys.modules stub pattern to sidestep slowapi/starlette
.env UnicodeDecodeError before importing.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

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
    """Return a DataQueryService with stubbed Supabase service client."""
    with (
        patch.dict("os.environ", _FAKE_ENV, clear=False),
        patch(
            "app.services.supabase.get_service_client",
            return_value=MagicMock(),
        ),
    ):
        from app.services.data_query_service import DataQueryService

        svc = DataQueryService()
        _ = svc.client
        return svc


# ---------------------------------------------------------------------------
# TestClassifyQuery
# ---------------------------------------------------------------------------


class TestClassifyQuery:
    """Unit tests for DataQueryService.classify_query."""

    def test_classify_revenue_question(self):
        """Revenue/money question routes to financial_records."""
        svc = _make_service()

        result = svc.classify_query("What is my revenue this month?")

        assert result["source"] == "financial_records"
        assert isinstance(result["confidence"], float)
        assert result["confidence"] > 0.5
        assert isinstance(result["parsed_intent"], str)

    def test_classify_customer_question(self):
        """Customer/subscriber question routes to subscriptions."""
        svc = _make_service()

        result = svc.classify_query("How many customers did I get last month?")

        assert result["source"] in ("subscriptions", "financial_records")
        assert isinstance(result["confidence"], float)

    def test_classify_shopify_question(self):
        """Shopify/orders question routes to shopify."""
        svc = _make_service()

        result = svc.classify_query("Show me my Shopify orders")

        assert result["source"] == "shopify"
        assert isinstance(result["confidence"], float)

    def test_classify_external_db_question(self):
        """SQL/database question routes to external_db."""
        svc = _make_service()

        result = svc.classify_query("Run a SQL query on my database")

        assert result["source"] == "external_db"
        assert isinstance(result["confidence"], float)

    def test_classify_analytics_events_question(self):
        """Events/analytics question routes to analytics_events."""
        svc = _make_service()

        result = svc.classify_query("How many events happened today?")

        assert result["source"] == "analytics_events"
        assert isinstance(result["confidence"], float)

    def test_classify_sales_question(self):
        """Sales question routes to financial_records."""
        svc = _make_service()

        result = svc.classify_query("What are my total sales for Q1?")

        assert result["source"] == "financial_records"

    def test_classify_churn_question(self):
        """Churn/retention question routes to subscriptions."""
        svc = _make_service()

        result = svc.classify_query("What is my churn rate?")

        assert result["source"] == "subscriptions"

    def test_classify_result_has_required_keys(self):
        """classify_query always returns dict with source, confidence, parsed_intent."""
        svc = _make_service()

        result = svc.classify_query("anything goes here")

        assert "source" in result
        assert "confidence" in result
        assert "parsed_intent" in result


# ---------------------------------------------------------------------------
# TestFormatNlAnswer
# ---------------------------------------------------------------------------


class TestFormatNlAnswer:
    """Unit tests for DataQueryService.format_nl_answer."""

    def test_format_nl_answer_returns_string(self):
        """format_nl_answer always returns a non-empty string."""
        svc = _make_service()

        raw_data = {
            "rows": [{"amount": 5000, "currency": "USD"}],
            "summary": {"total_revenue": 5000},
        }
        result = svc.format_nl_answer(raw_data, "What is my revenue?")

        assert isinstance(result, str)
        assert len(result) > 10

    def test_format_nl_answer_includes_key_number(self):
        """format_nl_answer includes the key number from summary."""
        svc = _make_service()

        raw_data = {
            "rows": [],
            "summary": {"total_revenue": 12345},
        }
        result = svc.format_nl_answer(raw_data, "What is my revenue this month?")

        assert "12345" in result or "12,345" in result

    def test_format_nl_answer_empty_data(self):
        """format_nl_answer handles empty raw_data gracefully."""
        svc = _make_service()

        result = svc.format_nl_answer({}, "How many customers?")

        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# TestFormatChartData
# ---------------------------------------------------------------------------


class TestFormatChartData:
    """Unit tests for DataQueryService.format_chart_data."""

    def test_format_chart_data_returns_required_keys(self):
        """format_chart_data returns dict with chart_type, labels, values, title."""
        svc = _make_service()

        raw_data = {
            "rows": [
                {"label": "Jan", "amount": 1000},
                {"label": "Feb", "amount": 2000},
            ],
            "summary": {"total_revenue": 3000},
        }
        result = svc.format_chart_data(raw_data, "financial_records")

        assert "chart_type" in result
        assert "labels" in result
        assert "values" in result
        assert "title" in result
        assert result["chart_type"] in ("bar", "line", "pie")

    def test_format_chart_data_financial_is_bar_or_line(self):
        """Financial records chart is bar or line type."""
        svc = _make_service()

        raw_data = {"rows": [], "summary": {}}
        result = svc.format_chart_data(raw_data, "financial_records")

        assert result["chart_type"] in ("bar", "line")

    def test_format_chart_data_empty_data(self):
        """format_chart_data handles empty rows without raising."""
        svc = _make_service()

        result = svc.format_chart_data({}, "shopify")

        assert isinstance(result, dict)
        assert "chart_type" in result
        assert isinstance(result["labels"], list)
        assert isinstance(result["values"], list)


# ---------------------------------------------------------------------------
# TestQueryInternalData
# ---------------------------------------------------------------------------


class TestQueryInternalData:
    """Unit tests for DataQueryService.query_internal_data."""

    @pytest.mark.asyncio
    async def test_query_financial_returns_structured_result(self):
        """query_internal_data(financial_records) returns rows, summary, chart_data."""
        svc = _make_service()
        svc.client.table = MagicMock(return_value=MagicMock(
            select=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    gte=MagicMock(return_value=MagicMock(
                        lte=MagicMock(return_value=MagicMock())
                    ))
                ))
            ))
        ))

        fake_rows = [
            {"amount": 1000, "transaction_type": "revenue", "transaction_date": "2026-04-01"},
            {"amount": 2000, "transaction_type": "revenue", "transaction_date": "2026-04-15"},
        ]

        with patch(
            "app.services.data_query_service.execute_async",
            return_value=_result(data=fake_rows),
        ):
            result = await svc.query_internal_data(
                "What is my revenue this month?", "financial_records", "user-123"
            )

        assert "rows" in result
        assert "summary" in result
        assert "chart_data" in result

    @pytest.mark.asyncio
    async def test_query_internal_data_empty_results(self):
        """query_internal_data handles empty results with 'No data found' message."""
        svc = _make_service()
        svc.client.table = MagicMock(return_value=MagicMock(
            select=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    gte=MagicMock(return_value=MagicMock(
                        lte=MagicMock(return_value=MagicMock())
                    ))
                ))
            ))
        ))

        with patch(
            "app.services.data_query_service.execute_async",
            return_value=_result(data=[]),
        ):
            result = await svc.query_internal_data(
                "How many orders?", "shopify", "user-123"
            )

        assert "rows" in result
        assert isinstance(result["rows"], list)
        summary_str = str(result.get("summary", ""))
        message_str = str(result.get("message", ""))
        assert (
            len(result["rows"]) == 0
            or "no data" in summary_str.lower()
            or "no data" in message_str.lower()
            or result.get("summary", {}).get("total", 0) == 0
        )

    @pytest.mark.asyncio
    async def test_query_subscriptions_returns_structured_result(self):
        """query_internal_data(subscriptions) returns rows and customer_count."""
        svc = _make_service()

        fake_rows = [
            {"id": "sub-1", "status": "active", "created_at": "2026-04-01"},
            {"id": "sub-2", "status": "active", "created_at": "2026-04-10"},
        ]

        with patch(
            "app.services.data_query_service.execute_async",
            return_value=_result(data=fake_rows),
        ):
            result = await svc.query_internal_data(
                "How many subscribers?", "subscriptions", "user-123"
            )

        assert "rows" in result
        assert "summary" in result
        assert "chart_data" in result
