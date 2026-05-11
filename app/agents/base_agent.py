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

import logging
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from google.adk.agents import Agent as BaseAgent

from app.agents.runtime import lifecycle
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    ResearchResult,
    TaskContract,
    TodoItem,
)
from app.skills.registry import AgentID

logger = logging.getLogger(__name__)


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
        # ADK's ``Agent`` is a pydantic ``BaseModel`` with ``extra='forbid'``;
        # writing ``self.agent_id = ...`` after ``super().__init__`` would
        # raise ``ValueError: "PikarBaseAgent" object has no field …``. Use
        # ``object.__setattr__`` to bypass the model's ``__setattr__``
        # validation -- the W2 runtime treats these as plain Python
        # attributes (not declared pydantic fields).
        object.__setattr__(self, "agent_id", agent_id)
        object.__setattr__(self, "user_id", user_id)
        object.__setattr__(self, "persona_id", persona_id)

        # 2. Operations config (fail fast on schema error) ----------------
        object.__setattr__(self, "ops", OperationsConfig.load(ops_config_path))

        # 3. Instructions --------------------------------------------------
        if instructions_path is None:
            raise ValueError("PikarBaseAgent requires a non-empty instructions_path")
        instructions_path = Path(instructions_path)
        instruction = instructions_path.read_text(encoding="utf-8")
        if not instruction.strip():
            raise ValueError(
                f"PikarBaseAgent instructions file at {instructions_path} is empty"
            )

        # 4. Tools manifest ------------------------------------------------
        # Stash the manifest itself (not just the resolved callables) so
        # ``research()`` can inspect ``tool_ids`` to find the research-tool
        # subset. The ADK ``Agent`` doesn't expose the manifest object —
        # only the flat list of callables — so we keep our own reference.
        object.__setattr__(self, "_tools_manifest", tools_manifest)
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

    # ------------------------------------------------------------------
    # step_runtime contract — research / audit / run_step.
    # ------------------------------------------------------------------
    # These three methods are the surface that
    # :func:`app.agents.runtime.step_runtime.execute_task` invokes on the
    # agent. They are wired so the integration path is unblocked; the
    # in-method LLM orchestration is intentionally minimal (see comments)
    # because production wiring of multi-tool research + LLM-driven step
    # execution lives in a follow-up. Tests mock these methods directly.

    async def _call_research_tool(self, *, query: str, tool_id: str) -> dict[str, Any]:
        """Best-effort single-shot research tool stub.

        Returns a minimal structured dict so :meth:`research` can record it
        via :func:`research_gate.record_tool_result`. Production wiring will
        invoke the actual research tool callables resolved off the agent's
        ``tools_manifest``; for the pilot this returns a placeholder
        describing the query so the gate can still progress.

        Override in subclasses (or monkeypatch in tests) to plug in real
        tool execution.
        """
        return {
            "tool_id": tool_id,
            "query": query,
            "results": [],
            "note": "placeholder — production research-tool wiring is a follow-up",
        }

    async def research(self, *, contract: TaskContract) -> ResearchResult:
        """Open a research run, iterate research tools, return the result.

        Bounded loop (``self.ops.research.max_iterations``) that:
          1. opens a gate via :func:`research_gate.open_gate`,
          2. calls each available research tool (filtered to
             :data:`research_gate.RESEARCH_TOOL_IDS`) via
             :meth:`_call_research_tool`,
          3. records each result via
             :func:`research_gate.record_tool_result`,
          4. polls coverage via :func:`research_gate.check_coverage`,
          5. closes the gate via :func:`research_gate.close_gate` and
             returns the :class:`ResearchResult` on coverage=complete,
          6. on a :class:`ResearchGateError` (budget exhausted), returns a
             ``coverage_assessment="partial"`` fallback rather than
             bubbling — so the downstream audit gets a chance to evaluate
             whatever was produced.

        Production wiring of multi-tool research (parallel calls, query
        refinement based on coverage gaps) is a follow-up; for the pilot
        the loop issues the contract goal as the query each iteration and
        relies on the gate's coverage check + iteration budget to bound
        work.
        """
        # Lazy import: keeps ``base_agent`` importable even when the
        # runtime package is being patched in tests that don't exercise
        # this method.
        from app.agents.runtime import research_gate
        from app.agents.runtime.types import ResearchGateError

        max_iterations = max(int(self.ops.research.max_iterations), 1)

        # Which tool IDs from the manifest are actually research tools?
        manifest_ids: list[str] = []
        tools_manifest = getattr(self, "_tools_manifest", None)
        if tools_manifest is not None:
            manifest_ids = list(getattr(tools_manifest, "tool_ids", []) or [])
        research_tool_ids = [
            tid for tid in manifest_ids if tid in research_gate.RESEARCH_TOOL_IDS
        ]
        # If no research tools are configured, fall through to a single
        # generic call so the gate still gets one shot at coverage.
        if not research_tool_ids:
            research_tool_ids = ["quick_research"]

        run_id = await research_gate.open_gate(
            task_contract_id=contract.id,
            contract_source=contract.source,
            agent_id=self.agent_id,
            initial_query=contract.goal,
            user_id=self.user_id,
        )

        query = contract.goal
        result: ResearchResult | None = None
        try:
            for _iteration in range(max_iterations):
                for tool_id in research_tool_ids:
                    raw = await self._call_research_tool(query=query, tool_id=tool_id)
                    try:
                        await research_gate.record_tool_result(
                            run_id=run_id,
                            tool_id=tool_id,
                            raw_result=raw,
                        )
                    except Exception:
                        logger.exception(
                            "research_gate.record_tool_result failed for "
                            "tool_id=%s run_id=%s",
                            tool_id,
                            run_id,
                        )
                try:
                    coverage = await research_gate.check_coverage(
                        run_id=run_id,
                        success_criteria=list(contract.success_criteria),
                        max_iterations=max_iterations,
                    )
                except ResearchGateError as exc:
                    logger.warning(
                        "research_gate exhausted iterations for contract %s: %s",
                        contract.id,
                        exc,
                    )
                    result = ResearchResult(
                        summary=(
                            f"Research budget exhausted after {max_iterations} "
                            f"iteration(s); falling back to partial coverage."
                        ),
                        sources=[],
                        contradictions=[],
                        coverage_assessment="partial",
                        missing_information=list(contract.success_criteria),
                    )
                    break
                if coverage is not None:
                    result = coverage
                    break
                # Refine query for the next iteration. Keep it deterministic
                # and cheap — production code can route through an LLM here.
                query = f"{contract.goal} (refining; iteration check)"

            if result is None:
                # Loop exhausted without check_coverage raising — surface a
                # partial-coverage fallback so the audit still runs.
                result = ResearchResult(
                    summary=(
                        f"Research loop exhausted {max_iterations} iteration(s) "
                        f"without reaching complete coverage."
                    ),
                    sources=[],
                    contradictions=[],
                    coverage_assessment="partial",
                    missing_information=list(contract.success_criteria),
                )

            try:
                await research_gate.close_gate(run_id=run_id, result=result)
            except Exception:
                logger.exception(
                    "research_gate.close_gate failed for run_id=%s", run_id
                )
        finally:
            # Cache the last research on the agent so a subsequent audit
            # call can reuse it without re-running research.
            object.__setattr__(self, "_last_research", result)
        # ``result`` is always set above before the finally; mypy/ty needs
        # the explicit assertion.
        assert result is not None
        return result

    async def audit(
        self,
        *,
        contract: TaskContract,
        artifacts: list[Artifact],
    ) -> AuditReport:
        """Run the deterministic LLM audit against the contract + artifacts.

        Delegates to :func:`app.agents.runtime.audit.audit_against_contract`.
        If a research result was cached during :meth:`research` it is
        re-used so the audit prompt can cite the same evidence; otherwise
        a minimal empty :class:`ResearchResult` is supplied (the audit
        prompt tolerates an empty research summary — see
        :mod:`app.agents.runtime.audit`).
        """
        # Lazy import keeps the agent importable in tests that don't touch
        # this method (and avoids a hard dependency on google.genai at
        # construction time).
        from app.agents.runtime.audit import audit_against_contract

        research = getattr(self, "_last_research", None)
        if not isinstance(research, ResearchResult):
            research = ResearchResult(
                summary="",
                sources=[],
                contradictions=[],
                coverage_assessment="complete",
                missing_information=[],
            )
        return await audit_against_contract(
            contract=contract,
            artifacts=artifacts,
            research=research,
            ops=self.ops,
        )

    async def run_step(
        self,
        *,
        item: TodoItem,
        research: ResearchResult | None,
    ) -> Artifact:
        """Execute a single :class:`TodoItem` and return an :class:`Artifact`.

        Minimal viable shape for the pilot: returns an inline placeholder
        artifact describing what was completed. Production wiring will
        route the prompt below through the agent's ADK model (via
        :meth:`google.adk.agents.Agent.run_async` with a runner-built
        :class:`InvocationContext`) and convert the model's output into a
        domain-specific artifact (doc / image / video_render / etc.).
        """
        # Build the prompt explicitly so production wiring is a drop-in
        # swap: replace the placeholder Artifact below with a real model
        # invocation that consumes ``prompt`` and returns a structured
        # Artifact payload.
        research_summary = research.summary if research is not None else "N/A"
        prompt = (
            f"Complete this step: {item.title}\n"
            f"{item.description or ''}\n"
            f"Research context: {research_summary}"
        )
        logger.debug(
            "PikarBaseAgent.run_step placeholder",
            extra={
                "agent_id": self.agent_id.value,
                "item_id": str(item.id),
                "prompt_length": len(prompt),
            },
        )
        return Artifact(
            kind="doc",
            ref=f"inline://placeholder/{item.id}",
            summary=f"Completed: {item.title}",
            payload={
                "note": (
                    "placeholder artifact — production LLM-driven step "
                    "execution is a follow-up"
                ),
                "prompt_preview": prompt[:500],
            },
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
