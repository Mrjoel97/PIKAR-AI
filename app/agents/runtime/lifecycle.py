# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""ADK lifecycle callback factories.

Section A scope: stubs only — every factory returns a no-op callable so the
:class:`~app.agents.base_agent.PikarBaseAgent` skeleton can wire its hooks
without circular imports or runtime errors. Section B (Tasks 21–45) replaces
each body with the real enforcement stack: skill injection, research gate,
persona gate, audit, compaction, etc.

The factory pattern (``before_agent(agent) -> callable``) is what binds the
callback to a specific agent instance — needed because ADK passes only the
:class:`CallbackContext` (or tool + args + context) into the callback itself,
without a back-reference to the owning agent.

ADK callback signatures (from ``google.adk.agents``):

- ``before_agent_callback(callback_context) -> google.genai.types.Content | None``
- ``before_tool_callback(tool, args, tool_context) -> dict | None``
- ``after_tool_callback(tool, args, tool_context, tool_response) -> dict | None``
- ``after_agent_callback(callback_context) -> google.genai.types.Content | None``

Returning ``None`` from any callback signals "no override" — ADK proceeds
with its default behaviour. That is what Section A needs.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Forward reference only — avoids a circular import because
    # PikarBaseAgent itself imports from this module to wire callbacks.
    from app.agents.base_agent import PikarBaseAgent  # noqa: F401


__all__ = [
    "before_agent",
    "before_tool",
    "after_tool",
    "after_agent",
]


def _noop(*_args: Any, **_kwargs: Any) -> None:
    """Generic no-op accepting any ADK callback signature.

    Section A uses one callable for all four hooks because their signatures
    differ only in argument names and counts; ``*_args, **_kwargs`` absorbs
    any of them. Section B will split these into four properly-typed
    closures.
    """
    return None


def before_agent(agent: PikarBaseAgent) -> Callable[..., Any]:
    """Build the ``before_agent_callback`` for ``agent``.

    Section B will implement: task router (chat vs initiative classification),
    skill injection (top-K skills + hydration into system instruction),
    memory layer-3 retrieval, persona prompt fragments, initiative-context
    loading, ops-config fail-fast on missing required fields.

    Section A stub: returns a no-op callable so the agent boots.
    """
    del agent  # bound by Section B
    return _noop


def before_tool(agent: PikarBaseAgent) -> Callable[..., Any]:
    """Build the ``before_tool_callback`` for ``agent``.

    Section B will implement: persona allow/deny on tool name, action
    threshold gates (e.g. spend > $X requires approval token), research-gate
    enforcement (cannot run execution tools while research is in progress),
    approval-token validation for gated tools.

    Section A stub: returns a no-op callable so the agent boots.
    """
    del agent  # bound by Section B
    return _noop


def after_tool(agent: PikarBaseAgent) -> Callable[..., Any]:
    """Build the ``after_tool_callback`` for ``agent``.

    Section B will implement: capture structured outputs into the handoff
    packet, close the research gate when ``finish_research`` succeeds, log
    tool failures to ``agent_task_executions``, emit workspace progress
    events for long-running tools.

    Section A stub: returns a no-op callable so the agent boots.
    """
    del agent  # bound by Section B
    return _noop


def after_agent(agent: PikarBaseAgent) -> Callable[..., Any]:
    """Build the ``after_agent_callback`` for ``agent``.

    Section B will implement: self-audit on artifact-producing turns (must
    cite skills, must reference completed research, must include handoff
    packet), compaction trigger when context budget exceeded, persist
    outcome to ``agent_task_executions`` with skill-citations and audit
    verdict.

    Section A stub: returns a no-op callable so the agent boots.
    """
    del agent  # bound by Section B
    return _noop
