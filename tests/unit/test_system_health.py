"""Tests for system health tool."""

import asyncio
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch


def _run(coro):
    return asyncio.run(coro)


def test_system_health_no_data():
    mock_service = MagicMock()
    mock_service.get_agent_health = AsyncMock(return_value=MagicMock(total_calls=0))
    mock_service.get_tool_usage = AsyncMock(return_value=[])

    from app.agents.tools.system_health import get_system_health

    with patch(
        "app.agents.tools.system_health.get_telemetry_service",
        return_value=mock_service,
    ):
        result = _run(get_system_health(24))

    assert result["status"] == "no_data"
    assert "No telemetry data" in result["message"]


def test_system_health_healthy():
    @dataclass
    class MockHealth:
        agent_name: str
        total_calls: int
        success_count: int
        error_count: int
        timeout_count: int = 0
        avg_duration_ms: float = 500.0
        success_rate: float = 0.95
        top_errors: list = field(default_factory=list)

    mock_service = MagicMock()
    mock_service.get_agent_health = AsyncMock(
        return_value=MockHealth("TestAgent", 100, 95, 5)
    )
    mock_service.get_tool_usage = AsyncMock(return_value=[])

    from app.agents.tools.system_health import get_system_health

    with patch(
        "app.agents.tools.system_health.get_telemetry_service",
        return_value=mock_service,
    ):
        result = _run(get_system_health(24))

    assert result["status"] == "healthy"
    assert len(result["agent_health"]) >= 1


def test_system_health_degraded():
    @dataclass
    class MockHealth:
        agent_name: str
        total_calls: int
        success_count: int
        error_count: int
        timeout_count: int = 0
        avg_duration_ms: float = 500.0
        success_rate: float = 0.5
        top_errors: list = field(default_factory=list)

    mock_service = MagicMock()
    mock_service.get_agent_health = AsyncMock(
        return_value=MockHealth("BadAgent", 100, 50, 50, success_rate=0.5)
    )
    mock_service.get_tool_usage = AsyncMock(return_value=[])

    from app.agents.tools.system_health import get_system_health

    with patch(
        "app.agents.tools.system_health.get_telemetry_service",
        return_value=mock_service,
    ):
        result = _run(get_system_health(24))

    assert result["status"] == "degraded"
    assert any("success rate" in r for r in result["recommendations"])


def test_system_health_error_graceful():
    from app.agents.tools.system_health import get_system_health

    with patch(
        "app.agents.tools.system_health.get_telemetry_service",
        side_effect=Exception("DB down"),
    ):
        result = _run(get_system_health(24))

    assert result["status"] == "unavailable"
