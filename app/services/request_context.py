"""Request-scoped context for agent tool execution.

Stores per-request metadata (like user_id, agent_mode) using contextvars so tools can
access the current user without passing it through every function call.
"""

import asyncio
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Literal

_current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)
_current_agent_mode: ContextVar[str] = ContextVar("current_agent_mode", default="auto")
_current_session_id: ContextVar[str | None] = ContextVar("current_session_id", default=None)
_current_workflow_execution_id: ContextVar[str | None] = ContextVar(
    "current_workflow_execution_id", default=None
)
_current_progress_queue: ContextVar[asyncio.Queue[dict[str, Any]] | None] = ContextVar(
    "current_progress_queue", default=None
)

# Type alias for agent modes
AgentMode = Literal["auto", "collab", "ask"]


def set_current_user_id(user_id: str | None) -> None:
    """Set the current user ID for this request context."""
    _current_user_id.set(user_id)


def get_current_user_id() -> str | None:
    """Get the current user ID for this request context."""
    return _current_user_id.get()


def set_current_session_id(session_id: str | None) -> None:
    """Set the current session ID for this request context."""
    _current_session_id.set(session_id)


def get_current_session_id() -> str | None:
    """Get the current session ID for this request context."""
    return _current_session_id.get()


def set_current_workflow_execution_id(execution_id: str | None) -> None:
    """Set the current workflow execution ID for this request context."""
    _current_workflow_execution_id.set(execution_id)


def get_current_workflow_execution_id() -> str | None:
    """Get the current workflow execution ID for this request context."""
    return _current_workflow_execution_id.get()


def set_current_agent_mode(mode: str) -> None:
    """Set the agent interaction mode for this request context.

    Modes:
    - 'auto': Agent works independently until task completion
    - 'collab': Agent asks for approval and insights as it works
    - 'ask': User queries the agent about progress, chats, reports
    """
    _current_agent_mode.set(mode)


def get_current_agent_mode() -> str:
    """Get the current agent interaction mode for this request context."""
    return _current_agent_mode.get()


def set_current_progress_queue(queue: asyncio.Queue[dict[str, Any]] | None) -> None:
    """Set request-scoped progress queue for live SSE progress events."""
    _current_progress_queue.set(queue)


def get_current_progress_queue() -> asyncio.Queue[dict[str, Any]] | None:
    """Get request-scoped progress queue."""
    return _current_progress_queue.get()


async def emit_progress_update(stage: str, payload: dict[str, Any] | None = None) -> None:
    """Emit a progress update to the request-scoped queue, if present."""
    queue = _current_progress_queue.get()
    if queue is None:
        return
    event = {
        "type": "director_progress",
        "stage": stage,
        "payload": payload or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await queue.put(event)
