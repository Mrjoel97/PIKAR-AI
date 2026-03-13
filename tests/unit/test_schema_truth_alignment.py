from __future__ import annotations

import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.agents.financial.tools import _query_financial_records
from app.services.dashboard_summary_service import DashboardSummaryService
from app.services.financial_service import FinancialService


class FakeQuery:
    def __init__(self, rows: list[dict]):
        self._rows = rows
        self.select_fields: str | None = None
        self.eq_calls: list[tuple[str, object]] = []
        self.gte_calls: list[tuple[str, object]] = []
        self.lte_calls: list[tuple[str, object]] = []
        self.order_calls: list[tuple[str, bool]] = []
        self.limit_value: int | None = None

    def select(self, fields: str):
        self.select_fields = fields
        return self

    def eq(self, field: str, value: object):
        self.eq_calls.append((field, value))
        return self

    def gte(self, field: str, value: object):
        self.gte_calls.append((field, value))
        return self

    def lte(self, field: str, value: object):
        self.lte_calls.append((field, value))
        return self

    def order(self, field: str, desc: bool = False):
        self.order_calls.append((field, desc))
        return self

    def limit(self, value: int):
        self.limit_value = value
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows)


class FakeClient:
    def __init__(self, rows: list[dict]):
        self.query = FakeQuery(rows)
        self.tables: list[str] = []

    def table(self, name: str):
        self.tables.append(name)
        return self.query


@pytest.mark.asyncio
@patch.dict(os.environ, {"SUPABASE_URL": "http://test", "SUPABASE_ANON_KEY": "anon"}, clear=False)
@patch("app.services.base_service.create_client")
async def test_financial_service_uses_transaction_type(mock_create_client):
    client = FakeClient([
        {
            "amount": 125.5,
            "currency": "USD",
            "transaction_date": "2026-03-01T12:00:00+00:00",
            "description": "Monthly subscription",
        }
    ])
    mock_create_client.return_value = client

    service = FinancialService()
    result = await service.get_revenue_stats("current_month")

    assert client.tables == ["financial_records"]
    assert client.query.select_fields == "amount, currency, transaction_date, description"
    assert ("transaction_type", "revenue") in client.query.eq_calls
    assert result["revenue"] == 125.5
    assert result["currency"] == "USD"


@pytest.mark.asyncio
@patch.dict(os.environ, {"SUPABASE_URL": "http://test", "SUPABASE_ANON_KEY": "anon"}, clear=False)
@patch("app.services.base_service.create_client")
async def test_financial_tools_query_uses_transaction_type(mock_create_client):
    client = FakeClient([])
    mock_create_client.return_value = client

    rows = await _query_financial_records(
        user_id="user-1",
        record_type="expense",
        days_back=30,
        limit=10,
    )

    assert rows == []
    assert client.tables == ["financial_records"]
    assert client.query.select_fields == (
        "id, user_id, amount, transaction_type, currency, transaction_date, description"
    )
    assert ("user_id", "user-1") in client.query.eq_calls
    assert ("transaction_type", "expense") in client.query.eq_calls
    assert client.query.limit_value == 10


def test_dashboard_financial_summary_uses_transaction_type():
    now = datetime.now(timezone.utc)
    client = FakeClient(
        [
            {
                "amount": 200.0,
                "transaction_type": "revenue",
                "currency": "USD",
                "transaction_date": now.isoformat(),
            },
            {
                "amount": 60.0,
                "transaction_type": "expense",
                "currency": "USD",
                "transaction_date": now.isoformat(),
            },
        ]
    )

    with patch("app.services.dashboard_summary_service.get_service_client", return_value=client):
        service = DashboardSummaryService()
        summary = service._financial_summary("user-1")

    assert client.tables == ["financial_records"]
    assert client.query.select_fields == "amount, transaction_type, currency, transaction_date"
    assert ("user_id", "user-1") in client.query.eq_calls
    assert summary["revenue"] == 200.0
    assert summary["cash_position"] == 140.0
    assert summary["monthly_burn"] == 20.0
