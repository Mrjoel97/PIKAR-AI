"""Admin config REST API — agent instructions, feature flags, autonomy permissions, MCP.

Provides 11 endpoints under ``/admin/config/``:

- GET  /config/agents                         — list all agent configs (summary)
- GET  /config/agents/{agent_name}            — full config with instructions
- POST /config/agents/{agent_name}/preview-diff — diff without saving
- PUT  /config/agents/{agent_name}            — save updated instructions
- GET  /config/agents/{agent_name}/history    — version history
- POST /config/agents/{agent_name}/rollback   — restore previous version
- GET  /config/flags                          — list all feature flags
- PUT  /config/flags/{flag_key}               — toggle a feature flag
- GET  /config/permissions                    — list all autonomy permissions
- PUT  /config/permissions/{action_name}      — update autonomy tier
- GET  /config/mcp-endpoints                  — MCP endpoint configs (read-only)

All endpoints require admin authentication via ``require_admin`` dependency.
All write operations validate input before persisting.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.middleware.admin_auth import require_admin
from app.middleware.rate_limiter import limiter
from app.services.agent_config_service import (
    generate_instruction_diff,
    get_agent_config,
    get_config_history,
    rollback_agent_config,
    save_agent_config,
    set_flag,
)
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter()

_VALID_AUTONOMY_LEVELS = frozenset({"auto", "confirm", "blocked"})


# ---------------------------------------------------------------------------
# Pydantic request body models
# ---------------------------------------------------------------------------


class AgentConfigUpdateBody(BaseModel):
    """Request body for PUT /config/agents/{agent_name}."""

    new_instructions: str


class PreviewDiffBody(BaseModel):
    """Request body for POST /config/agents/{agent_name}/preview-diff."""

    proposed_instructions: str


class RollbackBody(BaseModel):
    """Request body for POST /config/agents/{agent_name}/rollback."""

    history_id: str


class FlagToggleBody(BaseModel):
    """Request body for PUT /config/flags/{flag_key}."""

    is_enabled: bool


class PermissionUpdateBody(BaseModel):
    """Request body for PUT /config/permissions/{action_name}."""

    autonomy_level: str


# ---------------------------------------------------------------------------
# Agent config endpoints
# ---------------------------------------------------------------------------


@router.get("/config/agents")
@limiter.limit("120/minute")
async def list_agent_configs(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> list[dict[str, Any]]:
    """Return a summary of all agent configs (no full instruction text).

    Excludes ``current_instructions`` from list view for readability —
    use GET /config/agents/{agent_name} for the full config.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin.

    Returns:
        List of dicts with ``agent_name``, ``version``, ``updated_at``.
    """
    client = get_service_client()
    try:
        result = await execute_async(
            client.table("admin_agent_configs")
            .select("agent_name, version, updated_at")
            .order("agent_name"),
            op_name="list_agent_configs",
        )
        return result.data or []
    except Exception as exc:
        logger.error("list_agent_configs failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list agent configs") from exc


@router.get("/config/agents/{agent_name}")
@limiter.limit("120/minute")
async def get_agent_config_detail(
    request: Request,
    agent_name: str,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict[str, Any]:
    """Return the full agent config including current instruction text.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        agent_name: The agent to retrieve.
        admin_user: Injected by require_admin.

    Returns:
        Full config dict with ``current_instructions``.

    Raises:
        HTTPException 404: If no config row exists for this agent.
    """
    try:
        config = await get_agent_config(agent_name)
        if config is None:
            raise HTTPException(
                status_code=404,
                detail=f"No config found for agent '{agent_name}'",
            )
        return config
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_agent_config_detail failed for %s: %s", agent_name, exc)
        raise HTTPException(status_code=500, detail="Failed to get agent config") from exc


@router.post("/config/agents/{agent_name}/preview-diff")
@limiter.limit("120/minute")
async def preview_diff(
    request: Request,
    agent_name: str,
    body: PreviewDiffBody,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict[str, str]:
    """Return unified diff of proposed vs current instructions without saving.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        agent_name: The agent whose current instructions to diff against.
        body: PreviewDiffBody with proposed_instructions.
        admin_user: Injected by require_admin.

    Returns:
        ``{"diff": str}`` — unified diff string (empty if no changes).
    """
    try:
        current = await get_agent_config(agent_name)
        current_text = current["current_instructions"] if current else ""
        diff = generate_instruction_diff(current_text, body.proposed_instructions)
        return {"diff": diff}
    except Exception as exc:
        logger.error("preview_diff failed for %s: %s", agent_name, exc)
        raise HTTPException(status_code=500, detail="Failed to generate diff") from exc


@router.put("/config/agents/{agent_name}")
@limiter.limit("120/minute")
async def update_agent_config_endpoint(
    request: Request,
    agent_name: str,
    body: AgentConfigUpdateBody,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict[str, Any]:
    """Save updated instructions for an agent (with injection validation).

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        agent_name: The agent whose instructions to update.
        body: AgentConfigUpdateBody with new_instructions.
        admin_user: Injected by require_admin.

    Returns:
        Updated config result with ``agent_name``, ``version``, ``diff``, ``status``.

    Raises:
        HTTPException 422: If injection validation fails.
    """
    admin_user_id: str | None = admin_user.get("id")
    try:
        result = await save_agent_config(
            agent_name=agent_name,
            new_instructions=body.new_instructions,
            changed_by=admin_user_id,
        )
        if "error" in result:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": result["error"],
                    "violations": result.get("violations", []),
                },
            )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("update_agent_config_endpoint failed for %s: %s", agent_name, exc)
        raise HTTPException(status_code=500, detail="Failed to update agent config") from exc


@router.get("/config/agents/{agent_name}/history")
@limiter.limit("120/minute")
async def get_agent_history(
    request: Request,
    agent_name: str,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> list[dict[str, Any]]:
    """Return version history for an agent's instruction changes.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        agent_name: The agent to query history for.
        admin_user: Injected by require_admin.

    Returns:
        List of history row dicts ordered newest-first.
    """
    try:
        return await get_config_history(agent_name=agent_name, config_type="agent_instruction")
    except Exception as exc:
        logger.error("get_agent_history failed for %s: %s", agent_name, exc)
        raise HTTPException(status_code=500, detail="Failed to get config history") from exc


@router.post("/config/agents/{agent_name}/rollback")
@limiter.limit("120/minute")
async def rollback_agent_config_endpoint(
    request: Request,
    agent_name: str,
    body: RollbackBody,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict[str, Any]:
    """Restore a previous agent instruction version.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        agent_name: The agent to rollback.
        body: RollbackBody with history_id.
        admin_user: Injected by require_admin.

    Returns:
        Result from save_agent_config (same shape as PUT endpoint).

    Raises:
        HTTPException 422: If validation of the restored text fails.
    """
    admin_user_id: str | None = admin_user.get("id")
    try:
        result = await rollback_agent_config(
            history_id=body.history_id,
            agent_name=agent_name,
            changed_by=admin_user_id,
        )
        if "error" in result:
            raise HTTPException(status_code=422, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "rollback_agent_config_endpoint failed for %s: %s", agent_name, exc
        )
        raise HTTPException(status_code=500, detail="Failed to rollback agent config") from exc


# ---------------------------------------------------------------------------
# Feature flag endpoints
# ---------------------------------------------------------------------------


@router.get("/config/flags")
@limiter.limit("120/minute")
async def list_feature_flags(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> list[dict[str, Any]]:
    """Return all feature flags with their current enabled state.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin.

    Returns:
        List of flag dicts (``flag_key``, ``is_enabled``, ``description``,
        ``updated_at``).
    """
    client = get_service_client()
    try:
        result = await execute_async(
            client.table("admin_feature_flags")
            .select("flag_key, is_enabled, description, updated_at")
            .order("flag_key"),
            op_name="list_feature_flags",
        )
        return result.data or []
    except Exception as exc:
        logger.error("list_feature_flags failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list feature flags") from exc


@router.put("/config/flags/{flag_key}")
@limiter.limit("120/minute")
async def toggle_flag_endpoint(
    request: Request,
    flag_key: str,
    body: FlagToggleBody,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict[str, Any]:
    """Enable or disable a feature flag.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        flag_key: The flag key to toggle.
        body: FlagToggleBody with is_enabled.
        admin_user: Injected by require_admin.

    Returns:
        Updated flag dict (``flag_key``, ``is_enabled``, ``status``).
    """
    admin_user_id: str | None = admin_user.get("id")
    try:
        return await set_flag(key=flag_key, enabled=body.is_enabled, changed_by=admin_user_id)
    except Exception as exc:
        logger.error("toggle_flag_endpoint failed for %s: %s", flag_key, exc)
        raise HTTPException(status_code=500, detail=f"Failed to toggle flag '{flag_key}'") from exc


# ---------------------------------------------------------------------------
# Autonomy permission endpoints
# ---------------------------------------------------------------------------


@router.get("/config/permissions")
@limiter.limit("120/minute")
async def list_autonomy_permissions(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> list[dict[str, Any]]:
    """Return all admin action autonomy permission rows.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin.

    Returns:
        List of permission dicts ordered by category and action name.
    """
    client = get_service_client()
    try:
        result = await execute_async(
            client.table("admin_agent_permissions")
            .select("action_name, action_category, autonomy_level, description")
            .order("action_category")
            .order("action_name"),
            op_name="list_autonomy_permissions",
        )
        return result.data or []
    except Exception as exc:
        logger.error("list_autonomy_permissions failed: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to list autonomy permissions"
        ) from exc


@router.put("/config/permissions/{action_name}")
@limiter.limit("120/minute")
async def update_permission_endpoint(
    request: Request,
    action_name: str,
    body: PermissionUpdateBody,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict[str, Any]:
    """Change the autonomy tier for an admin action.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        action_name: The action to update.
        body: PermissionUpdateBody with autonomy_level.
        admin_user: Injected by require_admin.

    Returns:
        Updated permission dict (``action_name``, ``autonomy_level``, ``status``).

    Raises:
        HTTPException 422: If autonomy_level is not "auto", "confirm", or "blocked".
    """
    if body.autonomy_level not in _VALID_AUTONOMY_LEVELS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid autonomy_level '{body.autonomy_level}'. "
                f"Must be one of: {', '.join(sorted(_VALID_AUTONOMY_LEVELS))}"
            ),
        )

    admin_user_id: str | None = admin_user.get("id")
    client = get_service_client()
    try:
        # Update the permission row
        await execute_async(
            client.table("admin_agent_permissions")
            .update({"autonomy_level": body.autonomy_level})
            .eq("action_name", action_name),
            op_name=f"update_permission.{action_name}",
        )

        # Write an audit record in config history
        import json

        history_data: dict[str, Any] = {
            "config_type": "autonomy_permission",
            "config_key": action_name,
            "new_value": json.dumps({"autonomy_level": body.autonomy_level}),
            "change_source": "admin_api",
        }
        if admin_user_id:
            history_data["changed_by"] = admin_user_id

        await execute_async(
            client.table("admin_config_history").insert(history_data),
            op_name=f"update_permission.history.{action_name}",
        )

        return {
            "action_name": action_name,
            "autonomy_level": body.autonomy_level,
            "status": "updated",
        }
    except Exception as exc:
        logger.error("update_permission_endpoint failed for %s: %s", action_name, exc)
        raise HTTPException(
            status_code=500, detail=f"Failed to update permission for '{action_name}'"
        ) from exc


# ---------------------------------------------------------------------------
# MCP endpoints (CONF-05 — read-only view)
# ---------------------------------------------------------------------------


@router.get("/config/mcp-endpoints")
@limiter.limit("120/minute")
async def list_mcp_endpoints(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> list[dict[str, Any]]:
    """Return current MCP server endpoint configurations (read-only).

    Provides a read-only view of configured MCP integrations. Full CRUD for
    MCP endpoints is deferred to when additional MCP servers are added beyond
    the initial Stitch integration.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin.

    Returns:
        List of MCP endpoint config dicts.
    """
    # Read the Stitch MCP config from the environment to derive the base URL.
    # For now, return a static representation derived from StitchMCPService config.
    try:
        import os

        stitch_url = os.environ.get("STITCH_MCP_URL", "https://stitch.google.com/mcp")
        stitch_enabled = bool(os.environ.get("STITCH_API_KEY"))
        return [
            {
                "name": "stitch",
                "display_name": "Google Stitch",
                "url": stitch_url,
                "status": "active" if stitch_enabled else "unconfigured",
                "description": "UI generation via Google Stitch MCP",
                "capabilities": ["generate_screen", "generate_device_variant"],
            }
        ]
    except Exception as exc:
        logger.error("list_mcp_endpoints failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list MCP endpoints") from exc
