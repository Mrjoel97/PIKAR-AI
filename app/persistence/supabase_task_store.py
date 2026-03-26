# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

import logging
from datetime import datetime, timezone

from a2a.server.context import ServerCallContext
from a2a.server.tasks.task_store import TaskStore
from a2a.types import Task

from app.services.supabase_client import get_service_client

logger = logging.getLogger(__name__)


class SupabaseTaskStore(TaskStore):
    """A TaskStore implementation backed by Supabase (PostgreSQL).

    A2A TaskStore interface mandates sync methods (``get``, ``save``, ``delete``).
    These low-frequency operations (task create/update per A2A call, not per-message)
    remain on the sync client. The thread pool easily handles the small number of
    sync Supabase calls even at reduced pool size.
    """

    def __init__(self):
        self.client = get_service_client()
        self.table = "a2a_tasks"

    def get(
        self, task_id: str, context: ServerCallContext | None = None
    ) -> Task | None:
        try:
            response = (
                self.client.table(self.table)
                .select("task_data")
                .eq("task_id", task_id)
                .single()
                .execute()
            )
            if response.data:
                # Deserialize JSON back to Task object
                # Assuming Task matches the dict structure or has a parse method
                # Pydantic models usually have model_validate
                return Task.model_validate(response.data["task_data"])
            return None
        except Exception as e:
            logger.warning(f"Failed to get task {task_id}: {e}")
            return None

    def save(self, task: Task, context: ServerCallContext | None = None) -> None:
        try:
            data = {
                "task_id": task.task_id,
                "task_data": task.model_dump(mode="json"),
                "status": str(task.status),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            # Upsert
            self.client.table(self.table).upsert(data).execute()
        except Exception as e:
            logger.error(f"Failed to save task {task.task_id}: {e}")
            raise

    def delete(self, task_id: str, context: ServerCallContext | None = None) -> None:
        try:
            self.client.table(self.table).delete().eq("task_id", task_id).execute()
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            raise
