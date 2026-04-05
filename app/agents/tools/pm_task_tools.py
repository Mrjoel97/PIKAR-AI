# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""PM task agent tools -- Linear and Asana integration for OperationsAgent.

Provides 5 agent-callable functions that bridge the agent to real PM
platform APIs (LinearService, AsanaService) and bidirectional sync
(PMSyncService). Provider auto-detection picks the connected tool
automatically when only one is configured; prompts for clarification
when both are connected.

Loop prevention uses the Redis skip-flag pattern (same as HubSpot):
  pikar:pm:skip:{provider}:{external_id}  TTL=30s

All tools use lazy imports and get_current_user_id() from request context.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_user_id() -> str | None:
    """Extract the current user ID from the request-scoped context."""
    from app.services.request_context import get_current_user_id

    return get_current_user_id()


async def _detect_provider(
    provider: str | None = None,
) -> tuple[str | None, str | None]:
    """Auto-detect PM provider from connected integrations.

    Args:
        provider: Explicit provider hint (``"linear"`` or ``"asana"``).
            When given, returned as-is without any credential check.

    Returns:
        ``(provider_key, error_message)`` — exactly one is non-None.
    """
    if provider:
        return provider, None

    user_id = _get_user_id()
    if not user_id:
        return None, "Authentication required."

    from app.services.integration_manager import IntegrationManager

    mgr = IntegrationManager()
    linear_creds = await mgr.get_credentials(user_id, "linear")
    asana_creds = await mgr.get_credentials(user_id, "asana")

    has_linear = bool(linear_creds)
    has_asana = bool(asana_creds)

    if has_linear and not has_asana:
        return "linear", None
    if has_asana and not has_linear:
        return "asana", None
    if has_linear and has_asana:
        return (
            None,
            "Both Linear and Asana are connected. "
            "Please specify: provider='linear' or provider='asana'",
        )
    return (
        None,
        "No PM tool connected. Connect Linear or Asana in Settings > Configuration.",
    )


# ---------------------------------------------------------------------------
# Tool 1: get_pm_projects
# ---------------------------------------------------------------------------


async def get_pm_projects(provider: str = None) -> dict[str, Any]:
    """List available projects from the connected PM tool.

    For Linear, returns teams. For Asana, returns workspaces and their
    active projects. Auto-detects the connected provider when ``provider``
    is omitted.

    Args:
        provider: ``"linear"`` or ``"asana"``. Omit to auto-detect.

    Returns:
        Dict with ``provider``, ``projects`` list (``{id, name}``), and
        ``count``. On error: ``{"error": str}``.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    detected, err = await _detect_provider(provider)
    if err:
        return {"error": err}

    try:
        if detected == "linear":
            from app.services.linear_service import LinearService

            svc = LinearService()
            teams = await svc.list_teams(user_id)
            projects = [
                {
                    "id": t.get("id", ""),
                    "name": t.get("name", ""),
                    "key": t.get("key", ""),
                }
                for t in teams
            ]
            return {
                "success": True,
                "provider": "linear",
                "projects": projects,
                "count": len(projects),
            }

        # Asana: enumerate workspaces then their projects
        from app.services.asana_service import AsanaService

        svc = AsanaService()
        workspaces = await svc.list_workspaces(user_id)
        projects: list[dict[str, Any]] = []
        for ws in workspaces:
            ws_projects = await svc.list_projects(
                user_id=user_id, workspace_id=ws.get("gid", "")
            )
            for p in ws_projects:
                projects.append(
                    {
                        "id": p.get("gid", ""),
                        "name": p.get("name", ""),
                        "workspace": ws.get("name", ""),
                    }
                )

        return {
            "success": True,
            "provider": "asana",
            "projects": projects,
            "count": len(projects),
        }

    except Exception as exc:
        logger.exception("get_pm_projects failed for user=%s", user_id)
        return {"error": f"Failed to fetch projects: {exc}"}


# ---------------------------------------------------------------------------
# Tool 2: list_pm_tasks
# ---------------------------------------------------------------------------


async def list_pm_tasks(
    project: str = None,
    status: str = None,
    provider: str = None,
    limit: int = 50,
) -> dict[str, Any]:
    """List synced PM tasks from the local synced_tasks table.

    Queries already-synced tasks; does not make a live API call. Run
    ``get_pm_sync_status`` or ask the user to configure sync in Settings
    if no tasks appear.

    Args:
        project: Optional external project/team ID filter.
        status: Optional Pikar status filter (``"pending"``,
            ``"in_progress"``, ``"completed"``, ``"cancelled"``).
        provider: ``"linear"`` or ``"asana"``. Omit to auto-detect.
        limit: Maximum tasks to return (default 50).

    Returns:
        Dict with ``tasks`` list, ``count``, and ``provider``.
        On error: ``{"error": str}``.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    detected, err = await _detect_provider(provider)
    if err:
        return {"error": err}

    try:
        from app.services.base_service import AdminService
        from app.services.supabase_async import execute_async

        admin = AdminService()
        query = (
            admin.client.table("synced_tasks")
            .select(
                "id, external_id, external_project_id, provider, "
                "title, description, status, priority, assignee, "
                "labels, external_url, created_at, updated_at"
            )
            .eq("user_id", user_id)
            .eq("provider", detected)
            .limit(limit)
        )

        if project:
            query = query.eq("external_project_id", project)
        if status:
            query = query.eq("status", status)

        result = await execute_async(query, op_name="pm_tools.list_pm_tasks")
        tasks: list[dict[str, Any]] = result.data or []

        if not tasks:
            return {
                "success": True,
                "provider": detected,
                "tasks": [],
                "count": 0,
                "hint": (
                    "No synced tasks found. "
                    "Configure project sync in Settings > Configuration, "
                    "then expand the Linear or Asana card to select projects."
                ),
            }

        return {
            "success": True,
            "provider": detected,
            "tasks": tasks,
            "count": len(tasks),
        }

    except Exception as exc:
        logger.exception("list_pm_tasks failed for user=%s", user_id)
        return {"error": f"Failed to list PM tasks: {exc}"}


# ---------------------------------------------------------------------------
# Tool 3: create_pm_task
# ---------------------------------------------------------------------------


async def create_pm_task(
    title: str,
    description: str,
    project: str,
    provider: str = None,
    priority: str = "medium",
    labels: list[str] = None,
) -> dict[str, Any]:
    """Create a task simultaneously in the external PM tool and locally.

    Sets the Redis skip-flag before creation to prevent the inbound
    webhook from double-importing the task.  After creation the task is
    stored in ``synced_tasks`` with the external issue ID linked.

    Args:
        title: Task title.
        description: Task description.
        project: External project or team ID (use ``get_pm_projects`` to
            find valid IDs).
        provider: ``"linear"`` or ``"asana"``. Omit to auto-detect.
        priority: ``"urgent"``, ``"high"``, ``"medium"`` (default),
            ``"low"``, or ``"none"``.
        labels: Optional list of label names (ignored for Asana).

    Returns:
        Dict with ``task`` (local record), ``external_url``, ``provider``.
        On error: ``{"error": str}``.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    detected, err = await _detect_provider(provider)
    if err:
        return {"error": err}

    # Map Pikar priority strings to Linear priority integers
    priority_map_to_linear = {
        "none": 0,
        "urgent": 1,
        "high": 2,
        "medium": 3,
        "low": 4,
    }

    try:
        external_id: str = ""
        external_url: str = ""

        if detected == "linear":
            from app.services.linear_service import LinearService

            linear_svc = LinearService()
            linear_priority = priority_map_to_linear.get(priority, 3)
            issue = await linear_svc.create_issue(
                user_id=user_id,
                team_id=project,
                title=title,
                description=description,
                priority=linear_priority,
            )
            external_id = issue.get("id", "")
            external_url = issue.get("url", "")

        else:  # asana
            from app.services.asana_service import AsanaService

            asana_svc = AsanaService()
            task = await asana_svc.create_task(
                user_id=user_id,
                project_id=project,
                name=title,
                notes=description,
            )
            external_id = task.get("gid", "")
            external_url = task.get("permalink_url", "")

        if not external_id:
            return {
                "success": False,
                "error": (
                    "External PM tool returned no ID "
                    "— task may not have been created."
                ),
            }

        # Set skip-flag before writing locally to suppress webhook echo
        from app.services.pm_sync_service import PMSyncService

        sync_svc = PMSyncService()
        await sync_svc._set_skip_flag(detected, external_id)

        # Persist in synced_tasks
        from app.services.base_service import AdminService
        from app.services.supabase_async import execute_async

        admin = AdminService()
        row: dict[str, Any] = {
            "user_id": user_id,
            "external_id": external_id,
            "provider": detected,
            "external_project_id": project,
            "title": title,
            "description": description,
            "status": "pending",
            "priority": priority,
            "labels": labels or [],
            "external_url": external_url,
        }

        result = await execute_async(
            admin.client.table("synced_tasks").insert(row),
            op_name="pm_tools.create_pm_task.insert",
        )
        local_task: dict[str, Any] = (
            result.data[0] if result.data else row
        )

        logger.info(
            "pm_tools.create_pm_task: user=%s provider=%s external_id=%s",
            user_id,
            detected,
            external_id,
        )
        return {
            "success": True,
            "provider": detected,
            "task": local_task,
            "external_url": external_url,
            "external_id": external_id,
            "message": (
                f"Task created in {detected.title()} and synced locally. "
                f"View at: {external_url}"
            ),
        }

    except Exception as exc:
        logger.exception("create_pm_task failed for user=%s", user_id)
        return {"error": f"Failed to create PM task: {exc}"}


# ---------------------------------------------------------------------------
# Tool 4: update_pm_task
# ---------------------------------------------------------------------------


async def update_pm_task(
    task_id: str,
    status: str = None,
    title: str = None,
    description: str = None,
    priority: str = None,
) -> dict[str, Any]:
    """Update a synced PM task in both Pikar and the external PM tool.

    Reads the ``synced_tasks`` record to find provider + external_id, then
    delegates to ``PMSyncService.sync_to_external`` which sets the Redis
    skip-flag before calling the PM API.

    Args:
        task_id: Pikar ``synced_tasks`` row UUID.
        status: New Pikar status (``"pending"``, ``"in_progress"``,
            ``"completed"``, or ``"cancelled"``).
        title: New task title.
        description: New task description.
        priority: New priority (``"urgent"``, ``"high"``, ``"medium"``,
            ``"low"``, or ``"none"``).

    Returns:
        Dict with ``success``, ``task_id``, ``provider``, ``external_id``,
        and ``api_result`` from the PM tool.
        On error: ``{"error": str}``.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    updates: dict[str, Any] = {}
    if status is not None:
        updates["status"] = status
    if title is not None:
        updates["title"] = title
    if description is not None:
        updates["description"] = description
    if priority is not None:
        updates["priority"] = priority

    if not updates:
        return {"success": False, "error": "No updates provided."}

    try:
        from app.services.pm_sync_service import PMSyncService

        sync_svc = PMSyncService()
        api_result = await sync_svc.sync_to_external(
            user_id=user_id,
            task_id=task_id,
            updates=updates,
        )

        # Also update the local synced_tasks record
        from app.services.base_service import AdminService
        from app.services.supabase_async import execute_async

        admin = AdminService()
        await execute_async(
            admin.client.table("synced_tasks")
            .update(updates)
            .eq("id", task_id)
            .eq("user_id", user_id),
            op_name="pm_tools.update_pm_task.local_update",
        )

        logger.info(
            "pm_tools.update_pm_task: user=%s task_id=%s updates=%s",
            user_id,
            task_id,
            list(updates.keys()),
        )
        return {
            "success": True,
            "task_id": task_id,
            "updated_fields": list(updates.keys()),
            "api_result": api_result,
            "message": "Task updated in both Pikar and the connected PM tool.",
        }

    except ValueError as exc:
        return {"success": False, "error": str(exc)}
    except Exception as exc:
        logger.exception(
            "update_pm_task failed for user=%s task_id=%s", user_id, task_id
        )
        return {"error": f"Failed to update PM task: {exc}"}


# ---------------------------------------------------------------------------
# Tool 5: get_pm_sync_status
# ---------------------------------------------------------------------------


async def get_pm_sync_status(provider: str = None) -> dict[str, Any]:
    """Get the current PM sync configuration and task counts.

    Returns which projects are configured for sync, last sync timestamp,
    task counts per provider, and connection status.

    Args:
        provider: ``"linear"`` or ``"asana"``. Omit to auto-detect.

    Returns:
        Dict with ``provider``, ``connected``, ``project_ids``,
        ``last_sync_at``, ``task_count``, and ``configuration_note``.
        On error: ``{"error": str}``.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    detected, err = await _detect_provider(provider)
    if err:
        return {"error": err}

    try:
        from app.services.base_service import AdminService
        from app.services.pm_sync_service import PMSyncService
        from app.services.supabase_async import execute_async

        sync_svc = PMSyncService()
        sync_config = await sync_svc.get_sync_config(user_id, detected)

        admin = AdminService()
        count_result = await execute_async(
            admin.client.table("synced_tasks")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("provider", detected),
            op_name="pm_tools.get_pm_sync_status.count",
        )
        task_count: int = count_result.count or 0

        project_ids: list[str] = sync_config.get("project_ids", [])
        last_sync_at: str | None = sync_config.get("last_sync_at")

        config_note: str
        if not project_ids:
            config_note = (
                "No projects configured for sync. "
                "Go to Settings > Configuration and expand the "
                f"{detected.title()} card to select projects."
            )
        else:
            config_note = (
                f"{len(project_ids)} project(s) synced. "
                f"{task_count} total tasks in Pikar."
            )

        return {
            "success": True,
            "provider": detected,
            "connected": True,
            "project_ids": project_ids,
            "project_count": len(project_ids),
            "last_sync_at": last_sync_at,
            "task_count": task_count,
            "configuration_note": config_note,
        }

    except Exception as exc:
        logger.exception("get_pm_sync_status failed for user=%s", user_id)
        return {"error": f"Failed to get sync status: {exc}"}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

PM_TASK_TOOLS = [
    get_pm_projects,
    list_pm_tasks,
    create_pm_task,
    update_pm_task,
    get_pm_sync_status,
]
