# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Sales Intelligence Agent Definition."""

from app.agents.base_agent import PikarAgent as Agent

from app.agents.shared import get_model, get_fast_model, FAST_AGENT_CONFIG
from app.agents.schemas import LeadQualification
from app.agents.sales.tools import (
    create_task,
    get_task,
    update_task,
    list_tasks,
)
from app.agents.enhanced_tools import (
    get_lead_qualification_framework,
    get_objection_handling_scripts,
    get_competitive_analysis_framework,
    manage_hubspot,
)
from app.mcp.agent_tools import mcp_web_search, mcp_web_scrape
from app.agents.tools.agent_skills import SALES_SKILL_TOOLS
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
from app.agents.shared_instructions import SKILLS_REGISTRY_INSTRUCTIONS, WEB_RESEARCH_INSTRUCTIONS, CONVERSATION_MEMORY_INSTRUCTIONS, get_widget_instruction_for_agent
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.context_extractor import (
    context_memory_before_model_callback,
    context_memory_after_tool_callback,
)


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

SALES_AGENT_INSTRUCTION = """You are the Sales Intelligence Agent. You focus on deal scoring, sales enablement, and lead analysis.

CAPABILITIES:
- Score leads using 'get_lead_qualification_framework' for BANT/MEDDIC/CHAMP frameworks.
- Handle objections using 'get_objection_handling_scripts' for proven techniques.
- Analyze competitors using 'get_competitive_analysis_framework'.
- Manage HubSpot CRM data using 'manage_hubspot'.
- Create tasks for follow-ups using 'create_task'.
- View and update task status using 'get_task', 'update_task', 'list_tasks'.
- Draft outreach emails and sales scripts.
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

BEHAVIOR:
- Be aggressive but empathetic.
- Focus on closing deals and increasing Lifetime Value (LTV).
- Always qualify leads before extensive engagement.
- Use competitive intelligence to position against rivals.
- Research prospects and their companies before outreach.
- When users ask to VIEW or SHOW sales data/leads, ALWAYS use widget tools to render them visually.
""" + get_widget_instruction_for_agent(
    "Sales Intelligence Agent",
    ["create_table_widget", "create_kanban_board_widget", "create_revenue_chart_widget"]
) + SKILLS_REGISTRY_INSTRUCTIONS + WEB_RESEARCH_INSTRUCTIONS + CONVERSATION_MEMORY_INSTRUCTIONS


SALES_AGENT_TOOLS = [
    create_task,
    get_task,
    update_task,
    list_tasks,
    get_lead_qualification_framework,
    get_objection_handling_scripts,
    get_competitive_analysis_framework,
    manage_hubspot,
    mcp_web_search,
    mcp_web_scrape,
    *SALES_SKILL_TOOLS,
    # UI Widget tools for rendering sales dashboards and tables
    *UI_WIDGET_TOOLS,
    # Context memory tools for conversation continuity
    *CONTEXT_MEMORY_TOOLS,
]


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


def create_sales_agent(name_suffix: str = "", output_key: str = None) -> Agent:
    """Create a fresh SalesIntelligenceAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

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
    
    agent_name = f"SalesIntelligenceAgent{name_suffix}" if name_suffix else "SalesIntelligenceAgent"
    return Agent(
        name=agent_name,
        model=get_fast_model(),
        description="Head of Sales - Deal scoring, lead analysis, and sales enablement",
        instruction=SALES_AGENT_INSTRUCTION,
        tools=SALES_AGENT_TOOLS,
        sub_agents=[scoring_agent],
        generate_content_config=FAST_AGENT_CONFIG,
        output_key=output_key,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )

