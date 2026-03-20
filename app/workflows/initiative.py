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

from google.adk.agents import LoopAgent, ParallelAgent, SequentialAgent


# Lazy import of agent factories to avoid circular import:
# workflows.initiative -> specialized_agents -> strategic -> tools.workflows -> workflows.engine -> workflows.initiative
def _get_agent_factories():
    from app.agents.specialized_agents import (
        create_compliance_agent,
        create_content_agent,
        create_data_agent,
        create_financial_agent,
        create_hr_agent,
        create_marketing_agent,
        create_operations_agent,
        create_sales_agent,
        create_strategic_agent,
    )

    return {
        "create_strategic_agent": create_strategic_agent,
        "create_content_agent": create_content_agent,
        "create_data_agent": create_data_agent,
        "create_financial_agent": create_financial_agent,
        "create_operations_agent": create_operations_agent,
        "create_hr_agent": create_hr_agent,
        "create_marketing_agent": create_marketing_agent,
        "create_sales_agent": create_sales_agent,
        "create_compliance_agent": create_compliance_agent,
    }


# =============================================================================
# 1. InitiativeIdeationPipeline
# =============================================================================


def create_initiative_ideation_pipeline() -> SequentialAgent:
    """Create InitiativeIdeationPipeline with fresh agent instances.

    Returns:
        A SequentialAgent for brainstorming and validating initiative ideas
        through strategic, content, and data analysis.
    """
    f = _get_agent_factories()
    return SequentialAgent(
        name="InitiativeIdeationPipeline",
        description="Brainstorm and validate initiative ideas through strategic, content, and data analysis",
        sub_agents=[
            f["create_strategic_agent"](
                name_suffix="_ideation", output_key="strategic_ideation_output"
            ),
            f["create_content_agent"](
                name_suffix="_ideation", output_key="content_ideation_output"
            ),
            f["create_data_agent"](
                name_suffix="_ideation", output_key="data_ideation_output"
            ),
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
    f = _get_agent_factories()
    validation_parallel = ParallelAgent(
        name="ValidationParallelAnalysis",
        description="Concurrent multi-perspective feasibility analysis",
        sub_agents=[
            f["create_data_agent"](
                name_suffix="_validation", output_key="data_validation_output"
            ),
            f["create_financial_agent"](
                name_suffix="_validation", output_key="financial_validation_output"
            ),
            f["create_strategic_agent"](
                name_suffix="_validation", output_key="strategic_validation_output"
            ),
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
    f = _get_agent_factories()
    return SequentialAgent(
        name="InitiativeBuildPipeline",
        description="Plan resources and execution timeline for an initiative",
        sub_agents=[
            f["create_strategic_agent"](
                name_suffix="_build", output_key="strategic_build_output"
            ),
            f["create_operations_agent"](
                name_suffix="_build", output_key="operations_build_output"
            ),
            f["create_hr_agent"](name_suffix="_build", output_key="hr_build_output"),
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
    f = _get_agent_factories()
    test_sequential = SequentialAgent(
        name="TestQualityCheck",
        description="Single iteration of quality and compliance verification",
        sub_agents=[
            f["create_operations_agent"](
                name_suffix="_test", output_key="operations_test_output"
            ),
            f["create_data_agent"](name_suffix="_test", output_key="data_test_output"),
            f["create_compliance_agent"](
                name_suffix="_test", output_key="compliance_test_output"
            ),
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
    f = _get_agent_factories()
    launch_parallel = ParallelAgent(
        name="LaunchParallelPrep",
        description="Concurrent go-to-market preparation across marketing, sales, and content",
        sub_agents=[
            f["create_marketing_agent"](
                name_suffix="_launch", output_key="marketing_launch_output"
            ),
            f["create_sales_agent"](
                name_suffix="_launch", output_key="sales_launch_output"
            ),
            f["create_content_agent"](
                name_suffix="_launch", output_key="content_launch_output"
            ),
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
    f = _get_agent_factories()
    return SequentialAgent(
        name="InitiativeScalePipeline",
        description="Growth optimization post-launch through data-driven financial and strategic analysis",
        sub_agents=[
            f["create_data_agent"](
                name_suffix="_scale", output_key="data_scale_output"
            ),
            f["create_financial_agent"](
                name_suffix="_scale", output_key="financial_scale_output"
            ),
            f["create_strategic_agent"](
                name_suffix="_scale", output_key="strategic_scale_output"
            ),
            f["create_operations_agent"](
                name_suffix="_scale", output_key="operations_scale_output"
            ),
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
