"""Unit tests for autonomy tier enforcement in check_system_health.

Tests verify:
- Auto tier: executes health check and returns overall_status
- Confirm tier: returns {requires_confirmation: True, confirmation_token, action_details}
- Blocked tier: returns {error: "...blocked..."}
- DB error fallback: defaults to auto, executes normally
- Health check result structure: overall_status and services keys
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Patch target for the internal liveness helper
_LIVENESS_PATCH = "app.agents.admin.tools.health._run_liveness_check"
_SERVICE_CLIENT_PATCH = "app.agents.admin.tools.health.get_service_client"
# The autonomy check imports get_service_client in its own module — must patch there too
_AUTONOMY_CLIENT_PATCH = "app.agents.admin.tools._autonomy.get_service_client"

_LIVENESS_RESULT = {"status": "alive"}


@pytest.fixture
def mock_supabase_auto():
    """Mock Supabase returning autonomy_level='auto'."""
    client = MagicMock()
    table_mock = MagicMock()
    client.table.return_value = table_mock
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.execute.return_value = MagicMock(
        data=[{"autonomy_level": "auto"}]
    )
    return client


@pytest.fixture
def mock_supabase_confirm():
    """Mock Supabase returning autonomy_level='confirm'."""
    client = MagicMock()
    table_mock = MagicMock()
    client.table.return_value = table_mock
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.execute.return_value = MagicMock(
        data=[{"autonomy_level": "confirm"}]
    )
    return client


@pytest.fixture
def mock_supabase_blocked():
    """Mock Supabase returning autonomy_level='blocked'."""
    client = MagicMock()
    table_mock = MagicMock()
    client.table.return_value = table_mock
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.execute.return_value = MagicMock(
        data=[{"autonomy_level": "blocked"}]
    )
    return client


@pytest.fixture
def mock_supabase_error():
    """Mock Supabase that raises an exception on execute."""
    client = MagicMock()
    table_mock = MagicMock()
    client.table.return_value = table_mock
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.execute.side_effect = Exception("DB connection error")
    return client


@pytest.mark.asyncio
async def test_health_tool_auto_tier(mock_supabase_auto):
    """Auto tier: check_system_health executes and returns overall_status."""
    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_supabase_auto):
        with patch(_LIVENESS_PATCH, new_callable=AsyncMock, return_value=_LIVENESS_RESULT):
            from app.agents.admin.tools.health import check_system_health

            result = await check_system_health()

    assert "overall_status" in result
    assert "services" in result
    assert result["overall_status"] in ("healthy", "degraded", "unhealthy")


@pytest.mark.asyncio
async def test_health_tool_confirm_tier(mock_supabase_confirm):
    """Confirm tier: returns requires_confirmation=True with UUID token and action_details."""
    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_supabase_confirm), patch(
        _AUTONOMY_CLIENT_PATCH, return_value=mock_supabase_confirm
    ):
        from app.agents.admin.tools.health import check_system_health

        result = await check_system_health()

    assert result.get("requires_confirmation") is True
    assert "confirmation_token" in result
    assert "action_details" in result
    # Token should be a valid UUID string
    import uuid
    uuid.UUID(result["confirmation_token"])  # raises ValueError if not valid UUID


@pytest.mark.asyncio
async def test_health_tool_blocked_tier(mock_supabase_blocked):
    """Blocked tier: returns error explanation without executing."""
    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_supabase_blocked), patch(
        _AUTONOMY_CLIENT_PATCH, return_value=mock_supabase_blocked
    ):
        from app.agents.admin.tools.health import check_system_health

        result = await check_system_health()

    assert "error" in result
    assert "block" in result["error"].lower()
    # Should not have executed the health check
    assert "overall_status" not in result


@pytest.mark.asyncio
async def test_health_tool_permission_db_error(mock_supabase_error):
    """DB error: defaults to auto tier, executes health check normally."""
    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_supabase_error):
        with patch(_LIVENESS_PATCH, new_callable=AsyncMock, return_value=_LIVENESS_RESULT):
            from app.agents.admin.tools.health import check_system_health

            result = await check_system_health()

    # Should have fallen back to auto and executed
    assert "overall_status" in result
    assert "services" in result


@pytest.mark.asyncio
async def test_health_tool_returns_service_status(mock_supabase_auto):
    """Auto tier: tool returns dict with overall_status and services keys."""
    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_supabase_auto):
        with patch(_LIVENESS_PATCH, new_callable=AsyncMock, return_value=_LIVENESS_RESULT):
            from app.agents.admin.tools.health import check_system_health

            result = await check_system_health()

    assert isinstance(result, dict)
    assert "overall_status" in result
    assert "services" in result
    assert isinstance(result["services"], dict)
