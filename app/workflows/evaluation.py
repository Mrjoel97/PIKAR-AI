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

"""Evaluation & Analysis Workflows (Category 6).

This module implements 6 workflow agents for business analysis:
31. BusinessEvaluationPipeline - 360° business health assessment
32. ProjectEvaluationPipeline - Post-project analysis
33. UserActivityAnalysisPipeline - User behavior insights
34. GrowthEvaluationPipeline - Growth trajectory analysis
35. CompetitorAnalysisPipeline - Competitive intelligence
36. MarketResearchPipeline - Comprehensive market analysis

Architecture Note: Uses factory functions to create fresh agent instances for each
workflow to avoid ADK's single-parent constraint.
"""

from google.adk.agents import SequentialAgent, ParallelAgent

from app.agents.specialized_agents import (
    create_strategic_agent,
    create_content_agent,
    create_data_agent,
    create_financial_agent,
    create_operations_agent,
    create_marketing_agent,
    create_sales_agent,
)


# =============================================================================
# 31. BusinessEvaluationPipeline (Consensus Pattern)
# =============================================================================

def create_business_evaluation_pipeline() -> SequentialAgent:
    """Create BusinessEvaluationPipeline with fresh agent instances."""
    business_eval_parallel = ParallelAgent(
        name="BusinessEvalConsensus",
        description="Parallel 360° analysis from financial, data, and strategic perspectives",
        sub_agents=[
            create_financial_agent(),
            create_data_agent(),
            create_strategic_agent(),
        ],
    )
    return SequentialAgent(
        name="BusinessEvaluationPipeline",
        description="360° business health assessment with multi-perspective consensus",
        sub_agents=[business_eval_parallel],
    )


# =============================================================================
# 32. ProjectEvaluationPipeline
# =============================================================================

def create_project_evaluation_pipeline() -> SequentialAgent:
    """Create ProjectEvaluationPipeline with fresh agent instances."""
    return SequentialAgent(
        name="ProjectEvaluationPipeline",
        description="Post-project analysis through data, operations, and financial review",
        sub_agents=[
            create_data_agent(),
            create_operations_agent(),
            create_financial_agent(),
        ],
    )


# =============================================================================
# 33. UserActivityAnalysisPipeline
# =============================================================================

def create_user_activity_analysis_pipeline() -> SequentialAgent:
    """Create UserActivityAnalysisPipeline with fresh agent instances."""
    return SequentialAgent(
        name="UserActivityAnalysisPipeline",
        description="User behavior insights from data to marketing to sales",
        sub_agents=[
            create_data_agent(),
            create_marketing_agent(),
            create_sales_agent(),
        ],
    )


# =============================================================================
# 34. GrowthEvaluationPipeline
# =============================================================================

def create_growth_evaluation_pipeline() -> SequentialAgent:
    """Create GrowthEvaluationPipeline with fresh agent instances."""
    return SequentialAgent(
        name="GrowthEvaluationPipeline",
        description="Growth trajectory analysis through data, financial, and strategic lens",
        sub_agents=[
            create_data_agent(),
            create_financial_agent(),
            create_strategic_agent(),
        ],
    )


# =============================================================================
# 35. CompetitorAnalysisPipeline
# =============================================================================

def create_competitor_analysis_pipeline() -> SequentialAgent:
    """Create CompetitorAnalysisPipeline with fresh agent instances."""
    return SequentialAgent(
        name="CompetitorAnalysisPipeline",
        description="Competitive intelligence gathering and analysis",
        sub_agents=[
            create_strategic_agent(),
            create_data_agent(),
            create_sales_agent(),
        ],
    )


# =============================================================================
# 36. MarketResearchPipeline
# =============================================================================

def create_market_research_pipeline() -> SequentialAgent:
    """Create MarketResearchPipeline with fresh agent instances."""
    market_research_parallel = ParallelAgent(
        name="MarketResearchGathering",
        description="Parallel market data gathering from data and strategic perspectives",
        sub_agents=[
            create_data_agent(),
            create_strategic_agent(),
        ],
    )
    return SequentialAgent(
        name="MarketResearchPipeline",
        description="Comprehensive market analysis with parallel research and content synthesis",
        sub_agents=[market_research_parallel, create_marketing_agent(), create_content_agent()],
    )


# =============================================================================
# Exports
# =============================================================================

EVALUATION_WORKFLOW_FACTORIES = {
    "BusinessEvaluationPipeline": create_business_evaluation_pipeline,
    "ProjectEvaluationPipeline": create_project_evaluation_pipeline,
    "UserActivityAnalysisPipeline": create_user_activity_analysis_pipeline,
    "GrowthEvaluationPipeline": create_growth_evaluation_pipeline,
    "CompetitorAnalysisPipeline": create_competitor_analysis_pipeline,
    "MarketResearchPipeline": create_market_research_pipeline,
}

__all__ = [
    "create_business_evaluation_pipeline",
    "create_project_evaluation_pipeline",
    "create_user_activity_analysis_pipeline",
    "create_growth_evaluation_pipeline",
    "create_competitor_analysis_pipeline",
    "create_market_research_pipeline",
    "EVALUATION_WORKFLOW_FACTORIES",
]
