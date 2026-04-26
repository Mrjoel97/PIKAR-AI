from app.agents.strategic import create_strategic_agent
from app.agents.tools.tool_registry import get_tools_for_agent
from app.skills.registry import AgentID


def _tool_names(tools) -> set[str]:
    return {getattr(tool, "__name__", "") for tool in tools}


def test_create_strategic_agent_exposes_start_initiative_from_idea_directly():
    agent = create_strategic_agent()

    assert "start_initiative_from_idea" in _tool_names(agent.tools)


def test_strategic_tool_registry_includes_start_initiative_from_idea():
    tools = get_tools_for_agent(AgentID.STRAT)

    assert "start_initiative_from_idea" in _tool_names(tools)
