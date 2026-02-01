# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Marketing Automation Agent Definition."""

from google.adk.agents import Agent

from app.agents.shared import get_model
from app.agents.content.tools import search_knowledge
from app.agents.marketing.tools import (
    create_campaign,
    get_campaign,
    update_campaign,
    list_campaigns,
    record_campaign_metrics,
)
from app.agents.enhanced_tools import (
    use_skill,
    generate_campaign_ideas,
    get_seo_checklist,
    get_social_media_guide,
)
from app.mcp.agent_tools import mcp_web_search, mcp_web_scrape, mcp_generate_landing_page
from app.agents.tools.social import SOCIAL_TOOLS


MARKETING_AGENT_INSTRUCTION = """You are the Marketing Automation Agent. You focus on campaign planning, content scheduling, and audience targeting.

CAPABILITIES:
- Generate campaign ideas using 'generate_campaign_ideas' for creative frameworks.
- Plan and schedule marketing campaigns using 'create_campaign'.
- Manage campaigns using 'get_campaign', 'update_campaign', 'list_campaigns'.
- Track campaign performance using 'record_campaign_metrics'.
- Optimize SEO using 'get_seo_checklist' for comprehensive audits.
- Master social media using 'get_social_media_guide' for platform best practices.
- Search knowledge base for brand voice and context.
- Research trends and competitors using 'mcp_web_search' (privacy-safe).
- Extract competitor content using 'mcp_web_scrape'.
- Generate landing pages using 'mcp_generate_landing_page'.
- Publish to social media using 'publish_to_social' for connected accounts.
- List connected accounts using 'list_connected_accounts'.
- Connect new social accounts using 'get_oauth_url'.

BEHAVIOR:
- Focus on ROI.
- Use data to inform campaign decisions.
- Consider brand voice and consistency.
- Leverage skills for professional marketing frameworks.
- Research market trends and competitor campaigns."""


MARKETING_AGENT_TOOLS = [
    search_knowledge,
    create_campaign,
    get_campaign,
    update_campaign,
    list_campaigns,
    record_campaign_metrics,
    generate_campaign_ideas,
    get_seo_checklist,
    get_social_media_guide,
    mcp_web_search,
    mcp_web_scrape,
    mcp_generate_landing_page,
    use_skill,
    *SOCIAL_TOOLS,
]


# Singleton instance for direct import
marketing_agent = Agent(
    name="MarketingAutomationAgent",
    model=get_model(),
    description="Marketing Director - Campaign planning, content scheduling, and audience targeting",
    instruction=MARKETING_AGENT_INSTRUCTION,
    tools=MARKETING_AGENT_TOOLS,
)


def create_marketing_agent(name_suffix: str = "") -> Agent:
    """Create a fresh MarketingAutomationAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = f"MarketingAutomationAgent{name_suffix}" if name_suffix else "MarketingAutomationAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="Marketing Director - Campaign planning, content scheduling, and audience targeting",
        instruction=MARKETING_AGENT_INSTRUCTION,
        tools=MARKETING_AGENT_TOOLS,
    )
