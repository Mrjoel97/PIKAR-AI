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


def test_extract_routing_signals():
    from app.agents.context_extractor import _extract_routing_signals
    signals = _extract_routing_signals("Show me the Q1 revenue forecast and create a blog post")
    assert "revenue" in signals or "forecast" in signals
    assert "blog" in signals


def test_routing_log_emitted_for_sub_agent(caplog):
    import logging
    mock_context = MagicMock()
    mock_context.state = {"user_id": "user-123"}
    mock_context.agent_name = "FinancialAnalysisAgent"

    with patch("app.agents.context_extractor.get_telemetry_service"):
        from app.agents.context_extractor import _record_agent_start
        with caplog.at_level(logging.INFO, logger="app.agents.context_extractor"):
            _record_agent_start(mock_context, "Show me Q1 revenue")

    # Should have emitted a routing log
    routing_logs = [r for r in caplog.records if "agent_routing_decision" in r.message]
    assert len(routing_logs) >= 1


# ---------------------------------------------------------------------------
# Cross-agent context enrichment tests
# ---------------------------------------------------------------------------

def test_build_cross_agent_context_empty():
    from app.agents.context_extractor import _build_cross_agent_context
    mock_ctx = MagicMock()
    mock_ctx.state = {}
    result = _build_cross_agent_context(mock_ctx)
    assert result == ""


def test_build_cross_agent_context_with_entries():
    from app.agents.context_extractor import _build_cross_agent_context, CROSS_AGENT_CONTEXT_KEY
    mock_ctx = MagicMock()
    mock_ctx.state = {
        CROSS_AGENT_CONTEXT_KEY: [
            {"agent": "FinancialAnalysisAgent", "summary": "Q1 revenue: $12M ARR", "turns_ago": 1},
            {"agent": "DataAnalysisAgent", "summary": "Churn rate: 2.3%", "turns_ago": 3},
        ]
    }
    result = _build_cross_agent_context(mock_ctx)
    assert "CROSS-AGENT CONTEXT" in result
    assert "FinancialAnalysisAgent" in result
    assert "$12M ARR" in result
    assert "DataAnalysisAgent" in result


def test_build_cross_agent_context_filters_old():
    from app.agents.context_extractor import _build_cross_agent_context, CROSS_AGENT_CONTEXT_KEY
    mock_ctx = MagicMock()
    mock_ctx.state = {
        CROSS_AGENT_CONTEXT_KEY: [
            {"agent": "OldAgent", "summary": "stale data", "turns_ago": 15},
        ]
    }
    result = _build_cross_agent_context(mock_ctx)
    assert result == ""  # filtered out (>10 turns)


def test_record_agent_output():
    from app.agents.context_extractor import _record_agent_output, CROSS_AGENT_CONTEXT_KEY
    mock_ctx = MagicMock()
    mock_ctx.state = {}
    _record_agent_output(mock_ctx, "SalesAgent", "Lead scored: Acme Corp — 85/100 BANT")
    assert CROSS_AGENT_CONTEXT_KEY in mock_ctx.state
    entries = mock_ctx.state[CROSS_AGENT_CONTEXT_KEY]
    assert len(entries) == 1
    assert entries[0]["agent"] == "SalesAgent"
    assert "Acme Corp" in entries[0]["summary"]
    assert entries[0]["turns_ago"] == 0


def test_record_agent_output_ages_existing():
    from app.agents.context_extractor import _record_agent_output, CROSS_AGENT_CONTEXT_KEY
    mock_ctx = MagicMock()
    mock_ctx.state = {
        CROSS_AGENT_CONTEXT_KEY: [
            {"agent": "OldAgent", "summary": "old work", "turns_ago": 2}
        ]
    }
    _record_agent_output(mock_ctx, "NewAgent", "new work")
    entries = mock_ctx.state[CROSS_AGENT_CONTEXT_KEY]
    assert len(entries) == 2
    assert entries[0]["agent"] == "NewAgent"
    assert entries[0]["turns_ago"] == 0
    assert entries[1]["agent"] == "OldAgent"
    assert entries[1]["turns_ago"] == 3  # aged from 2 to 3


# ---------------------------------------------------------------------------
# Session Action Log tests
# ---------------------------------------------------------------------------

def test_record_action_high_value_tool():
    from app.agents.context_extractor import _record_action, SESSION_ACTION_LOG_KEY
    mock_ctx = MagicMock()
    mock_ctx.state = {}
    _record_action(
        mock_ctx,
        "create_image",
        {"prompt": "sunset over mountains with golden light", "style": "vibrant"},
        {"url": "https://example.com/image.png", "status": "success"},
    )
    log = mock_ctx.state[SESSION_ACTION_LOG_KEY]
    assert len(log) == 1
    assert log[0]["tool"] == "create_image"
    assert "sunset" in log[0]["args"]["prompt"]
    assert log[0]["args"]["style"] == "vibrant"
    assert log[0]["results"]["url"] == "https://example.com/image.png"


def test_record_action_regular_tool():
    from app.agents.context_extractor import _record_action, SESSION_ACTION_LOG_KEY
    mock_ctx = MagicMock()
    mock_ctx.state = {}
    _record_action(
        mock_ctx,
        "search_business_knowledge",
        {"query": "What is our company mission?"},
        {"results": [{"text": "Our mission is..."}]},
    )
    log = mock_ctx.state[SESSION_ACTION_LOG_KEY]
    assert len(log) == 1
    assert log[0]["tool"] == "search_business_knowledge"
    assert "company mission" in log[0]["query"]


def test_build_session_action_context():
    from app.agents.context_extractor import _build_session_action_context, SESSION_ACTION_LOG_KEY
    mock_ctx = MagicMock()
    mock_ctx.state = {
        SESSION_ACTION_LOG_KEY: [
            {
                "tool": "create_image",
                "agent": "ContentCreationAgent",
                "turn": 0,
                "args": {"prompt": "sunset over mountains", "style": "vibrant"},
                "results": {"url": "https://example.com/img.png"},
            }
        ]
    }
    result = _build_session_action_context(mock_ctx)
    assert "SESSION ACTIONS" in result
    assert "create_image" in result
    assert "sunset over mountains" in result
    assert "vibrant" in result


def test_build_session_action_context_empty():
    from app.agents.context_extractor import _build_session_action_context, SESSION_ACTION_LOG_KEY
    mock_ctx = MagicMock()
    mock_ctx.state = {}
    result = _build_session_action_context(mock_ctx)
    assert result == ""


def test_action_log_caps_at_max():
    from app.agents.context_extractor import _record_action, SESSION_ACTION_LOG_KEY
    mock_ctx = MagicMock()
    mock_ctx.state = {}
    for i in range(15):
        _record_action(mock_ctx, f"tool_{i}", {"q": f"query_{i}"}, {"status": "ok"})
    log = mock_ctx.state[SESSION_ACTION_LOG_KEY]
    assert len(log) == 10  # max is 10
    assert log[0]["tool"] == "tool_5"  # oldest 5 dropped
