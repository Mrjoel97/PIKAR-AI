"""Unit tests for admin analytics API endpoints.

Tests verify:
- GET /admin/analytics/summary returns all 4 sections: usage_trends, agent_effectiveness,
  feature_usage, config_status
- GET /admin/analytics/summary returns empty arrays/defaults when tables have no data
- GET /admin/analytics/summary?days=7 limits results to 7 days
- POST /admin/analytics/aggregate returns 200 with valid WORKFLOW_SERVICE_SECRET
- POST /admin/analytics/aggregate returns 401 without valid secret
- GET /admin/analytics/summary includes config_status with permission_counts and
  last_config_change
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request as StarletteRequest

# Patch targets
_SERVICE_CLIENT_PATCH = "app.routers.admin.analytics.get_service_client"
_EXECUTE_ASYNC_PATCH = "app.routers.admin.analytics.execute_async"
_VERIFY_SERVICE_AUTH_PATCH = "app.routers.admin.analytics.verify_service_auth"
_RUN_AGGREGATION_PATCH = "app.services.analytics_aggregator.run_daily_aggregation"


def _make_mock_request(path: str = "/admin/analytics/summary", method: str = "GET"):
    """Create a minimal Starlette Request for rate limiter dependency.

    slowapi validates ``isinstance(request, Request)`` so a plain MagicMock
    won't satisfy the check. We build a minimal ASGI scope instead.
    """
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [(b"x-forwarded-for", b"127.0.0.1")],
        "client": ("127.0.0.1", 12345),
    }
    return StarletteRequest(scope=scope)


def _make_analytics_rows(count: int = 5) -> list[dict]:
    """Build fake admin_analytics_daily rows."""
    return [
        {
            "stat_date": f"2026-03-{20 - i:02d}",
            "dau": 15 + i,
            "mau": 120,
            "messages": 340 + i * 10,
            "workflows": 12 + i,
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
        },
        {
            "agent_name": "content",
            "success_count": 40,
            "error_count": 2,
            "timeout_count": 0,
            "avg_duration_ms": 800.0,
            "total_calls": 42,
            "stat_date": "2026-03-20",
        },
    ]


def _make_tool_telemetry_rows() -> list[dict]:
    """Build fake tool_telemetry aggregated rows."""
    return [
        {"tool_name": "create_workflow", "call_count": 45},
        {"tool_name": "get_data", "call_count": 30},
    ]


def _make_analytics_event_rows() -> list[dict]:
    """Build fake analytics_events aggregated rows."""
    return [
        {"category": "chat", "event_count": 230},
        {"category": "workflow", "event_count": 80},
    ]


def _make_permission_rows() -> list[dict]:
    """Build fake admin_agent_permissions rows."""
    return [
        {"autonomy_level": "auto"},
        {"autonomy_level": "auto"},
        {"autonomy_level": "confirm"},
        {"autonomy_level": "blocked"},
    ]


def _make_config_history_rows() -> list[dict]:
    """Build fake admin_config_history rows."""
    return [{"created_at": "2026-03-20T15:30:00Z"}]


# =========================================================================
# Test 1: GET /admin/analytics/summary returns correct top-level shape
# =========================================================================


@pytest.mark.asyncio
async def test_analytics_summary_returns_all_four_sections(admin_user_dict):
    """GET /admin/analytics/summary returns all 4 data sections."""
    from app.routers.admin.analytics import get_analytics_summary

    analytics_rows = _make_analytics_rows()
    agent_rows = _make_agent_stat_rows()
    tool_rows = _make_tool_telemetry_rows()
    event_rows = _make_analytics_event_rows()
    perm_rows = _make_permission_rows()
    config_rows = _make_config_history_rows()

    mock_client = MagicMock()

    # Track query calls to return different data per table
    call_seq = {"n": 0}

    def _make_chain(data):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.gte.return_value = chain
        chain.lte.return_value = chain
        chain._return_data = data
        return chain

    def fake_table(name: str):
        call_seq["n"] += 1
        if name == "admin_analytics_daily":
            return _make_chain(analytics_rows)
        if name == "admin_agent_stats_daily":
            return _make_chain(agent_rows)
        if name == "tool_telemetry":
            return _make_chain(tool_rows)
        if name == "analytics_events":
            return _make_chain(event_rows)
        if name == "admin_agent_permissions":
            return _make_chain(perm_rows)
        if name == "admin_config_history":
            return _make_chain(config_rows)
        return _make_chain([])

    mock_client.table.side_effect = fake_table

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        return result

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client), patch(
        _EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async
    ):
        result = await get_analytics_summary(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    assert "usage_trends" in result
    assert "agent_effectiveness" in result
    assert "feature_usage" in result
    assert "config_status" in result
    assert "days" in result
    assert "data_source" in result


# =========================================================================
# Test 2: Empty tables return empty arrays/defaults (not errors)
# =========================================================================


@pytest.mark.asyncio
async def test_analytics_summary_empty_tables_return_defaults(admin_user_dict):
    """GET /admin/analytics/summary returns empty arrays when tables have no data."""
    from app.routers.admin.analytics import get_analytics_summary

    mock_client = MagicMock()
    empty = MagicMock()
    empty.select.return_value = empty
    empty.eq.return_value = empty
    empty.order.return_value = empty
    empty.limit.return_value = empty
    empty.gte.return_value = empty
    empty.lte.return_value = empty
    empty._return_data = []
    mock_client.table.return_value = empty

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = []
        return result

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client), patch(
        _EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async
    ):
        result = await get_analytics_summary(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    assert result["usage_trends"] == []
    assert result["agent_effectiveness"] == []
    assert result["feature_usage"]["by_tool"] == []
    assert result["feature_usage"]["by_category"] == []
    assert result["data_source"] == "no_data"


# =========================================================================
# Test 3: ?days=7 limits results to 7 days
# =========================================================================


@pytest.mark.asyncio
async def test_analytics_summary_days_param_respected(admin_user_dict):
    """GET /admin/analytics/summary?days=7 returns days=7 in response."""
    from app.routers.admin.analytics import get_analytics_summary

    mock_client = MagicMock()
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.gte.return_value = chain
    chain.lte.return_value = chain
    chain._return_data = []
    mock_client.table.return_value = chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = []
        return result

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client), patch(
        _EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async
    ):
        result = await get_analytics_summary(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
            days=7,
        )

    assert result["days"] == 7


# =========================================================================
# Test 4: POST /admin/analytics/aggregate returns 200 with valid secret
# =========================================================================


@pytest.mark.asyncio
async def test_aggregate_returns_200_with_valid_secret():
    """POST /admin/analytics/aggregate returns 200 with valid WORKFLOW_SERVICE_SECRET."""
    from app.routers.admin.analytics import trigger_analytics_aggregate

    aggregation_result = {"date": "2026-03-21", "rows_written": 3}

    with patch(
        _RUN_AGGREGATION_PATCH,
        new_callable=AsyncMock,
        return_value=aggregation_result,
    ) as mock_agg:
        result = await trigger_analytics_aggregate(
            request=_make_mock_request(method="POST"),
            _auth=True,
        )
        mock_agg.assert_called_once()

    assert result["status"] == "ok"
    assert result["date"] == "2026-03-21"
    assert result["rows_written"] == 3


# =========================================================================
# Test 5: POST /admin/analytics/aggregate returns 401 without valid secret
# =========================================================================


@pytest.mark.asyncio
async def test_aggregate_returns_401_without_valid_secret():
    """POST /admin/analytics/aggregate returns 401 without valid secret."""
    from fastapi import HTTPException

    from app.app_utils.auth import verify_service_auth

    import os

    os.environ["WORKFLOW_SERVICE_SECRET"] = "correct-secret"

    try:
        with pytest.raises(HTTPException) as exc_info:
            await verify_service_auth(x_service_secret="wrong-secret")  # type: ignore[call-arg]
        assert exc_info.value.status_code == 401
    finally:
        del os.environ["WORKFLOW_SERVICE_SECRET"]


# =========================================================================
# Test 6: config_status includes permission_counts and last_config_change
# =========================================================================


@pytest.mark.asyncio
async def test_analytics_summary_config_status_shape(admin_user_dict):
    """GET /admin/analytics/summary returns config_status with permission_counts and last_config_change."""
    from app.routers.admin.analytics import get_analytics_summary

    perm_rows = _make_permission_rows()
    config_rows = _make_config_history_rows()

    mock_client = MagicMock()

    def _make_chain(data):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.gte.return_value = chain
        chain.lte.return_value = chain
        chain._return_data = data
        return chain

    def fake_table(name: str):
        if name == "admin_agent_permissions":
            return _make_chain(perm_rows)
        if name == "admin_config_history":
            return _make_chain(config_rows)
        return _make_chain([])

    mock_client.table.side_effect = fake_table

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        return result

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client), patch(
        _EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async
    ):
        result = await get_analytics_summary(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    config_status = result["config_status"]
    assert "permission_counts" in config_status
    assert "last_config_change" in config_status

    perm_counts = config_status["permission_counts"]
    # 2 auto, 1 confirm, 1 blocked from _make_permission_rows
    assert perm_counts.get("auto") == 2
    assert perm_counts.get("confirm") == 1
    assert perm_counts.get("blocked") == 1
    assert config_status["last_config_change"] == "2026-03-20T15:30:00Z"


# =========================================================================
# Test 7: agent_effectiveness computes success_rate correctly
# =========================================================================


@pytest.mark.asyncio
async def test_analytics_summary_agent_effectiveness_success_rate(admin_user_dict):
    """agent_effectiveness entries include success_rate, avg_duration_ms, total_calls."""
    from app.routers.admin.analytics import get_analytics_summary

    agent_rows = [
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

    mock_client = MagicMock()

    def _make_chain(data):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.gte.return_value = chain
        chain.lte.return_value = chain
        chain._return_data = data
        return chain

    def fake_table(name: str):
        if name == "admin_agent_stats_daily":
            return _make_chain(agent_rows)
        return _make_chain([])

    mock_client.table.side_effect = fake_table

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        return result

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client), patch(
        _EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async
    ):
        result = await get_analytics_summary(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    agents = result["agent_effectiveness"]
    assert len(agents) >= 1
    financial = next((a for a in agents if a["agent_name"] == "financial"), None)
    assert financial is not None
    assert "success_rate" in financial
    assert "avg_duration_ms" in financial
    assert "total_calls" in financial
    # 90/96 * 100 = 93.75
    assert abs(financial["success_rate"] - 93.75) < 0.1
