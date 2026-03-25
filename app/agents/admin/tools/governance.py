# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Governance tools for the AdminAgent — Phase 15.

Provides 8 tools covering autonomy tier recommendations, compliance
reporting, role permission suggestions, daily operational digest, severity
classification/escalation, and approval/role management actions.

Autonomy tiers:
- recommend_autonomy_tier, generate_compliance_report, suggest_role_permissions,
  generate_daily_digest, list_all_approvals: auto
- classify_and_escalate, override_approval, manage_admin_role: confirm
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.agents.admin.tools._autonomy import check_autonomy as _check_autonomy
from app.services.admin_audit import log_admin_action
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

# Sections used in permission suggestions
_SECTION_LIST = [
    "users",
    "monitoring",
    "analytics",
    "approvals",
    "config",
    "knowledge",
    "billing",
    "integrations",
    "settings",
    "audit_log",
]

# Risk keyword sets for autonomy tier recommendations
_READ_PATTERNS = frozenset(
    {"get", "list", "search", "view", "query", "fetch", "read", "show"}
)
_WRITE_PATTERNS = frozenset(
    {"update", "edit", "change", "toggle", "set", "modify", "patch"}
)
_FINANCIAL_PATTERNS = frozenset(
    {"refund", "charge", "payment", "billing", "invoice", "payout"}
)
_DESTRUCTIVE_PATTERNS = frozenset(
    {"delete", "remove", "drop", "purge", "reset", "destroy", "wipe"}
)
_EXTERNAL_PATTERNS = frozenset(
    {"external", "api", "proxy", "integration", "webhook", "third-party"}
)

# Severity keyword sets for issue classification
_CRITICAL_PHRASES = (
    "data loss",
    "security breach",
    "payment failure",
    "all users affected",
    "production down",
    "database down",
    "complete outage",
)
_HIGH_PHRASES = (
    "degraded",
    "multiple users",
    "billing issue",
    "auth failure",
    "timeout",
    "memory leak",
    "race condition",
)
_LOW_PHRASES = (
    "question",
    "request",
    "suggestion",
    "minor",
    "cosmetic",
    "typo",
    "wording",
)


# ---------------------------------------------------------------------------
# Tool 1: recommend_autonomy_tier (SKIL-12, auto tier)
# ---------------------------------------------------------------------------


async def recommend_autonomy_tier(
    action_name: str,
    action_description: str,
) -> dict[str, Any]:
    """Analyse a tool's risk profile and return a recommended autonomy tier.

    Examines keywords in the action description to classify risk and
    recommend one of three tiers: ``"auto"``, ``"confirm"``, or ``"blocked"``.
    Does not modify any state — the admin always makes the final decision.

    Autonomy tier: auto (read-only analysis).

    Args:
        action_name: The tool or action identifier being assessed.
        action_description: Human-readable description of what the action does.

    Returns:
        Dict with ``recommended_tier``, ``reasoning`` (str), ``risk_factors``
        (list[str]), and ``action_name``.
    """
    gate = await _check_autonomy("recommend_autonomy_tier")
    if gate is not None:
        return gate

    desc_lower = action_description.lower()
    name_lower = action_name.lower()
    combined = f"{name_lower} {desc_lower}"

    risk_factors: list[str] = []

    # Check for destructive patterns — highest risk
    destructive_hits = [p for p in _DESTRUCTIVE_PATTERNS if p in combined]
    financial_hits = [p for p in _FINANCIAL_PATTERNS if p in combined]
    external_hits = [p for p in _EXTERNAL_PATTERNS if p in combined]
    write_hits = [p for p in _WRITE_PATTERNS if p in combined]
    read_hits = [p for p in _READ_PATTERNS if p in combined]

    if destructive_hits:
        risk_factors.extend(f"destructive keyword: '{h}'" for h in destructive_hits)
        # Targeted destructive (e.g. "delete_user" not "delete_all") → confirm
        # Mass destructive (e.g. "all users", "delete_all") → blocked
        if any(
            mass in combined
            for mass in (
                "all users",
                "all data",
                "all records",
                "bulk delete",
                "delete_all",
                "delete all",
                "purge all",
                "drop all",
            )
        ):
            recommended_tier = "blocked"
            reasoning = (
                f"Action '{action_name}' contains mass-destructive keywords "
                f"({', '.join(destructive_hits)}) targeting all records. "
                "This action cannot be delegated to AI — block and require super-admin manual execution."
            )
        else:
            recommended_tier = "confirm"
            reasoning = (
                f"Action '{action_name}' contains destructive keywords "
                f"({', '.join(destructive_hits)}). "
                "Confirmation required before execution to prevent accidental data loss."
            )
    elif financial_hits:
        risk_factors.extend(f"financial keyword: '{h}'" for h in financial_hits)
        recommended_tier = "confirm"
        reasoning = (
            f"Action '{action_name}' involves financial operations "
            f"({', '.join(financial_hits)}). "
            "Financial mutations require admin confirmation to prevent billing errors."
        )
    elif external_hits:
        risk_factors.extend(f"external call keyword: '{h}'" for h in external_hits)
        recommended_tier = "confirm"
        reasoning = (
            f"Action '{action_name}' makes external API calls "
            f"({', '.join(external_hits)}). "
            "External calls consume rate-limited budgets and should require confirmation."
        )
    elif write_hits:
        risk_factors.extend(f"write keyword: '{h}'" for h in write_hits)
        recommended_tier = "confirm"
        reasoning = (
            f"Action '{action_name}' modifies platform state "
            f"({', '.join(write_hits)}). "
            "Write operations should be confirmed to maintain an auditable change trail."
        )
    else:
        if read_hits:
            risk_factors.extend(f"read keyword: '{h}'" for h in read_hits)
        recommended_tier = "auto"
        reasoning = (
            f"Action '{action_name}' appears to be read-only with no detected "
            "destructive, financial, external, or write-mutation keywords. "
            "Safe to execute automatically."
        )

    return {
        "recommended_tier": recommended_tier,
        "reasoning": reasoning,
        "risk_factors": risk_factors,
        "action_name": action_name,
    }


# ---------------------------------------------------------------------------
# Tool 2: generate_compliance_report (SKIL-13, auto tier)
# ---------------------------------------------------------------------------


async def generate_compliance_report(
    start_date: str,
    end_date: str,
    include_details: bool = False,
) -> dict[str, Any]:
    """Query audit logs and generate a narrative compliance summary.

    Queries ``admin_audit_log`` between ``start_date`` and ``end_date``,
    aggregates by source and action, and produces a human-readable narrative.

    Autonomy tier: auto (read-only audit log query).

    Args:
        start_date: ISO date string for the report period start (e.g. ``"2026-03-01"``).
        end_date: ISO date string for the report period end (inclusive).
        include_details: When True, includes the full list of audit rows in the
            response (may be large). Defaults to False.

    Returns:
        Dict with ``period``, ``total_actions`` (int), ``by_source`` (dict),
        ``by_action`` (dict), ``by_admin`` (dict), ``narrative`` (str),
        and ``key_actions`` (list of top 10 action names by frequency).
    """
    gate = await _check_autonomy("generate_compliance_report")
    if gate is not None:
        return gate

    client = get_service_client()
    try:
        query = (
            client.table("admin_audit_log")
            .select("action, source, admin_user_id, created_at")
            .gte("created_at", start_date)
            .lte("created_at", end_date)
            .order("created_at", desc=True)
            .limit(1000)
        )
        result = await execute_async(query, op_name="generate_compliance_report")
        rows: list[dict] = result.data or []

        total_actions = len(rows)
        by_source: Counter = Counter()
        by_action: Counter = Counter()
        by_admin: Counter = Counter()

        for row in rows:
            src = row.get("source") or "unknown"
            act = row.get("action") or "unknown"
            admin = row.get("admin_user_id") or "system"
            by_source[src] += 1
            by_action[act] += 1
            by_admin[admin] += 1

        key_actions = [action for action, _ in by_action.most_common(10)]

        # Build narrative
        if total_actions == 0:
            narrative = (
                f"Between {start_date} and {end_date}, no admin actions were recorded. "
                "The platform operated without administrative intervention during this period."
            )
        else:
            ai_count = by_source.get("ai_agent", 0)
            manual_count = by_source.get("manual", 0)
            ai_pct = round(ai_count / total_actions * 100) if total_actions else 0
            manual_pct = (
                round(manual_count / total_actions * 100) if total_actions else 0
            )
            top_3 = ", ".join(key_actions[:3]) if key_actions else "none"

            narrative = (
                f"Between {start_date} and {end_date}, {total_actions} admin actions were recorded. "
                f"{ai_pct}% were AI-initiated (ai_agent), {manual_pct}% were manual. "
                f"Top actions: {top_3}. "
                f"{len(by_admin)} distinct admin(s) were active during this period."
            )

        output: dict[str, Any] = {
            "period": {"start": start_date, "end": end_date},
            "total_actions": total_actions,
            "by_source": dict(by_source),
            "by_action": dict(by_action),
            "by_admin": dict(by_admin),
            "narrative": narrative,
            "key_actions": key_actions,
        }
        if include_details:
            output["rows"] = rows

        return output

    except Exception as exc:
        logger.error("generate_compliance_report failed: %s", exc)
        return {"error": f"Failed to generate compliance report: {exc}"}


# ---------------------------------------------------------------------------
# Tool 3: suggest_role_permissions (SKIL-14, auto tier)
# ---------------------------------------------------------------------------


async def suggest_role_permissions(
    role_description: str,
    base_role: str = "junior_admin",
) -> dict[str, Any]:
    """Return a section-action permission matrix for a described admin role.

    Analyses keywords in the role description to determine appropriate access
    levels across all admin sections. Does not create or modify any role —
    the super admin reviews and applies the suggestion.

    Autonomy tier: auto (read-only analysis, no mutations).

    Args:
        role_description: Free-text description of the admin's responsibilities.
        base_role: Starting role template (default ``"junior_admin"``).

    Returns:
        Dict with ``suggested_permissions`` (list of dicts with ``role``,
        ``section``, and ``allowed_actions``), ``base_role``, and ``reasoning``.
    """
    gate = await _check_autonomy("suggest_role_permissions")
    if gate is not None:
        return gate

    desc_lower = role_description.lower()

    # Determine access level from description keywords
    full_access = any(
        kw in desc_lower
        for kw in ("full", "everything", "all access", "superadmin", "super admin")
    )
    operations_access = any(
        kw in desc_lower
        for kw in ("operations", "manage", "lead", "operator", "manager")
    )
    read_only = any(
        kw in desc_lower
        for kw in (
            "read",
            "view",
            "monitor",
            "analyst",
            "read-only",
            "readonly",
            "observer",
        )
    )

    # Build per-section overrides for specific section keywords
    section_write_overrides: set[str] = set()
    for section in _SECTION_LIST:
        if section.replace("_", " ") in desc_lower or section in desc_lower:
            section_write_overrides.add(section)

    suggested_permissions: list[dict[str, Any]] = []

    for section in _SECTION_LIST:
        if full_access:
            actions = ["read", "write", "manage"]
        elif operations_access:
            # Operations leads get read+write on most sections, no manage
            if section in ("settings", "audit_log"):
                actions = ["read"]
            else:
                actions = ["read", "write"]
        elif read_only:
            actions = ["read"]
        elif section in section_write_overrides:
            # Specific section mentioned → read+write on that section
            actions = ["read", "write"]
        else:
            # Default: read-only
            actions = ["read"]

        suggested_permissions.append(
            {
                "role": base_role,
                "section": section,
                "allowed_actions": actions,
            }
        )

    # Build reasoning
    if full_access:
        reasoning = (
            "Role description indicates full access ('full'/'everything'/'all access'). "
            "Suggested read+write+manage across all sections. "
            "Review carefully before applying — this grants super-admin equivalent access."
        )
    elif operations_access:
        reasoning = (
            "Role description indicates operations/management responsibilities. "
            "Suggested read+write on operational sections (users, approvals, monitoring, etc.). "
            "Settings and audit_log restricted to read-only to preserve governance controls."
        )
    elif read_only:
        reasoning = (
            "Role description indicates read-only/analyst access. "
            "Suggested read-only across all sections — no write or manage permissions."
        )
    elif section_write_overrides:
        reasoning = (
            f"Role description references specific sections: {', '.join(sorted(section_write_overrides))}. "
            "Suggested read+write on those sections, read-only elsewhere."
        )
    else:
        reasoning = (
            "No clear access level keywords detected. Defaulting to read-only baseline. "
            "Review and adjust permissions for the admin's specific responsibilities."
        )

    return {
        "suggested_permissions": suggested_permissions,
        "base_role": base_role,
        "reasoning": reasoning,
    }


# ---------------------------------------------------------------------------
# Tool 4: generate_daily_digest (SKIL-15, auto tier)
# ---------------------------------------------------------------------------


async def generate_daily_digest(
    admin_user_id: str | None = None,
) -> dict[str, Any]:
    """Aggregate pending approvals, at-risk users, anomalies, and upcoming expirations.

    Each section degrades gracefully — if the source table is unavailable,
    the section returns ``count=0`` with an error note rather than failing
    the whole digest.

    Autonomy tier: auto (read-only aggregation from four sources).

    Args:
        admin_user_id: Optional admin UUID for future personalisation.
            Currently unused but reserved for per-admin digest filtering.

    Returns:
        Dict with ``generated_at`` (ISO timestamp), ``pending_approvals``,
        ``at_risk_users``, ``anomalies``, ``upcoming_expirations`` (each with
        ``count`` and ``items`` or ``summary``), and ``narrative`` (str).
    """
    gate = await _check_autonomy("generate_daily_digest")
    if gate is not None:
        return gate

    client = get_service_client()
    generated_at = datetime.now(tz=timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Section 1: Pending approvals
    # ------------------------------------------------------------------
    pending_approvals: dict[str, Any] = {"count": 0, "items": []}
    try:
        query = (
            client.table("approval_requests")
            .select("id, status, user_id, created_at, action_name")
            .eq("status", "PENDING")
            .order("created_at", desc=True)
            .limit(100)
        )
        result = await execute_async(query, op_name="daily_digest.pending_approvals")
        rows: list[dict] = result.data or []
        pending_approvals = {"count": len(rows), "items": rows[:5]}
    except Exception as exc:
        logger.warning("daily_digest: pending_approvals section failed: %s", exc)
        pending_approvals = {"count": 0, "items": [], "error": str(exc)}

    # ------------------------------------------------------------------
    # Section 2: At-risk users (declining 7-day activity)
    # ------------------------------------------------------------------
    at_risk_users: dict[str, Any] = {"count": 0, "summary": []}
    try:
        # Proxy through admin_analytics_daily — users with declining messages
        # compared to prior week (last 14 days, split into two 7-day windows)
        query = (
            client.table("admin_analytics_daily")
            .select("stat_date, messages, active_users")
            .order("stat_date", desc=True)
            .limit(14)
        )
        result = await execute_async(query, op_name="daily_digest.at_risk_users")
        rows = result.data or []
        # Simple heuristic: if last 7 days average is < previous 7 days average
        recent_msgs = sum(r.get("messages", 0) for r in rows[:7])
        prior_msgs = (
            sum(r.get("messages", 0) for r in rows[7:14]) if len(rows) >= 14 else None
        )

        at_risk_count = 0
        summary: list[dict] = []
        if prior_msgs is not None and prior_msgs > 0:
            change_pct = (recent_msgs - prior_msgs) / prior_msgs * 100
            if change_pct < -20:
                at_risk_count = 1
                summary = [
                    {
                        "metric": "platform_activity",
                        "recent_messages": recent_msgs,
                        "prior_messages": prior_msgs,
                        "change_pct": round(change_pct, 1),
                        "note": "Platform-wide activity declining >20% week-over-week",
                    }
                ]

        at_risk_users = {"count": at_risk_count, "summary": summary}
    except Exception as exc:
        logger.warning("daily_digest: at_risk_users section failed: %s", exc)
        at_risk_users = {"count": 0, "summary": [], "error": str(exc)}

    # ------------------------------------------------------------------
    # Section 3: Anomalous metrics (>2 stddev from 30-day mean)
    # ------------------------------------------------------------------
    anomalies: dict[str, Any] = {"count": 0, "items": []}
    try:
        query = (
            client.table("admin_analytics_daily")
            .select("stat_date, messages, active_users, workflows_run")
            .order("stat_date", desc=True)
            .limit(30)
        )
        result = await execute_async(query, op_name="daily_digest.anomalies")
        rows = result.data or []

        flagged: list[dict] = []
        if len(rows) >= 3:
            for metric_key in ("messages", "active_users", "workflows_run"):
                values = [float(r.get(metric_key) or 0) for r in rows]
                if not values:
                    continue
                current = values[0]
                baseline = values[1:]
                if len(baseline) < 2:
                    continue
                mean_val = sum(baseline) / len(baseline)
                variance = sum((v - mean_val) ** 2 for v in baseline) / len(baseline)
                stddev = variance**0.5
                if stddev == 0:
                    if current != mean_val:
                        flagged.append(
                            {
                                "metric": metric_key,
                                "current": current,
                                "mean": round(mean_val, 2),
                                "deviation": "inf",
                            }
                        )
                elif abs(current - mean_val) / stddev > 2.0:
                    flagged.append(
                        {
                            "metric": metric_key,
                            "current": current,
                            "mean": round(mean_val, 2),
                            "deviation": round(abs(current - mean_val) / stddev, 2),
                        }
                    )

        anomalies = {"count": len(flagged), "items": flagged}
    except Exception as exc:
        logger.warning("daily_digest: anomalies section failed: %s", exc)
        anomalies = {"count": 0, "items": [], "error": str(exc)}

    # ------------------------------------------------------------------
    # Section 4: Upcoming subscription expirations (next 7 days)
    # ------------------------------------------------------------------
    upcoming_expirations: dict[str, Any] = {"count": 0, "items": []}
    try:
        now_iso = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        from datetime import timedelta

        seven_days_iso = (datetime.now(tz=timezone.utc) + timedelta(days=7)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        query = (
            client.table("subscriptions")
            .select("id, user_id, current_period_end, tier, is_active")
            .eq("is_active", True)
            .gte("current_period_end", now_iso)
            .lt("current_period_end", seven_days_iso)
            .order("current_period_end")
            .limit(20)
        )
        result = await execute_async(query, op_name="daily_digest.upcoming_expirations")
        exp_rows: list[dict] = result.data or []
        upcoming_expirations = {"count": len(exp_rows), "items": exp_rows}
    except Exception as exc:
        logger.warning("daily_digest: upcoming_expirations section failed: %s", exc)
        upcoming_expirations = {"count": 0, "items": [], "error": str(exc)}

    # ------------------------------------------------------------------
    # Build narrative
    # ------------------------------------------------------------------
    narrative_parts: list[str] = [f"Daily digest as of {generated_at[:10]}."]

    if pending_approvals["count"] > 0:
        narrative_parts.append(
            f"{pending_approvals['count']} approval(s) pending — review in the Approvals section."
        )
    else:
        narrative_parts.append("No pending approvals.")

    if at_risk_users["count"] > 0:
        narrative_parts.append(
            f"{at_risk_users['count']} at-risk user/activity signal(s) detected."
        )

    if anomalies["count"] > 0:
        narrative_parts.append(
            f"{anomalies['count']} metric anomaly/anomalies flagged (>2 stddev from baseline)."
        )

    if upcoming_expirations["count"] > 0:
        narrative_parts.append(
            f"{upcoming_expirations['count']} subscription(s) expiring in the next 7 days."
        )

    if len(narrative_parts) == 1:
        narrative_parts.append(
            "All systems nominal — no items require immediate attention."
        )

    narrative = " ".join(narrative_parts)

    return {
        "generated_at": generated_at,
        "pending_approvals": pending_approvals,
        "at_risk_users": at_risk_users,
        "anomalies": anomalies,
        "upcoming_expirations": upcoming_expirations,
        "narrative": narrative,
    }


# ---------------------------------------------------------------------------
# Tool 5: classify_and_escalate (SKIL-16, confirm tier)
# ---------------------------------------------------------------------------


async def classify_and_escalate(
    issue_description: str,
    issue_context: dict | None = None,
) -> dict[str, Any]:
    """Score issue severity and route critical/high issues to super_admin.

    Classifies the described issue as critical, high, medium, or low based
    on keyword matching. For HIGH and CRITICAL severity, automatically writes
    an escalation entry to the audit log targeting super_admin. Because this
    tool writes to the audit log, it is CONFIRM tier.

    Autonomy tier: confirm (writes audit log entry for escalations).

    Args:
        issue_description: Free-text description of the issue to classify.
        issue_context: Optional dict with additional context (e.g. affected user
            count, error codes, timestamps).

    Returns:
        Dict with ``severity`` (str), ``confidence`` (float), ``escalated``
        (bool), ``routed_to`` (``"super_admin"`` if escalated else None),
        ``recommended_action`` (str), and ``issue_summary`` (str).
    """
    gate = await _check_autonomy("classify_and_escalate")
    if gate is not None:
        return gate

    desc_lower = issue_description.lower()

    # Score severity from highest to lowest
    severity: str
    confidence: float

    if any(phrase in desc_lower for phrase in _CRITICAL_PHRASES):
        severity = "critical"
        confidence = 0.95
        recommended_action = (
            "CRITICAL: Immediately engage on-call engineering and super-admin. "
            "Begin incident response protocol. Consider rollback if recent deployment."
        )
    elif any(phrase in desc_lower for phrase in _HIGH_PHRASES):
        severity = "high"
        confidence = 0.80
        recommended_action = (
            "HIGH: Investigate within 30 minutes. "
            "Check recent deployments, error logs (sentry_get_issues), "
            "and health metrics (get_api_health_summary). "
            "Escalate to super_admin if not resolved within 1 hour."
        )
    elif any(phrase in desc_lower for phrase in _LOW_PHRASES):
        severity = "low"
        confidence = 0.75
        recommended_action = (
            "LOW: Log for backlog review. No immediate action required. "
            "Address in the next scheduled maintenance window."
        )
    else:
        # Default to medium for unclassified issues
        severity = "medium"
        confidence = 0.60
        recommended_action = (
            "MEDIUM: Investigate within 4 hours. "
            "Check error logs and user reports for patterns. "
            "Escalate to super_admin if impact grows."
        )

    escalated = severity in ("critical", "high")
    routed_to: str | None = "super_admin" if escalated else None

    # Write escalation audit entry for high/critical issues
    if escalated:
        try:
            await log_admin_action(
                admin_user_id=None,
                action="escalate_issue",
                target_type="incident",
                target_id=None,
                details={
                    "severity": severity,
                    "description": issue_description[:500],
                    "context": issue_context,
                    "recommended_action": recommended_action,
                    "routed_to": routed_to,
                },
                source="ai_agent",
            )
        except Exception as exc:
            logger.warning("classify_and_escalate: audit log failed: %s", exc)

    # Build a concise issue summary
    issue_summary = issue_description[:200].strip()
    if len(issue_description) > 200:
        issue_summary += "..."

    return {
        "severity": severity,
        "confidence": confidence,
        "escalated": escalated,
        "routed_to": routed_to,
        "recommended_action": recommended_action,
        "issue_summary": issue_summary,
    }


# ---------------------------------------------------------------------------
# Tool 6: list_all_approvals (auto tier)
# ---------------------------------------------------------------------------


async def list_all_approvals(
    status: str = "PENDING",
    limit: int = 20,
) -> dict[str, Any]:
    """Return the list of approval requests filtered by status.

    Agent-callable equivalent of the ``GET /admin/approvals`` REST endpoint.
    Returns up to ``limit`` rows plus the total count.

    Autonomy tier: auto (read-only query).

    Args:
        status: Filter by approval status. Defaults to ``"PENDING"``.
            Use ``"ALL"`` to retrieve approvals of any status.
        limit: Maximum number of approvals to return (default 20).

    Returns:
        Dict with ``approvals`` (list), ``total`` (int), and ``status_filter`` (str).
    """
    gate = await _check_autonomy("list_all_approvals")
    if gate is not None:
        return gate

    client = get_service_client()
    try:
        base = client.table("approval_requests").select(
            "id, status, user_id, action_name, action_details, created_at, updated_at"
        )
        if status != "ALL":
            base = base.eq("status", status)
        query = base.order("created_at", desc=True).limit(limit)
        result = await execute_async(query, op_name="list_all_approvals")
        rows: list[dict] = result.data or []

        return {
            "approvals": rows,
            "total": len(rows),
            "status_filter": status,
        }

    except Exception as exc:
        logger.error("list_all_approvals failed: %s", exc)
        return {"error": f"Failed to list approvals: {exc}"}


# ---------------------------------------------------------------------------
# Tool 7: override_approval (confirm tier)
# ---------------------------------------------------------------------------


async def override_approval(
    approval_id: str,
    decision: str,
    reason: str | None = None,
    confirmation_token: str | None = None,
) -> dict[str, Any]:
    """Override an approval request status — requires admin confirmation.

    Verifies the approval exists and is PENDING, then updates the status
    to the given decision (APPROVED or REJECTED) and writes an audit entry.
    This tool is CONFIRM tier because it mutates approval state.

    Autonomy tier: confirm (mutates approval_requests table).

    Args:
        approval_id: UUID of the approval request to override.
        decision: New status to set (e.g. ``"APPROVED"`` or ``"REJECTED"``).
        reason: Optional explanation for the override, stored in audit details.
        confirmation_token: Token from the prior confirmation request. Required
            for the mutation to proceed.

    Returns:
        Dict with ``success`` (bool), ``approval_id``, ``new_status``, and
        ``audited`` (bool). Returns ``{"error": str}`` on failure.
    """
    gate = await _check_autonomy("override_approval")
    if gate is not None:
        return gate

    client = get_service_client()
    try:
        # Fetch existing approval
        fetch_query = (
            client.table("approval_requests")
            .select("id, status, user_id, action_name")
            .eq("id", approval_id)
            .limit(1)
        )
        fetch_result = await execute_async(
            fetch_query, op_name="override_approval.fetch"
        )
        rows: list[dict] = fetch_result.data or []

        if not rows:
            return {
                "error": f"Approval request '{approval_id}' not found.",
                "success": False,
            }

        existing = rows[0]
        if existing.get("status") != "PENDING":
            return {
                "error": (
                    f"Approval '{approval_id}' is already '{existing.get('status')}'. "
                    "Only PENDING approvals can be overridden."
                ),
                "success": False,
            }

        # Update status
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        update_query = (
            client.table("approval_requests")
            .update({"status": decision, "updated_at": now_iso})
            .eq("id", approval_id)
        )
        await execute_async(update_query, op_name="override_approval.update")

        # Audit the override
        await log_admin_action(
            admin_user_id=None,
            action="override_approval",
            target_type="approval_request",
            target_id=approval_id,
            details={
                "approval_id": approval_id,
                "previous_status": "PENDING",
                "new_status": decision,
                "reason": reason,
                "action_name": existing.get("action_name"),
            },
            source="admin_override",
        )

        return {
            "success": True,
            "approval_id": approval_id,
            "new_status": decision,
            "audited": True,
        }

    except Exception as exc:
        logger.error("override_approval failed for %s: %s", approval_id, exc)
        return {"error": f"Failed to override approval: {exc}", "success": False}


# ---------------------------------------------------------------------------
# Tool 8: manage_admin_role (confirm tier)
# ---------------------------------------------------------------------------


async def manage_admin_role(
    target_user_id: str,
    role: str,
    action: str = "assign",
    confirmation_token: str | None = None,
) -> dict[str, Any]:
    """Assign or remove an admin role for a user — requires confirmation.

    For ``action="assign"``, upserts a row in the ``user_roles`` table.
    For ``action="remove"``, deletes the matching row. Both operations
    write an audit entry. This tool is CONFIRM tier.

    Autonomy tier: confirm (mutates user_roles table and audit log).

    Args:
        target_user_id: UUID of the user whose role is being changed.
        role: Role name to assign or remove (e.g. ``"admin"``, ``"super_admin"``).
        action: ``"assign"`` (default) or ``"remove"``.
        confirmation_token: Token from the prior confirmation request.

    Returns:
        Dict with ``success`` (bool), ``user_id``, ``role``, ``action``, and
        ``audited`` (bool). Returns ``{"error": str}`` on failure.
    """
    gate = await _check_autonomy("manage_admin_role")
    if gate is not None:
        return gate

    if action not in ("assign", "remove"):
        return {
            "error": f"Invalid action '{action}'. Must be 'assign' or 'remove'.",
            "success": False,
        }

    client = get_service_client()
    try:
        now_iso = datetime.now(tz=timezone.utc).isoformat()

        if action == "assign":
            upsert_query = client.table("user_roles").upsert(
                {
                    "user_id": target_user_id,
                    "role": role,
                    "created_at": now_iso,
                },
                on_conflict="user_id,role",
            )
            await execute_async(upsert_query, op_name="manage_admin_role.upsert")

        else:  # remove
            delete_query = (
                client.table("user_roles")
                .delete()
                .eq("user_id", target_user_id)
                .eq("role", role)
            )
            await execute_async(delete_query, op_name="manage_admin_role.delete")

        # Audit the role change
        await log_admin_action(
            admin_user_id=None,
            action="manage_admin_role",
            target_type="user",
            target_id=target_user_id,
            details={
                "target_user_id": target_user_id,
                "role": role,
                "action": action,
            },
            source="ai_agent",
        )

        return {
            "success": True,
            "user_id": target_user_id,
            "role": role,
            "action": action,
            "audited": True,
        }

    except Exception as exc:
        logger.error(
            "manage_admin_role failed for user %s role %s: %s",
            target_user_id,
            role,
            exc,
        )
        return {"error": f"Failed to manage admin role: {exc}", "success": False}
