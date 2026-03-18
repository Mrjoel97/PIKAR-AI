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
workflow to avoid ADK's single-parent constraint. Each sub-agent uses output_key
so downstream agents can read upstream results from session.state.
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
    """Create ContentCampaignPipeline with data flow between stages.

    Flow: Strategy (market positioning, audience, channels)
        → Content (produce assets based on strategy)
        → Marketing (schedule, publish, track via campaign tools)

    Each agent writes its output to session.state via output_key so the
    next agent has full context from the previous stage.
    """
    return SequentialAgent(
        name="ContentCampaignPipeline",
        description="End-to-end content campaign from strategy to execution",
        sub_agents=[
            create_strategic_agent(
                name_suffix="_CampaignStrategy",
                output_key="campaign_strategy",
            ),
            create_content_agent(
                name_suffix="_CampaignContent",
                output_key="campaign_content",
            ),
            create_marketing_agent(
                name_suffix="_CampaignExecution",
                output_key="campaign_execution",
            ),
        ],
    )


# =============================================================================
# 20. EmailSequencePipeline
# =============================================================================

def create_email_sequence_pipeline() -> SequentialAgent:
    """Create EmailSequencePipeline with data flow between stages.

    Flow: Marketing (sequence strategy, audience segments, triggers)
        → Content (write email copy per sequence step)
        → Data (analyze deliverability benchmarks, suggest optimizations)
    """
    return SequentialAgent(
        name="EmailSequencePipeline",
        description="Automated email drip campaign creation and analysis",
        sub_agents=[
            create_marketing_agent(
                name_suffix="_EmailStrategy",
                output_key="email_strategy",
            ),
            create_content_agent(
                name_suffix="_EmailContent",
                output_key="email_content",
            ),
            create_data_agent(
                name_suffix="_EmailAnalysis",
                output_key="email_analysis",
            ),
        ],
    )


# =============================================================================
# 21. SocialMediaPipeline
# =============================================================================

def create_social_media_pipeline() -> SequentialAgent:
    """Create SocialMediaPipeline with data flow between stages.

    Flow: Content (create posts, visuals, video for each platform)
        → Marketing (schedule across platforms, set UTMs, publish)
        → Data (engagement forecasting, audience overlap analysis)
    """
    return SequentialAgent(
        name="SocialMediaPipeline",
        description="Social content creation and scheduling with analytics",
        sub_agents=[
            create_content_agent(
                name_suffix="_SocialContent",
                output_key="social_content",
            ),
            create_marketing_agent(
                name_suffix="_SocialScheduling",
                output_key="social_schedule",
            ),
            create_data_agent(
                name_suffix="_SocialAnalytics",
                output_key="social_analytics",
            ),
        ],
    )


# =============================================================================
# 22. NewsletterPipeline
# =============================================================================

def create_newsletter_pipeline() -> LoopAgent:
    """Create NewsletterPipeline with data flow and iterative refinement.

    Each cycle: Content (draft newsletter sections)
        → Marketing (review against brand voice, audience fit, CTA strength)
    Loop refines until quality standards met (max 3 iterations).
    """
    newsletter_cycle = SequentialAgent(
        name="NewsletterCreationCycle",
        description="Single iteration of newsletter content creation and review",
        sub_agents=[
            create_content_agent(
                name_suffix="_NewsletterDraft",
                output_key="newsletter_draft",
            ),
            create_marketing_agent(
                name_suffix="_NewsletterReview",
                output_key="newsletter_review",
            ),
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
    """Create BlogContentPipeline with data flow and iterative SEO refinement.

    Each cycle: Strategy (keyword research, topic authority mapping)
        → Content (write/refine article with SEO structure)
        → Data (score readability, keyword density, internal link gaps)
    Loop refines until SEO quality met (max 3 iterations).
    """
    blog_cycle = SequentialAgent(
        name="BlogContentCycle",
        description="Single iteration of blog content creation and SEO analysis",
        sub_agents=[
            create_strategic_agent(
                name_suffix="_BlogStrategy",
                output_key="blog_strategy",
            ),
            create_content_agent(
                name_suffix="_BlogContent",
                output_key="blog_content",
            ),
            create_data_agent(
                name_suffix="_BlogSEO",
                output_key="blog_seo_analysis",
            ),
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
    """Create BrandVoicePipeline with data flow and iterative alignment.

    Each cycle: Content (draft brand voice samples, tone examples)
        → Marketing (audit consistency, channel-specific adaptation)
        → Strategy (align with business positioning, competitive differentiation)
    Loop refines until guidelines finalized (max 3 iterations).
    """
    brand_cycle = SequentialAgent(
        name="BrandVoiceCycle",
        description="Single iteration of brand voice development and strategic alignment",
        sub_agents=[
            create_content_agent(
                name_suffix="_BrandDraft",
                output_key="brand_voice_draft",
            ),
            create_marketing_agent(
                name_suffix="_BrandAudit",
                output_key="brand_voice_audit",
            ),
            create_strategic_agent(
                name_suffix="_BrandStrategy",
                output_key="brand_voice_strategy",
            ),
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
    """Create CampaignAnalyticsPipeline with data flow.

    Flow: Data (pull metrics, compute attribution, identify trends)
        → Marketing (interpret results, recommend optimizations, next actions)
    """
    return SequentialAgent(
        name="CampaignAnalyticsPipeline",
        description="Campaign performance analysis and reporting",
        sub_agents=[
            create_data_agent(
                name_suffix="_CampaignMetrics",
                output_key="campaign_metrics",
            ),
            create_marketing_agent(
                name_suffix="_CampaignInsights",
                output_key="campaign_insights",
            ),
        ],
    )


# =============================================================================
# 26. ABTestingPipeline
# =============================================================================

def create_ab_testing_pipeline() -> LoopAgent:
    """Create ABTestingPipeline with data flow and iterative optimization.

    Each cycle: Marketing (define variants, hypotheses, success criteria)
        → Data (analyze results, statistical significance, segment performance)
        → Content (generate next variant based on winning elements)
    Loop refines until winner found (max 5 iterations).
    """
    ab_test_cycle = SequentialAgent(
        name="ABTestCycle",
        description="Single A/B test iteration with analysis",
        sub_agents=[
            create_marketing_agent(
                name_suffix="_ABTestDesign",
                output_key="ab_test_design",
            ),
            create_data_agent(
                name_suffix="_ABTestAnalysis",
                output_key="ab_test_results",
            ),
            create_content_agent(
                name_suffix="_ABTestVariant",
                output_key="ab_test_variant",
            ),
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
    """Create LandingPageCreationPipeline with data flow.

    Flow: Strategy (audience research, competitive positioning)
        → Data (conversion benchmarks, heat map patterns)
        → Marketing (page structure, CTA placement, form strategy)
        → Content (copy, visuals, landing page generation)
    """
    return SequentialAgent(
        name="LandingPageCreationPipeline",
        description="Landing page creation with research, design, and copywriting",
        sub_agents=[
            create_strategic_agent(
                name_suffix="_LPResearch",
                output_key="lp_research",
            ),
            create_data_agent(
                name_suffix="_LPBenchmarks",
                output_key="lp_benchmarks",
            ),
            create_marketing_agent(
                name_suffix="_LPStrategy",
                output_key="lp_strategy",
            ),
            create_content_agent(
                name_suffix="_LPContent",
                output_key="lp_content",
            ),
        ],
    )


# =============================================================================
# 28. FormCreationPipeline
# =============================================================================

def create_form_creation_pipeline() -> LoopAgent:
    """Create FormCreationPipeline with data flow and iterative CRO.

    Each cycle: Marketing (form design, field strategy, UX best practices)
        → Data (conversion rate analysis, drop-off identification, CRO scoring)
    Loop refines until conversion targets met (max 3 iterations).
    """
    form_optimization_cycle = SequentialAgent(
        name="FormOptimizationCycle",
        description="Single iteration of form design and conversion rate optimization",
        sub_agents=[
            create_marketing_agent(
                name_suffix="_FormDesign",
                output_key="form_design",
            ),
            create_data_agent(
                name_suffix="_FormCRO",
                output_key="form_cro_analysis",
            ),
        ],
    )
    return LoopAgent(
        name="FormCreationPipeline",
        description="Iterative form creation with CRO optimization until conversion targets met",
        sub_agents=[form_optimization_cycle],
        max_iterations=3,
    )


# =============================================================================
# 29. BlogPublicationPipeline
# =============================================================================

def create_blog_publication_pipeline() -> LoopAgent:
    """Create BlogPublicationPipeline for end-to-end blog creation and publishing.

    Each cycle: Marketing (keyword research, topic authority, SEO strategy)
        → Content (draft blog post with create_blog_post, apply SEO metadata)
        → Data (score readability, keyword density, competitor gap analysis)
        → Marketing (review, optimize, schedule on content calendar or publish)
    Loop refines until publication quality met (max 3 iterations).
    """
    blog_pub_cycle = SequentialAgent(
        name="BlogPublicationCycle",
        description="Single iteration of blog drafting, SEO scoring, and publishing review",
        sub_agents=[
            create_marketing_agent(
                name_suffix="_BlogSEOStrategy",
                output_key="blog_seo_strategy",
            ),
            create_content_agent(
                name_suffix="_BlogDraft",
                output_key="blog_draft",
            ),
            create_data_agent(
                name_suffix="_BlogSEOScore",
                output_key="blog_seo_score",
            ),
            create_marketing_agent(
                name_suffix="_BlogPublishReview",
                output_key="blog_publish_review",
            ),
        ],
    )
    return LoopAgent(
        name="BlogPublicationPipeline",
        description="End-to-end blog creation: SEO research → draft → score → publish",
        sub_agents=[blog_pub_cycle],
        max_iterations=3,
    )


# =============================================================================
# 30. ContentRepurposingPipeline
# =============================================================================

def create_content_repurposing_pipeline() -> SequentialAgent:
    """Create ContentRepurposingPipeline for multi-format content distribution.

    Flow: Content (analyze source content, generate repurposing briefs via repurpose_content)
        → Marketing (adapt variants for each platform, schedule on content calendar)
        → Data (forecast engagement per format, recommend optimal posting times)
    """
    return SequentialAgent(
        name="ContentRepurposingPipeline",
        description="Repurpose source content into multi-platform variants with scheduling",
        sub_agents=[
            create_content_agent(
                name_suffix="_RepurposeSource",
                output_key="repurposed_variants",
            ),
            create_marketing_agent(
                name_suffix="_RepurposeSchedule",
                output_key="repurpose_schedule",
            ),
            create_data_agent(
                name_suffix="_RepurposeAnalytics",
                output_key="repurpose_analytics",
            ),
        ],
    )


# =============================================================================
# 31. EmailTemplatePipeline
# =============================================================================

def create_email_template_pipeline() -> LoopAgent:
    """Create EmailTemplatePipeline for email template creation with A/B testing.

    Each cycle: Marketing (define audience segment, email goals, template category)
        → Content (write subject lines, HTML body, plain text, A/B variants)
        → Data (analyze subject line effectiveness, readability, CTA placement)
    Loop refines until template quality targets met (max 3 iterations).
    """
    email_tpl_cycle = SequentialAgent(
        name="EmailTemplateCycle",
        description="Single iteration of email template creation and quality scoring",
        sub_agents=[
            create_marketing_agent(
                name_suffix="_EmailTemplateStrategy",
                output_key="email_template_strategy",
            ),
            create_content_agent(
                name_suffix="_EmailTemplateContent",
                output_key="email_template_content",
            ),
            create_data_agent(
                name_suffix="_EmailTemplateAnalysis",
                output_key="email_template_analysis",
            ),
        ],
    )
    return LoopAgent(
        name="EmailTemplatePipeline",
        description="Email template creation with A/B variants and iterative quality refinement",
        sub_agents=[email_tpl_cycle],
        max_iterations=3,
    )


# =============================================================================
# 32. CampaignOrchestratorPipeline
# =============================================================================

def create_campaign_orchestrator_pipeline() -> SequentialAgent:
    """Create CampaignOrchestratorPipeline — 5-phase start-to-finish campaign.

    Flow: Strategy (define audience, persona, positioning, channels, budget)
        → Marketing (create campaign, set UTM config, build content calendar)
        → Content (create blog posts, email templates, social copy, visuals)
        → Marketing (schedule everything, advance to review, request approval)
        → Data (set up tracking, forecast performance, define success metrics)

    This is the full campaign launch pipeline. After completion, the campaign
    is in 'review' phase awaiting approval before going active.
    """
    return SequentialAgent(
        name="CampaignOrchestratorPipeline",
        description="Full campaign orchestration: strategy → content → scheduling → review",
        sub_agents=[
            create_strategic_agent(
                name_suffix="_CampaignOrchStrategy",
                output_key="orch_strategy",
            ),
            create_marketing_agent(
                name_suffix="_CampaignOrchSetup",
                output_key="orch_campaign_setup",
            ),
            create_content_agent(
                name_suffix="_CampaignOrchContent",
                output_key="orch_content",
            ),
            create_marketing_agent(
                name_suffix="_CampaignOrchSchedule",
                output_key="orch_schedule",
            ),
            create_data_agent(
                name_suffix="_CampaignOrchTracking",
                output_key="orch_tracking",
            ),
        ],
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
    "BlogPublicationPipeline": create_blog_publication_pipeline,
    "ContentRepurposingPipeline": create_content_repurposing_pipeline,
    "EmailTemplatePipeline": create_email_template_pipeline,
    "CampaignOrchestratorPipeline": create_campaign_orchestrator_pipeline,
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
    "create_blog_publication_pipeline",
    "create_content_repurposing_pipeline",
    "create_email_template_pipeline",
    "create_campaign_orchestrator_pipeline",
    "MARKETING_WORKFLOW_FACTORIES",
]
