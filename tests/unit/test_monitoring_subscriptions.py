# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Wiring tests for Research Agent monitoring subscriptions and persona synthesis.

Verifies that:
1. Monitoring tools (create, list, pause, resume, delete) are registered on ResearchAgent.
2. format_synthesis_for_persona is registered on ResearchAgent.
3. Research Agent instructions contain the expected Phase 69 guidance sections.

These are integration/wiring tests — not functional tests.
Functional tests live in test_persona_synthesizer.py.
"""

from __future__ import annotations


def test_monitoring_tools_registered_on_research_agent():
    """All 5 monitoring tools must be in the ResearchAgent tools list."""
    from app.agents.research.agent import RESEARCH_AGENT_TOOLS
    from app.agents.research.tools.monitoring_tools import (
        create_monitoring_job,
        delete_monitoring_job,
        list_monitoring_jobs,
        pause_monitoring_job,
        resume_monitoring_job,
    )

    tool_names = {
        t.__name__ if hasattr(t, "__name__") else str(t)
        for t in RESEARCH_AGENT_TOOLS
    }
    expected = {
        create_monitoring_job.__name__,
        list_monitoring_jobs.__name__,
        pause_monitoring_job.__name__,
        resume_monitoring_job.__name__,
        delete_monitoring_job.__name__,
    }
    missing = expected - tool_names
    assert not missing, f"Missing monitoring tools in ResearchAgent: {missing}"


def test_persona_synthesizer_registered_on_research_agent():
    """format_synthesis_for_persona must be in the ResearchAgent tools list."""
    from app.agents.research.agent import RESEARCH_AGENT_TOOLS
    from app.agents.research.tools.persona_synthesizer import format_synthesis_for_persona

    tool_names = {
        t.__name__ if hasattr(t, "__name__") else str(t)
        for t in RESEARCH_AGENT_TOOLS
    }
    assert (
        format_synthesis_for_persona.__name__ in tool_names
    ), "format_synthesis_for_persona not registered in ResearchAgent tools"


def test_instructions_contain_persona_aware_synthesis_section():
    """RESEARCH_AGENT_INSTRUCTION must contain the Phase 69 persona-aware synthesis guidance."""
    from app.agents.research.instructions import RESEARCH_AGENT_INSTRUCTION

    assert "Persona-Aware Synthesis" in RESEARCH_AGENT_INSTRUCTION, (
        "Expected 'Persona-Aware Synthesis' section in RESEARCH_AGENT_INSTRUCTION"
    )


def test_instructions_contain_conversational_monitoring_section():
    """RESEARCH_AGENT_INSTRUCTION must contain the Phase 69 monitoring subscription flow."""
    from app.agents.research.instructions import RESEARCH_AGENT_INSTRUCTION

    assert "Conversational Monitoring Subscriptions" in RESEARCH_AGENT_INSTRUCTION, (
        "Expected 'Conversational Monitoring Subscriptions' section in RESEARCH_AGENT_INSTRUCTION"
    )


def test_instructions_contain_monitoring_trigger_phrases():
    """Instruction must mention the key trigger phrases for monitoring subscription."""
    from app.agents.research.instructions import RESEARCH_AGENT_INSTRUCTION

    assert "monitor" in RESEARCH_AGENT_INSTRUCTION.lower(), (
        "Expected 'monitor' keyword in monitoring subscription instruction"
    )
    assert "create_monitoring_job" in RESEARCH_AGENT_INSTRUCTION, (
        "Expected create_monitoring_job reference in monitoring subscription instruction"
    )


def test_instructions_contain_persona_format_tool_reference():
    """Instruction must reference the format_synthesis_for_persona tool by name."""
    from app.agents.research.instructions import RESEARCH_AGENT_INSTRUCTION

    assert "format_synthesis_for_persona" in RESEARCH_AGENT_INSTRUCTION, (
        "Expected format_synthesis_for_persona reference in persona synthesis instruction"
    )


def test_research_agent_singleton_loads_without_error():
    """The research_agent singleton must import and load without raising."""
    from app.agents.research.agent import research_agent

    # Verify it has a tools attribute and it's not empty
    assert hasattr(research_agent, "tools"), "research_agent has no 'tools' attribute"
    tools = research_agent.tools
    assert tools, "research_agent.tools is empty"
