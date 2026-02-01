"""TaskService - CRUD operations for task management.

This service provides Create, Read, Update, Delete operations for tasks
stored in the ai_jobs table in Supabase with proper RLS authentication.
"""

from typing import Optional
from app.services.base_service import BaseService


class TaskService(BaseService):
    """Service for managing tasks in the ai_jobs table.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: Optional[str] = None):
        """Initialize the task service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)
        self._table_name = "ai_jobs"

    async def create_task(
        self,
        description: str,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> dict:
        """Create a new task in the ai_jobs table.
        
        Args:
            description: Task description text.
            agent_id: Optional agent ID to assign the task to.
            user_id: Optional user ID who owns the task.
            
        Returns:
            The created task record.
        """
        data = {
            "agent_id": agent_id,
            "job_type": "task",
            "input_data": {"description": description},
            "status": "pending",
            "user_id": user_id
        }
        
        response = self.client.table(self._table_name).insert(data).execute()
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert")

    async def get_task(self, task_id: str) -> dict:
        """Retrieve a single task by ID.
        
        Args:
            task_id: The unique task ID.
            
        Returns:
            The task record.
        """
        response = (
            self.client.table(self._table_name)
            .select("*")
            .eq("id", task_id)
            .single()
            .execute()
        )
        return response.data

    async def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        output_data: Optional[dict] = None
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
            
        response = (
            self.client.table(self._table_name)
            .update(update_data)
            .eq("id", task_id)
            .execute()
        )
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update")

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID.
        
        Args:
            task_id: The unique task ID.
            
        Returns:
            True if deletion was successful.
        """
        response = (
            self.client.table(self._table_name)
            .delete()
            .eq("id", task_id)
            .execute()
        )
        return len(response.data) > 0

    async def list_tasks(
        self,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 50
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
        query = self.client.table(self._table_name).select("*")
        
        if status:
            query = query.eq("status", status)
        if user_id:
            query = query.eq("user_id", user_id)
        if agent_id:
            query = query.eq("agent_id", agent_id)
            
        response = query.order("created_at", desc=True).execute()
        return response.data
