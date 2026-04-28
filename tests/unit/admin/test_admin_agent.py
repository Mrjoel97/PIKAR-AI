"""Unit tests for AdminAgent instantiation and factory function.

Tests verify:
- admin_agent is a routing parent with 5 sub-agents
- Each sub-agent has scoped tools and focused instructions
- Parent and all sub-agents have context memory callbacks
- All 57 original tools are distributed across sub-agents
- create_admin_agent() factory produces agents with 5 sub-agents
"""
import pytest


def test_admin_agent_instantiation():
    """admin_agent has name='AdminAgent' and check_system_health is in a sub-agent."""
    from app.agents.admin.agent import admin_agent

    assert admin_agent.name == "AdminAgent"
    assert hasattr(admin_agent, "sub_agents")
    assert admin_agent.sub_agents  # not empty

    # check_system_health must be accessible via a sub-agent
    all_tool_names = []
    for sub in admin_agent.sub_agents:
        for t in sub.tools:
            name = getattr(t, "__name__", None) or getattr(t, "name", None)
            if name:
                all_tool_names.append(name)
    assert "check_system_health" in all_tool_names


def test_create_admin_agent_factory():
    """create_admin_agent() returns a new Agent instance without suffix."""
    from app.agents.admin.agent import create_admin_agent

    agent = create_admin_agent()
    assert agent is not None
    assert agent.name == "AdminAgent"


def test_create_admin_agent_factory_with_suffix():
    """create_admin_agent('_test') returns an agent with name='AdminAgent_test'."""
    from app.agents.admin.agent import create_admin_agent

    agent = create_admin_agent("_test")
    assert agent.name == "AdminAgent_test"


def test_admin_agent_has_instruction():
    """admin_agent has a non-empty instruction string."""
    from app.agents.admin.agent import admin_agent

    assert admin_agent.instruction
    assert len(admin_agent.instruction) > 50


def test_admin_agent_singleton_is_agent_type():
    """admin_agent is an instance of the Agent class used in this project."""
    from app.agents.admin.agent import admin_agent
    from app.agents.base_agent import PikarAgent

    assert isinstance(admin_agent, PikarAgent)


def test_admin_agent_has_five_sub_agents():
    """admin_agent has exactly 5 sub-agents."""
    from app.agents.admin.agent import admin_agent

    assert len(admin_agent.sub_agents) == 5


def test_admin_sub_agent_names():
    """The 5 sub-agents have the correct names."""
    from app.agents.admin.agent import admin_agent

    expected_names = {
        "SystemHealthAgent",
        "UserManagementAgent",
        "BillingAgent",
        "GovernanceAgent",
        "KnowledgeAgent",
    }
    actual_names = {sub.name for sub in admin_agent.sub_agents}
    assert actual_names == expected_names


def _get_agent_kwargs(agent) -> dict:
    """Extract constructor kwargs stored by ADK's BaseModel.

    ADK stores the original kwargs in __dict__['_kwargs']. This is the
    most reliable way to verify callbacks were passed at construction time.
    """
    return agent.__dict__.get("_kwargs", {})


def test_admin_sub_agents_have_context_callbacks():
    """Each sub-agent has before_model_callback and after_tool_callback set.

    ADK stores constructor kwargs in __dict__['_kwargs'].
    """
    from app.agents.admin.agent import admin_agent

    for sub in admin_agent.sub_agents:
        kwargs = _get_agent_kwargs(sub)
        assert kwargs.get("before_model_callback") is not None, (
            f"{sub.name} missing before_model_callback"
        )
        assert kwargs.get("after_tool_callback") is not None, (
            f"{sub.name} missing after_tool_callback"
        )


def test_admin_parent_has_context_callbacks():
    """admin_agent parent has before_model_callback and after_tool_callback set.

    ADK stores constructor kwargs in __dict__['_kwargs'].
    """
    from app.agents.admin.agent import admin_agent

    kwargs = _get_agent_kwargs(admin_agent)
    assert kwargs.get("before_model_callback") is not None, (
        "admin_agent missing before_model_callback"
    )
    assert kwargs.get("after_tool_callback") is not None, (
        "admin_agent missing after_tool_callback"
    )


def test_admin_all_tools_distributed():
    """All 57 original tools are distributed across sub-agents (count >= 57)."""
    from app.agents.admin.agent import admin_agent

    all_tool_names = []
    for sub in admin_agent.sub_agents:
        for t in sub.tools:
            name = getattr(t, "__name__", None) or getattr(t, "name", None)
            if name:
                all_tool_names.append(name)

    # Original 57 tools must all be accessible somewhere
    assert len(all_tool_names) >= 57, (
        f"Expected >= 57 tools across sub-agents, got {len(all_tool_names)}"
    )

    # Spot-check key tools from each domain
    key_tools = [
        "check_system_health",      # SystemHealthAgent
        "list_users",               # UserManagementAgent
        "get_billing_metrics",      # BillingAgent
        "manage_admin_role",        # GovernanceAgent
        "search_knowledge",         # KnowledgeAgent
    ]
    for tool_name in key_tools:
        assert tool_name in all_tool_names, (
            f"Key tool '{tool_name}' not found in any sub-agent"
        )


def test_admin_parent_has_no_direct_tools():
    """admin_agent parent has no direct tools — it is a pure router."""
    from app.agents.admin.agent import admin_agent

    assert len(admin_agent.tools) == 0


def test_create_admin_agent_factory_has_sub_agents():
    """create_admin_agent() produces an agent with 5 sub-agents."""
    from app.agents.admin.agent import create_admin_agent

    agent = create_admin_agent()
    assert len(agent.sub_agents) == 5


def test_create_admin_agent_factory_suffix_propagates():
    """create_admin_agent('_test') propagates suffix to sub-agent names."""
    from app.agents.admin.agent import create_admin_agent

    agent = create_admin_agent("_test")
    sub_names = [sub.name for sub in agent.sub_agents]

    # Every sub-agent name should include the suffix
    for name in sub_names:
        assert name.endswith("_test"), (
            f"Sub-agent '{name}' does not end with '_test'"
        )

    # Spot-check specific sub-agent names with suffix
    assert "SystemHealthAgent_test" in sub_names
    assert "UserManagementAgent_test" in sub_names
    assert "BillingAgent_test" in sub_names
    assert "GovernanceAgent_test" in sub_names
    assert "KnowledgeAgent_test" in sub_names
