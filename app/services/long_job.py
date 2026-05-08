# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Long-running job helpers (LONGTASK-01).

Tasks that are expected to exceed the SSE soft-limit (~5 minutes) are
handed off to the existing ``ai_jobs`` queue (claimed and executed by
``app.workflows.worker.WorkflowWorker``). The SSE generator returns a
``job_id`` immediately; the frontend then polls ``/jobs/{id}/progress``
which reads the ``ai_jobs`` row directly.

This module is **additive**:
- Short tasks keep running inline through the existing event_generator.
- Agents opt in to long-running mode via ``run_as_long_job`` (see
  ``app.agents.tools.long_task``).
- The WorkflowWorker is already deployed (LONGTASK-03 made it async).
  Production deploy of the worker as a Cloud Run Job is LONGTASK-02 and
  remains deferred — this module only wires the helpers + endpoints.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from app.services.supabase_async import execute_async
from app.services.supabase_client import get_async_client

logger = logging.getLogger(__name__)

# Terminal statuses returned by the WorkflowWorker.
_TERMINAL_STATUSES: frozenset[str] = frozenset({"completed", "failed", "cancelled"})

# Polling cadence for ``poll_job_progress``. Starts tight and backs off
# slowly so the consumer notices fast-finishing jobs without flooding the
# DB on multi-minute jobs.
_POLL_INITIAL_S: float = 2.0
_POLL_MAX_S: float = 5.0
_POLL_BACKOFF: float = 1.25

# Hard cap on how long ``poll_job_progress`` will hang around. After this
# the consumer gets a synthetic ``timeout`` event and is expected to fall
# back to the polling endpoint. Defaults align with the SSE max-duration
# (LONGTASK-04, Wave 3).
_POLL_DEADLINE_S: float = 30 * 60  # 30 minutes


async def submit_long_job(
    *,
    kind: str,
    payload: dict[str, Any],
    user_id: str | None,
    session_id: str | None = None,
    priority: int = 5,
) -> str:
    """Insert an ``ai_jobs`` row with status ``pending``.

    The WorkflowWorker will pick it up via ``claim_next_ai_job`` on its
    next poll and route it through ``handle_job_type`` → tool registry.

    Args:
        kind: Job type identifier (matches ``ai_jobs.job_type``). Should
            either be one of the worker's built-in handlers (e.g.
            ``daily_report``) or the name of a registered tool.
        payload: Input data forwarded to the handler as ``input_data``.
            ``session_id`` is merged in if not already present so handlers
            can correlate progress back to the chat session.
        user_id: Owning user id; required for the job-progress endpoint
            authorization check.
        session_id: Originating chat session id (optional).
        priority: Higher value = claimed sooner (default 5).

    Returns:
        The newly minted job id (UUID string).
    """
    job_id = str(uuid.uuid4())
    enriched_payload: dict[str, Any] = dict(payload or {})
    if session_id and "session_id" not in enriched_payload:
        enriched_payload["session_id"] = session_id

    row = {
        "id": job_id,
        "user_id": user_id,
        "job_type": kind,
        "status": "pending",
        "priority": priority,
        "input_data": enriched_payload,
    }

    client = await get_async_client()
    await execute_async(
        client.table("ai_jobs").insert(row),
        op_name="long_job.submit",
    )
    logger.info("Submitted long job %s (kind=%s, user=%s)", job_id, kind, user_id)
    return job_id


async def get_job_row(job_id: str, *, user_id: str | None = None) -> dict[str, Any] | None:
    """Fetch a single ``ai_jobs`` row.

    Args:
        job_id: The job id to look up.
        user_id: When provided, also enforces ownership (returns ``None``
            when the row exists but belongs to another user).

    Returns:
        The row dict or ``None`` when not found / not owned.
    """
    client = await get_async_client()
    query = client.table("ai_jobs").select("*").eq("id", job_id)
    response = await execute_async(query.limit(1), op_name="long_job.get")
    rows = response.data or []
    if not rows:
        return None
    row = rows[0]
    if user_id is not None and str(row.get("user_id") or "") != str(user_id):
        return None
    return row


def _project_progress_event(row: dict[str, Any]) -> dict[str, Any]:
    """Project an ``ai_jobs`` row into a frontend-friendly progress event."""
    status = (row.get("status") or "pending").lower()
    input_data = row.get("input_data") or {}
    output_data = row.get("output_data") or {}
    # Workers may stash a percent + message inside output_data while
    # status is still ``processing``. Default to None so the frontend
    # can render an indeterminate spinner.
    progress_pct = None
    message = None
    if isinstance(output_data, dict):
        progress_pct = output_data.get("progress_pct")
        message = output_data.get("message")

    event: dict[str, Any] = {
        "event_type": "long_task_progress",
        "job_id": str(row.get("id")),
        "kind": row.get("job_type"),
        "status": status,
        "progress_pct": progress_pct,
        "message": message,
        "started_at": row.get("started_at"),
        "completed_at": row.get("completed_at"),
    }
    if status == "completed":
        event["event_type"] = "long_task_completed"
        event["result"] = output_data
    elif status in {"failed", "cancelled"}:
        event["event_type"] = "long_task_completed"
        event["error"] = row.get("error_message")
        event["result"] = output_data
    elif isinstance(input_data, dict):
        # Surface the originally-estimated duration on the first event so
        # the UI can pick a reasonable progress animation.
        est = input_data.get("estimated_duration_s")
        if est is not None:
            event["estimated_duration_s"] = est
    return event


async def poll_job_progress(
    job_id: str,
    *,
    user_id: str | None = None,
    deadline_s: float = _POLL_DEADLINE_S,
) -> AsyncIterator[dict[str, Any]]:
    """Yield progress events as the ``ai_jobs`` row advances.

    Polls every 2-5s with mild backoff. Yields one event per status/progress
    change plus a final terminal event. If ``deadline_s`` is exceeded,
    yields a synthetic ``timeout`` event and returns.

    Args:
        job_id: The job id to watch.
        user_id: Optional ownership guard.
        deadline_s: Maximum total wait before bailing out.

    Yields:
        Dicts shaped like
        ``{event_type, job_id, kind, status, progress_pct, message, ...}``
        with the final event carrying ``status`` in
        ``{completed, failed, cancelled}``.
    """
    deadline = asyncio.get_event_loop().time() + max(deadline_s, 1.0)
    delay = _POLL_INITIAL_S
    last_signature: tuple[Any, Any, Any] | None = None

    while True:
        row = await get_job_row(job_id, user_id=user_id)
        if row is None:
            yield {
                "event_type": "long_task_completed",
                "job_id": job_id,
                "status": "failed",
                "error": "job_not_found",
            }
            return

        event = _project_progress_event(row)
        signature = (event["status"], event.get("progress_pct"), event.get("message"))
        if signature != last_signature:
            yield event
            last_signature = signature

        if event["status"] in _TERMINAL_STATUSES:
            return

        if asyncio.get_event_loop().time() >= deadline:
            yield {
                "event_type": "long_task_progress",
                "job_id": job_id,
                "status": event["status"],
                "message": "poll deadline reached; switch to /jobs/{id}/progress",
            }
            return

        await asyncio.sleep(delay)
        delay = min(delay * _POLL_BACKOFF, _POLL_MAX_S)
