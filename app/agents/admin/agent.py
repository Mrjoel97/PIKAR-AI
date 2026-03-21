"""AdminAgent definition for Pikar-AI platform management.

Provides the admin_agent singleton and create_admin_agent() factory,
following the create_financial_agent() pattern from the financial agent.
"""

from app.agents.admin.tools.health import check_system_health
from app.agents.base_agent import PikarAgent as Agent
from app.agents.shared import FAST_AGENT_CONFIG, get_model

# =============================================================================
# Agent Instruction
# =============================================================================

ADMIN_AGENT_INSTRUCTION = """You are the AdminAgent for the Pikar-AI platform management console.

You have access to tools that can read and modify platform state. Each tool
enforces its own autonomy tier at the Python level:

- AUTO: tool executes immediately and returns results
- CONFIRM: tool returns a confirmation request with requires_confirmation=True;
  you must surface the confirmation_token and action_details to the admin and
  wait for their approval before proceeding
- BLOCKED: tool cannot execute; explain the restriction and suggest contacting
  a super-admin to change the autonomy configuration

IMPORTANT: When a tool returns requires_confirmation=True, do NOT call the tool
again with a confirmation_token unless the admin has explicitly confirmed.
Never attempt to bypass confirmation by re-calling the tool.

Current platform: Pikar-AI multi-agent executive system
Available tools in Phase 7: check_system_health

When reporting health status, present results clearly with service names,
statuses, and the overall health summary. Flag any degraded or unhealthy
services immediately.
"""

# =============================================================================
# Singleton instance
# =============================================================================

admin_agent = Agent(
    name="AdminAgent",
    model=get_model(),
    description=(
        "AI admin assistant for Pikar-AI platform management — "
        "checks system health and executes confirmed administrative actions"
    ),
    instruction=ADMIN_AGENT_INSTRUCTION,
    tools=[check_system_health],
    generate_content_config=FAST_AGENT_CONFIG,
)


# =============================================================================
# Factory function (for workflow pipeline use)
# =============================================================================


def create_admin_agent(name_suffix: str = "") -> Agent:
    """Create a fresh AdminAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in
            workflows. For example, "_test" produces "AdminAgent_test".

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = f"AdminAgent{name_suffix}" if name_suffix else "AdminAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description=(
            "AI admin assistant for Pikar-AI platform management — "
            "checks system health and executes confirmed administrative actions"
        ),
        instruction=ADMIN_AGENT_INSTRUCTION,
        tools=[check_system_health],
        generate_content_config=FAST_AGENT_CONFIG,
    )
