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
from app.agents.admin.tools.integrations import (
    github_get_pr_status,
    github_list_prs,
    posthog_get_insights,
    posthog_query_events,
    sentry_get_issue_detail,
    sentry_get_issues,
)
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

## External Integration Tools (Phase 11)

Available integration tools: sentry_get_issues, sentry_get_issue_detail,
posthog_query_events, posthog_get_insights, github_list_prs, github_get_pr_status

When the admin asks about external service data (Sentry errors, PostHog events,
GitHub PRs, or Stripe status), use the appropriate integration tool. These tools
proxy through the backend — API keys are never exposed in chat responses.
If an integration is not configured, inform the admin they need to set it up
on the Integrations page first.

## Cross-Service Diagnostic Reasoning (SKIL-01)

When the admin reports an incident or asks about errors, DO NOT just return raw
data from a single source. Instead, correlate across available services:

1. Fetch Sentry errors (sentry_get_issues) to identify error patterns and affected endpoints.
2. Fetch PostHog events (posthog_query_events) around the same time window to check for
   user-facing impact (e.g., increased error events, drop in page views).
3. Cross-reference with health check data (get_api_health_summary, get_active_incidents)
   to see if any endpoints are degraded.
4. Synthesize a root-cause hypothesis. Example: "Sentry shows OOM errors on the embeddings
   worker (5 occurrences in the last hour), which explains the /health/embeddings failures
   you're seeing. PostHog confirms a 40% drop in embedding-related events since 14:00 UTC."

Key reasoning patterns:
- Error cluster + health failure on same service = probable root cause
- Sentry error spike + PostHog event drop = user-facing outage
- Multiple Sentry issues sharing the same culprit module = systemic issue, not isolated bug
- Health incident without Sentry errors = infrastructure issue (DNS, load balancer, network)
- Always state confidence level: "high confidence" when multiple signals align,
  "possible cause" when only one signal is available

## Response Time Degradation Trend Detection (SKIL-02)

When the admin asks about performance or when you detect signs of degradation in
health data, proactively analyze trends:

1. Use get_api_health_history to retrieve recent P95 response time data.
2. Compare the current P95 against the 7-day rolling baseline:
   - Calculate the 7-day average P95 from historical health check data.
   - If current P95 exceeds the baseline by more than 50%, flag as "degrading".
   - If current P95 exceeds the baseline by more than 100%, flag as "critical degradation".
3. When degradation is detected, proactively alert the admin even if they asked about
   something else: "I also noticed that /api/chat P95 response time is currently 2.3s,
   which is 85% above the 7-day baseline of 1.24s. This may indicate a growing issue."
4. Cross-reference with Sentry (new error types?) and PostHog (traffic spike?) to
   suggest whether the degradation is load-driven, error-driven, or infrastructure-driven.

Key patterns:
- Gradual P95 increase over days = memory leak, connection pool exhaustion, or growing dataset
- Sudden P95 spike = deployment regression, external dependency slowdown, or traffic surge
- P95 degradation on specific endpoints only = localized issue (query optimization, missing index)
- P95 degradation across all endpoints = infrastructure issue (CPU, memory, network)
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
        # Phase 11: external integrations
        sentry_get_issues,
        sentry_get_issue_detail,
        posthog_query_events,
        posthog_get_insights,
        github_list_prs,
        github_get_pr_status,
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
            # Phase 11: external integrations
            sentry_get_issues,
            sentry_get_issue_detail,
            posthog_query_events,
            posthog_get_insights,
            github_list_prs,
            github_get_pr_status,
        ],
        generate_content_config=FAST_AGENT_CONFIG,
    )
