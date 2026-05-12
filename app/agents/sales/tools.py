# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tools for the Sales Intelligence Agent.

Note: Task tools are shared with Operations agent.
"""

from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.tools_manifest import ToolsManifest


async def create_task(description: str) -> dict:
    """Create a new task in the task management system via TaskService.

    Args:
        description: Clear description of what needs to be done.

    Returns:
        Dictionary containing task_id, status, and description.
    """
    from app.services.task_service import TaskService

    try:
        from app.services.request_context import get_current_user_id

        service = TaskService()
        # agent_id is None for now as we don't have context injection yet
        task = await service.create_task(
            description, agent_id=None, user_id=get_current_user_id()
        )
        return {
            "task_id": task["id"],
            "task": task,
            "status": task["status"],
            "description": description,
            "success": True,
        }
    except Exception as e:
        return {
            "error": f"Failed to create task: {e!s}",
            "description": description,
            "success": False,
        }


async def get_task(task_id: str) -> dict:
    """Retrieve a task by its ID from TaskService.

    Args:
        task_id: The unique identifier of the task.

    Returns:
        Dictionary containing the task details.
    """
    from app.services.task_service import TaskService

    try:
        from app.services.request_context import get_current_user_id

        service = TaskService()
        task = await service.get_task(task_id, user_id=get_current_user_id())
        return {"success": True, "task": task}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_task(task_id: str, status: str) -> dict:
    """Update a task's status via TaskService.

    Args:
        task_id: The unique identifier of the task.
        status: New status (pending, running, completed, failed).

    Returns:
        Dictionary confirming the update.
    """
    from app.services.task_service import TaskService

    try:
        from app.services.request_context import get_current_user_id

        service = TaskService()
        task = await service.update_task(
            task_id, status=status, user_id=get_current_user_id()
        )
        return {"success": True, "task": task}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_tasks(status: str = None) -> dict:
    """List tasks, optionally filtered by status.

    Args:
        status: Optional status filter (pending, running, completed, failed).

    Returns:
        Dictionary containing list of tasks.
    """
    from app.services.task_service import TaskService

    try:
        from app.services.request_context import get_current_user_id

        service = TaskService()
        tasks = await service.list_tasks(status=status, user_id=get_current_user_id())
        return {"success": True, "tasks": tasks, "count": len(tasks)}
    except Exception as e:
        return {"success": False, "error": str(e), "tasks": []}


# =============================================================================
# Tools manifest — declarative tool surface for PikarBaseAgent factory.
# =============================================================================

_TOOL_IDS: list[str] = [
    # Local sales callables defined above in this module.
    "create_task",
    "get_task",
    "update_task",
    "list_tasks",
    # Shared tool packs under ``app.agents.tools.<id>``.
    "hubspot_tools",
    "ui_widgets",
    "context_memory",
    "graph_tools",
    "system_knowledge",
    "document_gen",
    "calendar_tool",
    "pipeline_dashboard",
    "sales_followup",
    "proposal_generator",
    "quick_research",
]


def build_tools_manifest(ops: OperationsConfig) -> ToolsManifest:
    """Build the sales director tool manifest."""
    _ = ops  # reserved for future per-persona filtering
    return ToolsManifest(
        tool_ids=list(_TOOL_IDS),
        local_tools_module=__name__,
    )
