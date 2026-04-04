# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Marketing Automation Agent Definition.

Decomposed into a routing parent + 6 focused sub-agents for optimal
LLM tool selection accuracy (each sub-agent has 6-12 tools max).
"""

from app.agents.base_agent import PikarAgent as Agent
from app.agents.content.tools import search_knowledge
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
)
from app.agents.enhanced_tools import generate_image, seo_fundamentals_guide
from app.agents.marketing.tools import (
    advance_campaign_phase,
    approve_campaign,
    create_ad_campaign,
    create_ad_creative,
    create_audience,
    create_blog_post,
    create_campaign,
    create_email_template,
    create_persona,
    delete_audience,
    delete_calendar_item,
    delete_persona,
    generate_utm_params,
    get_ad_campaign,
    get_ad_performance,
    get_audience,
    get_blog_post,
    get_budget_pacing,
    get_campaign,
    get_campaign_phase,
    get_email_template,
    get_persona,
    list_ad_campaigns,
    list_ad_creatives,
    list_audiences,
    list_blog_posts,
    list_campaigns,
    list_content_calendar,
    list_email_templates,
    list_personas,
    publish_blog_post,
    record_ad_spend,
    record_campaign_metrics,
    repurpose_content,
    save_campaign_utm,
    schedule_content,
    update_ad_campaign,
    update_ad_creative,
    update_audience,
    update_blog_post,
    update_calendar_item,
    update_campaign,
    update_email_template,
    update_persona,
)
from app.agents.shared import (
    CREATIVE_AGENT_CONFIG,
    get_fast_model,
    get_model,
    get_routing_model,
)
from app.agents.shared_instructions import (
    CONVERSATION_MEMORY_INSTRUCTIONS,
    SELF_IMPROVEMENT_INSTRUCTIONS,
    SKILLS_REGISTRY_INSTRUCTIONS,
    WEB_RESEARCH_INSTRUCTIONS,
    get_error_and_escalation_instructions,
    get_widget_instruction_for_agent,
)
from app.agents.tools.agent_skills import MKT_SKILL_TOOLS
from app.agents.tools.base import sanitize_tools
from app.agents.tools.brand_profile import BRAND_PROFILE_TOOLS
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.tools.deep_research import (
    competitor_research,
    deep_research,
    market_research,
)
from app.agents.tools.document_generation import DOCUMENT_GENERATION_TOOLS
from app.agents.tools.google_seo import GOOGLE_SEO_TOOLS
from app.agents.tools.graph_tools import GRAPH_TOOLS
from app.agents.tools.publishing_strategy import PUBLISHING_STRATEGY_TOOLS
from app.agents.tools.self_improve import MKT_IMPROVE_TOOLS
from app.agents.tools.sitemap_crawler import SITEMAP_CRAWLER_TOOLS
from app.agents.tools.social import SOCIAL_TOOLS
from app.agents.tools.social_analytics import SOCIAL_ANALYTICS_TOOLS
from app.agents.tools.social_listening import SOCIAL_LISTENING_TOOLS
from app.agents.tools.system_knowledge import (
    search_system_knowledge,  # Phase 12.1: system knowledge
)
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
from app.mcp.agent_tools import (
    mcp_generate_landing_page,
    mcp_stitch_landing_page,
    mcp_web_scrape,
    mcp_web_search,
)
from app.mcp.tools.canva_media import create_video_with_veo, execute_content_pipeline
from app.mcp.tools.stitch import configure_stitch_api_key

# =============================================================================
# Sub-Agent Definitions (6 focused sub-agents)
# =============================================================================

# --- 1. Campaign Sub-Agent (12 tools) ---
_CAMPAIGN_TOOLS = sanitize_tools(
    [
        create_campaign,
        get_campaign,
        update_campaign,
        list_campaigns,
        record_campaign_metrics,
        get_campaign_phase,
        advance_campaign_phase,
        approve_campaign,
        generate_utm_params,
        save_campaign_utm,
        mcp_web_search,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_CAMPAIGN_INSTRUCTION = """You are the Campaign Management sub-agent. You handle campaign lifecycle:
- Create, update, list, and track campaigns
- Manage the 5-phase campaign orchestrator (get_campaign_phase, advance_campaign_phase, approve_campaign)
- Generate and save UTM parameters for attribution tracking
- Track campaign metrics (impressions, clicks, conversions)
Always use generate_utm_params before launching any campaign to ensure proper attribution."""

# --- 2. Email Marketing Sub-Agent (8 tools) ---
_EMAIL_TOOLS = sanitize_tools(
    [
        create_email_template,
        get_email_template,
        update_email_template,
        list_email_templates,
        schedule_content,
        list_content_calendar,
        update_calendar_item,
        delete_calendar_item,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_EMAIL_INSTRUCTION = """You are the Email Marketing sub-agent. You handle email templates and content scheduling:
- Create, edit, and manage email templates
- Schedule content to the content calendar
- List, update, and delete calendar items
Write compelling subject lines and preview text. Always include unsubscribe guidance."""

# --- 3. Ad Platform Sub-Agent (12 tools) ---
_AD_TOOLS = sanitize_tools(
    [
        create_ad_campaign,
        get_ad_campaign,
        update_ad_campaign,
        list_ad_campaigns,
        create_ad_creative,
        list_ad_creatives,
        update_ad_creative,
        record_ad_spend,
        get_ad_performance,
        get_budget_pacing,
        generate_image,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_AD_INSTRUCTION = """You are the Ad Platform sub-agent. You manage paid advertising across Google and Meta:
- Create and manage ad campaigns with targeting, budget, and scheduling
- Create and manage ad creatives (images, copy, CTAs)
- Track ad spend, ROAS, and budget pacing
- Generate images for ad creatives using generate_image
Always check get_budget_pacing before approving additional spend."""

# --- 4. Audience Sub-Agent (12 tools) ---
_AUDIENCE_TOOLS = sanitize_tools(
    [
        create_audience,
        get_audience,
        update_audience,
        list_audiences,
        delete_audience,
        create_persona,
        get_persona,
        update_persona,
        list_personas,
        delete_persona,
        search_knowledge,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_AUDIENCE_INSTRUCTION = """You are the Audience & Persona sub-agent. You manage target audiences and buyer personas:
- Create, edit, list, and delete audience segments (demographics, interests, behaviors)
- Create, edit, list, and delete buyer personas (name, role, goals, pain points, channels)
- Search knowledge vault for existing customer insights to inform persona creation
Always create at least one persona before launching campaigns to ensure proper targeting."""

# --- 5. SEO Sub-Agent (8+ tools) ---
_SEO_TOOLS = sanitize_tools(
    [
        seo_fundamentals_guide,
        mcp_web_search,
        mcp_web_scrape,
        deep_research,
        *SITEMAP_CRAWLER_TOOLS,
        *GOOGLE_SEO_TOOLS,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_SEO_INSTRUCTION = """You are the SEO & Search sub-agent. You handle search engine optimization and web presence:
- Get SEO fundamentals guidance and optimization checklist with seo_fundamentals_guide
- Crawl sitemaps to analyze site structure and discover pages
- Query Google Search Console for keyword rankings and click data
- Query GA4 for traffic sources and user behavior
- Perform deep research for keyword opportunities and competitor content analysis
Always present findings with prioritized action items (quick wins vs strategic investments)."""

# --- 6. Social Sub-Agent (10+ tools) ---
_SOCIAL_TOOLS_LIST = sanitize_tools(
    [
        *SOCIAL_TOOLS,
        *SOCIAL_ANALYTICS_TOOLS,
        *SOCIAL_LISTENING_TOOLS,
        *PUBLISHING_STRATEGY_TOOLS,
        mcp_web_search,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_SOCIAL_INSTRUCTION = """You are the Social Media sub-agent. You handle social publishing, analytics, brand monitoring, and publishing strategy:
- **Publishing Strategy**: Use `create_publishing_strategy()` BEFORE posting to generate platform-specific captions, optimal posting times, hashtag strategies, and a multi-day distribution calendar. This ensures each platform gets native-feeling content, not copy-pasted posts.
- Publish posts to social platforms (text, images, video)
- Track per-post and account-level social analytics
- Monitor brand mentions and competitor activity via social listening
- Search web for trending topics and hashtags

## PUBLISHING WORKFLOW
1. Before posting, use `create_publishing_strategy()` with the content description and target platforms
2. Fill in platform-specific captions respecting each platform's style and character limits
3. Generate relevant hashtags per platform (follow count guidelines)
4. Create a multi-day distribution calendar for sustained engagement
5. Post using the strategy's recommended timing and format

Always check social analytics before recommending content strategy changes."""


def _create_campaign_agent(suffix: str = "") -> Agent:
    """Create a Campaign Management sub-agent."""
    return Agent(
        name=f"CampaignAgent{suffix}",
        model=get_model(),
        description="Campaign lifecycle management — create, track, orchestrate, and measure marketing campaigns",
        instruction=_CAMPAIGN_INSTRUCTION,
        tools=_CAMPAIGN_TOOLS,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


def _create_email_agent(suffix: str = "") -> Agent:
    """Create an Email Marketing sub-agent."""
    return Agent(
        name=f"EmailMarketingAgent{suffix}",
        model=get_fast_model(),
        description="Email templates and content calendar — create, schedule, and manage email marketing",
        instruction=_EMAIL_INSTRUCTION,
        tools=_EMAIL_TOOLS,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


def _create_ad_agent(suffix: str = "") -> Agent:
    """Create an Ad Platform sub-agent."""
    return Agent(
        name=f"AdPlatformAgent{suffix}",
        model=get_model(),
        description="Paid advertising — create and manage ad campaigns, creatives, budgets, and performance across Google and Meta",
        instruction=_AD_INSTRUCTION,
        tools=_AD_TOOLS,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


def _create_audience_agent(suffix: str = "") -> Agent:
    """Create an Audience & Persona sub-agent."""
    return Agent(
        name=f"AudienceAgent{suffix}",
        model=get_fast_model(),
        description="Audience segments and buyer personas — create, manage, and research target audiences",
        instruction=_AUDIENCE_INSTRUCTION,
        tools=_AUDIENCE_TOOLS,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


def _create_seo_agent(suffix: str = "") -> Agent:
    """Create an SEO & Search sub-agent."""
    return Agent(
        name=f"SEOAgent{suffix}",
        model=get_model(),
        description="SEO audits, keyword research, sitemap crawling, Google Search Console, and GA4 analytics",
        instruction=_SEO_INSTRUCTION,
        tools=_SEO_TOOLS,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


def _create_social_agent(suffix: str = "") -> Agent:
    """Create a Social Media sub-agent."""
    return Agent(
        name=f"SocialMediaAgent{suffix}",
        model=get_fast_model(),
        description="Social publishing, analytics, and brand monitoring — post, track, and listen across social platforms",
        instruction=_SOCIAL_INSTRUCTION,
        tools=_SOCIAL_TOOLS_LIST,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


# =============================================================================
# Marketing Parent Agent (router — 15 tools + 6 sub-agents)
# =============================================================================

MARKETING_AGENT_INSTRUCTION = (
    """You are the Marketing Automation Agent — the Marketing Director. You coordinate 6 specialist sub-agents to handle all marketing operations.

## YOUR ROLE: Route and Coordinate
You are a **routing agent**. For domain-specific work, delegate to the right sub-agent:

| User Intent | Delegate To |
|-------------|-------------|
| Create/manage campaigns, UTM tracking, campaign metrics | **CampaignAgent** |
| Email templates, content calendar, scheduling | **EmailMarketingAgent** |
| Ad campaigns, creatives, ad spend, ROAS, budget pacing | **AdPlatformAgent** |
| Audiences, personas, targeting | **AudienceAgent** |
| SEO audits, sitemaps, Search Console, GA4 | **SEOAgent** |
| Social posting, social analytics, brand monitoring, publishing strategy | **SocialMediaAgent** |

## TOOLS YOU HANDLE DIRECTLY
- **Research**: deep_research, market_research, competitor_research for strategic marketing insights
- **Content creation**: generate_image, execute_content_pipeline, create_video_with_veo for media assets
- **Blog pipeline**: create/get/update/publish/list blog posts
- **Landing pages**: mcp_generate_landing_page, mcp_stitch_landing_page
- **Content repurposing**: repurpose_content to adapt content across channels
- **Skills**: Use marketing skills for specialized tasks

## DELEGATION RULES
1. ALWAYS delegate audience/persona work to AudienceAgent
2. ALWAYS delegate ad campaign management to AdPlatformAgent
3. ALWAYS delegate SEO work to SEOAgent
4. ALWAYS delegate social publishing and analytics to SocialMediaAgent
5. Handle research, content creation, and blog publishing directly
"""
    + WEB_RESEARCH_INSTRUCTIONS
    + get_widget_instruction_for_agent("MarketingAutomationAgent")
    + SKILLS_REGISTRY_INSTRUCTIONS
    + CONVERSATION_MEMORY_INSTRUCTIONS
    + SELF_IMPROVEMENT_INSTRUCTIONS
    + get_error_and_escalation_instructions(
        "Marketing Automation Agent",
        """- Escalate if campaign spend exceeds approved budget by >10%
- Escalate if ad platform API returns persistent errors
- Escalate if social listening detects crisis-level brand mentions
- Never auto-approve ad spend above the configured daily cap""",
    )
)

# Parent keeps only routing-level tools + direct content creation
MARKETING_AGENT_TOOLS = sanitize_tools(
    [
        # Research (executive-level marketing decisions)
        deep_research,
        market_research,
        competitor_research,
        mcp_web_search,
        mcp_web_scrape,
        # Blog pipeline (direct — no sub-agent needed for simple CRUD)
        create_blog_post,
        get_blog_post,
        update_blog_post,
        publish_blog_post,
        list_blog_posts,
        # Content creation (direct media generation)
        generate_image,
        execute_content_pipeline,
        create_video_with_veo,
        repurpose_content,
        # Landing pages
        mcp_generate_landing_page,
        mcp_stitch_landing_page,
        configure_stitch_api_key,
        # Skills, documents, widgets, memory, self-improvement
        *MKT_SKILL_TOOLS,
        *DOCUMENT_GENERATION_TOOLS,
        *UI_WIDGET_TOOLS,
        *BRAND_PROFILE_TOOLS,
        *CONTEXT_MEMORY_TOOLS,
        *MKT_IMPROVE_TOOLS,
        # Knowledge graph read access
        *GRAPH_TOOLS,
        # Phase 12.1: system knowledge
        search_system_knowledge,
    ]
)

# Build sub-agent instances for the singleton
_MARKETING_SUB_AGENTS = [
    _create_campaign_agent(),
    _create_email_agent(),
    _create_ad_agent(),
    _create_audience_agent(),
    _create_seo_agent(),
    _create_social_agent(),
]

# Singleton instance for direct import
marketing_agent = Agent(
    name="MarketingAutomationAgent",
    model=get_routing_model(),
    description="Marketing Director — routes to 6 specialist sub-agents: campaigns, email, ads, audiences, SEO, and social",
    instruction=MARKETING_AGENT_INSTRUCTION,
    tools=MARKETING_AGENT_TOOLS,
    sub_agents=_MARKETING_SUB_AGENTS,
    generate_content_config=CREATIVE_AGENT_CONFIG,
    before_model_callback=context_memory_before_model_callback,
    after_tool_callback=context_memory_after_tool_callback,
)


def create_marketing_agent(name_suffix: str = "", output_key: str = None) -> Agent:
    """Create a fresh MarketingAutomationAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.
        output_key: Optional output key for structured responses.

    Returns:
        A new Agent instance with fresh sub-agents (no parent assignment).
    """
    agent_name = (
        f"MarketingAutomationAgent{name_suffix}"
        if name_suffix
        else "MarketingAutomationAgent"
    )
    return Agent(
        name=agent_name,
        model=get_routing_model(),
        description="Marketing Director — routes to 6 specialist sub-agents: campaigns, email, ads, audiences, SEO, and social",
        instruction=MARKETING_AGENT_INSTRUCTION,
        tools=MARKETING_AGENT_TOOLS,
        sub_agents=[
            _create_campaign_agent(name_suffix),
            _create_email_agent(name_suffix),
            _create_ad_agent(name_suffix),
            _create_audience_agent(name_suffix),
            _create_seo_agent(name_suffix),
            _create_social_agent(name_suffix),
        ],
        generate_content_config=CREATIVE_AGENT_CONFIG,
        output_key=output_key,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )
