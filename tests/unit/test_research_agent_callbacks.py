"""Tests for ResearchAgent context-memory callback wiring and instruction hygiene.

Covers two regressions fixed together:

1. ResearchAgent was missing `before_model_callback` and `after_tool_callback`,
   so research findings did not persist across multi-turn requests.
2. ResearchAgent's instruction string included the shared
   `SELF_IMPROVEMENT_INSTRUCTIONS` block which referenced tools
   (`report_skill_gap`, `check_my_performance`) that ResearchAgent does not
   own — the agent then called non-existent functions and corrupted traces.
"""


def _get_agent_kwargs(agent) -> dict:
    """Extract constructor kwargs stored by ADK's BaseModel / MockAgent.

    Both PikarAgent (real ADK) and the unit-test MockAgent stash the original
    kwargs in `__dict__['_kwargs']`. This is the most reliable way to verify
    callbacks were passed at construction time.
    """
    return agent.__dict__.get("_kwargs", {})


def test_research_agent_has_before_model_callback():
    """Singleton research_agent must have a non-None before_model_callback."""
    from app.agents.research.agent import research_agent

    kwargs = _get_agent_kwargs(research_agent)
    assert kwargs.get("before_model_callback") is not None, (
        "research_agent missing before_model_callback "
        "(context memory will not load on multi-turn requests)"
    )


def test_research_agent_has_after_tool_callback():
    """Singleton research_agent must have a non-None after_tool_callback."""
    from app.agents.research.agent import research_agent

    kwargs = _get_agent_kwargs(research_agent)
    assert kwargs.get("after_tool_callback") is not None, (
        "research_agent missing after_tool_callback "
        "(tool outputs will not be persisted to context memory)"
    )


def test_create_research_agent_factory_wires_callbacks():
    """Factory-built ResearchAgents must also carry both callbacks."""
    from app.agents.research.agent import create_research_agent

    agent = create_research_agent(name_suffix="_callback_test")
    kwargs = _get_agent_kwargs(agent)
    assert kwargs.get("before_model_callback") is not None
    assert kwargs.get("after_tool_callback") is not None


def test_research_instruction_does_not_reference_missing_tools():
    """Instruction must NOT mention self-improvement tools that aren't bound.

    `report_skill_gap` and `check_my_performance` live in self-improvement
    tool packs that the ResearchAgent does not load. If the instruction
    string still names them, the model will call non-existent functions and
    corrupt every multi-turn trace.
    """
    from app.agents.research.agent import research_agent

    instruction = research_agent.instruction or ""
    assert "report_skill_gap" not in instruction, (
        "ResearchAgent instruction still references report_skill_gap — "
        "remove SELF_IMPROVEMENT_INSTRUCTIONS from the prompt assembly."
    )
    assert "check_my_performance" not in instruction, (
        "ResearchAgent instruction still references check_my_performance — "
        "remove SELF_IMPROVEMENT_INSTRUCTIONS from the prompt assembly."
    )
