# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for per-agent memory injection inside context_memory_before_model_callback."""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

# Stub the google.adk + google.genai surface the same way other unit tests do
# so importing app.agents.context_extractor does not require the real ADK.
sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())


def _make_callback_context(user_id: str, agent_name: str) -> MagicMock:
    """Build a CallbackContext-shaped mock with a real dict for state."""
    ctx = MagicMock()
    ctx.state = {"user_id": user_id}
    ctx.agent_name = agent_name
    return ctx


def _make_llm_request_with_user_text(text: str) -> MagicMock:
    """Build an llm_request mock containing one user content turn and a config."""
    part = MagicMock()
    part.text = text
    content = MagicMock()
    content.role = "user"
    content.parts = [part]

    config = MagicMock()
    config.system_instruction = ""

    request = MagicMock()
    request.contents = [content]
    request.config = config
    return request


def test_try_load_agent_memory_injects_facts_block():
    from app.agents import context_extractor

    ctx = _make_callback_context("user-abc", "FinancialAnalysisAgent")
    canned_facts = {"preferred_currency": "USD", "fiscal_year_end": "Dec 31"}

    with patch(
        "app.services.agent_memory.get_agent_memory_sync",
        return_value=canned_facts,
    ):
        block = context_extractor._try_load_agent_memory(ctx)

    assert block, "expected a non-empty block when facts exist"
    assert "[AGENT MEMORY" in block
    assert "FinancialAnalysisAgent" in block
    assert "preferred_currency" in block
    assert "USD" in block
    # The cache key must be set so a second call short-circuits.
    cache_keys = [k for k in ctx.state if k.startswith("_agent_memory_loaded::")]
    assert cache_keys, "loader must cache its result in session state"


def test_try_load_agent_memory_returns_empty_when_no_facts():
    from app.agents import context_extractor

    ctx = _make_callback_context("user-abc", "FinancialAnalysisAgent")

    with patch(
        "app.services.agent_memory.get_agent_memory_sync",
        return_value={},
    ):
        block = context_extractor._try_load_agent_memory(ctx)

    assert block == ""


def test_try_load_agent_memory_caches_per_session():
    from app.agents import context_extractor

    ctx = _make_callback_context("user-abc", "FinancialAnalysisAgent")
    canned_facts = {"x": 1}

    with patch(
        "app.services.agent_memory.get_agent_memory_sync",
        return_value=canned_facts,
    ) as mocked:
        first = context_extractor._try_load_agent_memory(ctx)
        second = context_extractor._try_load_agent_memory(ctx)

    assert first == second
    assert first  # not empty
    # Sync loader must only be hit once per session per agent.
    assert mocked.call_count == 1


def test_try_load_agent_memory_skips_without_user_or_agent():
    from app.agents import context_extractor

    no_user = _make_callback_context("", "FinancialAnalysisAgent")
    no_agent = _make_callback_context("user-abc", "")

    with patch(
        "app.services.agent_memory.get_agent_memory_sync",
        return_value={"x": 1},
    ) as mocked:
        assert context_extractor._try_load_agent_memory(no_user) == ""
        assert context_extractor._try_load_agent_memory(no_agent) == ""
        mocked.assert_not_called()


def test_try_load_agent_memory_swallows_loader_errors():
    from app.agents import context_extractor

    ctx = _make_callback_context("user-abc", "FinancialAnalysisAgent")

    with patch(
        "app.services.agent_memory.get_agent_memory_sync",
        side_effect=RuntimeError("boom"),
    ):
        block = context_extractor._try_load_agent_memory(ctx)

    assert block == ""


def test_before_model_callback_extends_system_instruction_with_agent_memory():
    """End-to-end: the public callback must inject the agent_memory block
    into llm_request.config.system_instruction when facts exist.
    """
    from app.agents import context_extractor

    ctx = _make_callback_context("user-abc", "FinancialAnalysisAgent")
    request = _make_llm_request_with_user_text("hello")

    canned_facts = {"preferred_currency": "USD"}

    with (
        patch(
            "app.services.agent_memory.get_agent_memory_sync",
            return_value=canned_facts,
        ),
        # Avoid touching cross-session vault / brand profile in this test.
        patch.object(context_extractor, "_try_load_cross_session_context"),
        patch.object(context_extractor, "_try_load_brand_profile", return_value=""),
    ):
        result = context_extractor.context_memory_before_model_callback(ctx, request)

    # Callback returns None and mutates the request's system_instruction in place.
    assert result is None
    si = request.config.system_instruction
    assert isinstance(si, str)
    assert "[AGENT MEMORY" in si
    assert "preferred_currency" in si
    assert json.dumps(canned_facts, indent=2)[:20] in si or "USD" in si
