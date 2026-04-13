# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""User problem diagnosis tool for the AdminAgent (Phase 69).

Provides a single async tool ``diagnose_user_problem`` that runs four parallel
diagnostic checks (OAuth integration status, platform API health, ad budget
caps, pending governance approvals) and returns a structured diagnosis with a
plain-English summary suitable for non-technical admins.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.agents.admin.tools._autonomy import check_autonomy as _check_autonomy
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

_ACTION_NAME = "diagnose_user_problem"


# ---------------------------------------------------------------------------
# Diagnostic check helpers
# ---------------------------------------------------------------------------


async def _check_oauth(client: Any, user_id: str) -> list[dict]:
    """Check user MCP integrations for inactive or missing connections.

    Returns a list of issue dicts — one per inactive provider.
    """
    try:
        query = (
            client.table("user_mcp_integrations")
            .select("provider, is_active")
            .eq("user_id", user_id)
        )
        result = await execute_async(query, op_name=f"{_ACTION_NAME}.oauth")
        rows: list[dict] = result.data or []

        # Flag integrations that are not active
        inactive = [r["provider"] for r in rows if not r.get("is_active", True)]
        if inactive:
            return [
                {
                    "category": "integration_issues",
                    "severity": "warning",
                    "details": {
                        "inactive_providers": inactive,
                        "count": len(inactive),
                    },
                    "recommended_action": (
                        f"Re-connect the following integration(s): "
                        f"{', '.join(inactive)}. The user should visit Settings > "
                        "Integrations to reconnect their account."
                    ),
                }
            ]
    except Exception as exc:
        logger.warning("%s: OAuth check failed: %s", _ACTION_NAME, exc)
    return []


async def _check_health(client: Any) -> list[dict]:
    """Check latest API health check rows for non-healthy endpoints.

    Returns a list of issue dicts if any endpoints are degraded.
    """
    try:
        query = (
            client.table("api_health_checks")
            .select("endpoint, status, response_time_ms")
            .neq("status", "healthy")
        )
        result = await execute_async(query, op_name=f"{_ACTION_NAME}.health")
        rows: list[dict] = result.data or []

        if rows:
            degraded = [r["endpoint"] for r in rows]
            critical = [r["endpoint"] for r in rows if r.get("status") == "unhealthy"]
            severity = "critical" if critical else "warning"
            return [
                {
                    "category": "platform_health_issues",
                    "severity": severity,
                    "details": {
                        "degraded_endpoints": degraded,
                        "count": len(degraded),
                    },
                    "recommended_action": (
                        f"Platform health is degraded on: {', '.join(degraded)}. "
                        "This may affect the user's ability to use certain features. "
                        "Check the Admin monitoring dashboard for details."
                    ),
                }
            ]
    except Exception as exc:
        logger.warning("%s: Health check failed: %s", _ACTION_NAME, exc)
    return []


async def _check_budget(client: Any, user_id: str) -> list[dict]:
    """Check ad budget caps for exceeded limits.

    Returns a list of issue dicts for each exceeded budget cap.
    """
    try:
        query = (
            client.table("ad_budget_caps")
            .select("platform, monthly_cap_usd, current_spend_usd")
            .eq("user_id", user_id)
            .gte("current_spend_usd", 0)
        )
        result = await execute_async(query, op_name=f"{_ACTION_NAME}.budget")
        rows: list[dict] = result.data or []

        exceeded = [
            r
            for r in rows
            if r.get("current_spend_usd", 0) >= r.get("monthly_cap_usd", float("inf"))
        ]
        if exceeded:
            issues = []
            for r in exceeded:
                platform = r.get("platform", "unknown")
                cap = r.get("monthly_cap_usd", 0)
                spend = r.get("current_spend_usd", 0)
                issues.append(
                    {
                        "category": "budget_cap_exceeded",
                        "severity": "critical",
                        "details": {
                            "platform": platform,
                            "monthly_cap_usd": cap,
                            "current_spend_usd": spend,
                        },
                        "recommended_action": (
                            f"The {platform} ad budget cap (${cap:.2f}/month) has been "
                            f"exceeded (current spend: ${spend:.2f}). Ad campaigns on "
                            "this platform may be paused. The user or admin should "
                            "review the budget cap in Settings > Ad Platforms."
                        ),
                    }
                )
            return issues
    except Exception as exc:
        logger.warning("%s: Budget check failed: %s", _ACTION_NAME, exc)
    return []


async def _check_approvals(client: Any, user_id: str) -> list[dict]:
    """Check governance approvals for pending items that may block the user.

    Returns a list of issue dicts if pending approvals exist.
    """
    try:
        query = (
            client.table("governance_approvals")
            .select("action_type, status")
            .eq("user_id", user_id)
            .eq("status", "pending")
        )
        result = await execute_async(query, op_name=f"{_ACTION_NAME}.approvals")
        rows: list[dict] = result.data or []

        if rows:
            action_types = [r.get("action_type", "unknown") for r in rows]
            unique_actions = list(set(action_types))
            return [
                {
                    "category": "pending_approvals",
                    "severity": "info",
                    "details": {
                        "count": len(rows),
                        "action_types": unique_actions,
                    },
                    "recommended_action": (
                        f"This user has {len(rows)} pending approval request(s) "
                        f"({', '.join(unique_actions)}). These may be blocking their "
                        "workflow. An admin can review them in the Approvals dashboard."
                    ),
                }
            ]
    except Exception as exc:
        logger.warning("%s: Approvals check failed: %s", _ACTION_NAME, exc)
    return []


# ---------------------------------------------------------------------------
# Summary builder
# ---------------------------------------------------------------------------


def _build_summary(issues: list[dict]) -> str:
    """Build a plain-English summary from the issues list.

    Args:
        issues: List of issue dicts with ``category`` and ``recommended_action``.

    Returns:
        A human-readable string suitable for display in an admin chat.
    """
    if not issues:
        return (
            "All systems look good for this user. OAuth integrations are connected, "
            "platform health is normal, budget caps are within limits, and there are "
            "no pending approvals."
        )

    n = len(issues)
    bullet_lines = "\n".join(
        f"  - {issue['recommended_action']}" for issue in issues
    )
    return (
        f"I found {n} issue(s) that may be affecting this user:\n{bullet_lines}"
    )


# ---------------------------------------------------------------------------
# Main tool function
# ---------------------------------------------------------------------------


async def diagnose_user_problem(user_id: str) -> dict[str, Any]:
    """Diagnose potential causes of a user-reported problem.

    Runs four parallel checks against platform data sources:
    1. OAuth / MCP integration status
    2. Platform API health (degraded endpoints)
    3. Ad budget caps (exceeded limits)
    4. Governance approvals (pending requests blocking workflow)

    Autonomy tier: auto (read-only diagnostic).

    Args:
        user_id: UUID of the user to diagnose.

    Returns:
        Dict with:
        - ``issues``: list of issue dicts (category, severity, details, recommended_action)
        - ``all_clear``: True when no issues found
        - ``plain_english_summary``: human-readable summary string
        On blocked autonomy tier: ``{"error": "..."}``
    """
    gate = await _check_autonomy(_ACTION_NAME)
    if gate is not None:
        return gate

    client = get_service_client()

    # Run all four checks in parallel
    oauth_issues, health_issues, budget_issues, approval_issues = await asyncio.gather(
        _check_oauth(client, user_id),
        _check_health(client),
        _check_budget(client, user_id),
        _check_approvals(client, user_id),
    )

    issues: list[dict] = (
        oauth_issues + health_issues + budget_issues + approval_issues
    )

    summary = _build_summary(issues)

    return {
        "user_id": user_id,
        "issues": issues,
        "all_clear": len(issues) == 0,
        "plain_english_summary": summary,
    }
