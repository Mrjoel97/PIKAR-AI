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
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
)
from app.agents.enhanced_tools import generate_image, seo_fundamentals_guide
from app.agents.marketing.tools import (
    advance_campaign_phase,
    approve_campaign,
    create_audience,
    create_campaign,
    create_email_template,
    create_persona,
    delete_audience,
    delete_calendar_item,
    delete_persona,
    generate_utm_params,
    get_audience,
    get_campaign,
    get_campaign_phase,
    get_email_template,
    get_persona,
    list_audiences,
    list_campaigns,
    list_content_calendar,
    list_email_templates,
    list_personas,
    record_campaign_metrics,
    save_campaign_utm,
    schedule_content,
    update_audience,
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
from app.agents.tools.ad_copy_tools import AD_COPY_TOOLS
from app.agents.tools.ad_platform_tools import (
    AD_PLATFORM_TOOLS,
    connect_google_ads_status,
    connect_meta_ads_status,
)
from app.agents.tools.agent_skills import MKT_SKILL_TOOLS
from app.agents.tools.attribution_tools import ATTRIBUTION_TOOLS
from app.agents.tools.base import sanitize_tools
from app.agents.tools.brand_profile import BRAND_PROFILE_TOOLS
from app.agents.tools.campaign_performance_tools import CAMPAIGN_PERFORMANCE_TOOLS
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.tools.deep_research import (
    competitor_research,
    deep_research,
    market_research,
)
from app.agents.tools.document_gen import DOCUMENT_GEN_TOOLS
from app.agents.tools.document_generation import DOCUMENT_GENERATION_TOOLS
from app.agents.tools.email_ab_tools import EMAIL_AB_TOOLS
from app.agents.tools.email_sequence_tools import EMAIL_SEQUENCE_TOOLS
from app.agents.tools.google_seo import GOOGLE_SEO_TOOLS
from app.agents.tools.graph_tools import GRAPH_TOOLS
from app.agents.tools.knowledge import search_knowledge
from app.agents.tools.publishing_strategy import PUBLISHING_STRATEGY_TOOLS
from app.agents.tools.self_improve import MKT_IMPROVE_TOOLS
from app.agents.tools.shopify_tools import SHOPIFY_ANALYTICS_TOOLS
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
from app.mcp.tools.stitch import configure_stitch_api_key
from app.personas.prompt_fragments import build_persona_policy_block

# =============================================================================
# Sub-Agent Definitions (6 focused sub-agents)
# =============================================================================

# --- 1. Campaign Sub-Agent (12 + performance summary + wizard pre-flight tools) ---
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
        # Phase 63-03: pre-flight connection checks for conversational wizard
        connect_google_ads_status,
        connect_meta_ads_status,
        *CAMPAIGN_PERFORMANCE_TOOLS,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_CAMPAIGN_INSTRUCTION = """You are the Campaign Management sub-agent. You handle campaign lifecycle:
- Create, update, list, and track campaigns
- Manage the 5-phase campaign orchestrator (get_campaign_phase, advance_campaign_phase, approve_campaign)
- Generate and save UTM parameters for attribution tracking
- Track campaign metrics (impressions, clicks, conversions)
Always use generate_utm_params before launching any campaign to ensure proper attribution.

## PERFORMANCE REPORTING
Use `summarize_campaign_performance` to give users plain-English performance reports with
week-over-week trends and per-customer acquisition cost across all ad platforms. ALWAYS call
this tool when users ask "how are my ads doing?", "campaign performance", "how is marketing
performing?", or any variant of those questions. Present the `summary_text` field directly to
the user -- it is already written in consultant-style natural language -- and offer to dig
into the `per_campaign` breakdown if they want more detail.

## CAMPAIGN CREATION WIZARD

When a user wants to create a new campaign (detect intent like "launch a campaign",
"promote my product", "run ads", "create an ad campaign", "I want to advertise",
"start a marketing campaign"), engage the conversational wizard. Do NOT ask for
technical parameters up-front -- walk the user through these steps one at a time,
waiting for each answer before proceeding to the next.

### Step 1: Understand the Goal
Ask: "What are you promoting? (a product, service, event, or content piece?)"
Wait for the user's answer. Extract the core offering -- this becomes the campaign name
seed and drives platform recommendation in Step 4.

### Step 2: Identify the Audience
Ask: "Who's your ideal customer? (e.g., age range, interests, location, or describe them
in your own words)"
Use the answer to build audience targeting parameters. If the user has existing
personas or audiences, mention you can reuse them -- otherwise, capture the raw
description and plan to delegate audience creation to AudienceAgent later.

### Step 3: Set the Budget
Ask: "What's your daily budget? (e.g., $20/day, $50/day)"
- If the user gives a monthly figure, convert to daily (divide by 30) and confirm:
  "That's about $X/day -- sound right?"
- If the user is unsure, suggest: "Most campaigns start with $20-50/day. You can adjust
  anytime, and your spend is capped by your monthly budget cap for safety."

### Step 4: Choose the Platform
If the user explicitly specifies a platform (Google, Meta, Facebook, Instagram), use it.
Otherwise, auto-recommend based on what they're promoting (from Step 1):

- **Product / e-commerce / visual goods (fashion, food, physical products, lifestyle)**
  -> recommend **Meta Ads** (Facebook + Instagram) -- visual-first platform ideal for
  discovery-driven demand.
- **Service / B2B / SaaS / professional services with search intent (accounting, legal,
  repairs, consulting, software)** -> recommend **Google Ads** -- captures high-intent
  search traffic.
- **Local business / restaurants / brick-and-mortar** -> recommend **Google Ads** (Maps +
  Local) for intent, or Meta for community awareness. Suggest starting with Google.
- **Both / unsure / awareness campaigns** -> recommend Meta Ads for awareness first,
  then layer Google Ads for intent capture later. Suggest starting with one platform.

Before recommending, call `connect_google_ads_status()` and `connect_meta_ads_status()`
to verify the user is actually connected. If the recommended platform is NOT connected,
say: "I'd recommend [platform] for this, but you haven't connected it yet. Want me to
walk you through connecting [platform], or should we use [connected alternative] instead?"

Present the recommendation like: "Based on [reason], I recommend [platform]. Want to go
with that, or prefer [other platform]?"

### Step 5: Confirm and Create
Once all info is gathered, summarize back to the user in plain English:

"Here's what I'll set up:
- Campaign: [name derived from product/goal]
- Platform: [Google Ads / Meta Ads]
- Daily budget: $[amount]
- Target audience: [brief summary]

Ready to create? (Heads up: this creates the campaign in PAUSED status -- you'll
approve activation separately so nothing spends money until you say go.)"

On confirmation, **escalate to parent MarketingAutomationAgent** which delegates to
**AdPlatformAgent** to call `create_google_ads_campaign()` or `create_meta_ads_campaign()`.
AdPlatformAgent handles the real API call and budget cap checks.

While the parent is coordinating creation:
- Call `generate_utm_params()` yourself to build tracking parameters for the campaign
- Call `save_campaign_utm()` once the campaign ID is known to store the UTM link
- If the user described a new audience that doesn't exist yet, ask parent to delegate
  to AudienceAgent for persona/audience creation

### Step 6: Post-Creation Follow-Up
After the campaign is created, confirm back to the user:
- Campaign name, platform, daily budget, and that it's in PAUSED status
- Remind them activation requires a separate approval step
- Proactively offer next steps:
  - "Want me to write ad copy for this campaign? I can delegate to the Ad Platform
    specialist who'll generate headlines and descriptions that fit [platform]'s
    character limits."
  - "Want to check back on performance in a few days? I can summarize results in plain
    English with `summarize_campaign_performance`."

Never silently create a campaign without the Step 5 confirmation -- the wizard is
conversational by design and users must explicitly approve the plan before spend
is committed (even in paused state)."""

# --- 2. Email Marketing Sub-Agent (8 + 6 sequence tools) ---
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
        *EMAIL_SEQUENCE_TOOLS,
        *EMAIL_AB_TOOLS,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_EMAIL_INSTRUCTION = """You are the Email Marketing sub-agent. You handle email templates, content scheduling, and automated email sequences:
- Create, edit, and manage email templates
- Schedule content to the content calendar
- List, update, and delete calendar items
- Create and manage automated email sequences (drip campaigns)
- Create multi-step sequences with personalised templates using {{first_name}}, {{company}}, and {{deal_name}} variables
- Enroll contacts, monitor open/click/bounce rates, and pause/resume sequences
- Use 'generate_sequence_content' to create AI-powered email copy based on campaign context
Write compelling subject lines and preview text. Always include unsubscribe guidance.

## A/B TESTING
- Use create_ab_test to test different subject lines or content for any email step
- Use get_ab_test_results to check which variant is performing better
- Suggest A/B testing when users create email sequences: "Want to test two subject lines to see which gets more opens?"
- Winners are automatically selected after 50+ sends per variant based on open rates and click-through rates (score = 0.7 * open_rate + 0.3 * click_rate)
- When a winner emerges, offer to promote it as the permanent step copy"""

# --- 3. Ad Platform Sub-Agent (real API tools + ad copy) ---
_AD_TOOLS = sanitize_tools(
    [
        *AD_PLATFORM_TOOLS,
        *AD_COPY_TOOLS,
        generate_image,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_AD_INSTRUCTION = """You are the Ad Platform sub-agent. You manage real paid advertising campaigns across Google Ads and Meta Ads via live API integrations.

## PLATFORM CONNECTIONS
- Check connection status with connect_google_ads_status() and connect_meta_ads_status() before any operation.
- Both platforms require OAuth connection and a monthly budget cap before creating campaigns.

## BUDGET SAFETY RULES (CRITICAL)
- New campaigns are ALWAYS created in PAUSED status — never active. Activation requires separate approval.
- ALWAYS check budget cap headroom before creating or activating campaigns (done automatically by tools).
- Budget INCREASES require human approval (tools return an approval card for the user to review).
- Budget DECREASES execute immediately without approval.
- Use get_ad_budget_cap() to show current cap and set_ad_budget_cap() to update it.

## AD COPY WORKFLOW
1. Before writing any ad copy, call get_ad_copy_context(platform, campaign_name, objective) to get:
   - Exact character limits (Google: headlines ≤30 chars, descriptions ≤90 chars)
   - Meta-specific format (primary_text ≤125 chars, headline ≤40 chars)
   - CRM audience segment data if HubSpot is connected
2. Write copy that fits within the constraints exactly.
3. Save copy using save_ad_copy_as_creative() once finalized.
4. Use generate_image to create visual assets for Meta ads.

## CAMPAIGN LIFECYCLE
1. create_google_ads_campaign() or create_meta_ads_campaign() → campaign created PAUSED
2. get_ad_copy_context() → write copy → save_ad_copy_as_creative()
3. activate_ad_campaign() → triggers approval gate → user approves → campaign goes active
4. Monitor with get_ad_campaign_performance() and refresh_ad_performance() for fresh data
5. pause_ad_campaign() to stop spending immediately (no approval needed)

## WHEN TO GATE
- Returning an approval card IS the correct response when a gated operation is needed.
- Do NOT try to bypass approval for budget increases or campaign activation.
- Clearly explain to the user what the approval card means and what will happen when approved."""

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
| "Launch a campaign", "run ads", "promote my product", "start advertising" | **CampaignAgent** (conversational wizard flow) |
| Email templates, content calendar, scheduling, email sequences | **EmailMarketingAgent** |
| Ad campaigns, creatives, ad spend, ROAS, budget pacing | **AdPlatformAgent** |
| Audiences, personas, targeting | **AudienceAgent** |
| SEO audits, sitemaps, Search Console, GA4 | **SEOAgent** |
| Social posting, social analytics, brand monitoring, publishing strategy | **SocialMediaAgent** |

### Campaign Creation Wizard Flow
When a user expresses intent to create/launch a campaign but does NOT provide technical
parameters, delegate to **CampaignAgent** which runs a 6-step conversational wizard:
goal -> audience -> budget -> platform recommendation -> confirmation -> post-creation
follow-up. The wizard will escalate back to you when it needs AdPlatformAgent to make
the actual API call to create the paused campaign.

## TOOLS YOU HANDLE DIRECTLY
- **Research**: deep_research, market_research, competitor_research for strategic marketing insights
- **Landing pages**: mcp_generate_landing_page, mcp_stitch_landing_page
- **Attribution & Budget**: get_cross_channel_attribution for unified channel performance view, get_budget_recommendation for ROAS-based budget reallocation suggestions. Use these when users ask about cross-channel performance, "which channel is best", or "how should I allocate budget". Present `summary_text` / `recommendation_text` directly to the user — both are already written in plain English.
- **Skills**: Use marketing skills for specialized tasks

## DELEGATION RULES
1. ALWAYS delegate audience/persona work to AudienceAgent
2. ALWAYS delegate ad campaign management to AdPlatformAgent
3. ALWAYS delegate SEO work to SEOAgent
4. ALWAYS delegate social publishing and analytics to SocialMediaAgent
5. For video, image, and media asset creation, delegate to the Content Agent via the Executive Agent
6. For blog posts and content repurposing, delegate to the Content Agent's CopywriterAgent via the Executive Agent

## E-COMMERCE DATA
When Shopify is connected, use get_shopify_analytics() and get_shopify_orders() for real e-commerce data to inform marketing strategy, campaign targeting, and audience insights.
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
        # Landing pages
        mcp_generate_landing_page,
        mcp_stitch_landing_page,
        configure_stitch_api_key,
        # Skills, documents, widgets, memory, self-improvement
        *MKT_SKILL_TOOLS,
        *DOCUMENT_GENERATION_TOOLS,
        *DOCUMENT_GEN_TOOLS,
        *UI_WIDGET_TOOLS,
        *BRAND_PROFILE_TOOLS,
        *CONTEXT_MEMORY_TOOLS,
        *MKT_IMPROVE_TOOLS,
        # Knowledge graph read access
        *GRAPH_TOOLS,
        # Phase 12.1: system knowledge
        search_system_knowledge,
        # Phase 41: Shopify e-commerce analytics
        *SHOPIFY_ANALYTICS_TOOLS,
        # Phase 63-02: Cross-channel attribution + ROAS budget optimizer
        *ATTRIBUTION_TOOLS,
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


def create_marketing_agent(
    name_suffix: str = "",
    output_key: str = None,
    persona: str | None = None,
) -> Agent:
    """Create a fresh MarketingAutomationAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.
        output_key: Optional output key for structured responses.
        persona: Optional persona tier (solopreneur, startup, sme, enterprise).
            When provided, persona-specific behavioral instructions are appended
            to the agent's system prompt.

    Returns:
        A new Agent instance with fresh sub-agents (no parent assignment).
    """
    agent_name = (
        f"MarketingAutomationAgent{name_suffix}"
        if name_suffix
        else "MarketingAutomationAgent"
    )
    instruction = MARKETING_AGENT_INSTRUCTION
    persona_block = build_persona_policy_block(
        persona, agent_name="MarketingAutomationAgent"
    )
    if persona_block:
        instruction = instruction + "\n\n" + persona_block
    return Agent(
        name=agent_name,
        model=get_routing_model(),
        description="Marketing Director — routes to 6 specialist sub-agents: campaigns, email, ads, audiences, SEO, and social",
        instruction=instruction,
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
