"""Admin Agent tools package."""

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

__all__ = [
    "change_user_persona",
    "check_error_logs",
    "check_rate_limits",
    "check_system_health",
    "generate_report",
    "get_active_incidents",
    "get_agent_effectiveness",
    "get_api_health_history",
    "get_api_health_summary",
    "get_engagement_report",
    "get_incident_detail",
    "get_usage_stats",
    "get_user_detail",
    "github_get_pr_status",
    "github_list_prs",
    "impersonate_user",
    "list_users",
    "posthog_get_insights",
    "posthog_query_events",
    "run_diagnostic",
    "sentry_get_issue_detail",
    "sentry_get_issues",
    "suspend_user",
    "unsuspend_user",
]
