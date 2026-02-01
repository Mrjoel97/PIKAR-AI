"""Unit tests for agent factory functions.

Tests that factory functions create fresh agent instances without parent
assignments, ensuring the hybrid architecture resolves ADK's single-parent
constraint.
"""
import pytest
from unittest.mock import patch, MagicMock


# Test data for agent factory verification
AGENT_FACTORIES = [
    ("create_financial_agent", "FinancialAnalysisAgent"),
    ("create_content_agent", "ContentCreationAgent"),
    ("create_strategic_agent", "StrategicPlanningAgent"),
    ("create_sales_agent", "SalesIntelligenceAgent"),
    ("create_marketing_agent", "MarketingAutomationAgent"),
    ("create_operations_agent", "OperationsOptimizationAgent"),
    ("create_hr_agent", "HRRecruitmentAgent"),
    ("create_compliance_agent", "ComplianceRiskAgent"),
    ("create_customer_support_agent", "CustomerSupportAgent"),
    ("create_data_agent", "DataAnalysisAgent"),
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
    def test_factory_creates_agent_with_correct_name(self, factory_name, expected_agent_name):
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
    """Tests that singleton agent instances remain unchanged."""

    def test_singleton_agents_still_exist(self):
        """Test that original singleton agents are still available."""
        from app.agents.specialized_agents import (
            financial_agent,
            content_agent,
            strategic_agent,
            sales_agent,
            marketing_agent,
            operations_agent,
            hr_agent,
            compliance_agent,
            customer_support_agent,
            data_agent,
        )
        
        # All singletons should exist
        assert financial_agent is not None
        assert content_agent is not None
        assert strategic_agent is not None
        assert sales_agent is not None
        assert marketing_agent is not None
        assert operations_agent is not None
        assert hr_agent is not None
        assert compliance_agent is not None
        assert customer_support_agent is not None
        assert data_agent is not None

    def test_singleton_is_same_instance_on_reimport(self):
        """Test that singleton returns same instance on multiple imports."""
        from app.agents.specialized_agents import financial_agent as fa1
        from app.agents.specialized_agents import financial_agent as fa2
        
        assert fa1 is fa2

    def test_factory_creates_different_instance_than_singleton(self):
        """Test that factory instance is different from singleton."""
        from app.agents.specialized_agents import (
            financial_agent,
            create_financial_agent,
        )
        
        factory_agent = create_financial_agent()
        
        # Factory should create different instance
        assert factory_agent is not financial_agent
        # But with same base configuration
        assert factory_agent.name == financial_agent.name


class TestSpecializedAgentsList:
    """Tests for the SPECIALIZED_AGENTS list."""

    def test_specialized_agents_contains_10_agents(self):
        """Test that SPECIALIZED_AGENTS has exactly 10 agents."""
        from app.agents.specialized_agents import SPECIALIZED_AGENTS
        
        assert len(SPECIALIZED_AGENTS) == 10

    def test_specialized_agents_are_singletons(self):
        """Test that SPECIALIZED_AGENTS contains the singleton instances."""
        from app.agents.specialized_agents import (
            SPECIALIZED_AGENTS,
            financial_agent,
            strategic_agent,
        )
        
        # Singletons should be in the list
        assert financial_agent in SPECIALIZED_AGENTS
        assert strategic_agent in SPECIALIZED_AGENTS

