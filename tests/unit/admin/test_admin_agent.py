"""Unit tests for AdminAgent instantiation and factory function.

Tests verify:
- admin_agent is an Agent instance with name="AdminAgent" and check_system_health in tools
- create_admin_agent() returns a new Agent instance
- create_admin_agent("_test") has name="AdminAgent_test"
"""
import pytest


def test_admin_agent_instantiation():
    """admin_agent is an Agent instance with name='AdminAgent' and check_system_health in tools."""
    from app.agents.admin.agent import admin_agent

    assert admin_agent.name == "AdminAgent"
    assert hasattr(admin_agent, "tools")
    tool_names = [
        getattr(t, "__name__", None) or getattr(t, "name", None)
        for t in admin_agent.tools
    ]
    assert "check_system_health" in tool_names


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
