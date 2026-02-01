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

"""Team & HR Workflows (Category 8).

This module implements 4 workflow agents for HR operations:
41. TeamTrainingPipeline - Training program creation
42. RecruitmentPipeline - End-to-end hiring workflow
43. OnboardingPipeline - New employee onboarding
44. PerformanceReviewPipeline - Employee performance analysis

Architecture Note: Uses factory functions to create fresh agent instances for each
workflow to avoid ADK's single-parent constraint.
"""

from google.adk.agents import SequentialAgent, LoopAgent

from app.agents.specialized_agents import (
    create_content_agent,
    create_data_agent,
    create_operations_agent,
    create_hr_agent,
)


# =============================================================================
# 41. TeamTrainingPipeline
# =============================================================================

def create_team_training_pipeline() -> SequentialAgent:
    """Create TeamTrainingPipeline with fresh agent instances."""
    return SequentialAgent(
        name="TeamTrainingPipeline",
        description="Training program creation from HR to content to operations",
        sub_agents=[
            create_hr_agent(),
            create_content_agent(),
            create_operations_agent(),
        ],
    )


# =============================================================================
# 42. RecruitmentPipeline
# =============================================================================

def create_recruitment_pipeline() -> SequentialAgent:
    """Create RecruitmentPipeline with fresh agent instances."""
    return SequentialAgent(
        name="RecruitmentPipeline",
        description="End-to-end hiring workflow with HR and data involvement",
        sub_agents=[
            create_hr_agent(),
            create_data_agent(),
        ],
    )


# =============================================================================
# 43. OnboardingPipeline
# =============================================================================

def create_onboarding_pipeline() -> SequentialAgent:
    """Create OnboardingPipeline with fresh agent instances."""
    return SequentialAgent(
        name="OnboardingPipeline",
        description="New employee onboarding through HR, content, and operations",
        sub_agents=[
            create_hr_agent(),
            create_content_agent(),
            create_operations_agent(),
        ],
    )


# =============================================================================
# 44. PerformanceReviewPipeline
# =============================================================================

def create_performance_review_pipeline() -> LoopAgent:
    """Create PerformanceReviewPipeline with fresh agent instances."""
    performance_review_cycle = SequentialAgent(
        name="PerformanceReviewCycle",
        description="Single iteration of performance analysis and feedback development",
        sub_agents=[
            create_hr_agent(),
            create_data_agent(),
        ],
    )
    return LoopAgent(
        name="PerformanceReviewPipeline",
        description="Iterative employee performance analysis with feedback refinement until comprehensive review complete",
        sub_agents=[performance_review_cycle],
        max_iterations=3,
    )


# =============================================================================
# Exports
# =============================================================================

HR_WORKFLOW_FACTORIES = {
    "TeamTrainingPipeline": create_team_training_pipeline,
    "RecruitmentPipeline": create_recruitment_pipeline,
    "OnboardingPipeline": create_onboarding_pipeline,
    "PerformanceReviewPipeline": create_performance_review_pipeline,
}

__all__ = [
    "create_team_training_pipeline",
    "create_recruitment_pipeline",
    "create_onboarding_pipeline",
    "create_performance_review_pipeline",
    "HR_WORKFLOW_FACTORIES",
]
