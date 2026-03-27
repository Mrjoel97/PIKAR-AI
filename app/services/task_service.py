# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""TaskService - CRUD operations for task management.

This service provides Create, Read, Update, Delete operations for tasks
stored in the ai_jobs table in Supabase with proper RLS authentication.
"""

from app.services.base_service import AdminService, BaseService
from app.services.request_context import get_current_user_id
from app.services.supabase_async import execute_async


class TaskService(BaseService):
    """Service for managing tasks in the ai_jobs table.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: str | None = None):
        """Initialize the task service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)
        self._table_name = "ai_jobs"

    async def create_task(
        self, description: str, agent_id: str | None = None, user_id: str | None = None
    ) -> dict:
        """Create a new task in the ai_jobs table.

        Args:
            description: Task description text.
            agent_id: Optional agent ID to assign the task to.
            user_id: Optional user ID who owns the task.

        Returns:
            The created task record.
        """
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for task creation")

        data = {
            "agent_id": agent_id,
            "job_type": "task",
            "input_data": {"description": description},
            "status": "pending",
            "user_id": effective_user_id,
        }

        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(client.table(self._table_name).insert(data))
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert")

    async def get_task(self, task_id: str, user_id: str | None = None) -> dict:
        """Retrieve a single task by ID.

        Args:
            task_id: The unique task ID.

        Returns:
            The task record.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).select("*").eq("id", task_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query.single())
        return response.data

    async def update_task(
        self,
        task_id: str,
        status: str | None = None,
        output_data: dict | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Update a task's status or output.

        Args:
            task_id: The unique task ID.
            status: New status value (pending, running, completed, failed).
            output_data: New output data dictionary.

        Returns:
            The updated task record.
        """
        update_data = {}
        if status is not None:
            update_data["status"] = status
        if output_data is not None:
            update_data["output_data"] = output_data

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).update(update_data).eq("id", task_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update")

    async def delete_task(self, task_id: str, user_id: str | None = None) -> bool:
        """Delete a task by ID.

        Args:
            task_id: The unique task ID.

        Returns:
            True if deletion was successful.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).delete().eq("id", task_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        return len(response.data) > 0

    async def list_tasks(
        self,
        status: str | None = None,
        user_id: str | None = None,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list:
        """List tasks with optional filters.

        Args:
            status: Filter by task status.
            user_id: Filter by user ID.
            agent_id: Filter by agent ID.
            limit: Maximum number of results (default 50).

        Returns:
            List of task records.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).select("*")

        if status:
            query = query.eq("status", status)
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)
        if agent_id:
            query = query.eq("agent_id", agent_id)

        response = await execute_async(query.order("created_at", desc=True))
        return response.data
