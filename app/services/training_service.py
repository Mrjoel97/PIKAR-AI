# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""TrainingService - CRUD operations for training assignments.

Provides Create, Read, Update operations for training assignment records
stored in Supabase with proper RLS authentication. Used by the real
assign_training tool (Phase 65-04, HR-06).
"""

from __future__ import annotations

import logging

from app.services.base_service import AdminService, BaseService
from app.services.request_context import get_current_user_id
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


class TrainingService(BaseService):
    """Service for managing training assignments.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    _table = "training_assignments"

    def __init__(self, user_token: str | None = None):
        """Initialize the training service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)

    async def assign_training(
        self,
        training_name: str,
        assignee: str,
        description: str | None = None,
        due_date: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Create a new training assignment record.

        Args:
            training_name: Name of the training module.
            assignee: Person or team assigned to complete the training.
            description: Optional description of the training.
            due_date: Optional due date in YYYY-MM-DD format.
            user_id: Owner user ID (falls back to request context).

        Returns:
            Dictionary containing the created training assignment record.
        """
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for training assignment creation")

        data: dict = {
            "training_name": training_name,
            "assignee": assignee,
            "status": "assigned",
            "user_id": effective_user_id,
        }
        if description:
            data["description"] = description
        if due_date:
            data["due_date"] = due_date

        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(client.table(self._table).insert(data))
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert training assignment")

    async def list_assignments(
        self,
        assignee: str | None = None,
        status: str | None = None,
        user_id: str | None = None,
    ) -> list[dict]:
        """List training assignments with optional filters.

        Args:
            assignee: Filter by assignee name.
            status: Filter by assignment status.
            user_id: Owner user ID (falls back to request context).

        Returns:
            List of training assignment dictionaries.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table).select("*")

        if assignee:
            query = query.eq("assignee", assignee)
        if status:
            query = query.eq("status", status)
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)

        response = await execute_async(query.order("created_at", desc=True))
        return response.data

    async def complete_assignment(
        self,
        assignment_id: str,
        user_id: str | None = None,
    ) -> dict:
        """Mark a training assignment as completed.

        Args:
            assignment_id: The unique assignment ID.
            user_id: Owner user ID (falls back to request context).

        Returns:
            Dictionary containing the updated training assignment record.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table(self._table)
            .update({"status": "completed", "completed_at": "now()"})
            .eq("id", assignment_id)
        )
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)

        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update training assignment")
