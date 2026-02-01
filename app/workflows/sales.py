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

"""Lead Generation & Sales Workflows (Category 3).

This module implements 7 workflow agents for sales lifecycle:
12. LeadGenerationPipeline - Generate and qualify leads
13. LeadScoringPipeline - Score and prioritize leads
14. LeadNurturingPipeline - Automated lead nurture sequence
15. SalesFunnelCreationPipeline - Build complete sales funnel
16. DealQualificationPipeline - Smart deal routing
17. OutreachSequencePipeline - Multi-touch outreach campaign
18. CustomerJourneyPipeline - Full customer lifecycle mapping

Architecture Note: Uses factory functions to create fresh agent instances for each
workflow to avoid ADK's single-parent constraint.
"""

from google.adk.agents import SequentialAgent, LoopAgent

from app.agents.specialized_agents import (
    create_strategic_agent,
    create_content_agent,
    create_data_agent,
    create_financial_agent,
    create_marketing_agent,
    create_sales_agent,
    create_customer_support_agent,
)


# =============================================================================
# 12. LeadGenerationPipeline
# =============================================================================

def create_lead_generation_pipeline() -> SequentialAgent:
    """Create LeadGenerationPipeline with fresh agent instances."""
    return SequentialAgent(
        name="LeadGenerationPipeline",
        description="Generate and qualify leads through marketing, content, and data analysis",
        sub_agents=[
            create_marketing_agent(),
            create_content_agent(),
            create_data_agent(),
        ],
    )


# =============================================================================
# 13. LeadScoringPipeline
# =============================================================================

def create_lead_scoring_pipeline() -> SequentialAgent:
    """Create LeadScoringPipeline with fresh agent instances."""
    return SequentialAgent(
        name="LeadScoringPipeline",
        description="Score and prioritize leads based on data, sales, and financial analysis",
        sub_agents=[
            create_data_agent(),
            create_sales_agent(),
            create_financial_agent(),
        ],
    )


# =============================================================================
# 14. LeadNurturingPipeline
# =============================================================================

def create_lead_nurturing_pipeline() -> LoopAgent:
    """Create LeadNurturingPipeline with fresh agent instances."""
    nurture_cycle = SequentialAgent(
        name="NurtureCycle",
        description="Single iteration of lead nurture sequence",
        sub_agents=[
            create_content_agent(),
            create_sales_agent(),
            create_data_agent(),
        ],
    )
    return LoopAgent(
        name="LeadNurturingPipeline",
        description="Automated lead nurture sequence that loops until conversion",
        sub_agents=[nurture_cycle],
        max_iterations=10,
    )


# =============================================================================
# 15. SalesFunnelCreationPipeline
# =============================================================================

def create_sales_funnel_creation_pipeline() -> SequentialAgent:
    """Create SalesFunnelCreationPipeline with fresh agent instances."""
    return SequentialAgent(
        name="SalesFunnelCreationPipeline",
        description="Build complete sales funnel from strategy to execution",
        sub_agents=[
            create_strategic_agent(),
            create_marketing_agent(),
            create_sales_agent(),
            create_content_agent(),
        ],
    )


# =============================================================================
# 16. DealQualificationPipeline
# =============================================================================

def create_deal_qualification_pipeline() -> SequentialAgent:
    """Create DealQualificationPipeline with fresh agent instances."""
    return SequentialAgent(
        name="DealQualificationPipeline",
        description="Smart deal routing through sales qualification and financial analysis",
        sub_agents=[
            create_sales_agent(),
            create_financial_agent(),
        ],
    )


# =============================================================================
# 17. OutreachSequencePipeline
# =============================================================================

def create_outreach_sequence_pipeline() -> SequentialAgent:
    """Create OutreachSequencePipeline with fresh agent instances."""
    return SequentialAgent(
        name="OutreachSequencePipeline",
        description="Multi-touch outreach campaign through sales, content, and marketing",
        sub_agents=[
            create_sales_agent(),
            create_content_agent(),
            create_marketing_agent(),
        ],
    )


# =============================================================================
# 18. CustomerJourneyPipeline
# =============================================================================

def create_customer_journey_pipeline() -> SequentialAgent:
    """Create CustomerJourneyPipeline with fresh agent instances."""
    return SequentialAgent(
        name="CustomerJourneyPipeline",
        description="Full customer lifecycle mapping from data to support",
        sub_agents=[
            create_data_agent(),
            create_marketing_agent(),
            create_sales_agent(),
            create_customer_support_agent(),
        ],
    )


# =============================================================================
# Exports
# =============================================================================

SALES_WORKFLOW_FACTORIES = {
    "LeadGenerationPipeline": create_lead_generation_pipeline,
    "LeadScoringPipeline": create_lead_scoring_pipeline,
    "LeadNurturingPipeline": create_lead_nurturing_pipeline,
    "SalesFunnelCreationPipeline": create_sales_funnel_creation_pipeline,
    "DealQualificationPipeline": create_deal_qualification_pipeline,
    "OutreachSequencePipeline": create_outreach_sequence_pipeline,
    "CustomerJourneyPipeline": create_customer_journey_pipeline,
}

__all__ = [
    "create_lead_generation_pipeline",
    "create_lead_scoring_pipeline",
    "create_lead_nurturing_pipeline",
    "create_sales_funnel_creation_pipeline",
    "create_deal_qualification_pipeline",
    "create_outreach_sequence_pipeline",
    "create_customer_journey_pipeline",
    "SALES_WORKFLOW_FACTORIES",
]
