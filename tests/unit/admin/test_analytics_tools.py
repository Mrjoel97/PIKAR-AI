"""Unit tests for AdminAgent analytics tools.

Tests verify:
- get_usage_stats returns DAU, MAU, messages, workflows for default 30 days
- get_usage_stats handles empty summary table (returns empty/zero data, not error)
- get_agent_effectiveness returns per-agent success_rate and avg_duration_ms
- get_agent_effectiveness handles empty agent_telemetry gracefully
- get_engagement_report returns feature usage by category
- generate_report returns formatted summary text for a date range
- All tools call _check_autonomy before execution
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Patch targets at the analytics tools module level
_SERVICE_CLIENT_PATCH = "app.agents.admin.tools.analytics.get_service_client"
_EXECUTE_ASYNC_PATCH = "app.agents.admin.tools.analytics.execute_async"


# ---------------------------------------------------------------------------
# Fixtures — autonomy mocks
# ---------------------------------------------------------------------------


def _build_autonomy_client(level: str) -> MagicMock:
    """Build a mock Supabase client that returns the given autonomy level."""
    client = MagicMock()
    table_mock = MagicMock()
    client.table.return_value = table_mock
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=[{"autonomy_level": level}])
    return client


@pytest.fixture
def client_auto():
    """Supabase mock returning autonomy_level='auto'."""
    return _build_autonomy_client("auto")


@pytest.fixture
def client_blocked():
    """Supabase mock returning autonomy_level='blocked'."""
    return _build_autonomy_client("blocked")


def _make_execute_async(rows: list[dict]) -> AsyncMock:
    """AsyncMock for execute_async that returns given rows."""
    return AsyncMock(return_value=MagicMock(data=rows))


def _make_analytics_rows(count: int = 5) -> list[dict]:
    """Build fake admin_analytics_daily rows."""
    return [
        {
            "stat_date": f"2026-03-{20 - i:02d}",
            "dau": 15 + i,
            "mau": 120,
            "messages": 340,
            "workflows": 12,
        }
        for i in range(count)
    ]


def _make_agent_stat_rows() -> list[dict]:
    """Build fake admin_agent_stats_daily rows."""
    return [
        {
            "agent_name": "financial",
            "success_count": 90,
            "error_count": 5,
            "timeout_count": 1,
            "avg_duration_ms": 1200.0,
            "total_calls": 96,
            "stat_date": "2026-03-20",
        }
    ]


def _make_tool_rows() -> list[dict]:
    """Build fake tool_telemetry rows."""
    return [
        {"tool_name": "create_workflow", "created_at": "2026-03-20T10:00:00Z"},
        {"tool_name": "create_workflow", "created_at": "2026-03-20T11:00:00Z"},
        {"tool_name": "get_data", "created_at": "2026-03-20T12:00:00Z"},
    ]


def _make_event_rows() -> list[dict]:
    """Build fake analytics_events rows."""
    return [
        {"category": "chat", "created_at": "2026-03-20T10:00:00Z"},
        {"category": "chat", "created_at": "2026-03-20T11:00:00Z"},
        {"category": "workflow", "created_at": "2026-03-20T12:00:00Z"},
    ]


# ---------------------------------------------------------------------------
# Test 1: get_usage_stats returns correct shape at auto tier
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_usage_stats_returns_correct_shape(client_auto):
    """Auto tier: get_usage_stats() returns usage_trends and summary dict."""
    analytics_rows = _make_analytics_rows()
    execute_async_mock = _make_execute_async(analytics_rows)

    with patch(_SERVICE_CLIENT_PATCH, return_value=client_auto), patch(
        _EXECUTE_ASYNC_PATCH, new=execute_async_mock
    ):
        from app.agents.admin.tools.analytics import get_usage_stats

        result = await get_usage_stats()

    assert "requires_confirmation" not in result
    assert "error" not in result
    assert "usage_trends" in result
    assert "summary" in result
    assert isinstance(result["usage_trends"], list)
    assert "avg_dau" in result["summary"]
    assert "latest_mau" in result["summary"]
    assert "total_messages" in result["summary"]
    assert "total_workflows" in result["summary"]


# ---------------------------------------------------------------------------
# Test 2: get_usage_stats handles empty table gracefully
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_usage_stats_empty_table(client_auto):
    """Auto tier: get_usage_stats() with empty table returns empty/zero data, not error."""
    execute_async_mock = _make_execute_async([])

    with patch(_SERVICE_CLIENT_PATCH, return_value=client_auto), patch(
        _EXECUTE_ASYNC_PATCH, new=execute_async_mock
    ):
        from app.agents.admin.tools.analytics import get_usage_stats

        result = await get_usage_stats()

    assert "error" not in result
    assert result["usage_trends"] == []
    assert result["summary"]["avg_dau"] == 0
    assert result["summary"]["latest_mau"] == 0
    assert result["summary"]["total_messages"] == 0
    assert result["summary"]["total_workflows"] == 0


# ---------------------------------------------------------------------------
# Test 3: get_agent_effectiveness returns per-agent data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_agent_effectiveness_returns_correct_shape(client_auto):
    """Auto tier: get_agent_effectiveness() returns per-agent effectiveness data."""
    agent_rows = _make_agent_stat_rows()
    execute_async_mock = _make_execute_async(agent_rows)

    with patch(_SERVICE_CLIENT_PATCH, return_value=client_auto), patch(
        _EXECUTE_ASYNC_PATCH, new=execute_async_mock
    ):
        from app.agents.admin.tools.analytics import get_agent_effectiveness

        result = await get_agent_effectiveness()

    assert "requires_confirmation" not in result
    assert "error" not in result
    assert "agents" in result
    assert isinstance(result["agents"], list)
    assert len(result["agents"]) >= 1

    financial = next(
        (a for a in result["agents"] if a["agent_name"] == "financial"), None
    )
    assert financial is not None
    assert "success_rate" in financial
    assert "avg_duration_ms" in financial
    assert "total_calls" in financial
    # 90/96 * 100 = 93.75
    assert abs(financial["success_rate"] - 93.75) < 0.1


# ---------------------------------------------------------------------------
# Test 4: get_agent_effectiveness handles empty table gracefully
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_agent_effectiveness_empty_table(client_auto):
    """Auto tier: get_agent_effectiveness() with empty table returns empty agents list."""
    execute_async_mock = _make_execute_async([])

    with patch(_SERVICE_CLIENT_PATCH, return_value=client_auto), patch(
        _EXECUTE_ASYNC_PATCH, new=execute_async_mock
    ):
        from app.agents.admin.tools.analytics import get_agent_effectiveness

        result = await get_agent_effectiveness()

    assert "error" not in result
    assert result["agents"] == []


# ---------------------------------------------------------------------------
# Test 5: get_engagement_report returns feature usage by category
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_engagement_report_returns_feature_usage(client_auto):
    """Auto tier: get_engagement_report() returns top_tools and event_categories."""
    tool_rows = _make_tool_rows()
    event_rows = _make_event_rows()

    # First call returns tool_rows, second call returns event_rows
    call_n = {"n": 0}
    original_rows = [tool_rows, event_rows]

    async def fake_execute_async(query, **kwargs):
        idx = call_n["n"] % 2
        call_n["n"] += 1
        return MagicMock(data=original_rows[idx])

    with patch(_SERVICE_CLIENT_PATCH, return_value=client_auto), patch(
        _EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async
    ):
        from app.agents.admin.tools.analytics import get_engagement_report

        result = await get_engagement_report()

    assert "requires_confirmation" not in result
    assert "error" not in result
    assert "top_tools" in result
    assert "event_categories" in result
    assert "days" in result
    assert isinstance(result["top_tools"], list)
    assert isinstance(result["event_categories"], list)


# ---------------------------------------------------------------------------
# Test 6: generate_report returns formatted summary dict with summary_text
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_report_returns_formatted_summary(client_auto):
    """Auto tier: generate_report() returns period_days, summary_text, usage, agent_performance."""
    analytics_rows = _make_analytics_rows(7)
    agent_rows = _make_agent_stat_rows()

    call_n = {"n": 0}

    async def fake_execute_async(query, **kwargs):
        idx = call_n["n"] % 2
        call_n["n"] += 1
        return MagicMock(data=[analytics_rows, agent_rows][idx])

    with patch(_SERVICE_CLIENT_PATCH, return_value=client_auto), patch(
        _EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async
    ):
        from app.agents.admin.tools.analytics import generate_report

        result = await generate_report(days=7)

    assert "requires_confirmation" not in result
    assert "error" not in result
    assert "report" in result
    report = result["report"]
    assert "period_days" in report
    assert "summary_text" in report
    assert "usage" in report
    assert "agent_performance" in report
    assert report["period_days"] == 7
    assert isinstance(report["summary_text"], str)
    assert len(report["summary_text"]) > 0


# ---------------------------------------------------------------------------
# Test 7: All tools call _check_autonomy (blocked tier returns error)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_usage_stats_blocked_returns_error(client_blocked):
    """Blocked tier: get_usage_stats() returns error dict without executing."""
    execute_async_mock = _make_execute_async([])

    with patch(_SERVICE_CLIENT_PATCH, return_value=client_blocked), patch(
        _EXECUTE_ASYNC_PATCH, new=execute_async_mock
    ):
        from app.agents.admin.tools.analytics import get_usage_stats

        result = await get_usage_stats()

    assert "error" in result
    assert "block" in result["error"].lower()
    assert "usage_trends" not in result


@pytest.mark.asyncio
async def test_get_agent_effectiveness_blocked_returns_error(client_blocked):
    """Blocked tier: get_agent_effectiveness() returns error dict without executing."""
    execute_async_mock = _make_execute_async([])

    with patch(_SERVICE_CLIENT_PATCH, return_value=client_blocked), patch(
        _EXECUTE_ASYNC_PATCH, new=execute_async_mock
    ):
        from app.agents.admin.tools.analytics import get_agent_effectiveness

        result = await get_agent_effectiveness()

    assert "error" in result
    assert "block" in result["error"].lower()
    assert "agents" not in result


@pytest.mark.asyncio
async def test_get_engagement_report_blocked_returns_error(client_blocked):
    """Blocked tier: get_engagement_report() returns error dict without executing."""
    execute_async_mock = _make_execute_async([])

    with patch(_SERVICE_CLIENT_PATCH, return_value=client_blocked), patch(
        _EXECUTE_ASYNC_PATCH, new=execute_async_mock
    ):
        from app.agents.admin.tools.analytics import get_engagement_report

        result = await get_engagement_report()

    assert "error" in result
    assert "block" in result["error"].lower()
    assert "top_tools" not in result


@pytest.mark.asyncio
async def test_generate_report_blocked_returns_error(client_blocked):
    """Blocked tier: generate_report() returns error dict without executing."""
    execute_async_mock = _make_execute_async([])

    with patch(_SERVICE_CLIENT_PATCH, return_value=client_blocked), patch(
        _EXECUTE_ASYNC_PATCH, new=execute_async_mock
    ):
        from app.agents.admin.tools.analytics import generate_report

        result = await generate_report()

    assert "error" in result
    assert "block" in result["error"].lower()
    assert "report" not in result
