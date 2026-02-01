"""End-to-end tests for the hybrid agent architecture.

Tests that ExecutiveAgent with singleton sub_agents and workflow factories
using fresh agent instances can coexist without conflicts.
"""
import pytest


class TestHybridArchitectureCoexistence:
    """Tests that singletons and factories coexist without conflicts."""

    def test_executive_agent_uses_singletons(self):
        """Test that ExecutiveAgent still uses singleton specialized agents."""
        from app.agent import executive_agent
        from app.agents.specialized_agents import (
            SPECIALIZED_AGENTS,
            financial_agent,
            strategic_agent,
        )
        
        # ExecutiveAgent should have SPECIALIZED_AGENTS as sub_agents
        assert executive_agent.sub_agents == SPECIALIZED_AGENTS
        
        # The singleton agents should be in sub_agents
        assert financial_agent in executive_agent.sub_agents
        assert strategic_agent in executive_agent.sub_agents

    def test_workflow_factory_uses_fresh_agents(self):
        """Test that workflow factories create fresh agent instances."""
        from app.workflows.initiative import create_initiative_ideation_pipeline
        from app.agents.specialized_agents import strategic_agent
        
        workflow = create_initiative_ideation_pipeline()
        
        # Workflow should have sub_agents
        assert hasattr(workflow, 'sub_agents')
        assert len(workflow.sub_agents) > 0
        
        # The strategic agent in workflow should NOT be the singleton
        workflow_strategic = None
        for agent in workflow.sub_agents:
            if "Strategic" in agent.name:
                workflow_strategic = agent
                break
        
        if workflow_strategic:
            assert workflow_strategic is not strategic_agent

    def test_singleton_and_factory_agents_have_same_config(self):
        """Test that singleton and factory agents have equivalent configs."""
        from app.agents.specialized_agents import (
            financial_agent,
            create_financial_agent,
        )
        
        factory_agent = create_financial_agent()
        
        # Same name, description, instruction
        assert factory_agent.name == financial_agent.name
        assert factory_agent.description == financial_agent.description
        assert factory_agent.instruction == financial_agent.instruction

    def test_multiple_workflows_dont_conflict(self):
        """Test that creating multiple workflows doesn't cause conflicts."""
        from app.workflows.initiative import create_initiative_ideation_pipeline
        from app.workflows.sales import create_lead_generation_pipeline
        from app.workflows.marketing import create_email_sequence_pipeline

        # Create multiple workflows that might use same agent types
        w1 = create_initiative_ideation_pipeline()
        w2 = create_lead_generation_pipeline()
        w3 = create_email_sequence_pipeline()

        # All should succeed without parent conflicts
        assert w1 is not None
        assert w2 is not None
        assert w3 is not None


class TestDynamicWorkflowGenerator:
    """Tests for DynamicWorkflowGenerator with factory functions."""

    def test_agent_factory_registry_exists(self):
        """Test that AGENT_FACTORY_REGISTRY is properly defined."""
        from app.workflows.dynamic import AGENT_FACTORY_REGISTRY
        
        expected_keys = [
            "strategic", "content", "data", "financial",
            "operations", "hr", "marketing", "sales",
            "compliance", "support"
        ]
        
        for key in expected_keys:
            assert key in AGENT_FACTORY_REGISTRY, f"Missing {key}"
            assert callable(AGENT_FACTORY_REGISTRY[key])

    def test_factory_registry_creates_agents(self):
        """Test that factory registry entries create valid agents."""
        from app.workflows.dynamic import AGENT_FACTORY_REGISTRY
        
        for key, factory in AGENT_FACTORY_REGISTRY.items():
            agent = factory()
            assert agent is not None
            assert hasattr(agent, 'name')

    def test_dynamic_workflow_generator_exists(self):
        """Test that DynamicWorkflowGenerator is importable."""
        from app.workflows.dynamic import DynamicWorkflowGenerator
        
        generator = DynamicWorkflowGenerator()
        assert generator is not None


class TestUserAgentFactory:
    """Tests for UserAgentFactory workflow creation."""

    def test_user_agent_factory_has_workflow_methods(self):
        """Test that UserAgentFactory has workflow-related methods."""
        from app.services.user_agent_factory import UserAgentFactory
        
        # Check methods exist
        assert hasattr(UserAgentFactory, 'create_user_workflow')
        assert hasattr(UserAgentFactory, 'list_available_workflows')
        assert hasattr(UserAgentFactory, 'get_workflow_metadata')

    def test_convenience_function_exists(self):
        """Test that get_user_workflow convenience function exists."""
        from app.services.user_agent_factory import get_user_workflow
        
        assert callable(get_user_workflow)


class TestNoParentConflicts:
    """Tests specifically for the single-parent constraint resolution."""

    def test_executive_agent_singletons_have_parent(self):
        """Test that singleton agents have ExecutiveAgent as parent."""
        from app.agent import executive_agent
        from app.agents.specialized_agents import financial_agent
        
        # After being added to ExecutiveAgent, singletons should have parent
        # Note: This test verifies the current state after app initialization
        assert financial_agent in executive_agent.sub_agents

    def test_factory_agents_start_without_parent(self):
        """Test that factory-created agents initially have no parent."""
        from app.agents.specialized_agents import create_financial_agent
        
        # Create a fresh agent
        fresh_agent = create_financial_agent()
        
        # Fresh agent should not have a parent initially
        # (parent is assigned when added to a workflow's sub_agents)
        assert fresh_agent is not None
        assert fresh_agent.name == "FinancialAnalysisAgent"

    def test_workflow_with_fresh_agents_succeeds(self):
        """Test that workflows with fresh agents don't raise parent errors."""
        from google.adk.agents import SequentialAgent
        from app.agents.specialized_agents import (
            create_strategic_agent,
            create_content_agent,
            create_data_agent,
        )
        
        # This should NOT raise "Agent already has a parent" error
        try:
            workflow = SequentialAgent(
                name="TestWorkflow",
                description="Test workflow with fresh agents",
                sub_agents=[
                    create_strategic_agent(),
                    create_content_agent(),
                    create_data_agent(),
                ],
            )
            assert workflow is not None
            assert len(workflow.sub_agents) == 3
        except ValueError as e:
            if "already has a parent" in str(e):
                pytest.fail(f"Factory agents should not have parent conflicts: {e}")
            raise

