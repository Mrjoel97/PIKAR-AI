"""Configuration management tools for the AdminAgent (Phase 12).

Provides 10 tools for reading and writing agent instruction sets, feature
flags, and autonomy permission tiers through the AdminAgent chat interface.

**Autonomy tiers:**

- AUTO: get_agent_config, get_config_history, get_feature_flags,
  get_autonomy_permissions, assess_config_impact, recommend_config_rollback
- CONFIRM: update_agent_config, rollback_agent_config, toggle_feature_flag,
  update_autonomy_permission

All confirm-tier tools accept an optional ``confirmation_token`` parameter.
Without a token the tool returns ``{"requires_confirmation": True, ...}`` and
the AdminAgent surfaces the token to the admin. On the next call the admin
passes the token back and execution proceeds.
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async
from app.workflows.registry import get_workflow_registry

from app.agents.admin.tools._autonomy import check_autonomy as _check_autonomy
import app.services.agent_config_service as agent_config_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent name → workflow registry category mapping (SKIL-07)
# ---------------------------------------------------------------------------

_AGENT_CATEGORY_MAP: dict[str, str] = {
    "financial": "financial",
    "content": "knowledge",
    "marketing": "marketing",
    "strategic": "goals",
    "sales": "sales",
    "hr": "hr",
    "compliance": "compliance",
    "operations": "initiative",
    "data": "evaluation",
    "customer_support": "knowledge",
}

# Valid autonomy tier values
_VALID_AUTONOMY_LEVELS = frozenset({"auto", "confirm", "blocked"})


# ---------------------------------------------------------------------------
# Tool 1: get_agent_config
# ---------------------------------------------------------------------------


async def get_agent_config(agent_name: str) -> dict[str, Any]:
    """Get the current instruction set and version for a named agent.

    Autonomy tier: auto (read-only).

    Args:
        agent_name: The agent to query (e.g. "financial", "marketing").

    Returns:
        Dict with ``agent_name``, ``current_instructions``, ``version``, and
        ``updated_at``, or ``{"error": str}`` on failure or blocked tier.
    """
    gate = await _check_autonomy("get_agent_config")
    if gate is not None:
        return gate

    try:
        config = await agent_config_service.get_agent_config(agent_name)
        if config is None:
            return {"error": f"No config found for agent '{agent_name}'"}
        return config
    except Exception as exc:
        logger.error("get_agent_config failed for %s: %s", agent_name, exc)
        return {"error": f"Failed to get config for '{agent_name}': {exc}"}


# ---------------------------------------------------------------------------
# Tool 2: update_agent_config
# ---------------------------------------------------------------------------


async def update_agent_config(
    agent_name: str,
    new_instructions: str,
    confirmation_token: str | None = None,
) -> dict[str, Any]:
    """Update agent instruction set with injection validation and diff generation.

    Autonomy tier: confirm. Without ``confirmation_token`` returns a
    confirmation request. With token, validates the instruction text and
    persists the update.

    Args:
        agent_name: The agent whose instructions to update.
        new_instructions: The new instruction text (will be injection-validated).
        confirmation_token: Token from a prior confirmation request. Required
            to actually execute the update.

    Returns:
        Without token: ``{"requires_confirmation": True, ...}`` dict.
        With token and valid text: ``{"agent_name", "version", "diff", "status"}``.
        With token and injection content: ``{"error": ..., "violations": [...]}``.
    """
    gate = await _check_autonomy("update_agent_config")
    if gate is not None and confirmation_token is None:
        return gate

    try:
        result = await agent_config_service.save_agent_config(
            agent_name=agent_name,
            new_instructions=new_instructions,
        )
        return result
    except Exception as exc:
        logger.error("update_agent_config failed for %s: %s", agent_name, exc)
        return {"error": f"Failed to update config for '{agent_name}': {exc}"}


# ---------------------------------------------------------------------------
# Tool 3: get_config_history
# ---------------------------------------------------------------------------


async def get_config_history(
    agent_name: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Return configuration change history ordered newest-first.

    Autonomy tier: auto (read-only).

    Args:
        agent_name: Filter to changes for a specific agent. None returns all.
        limit: Maximum number of rows to return (default 20).

    Returns:
        List of history dicts, or ``{"error": str}`` if blocked.
    """
    gate = await _check_autonomy("get_config_history")
    if gate is not None:
        return gate

    try:
        return await agent_config_service.get_config_history(
            agent_name=agent_name, limit=limit
        )
    except Exception as exc:
        logger.error("get_config_history failed: %s", exc)
        return {"error": f"Failed to get config history: {exc}"}


# ---------------------------------------------------------------------------
# Tool 4: rollback_agent_config
# ---------------------------------------------------------------------------


async def rollback_agent_config(
    history_id: str,
    agent_name: str,
    confirmation_token: str | None = None,
) -> dict[str, Any]:
    """Restore a previous agent instruction version from history.

    Autonomy tier: confirm. Without ``confirmation_token`` returns a
    confirmation request.

    Args:
        history_id: UUID of the ``admin_config_history`` row to restore from.
        agent_name: Agent name being rolled back (for validation).
        confirmation_token: Token from a prior confirmation request.

    Returns:
        Without token: ``{"requires_confirmation": True, ...}`` dict.
        With token: Result from ``save_agent_config`` or error dict.
    """
    gate = await _check_autonomy("rollback_agent_config")
    if gate is not None and confirmation_token is None:
        return gate

    try:
        return await agent_config_service.rollback_agent_config(
            history_id=history_id,
            agent_name=agent_name,
            changed_by=None,
        )
    except Exception as exc:
        logger.error(
            "rollback_agent_config failed for %s / %s: %s", history_id, agent_name, exc
        )
        return {"error": f"Failed to rollback config: {exc}"}


# ---------------------------------------------------------------------------
# Tool 5: get_feature_flags
# ---------------------------------------------------------------------------


async def get_feature_flags() -> list[dict[str, Any]] | dict[str, Any]:
    """Return all feature flags with their current enabled state.

    Autonomy tier: auto (read-only).

    Returns:
        List of flag dicts (``flag_key``, ``is_enabled``, ``description``,
        ``updated_at``), or ``{"error": str}`` if blocked.
    """
    gate = await _check_autonomy("get_feature_flags")
    if gate is not None:
        return gate

    try:
        client = get_service_client()
        result = (
            client.table("admin_feature_flags")
            .select("flag_key, is_enabled, description, updated_at")
            .order("flag_key")
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.error("get_feature_flags failed: %s", exc)
        return {"error": f"Failed to get feature flags: {exc}"}


# ---------------------------------------------------------------------------
# Tool 6: toggle_feature_flag
# ---------------------------------------------------------------------------


async def toggle_feature_flag(
    flag_key: str,
    enabled: bool,
    confirmation_token: str | None = None,
) -> dict[str, Any]:
    """Enable or disable a feature flag by key.

    Autonomy tier: confirm. Toggles DB state and invalidates Redis cache.

    Args:
        flag_key: The feature flag key to toggle.
        enabled: The desired new state.
        confirmation_token: Token from a prior confirmation request.

    Returns:
        Without token: ``{"requires_confirmation": True, ...}`` dict.
        With token: ``{"flag_key", "is_enabled", "status"}`` on success.
    """
    gate = await _check_autonomy("toggle_feature_flag")
    if gate is not None and confirmation_token is None:
        return gate

    try:
        return await agent_config_service.set_flag(
            key=flag_key, enabled=enabled, changed_by=None
        )
    except Exception as exc:
        logger.error("toggle_feature_flag failed for %s: %s", flag_key, exc)
        return {"error": f"Failed to toggle flag '{flag_key}': {exc}"}


# ---------------------------------------------------------------------------
# Tool 7: get_autonomy_permissions
# ---------------------------------------------------------------------------


async def get_autonomy_permissions(
    category: str | None = None,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Return all autonomy permission rows from admin_agent_permissions.

    Autonomy tier: auto (read-only).

    Args:
        category: Optional action category filter (e.g. "monitoring").

    Returns:
        List of permission row dicts, or ``{"error": str}`` if blocked.
    """
    gate = await _check_autonomy("get_autonomy_permissions")
    if gate is not None:
        return gate

    try:
        client = get_service_client()
        query = (
            client.table("admin_agent_permissions")
            .select("action_name, action_category, autonomy_level, description")
            .order("action_category")
            .order("action_name")
        )
        if category is not None:
            query = query.eq("action_category", category)
        result = query.execute()
        return result.data or []
    except Exception as exc:
        logger.error("get_autonomy_permissions failed: %s", exc)
        return {"error": f"Failed to get autonomy permissions: {exc}"}


# ---------------------------------------------------------------------------
# Tool 8: update_autonomy_permission
# ---------------------------------------------------------------------------


async def update_autonomy_permission(
    action_name: str,
    new_level: str,
    confirmation_token: str | None = None,
) -> dict[str, Any]:
    """Change the autonomy tier for an admin action.

    Autonomy tier: confirm.

    Args:
        action_name: The ``action_name`` in ``admin_agent_permissions``.
        new_level: One of "auto", "confirm", or "blocked".
        confirmation_token: Token from a prior confirmation request.

    Returns:
        Without token: ``{"requires_confirmation": True, ...}`` dict.
        With invalid level: ``{"error": str}``.
        With token and valid level: ``{"action_name", "autonomy_level", "status"}``.
    """
    # Validate level first (before gate check — invalid input is immediate error)
    if new_level not in _VALID_AUTONOMY_LEVELS:
        return {
            "error": (
                f"Invalid autonomy level '{new_level}'. "
                f"Must be one of: {', '.join(sorted(_VALID_AUTONOMY_LEVELS))}"
            )
        }

    gate = await _check_autonomy("update_autonomy_permission")
    if gate is not None and confirmation_token is None:
        return gate

    try:
        client = get_service_client()
        client.table("admin_agent_permissions").update(
            {"autonomy_level": new_level}
        ).eq("action_name", action_name).execute()
        return {
            "action_name": action_name,
            "autonomy_level": new_level,
            "status": "updated",
        }
    except Exception as exc:
        logger.error(
            "update_autonomy_permission failed for %s: %s", action_name, exc
        )
        return {"error": f"Failed to update autonomy for '{action_name}': {exc}"}


# ---------------------------------------------------------------------------
# Tool 9: assess_config_impact (SKIL-07)
# ---------------------------------------------------------------------------


async def assess_config_impact(agent_name: str) -> dict[str, Any]:
    """Assess the blast radius of a config change for a named agent.

    Queries the WorkflowRegistry to find workflows that use the target agent
    and queries agent_telemetry for the 7-day call volume. Returns a risk
    assessment to help the admin decide whether to proceed with the change.

    Autonomy tier: auto (SKIL-07).

    Args:
        agent_name: The agent name to assess (e.g. "financial").

    Returns:
        Dict with ``agent_name``, ``workflows_using_agent``, ``workflow_count``,
        ``calls_last_7_days``, and ``risk_assessment`` ("HIGH"/"MEDIUM"/"LOW").
    """
    gate = await _check_autonomy("assess_config_impact")
    if gate is not None:
        return gate

    try:
        registry = get_workflow_registry()
        category = _AGENT_CATEGORY_MAP.get(agent_name.lower())
        workflows_using_agent: list[str] = []
        if category:
            workflows_using_agent = registry.list_by_category(category)

        # Query 7-day call volume from agent_telemetry
        client = get_service_client()
        telem_result = (
            client.table("agent_telemetry")
            .select("agent_name, status")
            .eq("agent_name", agent_name)
            .gte("created_at", "now() - interval '7 days'")
            .execute()
        )
        call_count = len(telem_result.data or [])

        risk_assessment: str
        if call_count > 100:
            risk_assessment = "HIGH"
        elif call_count > 20:
            risk_assessment = "MEDIUM"
        else:
            risk_assessment = "LOW"

        return {
            "agent_name": agent_name,
            "workflows_using_agent": workflows_using_agent,
            "workflow_count": len(workflows_using_agent),
            "calls_last_7_days": call_count,
            "risk_assessment": risk_assessment,
        }
    except Exception as exc:
        logger.error("assess_config_impact failed for %s: %s", agent_name, exc)
        return {"error": f"Failed to assess impact for '{agent_name}': {exc}"}


# ---------------------------------------------------------------------------
# Tool 10: recommend_config_rollback (SKIL-08)
# ---------------------------------------------------------------------------


def _agg_stats(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Aggregate daily stats rows into a summary dict.

    Args:
        rows: List of ``admin_agent_stats_daily`` row dicts.

    Returns:
        Aggregated ``{"success_rate", "avg_duration_ms", "total_calls"}`` dict,
        or None when the rows list is empty.
    """
    if not rows:
        return None
    total = sum(r.get("total_calls", 0) for r in rows) or 1
    errors = sum(r.get("error_count", 0) for r in rows)
    durations = [r["avg_duration_ms"] for r in rows if r.get("avg_duration_ms") is not None]
    return {
        "success_rate": round(1 - errors / total, 3),
        "avg_duration_ms": round(sum(durations) / len(durations), 1) if durations else None,
        "total_calls": total,
    }


async def recommend_config_rollback(agent_name: str) -> dict[str, Any]:
    """Compare pre/post config-change metrics and recommend rollback if needed.

    Queries ``admin_config_history`` for the most recent instruction change for
    the agent, then computes 7-day pre-change and post-change success rate
    windows from ``admin_agent_stats_daily``. Recommends rollback when success
    rate drops more than 5%.

    Autonomy tier: auto (SKIL-08).

    Args:
        agent_name: The agent to analyse (e.g. "financial").

    Returns:
        Dict with ``agent_name``, ``last_config_change``, ``pre_change_stats``,
        ``post_change_stats``, ``recommend_rollback``, ``reason``, and
        ``rollback_history_id``.
    """
    gate = await _check_autonomy("recommend_config_rollback")
    if gate is not None:
        return gate

    try:
        client = get_service_client()

        # Find the most recent agent_instruction change for this agent
        hist_result = (
            client.table("admin_config_history")
            .select("created_at, new_value, previous_value, id")
            .eq("config_type", "agent_instruction")
            .eq("config_key", agent_name)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not hist_result.data:
            return {"recommendation": "no_config_change_found", "agent_name": agent_name}

        change_row = hist_result.data[0]
        change_at: str = change_row["created_at"]
        change_date = change_at[:10]  # YYYY-MM-DD

        # Pre-change: up to 7 days before the change
        pre_result = (
            client.table("admin_agent_stats_daily")
            .select("success_count, error_count, avg_duration_ms, total_calls")
            .eq("agent_name", agent_name)
            .lt("stat_date", change_date)
            .order("stat_date", desc=True)
            .limit(7)
            .execute()
        )

        # Post-change: since the change date
        post_result = (
            client.table("admin_agent_stats_daily")
            .select("success_count, error_count, avg_duration_ms, total_calls")
            .eq("agent_name", agent_name)
            .gte("stat_date", change_date)
            .execute()
        )

        pre_stats = _agg_stats(pre_result.data or [])
        post_stats = _agg_stats(post_result.data or [])

        recommend_rollback = False
        reason = "Insufficient data for comparison"
        if (
            pre_stats is not None
            and post_stats is not None
            and post_stats["total_calls"] >= 5
        ):
            sr_delta = post_stats["success_rate"] - pre_stats["success_rate"]
            reason = (
                f"Success rate changed {sr_delta:+.1%} since config change on {change_date}"
            )
            recommend_rollback = sr_delta < -0.05

        return {
            "agent_name": agent_name,
            "last_config_change": change_at,
            "pre_change_stats": pre_stats,
            "post_change_stats": post_stats,
            "recommend_rollback": recommend_rollback,
            "reason": reason,
            "rollback_history_id": change_row["id"] if recommend_rollback else None,
        }
    except Exception as exc:
        logger.error("recommend_config_rollback failed for %s: %s", agent_name, exc)
        return {"error": f"Failed to recommend rollback for '{agent_name}': {exc}"}
