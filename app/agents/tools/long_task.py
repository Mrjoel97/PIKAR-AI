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

This module also exposes the :func:`long_task` decorator: a metadata-driven
marker that auto-promotes specific known-slow tools to the long-job handoff
path when called inside an active SSE/agent context. Outside agent context
(unit tests, direct imports, worker re-execution) the decorator is a no-op
and the underlying function runs synchronously.
"""

from __future__ import annotations

import functools
import inspect
import logging
from typing import Any, Callable, TypeVar

from app.services.long_job import submit_long_job
from app.services.request_context import (
    get_current_progress_queue,
    get_current_session_id,
    get_current_user_id,
)
from app.sse_utils import wrap_long_task_as_job_handoff

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# Sentinel attribute name for tools wearing the @long_task decorator.
# The WorkflowWorker checks this so it can avoid recursive promotion when
# re-executing a promoted job inside the worker (the queue context-var is
# unset there so the no-op path is used, but this is a defense-in-depth
# marker for tooling that wants to introspect tools without calling them).
LONG_TASK_MARKER_ATTR = "__pikar_long_task__"

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


# ---------------------------------------------------------------------------
# @long_task decorator (LONGTASK-01 auto-promotion)
# ---------------------------------------------------------------------------


def _has_active_agent_context() -> bool:
    """Return True iff a request-scoped progress queue is set.

    The queue is installed by the SSE event_generator at the start of every
    ``/a2a/app/run_sse`` request (Wave 2 LONGTASK-08). When the queue is
    set we know we are inside an agent invocation and can safely promote
    a slow tool call to a background job. When it is unset the call is
    coming from a unit test, a direct script, or the WorkflowWorker
    re-executing a promoted job — all of which must run synchronously.
    """
    return get_current_progress_queue() is not None


def long_task(
    *,
    estimated_duration_s: int = 600,
    kind: str | None = None,
) -> Callable[[F], F]:
    """Mark a tool as long-running. Auto-promotes to a job_id handoff when called.

    Usage::

        @long_task(estimated_duration_s=600, kind="deep_research")
        async def deep_research(topic: str, ...) -> dict:
            ...

    Behavior:
        - When called from an agent context with an active SSE/progress
          queue, the decorator submits the underlying call as an
          ``ai_jobs`` row, returns a ``long_task_handoff`` dict
          immediately, and the actual work runs in the WorkflowWorker
          via the ``tool_invocation`` job type.
        - When called outside an agent context (tests, direct imports,
          the worker re-executing a promoted job), the decorator is a
          no-op — the underlying function runs synchronously and returns
          its real result.

    Args:
        estimated_duration_s: Hint for the frontend progress UI.
        kind: Job type identifier surfaced to the user ("video_render",
            "deep_research"). Defaults to the wrapped function's
            ``__name__`` so lookups against the tool registry still work.

    Returns:
        A decorator that wraps the function, preserving its signature,
        docstring, and ``__name__``.
    """

    def _decorator(func: F) -> F:
        if not inspect.iscoroutinefunction(func):
            # We could support sync tools by running them via asyncio.to_thread,
            # but the existing slow tools are all async. Reject sync to avoid
            # accidentally swallowing a synchronous callable's return value.
            raise TypeError(
                f"@long_task can only decorate async functions; got {func!r}"
            )

        resolved_kind = kind or func.__name__

        @functools.wraps(func)
        async def _wrapper(*args: Any, **kwargs: Any) -> Any:
            if not _has_active_agent_context():
                # No-op path: tests, direct imports, worker re-entry.
                return await func(*args, **kwargs)

            # Promote to background job. Lazy import to avoid circular
            # dependency with the registry (which imports the decorated
            # tools).
            user_id = get_current_user_id()
            session_id = get_current_session_id()

            payload: dict[str, Any] = {
                "tool_module": func.__module__,
                "tool_name": func.__name__,
                "args": list(args),
                "kwargs": dict(kwargs),
                "estimated_duration_s": estimated_duration_s,
            }
            if user_id and "user_id" not in payload["kwargs"]:
                # Surface user_id at the top level too so the worker can
                # restore it on the request context before executing.
                payload["user_id"] = user_id

            try:
                job_id = await submit_long_job(
                    kind=resolved_kind,
                    payload=payload,
                    user_id=user_id,
                    session_id=session_id,
                )
            except Exception as exc:  # noqa: BLE001 — surface to the agent
                logger.error(
                    "long_task auto-promote failed for %s: %s",
                    func.__name__,
                    exc,
                )
                # Fall back to running the tool inline so we never lose
                # the user's request — better a slow reply than no reply.
                return await func(*args, **kwargs)

            poll_url = f"/jobs/{job_id}/progress"

            queue = get_current_progress_queue()
            if queue is not None:
                try:
                    queue.put_nowait(
                        wrap_long_task_as_job_handoff(
                            {
                                "job_id": job_id,
                                "kind": resolved_kind,
                                "estimated_duration_s": estimated_duration_s,
                                "poll_url": poll_url,
                            }
                        )
                    )
                except Exception as exc:  # noqa: BLE001 — best-effort
                    logger.warning(
                        "Could not enqueue long_task_started for %s: %s",
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
                    f"I've started **{resolved_kind}** in the background. "
                    f"You can keep chatting; I'll surface the result when "
                    f"it finishes (estimated ~{estimated_duration_s // 60} min)."
                ),
            }

        # Marker attributes for introspection + tests.
        setattr(_wrapper, LONG_TASK_MARKER_ATTR, True)
        _wrapper.__long_task_kind__ = resolved_kind  # type: ignore[attr-defined]
        _wrapper.__long_task_estimated_duration_s__ = estimated_duration_s  # type: ignore[attr-defined]
        # functools.wraps already sets __wrapped__, but we re-affirm for clarity.
        _wrapper.__wrapped__ = func  # type: ignore[attr-defined]

        return _wrapper  # type: ignore[return-value]

    return _decorator


async def execute_tool_invocation_job(input_data: dict[str, Any]) -> dict[str, Any]:
    """Worker handler for ``tool_invocation`` jobs (auto-promoted via @long_task).

    The payload shape is produced by the :func:`long_task` decorator::

        {
            "tool_module": "app.agents.tools.deep_research",
            "tool_name": "deep_research",
            "args": [...],
            "kwargs": {...},
            "user_id": "...",
            "session_id": "...",
        }

    The worker imports the module, looks up the function (using
    ``__wrapped__`` so we run the *underlying* coroutine, not the decorated
    promoter), and invokes it. Restoring ``user_id``/``session_id`` on the
    request context ensures downstream tools that read those vars (vault
    save, etc.) continue to work.
    """
    import importlib

    from app.services.request_context import (
        set_current_session_id,
        set_current_user_id,
    )

    tool_module = input_data.get("tool_module")
    tool_name = input_data.get("tool_name")
    if not tool_module or not tool_name:
        raise ValueError(
            "tool_invocation job missing tool_module/tool_name in input_data"
        )

    args = list(input_data.get("args") or [])
    kwargs = dict(input_data.get("kwargs") or {})
    user_id = input_data.get("user_id")
    session_id = input_data.get("session_id")

    if user_id:
        set_current_user_id(str(user_id))
    if session_id:
        set_current_session_id(str(session_id))

    module = importlib.import_module(str(tool_module))
    func = getattr(module, str(tool_name), None)
    if func is None:
        raise ValueError(f"tool_invocation: {tool_module}.{tool_name} not found")

    # Unwrap the @long_task wrapper so we don't re-promote inside the worker.
    underlying = getattr(func, "__wrapped__", func)

    result = underlying(*args, **kwargs)
    if inspect.isawaitable(result):
        result = await result
    if not isinstance(result, dict):
        return {"result": result}
    return result
