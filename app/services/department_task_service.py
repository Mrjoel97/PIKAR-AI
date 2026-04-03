# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Department task service — cross-department handoff CRUD and health computation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

_VALID_STATUSES = frozenset({"pending", "in_progress", "completed", "cancelled"})
_VALID_PRIORITIES = frozenset({"low", "medium", "high", "urgent"})

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_department_task_service_instance: DepartmentTaskService | None = None


def get_department_task_service() -> DepartmentTaskService:
    """Return the shared DepartmentTaskService singleton."""
    global _department_task_service_instance
    if _department_task_service_instance is None:
        _department_task_service_instance = DepartmentTaskService()
    return _department_task_service_instance


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class DepartmentTaskService:
    """CRUD operations and health computation for cross-department task handoffs.

    All database calls use ``execute_async`` to remain compatible with both
    sync and async Supabase client variants while running in an async context.
    """

    def __init__(self) -> None:
        """Initialise with a Supabase service-role client."""
        self.client = get_service_client()

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def create_task(
        self,
        title: str,
        from_department_id: str,
        to_department_id: str,
        created_by: str,
        *,
        description: str | None = None,
        priority: str = "medium",
        due_date: str | None = None,
        assigned_to: str | None = None,
    ) -> dict[str, Any]:
        """Insert a new department task and return the created record.

        Args:
            title: Short descriptive title for the handoff task.
            from_department_id: UUID of the originating department.
            to_department_id: UUID of the receiving department.
            created_by: UUID of the user creating the handoff.
            description: Optional longer description.
            priority: One of low | medium | high | urgent (default medium).
            due_date: Optional ISO 8601 datetime string.
            assigned_to: Optional UUID of the user to assign the task to.

        Returns:
            The created task record as a dict.

        Raises:
            ValueError: If priority is not a recognised value.
        """
        if priority not in _VALID_PRIORITIES:
            raise ValueError(
                f"Invalid priority '{priority}'. Must be one of: {sorted(_VALID_PRIORITIES)}"
            )

        payload: dict[str, Any] = {
            "title": title,
            "from_department_id": from_department_id,
            "to_department_id": to_department_id,
            "created_by": created_by,
            "priority": priority,
        }
        if description is not None:
            payload["description"] = description
        if due_date is not None:
            payload["due_date"] = due_date
        if assigned_to is not None:
            payload["assigned_to"] = assigned_to

        res = await execute_async(
            self.client.table("department_tasks").insert(payload).select("*").single(),
            op_name="dept_tasks.create",
        )
        return res.data

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def list_tasks(
        self,
        department_id: str,
        *,
        direction: str = "inbound",
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List tasks for a department, enriched with department names.

        Args:
            department_id: UUID of the department whose tasks to list.
            direction: "inbound" (tasks sent TO this dept) or "outbound"
                       (tasks sent FROM this dept). Default "inbound".
            status: Optional status filter (pending, in_progress, completed, cancelled).
            limit: Maximum number of results to return (default 50).

        Returns:
            List of task dicts enriched with ``from_department_name`` and
            ``to_department_name``.
        """
        filter_col = (
            "to_department_id" if direction == "inbound" else "from_department_id"
        )

        query = (
            self.client.table("department_tasks")
            .select("*")
            .eq(filter_col, department_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if status is not None:
            query = query.eq("status", status)

        res = await execute_async(query, op_name="dept_tasks.list")
        tasks: list[dict[str, Any]] = res.data or []

        # Enrich with department names
        dept_ids: set[str] = set()
        for t in tasks:
            if t.get("from_department_id"):
                dept_ids.add(t["from_department_id"])
            if t.get("to_department_id"):
                dept_ids.add(t["to_department_id"])

        dept_name_map: dict[str, str] = {}
        if dept_ids:
            dept_res = await execute_async(
                self.client.table("departments")
                .select("id, name")
                .in_("id", list(dept_ids)),
                op_name="dept_tasks.list.names",
            )
            for row in dept_res.data or []:
                dept_name_map[row["id"]] = row["name"]

        for task in tasks:
            task["from_department_name"] = dept_name_map.get(
                task.get("from_department_id", ""), "Unknown"
            )
            task["to_department_name"] = dept_name_map.get(
                task.get("to_department_id", ""), "Unknown"
            )

        return tasks

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        """Retrieve a single task by ID, enriched with department names.

        Args:
            task_id: UUID of the department task.

        Returns:
            The task dict with department names, or None if not found.
        """
        res = await execute_async(
            self.client.table("department_tasks")
            .select("*")
            .eq("id", task_id)
            .single(),
            op_name="dept_tasks.get",
        )
        task: dict[str, Any] | None = res.data
        if not task:
            return None

        # Enrich with department names
        dept_ids = [
            i
            for i in (task.get("from_department_id"), task.get("to_department_id"))
            if i
        ]
        dept_name_map: dict[str, str] = {}
        if dept_ids:
            dept_res = await execute_async(
                self.client.table("departments").select("id, name").in_("id", dept_ids),
                op_name="dept_tasks.get.names",
            )
            for row in dept_res.data or []:
                dept_name_map[row["id"]] = row["name"]

        task["from_department_name"] = dept_name_map.get(
            task.get("from_department_id", ""), "Unknown"
        )
        task["to_department_name"] = dept_name_map.get(
            task.get("to_department_id", ""), "Unknown"
        )
        return task

    # ------------------------------------------------------------------
    # Status transition
    # ------------------------------------------------------------------

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Update the status of a department task.

        Args:
            task_id: UUID of the task to update.
            status: New status — one of pending | in_progress | completed | cancelled.
            user_id: UUID of the user performing the update (for audit trail).

        Returns:
            The updated task record as a dict.

        Raises:
            ValueError: If ``status`` is not a recognised value.
        """
        if status not in _VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {sorted(_VALID_STATUSES)}"
            )

        payload: dict[str, Any] = {"status": status}
        if status == "completed":
            payload["completed_at"] = datetime.now(timezone.utc).isoformat()

        res = await execute_async(
            self.client.table("department_tasks")
            .update(payload)
            .eq("id", task_id)
            .select("*")
            .single(),
            op_name="dept_tasks.update_status",
        )
        return res.data

    # ------------------------------------------------------------------
    # Health summary
    # ------------------------------------------------------------------

    async def get_department_health(self) -> list[dict[str, Any]]:
        """Query the department_health_summary view for all departments.

        Returns:
            List of dicts with keys: department_id, department_name,
            department_type, department_status, active_tasks, completed_30d,
            total_30d, health_status (green | yellow | red).
        """
        res = await execute_async(
            self.client.table("department_health_summary").select("*"),
            op_name="dept_tasks.health",
        )
        return res.data or []
