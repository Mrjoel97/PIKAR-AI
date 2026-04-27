# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests verifying SQL COUNT aggregation in analytics_aggregator.

These tests assert that run_daily_aggregation uses SELECT COUNT (via
count="exact") rather than fetching full rows and counting in Python.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.analytics_aggregator import _extract_count, run_daily_aggregation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_count_result(count: int) -> MagicMock:
    """Simulate a Supabase query result with result.count set."""
    result = MagicMock()
    result.count = count
    result.data = []
    return result


def _make_row_result(rows: list[dict]) -> MagicMock:
    """Simulate a Supabase query result with rows (legacy shape)."""
    result = MagicMock()
    result.count = None
    result.data = rows
    return result


def _make_client(
    dau_count: int = 5,
    mau_count: int = 20,
    messages_count: int = 100,
    workflows_count: int = 10,
) -> MagicMock:
    """Build a mock Supabase client.

    Patches execute_async to return appropriate mock results.
    """
    dau_result = _make_count_result(dau_count)
    mau_result = _make_count_result(mau_count)
    messages_result = _make_count_result(messages_count)
    workflows_result = _make_count_result(workflows_count)
    # agent_telemetry returns rows for Python-side aggregation
    agent_result = MagicMock()
    agent_result.count = None
    agent_result.data = []

    return [dau_result, mau_result, messages_result, workflows_result, agent_result]


# ---------------------------------------------------------------------------
# _extract_count unit tests
# ---------------------------------------------------------------------------


class TestExtractCount:
    """Unit tests for the _extract_count helper."""

    def test_reads_count_attribute_when_present(self):
        """A1: _extract_count reads result.count (count='exact' shape)."""
        result = MagicMock()
        result.count = 42
        result.data = []
        assert _extract_count(result) == 42

    def test_returns_zero_when_count_is_none(self):
        """A3: _extract_count returns 0 when result.count is None and data is empty."""
        result = MagicMock()
        result.count = None
        result.data = []
        assert _extract_count(result) == 0

    def test_returns_zero_when_count_is_zero(self):
        """A3: _extract_count returns 0 when result.count == 0."""
        result = MagicMock()
        result.count = 0
        result.data = []
        assert _extract_count(result) == 0

    def test_falls_back_to_legacy_dict_count_key(self):
        """_extract_count handles [{count: N}] legacy shape when result.count is None."""
        result = MagicMock()
        result.count = None
        result.data = [{"count": 7}]
        assert _extract_count(result) == 7

    def test_falls_back_to_len_data_when_no_count(self):
        """_extract_count falls back to len(data) when no count attribute or dict."""
        result = MagicMock()
        result.count = None
        result.data = [{"id": 1}, {"id": 2}, {"id": 3}]
        assert _extract_count(result) == 3

    def test_count_attribute_takes_priority_over_data(self):
        """result.count takes priority over data rows."""
        result = MagicMock()
        result.count = 99
        result.data = [{"id": 1}, {"id": 2}]
        assert _extract_count(result) == 99


# ---------------------------------------------------------------------------
# run_daily_aggregation integration tests (mocked Supabase)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dau_query_uses_count_exact():
    """A1: run_daily_aggregation DAU query uses select('*', count='exact').limit(0)."""
    call_args_list: list[Any] = []

    def fake_select(*args, **kwargs):
        call_args_list.append(("select", args, kwargs))
        builder = MagicMock()
        # Chain methods — each returns a builder
        builder.gte.return_value = builder
        builder.lt.return_value = builder
        builder.limit.return_value = builder
        builder.select.return_value = builder
        return builder

    count_result = _make_count_result(3)

    async def fake_execute_async(query, op_name=""):
        if "analytics.dau" in op_name:
            return count_result
        if "analytics.mau" in op_name:
            return _make_count_result(15)
        if "analytics.messages" in op_name:
            return _make_count_result(50)
        if "analytics.workflows" in op_name:
            return _make_count_result(5)
        # agent_telemetry and upserts
        mock_r = MagicMock()
        mock_r.count = None
        mock_r.data = []
        return mock_r

    client_mock = MagicMock()
    session_table = MagicMock()
    session_table.select = fake_select
    client_mock.table.return_value = session_table

    with (
        patch(
            "app.services.analytics_aggregator.get_service_client",
            return_value=client_mock,
        ),
        patch(
            "app.services.analytics_aggregator.execute_async",
            side_effect=fake_execute_async,
        ),
    ):
        result = await run_daily_aggregation("2026-04-01")

    # Verify a select call used count="exact"
    count_calls = [
        (args, kwargs)
        for name, args, kwargs in call_args_list
        if kwargs.get("count") == "exact"
    ]
    assert len(count_calls) >= 1, (
        "Expected at least one select('*', count='exact') call for DAU"
    )


@pytest.mark.asyncio
async def test_run_daily_aggregation_uses_result_count_for_dau_mau_messages_workflows():
    """A2: DAU/MAU/messages/workflows values come from result.count, not len(result.data)."""
    results = {
        "analytics.dau": _make_count_result(7),
        "analytics.mau": _make_count_result(31),
        "analytics.messages": _make_count_result(200),
        "analytics.workflows": _make_count_result(15),
    }

    async def fake_execute_async(query, op_name=""):
        if op_name in results:
            return results[op_name]
        mock_r = MagicMock()
        mock_r.count = None
        mock_r.data = []
        return mock_r

    client_mock = MagicMock()
    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.gte.return_value = table_mock
    table_mock.lt.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.upsert.return_value = table_mock
    client_mock.table.return_value = table_mock

    upserted_rows: list[dict] = []

    async def capturing_execute_async(query, op_name=""):
        if op_name in results:
            return results[op_name]
        if op_name == "analytics.upsert_daily":
            # Capture the upserted row to verify values
            upserted_rows.append(query)
        mock_r = MagicMock()
        mock_r.count = None
        mock_r.data = []
        return mock_r

    # We need to capture the analytics row values — patch upsert call
    captured: dict = {}

    original_upsert = MagicMock()

    def spy_upsert(row, on_conflict=None):
        if "dau" in row:
            captured.update(row)
        return table_mock

    table_mock.upsert = spy_upsert

    with (
        patch(
            "app.services.analytics_aggregator.get_service_client",
            return_value=client_mock,
        ),
        patch(
            "app.services.analytics_aggregator.execute_async",
            side_effect=capturing_execute_async,
        ),
    ):
        await run_daily_aggregation("2026-04-01")

    # Values should come from result.count, not len()
    assert captured.get("dau") == 7, f"Expected dau=7, got {captured.get('dau')}"
    assert captured.get("mau") == 31, f"Expected mau=31, got {captured.get('mau')}"
    assert captured.get("messages") == 200, (
        f"Expected messages=200, got {captured.get('messages')}"
    )
    assert captured.get("workflows") == 15, (
        f"Expected workflows=15, got {captured.get('workflows')}"
    )


@pytest.mark.asyncio
async def test_run_daily_aggregation_defaults_to_yesterday():
    """run_daily_aggregation with no args uses yesterday's date."""
    from datetime import date, timedelta

    yesterday = (date.today() - timedelta(days=1)).isoformat()

    async def fake_execute_async(query, op_name=""):
        mock_r = MagicMock()
        mock_r.count = 0
        mock_r.data = []
        return mock_r

    client_mock = MagicMock()
    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.gte.return_value = table_mock
    table_mock.lt.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.upsert.return_value = table_mock
    client_mock.table.return_value = table_mock

    with (
        patch(
            "app.services.analytics_aggregator.get_service_client",
            return_value=client_mock,
        ),
        patch(
            "app.services.analytics_aggregator.execute_async",
            side_effect=fake_execute_async,
        ),
    ):
        result = await run_daily_aggregation()

    assert result["date"] == yesterday
