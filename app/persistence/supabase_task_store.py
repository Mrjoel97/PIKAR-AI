import json
import logging
from typing import Optional
from a2a.server.tasks.task_store import TaskStore
from a2a.types import Task
from a2a.server.context import ServerCallContext
from app.rag.knowledge_vault import get_supabase_client

logger = logging.getLogger(__name__)

class SupabaseTaskStore(TaskStore):
    """A TaskStore implementation backed by Supabase (PostgreSQL)."""

    def __init__(self):
        self.client = get_supabase_client()
        self.table = "a2a_tasks"

    def get(self, task_id: str, context: Optional[ServerCallContext] = None) -> Optional[Task]:
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

    def save(self, task: Task, context: Optional[ServerCallContext] = None) -> None:
        try:
            data = {
                "task_id": task.task_id,
                "task_data": task.model_dump(mode="json"),
                "status": str(task.status),
                "updated_at": "now()"
            }
            # Upsert
            self.client.table(self.table).upsert(data).execute()
        except Exception as e:
            logger.error(f"Failed to save task {task.task_id}: {e}")
            raise e

    def delete(self, task_id: str, context: Optional[ServerCallContext] = None) -> None:
        try:
            self.client.table(self.table).delete().eq("task_id", task_id).execute()
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            raise e
