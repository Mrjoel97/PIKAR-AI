"""AdminAgent definition for Pikar-AI platform management.

Provides the admin_agent singleton and create_admin_agent() factory,
following the create_financial_agent() pattern from the financial agent.
"""

from app.agents.admin.tools.analytics import (
    generate_report,
    get_agent_effectiveness,
    get_engagement_report,
    get_usage_stats,
)
from app.agents.admin.tools.health import check_system_health
from app.agents.admin.tools.monitoring import (
    check_error_logs,
    check_rate_limits,
    get_active_incidents,
    get_api_health_history,
    get_api_health_summary,
    get_incident_detail,
    run_diagnostic,
)
from app.agents.admin.tools.users import (
    change_user_persona,
    get_user_detail,
    impersonate_user,
    list_users,
    suspend_user,
    unsuspend_user,
)
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
Available monitoring tools (Phase 8): get_api_health_summary, get_api_health_history,
get_active_incidents, get_incident_detail, run_diagnostic, check_error_logs, check_rate_limits
Available user management tools (Phase 9): list_users, get_user_detail,
suspend_user, unsuspend_user, change_user_persona, impersonate_user
Available analytics tools (Phase 10): get_usage_stats, get_agent_effectiveness,
get_engagement_report, generate_report

PROACTIVE GREETING: When a new conversation starts (the admin opens the panel or
sends their first message), IMMEDIATELY call get_api_health_summary() and
get_active_incidents() BEFORE responding. Include a brief health status line in
your greeting:
- If all endpoints healthy and no incidents: "All systems operational."
- If any endpoint degraded/down: "Alert: {endpoint} is {status}. {N} active incident(s)."
- If incidents exist: "There are {N} active incidents affecting {endpoints}."
Always lead with this health status before addressing the admin's question.

When the admin asks about system health in more detail, use get_api_health_summary
first for a quick overview, then drill into specific endpoints with
get_api_health_history or run_diagnostic if needed.

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
    tools=[
        check_system_health,
        get_api_health_summary,
        get_api_health_history,
        get_active_incidents,
        get_incident_detail,
        run_diagnostic,
        check_error_logs,
        check_rate_limits,
        list_users,
        get_user_detail,
        suspend_user,
        unsuspend_user,
        change_user_persona,
        impersonate_user,
        get_usage_stats,
        get_agent_effectiveness,
        get_engagement_report,
        generate_report,
    ],
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
        tools=[
            check_system_health,
            get_api_health_summary,
            get_api_health_history,
            get_active_incidents,
            get_incident_detail,
            run_diagnostic,
            check_error_logs,
            check_rate_limits,
            list_users,
            get_user_detail,
            suspend_user,
            unsuspend_user,
            change_user_persona,
            impersonate_user,
            get_usage_stats,
            get_agent_effectiveness,
            get_engagement_report,
            generate_report,
        ],
        generate_content_config=FAST_AGENT_CONFIG,
    )
