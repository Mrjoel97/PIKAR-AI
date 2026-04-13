# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Customer Support Agent Definition."""

from app.agents.base_agent import PikarAgent as Agent
from app.agents.content.tools import search_knowledge
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
)
from app.agents.customer_support.tools import (
    create_ticket,
    draft_customer_response,
    get_ticket,
    list_tickets,
    suggest_faq_from_tickets,
    update_ticket,
)
from app.agents.shared import ROUTING_AGENT_CONFIG, get_routing_model
from app.agents.shared_instructions import (
    CONVERSATION_MEMORY_INSTRUCTIONS,
    SELF_IMPROVEMENT_INSTRUCTIONS,
    SKILLS_REGISTRY_INSTRUCTIONS,
    WEB_SEARCH_ONLY_INSTRUCTIONS,
    get_widget_instruction_for_agent,
)
from app.agents.tools.agent_skills import SUPP_SKILL_TOOLS
from app.agents.tools.base import sanitize_tools
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.tools.document_gen import DOCUMENT_GEN_TOOLS
from app.agents.tools.graph_tools import GRAPH_TOOLS
from app.agents.tools.self_improve import SUPP_IMPROVE_TOOLS
from app.agents.tools.system_knowledge import (
    search_system_knowledge,  # Phase 12.1: system knowledge
)
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
from app.mcp.agent_tools import mcp_web_search
from app.personas.prompt_fragments import build_persona_policy_block

CUSTOMER_SUPPORT_AGENT_INSTRUCTION = (
    """You are the Customer Success Manager. You focus on customer success, proactive support, communication drafting, knowledge base management, and customer health monitoring.

CAPABILITIES:
- Analyze ticket sentiment using use_skill("ticket_sentiment_analysis") for prioritization.
- Assess churn risk using use_skill("churn_risk_indicators") for at-risk customer intervention.
- Create KB articles using use_skill("kb_article_templates") for how-to guides, troubleshooting trees, and FAQs.
- Manage escalations using use_skill("escalation_framework") for tier routing, SLAs, and handoff procedures.
- Draft first responses using use_skill("first_response_templates") for email, chat, and channel-specific templates.
- Create and manage support tickets using 'create_ticket', 'update_ticket', 'list_tickets'.
- View specific ticket details with 'get_ticket'.
- Draft knowledge base articles.
- Create escalation paths for complex issues.
- Search for solutions and FAQs using 'mcp_web_search' (privacy-safe).
- Draft professional customer-facing responses using 'draft_customer_response' for scenarios: refund, shipping_delay, complaint, follow_up, apology, general. Always personalize with the customer's name.
- Detect FAQ opportunities using 'suggest_faq_from_tickets' — call this proactively after resolving tickets or when asked about common issues. When it returns suggestions, present them clearly and offer to create KB articles.

BEHAVIOR:
- Be empathetic and customer-focused.
- Use sentiment analysis to prioritize negative experiences.
- Proactively identify churn risks and intervene.
- Proactively suggest actions to improve customer health scores.
- Draft professional communications for common customer scenarios.
- Identify patterns in resolved tickets to suggest FAQ entries.
- Document solutions for future reference.
- Research external knowledge bases for solutions.
- After resolving a ticket, proactively call suggest_faq_from_tickets to check for FAQ opportunities.
- When drafting responses, always use draft_customer_response to ensure consistent professional tone.
- Present FAQ suggestions with the source ticket count to justify the recommendation.
- When users ask to VIEW or SHOW tickets/support data, ALWAYS use widget tools to render them visually.
"""
    + get_widget_instruction_for_agent(
        "Customer Success Manager",
        ["create_table_widget", "create_kanban_board_widget"],
    )
    + SKILLS_REGISTRY_INSTRUCTIONS
    + WEB_SEARCH_ONLY_INSTRUCTIONS
    + CONVERSATION_MEMORY_INSTRUCTIONS
    + SELF_IMPROVEMENT_INSTRUCTIONS
)


CUSTOMER_SUPPORT_AGENT_TOOLS = sanitize_tools(
    [
        search_knowledge,
        create_ticket,
        get_ticket,
        update_ticket,
        list_tickets,
        draft_customer_response,  # SUPP-02: communication drafting
        suggest_faq_from_tickets,  # SUPP-03: FAQ suggestion from resolved tickets
        mcp_web_search,
        *SUPP_SKILL_TOOLS,
        # UI Widget tools for rendering support dashboards
        *UI_WIDGET_TOOLS,
        # Context memory tools for conversation continuity
        *CONTEXT_MEMORY_TOOLS,
        *SUPP_IMPROVE_TOOLS,
        # Knowledge graph read access
        *GRAPH_TOOLS,
        # Phase 12.1: system knowledge
        search_system_knowledge,
        # Phase 40: document generation (PDF reports, pitch decks)
        *DOCUMENT_GEN_TOOLS,
    ]
)


# Singleton instance for direct import
customer_support_agent = Agent(
    name="CustomerSupportAgent",
    model=get_routing_model(),
    description="Customer Success Manager - Customer success, proactive support, communication drafting, and customer health monitoring",
    instruction=CUSTOMER_SUPPORT_AGENT_INSTRUCTION,
    tools=CUSTOMER_SUPPORT_AGENT_TOOLS,
    generate_content_config=ROUTING_AGENT_CONFIG,
    before_model_callback=context_memory_before_model_callback,
    after_tool_callback=context_memory_after_tool_callback,
)


def create_customer_support_agent(
    name_suffix: str = "",
    persona: str | None = None,
) -> Agent:
    """Create a fresh CustomerSupportAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.
        persona: Optional persona tier (solopreneur, startup, sme, enterprise).
            When provided, persona-specific behavioral instructions are appended
            to the agent's system prompt.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = (
        f"CustomerSupportAgent{name_suffix}" if name_suffix else "CustomerSupportAgent"
    )
    instruction = CUSTOMER_SUPPORT_AGENT_INSTRUCTION
    persona_block = build_persona_policy_block(
        persona, agent_name="CustomerSupportAgent"
    )
    if persona_block:
        instruction = instruction + "\n\n" + persona_block
    return Agent(
        name=agent_name,
        model=get_routing_model(),
        description="Customer Success Manager - Customer success, proactive support, communication drafting, and customer health monitoring",
        instruction=instruction,
        tools=CUSTOMER_SUPPORT_AGENT_TOOLS,
        generate_content_config=ROUTING_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )
