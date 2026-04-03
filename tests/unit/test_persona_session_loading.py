# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""End-to-end tests for persona session loading pipeline.

Verifies that persona context flows from Supabase profile through
session state into every agent's system prompt with behavioral instructions.
Covers PERS-03: persona loaded once at session start, never re-stated by user.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.context_extractor import (
    USER_AGENT_PERSONALIZATION_STATE_KEY,
    context_memory_before_model_callback,
)
from app.services.user_agent_factory import (
    UserAgentFactory,
    build_runtime_personalization_block,
)


# ---------------------------------------------------------------------------
# Shared test helpers (same pattern as test_personalization_prompt_injection.py)
# ---------------------------------------------------------------------------


class DummyConfig:
    """Minimal stand-in for llm_request.config."""

    def __init__(self, system_instruction: str = "BASE") -> None:
        """Initialize with a system instruction."""
        self.system_instruction = system_instruction


class DummyRequest:
    """Minimal stand-in for llm_request."""

    def __init__(self, system_instruction: str = "BASE") -> None:
        """Initialize with a config and empty contents."""
        self.config = DummyConfig(system_instruction)
        self.contents = []


class DummyContext(SimpleNamespace):
    """Minimal stand-in for ADK CallbackContext."""


# ---------------------------------------------------------------------------
# Test 1: get_runtime_personalization returns persona for user with profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_persona_loaded_from_profile() -> None:
    """get_runtime_personalization returns persona from Supabase profile."""
    factory = UserAgentFactory.__new__(UserAgentFactory)
    mock_config = {
        "persona": "solopreneur",
        "business_context": {"company_name": "Solo Corp"},
        "preferences": {"verbosity": "concise"},
    }
    factory.get_user_config = AsyncMock(return_value=mock_config)
    factory._redis_cache = MagicMock()
    factory._redis_cache.get_user_persona = AsyncMock(return_value=None)

    result = await factory.get_runtime_personalization("user-123")

    assert result.get("persona") == "solopreneur", (
        f"Expected persona='solopreneur', got: {result}"
    )
    assert "business_context" in result
    assert "preferences" in result


# ---------------------------------------------------------------------------
# Test 2: get_runtime_personalization with no persona does not crash
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_persona_missing_from_profile_no_crash() -> None:
    """get_runtime_personalization for a user with no persona returns dict without 'persona' key."""
    factory = UserAgentFactory.__new__(UserAgentFactory)
    mock_config: dict = {
        "business_context": {"company_name": "Anon Corp"},
        "preferences": {},
    }
    factory.get_user_config = AsyncMock(return_value=mock_config)
    factory._redis_cache = MagicMock()
    factory._redis_cache.get_user_persona = AsyncMock(return_value=None)

    result = await factory.get_runtime_personalization("user-no-persona")

    # Must not crash and must not set persona to None
    assert "persona" not in result or result["persona"] is not None, (
        "persona key should be absent or truthy when no persona is configured"
    )


# ---------------------------------------------------------------------------
# Test 3: build_runtime_personalization_block with enterprise persona
# ---------------------------------------------------------------------------


def test_build_block_enterprise_financial_contains_behavioral_directives() -> None:
    """build_runtime_personalization_block includes BEHAVIORAL STYLE DIRECTIVES and ENTERPRISE policy."""
    block = build_runtime_personalization_block(
        {"persona": "enterprise"},
        agent_name="FinancialAnalysisAgent",
    )
    assert "BEHAVIORAL STYLE DIRECTIVES" in block, (
        f"Expected 'BEHAVIORAL STYLE DIRECTIVES' in block:\n{block}"
    )
    assert "ACTIVE PERSONA POLICY: ENTERPRISE" in block, (
        f"Expected 'ACTIVE PERSONA POLICY: ENTERPRISE' in block:\n{block}"
    )


# ---------------------------------------------------------------------------
# Test 4: build_runtime_personalization_block with None persona returns empty
# ---------------------------------------------------------------------------


def test_build_block_none_persona_returns_empty() -> None:
    """build_runtime_personalization_block with persona=None returns empty string."""
    block = build_runtime_personalization_block(
        {},
        agent_name="FinancialAnalysisAgent",
    )
    assert block == "", f"Expected empty string for empty personalization, got: {block!r}"


# ---------------------------------------------------------------------------
# Test 5: Full callback chain — solopreneur persona injected into system prompt
# ---------------------------------------------------------------------------


def test_callback_chain_solopreneur_behavioral_directives_injected() -> None:
    """Full callback chain injects BEHAVIORAL STYLE DIRECTIVES for solopreneur."""
    callback_context = DummyContext(
        state={
            USER_AGENT_PERSONALIZATION_STATE_KEY: {
                "persona": "solopreneur",
            }
        },
        agent_name="ExecutiveAgent",
    )
    llm_request = DummyRequest()

    result = context_memory_before_model_callback(callback_context, llm_request)

    assert result is None
    si = llm_request.config.system_instruction
    assert "BEHAVIORAL STYLE DIRECTIVES" in si, (
        f"Expected 'BEHAVIORAL STYLE DIRECTIVES' in system instruction:\n{si}"
    )
    si_lower = si.lower()
    assert any(
        word in si_lower for word in ("cash", "direct", "informal", "plain", "step")
    ), f"Expected solopreneur-specific language in:\n{si}"


# ---------------------------------------------------------------------------
# Test 6: Full callback chain — financial agent gets financial-specific solopreneur instructions
# ---------------------------------------------------------------------------


def test_callback_chain_financial_agent_solopreneur_specific_instructions() -> None:
    """Full callback chain for FinancialAnalysisAgent includes solopreneur financial behavioral instructions."""
    callback_context = DummyContext(
        state={
            USER_AGENT_PERSONALIZATION_STATE_KEY: {
                "persona": "solopreneur",
            }
        },
        agent_name="FinancialAnalysisAgent",
    )
    llm_request = DummyRequest()

    result = context_memory_before_model_callback(callback_context, llm_request)

    assert result is None
    si = llm_request.config.system_instruction
    assert "BEHAVIORAL STYLE DIRECTIVES" in si, (
        f"Expected 'BEHAVIORAL STYLE DIRECTIVES' in system instruction:\n{si}"
    )
    si_lower = si.lower()
    assert "cash" in si_lower, (
        f"Expected 'cash' (solopreneur financial language) in system instruction:\n{si}"
    )


# ---------------------------------------------------------------------------
# Test 7: Full callback chain — no personalization state, no crash, no behavioral block
# ---------------------------------------------------------------------------


def test_callback_chain_no_personalization_state_no_crash() -> None:
    """Full callback chain with no personalization state does not crash and does not inject behavioral block."""
    callback_context = DummyContext(
        state={},
        agent_name="ExecutiveAgent",
    )
    llm_request = DummyRequest()

    result = context_memory_before_model_callback(callback_context, llm_request)

    assert result is None
    # When nothing is in state the callback should not modify the base instruction
    assert "BEHAVIORAL STYLE DIRECTIVES" not in llm_request.config.system_instruction, (
        "Should not inject behavioral directives when no personalization state exists"
    )


# ---------------------------------------------------------------------------
# Test 8: Behavioral instructions differ between agents for same persona
# ---------------------------------------------------------------------------


def test_behavioral_instructions_differ_between_agents_same_persona() -> None:
    """Solopreneur ExecutiveAgent block differs from solopreneur FinancialAnalysisAgent block."""
    executive_block = build_runtime_personalization_block(
        {"persona": "solopreneur"},
        agent_name="ExecutiveAgent",
    )
    financial_block = build_runtime_personalization_block(
        {"persona": "solopreneur"},
        agent_name="FinancialAnalysisAgent",
    )

    assert executive_block, "Expected non-empty ExecutiveAgent block"
    assert financial_block, "Expected non-empty FinancialAnalysisAgent block"
    assert executive_block != financial_block, (
        "Expected different behavioral instructions for ExecutiveAgent vs FinancialAnalysisAgent "
        f"(same solopreneur persona).\n"
        f"ExecutiveAgent block:\n{executive_block}\n\n"
        f"FinancialAnalysisAgent block:\n{financial_block}"
    )
