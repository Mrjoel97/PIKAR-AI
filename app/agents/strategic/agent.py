# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Strategic Planning Agent Definition."""

from google.adk.agents import Agent

from app.agents.shared import get_model
from app.agents.strategic.tools import (
    create_initiative,
    get_initiative,
    update_initiative,
    list_initiatives,
)
from app.agents.enhanced_tools import (
    use_skill,
    list_available_skills,
    generate_product_roadmap,
)

from app.mcp.agent_tools import mcp_web_search, mcp_web_scrape
from app.agents.tools.adaptive_workflows import ADAPTIVE_TOOLS


STRATEGIC_AGENT_INSTRUCTION = """You are the Strategic Planning Agent. You help set long-term goals (OKRs) and track initiatives.

CAPABILITIES:
- Create initiatives using 'create_initiative'.
- View initiative details using 'get_initiative'.
- Update initiative status and progress using 'update_initiative'.
- List all initiatives using 'list_initiatives'.
- Help prioritize competing initiatives.
- Research market trends using 'mcp_web_search' (privacy-safe).
- Research market trends using 'mcp_web_search' (privacy-safe).
- Extract competitor information using 'mcp_web_scrape'.
- Design new standard operating procedures using 'generate_workflow_template'.
- Access any skill using 'use_skill' or find skills using 'list_available_skills'.
- Generate product roadmaps using 'generate_product_roadmap'.

BEHAVIOR:
- Focus on the "Why" and "How".
- Force the user to prioritize - not everything can be #1.
- Think long-term and strategic.
- Track progress on all active initiatives.
- Use web search for market intelligence and competitive analysis."""


STRATEGIC_AGENT_TOOLS = [
    create_initiative,
    get_initiative,
    update_initiative,
    list_initiatives,
    mcp_web_search,
    mcp_web_search,
    mcp_web_scrape,
    use_skill,
    list_available_skills,
    generate_product_roadmap,
    *ADAPTIVE_TOOLS,
]


# Singleton instance for direct import
strategic_agent = Agent(
    name="StrategicPlanningAgent",
    model=get_model(),
    description="Chief Strategy Officer - Sets long-term goals (OKRs) and tracks initiatives",
    instruction=STRATEGIC_AGENT_INSTRUCTION,
    tools=STRATEGIC_AGENT_TOOLS,
)


def create_strategic_agent(name_suffix: str = "") -> Agent:
    """Create a fresh StrategicPlanningAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = f"StrategicPlanningAgent{name_suffix}" if name_suffix else "StrategicPlanningAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="Chief Strategy Officer - Sets long-term goals (OKRs) and tracks initiatives",
        instruction=STRATEGIC_AGENT_INSTRUCTION,
        tools=STRATEGIC_AGENT_TOOLS,
    )
