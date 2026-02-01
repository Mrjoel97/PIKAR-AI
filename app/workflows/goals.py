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

"""Goal Setting & Monitoring Workflows (Category 5).

This module implements 4 workflow agents for goal management:
27. OKRCreationPipeline - Create objectives and key results
28. GoalTrackingPipeline - Continuous goal progress monitoring
29. KPIDashboardPipeline - Real-time KPI aggregation
30. QuarterlyReviewPipeline - Quarterly business review

Architecture Note: Uses factory functions to create fresh agent instances for each
workflow to avoid ADK's single-parent constraint.
"""

from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent

from app.agents.specialized_agents import (
    create_strategic_agent,
    create_data_agent,
    create_financial_agent,
    create_sales_agent,
)


# =============================================================================
# 27. OKRCreationPipeline
# =============================================================================

def create_okr_creation_pipeline() -> SequentialAgent:
    """Create OKRCreationPipeline with fresh agent instances."""
    return SequentialAgent(
        name="OKRCreationPipeline",
        description="Create objectives and key results through strategic and data analysis",
        sub_agents=[
            create_strategic_agent(),
            create_data_agent(),
        ],
    )


# =============================================================================
# 28. GoalTrackingPipeline
# =============================================================================

def create_goal_tracking_pipeline() -> LoopAgent:
    """Create GoalTrackingPipeline with fresh agent instances."""
    goal_tracking_cycle = SequentialAgent(
        name="GoalTrackingCycle",
        description="Single iteration of goal progress monitoring",
        sub_agents=[
            create_data_agent(),
            create_strategic_agent(),
        ],
    )
    return LoopAgent(
        name="GoalTrackingPipeline",
        description="Continuous goal progress monitoring with weekly iterations",
        sub_agents=[goal_tracking_cycle],
        max_iterations=12,  # Quarterly tracking (12 weeks)
    )


# =============================================================================
# 29. KPIDashboardPipeline
# =============================================================================

def create_kpi_dashboard_pipeline() -> SequentialAgent:
    """Create KPIDashboardPipeline with fresh agent instances."""
    kpi_parallel = ParallelAgent(
        name="KPIDataGathering",
        description="Parallel KPI data collection from multiple sources",
        sub_agents=[
            create_data_agent(),
            create_financial_agent(),
            create_sales_agent(),
        ],
    )
    return SequentialAgent(
        name="KPIDashboardPipeline",
        description="Real-time KPI aggregation with parallel data gathering",
        sub_agents=[kpi_parallel],
    )


# =============================================================================
# 30. QuarterlyReviewPipeline
# =============================================================================

def create_quarterly_review_pipeline() -> SequentialAgent:
    """Create QuarterlyReviewPipeline with fresh agent instances."""
    return SequentialAgent(
        name="QuarterlyReviewPipeline",
        description="Quarterly business review through comprehensive analysis",
        sub_agents=[
            create_data_agent(),
            create_financial_agent(),
            create_strategic_agent(),
        ],
    )


# =============================================================================
# Exports
# =============================================================================

GOALS_WORKFLOW_FACTORIES = {
    "OKRCreationPipeline": create_okr_creation_pipeline,
    "GoalTrackingPipeline": create_goal_tracking_pipeline,
    "KPIDashboardPipeline": create_kpi_dashboard_pipeline,
    "QuarterlyReviewPipeline": create_quarterly_review_pipeline,
}

__all__ = [
    "create_okr_creation_pipeline",
    "create_goal_tracking_pipeline",
    "create_kpi_dashboard_pipeline",
    "create_quarterly_review_pipeline",
    "GOALS_WORKFLOW_FACTORIES",
]
