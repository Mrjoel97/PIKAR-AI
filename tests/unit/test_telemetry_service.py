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
