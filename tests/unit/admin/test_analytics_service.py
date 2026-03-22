"""Unit tests for analytics aggregation service.

Tests verify:
- run_daily_aggregation returns dict with date and rows_written > 0 when data exists
- run_daily_aggregation upserts correct dau/mau/messages/workflows to admin_analytics_daily
- run_daily_aggregation upserts per-agent success/error/timeout counts to admin_agent_stats_daily
- run_daily_aggregation handles empty source tables gracefully (zero-valued upsert)
- run_daily_aggregation is idempotent (can be called twice for same date without error)
- run_daily_aggregation accepts optional stat_date parameter (defaults to yesterday UTC)
"""

from datetime import date, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

# Patch targets
_SERVICE_CLIENT_PATCH = "app.services.analytics_aggregator.get_service_client"
_EXECUTE_ASYNC_PATCH = "app.services.analytics_aggregator.execute_async"


def _make_count_result(count: int) -> MagicMock:
    """Build a mock result whose .data[0]["count"] == count."""
    result = MagicMock()
    result.data = [{"count": count}]
    return result


def _make_agent_rows(agents: list[dict]) -> MagicMock:
    """Build a mock result for agent_telemetry group queries."""
    result = MagicMock()
    result.data = agents
    return result


def _make_upsert_result(rows_written: int = 1) -> MagicMock:
    """Build a mock upsert result."""
    result = MagicMock()
    result.data = [{"id": f"row-{i}"} for i in range(rows_written)]
    return result


# =========================================================================
# Test 1: returns dict with date and rows_written > 0 when data exists
# =========================================================================


@pytest.mark.asyncio
async def test_run_daily_aggregation_returns_result_dict():
    """run_daily_aggregation with data returns dict with date and rows_written > 0."""
    from app.services.analytics_aggregator import run_daily_aggregation

    mock_client = MagicMock()

    # Set up query chain mocks
    sessions_chain = MagicMock()
    sessions_chain.select.return_value = sessions_chain
    sessions_chain.gte.return_value = sessions_chain
    sessions_chain.lt.return_value = sessions_chain
    sessions_chain.eq.return_value = sessions_chain

    events_chain = MagicMock()
    events_chain.select.return_value = events_chain
    events_chain.gte.return_value = events_chain
    events_chain.lt.return_value = events_chain

    workflows_chain = MagicMock()
    workflows_chain.select.return_value = workflows_chain
    workflows_chain.gte.return_value = workflows_chain
    workflows_chain.lt.return_value = workflows_chain

    agent_chain = MagicMock()
    agent_chain.select.return_value = agent_chain
    agent_chain.gte.return_value = agent_chain
    agent_chain.lt.return_value = agent_chain

    upsert_analytics_chain = MagicMock()
    upsert_agent_chain = MagicMock()

    def fake_table(name):
        if name == "sessions":
            return sessions_chain
        if name == "session_events":
            return events_chain
        if name == "workflow_executions":
            return workflows_chain
        if name == "agent_telemetry":
            return agent_chain
        if name == "admin_analytics_daily":
            return upsert_analytics_chain
        if name == "admin_agent_stats_daily":
            return upsert_agent_chain
        return MagicMock()

    mock_client.table.side_effect = fake_table

    call_count = {"n": 0}

    async def fake_execute_async(query, **kwargs):
        call_count["n"] += 1
        # Queries 1-3: dau (sessions), mau (sessions), messages (session_events)
        # Query 4: workflows
        # Query 5: agent_telemetry
        # Query 6+: upserts
        n = call_count["n"]
        if n == 1:  # DAU
            return _make_count_result(5)
        if n == 2:  # MAU
            return _make_count_result(42)
        if n == 3:  # messages
            return _make_count_result(100)
        if n == 4:  # workflows
            return _make_count_result(10)
        if n == 5:  # agent_telemetry
            return _make_agent_rows([
                {
                    "agent_name": "financial",
                    "success_count": 8,
                    "error_count": 1,
                    "timeout_count": 0,
                    "avg_duration_ms": 250.5,
                    "total_calls": 9,
                }
            ])
        # Upsert calls
        return _make_upsert_result(1)

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client), patch(
        _EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async
    ):
        result = await run_daily_aggregation("2026-03-21")

    assert isinstance(result, dict)
    assert "date" in result
    assert result["date"] == "2026-03-21"
    assert "rows_written" in result
    assert result["rows_written"] > 0


# =========================================================================
# Test 2: upserts correct values to admin_analytics_daily
# =========================================================================


@pytest.mark.asyncio
async def test_run_daily_aggregation_upserts_correct_analytics_values():
    """run_daily_aggregation upserts dau/mau/messages/workflows to admin_analytics_daily."""
    from app.services.analytics_aggregator import run_daily_aggregation

    mock_client = MagicMock()
    upsert_calls = []

    sessions_chain = MagicMock()
    sessions_chain.select.return_value = sessions_chain
    sessions_chain.gte.return_value = sessions_chain
    sessions_chain.lt.return_value = sessions_chain

    events_chain = MagicMock()
    events_chain.select.return_value = events_chain
    events_chain.gte.return_value = events_chain
    events_chain.lt.return_value = events_chain

    workflows_chain = MagicMock()
    workflows_chain.select.return_value = workflows_chain
    workflows_chain.gte.return_value = workflows_chain
    workflows_chain.lt.return_value = workflows_chain

    agent_chain = MagicMock()
    agent_chain.select.return_value = agent_chain
    agent_chain.gte.return_value = agent_chain
    agent_chain.lt.return_value = agent_chain

    analytics_table_mock = MagicMock()

    def fake_upsert(data, **kwargs):
        upsert_calls.append(("admin_analytics_daily", data))
        return MagicMock()

    analytics_table_mock.upsert = fake_upsert

    agent_stats_table_mock = MagicMock()

    def fake_agent_upsert(data, **kwargs):
        upsert_calls.append(("admin_agent_stats_daily", data))
        return MagicMock()

    agent_stats_table_mock.upsert = fake_agent_upsert

    def fake_table(name):
        if name == "sessions":
            return sessions_chain
        if name == "session_events":
            return events_chain
        if name == "workflow_executions":
            return workflows_chain
        if name == "agent_telemetry":
            return agent_chain
        if name == "admin_analytics_daily":
            return analytics_table_mock
        if name == "admin_agent_stats_daily":
            return agent_stats_table_mock
        return MagicMock()

    mock_client.table.side_effect = fake_table

    call_count = {"n": 0}

    async def fake_execute_async(query, **kwargs):
        call_count["n"] += 1
        n = call_count["n"]
        if n == 1:
            return _make_count_result(7)   # DAU
        if n == 2:
            return _make_count_result(30)  # MAU
        if n == 3:
            return _make_count_result(200) # messages
        if n == 4:
            return _make_count_result(15)  # workflows
        if n == 5:
            return _make_agent_rows([])    # no agents
        return _make_upsert_result(1)

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client), patch(
        _EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async
    ):
        await run_daily_aggregation("2026-03-21")

    # Find the analytics daily upsert call
    analytics_upserts = [d for tbl, d in upsert_calls if tbl == "admin_analytics_daily"]
    assert len(analytics_upserts) == 1, "Should upsert exactly one row to admin_analytics_daily"

    upserted = analytics_upserts[0]
    assert upserted["stat_date"] == "2026-03-21"
    assert upserted["dau"] == 7
    assert upserted["mau"] == 30
    assert upserted["messages"] == 200
    assert upserted["workflows"] == 15


# =========================================================================
# Test 3: upserts per-agent stats to admin_agent_stats_daily
# =========================================================================


@pytest.mark.asyncio
async def test_run_daily_aggregation_upserts_per_agent_stats():
    """run_daily_aggregation upserts per-agent success/error/timeout counts."""
    from app.services.analytics_aggregator import run_daily_aggregation

    mock_client = MagicMock()
    agent_upsert_calls = []

    sessions_chain = MagicMock()
    sessions_chain.select.return_value = sessions_chain
    sessions_chain.gte.return_value = sessions_chain
    sessions_chain.lt.return_value = sessions_chain

    events_chain = MagicMock()
    events_chain.select.return_value = events_chain
    events_chain.gte.return_value = events_chain
    events_chain.lt.return_value = events_chain

    workflows_chain = MagicMock()
    workflows_chain.select.return_value = workflows_chain
    workflows_chain.gte.return_value = workflows_chain
    workflows_chain.lt.return_value = workflows_chain

    agent_chain = MagicMock()
    agent_chain.select.return_value = agent_chain
    agent_chain.gte.return_value = agent_chain
    agent_chain.lt.return_value = agent_chain

    analytics_table_mock = MagicMock()
    analytics_table_mock.upsert.return_value = MagicMock()

    agent_stats_table_mock = MagicMock()

    def fake_agent_upsert(data, **kwargs):
        agent_upsert_calls.append(data)
        return MagicMock()

    agent_stats_table_mock.upsert = fake_agent_upsert

    def fake_table(name):
        if name == "sessions":
            return sessions_chain
        if name == "session_events":
            return events_chain
        if name == "workflow_executions":
            return workflows_chain
        if name == "agent_telemetry":
            return agent_chain
        if name == "admin_analytics_daily":
            return analytics_table_mock
        if name == "admin_agent_stats_daily":
            return agent_stats_table_mock
        return MagicMock()

    mock_client.table.side_effect = fake_table

    call_count = {"n": 0}

    async def fake_execute_async(query, **kwargs):
        call_count["n"] += 1
        n = call_count["n"]
        if n <= 4:
            return _make_count_result(0)
        if n == 5:
            return _make_agent_rows([
                {
                    "agent_name": "financial",
                    "success_count": 10,
                    "error_count": 2,
                    "timeout_count": 1,
                    "avg_duration_ms": 300.0,
                    "total_calls": 13,
                },
                {
                    "agent_name": "content",
                    "success_count": 5,
                    "error_count": 0,
                    "timeout_count": 0,
                    "avg_duration_ms": 150.0,
                    "total_calls": 5,
                },
            ])
        return _make_upsert_result(1)

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client), patch(
        _EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async
    ):
        await run_daily_aggregation("2026-03-21")

    assert len(agent_upsert_calls) == 2, "Should upsert one row per agent"

    financial = next((r for r in agent_upsert_calls if r["agent_name"] == "financial"), None)
    assert financial is not None
    assert financial["stat_date"] == "2026-03-21"
    assert financial["success_count"] == 10
    assert financial["error_count"] == 2
    assert financial["timeout_count"] == 1
    assert financial["total_calls"] == 13

    content = next((r for r in agent_upsert_calls if r["agent_name"] == "content"), None)
    assert content is not None
    assert content["success_count"] == 5
    assert content["total_calls"] == 5


# =========================================================================
# Test 4: handles empty source tables gracefully
# =========================================================================


@pytest.mark.asyncio
async def test_run_daily_aggregation_handles_empty_source_tables():
    """run_daily_aggregation handles empty source tables (zero-valued upsert, no error)."""
    from app.services.analytics_aggregator import run_daily_aggregation

    mock_client = MagicMock()
    upsert_calls = []

    generic_chain = MagicMock()
    generic_chain.select.return_value = generic_chain
    generic_chain.gte.return_value = generic_chain
    generic_chain.lt.return_value = generic_chain

    analytics_table_mock = MagicMock()

    def fake_upsert(data, **kwargs):
        upsert_calls.append(("admin_analytics_daily", data))
        return MagicMock()

    analytics_table_mock.upsert = fake_upsert

    def fake_table(name):
        if name == "admin_analytics_daily":
            return analytics_table_mock
        return generic_chain

    mock_client.table.side_effect = fake_table

    async def fake_execute_async(query, **kwargs):
        # All source tables return empty / zero
        result = MagicMock()
        result.data = [{"count": 0}]
        return result

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client), patch(
        _EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async
    ):
        # Should not raise
        result = await run_daily_aggregation("2026-03-21")

    assert isinstance(result, dict)
    assert "date" in result
    assert "rows_written" in result

    # analytics daily upsert should contain zeros
    analytics_upserts = [d for tbl, d in upsert_calls if tbl == "admin_analytics_daily"]
    assert len(analytics_upserts) == 1
    row = analytics_upserts[0]
    assert row["dau"] == 0
    assert row["mau"] == 0
    assert row["messages"] == 0
    assert row["workflows"] == 0


# =========================================================================
# Test 5: idempotent — calling twice for the same date does not raise
# =========================================================================


@pytest.mark.asyncio
async def test_run_daily_aggregation_is_idempotent():
    """Calling run_daily_aggregation twice for the same date does not raise."""
    from app.services.analytics_aggregator import run_daily_aggregation

    mock_client = MagicMock()

    generic_chain = MagicMock()
    generic_chain.select.return_value = generic_chain
    generic_chain.gte.return_value = generic_chain
    generic_chain.lt.return_value = generic_chain

    analytics_table_mock = MagicMock()
    analytics_table_mock.upsert.return_value = MagicMock()

    agent_stats_table_mock = MagicMock()
    agent_stats_table_mock.upsert.return_value = MagicMock()

    def fake_table(name):
        if name == "admin_analytics_daily":
            return analytics_table_mock
        if name == "admin_agent_stats_daily":
            return agent_stats_table_mock
        return generic_chain

    mock_client.table.side_effect = fake_table

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = [{"count": 3}]
        return result

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client), patch(
        _EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async
    ):
        # First call
        result1 = await run_daily_aggregation("2026-03-21")
        # Second call — must not raise
        result2 = await run_daily_aggregation("2026-03-21")

    assert result1["date"] == result2["date"] == "2026-03-21"
    # Upsert was called both times (idempotency relies on DB ON CONFLICT, not Python guard)
    assert analytics_table_mock.upsert.call_count == 2


# =========================================================================
# Test 6: accepts optional stat_date parameter, defaults to yesterday UTC
# =========================================================================


@pytest.mark.asyncio
async def test_run_daily_aggregation_defaults_to_yesterday():
    """run_daily_aggregation defaults to yesterday UTC when stat_date not provided."""
    from app.services.analytics_aggregator import run_daily_aggregation

    mock_client = MagicMock()

    generic_chain = MagicMock()
    generic_chain.select.return_value = generic_chain
    generic_chain.gte.return_value = generic_chain
    generic_chain.lt.return_value = generic_chain

    analytics_table_mock = MagicMock()
    analytics_table_mock.upsert.return_value = MagicMock()

    agent_stats_table_mock = MagicMock()
    agent_stats_table_mock.upsert.return_value = MagicMock()

    def fake_table(name):
        if name == "admin_analytics_daily":
            return analytics_table_mock
        if name == "admin_agent_stats_daily":
            return agent_stats_table_mock
        return generic_chain

    mock_client.table.side_effect = fake_table

    upserted_dates = []

    def fake_upsert(data, **kwargs):
        upserted_dates.append(data.get("stat_date"))
        return MagicMock()

    analytics_table_mock.upsert = fake_upsert

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = [{"count": 0}]
        return result

    yesterday = (date.today() - timedelta(days=1)).isoformat()

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client), patch(
        _EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async
    ):
        result = await run_daily_aggregation()  # No stat_date → defaults to yesterday

    assert result["date"] == yesterday
    assert len(upserted_dates) == 1
    assert upserted_dates[0] == yesterday
