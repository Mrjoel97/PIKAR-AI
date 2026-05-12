"""Unit tests for agent factory functions.

Tests that factory functions create fresh agent instances without parent
assignments, ensuring the hybrid architecture resolves ADK's single-parent
constraint.
"""

import pytest

# Test data for agent factory verification.
#
# Agents migrated to ``PikarBaseAgent`` (W2 financial pilot, W4 content
# pilot) report their canonical :class:`AgentID` value as ``agent.name``
# (e.g. ``"FIN"``, ``"CONT"``) — *not* the legacy human-readable class
# name. Their module-level singletons are also retired to ``None``
# sentinels. The legacy parametrized assertions are scoped to *unmigrated*
# agents; migrated agents have their own contract tests under
# ``tests/unit/agents/{financial,content}/``.
AGENT_FACTORIES = [
    ("create_strategic_agent", "StrategicPlanningAgent"),
    ("create_sales_agent", "SalesIntelligenceAgent"),
    ("create_marketing_agent", "MarketingAutomationAgent"),
    ("create_operations_agent", "OperationsOptimizationAgent"),
    ("create_compliance_agent", "ComplianceRiskAgent"),
    ("create_customer_support_agent", "CustomerSupportAgent"),
    ("create_data_agent", "DataAnalysisAgent"),
]

# Migrated agents — their canonical name is ``AgentID.value`` and their
# module-level singleton is ``None``. Listed here so the singleton +
# count assertions can exclude them cleanly.
MIGRATED_AGENT_FACTORIES = [
    ("create_financial_agent", "FIN"),
    ("create_content_agent", "CONT"),
    ("create_hr_agent", "HR"),
]


class TestAgentFactoryFunctions:
    """Tests for agent factory functions in specialized_agents.py."""

    def test_all_factory_functions_exist(self):
        """Test that all 10 factory functions are exported."""
        from app.agents.specialized_agents import __all__

        expected_factories = [
            "create_financial_agent",
            "create_content_agent",
            "create_strategic_agent",
            "create_sales_agent",
            "create_marketing_agent",
            "create_operations_agent",
            "create_hr_agent",
            "create_compliance_agent",
            "create_customer_support_agent",
            "create_data_agent",
        ]

        for factory_name in expected_factories:
            assert factory_name in __all__, f"Factory {factory_name} not in __all__"

    @pytest.mark.parametrize("factory_name,expected_agent_name", AGENT_FACTORIES)
    def test_factory_creates_agent_with_correct_name(
        self, factory_name, expected_agent_name
    ):
        """Test that each factory creates an agent with the expected name."""
        from app.agents import specialized_agents

        factory_fn = getattr(specialized_agents, factory_name)
        agent = factory_fn()

        assert agent.name == expected_agent_name

    @pytest.mark.parametrize("factory_name,expected_agent_name", AGENT_FACTORIES)
    def test_factory_creates_fresh_instances(self, factory_name, expected_agent_name):
        """Test that factory returns new instance each time (not singleton)."""
        from app.agents import specialized_agents

        factory_fn = getattr(specialized_agents, factory_name)
        agent1 = factory_fn()
        agent2 = factory_fn()

        # Should be different objects
        assert agent1 is not agent2
        # But with same configuration
        assert agent1.name == agent2.name
        assert agent1.description == agent2.description

    @pytest.mark.parametrize("factory_name,expected_agent_name", AGENT_FACTORIES)
    def test_factory_with_name_suffix(self, factory_name, expected_agent_name):
        """Test that factory supports optional name_suffix parameter."""
        from app.agents import specialized_agents

        factory_fn = getattr(specialized_agents, factory_name)

        # Without suffix
        agent_no_suffix = factory_fn()
        assert agent_no_suffix.name == expected_agent_name

        # With suffix
        agent_with_suffix = factory_fn(name_suffix="_test")
        assert agent_with_suffix.name == f"{expected_agent_name}_test"


class TestSingletonsUnchanged:
    """Tests that singleton agent instances remain unchanged.

    Note: agents migrated to ``PikarBaseAgent`` (financial, content) have
    their module-level singletons set to ``None`` — instances are built
    lazily per-user via the factory. The ``content_agent``/``financial_agent``
    symbols still import cleanly; their contract is asserted in the
    per-agent ``test_specialized_agents_reexports`` modules.
    """

    def test_unmigrated_singleton_agents_still_exist(self):
        """Unmigrated singleton agents are still concrete instances."""
        from app.agents.specialized_agents import (
            compliance_agent,
            customer_support_agent,
            data_agent,
            marketing_agent,
            operations_agent,
            sales_agent,
            strategic_agent,
        )

        # Unmigrated singletons should exist
        assert strategic_agent is not None
        assert sales_agent is not None
        assert marketing_agent is not None
        assert operations_agent is not None
        assert compliance_agent is not None
        assert customer_support_agent is not None
        assert data_agent is not None

    def test_migrated_singletons_are_none_sentinels(self):
        """Migrated agents (financial, content, hr) export ``None`` sentinels."""
        from app.agents.specialized_agents import (
            content_agent,
            financial_agent,
            hr_agent,
        )

        assert financial_agent is None
        assert content_agent is None
        assert hr_agent is None

    def test_singleton_is_same_instance_on_reimport(self):
        """Test that singleton returns same instance on multiple imports."""
        from app.agents.specialized_agents import strategic_agent as sa1
        from app.agents.specialized_agents import strategic_agent as sa2

        assert sa1 is sa2

    def test_factory_creates_different_instance_than_singleton(self):
        """Test that factory instance is different from singleton."""
        from app.agents.specialized_agents import (
            create_strategic_agent,
            strategic_agent,
        )

        factory_agent = create_strategic_agent()

        # Factory should create different instance
        assert factory_agent is not strategic_agent
        # But with same base configuration
        assert factory_agent.name == strategic_agent.name


class TestSpecializedAgentsList:
    """Tests for the SPECIALIZED_AGENTS list."""

    def test_specialized_agents_contains_unmigrated_agents(self):
        """SPECIALIZED_AGENTS holds every unmigrated specialist (W2/W4 filter
        ``None`` placeholders for migrated agents).

        Live source list has 12 entries (financial + content + hr + 9 unmigrated).
        Post-W4-HR the filter drops the 3 migrated agents, leaving 9.
        """
        from app.agents.specialized_agents import SPECIALIZED_AGENTS

        assert len(SPECIALIZED_AGENTS) == 9

    def test_specialized_agents_are_singletons(self):
        """SPECIALIZED_AGENTS contains the unmigrated singleton instances."""
        from app.agents.specialized_agents import (
            SPECIALIZED_AGENTS,
            strategic_agent,
        )

        # An unmigrated singleton should be in the list
        assert strategic_agent in SPECIALIZED_AGENTS
