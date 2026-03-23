"""User intelligence tools for the AdminAgent (Phase 13, SKIL-03 + SKIL-04).

Provides two analytics tools for identifying at-risk users and building
structured support context for impersonation sessions.

- get_at_risk_users (SKIL-03): correlates declining usage, last login, and
  billing status to produce a watch list of users at risk of churning.
- get_user_support_context (SKIL-04): returns usage summary, error patterns,
  and troubleshooting suggestions for a specific user prior to impersonation.

Both tools use the service-role Supabase client and execute_async, same pattern
as analytics_tools.py. All DB operations are read-only (auto autonomy tier).
"""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from app.agents.admin.tools._autonomy import check_autonomy
from app.services.impersonation_service import IMPERSONATION_ALLOWED_PATHS
from app.services.integration_proxy import IntegrationProxyService
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool 1: get_at_risk_users (SKIL-03)
# ---------------------------------------------------------------------------


async def get_at_risk_users(threshold_days_inactive: int = 7) -> dict[str, Any]:
    """Identify platform users at risk of churning.

    Correlates declining session activity, last login date, and Stripe billing
    status to produce a watch list. Stripe is optional — degrades gracefully when
    the integration is not configured.

    Autonomy tier: auto (read-only analytics query).

    Args:
        threshold_days_inactive: Days since last login to flag as inactive.
            Defaults to 7.

    Returns:
        Dict with ``at_risk_users`` list and ``criteria`` metadata dict.
        Each user entry contains: user_id, email, last_sign_in_at,
        activity_decline_pct, billing_status, risk_factors.
        On blocked tier: error dict.
    """
    gate = await check_autonomy("get_at_risk_users")
    if gate is not None:
        return gate

    client = get_service_client()
    now = datetime.now(UTC)
    window_start = (now - timedelta(days=28)).isoformat()
    current_window_start = (now - timedelta(days=14)).isoformat()
    prior_window_start = (now - timedelta(days=28)).isoformat()
    prior_window_end = (now - timedelta(days=14)).isoformat()
    inactive_threshold = (now - timedelta(days=threshold_days_inactive)).isoformat()

    try:
        # Step 1: Fetch distinct users active in the last 28 days
        sessions_query = (
            client.table("sessions").select("user_id").gte("updated_at", window_start)
        )
        sessions_result = await execute_async(
            sessions_query, op_name="at_risk.sessions"
        )
        session_rows: list[dict] = sessions_result.data or []

        if not session_rows:
            return {
                "at_risk_users": [],
                "criteria": {
                    "threshold_days_inactive": threshold_days_inactive,
                    "activity_decline_threshold": "50%",
                    "analysis_window_days": 14,
                },
            }

        # Deduplicate user IDs
        user_ids = list({row["user_id"] for row in session_rows if row.get("user_id")})

        at_risk: list[dict] = []

        for uid in user_ids:
            # Step 2: Count events in current 14-day window
            current_query = (
                client.table("session_events")
                .select("created_at")
                .eq("user_id", uid)
                .gte("created_at", current_window_start)
            )
            current_result = await execute_async(
                current_query, op_name="at_risk.events_current"
            )
            current_count = len(current_result.data or [])

            # Step 3: Count events in prior 14-day window
            prior_query = (
                client.table("session_events")
                .select("created_at")
                .eq("user_id", uid)
                .gte("created_at", prior_window_start)
                .lt("created_at", prior_window_end)
            )
            prior_result = await execute_async(
                prior_query, op_name="at_risk.events_prior"
            )
            prior_count = len(prior_result.data or [])

            # Skip users without enough prior data or no decline
            if prior_count == 0:
                continue

            decline_pct = round(100 * (1 - current_count / prior_count))
            if decline_pct < 50:
                continue

            # Step 4: Fetch email from user_executive_agents
            email_query = (
                client.table("user_executive_agents")
                .select("user_id, email")
                .eq("user_id", uid)
                .limit(1)
            )
            email_result = await execute_async(email_query, op_name="at_risk.email")
            email_rows: list[dict] = email_result.data or []
            email = email_rows[0].get("email", "") if email_rows else ""

            # Step 5: Fetch last_sign_in_at from Supabase Auth Admin
            last_sign_in: str | None = None
            try:
                auth_resp = await asyncio.to_thread(
                    client.auth.admin.get_user_by_id, uid
                )
                auth_user = getattr(auth_resp, "user", auth_resp)
                last_sign_in = getattr(auth_user, "last_sign_in_at", None)
                if not email:
                    email = getattr(auth_user, "email", "") or ""
            except Exception as exc:
                logger.warning("Could not fetch auth data for user %s: %s", uid, exc)

            # Filter: only flag users whose last login exceeds the inactive threshold
            if last_sign_in and last_sign_in > inactive_threshold:
                continue

            # Step 6: Attempt Stripe billing status
            billing_status = "unknown (Stripe not configured)"
            try:
                stripe_response = await IntegrationProxyService().call(
                    provider="stripe",
                    action="list_customers",
                    params={"email": email} if email else {},
                    session_id="admin",
                )
                # Extract subscription status from Stripe response
                customers = stripe_response.get("data", [])
                if customers:
                    subs = customers[0].get("subscriptions", {}).get("data", [])
                    if subs:
                        billing_status = subs[0].get("status", "unknown")
                    else:
                        billing_status = "no_subscription"
                else:
                    billing_status = "no_customer"
            except Exception:
                billing_status = "unknown (Stripe not configured)"

            # Step 7: Build risk_factors list
            risk_factors: list[str] = [
                f"Activity declined {decline_pct}% over the last 14 days",
            ]
            if last_sign_in is None or last_sign_in < inactive_threshold:
                risk_factors.append(
                    f"No login in the last {threshold_days_inactive} days"
                )
            if billing_status in ("past_due", "unpaid", "canceled"):
                risk_factors.append(f"Billing issue: {billing_status}")

            at_risk.append(
                {
                    "user_id": uid,
                    "email": email,
                    "last_sign_in_at": last_sign_in,
                    "activity_decline_pct": decline_pct,
                    "billing_status": billing_status,
                    "risk_factors": risk_factors,
                }
            )

        return {
            "at_risk_users": at_risk,
            "criteria": {
                "threshold_days_inactive": threshold_days_inactive,
                "activity_decline_threshold": "50%",
                "analysis_window_days": 14,
            },
        }

    except Exception as exc:
        logger.error("get_at_risk_users failed: %s", exc)
        return {"error": f"Failed to retrieve at-risk users: {exc}"}


# ---------------------------------------------------------------------------
# Tool 2: get_user_support_context (SKIL-04)
# ---------------------------------------------------------------------------


async def get_user_support_context(user_id: str) -> dict[str, Any]:
    """Return structured support context for a specific user.

    Builds a support brief for use before or during an impersonation session,
    including usage summary, recent error patterns, and suggested remediation
    steps.

    Autonomy tier: auto (read-only).

    Args:
        user_id: UUID of the user to build context for.

    Returns:
        Dict with usage_summary, error_patterns, suggested_steps, and
        allow_listed_actions (from IMPERSONATION_ALLOWED_PATHS).
        On blocked tier: error dict.
    """
    gate = await check_autonomy("get_user_support_context")
    if gate is not None:
        return gate

    client = get_service_client()
    now = datetime.now(UTC)
    seven_days_ago = (now - timedelta(days=7)).isoformat()
    forty_eight_hours_ago = (now - timedelta(hours=48)).isoformat()

    try:
        # Step 1: Fetch recent session_events for usage summary
        events_query = (
            client.table("session_events")
            .select("user_id, event_type, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(10)
        )
        events_result = await execute_async(events_query, op_name="support.events")
        event_rows: list[dict] = events_result.data or []

        # Count messages in last 7 days
        messages_7d = sum(
            1
            for e in event_rows
            if e.get("created_at", "") >= seven_days_ago
            and e.get("event_type") != "tool_error"
        )
        last_activity = event_rows[0].get("created_at") if event_rows else None

        usage_summary = {
            "messages_last_7_days": messages_7d,
            "last_activity": last_activity,
            "total_recent_events": len(event_rows),
        }

        # Step 2: Fetch error events in the last 48 hours
        errors_query = (
            client.table("session_events")
            .select("user_id, event_type, agent_name, error_type, created_at")
            .eq("user_id", user_id)
            .eq("event_type", "tool_error")
            .gte("created_at", forty_eight_hours_ago)
        )
        errors_result = await execute_async(errors_query, op_name="support.errors")
        error_rows: list[dict] = errors_result.data or []

        # Aggregate error patterns by (agent_name, error_type)
        error_counter: Counter = Counter()
        error_last: dict[tuple, str] = {}
        for err in error_rows:
            agent = err.get("agent_name", "unknown")
            etype = err.get("error_type", "unknown")
            key = (agent, etype)
            error_counter[key] += 1
            ts = err.get("created_at", "")
            if key not in error_last or ts > error_last[key]:
                error_last[key] = ts

        error_patterns = [
            {
                "agent": agent,
                "error_type": etype,
                "count": count,
                "last_occurred": error_last[(agent, etype)],
            }
            for (agent, etype), count in error_counter.most_common()
        ]

        # Step 3: Fetch user profile
        profile_query = (
            client.table("user_executive_agents")
            .select("user_id, persona, onboarding_completed")
            .eq("user_id", user_id)
            .limit(1)
        )
        profile_result = await execute_async(profile_query, op_name="support.profile")
        profile_rows: list[dict] = profile_result.data or []
        profile = profile_rows[0] if profile_rows else {}

        onboarding_completed = profile.get("onboarding_completed", False)

        # Step 4: Build suggested_steps based on patterns
        suggested_steps: list[str] = []

        if error_patterns:
            top_error = error_patterns[0]
            agent_name = top_error["agent"]
            suggested_steps.append(
                f"Check agent config for {agent_name}, consider clearing session state"
                f" ({top_error['count']} {top_error['error_type']} errors in last 48h)"
            )

        if messages_7d == 0 and not error_patterns:
            if not onboarding_completed:
                suggested_steps.append(
                    "Onboarding not completed — suggest guided walkthrough"
                )
            else:
                suggested_steps.append(
                    "Zero activity with active account — check if user is aware of relevant features, consider outreach"
                )
        elif messages_7d < 3 and not error_patterns:
            suggested_steps.append(
                "Declining usage with no recent errors — check if user is aware of relevant features, consider outreach"
            )

        if not suggested_steps:
            suggested_steps.append("No critical issues detected — usage looks normal")

        return {
            "user_id": user_id,
            "usage_summary": usage_summary,
            "error_patterns": error_patterns,
            "suggested_steps": suggested_steps,
            "allow_listed_actions": sorted(IMPERSONATION_ALLOWED_PATHS),
        }

    except Exception as exc:
        logger.error("get_user_support_context failed for %s: %s", user_id, exc)
        return {"error": f"Failed to retrieve support context for {user_id}: {exc}"}
