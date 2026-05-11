"""Workspace item emission for workflow executions and other long-lived agent runs."""

import logging
from typing import Any

from app.services.supabase_async import execute_async
from app.services.supabase_client import get_service_client

logger = logging.getLogger(__name__)

INTERACTIVE_RUN_SOURCES = frozenset({"user_ui", "agent_ui"})


class WorkspaceItemEmitter:
    """Emits a workspace_item row when a workflow execution starts.

    Owns the mapping from run_source to layout_mode so other features can reuse
    the rule without re-implementing it.
    """

    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        return self._client or get_service_client()

    async def emit_for_execution(
        self,
        execution: dict[str, Any],
        run_source: str,
    ) -> None:
        """Insert a workflow_timeline workspace_item for ``execution``.

        Failures are logged and swallowed; the workflow must not abort because the
        visualization could not be persisted.
        """
        interactive = run_source in INTERACTIVE_RUN_SOURCES
        layout_mode = "focus" if interactive else "embedded"
        row = {
            "user_id": execution["user_id"],
            "widget_type": "workflow_timeline",
            "workflow_execution_id": execution["id"],
            "title": execution.get("name") or "Workflow",
            "layout_mode": layout_mode,
            "widget_payload": {
                "execution_id": execution["id"],
                "interactive": interactive,
            },
            "source_key": f"workflow_timeline:{execution['id']}",
        }
        try:
            await execute_async(
                self.client.table("workspace_items").upsert(
                    row, on_conflict="source_key"
                ),
                op_name="workspace_items.emit",
            )
        except Exception:
            logger.warning(
                "workspace_items emit failed for execution %s",
                execution.get("id"),
                exc_info=True,
            )
