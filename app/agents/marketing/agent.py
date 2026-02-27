# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Marketing Automation Agent Definition."""

from app.agents.base_agent import PikarAgent as Agent

from app.agents.shared import get_model, CREATIVE_AGENT_CONFIG
from app.agents.content.tools import search_knowledge
from app.agents.marketing.tools import (
    create_campaign,
    get_campaign,
    update_campaign,
    list_campaigns,
    record_campaign_metrics,
)
from app.agents.enhanced_tools import (
    generate_campaign_ideas,
    get_seo_checklist,
    get_social_media_guide,
    perform_seo_audit,
)
from app.mcp.agent_tools import mcp_web_search, mcp_web_scrape, mcp_generate_landing_page
from app.agents.tools.social import SOCIAL_TOOLS
from app.agents.tools.agent_skills import MKT_SKILL_TOOLS
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
from app.agents.shared_instructions import SKILLS_REGISTRY_INSTRUCTIONS, WEB_RESEARCH_INSTRUCTIONS, CONVERSATION_MEMORY_INSTRUCTIONS, get_widget_instruction_for_agent
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.context_extractor import (
    context_memory_before_model_callback,
    context_memory_after_tool_callback,
)


MARKETING_AGENT_INSTRUCTION = """You are the Marketing Automation Agent. You focus on campaign planning, content scheduling, and audience targeting.

CAPABILITIES:
- Generate campaign ideas using 'generate_campaign_ideas' for creative frameworks.
- Plan and schedule marketing campaigns using 'create_campaign'.
- Manage campaigns using 'get_campaign', 'update_campaign', 'list_campaigns'.
- Track campaign performance using 'record_campaign_metrics'.
- Optimize SEO using 'get_seo_checklist' for comprehensive audits.
- Perform Deep SEO Audits using 'perform_seo_audit' for specific URLs.
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
- Research market trends and competitor campaigns.
- When users ask to VIEW or SHOW campaigns/metrics, ALWAYS use widget tools to render them visually.
""" + get_widget_instruction_for_agent(
    "Marketing Director",
    ["create_table_widget", "create_revenue_chart_widget", "create_kanban_board_widget", "create_calendar_widget"]
) + SKILLS_REGISTRY_INSTRUCTIONS + WEB_RESEARCH_INSTRUCTIONS + CONVERSATION_MEMORY_INSTRUCTIONS


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
    perform_seo_audit,
    mcp_web_search,
    mcp_web_scrape,
    mcp_generate_landing_page,
    *MKT_SKILL_TOOLS,
    *SOCIAL_TOOLS,
    # UI Widget tools for rendering marketing dashboards
    *UI_WIDGET_TOOLS,
    # Context memory tools for conversation continuity
    *CONTEXT_MEMORY_TOOLS,
]


# Singleton instance for direct import
marketing_agent = Agent(
    name="MarketingAutomationAgent",
    model=get_model(),
    description="Marketing Director - Campaign planning, content scheduling, and audience targeting",
    instruction=MARKETING_AGENT_INSTRUCTION,
    tools=MARKETING_AGENT_TOOLS,
    generate_content_config=CREATIVE_AGENT_CONFIG,
    before_model_callback=context_memory_before_model_callback,
    after_tool_callback=context_memory_after_tool_callback,
)


def create_marketing_agent(name_suffix: str = "", output_key: str = None) -> Agent:
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
        generate_content_config=CREATIVE_AGENT_CONFIG,
        output_key=output_key,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )
