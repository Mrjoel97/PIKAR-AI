# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Regression: specialized_agents re-exports must keep working after W4 CS migration."""


def test_create_customer_support_agent_reexport_callable():
    from app.agents.specialized_agents import create_customer_support_agent

    assert callable(create_customer_support_agent)


def test_customer_support_agent_symbol_importable_for_legacy_callers():
    from app.agents.specialized_agents import customer_support_agent  # noqa: F401


def test_specialized_agents_list_does_not_include_none():
    from app.agents.specialized_agents import SPECIALIZED_AGENTS

    assert all(agent is not None for agent in SPECIALIZED_AGENTS), (
        "SPECIALIZED_AGENTS must not contain None placeholders post-migration"
    )


def test_create_customer_support_agent_in_all():
    from app.agents import specialized_agents

    assert "create_customer_support_agent" in specialized_agents.__all__
    assert "customer_support_agent" in specialized_agents.__all__


def test_customer_support_package_init_exposes_create_factory():
    from app.agents.customer_support import (
        create_customer_support_agent,
        customer_support_agent,
    )

    assert callable(create_customer_support_agent)
    assert customer_support_agent is None
