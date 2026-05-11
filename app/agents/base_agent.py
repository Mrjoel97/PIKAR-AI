# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""PikarAgent + PikarBaseAgent.

`PikarAgent` is the legacy ADK-path-resolution shim — kept verbatim so the
existing factory functions (e.g. ``create_financial_agent``) continue to
work throughout the wave-based migration. ADK uses ``inspect.getfile()`` on
the Agent class to determine ``app_name``; subclassing ``Agent`` here keeps
the class definition inside the user's project so ADK infers the app name
from the directory layout.

`PikarBaseAgent` is the new Section-A skeleton introduced by the agent
operating model W1+W2 plan:

  * Loads :class:`~app.agents.runtime.operations_config.OperationsConfig`
    from an ``operations.yaml`` path (fails fast on schema error).
  * Carries identity (``agent_id``, ``user_id``, ``persona_id``).
  * Wires all four ADK lifecycle hooks via factories in
    :mod:`app.agents.runtime.lifecycle` (Section A stubs; Section B replaces
    the bodies).
  * Declares the five public methods (``respond_directly``, ``execute_task``,
    ``start_initiative``, ``advance_phase``, ``close_initiative``) as
    ``NotImplementedError`` placeholders so a half-migrated agent fails
    loudly instead of silently no-opping.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from google.adk.agents import Agent as BaseAgent

from app.agents.runtime import lifecycle
from app.agents.runtime.operations_config import OperationsConfig
from app.skills.registry import AgentID


class PikarAgent(BaseAgent):
    """Custom Agent subclass for Pikar AI.

    This exists solely to fix ADK's path resolution issue.
    The class must be defined in the user's project (not google.adk.agents)
    for ADK to correctly infer the app name from the directory structure.
    """

    pass


@runtime_checkable
class ToolsManifest(Protocol):
    """Anything that knows how to materialize the agent's tool callables.

    The concrete carrier lives in
    :mod:`app.agents.runtime.tools_manifest`; this :class:`Protocol`
    just defines the duck-type the agent constructor needs so tests and
    alternative manifest sources can plug in without subclassing.
    """

    def resolve(self) -> list[Any]:
        """Return the materialized list of tool callables for the agent."""
        ...


class PikarBaseAgent(PikarAgent):
    """Section A skeleton — full responsibilities defined in spec § 5.

    Constructor responsibilities (this file):
      1. Load and validate ``operations.yaml`` (fail fast on schema error).
      2. Read ``instructions.md`` and pass it through to the parent
         ``instruction=`` field (empty/missing path raises ``ValueError``).
      3. Resolve the tool manifest.
      4. Wire all four ADK lifecycle hooks via
         :mod:`app.agents.runtime.lifecycle` factories.

    Section B owns the bodies of the lifecycle callbacks.
    Section C/D own ``execute_task``, ``respond_directly``, the three
    initiative ritual methods, and the publication / handoff plumbing.
    """

    def __init__(
        self,
        *,
        agent_id: AgentID,
        instructions_path: Path,
        tools_manifest: ToolsManifest,
        ops_config_path: Path,
        user_id: UUID,
        persona_id: str,
        **extra: Any,
    ) -> None:
        """Construct a ``PikarBaseAgent``.

        Args:
            agent_id: Canonical agent identifier from
                :class:`~app.skills.registry.AgentID`. Passed through to
                the ADK ``Agent`` as ``name``.
            instructions_path: Path to a ``instructions.md`` file. Read
                once at construction and used as the ADK ``instruction``
                kwarg. Empty or missing file raises ``ValueError``.
            tools_manifest: Anything with ``.resolve() -> list[callable]``
                describing the tool surface (see
                :class:`~app.agents.runtime.tools_manifest.ToolsManifest`).
            ops_config_path: Path to ``operations.yaml``. Loaded via
                :meth:`OperationsConfig.load` so schema errors surface as
                ``pydantic.ValidationError`` at construction time.
            user_id: Owning user UUID — bound into the lifecycle closures.
            persona_id: Owning persona slug (e.g. ``"founder"``) — bound
                into the lifecycle closures.
            **extra: Forwarded to the underlying ADK ``Agent.__init__``
                (model, generate_content_config, sub_agents, ...).

        Raises:
            ValueError: if ``instructions_path`` is empty / missing or the
                file is empty.
            FileNotFoundError: if either path does not exist.
            pydantic.ValidationError: if ``operations.yaml`` is malformed.
        """
        # 1. Identity ------------------------------------------------------
        self.agent_id = agent_id
        self.user_id = user_id
        self.persona_id = persona_id

        # 2. Operations config (fail fast on schema error) ----------------
        self.ops: OperationsConfig = OperationsConfig.load(ops_config_path)

        # 3. Instructions --------------------------------------------------
        if instructions_path is None:
            raise ValueError(
                "PikarBaseAgent requires a non-empty instructions_path"
            )
        instructions_path = Path(instructions_path)
        instruction = instructions_path.read_text(encoding="utf-8")
        if not instruction.strip():
            raise ValueError(
                f"PikarBaseAgent instructions file at {instructions_path} is empty"
            )

        # 4. Tools manifest ------------------------------------------------
        tools = tools_manifest.resolve()

        # 5. Wire ADK lifecycle hooks + delegate to parent ----------------
        super().__init__(
            name=agent_id.value,
            instruction=instruction,
            tools=tools,
            before_agent_callback=lifecycle.before_agent(self),
            before_tool_callback=lifecycle.before_tool(self),
            after_tool_callback=lifecycle.after_tool(self),
            after_agent_callback=lifecycle.after_agent(self),
            **extra,
        )

    # ------------------------------------------------------------------
    # Public surface — bodies live in Sections B / C / D.
    # ------------------------------------------------------------------

    async def respond_directly(self, request: Any) -> Any:
        """Direct-mode turn. Implemented in Section C."""
        raise NotImplementedError(
            "PikarBaseAgent.respond_directly is implemented in Section C."
        )

    async def execute_task(self, contract: Any) -> Any:
        """Initiative-mode TaskContract execution. Implemented in Section D."""
        raise NotImplementedError(
            "PikarBaseAgent.execute_task is implemented in Section D."
        )

    async def start_initiative(
        self,
        *,
        goal: str,
        success_criteria: list[str],
        owners: list[AgentID],
        phase: str = "ideation",
        name: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Initiative-ritual start. Implemented in Section D."""
        raise NotImplementedError(
            "PikarBaseAgent.start_initiative is implemented in Section D."
        )

    async def advance_phase(
        self,
        *,
        initiative_id: UUID,
        current_phase: str,
    ) -> Any:
        """Initiative-ritual phase-advance. Implemented in Section D."""
        raise NotImplementedError(
            "PikarBaseAgent.advance_phase is implemented in Section D."
        )

    async def close_initiative(
        self,
        *,
        initiative_id: UUID,
    ) -> Any:
        """Initiative-ritual close. Implemented in Section D."""
        raise NotImplementedError(
            "PikarBaseAgent.close_initiative is implemented in Section D."
        )


__all__ = [
    "PikarAgent",
    "PikarBaseAgent",
    "ToolsManifest",
]
