"""Tests for the Research Agent factory and system registration."""


def test_research_agent_exists():
    """Singleton research_agent should be importable and correctly named."""
    from app.agents.research.agent import research_agent

    assert research_agent is not None
    assert research_agent.name == "ResearchAgent"


def test_create_research_agent_factory():
    """Factory should produce distinct instances with custom suffixes."""
    from app.agents.research.agent import create_research_agent

    agent = create_research_agent(name_suffix="_test")
    assert agent.name == "ResearchAgent_test"
    assert agent.tools is not None
    assert len(agent.tools) > 0


def test_research_agent_in_specialized_agents():
    """ResearchAgent must appear in the SPECIALIZED_AGENTS list."""
    from app.agents.specialized_agents import SPECIALIZED_AGENTS

    agent_names = [a.name for a in SPECIALIZED_AGENTS]
    assert "ResearchAgent" in agent_names


def test_research_agent_has_required_tools():
    """Agent must carry all five research tool groups plus graph_read."""
    from app.agents.research.agent import research_agent

    tool_names = [
        t.__name__ if callable(t) else str(t) for t in (research_agent.tools or [])
    ]
    assert "plan_queries" in tool_names
    assert "run_track" in tool_names
    assert "synthesize_tracks" in tool_names
    assert "write_to_graph" in tool_names
    assert "log_research_cost" in tool_names
    assert "graph_read" in tool_names
