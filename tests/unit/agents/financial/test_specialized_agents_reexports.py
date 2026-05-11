# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Regression: specialized_agents re-exports must keep working after W2.

Many callers across the codebase import :func:`create_financial_agent`
and the (now nullable) module-level ``financial_agent`` symbol from
:mod:`app.agents.specialized_agents`. The W2 migration replaces the
singleton with a lazy factory; this test guards the public surface so a
future refactor cannot silently break those callers.
"""


def test_create_financial_agent_reexport_callable():
    from app.agents.specialized_agents import create_financial_agent

    assert callable(create_financial_agent)


def test_financial_agent_symbol_importable_for_legacy_callers():
    """Legacy ``from app.agents.specialized_agents import financial_agent`` must not raise.

    Behavior change: post-migration the module-level ``financial_agent`` is
    ``None`` (lazy-built per-user). Legacy callers that needed a singleton
    are migrated to use ``create_financial_agent(user_id=..., persona_id=...)``
    directly.
    """
    from app.agents.specialized_agents import financial_agent  # noqa: F401


def test_specialized_agents_list_does_not_include_none():
    from app.agents.specialized_agents import SPECIALIZED_AGENTS

    assert all(agent is not None for agent in SPECIALIZED_AGENTS), (
        "SPECIALIZED_AGENTS must not contain None placeholders post-migration"
    )


def test_create_financial_agent_in_all():
    """The re-export must remain in __all__ so star-imports keep working."""
    from app.agents import specialized_agents

    assert "create_financial_agent" in specialized_agents.__all__
    assert "financial_agent" in specialized_agents.__all__
