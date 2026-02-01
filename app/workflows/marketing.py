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

"""Marketing & Content Workflows (Category 4).

This module implements 10 workflow agents for marketing operations:
19. ContentCampaignPipeline - End-to-end content campaign
20. EmailSequencePipeline - Automated email drip campaigns
21. SocialMediaPipeline - Social content creation & scheduling
22. NewsletterPipeline - Weekly/monthly newsletter creation
23. BlogContentPipeline - SEO-optimized blog creation
24. BrandVoicePipeline - Establish and refine brand voice
25. CampaignAnalyticsPipeline - Campaign performance analysis
26. ABTestingPipeline - Iterative A/B optimization
27. LandingPageCreationPipeline - Landing page creation with research
28. FormCreationPipeline - Iterative form creation with CRO

Architecture Note: Uses factory functions to create fresh agent instances for each
workflow to avoid ADK's single-parent constraint.
"""

from google.adk.agents import SequentialAgent, LoopAgent

from app.agents.specialized_agents import (
    create_strategic_agent,
    create_content_agent,
    create_data_agent,
    create_marketing_agent,
)


# =============================================================================
# 19. ContentCampaignPipeline
# =============================================================================

def create_content_campaign_pipeline() -> SequentialAgent:
    """Create ContentCampaignPipeline with fresh agent instances."""
    return SequentialAgent(
        name="ContentCampaignPipeline",
        description="End-to-end content campaign from strategy to execution",
        sub_agents=[
            create_strategic_agent(),
            create_content_agent(),
            create_marketing_agent(),
        ],
    )


# =============================================================================
# 20. EmailSequencePipeline
# =============================================================================

def create_email_sequence_pipeline() -> SequentialAgent:
    """Create EmailSequencePipeline with fresh agent instances."""
    return SequentialAgent(
        name="EmailSequencePipeline",
        description="Automated email drip campaign creation and analysis",
        sub_agents=[
            create_marketing_agent(),
            create_content_agent(),
            create_data_agent(),
        ],
    )


# =============================================================================
# 21. SocialMediaPipeline
# =============================================================================

def create_social_media_pipeline() -> SequentialAgent:
    """Create SocialMediaPipeline with fresh agent instances."""
    return SequentialAgent(
        name="SocialMediaPipeline",
        description="Social content creation and scheduling with analytics",
        sub_agents=[
            create_content_agent(),
            create_marketing_agent(),
            create_data_agent(),
        ],
    )


# =============================================================================
# 22. NewsletterPipeline
# =============================================================================

def create_newsletter_pipeline() -> LoopAgent:
    """Create NewsletterPipeline with fresh agent instances."""
    newsletter_cycle = SequentialAgent(
        name="NewsletterCreationCycle",
        description="Single iteration of newsletter content creation and review",
        sub_agents=[
            create_content_agent(),
            create_marketing_agent(),
        ],
    )
    return LoopAgent(
        name="NewsletterPipeline",
        description="Iterative newsletter creation with refinement until quality standards met",
        sub_agents=[newsletter_cycle],
        max_iterations=3,
    )


# =============================================================================
# 23. BlogContentPipeline
# =============================================================================

def create_blog_content_pipeline() -> LoopAgent:
    """Create BlogContentPipeline with fresh agent instances."""
    blog_cycle = SequentialAgent(
        name="BlogContentCycle",
        description="Single iteration of blog content creation and SEO analysis",
        sub_agents=[
            create_strategic_agent(),
            create_content_agent(),
            create_data_agent(),
        ],
    )
    return LoopAgent(
        name="BlogContentPipeline",
        description="Iterative SEO-optimized blog content creation with refinement",
        sub_agents=[blog_cycle],
        max_iterations=3,
    )


# =============================================================================
# 24. BrandVoicePipeline
# =============================================================================

def create_brand_voice_pipeline() -> LoopAgent:
    """Create BrandVoicePipeline with fresh agent instances."""
    brand_cycle = SequentialAgent(
        name="BrandVoiceCycle",
        description="Single iteration of brand voice development and strategic alignment",
        sub_agents=[
            create_content_agent(),
            create_marketing_agent(),
            create_strategic_agent(),
        ],
    )
    return LoopAgent(
        name="BrandVoicePipeline",
        description="Iterative brand voice establishment and refinement until guidelines finalized",
        sub_agents=[brand_cycle],
        max_iterations=3,
    )


# =============================================================================
# 25. CampaignAnalyticsPipeline
# =============================================================================

def create_campaign_analytics_pipeline() -> SequentialAgent:
    """Create CampaignAnalyticsPipeline with fresh agent instances."""
    return SequentialAgent(
        name="CampaignAnalyticsPipeline",
        description="Campaign performance analysis and reporting",
        sub_agents=[
            create_data_agent(),
            create_marketing_agent(),
        ],
    )


# =============================================================================
# 26. ABTestingPipeline
# =============================================================================

def create_ab_testing_pipeline() -> LoopAgent:
    """Create ABTestingPipeline with fresh agent instances."""
    ab_test_cycle = SequentialAgent(
        name="ABTestCycle",
        description="Single A/B test iteration with analysis",
        sub_agents=[
            create_marketing_agent(),
            create_data_agent(),
            create_content_agent(),
        ],
    )
    return LoopAgent(
        name="ABTestingPipeline",
        description="Iterative A/B testing optimization until winner found",
        sub_agents=[ab_test_cycle],
        max_iterations=5,
    )


# =============================================================================
# 27. LandingPageCreationPipeline
# =============================================================================

def create_landing_page_creation_pipeline() -> SequentialAgent:
    """Create LandingPageCreationPipeline with fresh agent instances."""
    landing_page_research = SequentialAgent(
        name="LandingPageResearch",
        description="Research target audience, competitors, and strategic positioning",
        sub_agents=[
            create_strategic_agent(),
            create_data_agent(),
        ],
    )
    return SequentialAgent(
        name="LandingPageCreationPipeline",
        description="Landing page creation with research, design, and copywriting",
        sub_agents=[landing_page_research, create_marketing_agent(), create_content_agent()],
    )


# =============================================================================
# 28. FormCreationPipeline
# =============================================================================

def create_form_creation_pipeline() -> LoopAgent:
    """Create FormCreationPipeline with fresh agent instances."""
    form_optimization_cycle = SequentialAgent(
        name="FormOptimizationCycle",
        description="Single iteration of form design and conversion rate optimization",
        sub_agents=[
            create_marketing_agent(),
            create_data_agent(),
        ],
    )
    return LoopAgent(
        name="FormCreationPipeline",
        description="Iterative form creation with CRO optimization until conversion targets met",
        sub_agents=[form_optimization_cycle],
        max_iterations=3,
    )


# =============================================================================
# Exports
# =============================================================================

MARKETING_WORKFLOW_FACTORIES = {
    "ContentCampaignPipeline": create_content_campaign_pipeline,
    "EmailSequencePipeline": create_email_sequence_pipeline,
    "SocialMediaPipeline": create_social_media_pipeline,
    "NewsletterPipeline": create_newsletter_pipeline,
    "BlogContentPipeline": create_blog_content_pipeline,
    "BrandVoicePipeline": create_brand_voice_pipeline,
    "CampaignAnalyticsPipeline": create_campaign_analytics_pipeline,
    "ABTestingPipeline": create_ab_testing_pipeline,
    "LandingPageCreationPipeline": create_landing_page_creation_pipeline,
    "FormCreationPipeline": create_form_creation_pipeline,
}

__all__ = [
    "create_content_campaign_pipeline",
    "create_email_sequence_pipeline",
    "create_social_media_pipeline",
    "create_newsletter_pipeline",
    "create_blog_content_pipeline",
    "create_brand_voice_pipeline",
    "create_campaign_analytics_pipeline",
    "create_ab_testing_pipeline",
    "create_landing_page_creation_pipeline",
    "create_form_creation_pipeline",
    "MARKETING_WORKFLOW_FACTORIES",
]
