# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Regression: specialized_agents re-exports must keep working after W4 compliance migration."""


def test_create_compliance_agent_reexport_callable():
    from app.agents.specialized_agents import create_compliance_agent

    assert callable(create_compliance_agent)


def test_compliance_agent_symbol_importable_for_legacy_callers():
    from app.agents.specialized_agents import compliance_agent  # noqa: F401


def test_specialized_agents_list_does_not_include_none():
    from app.agents.specialized_agents import SPECIALIZED_AGENTS

    assert all(agent is not None for agent in SPECIALIZED_AGENTS)


def test_create_compliance_agent_in_all():
    from app.agents import specialized_agents

    assert "create_compliance_agent" in specialized_agents.__all__
    assert "compliance_agent" in specialized_agents.__all__


def test_compliance_package_init_exposes_create_factory():
    from app.agents.compliance import compliance_agent, create_compliance_agent

    assert callable(create_compliance_agent)
    assert compliance_agent is None
