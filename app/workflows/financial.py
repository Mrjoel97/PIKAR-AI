# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Financial Planning & Analysis Workflows.

This module implements workflow agents for financial modeling and analysis:
- FinancialModelCreationPipeline - Build comprehensive financial models
- BudgetPlanningPipeline - Annual/quarterly budget planning
- RevenueAnalysisPipeline - Revenue trends and forecasting
- CostOptimizationPipeline - Cost reduction analysis
- InvestorReadinessPipeline - Prepare for investor presentations
- CashFlowAnalysisPipeline - Cash flow management and forecasting

Architecture Note: Uses factory functions to create fresh agent instances for each
workflow to avoid ADK's single-parent constraint.
"""

from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent

from app.agents.specialized_agents import (
    create_strategic_agent,
    create_content_agent,
    create_data_agent,
    create_financial_agent,
    create_operations_agent,
    create_sales_agent,
    create_compliance_agent,
)


# =============================================================================
# FinancialModelCreationPipeline
# =============================================================================

def create_financial_model_creation_pipeline() -> SequentialAgent:
    """Create FinancialModelCreationPipeline with fresh agent instances."""
    # Stage 1: Parallel data gathering from multiple perspectives
    financial_model_research = ParallelAgent(
        name="FinancialModelResearch",
        description="Parallel research gathering financial data, market analysis, and strategic context",
        sub_agents=[
            create_data_agent(),
            create_strategic_agent(),
        ],
    )
    # Stage 2: Financial model construction
    financial_model_construction = SequentialAgent(
        name="FinancialModelConstruction",
        description="Build financial model with financial analysis and compliance review",
        sub_agents=[
            create_financial_agent(),
            create_compliance_agent(),
        ],
    )
    # Full pipeline: Research → Model → Documentation
    return SequentialAgent(
        name="FinancialModelCreationPipeline",
        description="End-to-end financial model creation: research, construction, and documentation",
        sub_agents=[financial_model_research, financial_model_construction, create_content_agent()],
    )


# =============================================================================
# BudgetPlanningPipeline
# =============================================================================

def create_budget_planning_pipeline() -> SequentialAgent:
    """Create BudgetPlanningPipeline with fresh agent instances."""
    budget_analysis = ParallelAgent(
        name="BudgetAnalysis",
        description="Parallel analysis of financial and operational budget requirements",
        sub_agents=[
            create_financial_agent(),
            create_operations_agent(),
        ],
    )
    return SequentialAgent(
        name="BudgetPlanningPipeline",
        description="Comprehensive budget planning with financial and operational alignment",
        sub_agents=[budget_analysis, create_strategic_agent()],
    )


# =============================================================================
# RevenueAnalysisPipeline
# =============================================================================

def create_revenue_analysis_pipeline() -> SequentialAgent:
    """Create RevenueAnalysisPipeline with fresh agent instances."""
    return SequentialAgent(
        name="RevenueAnalysisPipeline",
        description="Revenue analysis and forecasting from data to financial insights",
        sub_agents=[
            create_data_agent(),
            create_sales_agent(),
            create_financial_agent(),
        ],
    )


# =============================================================================
# CostOptimizationPipeline
# =============================================================================

def create_cost_optimization_pipeline() -> LoopAgent:
    """Create CostOptimizationPipeline with fresh agent instances."""
    cost_analysis_cycle = SequentialAgent(
        name="CostAnalysisCycle",
        description="Single iteration of cost analysis and optimization recommendations",
        sub_agents=[
            create_financial_agent(),
            create_operations_agent(),
        ],
    )
    return LoopAgent(
        name="CostOptimizationPipeline",
        description="Iterative cost reduction analysis with refinement until targets met",
        sub_agents=[cost_analysis_cycle],
        max_iterations=3,
    )


# =============================================================================
# InvestorReadinessPipeline
# =============================================================================

def create_investor_readiness_pipeline() -> SequentialAgent:
    """Create InvestorReadinessPipeline with fresh agent instances."""
    investor_assessment = ParallelAgent(
        name="InvestorAssessment",
        description="Parallel assessment of financial health, strategic positioning, and compliance",
        sub_agents=[
            create_financial_agent(),
            create_strategic_agent(),
            create_compliance_agent(),
        ],
    )
    return SequentialAgent(
        name="InvestorReadinessPipeline",
        description="Prepare investor-ready materials with comprehensive business analysis",
        sub_agents=[investor_assessment, create_content_agent()],
    )


# =============================================================================
# CashFlowAnalysisPipeline
# =============================================================================

def create_cash_flow_analysis_pipeline() -> SequentialAgent:
    """Create CashFlowAnalysisPipeline with fresh agent instances."""
    return SequentialAgent(
        name="CashFlowAnalysisPipeline",
        description="Cash flow management and forecasting analysis",
        sub_agents=[
            create_data_agent(),
            create_financial_agent(),
            create_operations_agent(),
        ],
    )


# =============================================================================
# Exports
# =============================================================================

FINANCIAL_WORKFLOW_FACTORIES = {
    "FinancialModelCreationPipeline": create_financial_model_creation_pipeline,
    "BudgetPlanningPipeline": create_budget_planning_pipeline,
    "RevenueAnalysisPipeline": create_revenue_analysis_pipeline,
    "CostOptimizationPipeline": create_cost_optimization_pipeline,
    "InvestorReadinessPipeline": create_investor_readiness_pipeline,
    "CashFlowAnalysisPipeline": create_cash_flow_analysis_pipeline,
}

__all__ = [
    "create_financial_model_creation_pipeline",
    "create_budget_planning_pipeline",
    "create_revenue_analysis_pipeline",
    "create_cost_optimization_pipeline",
    "create_investor_readiness_pipeline",
    "create_cash_flow_analysis_pipeline",
    "FINANCIAL_WORKFLOW_FACTORIES",
]

