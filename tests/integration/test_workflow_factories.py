"""Integration tests for workflow factory functions.

Tests that workflow factories create valid pipelines without raising
ADK's single-parent validation errors.
"""
import pytest


class TestWorkflowFactoriesExist:
    """Tests that all workflow factory registries are properly exported."""

    def test_initiative_workflow_factories_exist(self):
        """Test initiative workflow factories are exported."""
        from app.workflows.initiative import INITIATIVE_WORKFLOW_FACTORIES
        
        expected = [
            "InitiativeIdeationPipeline",
            "InitiativeValidationPipeline",
            "InitiativeBuildPipeline",
            "InitiativeTestPipeline",
            "InitiativeLaunchPipeline",
            "InitiativeScalePipeline",
        ]
        
        for name in expected:
            assert name in INITIATIVE_WORKFLOW_FACTORIES, f"Missing {name}"

    def test_sales_workflow_factories_exist(self):
        """Test sales workflow factories are exported."""
        from app.workflows.sales import SALES_WORKFLOW_FACTORIES

        expected = [
            "LeadGenerationPipeline",
            "LeadScoringPipeline",
            "LeadNurturingPipeline",
            "SalesFunnelCreationPipeline",
            "DealQualificationPipeline",
            "OutreachSequencePipeline",
            "CustomerJourneyPipeline",
        ]

        for name in expected:
            assert name in SALES_WORKFLOW_FACTORIES, f"Missing {name}"

    def test_marketing_workflow_factories_exist(self):
        """Test marketing workflow factories are exported."""
        from app.workflows.marketing import MARKETING_WORKFLOW_FACTORIES
        
        assert len(MARKETING_WORKFLOW_FACTORIES) >= 10

    def test_financial_workflow_factories_exist(self):
        """Test financial workflow factories are exported."""
        from app.workflows.financial import FINANCIAL_WORKFLOW_FACTORIES
        
        expected = [
            "FinancialModelCreationPipeline",
            "BudgetPlanningPipeline",
            "RevenueAnalysisPipeline",
            "CostOptimizationPipeline",
            "InvestorReadinessPipeline",
            "CashFlowAnalysisPipeline",
        ]
        
        for name in expected:
            assert name in FINANCIAL_WORKFLOW_FACTORIES, f"Missing {name}"


class TestWorkflowFactoryInstantiation:
    """Tests that workflow factories create valid instances."""

    def test_initiative_ideation_factory_creates_workflow(self):
        """Test InitiativeIdeationPipeline factory creates a workflow."""
        from app.workflows.initiative import create_initiative_ideation_pipeline
        
        workflow = create_initiative_ideation_pipeline()
        
        assert workflow is not None
        assert workflow.name == "InitiativeIdeationPipeline"
        assert hasattr(workflow, 'sub_agents')

    def test_sales_lead_generation_factory_creates_workflow(self):
        """Test LeadGenerationPipeline factory creates a workflow."""
        from app.workflows.sales import create_lead_generation_pipeline

        workflow = create_lead_generation_pipeline()

        assert workflow is not None
        assert workflow.name == "LeadGenerationPipeline"

    def test_financial_model_factory_creates_workflow(self):
        """Test FinancialModelCreationPipeline factory creates a workflow."""
        from app.workflows.financial import create_financial_model_creation_pipeline
        
        workflow = create_financial_model_creation_pipeline()
        
        assert workflow is not None
        assert workflow.name == "FinancialModelCreationPipeline"


class TestMultipleWorkflowInstances:
    """Tests that multiple workflow instances can coexist."""

    def test_multiple_instances_are_independent(self):
        """Test that multiple instances of same workflow are independent."""
        from app.workflows.initiative import create_initiative_ideation_pipeline
        
        workflow1 = create_initiative_ideation_pipeline()
        workflow2 = create_initiative_ideation_pipeline()
        
        # Should be different instances
        assert workflow1 is not workflow2
        
        # But same configuration
        assert workflow1.name == workflow2.name

    def test_different_workflows_can_coexist(self):
        """Test that different workflows can be instantiated together."""
        from app.workflows.initiative import create_initiative_ideation_pipeline
        from app.workflows.sales import create_lead_generation_pipeline
        from app.workflows.financial import create_financial_model_creation_pipeline

        # Create all three workflows
        initiative = create_initiative_ideation_pipeline()
        sales = create_lead_generation_pipeline()
        financial = create_financial_model_creation_pipeline()

        # All should exist without conflicts
        assert initiative is not None
        assert sales is not None
        assert financial is not None
        
        # Different workflows, different names
        assert initiative.name != sales.name
        assert sales.name != financial.name


class TestWorkflowRegistry:
    """Tests for the workflow registry with factory functions."""

    def test_registry_returns_fresh_instances(self):
        """Test that registry.get() returns fresh workflow instances."""
        from app.workflows.registry import get_workflow
        
        workflow1 = get_workflow("Initiative Ideation")
        workflow2 = get_workflow("Initiative Ideation")
        
        # Should be different instances (not cached singletons)
        if workflow1 is not None and workflow2 is not None:
            assert workflow1 is not workflow2

    def test_registry_lists_all_workflows(self):
        """Test that registry lists all registered workflows."""
        from app.workflows.registry import list_workflows

        workflows = list_workflows()

        # Should have many workflows registered
        assert len(workflows) >= 50

        # Spot check some expected workflows
        assert "Initiative Ideation" in workflows
        assert "Lead Generation" in workflows

    def test_get_workflow_factory_returns_callable(self):
        """Test that get_workflow_factory returns a callable."""
        from app.workflows.registry import get_workflow_factory
        
        factory = get_workflow_factory("Initiative Ideation")
        
        assert factory is not None
        assert callable(factory)
        
        # Calling factory should create a workflow
        workflow = factory()
        assert workflow is not None

