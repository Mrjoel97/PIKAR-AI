# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""AdminAgent definition for Pikar-AI platform management.

Decomposed into a routing parent + 5 focused sub-agents for optimal
LLM tool selection accuracy (each sub-agent has 8-18 tools max).

Provides the admin_agent singleton and create_admin_agent() factory,
following the Marketing agent reference architecture.
"""

from app.agents.admin.tools.analytics import (
    generate_report,
    get_agent_effectiveness,
    get_engagement_report,
    get_usage_stats,
)
from app.agents.admin.tools.billing import (
    assess_refund_risk,
    detect_analytics_anomalies,
    forecast_revenue,
    generate_executive_summary,
    get_billing_metrics,
    get_plan_distribution,
    issue_refund,
)
from app.agents.admin.tools.config import (
    assess_config_impact,
    get_agent_config,
    get_autonomy_permissions,
    get_config_history,
    get_feature_flags,
    recommend_config_rollback,
    rollback_agent_config,
    toggle_feature_flag,
    update_agent_config,
    update_autonomy_permission,
)
from app.agents.admin.tools.governance import (
    classify_and_escalate,
    generate_compliance_report,
    generate_daily_digest,
    list_all_approvals,
    manage_admin_role,
    override_approval,
    recommend_autonomy_tier,
    suggest_role_permissions,
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
from app.agents.admin.tools.knowledge import (
    check_knowledge_duplicate,
    delete_knowledge_entry,
    get_knowledge_stats,
    list_knowledge_entries,
    recommend_chunking_strategy,
    search_knowledge,
    upload_knowledge,
    validate_knowledge_relevance,
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
from app.agents.admin.tools.adoption import get_feature_adoption
from app.agents.admin.tools.billing_alerts import (
    check_billing_alerts,
    get_billing_cost_projection,
)
from app.agents.admin.tools.diagnosis import diagnose_user_problem
from app.agents.admin.tools.users_intelligence import (
    get_at_risk_users,
    get_user_support_context,
)
from app.agents.base_agent import PikarAgent as Agent
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
)
from app.agents.shared import FAST_AGENT_CONFIG, get_fast_model, get_model, get_routing_model
from app.agents.shared_instructions import CONVERSATION_MEMORY_INSTRUCTIONS
from app.agents.tools.base import sanitize_tools
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS

# =============================================================================
# Sub-Agent 1: SystemHealthAgent (~15 tools)
# =============================================================================

_SYSTEM_HEALTH_TOOLS = sanitize_tools(
    [
        check_system_health,
        get_api_health_summary,
        get_api_health_history,
        get_active_incidents,
        get_incident_detail,
        run_diagnostic,
        check_error_logs,
        check_rate_limits,
        sentry_get_issues,
        sentry_get_issue_detail,
        posthog_query_events,
        posthog_get_insights,
        github_list_prs,
        github_get_pr_status,
        diagnose_user_problem,
        get_feature_adoption,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_SYSTEM_HEALTH_INSTRUCTION = """You are the SystemHealthAgent for the Pikar-AI platform.

You monitor and diagnose platform health, external integrations, and feature adoption.

## PROACTIVE GREETING
When a new conversation starts, IMMEDIATELY call get_api_health_summary() and
get_active_incidents() BEFORE responding. Include a brief health status line:
- If all endpoints healthy and no incidents: "All systems operational."
- If any endpoint degraded/down: "Alert: {endpoint} is {status}. {N} active incident(s)."
- If incidents exist: "There are {N} active incidents affecting {endpoints}."
Always lead with this health status before addressing the admin's question.

## SYSTEM HEALTH
Use get_api_health_summary first for a quick overview, then drill into specific
endpoints with get_api_health_history or run_diagnostic if needed.
Flag any degraded or unhealthy services immediately.

## EXTERNAL INTEGRATIONS (Phase 11)
When the admin asks about Sentry errors, PostHog events, or GitHub PRs, use the
appropriate integration tool. API keys are never exposed in chat responses.
If an integration is not configured, inform the admin to set it up on the Integrations page.

## CROSS-SERVICE DIAGNOSTIC REASONING (SKIL-01)
When the admin reports an incident or asks about errors, correlate across services:
1. Fetch Sentry errors (sentry_get_issues) to identify error patterns.
2. Fetch PostHog events (posthog_query_events) for user-facing impact.
3. Cross-reference with health check data for degraded endpoints.
4. Synthesize a root-cause hypothesis with confidence level.

Key reasoning patterns:
- Error cluster + health failure on same service = probable root cause
- Sentry error spike + PostHog event drop = user-facing outage
- Health incident without Sentry errors = infrastructure issue
- Always state confidence level: "high confidence" or "possible cause"

## RESPONSE TIME DEGRADATION TREND DETECTION (SKIL-02)
When asked about performance or detecting degradation signs:
1. Use get_api_health_history to retrieve recent P95 response time data.
2. If current P95 exceeds the 7-day baseline by >50%, flag as "degrading".
3. If current P95 exceeds the baseline by >100%, flag as "critical degradation".
4. Cross-reference with Sentry and PostHog to assess cause.

## USER PROBLEM DIAGNOSIS (Phase 69)
When a user reports a problem, call diagnose_user_problem(user_id) FIRST before
manual investigation. It checks: OAuth status, platform API health, budget caps,
and pending approvals. Present the plain_english_summary directly.
If all clear but issues persist, escalate to get_user_support_context and Sentry tools.

## FEATURE ADOPTION METRICS (Phase 69)
When the admin asks about feature usage, call get_feature_adoption(days, user_id).
- Without user_id: platform-wide adoption per agent
- With user_id: specific user's tool usage pattern
""" + CONVERSATION_MEMORY_INSTRUCTIONS


def _create_system_health_agent(suffix: str = "") -> Agent:
    """Create a SystemHealth sub-agent."""
    return Agent(
        name=f"SystemHealthAgent{suffix}",
        model=get_model(),
        description="System health monitoring, incident management, external integrations (Sentry, PostHog, GitHub), and user problem diagnosis",
        instruction=_SYSTEM_HEALTH_INSTRUCTION,
        tools=_SYSTEM_HEALTH_TOOLS,
        generate_content_config=FAST_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


# =============================================================================
# Sub-Agent 2: UserManagementAgent (~8 tools)
# =============================================================================

_USER_MANAGEMENT_TOOLS = sanitize_tools(
    [
        list_users,
        get_user_detail,
        suspend_user,
        unsuspend_user,
        change_user_persona,
        impersonate_user,
        get_at_risk_users,
        get_user_support_context,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_USER_MANAGEMENT_INSTRUCTION = """You are the UserManagementAgent for the Pikar-AI platform.

You handle all user administration, user intelligence, and support operations.

## USER MANAGEMENT (Phase 9+13)
Available tools: list_users, get_user_detail, suspend_user, unsuspend_user,
change_user_persona, impersonate_user, get_at_risk_users, get_user_support_context

## AT-RISK USER IDENTIFICATION (SKIL-03)
When asked about user health, churn risk, or "which users are at risk":
1. Call get_at_risk_users(threshold_days_inactive=7) to get the current watch list.
2. For each at-risk user, present: email, last sign-in, activity decline %, billing status, risk factors.
3. Prioritize users with multiple risk factors (declining activity + billing issues).
4. If billing_status is "unknown", note that connecting Stripe improves accuracy.
5. Suggest concrete actions: "Consider reaching out to {email} — their usage dropped {N}% and they haven't logged in for {M} days."

## INTERACTIVE IMPERSONATION SUPPORT PLAYBOOKS (SKIL-04)
When an impersonation session is active, proactively call get_user_support_context(user_id)
to build a support picture. Surface findings as a structured support brief:
1. Usage summary: "Last active: {N} days ago. Messages in last 7 days: {N} (down {X}%)."
2. Error patterns: "{N} {error_type} errors in the last 48 hours on {agent_name}."
3. Suggested troubleshooting based on patterns.
4. Actions available during impersonation: only allow-listed endpoints.

Key: Never suggest actions outside the allow-list. Distinguish "what I can see" from
"what can be done during impersonation."
""" + CONVERSATION_MEMORY_INSTRUCTIONS


def _create_user_management_agent(suffix: str = "") -> Agent:
    """Create a UserManagement sub-agent."""
    return Agent(
        name=f"UserManagementAgent{suffix}",
        model=get_fast_model(),
        description="User administration — list, suspend, change persona, impersonate users, identify at-risk users, and support troubleshooting",
        instruction=_USER_MANAGEMENT_INSTRUCTION,
        tools=_USER_MANAGEMENT_TOOLS,
        generate_content_config=FAST_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


# =============================================================================
# Sub-Agent 3: BillingAgent (~13 tools)
# =============================================================================

_BILLING_TOOLS = sanitize_tools(
    [
        get_billing_metrics,
        get_plan_distribution,
        issue_refund,
        detect_analytics_anomalies,
        generate_executive_summary,
        forecast_revenue,
        assess_refund_risk,
        get_billing_cost_projection,
        check_billing_alerts,
        get_usage_stats,
        get_agent_effectiveness,
        get_engagement_report,
        generate_report,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_BILLING_INSTRUCTION = """You are the BillingAgent for the Pikar-AI platform.

You handle billing metrics, analytics, revenue forecasting, and executive reporting.

## BILLING TOOLS (Phase 14)
Available billing tools: get_billing_metrics, get_plan_distribution, issue_refund,
detect_analytics_anomalies, generate_executive_summary, forecast_revenue, assess_refund_risk

When the admin asks about revenue, subscriptions, or billing:
- Use get_billing_metrics for live MRR/ARR from Stripe
- Use get_plan_distribution for tier breakdown from DB (no Stripe budget consumed)
- issue_refund is CONFIRM tier: always show confirmation card with charge details

## ANALYTICS ANOMALY DETECTION (SKIL-05)
When reviewing analytics or asked about metrics health, call detect_analytics_anomalies
to check for statistical outliers (>2 stddev from 30-day baseline). Report any flagged
anomalies with: metric name, current value, baseline mean, deviation magnitude.
Proactively run this when generating executive summaries.

## EXECUTIVE SUMMARY GENERATION (SKIL-06)
When asked for a summary, overview, or report, call generate_executive_summary to produce
a narrative with actionable recommendations. Include: usage trends, revenue health,
agent effectiveness highlights, and any anomalies detected.

## REVENUE FORECASTING (SKIL-10)
When asked about revenue projections or trends, call forecast_revenue. Present the
projection with confidence level and growth rate. Note that forecasts are based on
linear extrapolation from subscription history — directional indicators only.

## REFUND RISK ASSESSMENT (SKIL-11)
Before processing any refund, ALWAYS call assess_refund_risk first with the user_id.
Present the risk assessment (tenure, LTV, usage level, risk rating) to the admin
before proceeding to issue_refund.

## PROACTIVE BILLING COST ALERTS (Phase 69)
When asked about cost trends or "how much will we spend this month?":
Call get_billing_cost_projection() to get month-to-date actual spend, projected
full-month spend, prior month comparison, top cost drivers, and plain-English summary.
If projection shows >20% month-over-month increase, proactively flag it.

check_billing_alerts is for scheduled monitoring — triggered by Cloud Scheduler,
not normal conversation.

## ANALYTICS TOOLS
- get_usage_stats: platform usage statistics
- get_agent_effectiveness: per-agent performance metrics
- get_engagement_report: user engagement trends
- generate_report: structured report generation
""" + CONVERSATION_MEMORY_INSTRUCTIONS


def _create_billing_agent(suffix: str = "") -> Agent:
    """Create a Billing sub-agent."""
    return Agent(
        name=f"BillingAgent{suffix}",
        model=get_model(),
        description="Billing metrics, revenue forecasting, refunds, analytics anomaly detection, executive summaries, and usage reports",
        instruction=_BILLING_INSTRUCTION,
        tools=_BILLING_TOOLS,
        generate_content_config=FAST_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


# =============================================================================
# Sub-Agent 4: GovernanceAgent (~18 tools)
# =============================================================================

_GOVERNANCE_TOOLS = sanitize_tools(
    [
        recommend_autonomy_tier,
        generate_compliance_report,
        suggest_role_permissions,
        generate_daily_digest,
        classify_and_escalate,
        list_all_approvals,
        override_approval,
        manage_admin_role,
        get_agent_config,
        update_agent_config,
        get_config_history,
        rollback_agent_config,
        get_feature_flags,
        toggle_feature_flag,
        get_autonomy_permissions,
        update_autonomy_permission,
        assess_config_impact,
        recommend_config_rollback,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_GOVERNANCE_INSTRUCTION = """You are the GovernanceAgent for the Pikar-AI platform.

You handle governance, compliance, configuration management, and approval workflows.

## CONFIGURATION MANAGEMENT TOOLS (Phase 12)
- get_agent_config(agent_name) — read current instructions and version
- update_agent_config(agent_name, new_instructions, confirmation_token) — CONFIRM tier
- get_config_history(agent_name, limit) — list version history
- rollback_agent_config(history_id, agent_name, confirmation_token) — CONFIRM tier
- get_feature_flags() — list all feature flags
- toggle_feature_flag(flag_key, enabled, confirmation_token) — CONFIRM tier
- get_autonomy_permissions(category) — list admin action autonomy tiers
- update_autonomy_permission(action_name, new_level, confirmation_token) — CONFIRM tier
- assess_config_impact(agent_name) — SKIL-07: identify workflows affected
- recommend_config_rollback(agent_name) — SKIL-08: compare pre/post change metrics

## PRE-CHANGE IMPACT ASSESSMENT (SKIL-07)
Before applying config changes to high-traffic agents, call assess_config_impact:
1. Get workflows using the agent and 7-day call volume.
2. If risk_assessment is "HIGH" (>100 calls in 7 days): warn the admin explicitly.
3. If risk_assessment is "MEDIUM" (21-100 calls): inform and proceed.
4. If risk_assessment is "LOW" (<=20 calls): proceed without special warning.
5. Always list affected workflows by name.

## PERFORMANCE-DRIVEN ROLLBACK RECOMMENDATION (SKIL-08)
When agent quality issues are reported, call recommend_config_rollback:
1. Compare pre/post-change success rates.
2. If recommend_rollback is True: present success rate delta and rollback recommendation.
3. If False: explain why and suggest alternative diagnostics.
4. If no config change found: direct to health and error log tools.

## GOVERNANCE TOOLS (Phase 15)
Available: recommend_autonomy_tier, generate_compliance_report, suggest_role_permissions,
generate_daily_digest, classify_and_escalate, list_all_approvals, override_approval,
manage_admin_role

## AUTONOMY TIER RECOMMENDATION (SKIL-12)
When adding a new tool or asked about autonomy settings, call recommend_autonomy_tier
to get a data-driven recommendation. Present reasoning and risk factors alongside.
Do not auto-apply — let the admin decide.

## COMPLIANCE REPORT GENERATION (SKIL-13)
When asked for an audit summary or compliance report, call generate_compliance_report
with date range. Present: total actions, breakdown by source, top actions, notable patterns.

## ROLE PERMISSION SUGGESTIONS (SKIL-14)
When creating a new admin account, proactively call suggest_role_permissions with
a description of responsibilities. Present the suggested matrix and let super admin adjust.

## DAILY OPERATIONAL DIGEST (SKIL-15)
At the start of each new admin chat session, call generate_daily_digest() alongside
the health check greeting. Present: pending approvals, at-risk users, anomalous metrics,
upcoming subscription expirations. Keep the digest concise.

## SEVERITY CLASSIFICATION AND ESCALATION (SKIL-16)
When an issue is reported or detected, call classify_and_escalate(issue_description,
issue_context). For HIGH and CRITICAL severity, the tool automatically creates an
escalation entry routed to super_admin. classify_and_escalate is CONFIRM tier.

## APPROVAL MANAGEMENT
list_all_approvals shows all pending approvals across users.
override_approval is CONFIRM tier — present confirmation card before overriding.
manage_admin_role is CONFIRM tier — present details before creating/removing admin roles.
""" + CONVERSATION_MEMORY_INSTRUCTIONS


def _create_governance_agent(suffix: str = "") -> Agent:
    """Create a Governance sub-agent."""
    return Agent(
        name=f"GovernanceAgent{suffix}",
        model=get_model(),
        description="Governance, compliance, configuration management, feature flags, autonomy permissions, and approval workflows",
        instruction=_GOVERNANCE_INSTRUCTION,
        tools=_GOVERNANCE_TOOLS,
        generate_content_config=FAST_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


# =============================================================================
# Sub-Agent 5: KnowledgeAgent (~8 tools)
# =============================================================================

_KNOWLEDGE_TOOLS = sanitize_tools(
    [
        upload_knowledge,
        list_knowledge_entries,
        search_knowledge,
        delete_knowledge_entry,
        get_knowledge_stats,
        check_knowledge_duplicate,
        validate_knowledge_relevance,
        recommend_chunking_strategy,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_KNOWLEDGE_INSTRUCTION = """You are the KnowledgeAgent for the Pikar-AI platform.

You manage the knowledge base: uploading, searching, and maintaining knowledge entries.

## KNOWLEDGE MANAGEMENT TOOLS (Phase 12.1)

**Upload flow:** Files are uploaded via the /admin/knowledge/upload REST endpoint.
The upload_knowledge tool confirms and reports the upload result — it does NOT
receive binary file data. Use the REST endpoint URL for actual file uploads.

Available tools:
- upload_knowledge(entry_id, filename, mime_type, agent_scope, confirmation_token) — CONFIRM tier
- list_knowledge_entries(agent_scope, status, limit) — AUTO tier
- search_knowledge(query, agent_name, top_k) — AUTO tier (admin's own module with autonomy gate)
- delete_knowledge_entry(entry_id, confirmation_token) — CONFIRM tier
- get_knowledge_stats() — AUTO tier
- check_knowledge_duplicate(text_sample, agent_scope, threshold) — AUTO tier (SKIL-09)
- validate_knowledge_relevance(text_sample, target_agent) — AUTO tier (SKIL-09)
- recommend_chunking_strategy(filename, file_size_bytes, mime_type) — AUTO tier (SKIL-09)

## PRE-UPLOAD INTELLIGENCE WORKFLOW (SKIL-09)
Before the admin uploads a document, proactively run quality checks:

1. Call check_knowledge_duplicate(text_sample) with the first paragraph:
   - If near_duplicate=True and similarity > 0.95: warn about very similar content.
   - If near_duplicate=True and similarity 0.92-0.95: suggest updating existing entry.
   - If near_duplicate=False: proceed.

2. Call validate_knowledge_relevance(text_sample, target_agent) if agent_scope specified:
   - If relevant=False and confidence > 0.6: warn about relevance mismatch.

3. Call recommend_chunking_strategy(filename, file_size_bytes, mime_type) for large uploads:
   - Surface any warnings from the list before proceeding.
   - Report estimated_chunks so the admin knows the expected index size.

Key patterns:
- Always run dedup check before upload to prevent knowledge base pollution
- For multi-agent platforms, relevance validation helps route content to right domain
- Large files (>500KB) should always see the chunking warning before upload
- Images and videos skip chunking analysis
""" + CONVERSATION_MEMORY_INSTRUCTIONS


def _create_knowledge_agent(suffix: str = "") -> Agent:
    """Create a Knowledge sub-agent."""
    return Agent(
        name=f"KnowledgeAgent{suffix}",
        model=get_fast_model(),
        description="Knowledge base management — upload, search, deduplicate, and maintain knowledge entries with pre-upload quality checks",
        instruction=_KNOWLEDGE_INSTRUCTION,
        tools=_KNOWLEDGE_TOOLS,
        generate_content_config=FAST_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


# =============================================================================
# Admin Parent Agent routing instruction
# =============================================================================

ADMIN_AGENT_INSTRUCTION = """You are the AdminAgent — the Pikar-AI platform management console.

## YOUR ROLE: Route and Coordinate

You are a **routing agent**. Delegate to the right specialist sub-agent:

| Admin Intent | Delegate To |
|-------------|-------------|
| System health, API status, incidents, diagnostics, Sentry/PostHog/GitHub, user problem diagnosis, feature adoption | **SystemHealthAgent** |
| List/suspend/unsuspend users, change persona, impersonate, at-risk users, user support context | **UserManagementAgent** |
| Billing metrics, MRR/ARR, refunds, revenue forecasting, analytics anomaly, executive summary, usage reports, billing cost alerts | **BillingAgent** |
| Config management, feature flags, autonomy permissions, compliance reports, daily digest, approvals, role management, escalation | **GovernanceAgent** |
| Knowledge base upload, search, deduplicate, chunking strategy | **KnowledgeAgent** |

## PROACTIVE GREETING
When a new conversation starts, IMMEDIATELY delegate to:
1. **SystemHealthAgent** to call get_api_health_summary() and get_active_incidents()
2. **GovernanceAgent** to call generate_daily_digest()
Include the health status and daily digest summary in your greeting before addressing the admin's question.

## AUTONOMY TIER ENFORCEMENT
Each tool enforces its own autonomy tier at the Python level:
- AUTO: executes immediately and returns results
- CONFIRM: returns requires_confirmation=True; surface confirmation_token and action_details to admin and wait for their approval
- BLOCKED: cannot execute; explain restriction and suggest contacting super-admin

IMPORTANT: When a tool returns requires_confirmation=True, do NOT call the tool
again with a confirmation_token unless the admin has explicitly confirmed.
Never attempt to bypass confirmation by re-calling the tool.

## DELEGATION RULES
1. ALWAYS delegate health/monitoring/integrations/diagnostics to SystemHealthAgent
2. ALWAYS delegate user list, suspend, persona, impersonation, at-risk users to UserManagementAgent
3. ALWAYS delegate billing, refunds, revenue, analytics, reports to BillingAgent
4. ALWAYS delegate config, governance, compliance, approvals, feature flags to GovernanceAgent
5. ALWAYS delegate knowledge base operations to KnowledgeAgent
6. Never attempt to handle domain-specific tasks directly — you are a pure router

Current platform: Pikar-AI multi-agent executive system
""" + CONVERSATION_MEMORY_INSTRUCTIONS

# =============================================================================
# Singleton instance
# =============================================================================

_ADMIN_SUB_AGENTS = [
    _create_system_health_agent(),
    _create_user_management_agent(),
    _create_billing_agent(),
    _create_governance_agent(),
    _create_knowledge_agent(),
]

admin_agent = Agent(
    name="AdminAgent",
    model=get_routing_model(),
    description=(
        "AI admin assistant for Pikar-AI platform management — "
        "routes to 5 specialist sub-agents: system health, users, billing, governance, and knowledge"
    ),
    instruction=ADMIN_AGENT_INSTRUCTION,
    tools=[],  # Parent has NO tools — pure router
    sub_agents=_ADMIN_SUB_AGENTS,
    generate_content_config=FAST_AGENT_CONFIG,
    before_model_callback=context_memory_before_model_callback,
    after_tool_callback=context_memory_after_tool_callback,
)


# =============================================================================
# Factory function (for workflow pipeline use)
# =============================================================================


def create_admin_agent(
    name_suffix: str = "",
    instruction_override: str | None = None,
) -> Agent:
    """Create a fresh AdminAgent instance for workflow use or per-request chat.

    When ``instruction_override`` is provided (fetched live from DB by the chat
    endpoint), the agent uses that instruction string instead of the hardcoded
    ``ADMIN_AGENT_INSTRUCTION`` constant. This is the runtime injection hook
    that makes admin-edited instructions take effect on the next chat message
    without requiring a code redeploy (see RESEARCH.md Pitfall 1).

    Args:
        name_suffix: Optional suffix to differentiate agent instances in
            workflows. For example, "_test" produces "AdminAgent_test".
        instruction_override: Optional instruction string fetched from DB at
            request time. When provided and not a placeholder, overrides the
            hardcoded constant. Falls back to ``ADMIN_AGENT_INSTRUCTION`` when
            None.

    Returns:
        A new Agent instance with 5 sub-agents (no parent assignment).
    """
    agent_name = f"AdminAgent{name_suffix}" if name_suffix else "AdminAgent"
    instruction = (
        instruction_override
        if instruction_override is not None
        else ADMIN_AGENT_INSTRUCTION
    )
    return Agent(
        name=agent_name,
        model=get_routing_model(),
        description=(
            "AI admin assistant for Pikar-AI platform management — "
            "routes to 5 specialist sub-agents: system health, users, billing, governance, and knowledge"
        ),
        instruction=instruction,
        tools=[],  # Parent has NO tools — pure router
        sub_agents=[
            _create_system_health_agent(name_suffix),
            _create_user_management_agent(name_suffix),
            _create_billing_agent(name_suffix),
            _create_governance_agent(name_suffix),
            _create_knowledge_agent(name_suffix),
        ],
        generate_content_config=FAST_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )
