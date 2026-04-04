# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for persona behavioral instruction fragments."""

from __future__ import annotations

import pytest

from app.personas.behavioral_instructions import get_behavioral_instructions
from app.personas.policy_registry import ALL_AGENT_NAMES

ALL_PERSONAS = ("solopreneur", "startup", "sme", "enterprise")


def test_solopreneur_executive_tone() -> None:
    """Solopreneur executive instructions contain confident, comprehensive directives."""
    result = get_behavioral_instructions("solopreneur", "ExecutiveAgent")
    result_lower = result.lower()
    assert result, "Expected non-empty behavioral instructions"
    assert any(
        word in result_lower for word in ("confident", "direct", "capable")
    ), f"Expected confident/direct/capable in: {result}"
    assert "next step" in result_lower or "next-step" in result_lower or "30-day" in result_lower, (
        f"Expected 'next step' or '30-day' in: {result}"
    )


def test_enterprise_executive_tone() -> None:
    """Enterprise executive instructions contain formal, governance-aware directives."""
    result = get_behavioral_instructions("enterprise", "ExecutiveAgent")
    result_lower = result.lower()
    assert result, "Expected non-empty behavioral instructions"
    assert "formal" in result_lower or "structured" in result_lower, (
        f"Expected 'formal' or 'structured' in: {result}"
    )
    assert any(
        word in result_lower for word in ("governance", "compliance", "stakeholder")
    ), f"Expected governance/compliance/stakeholder in: {result}"


def test_solopreneur_financial_agent_contains_revenue() -> None:
    """Solopreneur financial instructions focus on revenue and comprehensive analysis, not portfolio/board."""
    result = get_behavioral_instructions("solopreneur", "FinancialAnalysisAgent")
    result_lower = result.lower()
    assert result, "Expected non-empty behavioral instructions"
    assert "revenue" in result_lower, f"Expected 'revenue' in: {result}"
    assert "comprehensive" in result_lower, f"Expected 'comprehensive' in: {result}"
    assert "portfolio" not in result_lower, (
        f"Expected 'portfolio' NOT in solopreneur financial instructions: {result}"
    )
    assert "board-ready" not in result_lower, (
        f"Expected 'board-ready' NOT in solopreneur financial instructions: {result}"
    )


def test_enterprise_financial_agent_contains_portfolio() -> None:
    """Enterprise financial instructions focus on portfolio/board-ready analysis."""
    result = get_behavioral_instructions("enterprise", "FinancialAnalysisAgent")
    result_lower = result.lower()
    assert result, "Expected non-empty behavioral instructions"
    assert "portfolio" in result_lower or "board-ready" in result_lower, (
        f"Expected 'portfolio' or 'board-ready' in: {result}"
    )
    assert "cash flow summary" not in result_lower, (
        f"Expected 'cash flow summary' NOT in enterprise financial instructions: {result}"
    )


def test_all_48_combinations_return_non_empty() -> None:
    """All 4 personas x 12 agents = 48 combinations must return non-empty strings."""
    missing = []
    for persona in ALL_PERSONAS:
        for agent in ALL_AGENT_NAMES:
            result = get_behavioral_instructions(persona, agent)
            if not result:
                missing.append(f"{persona}/{agent}")
    assert not missing, f"Missing behavioral instructions for: {missing}"


def test_none_persona_returns_empty_string() -> None:
    """Passing None for persona returns empty string gracefully."""
    result = get_behavioral_instructions(None, "ExecutiveAgent")
    assert result == "", f"Expected empty string for None persona, got: {result!r}"


def test_none_agent_returns_executive_fallback() -> None:
    """Passing None for agent_name falls back to ExecutiveAgent instructions."""
    result_with_none = get_behavioral_instructions("solopreneur", None)
    result_with_executive = get_behavioral_instructions("solopreneur", "ExecutiveAgent")
    assert result_with_none, "Expected non-empty instructions for solopreneur with None agent"
    assert result_with_none == result_with_executive, (
        f"Expected None agent to fall back to ExecutiveAgent.\n"
        f"Got with None: {result_with_none!r}\n"
        f"Got with ExecutiveAgent: {result_with_executive!r}"
    )


def _word_overlap_ratio(text_a: str, text_b: str) -> float:
    """Return fraction of shared words between two texts (0.0 = no overlap, 1.0 = identical)."""
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


@pytest.mark.parametrize("agent", list(ALL_AGENT_NAMES))
def test_solopreneur_enterprise_blocks_materially_different(agent: str) -> None:
    """Solopreneur and enterprise instructions for the same agent have < 50% word overlap."""
    solo = get_behavioral_instructions("solopreneur", agent)
    enterprise = get_behavioral_instructions("enterprise", agent)
    overlap = _word_overlap_ratio(solo, enterprise)
    assert overlap < 0.50, (
        f"Overlap too high ({overlap:.1%}) for {agent}.\n"
        f"Solopreneur: {solo}\n"
        f"Enterprise: {enterprise}"
    )


def test_output_contains_behavioral_header() -> None:
    """Output is wrapped in the ## BEHAVIORAL STYLE DIRECTIVES header."""
    result = get_behavioral_instructions("startup", "ContentCreationAgent")
    assert "## BEHAVIORAL STYLE DIRECTIVES" in result, (
        f"Expected header '## BEHAVIORAL STYLE DIRECTIVES' in: {result}"
    )
