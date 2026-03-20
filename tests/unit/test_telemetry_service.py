"""Tests for TelemetryService — data models and structured logging."""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _run(coro):
    """Helper to run async code in sync tests."""
    return asyncio.run(coro)


def test_agent_event_creation():
    from app.services.telemetry import AgentEvent
    event = AgentEvent(
        agent_name="FinancialAnalysisAgent",
        delegated_from="ExecutiveAgent",
        user_id="user-123",
        session_id="session-456",
        task_summary="Show me Q1 revenue",
        status="success",
        duration_ms=1200,
        input_tokens=500,
        output_tokens=300,
    )
    assert event.agent_name == "FinancialAnalysisAgent"
    assert event.status == "success"
    assert event.duration_ms == 1200


def test_tool_event_creation():
    from app.services.telemetry import ToolEvent
    event = ToolEvent(
        tool_name="search_business_knowledge",
        agent_name="ExecutiveAgent",
        user_id="user-123",
        session_id="session-456",
        status="success",
        duration_ms=350,
    )
    assert event.tool_name == "search_business_knowledge"
    assert event.status == "success"


def test_agent_event_to_log_dict():
    from app.services.telemetry import AgentEvent
    event = AgentEvent(
        agent_name="SalesIntelligenceAgent",
        delegated_from="ExecutiveAgent",
        user_id="user-123",
        session_id="session-456",
        task_summary="Score this lead",
        status="error",
        error_message="Model timeout",
    )
    log_dict = event.to_log_dict()
    assert log_dict["level"] == "INFO"
    assert log_dict["event"] == "agent_delegated"
    assert log_dict["agent"] == "SalesIntelligenceAgent"
    assert log_dict["delegated_from"] == "ExecutiveAgent"
    assert log_dict["status"] == "error"
    assert "error_message" in log_dict


def test_tool_event_to_log_dict():
    from app.services.telemetry import ToolEvent
    event = ToolEvent(
        tool_name="create_image",
        agent_name="ContentCreationAgent",
        user_id="user-123",
        session_id="session-456",
        status="success",
        duration_ms=2500,
    )
    log_dict = event.to_log_dict()
    assert log_dict["event"] == "tool_executed"
    assert log_dict["tool"] == "create_image"
    assert log_dict["agent"] == "ContentCreationAgent"


def test_structured_log_emitted_for_agent_event(caplog):
    from app.services.telemetry import TelemetryService, AgentEvent
    service = TelemetryService.__new__(TelemetryService)
    service._initialized = True
    service._enabled = True
    service._supabase = None
    event = AgentEvent(agent_name="DataAnalysisAgent", status="success", duration_ms=800)
    with caplog.at_level(logging.INFO, logger="app.services.telemetry"):
        service._emit_structured_log(event)
    assert len(caplog.records) >= 1
    assert "DataAnalysisAgent" in caplog.records[-1].message


def test_structured_log_emitted_for_tool_event(caplog):
    from app.services.telemetry import TelemetryService, ToolEvent
    service = TelemetryService.__new__(TelemetryService)
    service._initialized = True
    service._enabled = True
    service._supabase = None
    event = ToolEvent(tool_name="deep_research", agent_name="ExecutiveAgent", status="success", duration_ms=5000)
    with caplog.at_level(logging.INFO, logger="app.services.telemetry"):
        service._emit_structured_log(event)
    assert len(caplog.records) >= 1
    assert "deep_research" in caplog.records[-1].message


# ---------------------------------------------------------------------------
# Supabase persistence tests
# ---------------------------------------------------------------------------

def test_persist_agent_event_calls_supabase():
    from app.services.telemetry import TelemetryService, AgentEvent, invalidate_telemetry_service
    invalidate_telemetry_service()
    service = TelemetryService()
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.execute.return_value = MagicMock()
    service._supabase = mock_client
    # Patch _get_supabase so it returns our mock directly (avoids lazy-load)
    service._get_supabase = lambda: mock_client
    event = AgentEvent(agent_name="FinancialAnalysisAgent", status="success", duration_ms=1000)
    _run(service._persist_agent_event(event))
    mock_client.table.assert_called_once_with("agent_telemetry")
    mock_table.insert.assert_called_once()
    inserted = mock_table.insert.call_args[0][0]
    assert inserted["agent_name"] == "FinancialAnalysisAgent"
    assert inserted["status"] == "success"


def test_persist_tool_event_calls_supabase():
    from app.services.telemetry import TelemetryService, ToolEvent, invalidate_telemetry_service
    invalidate_telemetry_service()
    service = TelemetryService()
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.execute.return_value = MagicMock()
    service._supabase = mock_client
    service._get_supabase = lambda: mock_client
    event = ToolEvent(tool_name="create_image", agent_name="ContentCreationAgent", status="success", duration_ms=3000)
    _run(service._persist_tool_event(event))
    mock_client.table.assert_called_once_with("tool_telemetry")
    inserted = mock_table.insert.call_args[0][0]
    assert inserted["tool_name"] == "create_image"


# ---------------------------------------------------------------------------
# Circuit breaker tests
# ---------------------------------------------------------------------------

def test_circuit_breaker_opens_after_threshold():
    from app.services.telemetry import TelemetryService, invalidate_telemetry_service
    invalidate_telemetry_service()
    service = TelemetryService()
    assert service._cb_state == "closed"
    for _ in range(5):
        service._cb_record_failure()
    assert service._cb_state == "open"
    assert service._cb_should_allow() is False


def test_circuit_breaker_half_open_after_timeout():
    from app.services.telemetry import TelemetryService, invalidate_telemetry_service
    invalidate_telemetry_service()
    service = TelemetryService()
    for _ in range(5):
        service._cb_record_failure()
    assert service._cb_state == "open"
    # Backdate the last-failure timestamp so the 30s recovery window has elapsed
    service._cb_last_failure_time = time.time() - 31.0
    assert service._cb_should_allow() is True
    assert service._cb_state == "half-open"


def test_circuit_breaker_closes_on_success():
    from app.services.telemetry import TelemetryService, invalidate_telemetry_service
    invalidate_telemetry_service()
    service = TelemetryService()
    service._cb_state = "half-open"
    service._cb_record_success()
    assert service._cb_state == "closed"
    assert service._cb_failures == 0


def test_persist_skipped_when_circuit_open():
    from app.services.telemetry import TelemetryService, AgentEvent, invalidate_telemetry_service
    invalidate_telemetry_service()
    service = TelemetryService()
    mock_client = MagicMock()
    service._supabase = mock_client
    service._get_supabase = lambda: mock_client
    service._cb_state = "open"
    # Keep the last-failure time recent so recovery window has NOT elapsed
    service._cb_last_failure_time = time.time()
    event = AgentEvent(agent_name="Test", status="success")
    _run(service._persist_agent_event(event))
    mock_client.table.assert_not_called()


def test_disabled_telemetry_skips_everything():
    from app.services.telemetry import TelemetryService, AgentEvent, invalidate_telemetry_service
    invalidate_telemetry_service()
    service = TelemetryService()
    service._enabled = False
    event = AgentEvent(agent_name="Test", status="success")
    _run(service.record_agent_event(event))
