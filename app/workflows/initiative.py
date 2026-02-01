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

"""Initiative & Project Lifecycle Workflows (Category 1).

This module implements 6 workflow agents for initiative lifecycle management:
1. InitiativeIdeationPipeline - Brainstorm and validate initiative ideas
2. InitiativeValidationPipeline - Multi-perspective feasibility analysis
3. InitiativeBuildPipeline - Plan resources and execution timeline
4. InitiativeTestPipeline - Iterative quality and compliance check
5. InitiativeLaunchPipeline - Coordinated go-to-market execution
6. InitiativeScalePipeline - Growth optimization post-launch

Note: Executive Agent handles synthesis externally per Agent-Eco-System.md.

Architecture Note: Uses factory functions to create fresh agent instances for each
workflow to avoid ADK's single-parent constraint. Each workflow gets its own
agent instances that are independent from ExecutiveAgent's sub_agents.
"""

from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent

# Import factory functions instead of singleton instances
from app.agents.specialized_agents import (
    create_strategic_agent,
    create_content_agent,
    create_data_agent,
    create_financial_agent,
    create_operations_agent,
    create_hr_agent,
    create_marketing_agent,
    create_sales_agent,
    create_compliance_agent,
)


# =============================================================================
# 1. InitiativeIdeationPipeline
# =============================================================================

def create_initiative_ideation_pipeline() -> SequentialAgent:
    """Create InitiativeIdeationPipeline with fresh agent instances.

    Returns:
        A SequentialAgent for brainstorming and validating initiative ideas
        through strategic, content, and data analysis.
    """
    return SequentialAgent(
        name="InitiativeIdeationPipeline",
        description="Brainstorm and validate initiative ideas through strategic, content, and data analysis",
        sub_agents=[
            create_strategic_agent(),
            create_content_agent(),
            create_data_agent(),
        ],
    )


# =============================================================================
# 2. InitiativeValidationPipeline
# =============================================================================

def create_initiative_validation_pipeline() -> SequentialAgent:
    """Create InitiativeValidationPipeline with fresh agent instances.

    Returns:
        A SequentialAgent containing parallel analysis for multi-perspective
        feasibility analysis with data, financial, and strategic agents.
    """
    validation_parallel = ParallelAgent(
        name="ValidationParallelAnalysis",
        description="Concurrent multi-perspective feasibility analysis",
        sub_agents=[
            create_data_agent(),
            create_financial_agent(),
            create_strategic_agent(),
        ],
    )
    return SequentialAgent(
        name="InitiativeValidationPipeline",
        description="Multi-perspective feasibility analysis with parallel data gathering",
        sub_agents=[validation_parallel],
    )


# =============================================================================
# 3. InitiativeBuildPipeline
# =============================================================================

def create_initiative_build_pipeline() -> SequentialAgent:
    """Create InitiativeBuildPipeline with fresh agent instances.

    Returns:
        A SequentialAgent for planning resources and execution timeline
        through strategic, operations, and HR analysis.
    """
    return SequentialAgent(
        name="InitiativeBuildPipeline",
        description="Plan resources and execution timeline for an initiative",
        sub_agents=[
            create_strategic_agent(),
            create_operations_agent(),
            create_hr_agent(),
        ],
    )


# =============================================================================
# 4. InitiativeTestPipeline
# =============================================================================

def create_initiative_test_pipeline() -> LoopAgent:
    """Create InitiativeTestPipeline with fresh agent instances.

    Returns:
        A LoopAgent for iterative quality and compliance checking
        until all criteria pass (max 5 iterations).
    """
    test_sequential = SequentialAgent(
        name="TestQualityCheck",
        description="Single iteration of quality and compliance verification",
        sub_agents=[
            create_operations_agent(),
            create_data_agent(),
            create_compliance_agent(),
        ],
    )
    return LoopAgent(
        name="InitiativeTestPipeline",
        description="Iterative quality and compliance check until all criteria pass",
        sub_agents=[test_sequential],
        max_iterations=5,
    )


# =============================================================================
# 5. InitiativeLaunchPipeline
# =============================================================================

def create_initiative_launch_pipeline() -> SequentialAgent:
    """Create InitiativeLaunchPipeline with fresh agent instances.

    Returns:
        A SequentialAgent containing parallel go-to-market preparation
        across marketing, sales, and content teams.
    """
    launch_parallel = ParallelAgent(
        name="LaunchParallelPrep",
        description="Concurrent go-to-market preparation across marketing, sales, and content",
        sub_agents=[
            create_marketing_agent(),
            create_sales_agent(),
            create_content_agent(),
        ],
    )
    return SequentialAgent(
        name="InitiativeLaunchPipeline",
        description="Coordinated go-to-market execution with parallel preparation",
        sub_agents=[launch_parallel],
    )


# =============================================================================
# 6. InitiativeScalePipeline
# =============================================================================

def create_initiative_scale_pipeline() -> SequentialAgent:
    """Create InitiativeScalePipeline with fresh agent instances.

    Returns:
        A SequentialAgent for growth optimization post-launch through
        data-driven financial and strategic analysis.
    """
    return SequentialAgent(
        name="InitiativeScalePipeline",
        description="Growth optimization post-launch through data-driven financial and strategic analysis",
        sub_agents=[
            create_data_agent(),
            create_financial_agent(),
            create_strategic_agent(),
            create_operations_agent(),
        ],
    )


# =============================================================================
# Exports
# =============================================================================

# Factory function registry for lazy workflow instantiation
INITIATIVE_WORKFLOW_FACTORIES = {
    "InitiativeIdeationPipeline": create_initiative_ideation_pipeline,
    "InitiativeValidationPipeline": create_initiative_validation_pipeline,
    "InitiativeBuildPipeline": create_initiative_build_pipeline,
    "InitiativeTestPipeline": create_initiative_test_pipeline,
    "InitiativeLaunchPipeline": create_initiative_launch_pipeline,
    "InitiativeScalePipeline": create_initiative_scale_pipeline,
}

__all__ = [
    # Factory functions for workflow creation
    "create_initiative_ideation_pipeline",
    "create_initiative_validation_pipeline",
    "create_initiative_build_pipeline",
    "create_initiative_test_pipeline",
    "create_initiative_launch_pipeline",
    "create_initiative_scale_pipeline",
    # Registry for dynamic access
    "INITIATIVE_WORKFLOW_FACTORIES",
]
