# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Customer Support Agent Definition."""

from google.adk.agents import Agent

from app.agents.shared import get_model
from app.agents.content.tools import search_knowledge
from app.agents.customer_support.tools import (
    create_ticket,
    get_ticket,
    update_ticket,
    list_tickets,
)
from app.agents.enhanced_tools import (
    use_skill,
    list_available_skills,
    analyze_ticket_sentiment,
    assess_churn_risk,
)
from app.mcp.agent_tools import mcp_web_search


CUSTOMER_SUPPORT_AGENT_INSTRUCTION = """You are the Customer Support Agent. You focus on customer ticket triage, knowledge base management, and technical support.

CAPABILITIES:
- Analyze ticket sentiment using 'analyze_ticket_sentiment' for prioritization.
- Assess churn risk using 'assess_churn_risk' for at-risk customer intervention.
- Create and manage support tickets using 'create_ticket', 'update_ticket', 'list_tickets'.
- View specific ticket details with 'get_ticket'.
- Draft knowledge base articles.
- Create escalation paths for complex issues.
- Search for solutions and FAQs using 'mcp_web_search' (privacy-safe).

BEHAVIOR:
- Be empathetic and customer-focused.
- Use sentiment analysis to prioritize negative experiences.
- Proactively identify churn risks and intervene.
- Document solutions for future reference.
- Research external knowledge bases for solutions."""


CUSTOMER_SUPPORT_AGENT_TOOLS = [
    search_knowledge,
    create_ticket,
    get_ticket,
    update_ticket,
    list_tickets,
    analyze_ticket_sentiment,
    assess_churn_risk,
    mcp_web_search,
    use_skill,
    list_available_skills,
]


# Singleton instance for direct import
customer_support_agent = Agent(
    name="CustomerSupportAgent",
    model=get_model(),
    description="CTO / IT Support - Customer ticket triage, knowledge base, and technical support",
    instruction=CUSTOMER_SUPPORT_AGENT_INSTRUCTION,
    tools=CUSTOMER_SUPPORT_AGENT_TOOLS,
)


def create_customer_support_agent(name_suffix: str = "") -> Agent:
    """Create a fresh CustomerSupportAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = f"CustomerSupportAgent{name_suffix}" if name_suffix else "CustomerSupportAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="CTO / IT Support - Customer ticket triage, knowledge base, and technical support",
        instruction=CUSTOMER_SUPPORT_AGENT_INSTRUCTION,
        tools=CUSTOMER_SUPPORT_AGENT_TOOLS,
    )
