# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for tool-call progress SSE events.

Verifies that:
1. `tool_progress_before_tool_callback` pushes a `tool_call_start` event
   onto the request-scoped progress queue with the correct shape.
2. `tool_progress_after_tool_callback` pushes a `tool_call_end` event with
   a populated `duration_ms` and `status` field.
3. `serialize_progress_event` round-trips both new event types through the
   SSE allowlist without coercing them back to `director_progress`.
"""

from __future__ import annotations

import asyncio
import json
import sys
from unittest.mock import MagicMock

# Stub the google.adk + google.genai surface the same way other unit tests do
# so importing app.agents.context_extractor does not require the real ADK.
sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())


def _make_tool_context() -> MagicMock:
    """Build a CallbackContext-shaped mock with a real dict for state."""
    ctx = MagicMock()
    ctx.state = {}
    ctx.agent_name = "TestAgent"
    return ctx


def _make_fake_tool(name: str = "fake_tool") -> MagicMock:
    """Build a callable mock with a `name` attribute, mimicking ADK BaseTool."""
    tool = MagicMock()
    tool.name = name
    tool.__name__ = name
    # Mimic the timed_tool wrapper attributes (no error by default).
    tool._is_timed_tool = True
    tool._last_duration_ms = 42
    tool._last_error = None
    return tool


def test_before_tool_callback_emits_tool_call_start():
    """Before-callback pushes one event with shape {event_type, tool_name, ts}."""
    from app.agents import context_extractor
    from app.services import request_context

    queue: asyncio.Queue[dict] = asyncio.Queue()
    request_context.set_current_progress_queue(queue)
    try:
        tool = _make_fake_tool("create_image")
        ctx = _make_tool_context()

        result = context_extractor.tool_progress_before_tool_callback(
            tool, {"prompt": "a cat"}, ctx
        )

        # Callback must never short-circuit the tool call.
        assert result is None

        # Exactly one event was queued.
        assert queue.qsize() == 1
        event = queue.get_nowait()

        assert event["event_type"] == "tool_call_start"
        assert event["tool_name"] == "create_image"
        assert isinstance(event["ts"], str) and event["ts"]

        # Start timestamp was stamped onto the tool context for the after-callback.
        starts = ctx.state.get("_tool_progress_starts")
        assert isinstance(starts, dict)
        assert "create_image" in starts
    finally:
        request_context.set_current_progress_queue(None)


def test_after_tool_callback_emits_tool_call_end_with_duration():
    """After-callback pushes a `tool_call_end` event with duration_ms and status."""
    from app.agents import context_extractor
    from app.services import request_context

    queue: asyncio.Queue[dict] = asyncio.Queue()
    request_context.set_current_progress_queue(queue)
    try:
        tool = _make_fake_tool("send_email")
        ctx = _make_tool_context()

        # Run the before-callback to seed state.
        context_extractor.tool_progress_before_tool_callback(tool, {}, ctx)
        # Drain the start event so we only inspect the end event below.
        queue.get_nowait()

        # Now the after-callback.
        result = context_extractor.tool_progress_after_tool_callback(
            tool, {}, ctx, {"success": True}
        )
        assert result is None

        assert queue.qsize() == 1
        event = queue.get_nowait()

        assert event["event_type"] == "tool_call_end"
        assert event["tool_name"] == "send_email"
        assert event["status"] == "ok"
        assert isinstance(event["duration_ms"], int)
        assert event["duration_ms"] >= 0
        assert isinstance(event["ts"], str) and event["ts"]

        # The start timestamp was popped to avoid leaking state.
        starts = ctx.state.get("_tool_progress_starts", {})
        assert "send_email" not in starts
    finally:
        request_context.set_current_progress_queue(None)


def test_after_tool_callback_marks_failed_response_as_error():
    """A `success: False` response surfaces status='error' on the end event."""
    from app.agents import context_extractor
    from app.services import request_context

    queue: asyncio.Queue[dict] = asyncio.Queue()
    request_context.set_current_progress_queue(queue)
    try:
        tool = _make_fake_tool("flaky_tool")
        ctx = _make_tool_context()

        context_extractor.tool_progress_before_tool_callback(tool, {}, ctx)
        queue.get_nowait()  # drop start event

        context_extractor.tool_progress_after_tool_callback(
            tool, {}, ctx, {"success": False, "error": "boom"}
        )

        event = queue.get_nowait()
        assert event["event_type"] == "tool_call_end"
        assert event["status"] == "error"
    finally:
        request_context.set_current_progress_queue(None)


def test_callbacks_no_op_without_active_queue():
    """When no progress queue is bound to the context, callbacks are silent no-ops."""
    from app.agents import context_extractor
    from app.services import request_context

    request_context.set_current_progress_queue(None)
    tool = _make_fake_tool("offline_tool")
    ctx = _make_tool_context()

    # Both callbacks must complete without raising.
    assert context_extractor.tool_progress_before_tool_callback(tool, {}, ctx) is None
    assert (
        context_extractor.tool_progress_after_tool_callback(tool, {}, ctx, {}) is None
    )


def test_serialize_progress_event_round_trips_tool_call_events():
    """`serialize_progress_event` keeps the new event types in their allowlist."""
    from app.sse_utils import serialize_progress_event

    start_event = {
        "event_type": "tool_call_start",
        "tool_name": "create_image",
        "ts": "2026-05-08T00:00:00Z",
    }
    serialized = serialize_progress_event(start_event)
    parsed = json.loads(serialized)
    assert parsed["event_type"] == "tool_call_start"
    assert parsed["tool_name"] == "create_image"
    assert parsed["ts"] == "2026-05-08T00:00:00Z"

    end_event = {
        "event_type": "tool_call_end",
        "tool_name": "create_image",
        "duration_ms": 1234,
        "status": "ok",
        "ts": "2026-05-08T00:00:01Z",
    }
    serialized = serialize_progress_event(end_event)
    parsed = json.loads(serialized)
    assert parsed["event_type"] == "tool_call_end"
    assert parsed["tool_name"] == "create_image"
    assert parsed["duration_ms"] == 1234
    assert parsed["status"] == "ok"


def test_serialize_progress_event_preserves_director_progress():
    """Legacy director_progress events still serialize to the same shape."""
    from app.sse_utils import serialize_progress_event

    event = {
        "stage": "rendering_started",
        "payload": {"foo": 1},
        "timestamp": "2026-05-08T00:00:00Z",
    }
    parsed = json.loads(serialize_progress_event(event))
    assert parsed["event_type"] == "director_progress"
    assert parsed["stage"] == "rendering_started"
    assert parsed["payload"] == {"foo": 1}
    assert parsed["timestamp"] == "2026-05-08T00:00:00Z"


def test_serialize_progress_event_unknown_type_falls_back_to_director():
    """Unknown event types fall back to director_progress for safety."""
    from app.sse_utils import serialize_progress_event

    event = {"event_type": "rogue_event", "stage": "x"}
    parsed = json.loads(serialize_progress_event(event))
    assert parsed["event_type"] == "director_progress"


def test_context_memory_after_callback_chains_progress_emit():
    """The pre-existing context_memory_after_tool_callback must still emit
    a `tool_call_end` boundary so all 53 wired agent sites stay covered.
    """
    from app.agents import context_extractor
    from app.services import request_context

    queue: asyncio.Queue[dict] = asyncio.Queue()
    request_context.set_current_progress_queue(queue)
    try:
        tool = _make_fake_tool("composite_tool")
        ctx = _make_tool_context()

        # Seed the start timestamp so the end event has a duration.
        context_extractor.tool_progress_before_tool_callback(tool, {}, ctx)
        queue.get_nowait()  # drop the start event

        # Invoke the canonical after callback (the one wired everywhere).
        context_extractor.context_memory_after_tool_callback(
            tool, {}, ctx, {"success": True, "message": "ok"}
        )

        # The first event drained should be the tool_call_end progress event.
        # (Telemetry / cross-agent context paths do not push to this queue.)
        event = queue.get_nowait()
        assert event["event_type"] == "tool_call_end"
        assert event["tool_name"] == "composite_tool"
    finally:
        request_context.set_current_progress_queue(None)
