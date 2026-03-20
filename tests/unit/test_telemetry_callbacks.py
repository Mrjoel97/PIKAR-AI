"""Tests for telemetry hooks in context_extractor callbacks."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sys

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())


def _run(coro):
    return asyncio.run(coro)


def test_after_tool_callback_records_tool_event():
    from app.services.telemetry import ToolEvent

    mock_telemetry = MagicMock()
    mock_telemetry.record_tool_event = AsyncMock()

    mock_tool = MagicMock()
    mock_tool.__name__ = "search_business_knowledge"
    mock_tool._is_timed_tool = True
    mock_tool._last_duration_ms = 250
    mock_tool._last_error = None

    mock_context = MagicMock()
    mock_context.state = {"user_id": "user-123", "session_id": "session-456"}

    with patch("app.agents.context_extractor.get_telemetry_service", return_value=mock_telemetry):
        from app.agents.context_extractor import _record_tool_telemetry

        _run(_record_tool_telemetry(mock_tool, mock_context, "success"))

    mock_telemetry.record_tool_event.assert_awaited_once()
    event = mock_telemetry.record_tool_event.call_args[0][0]
    assert isinstance(event, ToolEvent)
    assert event.tool_name == "search_business_knowledge"
    assert event.duration_ms == 250
    assert event.status == "success"


def test_before_model_callback_records_agent_start():
    mock_context = MagicMock()
    mock_context.state = {"user_id": "user-123"}
    mock_context.agent_name = "FinancialAnalysisAgent"

    with patch("app.agents.context_extractor.get_telemetry_service"):
        from app.agents.context_extractor import _record_agent_start

        _record_agent_start(mock_context, "Show me revenue")

    assert "_telemetry_agent_start" in mock_context.state
