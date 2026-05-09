# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for the ``@long_task`` decorator (LONGTASK-01 auto-promotion).

The decorator marks specific known-slow tools so they auto-promote to
the ``run_as_long_job`` handoff path when called from an active SSE
context. Outside agent context (unit tests, direct imports, the
WorkflowWorker re-executing a promoted job) the decorator is a no-op.

Covers:
- Decorator is a no-op outside agent context (no progress queue set)
- Decorator promotes to ai_jobs row + handoff dict inside agent context
- ``kind`` kwarg flows through to ``submit_long_job``
- Original args/kwargs are serialized into the ai_jobs payload
- The actually-decorated public tools (``deep_research``,
  ``create_pro_video``) carry the marker attribute
- ``execute_tool_invocation_job`` correctly unwraps and invokes the
  underlying function (worker re-entry path)
- Decorator rejects sync functions (deliberate guard)
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.tools import long_task as long_task_mod
from app.agents.tools.long_task import (
    LONG_TASK_MARKER_ATTR,
    execute_tool_invocation_job,
    long_task,
)


# ---------------------------------------------------------------------------
# No-op outside agent context
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decorator_is_noop_without_progress_queue():
    """Decorated function returns its real result when no progress queue is set."""

    @long_task(estimated_duration_s=600, kind="my_kind")
    async def slow_tool(x: int, *, label: str = "n/a") -> dict:
        return {"value": x * 2, "label": label}

    # Ensure no queue is set — this is the test's default contextvar state.
    with patch.object(long_task_mod, "get_current_progress_queue", lambda: None):
        result = await slow_tool(21, label="hi")

    assert result == {"value": 42, "label": "hi"}


@pytest.mark.asyncio
async def test_decorator_does_not_call_submit_long_job_outside_context():
    """No background job should be submitted when context is absent."""

    @long_task(estimated_duration_s=10, kind="x")
    async def f() -> str:
        return "ran-inline"

    submit_mock = AsyncMock(return_value="should-not-be-used")

    with patch.object(long_task_mod, "get_current_progress_queue", lambda: None), \
            patch.object(long_task_mod, "submit_long_job", submit_mock):
        result = await f()

    assert result == "ran-inline"
    submit_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Promotion inside agent context
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decorator_promotes_to_long_job_with_active_queue():
    """With an active progress queue, decorator submits and returns handoff."""
    queue: asyncio.Queue = asyncio.Queue()

    @long_task(estimated_duration_s=720, kind="auto_promote_kind")
    async def slow_tool(topic: str, depth: str = "deep") -> dict:
        return {"never": "reached"}

    captured_call: dict = {}

    async def _fake_submit(**kwargs):
        captured_call.update(kwargs)
        return "job-promoted-1"

    with patch.object(long_task_mod, "get_current_progress_queue", lambda: queue), \
            patch.object(long_task_mod, "get_current_user_id", lambda: "user-9"), \
            patch.object(long_task_mod, "get_current_session_id", lambda: "sess-9"), \
            patch.object(long_task_mod, "submit_long_job", _fake_submit):
        result = await slow_tool("ai agents", depth="quick")

    # Returned a handoff dict, not the original function's result.
    assert result["success"] is True
    assert result["kind"] == "long_task_handoff"
    assert result["job_id"] == "job-promoted-1"
    assert result["status"] == "pending"
    assert result["estimated_duration_s"] == 720
    assert result["poll_url"] == "/jobs/job-promoted-1/progress"
    assert "auto_promote_kind" in result["user_message"]

    # ``kind`` kwarg flowed through to submit_long_job.
    assert captured_call["kind"] == "auto_promote_kind"
    assert captured_call["user_id"] == "user-9"
    assert captured_call["session_id"] == "sess-9"

    # Args/kwargs serialized into payload.
    payload = captured_call["payload"]
    assert payload["tool_module"] == slow_tool.__wrapped__.__module__
    assert payload["tool_name"] == slow_tool.__wrapped__.__name__
    assert payload["args"] == ["ai agents"]
    assert payload["kwargs"] == {"depth": "quick"}
    assert payload["estimated_duration_s"] == 720
    # user_id surfaced at top level for context restore in the worker.
    assert payload["user_id"] == "user-9"

    # long_task_started event was enqueued.
    enqueued = queue.get_nowait()
    assert enqueued["event_type"] == "long_task_started"
    assert enqueued["job_id"] == "job-promoted-1"
    assert enqueued["kind"] == "auto_promote_kind"
    assert enqueued["estimated_duration_s"] == 720


@pytest.mark.asyncio
async def test_decorator_defaults_kind_to_function_name():
    """When ``kind`` is omitted the decorator falls back to func.__name__."""
    queue: asyncio.Queue = asyncio.Queue()

    @long_task(estimated_duration_s=60)
    async def my_research_op(query: str) -> dict:
        return {"unused": True}

    captured: dict = {}

    async def _fake_submit(**kwargs):
        captured.update(kwargs)
        return "j"

    with patch.object(long_task_mod, "get_current_progress_queue", lambda: queue), \
            patch.object(long_task_mod, "get_current_user_id", lambda: None), \
            patch.object(long_task_mod, "get_current_session_id", lambda: None), \
            patch.object(long_task_mod, "submit_long_job", _fake_submit):
        await my_research_op("anything")

    assert captured["kind"] == "my_research_op"


@pytest.mark.asyncio
async def test_decorator_falls_back_to_inline_on_submit_failure():
    """If submit_long_job raises, we run the underlying function inline."""
    queue: asyncio.Queue = asyncio.Queue()

    @long_task(estimated_duration_s=10, kind="will_fail")
    async def f() -> dict:
        return {"fallback": "ran"}

    with patch.object(long_task_mod, "get_current_progress_queue", lambda: queue), \
            patch.object(long_task_mod, "get_current_user_id", lambda: "u"), \
            patch.object(long_task_mod, "get_current_session_id", lambda: "s"), \
            patch.object(
                long_task_mod,
                "submit_long_job",
                AsyncMock(side_effect=RuntimeError("db down")),
            ):
        result = await f()

    # Did not crash; ran inline as a fallback.
    assert result == {"fallback": "ran"}


# ---------------------------------------------------------------------------
# Marker + signature preservation
# ---------------------------------------------------------------------------


def test_decorator_preserves_wrapped_metadata():
    """functools.wraps preserves __name__/__doc__ and exposes __wrapped__."""

    @long_task(estimated_duration_s=10, kind="meta")
    async def documented(x: int) -> int:
        """My docstring."""
        return x

    assert documented.__name__ == "documented"
    assert documented.__doc__ == "My docstring."
    assert getattr(documented, "__wrapped__", None) is not None
    assert getattr(documented, LONG_TASK_MARKER_ATTR) is True
    assert documented.__long_task_kind__ == "meta"
    assert documented.__long_task_estimated_duration_s__ == 10


def test_decorator_rejects_sync_functions():
    """Sync callables should raise TypeError at decoration time."""

    with pytest.raises(TypeError, match="async functions"):

        @long_task(estimated_duration_s=10, kind="bad")
        def sync_tool() -> int:
            return 1


# ---------------------------------------------------------------------------
# Real tools wear the decorator
# ---------------------------------------------------------------------------


def test_deep_research_is_decorated_with_long_task():
    """The public deep_research tool is wrapped with @long_task."""
    from app.agents.tools.deep_research import deep_research

    assert getattr(deep_research, LONG_TASK_MARKER_ATTR, False) is True
    assert getattr(deep_research, "__wrapped__", None) is not None
    assert deep_research.__long_task_kind__ == "deep_research"
    assert deep_research.__long_task_estimated_duration_s__ >= 60


def test_market_research_is_decorated_with_long_task():
    """market_research carries the marker too."""
    from app.agents.tools.deep_research import market_research

    assert getattr(market_research, LONG_TASK_MARKER_ATTR, False) is True
    assert market_research.__long_task_kind__ == "market_research"


def test_competitor_research_is_decorated_with_long_task():
    """competitor_research also opts in."""
    from app.agents.tools.deep_research import competitor_research

    assert getattr(competitor_research, LONG_TASK_MARKER_ATTR, False) is True
    assert competitor_research.__long_task_kind__ == "competitor_research"


def test_create_pro_video_is_decorated_with_long_task():
    """The Director pipeline (7-9 min) is decorated."""
    from app.agents.tools.media import create_pro_video

    assert getattr(create_pro_video, LONG_TASK_MARKER_ATTR, False) is True
    assert create_pro_video.__long_task_kind__ == "video_render"
    # Director pipeline empirically 7-9 min — decorator should reflect that.
    assert create_pro_video.__long_task_estimated_duration_s__ >= 300


def test_quick_research_is_NOT_decorated_with_long_task():
    """Fast tools should not carry the marker (false-positive guard)."""
    from app.agents.tools.deep_research import quick_research

    # quick_research takes <30s, must run inline.
    assert getattr(quick_research, LONG_TASK_MARKER_ATTR, False) is False


# ---------------------------------------------------------------------------
# Worker re-entry: execute_tool_invocation_job
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_tool_invocation_job_unwraps_and_runs_inline():
    """Worker handler imports the module + calls underlying function once."""
    # Build a fake module path that targets a known decorated function. We
    # use deep_research and stub its underlying coroutine so we don't hit
    # the network.
    from app.agents.tools import deep_research as dr_mod

    real_underlying = dr_mod.deep_research.__wrapped__

    invoked: dict = {}

    async def _fake_underlying(topic, research_type="comprehensive", depth="deep", user_id=None):
        invoked["topic"] = topic
        invoked["research_type"] = research_type
        invoked["depth"] = depth
        invoked["user_id"] = user_id
        return {"sources": [], "synthesis": "ok"}

    # Replace the wrapped inner coroutine on the decorated function.
    dr_mod.deep_research.__wrapped__ = _fake_underlying  # type: ignore[attr-defined]
    try:
        result = await execute_tool_invocation_job(
            {
                "tool_module": "app.agents.tools.deep_research",
                "tool_name": "deep_research",
                "args": ["my topic"],
                "kwargs": {"depth": "quick"},
                "user_id": "user-7",
                "session_id": "sess-7",
            }
        )
    finally:
        dr_mod.deep_research.__wrapped__ = real_underlying  # type: ignore[attr-defined]

    assert invoked["topic"] == "my topic"
    assert invoked["depth"] == "quick"
    assert result == {"sources": [], "synthesis": "ok"}


@pytest.mark.asyncio
async def test_execute_tool_invocation_job_rejects_missing_module():
    """Worker handler errors loudly when the payload is missing required keys."""
    with pytest.raises(ValueError, match="missing tool_module"):
        await execute_tool_invocation_job({"tool_name": "x"})

    with pytest.raises(ValueError, match="missing tool_module"):
        await execute_tool_invocation_job({"tool_module": "x"})
