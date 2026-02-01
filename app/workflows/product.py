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

"""Product & Service Creation Workflows (Category 2).

This module implements 5 workflow agents for product lifecycle:
7. ProductIdeationPipeline - Market-informed product concept
8. ProductValidationPipeline - ROI and market viability assessment
9. ServiceDesignPipeline - Service blueprint and pricing
10. ProductLaunchPipeline - Full product launch coordination
11. ProductIterationPipeline - Continuous product improvement

Note: Executive Agent handles synthesis externally per Agent-Eco-System.md.

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
    create_marketing_agent,
    create_sales_agent,
)


# =============================================================================
# 7. ProductIdeationPipeline
# =============================================================================

def create_product_ideation_pipeline() -> SequentialAgent:
    """Create ProductIdeationPipeline with fresh agent instances."""
    return SequentialAgent(
        name="ProductIdeationPipeline",
        description="Market-informed product concept development through strategic, data, and content analysis",
        sub_agents=[
            create_strategic_agent(),
            create_data_agent(),
            create_content_agent(),
        ],
    )


# =============================================================================
# 8. ProductValidationPipeline (Consensus Pattern)
# =============================================================================

def create_product_validation_pipeline() -> SequentialAgent:
    """Create ProductValidationPipeline with fresh agent instances."""
    validation_parallel = ParallelAgent(
        name="ProductValidationConsensus",
        description="Parallel ROI and viability analysis from financial, data, and strategic perspectives",
        sub_agents=[
            create_financial_agent(),
            create_data_agent(),
            create_strategic_agent(),
        ],
    )
    return SequentialAgent(
        name="ProductValidationPipeline",
        description="ROI and market viability assessment with multi-perspective consensus",
        sub_agents=[validation_parallel],
    )


# =============================================================================
# 9. ServiceDesignPipeline
# =============================================================================

def create_service_design_pipeline() -> SequentialAgent:
    """Create ServiceDesignPipeline with fresh agent instances."""
    return SequentialAgent(
        name="ServiceDesignPipeline",
        description="Service blueprint and pricing development",
        sub_agents=[
            create_strategic_agent(),
            create_operations_agent(),
            create_financial_agent(),
        ],
    )


# =============================================================================
# 10. ProductLaunchPipeline
# =============================================================================

def create_product_launch_pipeline() -> SequentialAgent:
    """Create ProductLaunchPipeline with fresh agent instances."""
    launch_parallel = ParallelAgent(
        name="ProductLaunchPrep",
        description="Concurrent launch preparation across marketing, sales, and content",
        sub_agents=[
            create_marketing_agent(),
            create_sales_agent(),
            create_content_agent(),
        ],
    )
    return SequentialAgent(
        name="ProductLaunchPipeline",
        description="Full product launch coordination with strategic planning and parallel execution",
        sub_agents=[create_strategic_agent(), launch_parallel],
    )


# =============================================================================
# 11. ProductIterationPipeline
# =============================================================================

def create_product_iteration_pipeline() -> LoopAgent:
    """Create ProductIterationPipeline with fresh agent instances."""
    iteration_cycle = SequentialAgent(
        name="ProductIterationCycle",
        description="Single iteration of product improvement cycle",
        sub_agents=[
            create_data_agent(),
            create_content_agent(),
            create_strategic_agent(),
        ],
    )
    return LoopAgent(
        name="ProductIterationPipeline",
        description="Continuous product improvement based on feedback loops",
        sub_agents=[iteration_cycle],
        max_iterations=5,
    )


# =============================================================================
# Exports
# =============================================================================

PRODUCT_WORKFLOW_FACTORIES = {
    "ProductIdeationPipeline": create_product_ideation_pipeline,
    "ProductValidationPipeline": create_product_validation_pipeline,
    "ServiceDesignPipeline": create_service_design_pipeline,
    "ProductLaunchPipeline": create_product_launch_pipeline,
    "ProductIterationPipeline": create_product_iteration_pipeline,
}

__all__ = [
    "create_product_ideation_pipeline",
    "create_product_validation_pipeline",
    "create_service_design_pipeline",
    "create_product_launch_pipeline",
    "create_product_iteration_pipeline",
    "PRODUCT_WORKFLOW_FACTORIES",
]
