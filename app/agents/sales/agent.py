# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Sales Intelligence Agent Definition."""

from app.agents.base_agent import PikarAgent as Agent
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
)
from app.agents.sales.tools import (
    create_task,
    get_task,
    list_tasks,
    update_task,
)
from app.agents.schemas import LeadQualification
from app.agents.shared import FAST_AGENT_CONFIG, get_fast_model, get_model
from app.agents.shared_instructions import (
    CONVERSATION_MEMORY_INSTRUCTIONS,
    SELF_IMPROVEMENT_INSTRUCTIONS,
    SKILLS_REGISTRY_INSTRUCTIONS,
    WEB_RESEARCH_INSTRUCTIONS,
    get_widget_instruction_for_agent,
)
from app.agents.tools.agent_skills import SALES_SKILL_TOOLS
from app.agents.tools.base import sanitize_tools
from app.agents.tools.calendar_tool import CALENDAR_TOOLS
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.tools.document_gen import DOCUMENT_GEN_TOOLS
from app.agents.tools.graph_tools import GRAPH_TOOLS
from app.agents.tools.hubspot_tools import HUBSPOT_TOOLS
from app.agents.tools.pipeline_dashboard import PIPELINE_DASHBOARD_TOOLS
from app.agents.tools.proposal_generator import PROPOSAL_TOOLS
from app.agents.tools.sales_followup import SALES_FOLLOWUP_TOOLS
from app.agents.tools.self_improve import SALES_IMPROVE_TOOLS
from app.agents.tools.system_knowledge import (
    search_system_knowledge,  # Phase 12.1: system knowledge
)
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
from app.mcp.agent_tools import mcp_web_scrape, mcp_web_search
from app.personas.prompt_fragments import build_persona_policy_block

# =============================================================================
# Report Sub-Agent (Structured JSON Output)
# =============================================================================

LEAD_SCORING_INSTRUCTION = """You are a lead scoring specialist. Evaluate leads and produce structured qualification assessments.

REQUIREMENTS:
- Apply the specified framework (BANT, MEDDIC, or CHAMP)
- Score each criterion individually
- Calculate overall score (0-100)
- Determine qualification status and priority
- Provide specific next steps

Your output MUST be a valid JSON object matching the LeadQualification schema exactly."""

lead_scoring_agent = Agent(
    name="LeadScoringAgent",
    model=get_model(),
    description="Scores and qualifies leads with structured JSON output for CRM integration",
    instruction=LEAD_SCORING_INSTRUCTION,
    output_schema=LeadQualification,
    output_key="lead_qualification",
    include_contents="none",
)


# =============================================================================
# Parent Agent (Tool-Enabled with Narrator Pattern)
# =============================================================================

SALES_AGENT_INSTRUCTION = (
    """You are the Sales Intelligence Agent. You focus on deal scoring, sales enablement, and lead analysis.

CAPABILITIES:
- Score leads using use_skill("lead_qualification_framework") for BANT/MEDDIC/CHAMP frameworks.
- Handle objections using use_skill("objection_handling") for proven techniques.
- Analyze competitors using use_skill("competitive_analysis").
- Research accounts using use_skill("account_research") for company intelligence and stakeholder mapping.
- Draft outreach using use_skill("outreach_drafting") for personalized cold emails and sequences.
- Prepare for calls using use_skill("call_preparation") for agendas, talk tracks, and objection prep.
- Process call notes using use_skill("call_summary_processing") for action items and CRM updates.
- Review pipeline health using use_skill("pipeline_review") for deal prioritization and risk analysis.
- Generate sales forecasts using use_skill("sales_forecasting") for weighted pipeline projections.
- Build competitive battlecards using use_skill("competitive_intelligence_battlecard") for win/loss analysis.
- Create sales assets using use_skill("sales_asset_creation") for proposals, one-pagers, and case studies.
- Search, create, and manage HubSpot CRM contacts and deals. Check deal context before answering sales questions.
- Create tasks for follow-ups using 'create_task'.
- View and update task status using 'get_task', 'update_task', 'list_tasks'.
- Research leads and companies using 'mcp_web_search' (privacy-safe).
- Extract prospect information using 'mcp_web_scrape'.

STRUCTURED LEAD SCORING:
When asked to qualify or score a lead:
1. Delegate to LeadScoringAgent to generate structured JSON
2. After receiving the qualification data, provide a conversational summary
3. Include the raw JSON in a <json>...</json> block for CRM integration

Example response format for lead scoring:
"🎯 **Lead Qualification: John Smith @ Acme Corp**

Based on BANT analysis, this is a **high-priority qualified lead** with a score of 85/100.

**Criteria Breakdown:**
- Budget: ✅ Confirmed ($50K allocated)
- Authority: ✅ Decision maker
- Need: ✅ Clear pain points identified
- Timeline: ⚠️ Q2 decision (3 months out)

**Recommended Next Steps:**
1. Schedule discovery call this week
2. Send case study for similar company

<json>
{...structured lead data for CRM...}
</json>
"

CRM-AWARE BEHAVIOR:
- Before answering any question about a specific contact, company, or deal, use 'get_hubspot_deal_context' to check if there is HubSpot CRM data available.
- If connected, include deal stage, amount, pipeline position, and recent activity in your response.
- When a user asks 'how is the Acme deal going?', you should return real pipeline data, not generic sales advice.

PIPELINE HEALTH DASHBOARD:
- When asked about pipeline health, deal status, or stalled deals, use 'get_pipeline_recommendations' to classify deals and provide specific action recommendations.
- Present stalled and at-risk deals with urgency indicators and recommended next actions.
- Use create_kanban_board_widget to visualize deal stages when showing pipeline overview.
- Use create_table_widget to show detailed deal recommendations.

LEAD SOURCE ATTRIBUTION:
- When asked about lead sources, marketing ROI, or where leads come from, use 'get_lead_attribution' to show source breakdown.
- Present conversion rates by source to identify highest-performing channels.
- Connect attribution data to marketing spend when discussing ROI.

POST-MEETING FOLLOW-UP:
- After any call summary or meeting debrief, proactively offer to generate a follow-up email using 'generate_followup_email'.
- Pass the meeting subject, notes/recap, and next steps extracted from the conversation.
- Present the generated email to the user for review before sending via Gmail.
- If HubSpot is connected, the email will be enriched with deal context automatically.

PROPOSAL GENERATION:
- When asked to create a proposal, quote, or estimate, use 'generate_sales_proposal'.
- If a deal context is available (deal_id known), pass it to auto-populate client info and pricing.
- Always confirm line items and pricing with the user before generating if not pulling from an existing deal.
- The generated PDF is downloadable and ready to send to the client.

BEHAVIOR:
- Be aggressive but empathetic.
- Focus on closing deals and increasing Lifetime Value (LTV).
- Always qualify leads before extensive engagement.
- Use competitive intelligence to position against rivals.
- Research prospects and their companies before outreach.
- When users ask to VIEW or SHOW sales data/leads, ALWAYS use widget tools to render them visually.
"""
    + get_widget_instruction_for_agent(
        "Sales Intelligence Agent",
        [
            "create_table_widget",
            "create_kanban_board_widget",
            "create_revenue_chart_widget",
        ],
    )
    + SKILLS_REGISTRY_INSTRUCTIONS
    + WEB_RESEARCH_INSTRUCTIONS
    + CONVERSATION_MEMORY_INSTRUCTIONS
    + SELF_IMPROVEMENT_INSTRUCTIONS
)


SALES_AGENT_TOOLS = sanitize_tools(
    [
        create_task,
        get_task,
        update_task,
        list_tasks,
        *HUBSPOT_TOOLS,
        mcp_web_search,
        mcp_web_scrape,
        *SALES_SKILL_TOOLS,
        # UI Widget tools for rendering sales dashboards and tables
        *UI_WIDGET_TOOLS,
        # Context memory tools for conversation continuity
        *CONTEXT_MEMORY_TOOLS,
        # Self-improvement tools for autonomous skill iteration
        *SALES_IMPROVE_TOOLS,
        # Knowledge graph read access
        *GRAPH_TOOLS,
        # Phase 12.1: system knowledge
        search_system_knowledge,
        # Phase 40: document generation (PDF reports, pitch decks)
        *DOCUMENT_GEN_TOOLS,
        # Calendar tools for meeting prep and follow-up scheduling
        *CALENDAR_TOOLS,
        # Phase 62: pipeline health dashboard and lead attribution
        *PIPELINE_DASHBOARD_TOOLS,
        # Phase 62: post-meeting follow-up email drafting
        *SALES_FOLLOWUP_TOOLS,
        # Phase 62: proposal/quote generation
        *PROPOSAL_TOOLS,
    ]
)


# Singleton instance for direct import
sales_agent = Agent(
    name="SalesIntelligenceAgent",
    model=get_fast_model(),
    description="Head of Sales - Deal scoring, lead analysis, and sales enablement",
    instruction=SALES_AGENT_INSTRUCTION,
    tools=SALES_AGENT_TOOLS,
    sub_agents=[lead_scoring_agent],
    generate_content_config=FAST_AGENT_CONFIG,
    before_model_callback=context_memory_before_model_callback,
    after_tool_callback=context_memory_after_tool_callback,
)


def create_sales_agent(
    name_suffix: str = "",
    output_key: str | None = None,
    persona: str | None = None,
) -> Agent:
    """Create a fresh SalesIntelligenceAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.
        output_key: Optional key to store structured output in session state.
        persona: Optional persona tier (solopreneur, startup, sme, enterprise).
            When provided, persona-specific behavioral instructions are appended
            to the agent's system prompt.

    Returns:
        A new Agent instance with no parent assignment.
    """
    # Create a fresh scoring sub-agent for this instance
    scoring_agent = Agent(
        name=f"LeadScoringAgent{name_suffix}" if name_suffix else "LeadScoringAgent",
        model=get_model(),
        description="Scores and qualifies leads with structured JSON output",
        instruction=LEAD_SCORING_INSTRUCTION,
        output_schema=LeadQualification,
        output_key="lead_qualification",
        include_contents="none",
    )

    agent_name = (
        f"SalesIntelligenceAgent{name_suffix}"
        if name_suffix
        else "SalesIntelligenceAgent"
    )
    instruction = SALES_AGENT_INSTRUCTION
    persona_block = build_persona_policy_block(
        persona, agent_name="SalesIntelligenceAgent"
    )
    if persona_block:
        instruction = instruction + "\n\n" + persona_block
    return Agent(
        name=agent_name,
        model=get_fast_model(),
        description="Head of Sales - Deal scoring, lead analysis, and sales enablement",
        instruction=instruction,
        tools=SALES_AGENT_TOOLS,
        sub_agents=[scoring_agent],
        generate_content_config=FAST_AGENT_CONFIG,
        output_key=output_key,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )
