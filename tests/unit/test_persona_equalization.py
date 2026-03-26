# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests proving every persona has equal access to all specialized agents.

Phase 28 core invariant: persona affects agent *behavior* (prompt fragments,
routing priorities) but never agent *availability*.
"""

from __future__ import annotations

from app.personas.policy_registry import list_persona_policies
from app.personas.prompt_fragments import (
    _AGENT_PERSONA_FOCUS,
    build_agent_persona_fragment,
    build_persona_policy_block,
)


def test_all_personas_have_identical_preferred_agents() -> None:
    """All 4 personas must have the exact same preferred_agents tuple."""
    policies = list_persona_policies()
    agent_sets = [policy.preferred_agents for policy in policies.values()]

    # All sets must be identical
    for agents in agent_sets[1:]:
        assert agents == agent_sets[0], (
            f"Preferred agents differ across personas: {agents} != {agent_sets[0]}"
        )


def test_preferred_agents_contains_all_canonical_agents() -> None:
    """The shared preferred_agents tuple must contain every agent in _AGENT_PERSONA_FOCUS."""
    policies = list_persona_policies()
    canonical_agents = set(_AGENT_PERSONA_FOCUS.keys())

    for key, policy in policies.items():
        preferred = set(policy.preferred_agents)
        missing = canonical_agents - preferred
        assert not missing, (
            f"Persona '{key}' is missing agents: {missing}"
        )


def test_solopreneur_can_access_all_agents() -> None:
    """Solopreneur must include agents it previously lacked."""
    policies = list_persona_policies()
    solo = policies["solopreneur"]
    previously_missing = [
        "ComplianceRiskAgent",
        "HRRecruitmentAgent",
        "OperationsOptimizationAgent",
        "StrategicPlanningAgent",
        "DataAnalysisAgent",
        "DataReportingAgent",
        "CustomerSupportAgent",
        "FinancialAnalysisAgent",
    ]
    for agent in previously_missing:
        assert agent in solo.preferred_agents, (
            f"Solopreneur still missing {agent}"
        )


def test_prompt_block_says_all_agents_available() -> None:
    """Prompt block must say 'All specialized agents' not 'Preferred agents: X, Y'."""
    block = build_persona_policy_block(
        "solopreneur", agent_name="ExecutiveAgent", include_routing=True
    )
    assert "All specialized agents" in block, (
        "Prompt block should mention 'All specialized agents'"
    )
    assert "Preferred agents:" not in block, (
        "Prompt block should NOT contain restrictive 'Preferred agents:' line"
    )


def test_routing_priorities_still_differ_per_persona() -> None:
    """Routing priorities must still differ between personas (behavioral tuning preserved)."""
    policies = list_persona_policies()
    solo_priorities = policies["solopreneur"].routing_priorities
    enterprise_priorities = policies["enterprise"].routing_priorities

    assert solo_priorities != enterprise_priorities, (
        "Routing priorities should differ between solopreneur and enterprise"
    )


def test_behavioral_fragments_exist_for_all_agents_all_personas() -> None:
    """Every agent x persona combination must produce a non-empty behavioral fragment."""
    persona_keys = ["solopreneur", "startup", "sme", "enterprise"]
    for agent in _AGENT_PERSONA_FOCUS:
        for persona in persona_keys:
            fragment = build_agent_persona_fragment(agent, persona)
            assert fragment, (
                f"Empty behavioral fragment for {agent} x {persona}"
            )


def test_rate_limits_still_differ_per_persona() -> None:
    """Rate limits remain the true differentiator, not agent access."""
    from app.middleware.rate_limiter import PERSONA_LIMITS

    assert PERSONA_LIMITS["solopreneur"] == "10/minute"
    assert PERSONA_LIMITS["startup"] == "30/minute"
    assert PERSONA_LIMITS["sme"] == "60/minute"
    assert PERSONA_LIMITS["enterprise"] == "120/minute"
