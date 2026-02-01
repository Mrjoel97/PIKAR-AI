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

"""Documentation & Reporting Workflows (Category 9).

This module implements 5 workflow agents for documentation:
45. BusinessDocumentationPipeline - Business process documentation
46. ProjectDocumentationPipeline - Project documentation
47. ReportCreationPipeline - Custom report generation
48. BoardPresentationPipeline - Board meeting preparation
49. WeeklyBriefingPipeline - Automated weekly executive brief

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
    create_compliance_agent,
)


# =============================================================================
# 45. BusinessDocumentationPipeline
# =============================================================================

def create_business_documentation_pipeline() -> SequentialAgent:
    """Create BusinessDocumentationPipeline with fresh agent instances."""
    return SequentialAgent(
        name="BusinessDocumentationPipeline",
        description="Business process documentation with compliance review",
        sub_agents=[
            create_strategic_agent(),
            create_content_agent(),
            create_compliance_agent(),
        ],
    )


# =============================================================================
# 46. ProjectDocumentationPipeline
# =============================================================================

def create_project_documentation_pipeline() -> SequentialAgent:
    """Create ProjectDocumentationPipeline with fresh agent instances."""
    return SequentialAgent(
        name="ProjectDocumentationPipeline",
        description="Project documentation from operations to content to data",
        sub_agents=[
            create_operations_agent(),
            create_content_agent(),
            create_data_agent(),
        ],
    )


# =============================================================================
# 47. ReportCreationPipeline
# =============================================================================

def create_report_creation_pipeline() -> SequentialAgent:
    """Create ReportCreationPipeline with fresh agent instances."""
    report_data_parallel = ParallelAgent(
        name="ReportDataGathering",
        description="Parallel data gathering from data and financial sources",
        sub_agents=[
            create_data_agent(),
            create_financial_agent(),
        ],
    )
    return SequentialAgent(
        name="ReportCreationPipeline",
        description="Custom report generation with parallel data gathering",
        sub_agents=[report_data_parallel, create_content_agent()],
    )


# =============================================================================
# 48. BoardPresentationPipeline
# =============================================================================

def create_board_presentation_pipeline() -> SequentialAgent:
    """Create BoardPresentationPipeline with fresh agent instances."""
    board_parallel = ParallelAgent(
        name="BoardPresentationGathering",
        description="Parallel board presentation content from data, financial, and strategic",
        sub_agents=[
            create_data_agent(),
            create_financial_agent(),
            create_strategic_agent(),
        ],
    )
    return SequentialAgent(
        name="BoardPresentationPipeline",
        description="Board meeting preparation with parallel analysis",
        sub_agents=[board_parallel],
    )


# =============================================================================
# 49. WeeklyBriefingPipeline
# =============================================================================

def create_weekly_briefing_pipeline() -> SequentialAgent:
    """Create WeeklyBriefingPipeline with fresh agent instances."""
    return SequentialAgent(
        name="WeeklyBriefingPipeline",
        description="Automated weekly executive brief generation",
        sub_agents=[
            create_data_agent(),
            create_strategic_agent(),
        ],
    )


# =============================================================================
# Exports
# =============================================================================

DOCUMENTATION_WORKFLOW_FACTORIES = {
    "BusinessDocumentationPipeline": create_business_documentation_pipeline,
    "ProjectDocumentationPipeline": create_project_documentation_pipeline,
    "ReportCreationPipeline": create_report_creation_pipeline,
    "BoardPresentationPipeline": create_board_presentation_pipeline,
    "WeeklyBriefingPipeline": create_weekly_briefing_pipeline,
}

__all__ = [
    "create_business_documentation_pipeline",
    "create_project_documentation_pipeline",
    "create_report_creation_pipeline",
    "create_board_presentation_pipeline",
    "create_weekly_briefing_pipeline",
    "DOCUMENTATION_WORKFLOW_FACTORIES",
]
