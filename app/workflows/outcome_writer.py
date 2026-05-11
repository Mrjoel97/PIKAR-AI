"""Persists per-step outcome text for the Live Workspace Workflow View."""

import logging
from typing import Any

from app.services.supabase_async import execute_async
from app.services.supabase_client import get_service_client

logger = logging.getLogger(__name__)

OUTCOME_MAX_LEN = 280


class OutcomeWriter:
    """Writes outcome_text and outcome_source on a workflow_steps row.

    Precedence:
        1. ``tool_output["summary"]`` if string, truncated to 280 chars (source=tool)
        2. Deterministic status string (source=status) — written immediately as a
           seed; the OutcomeSummaryWorker may overwrite with an LLM result later.
    """

    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        return self._client or get_service_client()

    async def write_for_step(
        self,
        *,
        step_id: str,
        tool_output: Any,
        status: str,
        tool_name: str,
        duration_ms: int,
        error_message: str | None = None,
    ) -> None:
        text, source = self._derive(
            tool_output=tool_output,
            status=status,
            tool_name=tool_name,
            duration_ms=duration_ms,
            error_message=error_message,
        )
        try:
            await execute_async(
                self.client.table("workflow_steps")
                    .update({"outcome_text": text, "outcome_source": source})
                    .eq("id", step_id),
                op_name="outcome_writer.write_for_step",
            )
        except Exception:
            logger.warning("outcome_text write failed for step %s", step_id, exc_info=True)

    def _derive(
        self,
        *,
        tool_output: Any,
        status: str,
        tool_name: str,
        duration_ms: int,
        error_message: str | None,
    ) -> tuple[str, str]:
        if isinstance(tool_output, dict):
            summary = tool_output.get("summary")
            if isinstance(summary, str) and summary.strip():
                if len(summary) > OUTCOME_MAX_LEN:
                    return summary[: OUTCOME_MAX_LEN - 3] + "...", "tool"
                return summary, "tool"
        if status == "failed":
            why = f" ({error_message})" if error_message else ""
            return f"Failed {tool_name}{why}.", "status"
        if status == "skipped":
            return f"Skipped {tool_name}.", "status"
        return f"Completed {tool_name} in {duration_ms}ms.", "status"
