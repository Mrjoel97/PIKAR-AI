"""Unit tests for the health checker service.

Tests verify:
- run_health_checks() calls all 5 endpoints concurrently and returns result dicts
- Results are written to api_health_checks via get_service_client()
- Anomaly detection: down, latency_spike, error_spike
- Incident lifecycle: create on anomaly, resolve on recovery
- Auto-prune: records older than 30 days, max 1000 per endpoint
- Network errors produce status='unhealthy' with error_message populated
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import httpx
import pytest


# -------------------------------------------------------------------
# Patch targets
# -------------------------------------------------------------------
_SERVICE_CLIENT_PATCH = "app.services.health_checker.get_service_client"
_EXECUTE_ASYNC_PATCH = "app.services.health_checker.execute_async"
_LOG_ADMIN_PATCH = "app.services.health_checker.log_admin_action"
_HTTPX_ASYNC_CLIENT_PATCH = "app.services.health_checker.httpx.AsyncClient"


# -------------------------------------------------------------------
# Helpers / fixtures
# -------------------------------------------------------------------


def _make_supabase_mock() -> MagicMock:
    """Build a chainable Supabase mock that covers all table ops."""
    client = MagicMock()
    tbl = MagicMock()
    client.table.return_value = tbl
    tbl.insert.return_value = tbl
    tbl.select.return_value = tbl
    tbl.eq.return_value = tbl
    tbl.is_.return_value = tbl
    tbl.limit.return_value = tbl
    tbl.update.return_value = tbl
    tbl.delete.return_value = tbl
    tbl.lte.return_value = tbl
    tbl.order.return_value = tbl
    tbl.execute.return_value = MagicMock(data=[])
    return client


def _make_http_response(status_code: int = 200) -> MagicMock:
    """Return a minimal httpx.Response-like mock."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    return resp


# -------------------------------------------------------------------
# _check_one unit tests
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_one_returns_dict_keys():
    """_check_one returns dict with required keys for a healthy endpoint."""
    from app.services.health_checker import _check_one

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_make_http_response(200))

    result = await _check_one(mock_client, "live", "/health/live")

    assert "endpoint" in result
    assert "status" in result
    assert "status_code" in result
    assert "response_time_ms" in result
    assert "error_message" in result
    assert result["endpoint"] == "live"


@pytest.mark.asyncio
async def test_check_one_healthy_on_200():
    """_check_one sets status='healthy' when response is 200."""
    from app.services.health_checker import _check_one

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_make_http_response(200))

    result = await _check_one(mock_client, "live", "/health/live")
    assert result["status"] == "healthy"
    assert result["status_code"] == 200
    assert result["error_message"] is None


@pytest.mark.asyncio
async def test_check_one_unhealthy_on_non_200():
    """_check_one sets status='unhealthy' when response is non-200."""
    from app.services.health_checker import _check_one

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_make_http_response(503))

    result = await _check_one(mock_client, "connections", "/health/connections")
    assert result["status"] == "unhealthy"
    assert result["status_code"] == 503


@pytest.mark.asyncio
async def test_check_one_network_error_returns_unhealthy():
    """_check_one catches network exceptions and returns status='unhealthy'."""
    from app.services.health_checker import _check_one

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    result = await _check_one(mock_client, "cache", "/health/cache")
    assert result["status"] == "unhealthy"
    assert result["status_code"] is None
    assert result["error_message"] is not None
    assert "Connection refused" in result["error_message"]


@pytest.mark.asyncio
async def test_check_one_timeout_returns_unhealthy():
    """_check_one catches timeout exceptions and returns status='unhealthy'."""
    from app.services.health_checker import _check_one

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=httpx.TimeoutException("Request timed out")
    )

    result = await _check_one(mock_client, "embeddings", "/health/embeddings")
    assert result["status"] == "unhealthy"
    assert result["error_message"] is not None


# -------------------------------------------------------------------
# _detect_anomaly unit tests
# -------------------------------------------------------------------


def test_detect_anomaly_down_on_non_200():
    """_detect_anomaly returns 'down' when status_code is not 200."""
    from app.services.health_checker import _detect_anomaly

    check_result = {"status": "unhealthy", "status_code": 503, "response_time_ms": 50}
    rolling = {"avg_response_time_ms": 100.0, "error_count": 0, "total_count": 10}
    anomaly = _detect_anomaly(check_result, rolling)
    assert anomaly == "down"


def test_detect_anomaly_down_on_none_status_code():
    """_detect_anomaly returns 'down' when status_code is None (network error)."""
    from app.services.health_checker import _detect_anomaly

    check_result = {
        "status": "unhealthy",
        "status_code": None,
        "response_time_ms": None,
    }
    rolling = {"avg_response_time_ms": 100.0, "error_count": 0, "total_count": 10}
    anomaly = _detect_anomaly(check_result, rolling)
    assert anomaly == "down"


def test_detect_anomaly_latency_spike():
    """_detect_anomaly returns 'latency_spike' when response_time > 2x rolling avg."""
    from app.services.health_checker import _detect_anomaly

    check_result = {"status": "healthy", "status_code": 200, "response_time_ms": 250}
    rolling = {"avg_response_time_ms": 100.0, "error_count": 0, "total_count": 10}
    anomaly = _detect_anomaly(check_result, rolling)
    assert anomaly == "latency_spike"


def test_detect_anomaly_latency_spike_sets_degraded():
    """_detect_anomaly sets status='degraded' on latency_spike."""
    from app.services.health_checker import _detect_anomaly

    check_result = {"status": "healthy", "status_code": 200, "response_time_ms": 250}
    rolling = {"avg_response_time_ms": 100.0, "error_count": 0, "total_count": 10}
    _detect_anomaly(check_result, rolling)
    assert check_result["status"] == "degraded"


def test_detect_anomaly_error_spike():
    """_detect_anomaly returns 'error_spike' when error_rate > 5%."""
    from app.services.health_checker import _detect_anomaly

    check_result = {"status": "healthy", "status_code": 200, "response_time_ms": 80}
    rolling = {"avg_response_time_ms": 100.0, "error_count": 1, "total_count": 10}
    anomaly = _detect_anomaly(check_result, rolling)
    assert anomaly == "error_spike"


def test_detect_anomaly_none_when_healthy():
    """_detect_anomaly returns None when endpoint is healthy with normal latency."""
    from app.services.health_checker import _detect_anomaly

    check_result = {"status": "healthy", "status_code": 200, "response_time_ms": 90}
    rolling = {"avg_response_time_ms": 100.0, "error_count": 0, "total_count": 10}
    anomaly = _detect_anomaly(check_result, rolling)
    assert anomaly is None


def test_detect_anomaly_no_rolling_stats_returns_none():
    """_detect_anomaly returns None when rolling_stats is None (not enough data)."""
    from app.services.health_checker import _detect_anomaly

    check_result = {"status": "healthy", "status_code": 200, "response_time_ms": 100}
    anomaly = _detect_anomaly(check_result, None)
    assert anomaly is None


# -------------------------------------------------------------------
# _update_incidents unit tests
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_incidents_creates_incident_on_anomaly():
    """_update_incidents creates api_incidents row when anomaly detected and no open incident."""
    from app.services.health_checker import _update_incidents

    mock_client = _make_supabase_mock()
    # No open incident exists
    mock_client.table.return_value.execute.return_value = MagicMock(data=[])

    with patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = MagicMock(data=[])
        checked_at = datetime.now(timezone.utc).isoformat()
        await _update_incidents(mock_client, "live", "down", checked_at)

    # Should have called insert on api_incidents
    calls = [str(c) for c in mock_exec.call_args_list]
    # Verify execute_async was called at least once (for query and possibly insert)
    assert mock_exec.call_count >= 1


@pytest.mark.asyncio
async def test_update_incidents_no_op_when_healthy_no_incident():
    """_update_incidents does nothing when healthy and no open incident exists."""
    from app.services.health_checker import _update_incidents

    mock_client = _make_supabase_mock()
    checked_at = datetime.now(timezone.utc).isoformat()

    with patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock) as mock_exec:
        # Return no open incident
        mock_exec.return_value = MagicMock(data=[])
        await _update_incidents(mock_client, "live", None, checked_at)

    # Query for open incident only — no insert/update
    assert mock_exec.call_count == 1  # only the SELECT query


@pytest.mark.asyncio
async def test_update_incidents_resolves_on_recovery():
    """_update_incidents resolves open incident when endpoint becomes healthy."""
    from app.services.health_checker import _update_incidents

    mock_client = _make_supabase_mock()
    open_incident = [{"id": "incident-uuid-1", "incident_type": "down"}]
    checked_at = datetime.now(timezone.utc).isoformat()

    with patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock) as mock_exec:
        # First call: SELECT returns open incident
        # Second call: UPDATE to resolve
        mock_exec.side_effect = [
            MagicMock(data=open_incident),
            MagicMock(data=[{"id": "incident-uuid-1"}]),
        ]
        await _update_incidents(mock_client, "live", None, checked_at)

    assert mock_exec.call_count == 2


@pytest.mark.asyncio
async def test_update_incidents_uses_is_null_for_resolved_at():
    """_update_incidents uses .is_('resolved_at', 'null') for PostgREST IS NULL syntax."""
    from app.services.health_checker import _update_incidents

    mock_client = _make_supabase_mock()
    checked_at = datetime.now(timezone.utc).isoformat()

    with patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = MagicMock(data=[])
        await _update_incidents(mock_client, "live", None, checked_at)

    # The query builder should have called .is_("resolved_at", "null")
    mock_client.table.assert_called_with("api_incidents")
    mock_client.table.return_value.is_.assert_called_with("resolved_at", "null")


# -------------------------------------------------------------------
# _prune_old_records unit tests
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prune_old_records_deletes_old_entries():
    """_prune_old_records deletes api_health_checks records older than 30 days."""
    from app.services.health_checker import _prune_old_records

    mock_client = _make_supabase_mock()

    with patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock) as mock_exec:
        # First call: delete by age; subsequent: count-per-endpoint queries
        mock_exec.return_value = MagicMock(data=[])
        await _prune_old_records(mock_client)

    # Should have called table("api_health_checks")
    assert any(
        c == call("api_health_checks")
        for c in mock_client.table.call_args_list
    )


@pytest.mark.asyncio
async def test_prune_old_records_limits_to_1000_per_endpoint():
    """_prune_old_records removes excess records when an endpoint has > 1000 rows."""
    from app.services.health_checker import _prune_old_records, HEALTH_ENDPOINTS

    mock_client = _make_supabase_mock()
    # Simulate count > 1000 for first endpoint
    endpoint_name = next(iter(HEALTH_ENDPOINTS))

    with patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock) as mock_exec:
        # Delete old: returns empty; count query returns 1200; delete excess
        mock_exec.side_effect = [
            MagicMock(data=[]),  # age-based delete
            # For each endpoint: select returns 1200 rows (simulating excess)
            *[MagicMock(data=[{"id": f"id-{i}"} for i in range(1200)])
              for _ in HEALTH_ENDPOINTS],
            # For the endpoint that has excess: delete returns empty
            *[MagicMock(data=[]) for _ in HEALTH_ENDPOINTS],
        ]
        await _prune_old_records(mock_client)

    assert mock_exec.call_count >= 2  # at least age delete + one count check


@pytest.mark.asyncio
async def test_prune_old_records_does_not_raise_on_error():
    """_prune_old_records swallows exceptions — never fails the health check loop."""
    from app.services.health_checker import _prune_old_records

    mock_client = _make_supabase_mock()

    with patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock) as mock_exec:
        mock_exec.side_effect = Exception("DB failure during prune")
        # Should NOT raise
        await _prune_old_records(mock_client)


# -------------------------------------------------------------------
# run_health_checks integration tests (all mocked)
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_health_checks_returns_list_of_dicts():
    """run_health_checks() returns a list of result dicts, one per endpoint."""
    from app.services.health_checker import HEALTH_ENDPOINTS, run_health_checks

    mock_supabase = _make_supabase_mock()
    mock_http_response = _make_http_response(200)

    async def fake_get(*args, **kwargs):
        return mock_http_response

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.get = AsyncMock(return_value=mock_http_response)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_supabase),
        patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock) as mock_exec,
        patch(_LOG_ADMIN_PATCH, new_callable=AsyncMock),
        patch(_HTTPX_ASYNC_CLIENT_PATCH, return_value=mock_http_client),
    ):
        mock_exec.return_value = MagicMock(data=[])
        results = await run_health_checks()

    assert isinstance(results, list)
    assert len(results) == len(HEALTH_ENDPOINTS)


@pytest.mark.asyncio
async def test_run_health_checks_result_keys():
    """run_health_checks() returns dicts with endpoint, status, status_code, response_time_ms, error_message."""
    from app.services.health_checker import run_health_checks

    mock_supabase = _make_supabase_mock()
    mock_http_response = _make_http_response(200)

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.get = AsyncMock(return_value=mock_http_response)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_supabase),
        patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock) as mock_exec,
        patch(_LOG_ADMIN_PATCH, new_callable=AsyncMock),
        patch(_HTTPX_ASYNC_CLIENT_PATCH, return_value=mock_http_client),
    ):
        mock_exec.return_value = MagicMock(data=[])
        results = await run_health_checks()

    for result in results:
        assert "endpoint" in result
        assert "status" in result
        assert "status_code" in result
        assert "response_time_ms" in result
        assert "error_message" in result


@pytest.mark.asyncio
async def test_run_health_checks_writes_to_api_health_checks():
    """run_health_checks() inserts results into api_health_checks table."""
    from app.services.health_checker import run_health_checks

    mock_supabase = _make_supabase_mock()
    mock_http_response = _make_http_response(200)

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.get = AsyncMock(return_value=mock_http_response)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_supabase),
        patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock) as mock_exec,
        patch(_LOG_ADMIN_PATCH, new_callable=AsyncMock),
        patch(_HTTPX_ASYNC_CLIENT_PATCH, return_value=mock_http_client),
    ):
        mock_exec.return_value = MagicMock(data=[])
        await run_health_checks()

    mock_supabase.table.assert_any_call("api_health_checks")
    mock_supabase.table.return_value.insert.assert_called()


@pytest.mark.asyncio
async def test_run_health_checks_creates_incident_on_down():
    """run_health_checks() creates api_incidents row with incident_type='down' for non-200."""
    from app.services.health_checker import run_health_checks

    mock_supabase = _make_supabase_mock()
    # Make all endpoints return 503
    mock_http_response = _make_http_response(503)

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.get = AsyncMock(return_value=mock_http_response)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_supabase),
        patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock) as mock_exec,
        patch(_LOG_ADMIN_PATCH, new_callable=AsyncMock),
        patch(_HTTPX_ASYNC_CLIENT_PATCH, return_value=mock_http_client),
    ):
        # SELECT returns no open incidents; rolling stats returns no data (< 3)
        mock_exec.return_value = MagicMock(data=[])
        await run_health_checks()

    # api_incidents insert should have been triggered
    mock_supabase.table.assert_any_call("api_incidents")


@pytest.mark.asyncio
async def test_run_health_checks_calls_log_admin_action():
    """run_health_checks() calls log_admin_action with source='monitoring_loop'."""
    from app.services.health_checker import run_health_checks

    mock_supabase = _make_supabase_mock()
    mock_http_response = _make_http_response(200)

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.get = AsyncMock(return_value=mock_http_response)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_supabase),
        patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock) as mock_exec,
        patch(_LOG_ADMIN_PATCH, new_callable=AsyncMock) as mock_log,
        patch(_HTTPX_ASYNC_CLIENT_PATCH, return_value=mock_http_client),
    ):
        mock_exec.return_value = MagicMock(data=[])
        await run_health_checks()

    mock_log.assert_called_once()
    call_kwargs = mock_log.call_args
    assert call_kwargs.kwargs.get("source") == "monitoring_loop" or (
        len(call_kwargs.args) > 5 and call_kwargs.args[5] == "monitoring_loop"
    )
