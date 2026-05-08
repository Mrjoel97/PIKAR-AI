# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Agent-facing tool for opting into long-running job execution (LONGTASK-01).

When an agent expects a task to exceed the SSE inline budget (~5 min), it
calls :func:`run_as_long_job` instead of executing inline. The tool:

1. Inserts an ``ai_jobs`` row via :func:`app.services.long_job.submit_long_job`.
2. Pushes a ``long_task_started`` event onto the request-scoped progress
   queue so the SSE stream tells the frontend to enter job-polling mode.
3. Returns a structured handoff dict to the model so it can produce a
   short reply ("I've kicked that off — I'll surface the result when it
   finishes") instead of streaming the work inline.

The WorkflowWorker (already async per LONGTASK-03) consumes the row from
its ``ai_jobs`` polling loop. Cloud Run Job deployment of the worker is
LONGTASK-02 and remains deferred.
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.long_job import submit_long_job
from app.services.request_context import (
    get_current_progress_queue,
    get_current_session_id,
    get_current_user_id,
)
from app.sse_utils import wrap_long_task_as_job_handoff

logger = logging.getLogger(__name__)

# Match other tool modules: ToolContext is loosely typed because the
# google.adk import surface differs across versions / runtimes.
ToolContextType = Any


async def run_as_long_job(
    kind: str,
    payload: dict[str, Any],
    *,
    estimated_duration_s: int = 600,
    tool_context: ToolContextType = None,
) -> dict[str, Any]:
    """Submit a long-running task and return early with a job handoff.

    The agent's tool result is a structured handoff dict::

        {
            "kind": "long_task_handoff",
            "job_id": "...",
            "status": "pending",
            "estimated_duration_s": 600,
            "poll_url": "/jobs/<id>/progress",
            "user_message": "I've started <kind> in the background...",
        }

    The SSE post-processor recognizes this shape (via the
    ``long_task_handoff`` discriminator) and the progress queue receives a
    ``long_task_started`` event so the frontend can switch into polling
    mode immediately. The frontend then polls
    ``/jobs/{job_id}/progress`` until status is terminal.

    Args:
        kind: Job type identifier — must match either a built-in handler
            in ``WorkflowWorker.handle_job_type`` or a registered tool in
            ``app.agents.tools.registry``.
        payload: Input data for the worker. ``user_id`` and ``session_id``
            from the request context are merged in if not already present.
        estimated_duration_s: Hint to the frontend for progress UI.
            Defaults to 10 minutes.
        tool_context: ADK tool context (unused here but accepted for the
            standard signature so the registry/inspector treats this like
            any other tool).

    Returns:
        Handoff dict (see above). Always includes ``success`` flag.
    """
    user_id = get_current_user_id()
    session_id = get_current_session_id()

    enriched_payload: dict[str, Any] = dict(payload or {})
    enriched_payload.setdefault("estimated_duration_s", estimated_duration_s)
    if user_id and "user_id" not in enriched_payload:
        enriched_payload["user_id"] = user_id

    try:
        job_id = await submit_long_job(
            kind=kind,
            payload=enriched_payload,
            user_id=user_id,
            session_id=session_id,
        )
    except Exception as exc:  # noqa: BLE001 — surfaced back to the agent
        logger.error("Failed to submit long job (kind=%s): %s", kind, exc)
        return {
            "success": False,
            "kind": "long_task_handoff",
            "error": str(exc),
            "user_message": (
                "I couldn't start the background task. Please try again "
                "or ask me to run it inline."
            ),
        }

    poll_url = f"/jobs/{job_id}/progress"

    # Push a long_task_started event onto the progress queue so the SSE
    # generator forwards it to the connected client without any changes
    # to the inline event loop. Best-effort — if the queue isn't set
    # (e.g. during background invocation outside SSE) we skip silently.
    queue = get_current_progress_queue()
    if queue is not None:
        try:
            queue.put_nowait(
                wrap_long_task_as_job_handoff(
                    {
                        "job_id": job_id,
                        "kind": kind,
                        "estimated_duration_s": estimated_duration_s,
                        "poll_url": poll_url,
                    }
                )
            )
        except Exception as exc:  # noqa: BLE001 — best-effort
            logger.warning(
                "Could not enqueue long_task_started event for job %s: %s",
                job_id,
                exc,
            )

    return {
        "success": True,
        "kind": "long_task_handoff",
        "job_id": job_id,
        "status": "pending",
        "estimated_duration_s": estimated_duration_s,
        "poll_url": poll_url,
        "user_message": (
            f"I've started **{kind}** in the background. "
            f"You can keep chatting; I'll surface the result when it finishes "
            f"(estimated ~{estimated_duration_s // 60} min)."
        ),
    }


# Standard module-level export so the Executive tool list can splat it.
LONG_TASK_TOOLS = [run_as_long_job]
