# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Sales Intelligence Agent Definition."""

from google.adk.agents import Agent

from app.agents.shared import get_model
from app.agents.schemas import LeadQualification
from app.agents.sales.tools import (
    create_task,
    get_task,
    update_task,
    list_tasks,
)
from app.agents.enhanced_tools import (
    use_skill,
    get_lead_qualification_framework,
    get_objection_handling_scripts,
    get_competitive_analysis_framework,
)
from app.mcp.agent_tools import mcp_web_search, mcp_web_scrape


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
- Research prospects and their companies before outreach."""


SALES_AGENT_TOOLS = [
    create_task,
    get_task,
    update_task,
    list_tasks,
    get_lead_qualification_framework,
    get_objection_handling_scripts,
    get_competitive_analysis_framework,
    mcp_web_search,
    mcp_web_scrape,
    use_skill,
]


# Singleton instance for direct import
sales_agent = Agent(
    name="SalesIntelligenceAgent",
    model=get_model(),
    description="Head of Sales - Deal scoring, lead analysis, and sales enablement",
    instruction=SALES_AGENT_INSTRUCTION,
    tools=SALES_AGENT_TOOLS,
    sub_agents=[lead_scoring_agent],
)


def create_sales_agent(name_suffix: str = "") -> Agent:
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
        model=get_model(),
        description="Head of Sales - Deal scoring, lead analysis, and sales enablement",
        instruction=SALES_AGENT_INSTRUCTION,
        tools=SALES_AGENT_TOOLS,
        sub_agents=[scoring_agent],
    )

