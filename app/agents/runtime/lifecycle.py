# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""ADK lifecycle callback factories for :class:`PikarBaseAgent`.

Each public function is a *factory*: it takes the owning agent instance and
returns the actual callback the ADK runtime invokes. The factory shape lets
each callback close over ``agent`` (and therefore over ``agent.ops``,
``agent.agent_id``, ``agent.user_id``, ``agent.persona_id``) without
smuggling globals or building a separate registry.

Section B replaces the no-op stubs from Section A with the real enforcement
stack defined in spec § 5. Each callback body delegates to the eight runtime
submodules (skill_injection, memory_retrieval, task_router, persona_gate,
research_gate, audit, compaction, handoff, plus optional publication for
Section D) — no business logic lives in this file, only:

* ordering: which gate runs first, which writes to state first, etc.;
* defensive try/except boundaries (Task 43): failures from a single
  submodule must never break a real agent turn, with the explicit
  exception of intentional blocks (``InitiativeContractError`` in
  ``before_agent``, ``PersonaPolicyError`` / ``ResearchGateError`` in
  ``before_tool``);
* normalisation of dict-shaped state values into typed runtime models
  (e.g. dict -> :class:`HandoffPacket`).

ADK callback signatures (from ``google.adk.agents.base_agent``):

* ``before_agent_callback(callback_context) -> google.genai.types.Content | None``
* ``before_tool_callback(tool, args, tool_context) -> dict | None``
* ``after_tool_callback(tool, args, tool_context, tool_response) -> dict | None``
* ``after_agent_callback(callback_context) -> google.genai.types.Content | None``

ADK awaits the return value if it is awaitable, so each callback returned
by these factories is an ``async def`` coroutine. Returning ``None``
signals "no override" — the model / tool runs normally.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from uuid import UUID

# Module-level imports so unit tests can ``patch("app.agents.runtime.lifecycle.<X>")``
# without having to dig through ``app.agents.runtime.<X>`` directly. Every
# enforcement module the four callbacks delegate to is reachable from here.
from app.agents.runtime import (
    audit,
    compaction,
    handoff,
    memory_retrieval,
    persona_gate,
    research_gate,
    skill_injection,
    task_router,
)
from app.agents.runtime.types import (
    DirectRequest,
    InitiativeContractError,
    PersonaPolicyError,
    ResearchGateError,
)

# Section D's ``publication`` module ships separately. Guard the import so a
# missing module degrades to a silent no-op rather than breaking the runtime.
try:  # pragma: no cover - import path exercised once Section D lands
    from app.agents.runtime import publication  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - expected during Section B
    publication = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    # Forward reference only — avoids a circular import because
    # PikarBaseAgent itself imports from this module to wire callbacks.
    from app.agents.base_agent import PikarBaseAgent


__all__ = [
    "after_agent",
    "after_tool",
    "apply_injected_blocks",
    "before_agent",
    "before_tool",
]


# ---------------------------------------------------------------------------
# Session-state keys (framework-owned; prefixed ``_runtime_`` so the
# distinction from user-/agent-set state is obvious at every read site).
# ---------------------------------------------------------------------------

_RUNTIME_BLOCKS_KEY = "_runtime_injected_blocks"
_RUNTIME_CLASSIFIER_MODE_KEY = "_runtime_classifier_mode"
_RUNTIME_CLASSIFIER_SIGNAL_KEY = "_runtime_classifier_signal"
_RUNTIME_CONTRACT_KEY = "_runtime_task_contract"
_RUNTIME_CONTRACT_ID_KEY = "_runtime_contract_id"
_RUNTIME_ARTIFACTS_KEY = "_runtime_artifacts"
_RUNTIME_RESEARCH_RESULT_KEY = "_runtime_research_result"
_RUNTIME_INITIATIVE_ID_KEY = "_runtime_initiative_id"
_RUNTIME_INITIATIVE_PHASE_KEY = "_runtime_initiative_phase"
_RUNTIME_PENDING_HANDOFF_KEY = "last_handoff_packet"
_RUNTIME_TOOL_FAILURES_KEY = "_runtime_tool_failures"
_RUNTIME_VIOLATIONS_KEY = "_runtime_audit_violations"
_RUNTIME_CALLBACK_ERRORS_KEY = "_runtime_callback_errors"
_RUNTIME_PERSONA_POLICY_KEY = "_runtime_persona_policy"
_RUNTIME_COMPACTION_SUMMARY_KEY = "_runtime_compaction_summary"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe_state(ctx: Any) -> dict[str, Any]:
    """Return a mutable dict view of ``ctx.state`` (creating one if missing).

    ADK's ``CallbackContext.state`` is a dict in production but tests pass a
    plain ``MagicMock`` whose ``.state`` may be a plain dict, missing, or
    re-bound mid-test. We tolerate all three so the rest of the body can
    treat state as a single uniform mapping.
    """
    state = getattr(ctx, "state", None)
    if isinstance(state, dict):
        return state
    # If state is something else (e.g. a MagicMock without ``__setitem__``),
    # synthesize a local dict; the callers tolerate this because everything
    # they care about (the blocks block, classifier mode, etc.) is keyed off
    # this same dict instance.
    new: dict[str, Any] = {}
    try:
        ctx.state = new  # type: ignore[attr-defined]
    except Exception:
        pass
    return new


def _extract_user_text(ctx: Any) -> str:
    """Pull the latest user message text off an ADK callback context.

    ADK exposes ``callback_context.user_content`` as a
    ``google.genai.types.Content`` with a list of ``Part``s. Each part may
    or may not have ``.text``. We concatenate every part that has text so
    multi-part messages still classify correctly.

    Falls back to ``state["latest_user_text"]`` for code paths that don't
    populate ``user_content`` (e.g. background agent invocations).
    """
    content = getattr(ctx, "user_content", None)
    if content is not None:
        parts = getattr(content, "parts", None) or []
        chunks: list[str] = []
        for part in parts:
            text = getattr(part, "text", None)
            if isinstance(text, str) and text:
                chunks.append(text)
        if chunks:
            return "\n".join(chunks).strip()
    # Fallback to a state hint some pipelines set explicitly.
    state = getattr(ctx, "state", None)
    if isinstance(state, dict):
        hint = state.get("latest_user_text")
        if isinstance(hint, str) and hint:
            return hint.strip()
    return ""


async def _maybe_await(value: Any) -> Any:
    """Await ``value`` if it's a coroutine/awaitable; else return as-is.

    Tests mock the runtime submodules with plain ``MagicMock`` (not
    ``AsyncMock``) in places, so the lifecycle must tolerate both shapes.
    Returns the resolved value either way.
    """
    if inspect.isawaitable(value):
        return await value
    return value


async def _dispatch_async(callback: Callable[..., Any], arg_or_args: Any) -> Any:
    """Drive a lifecycle callback from a test with positional args.

    * For ``before_agent`` / ``after_agent``: pass the callback_context as a
      single positional value: ``_dispatch_async(cb, ctx)``.
    * For ``before_tool`` / ``after_tool``: pass a tuple ``(tool, args, ctx)``
      or ``(tool, args, ctx, response)``: ``_dispatch_async(cb, (tool, args, ctx))``.

    Awaits the callback's return if it is awaitable (the real lifecycle
    callbacks here are ``async def``) and returns the resolved value.
    """
    if isinstance(arg_or_args, (tuple, list)):
        result = callback(*arg_or_args)
    else:
        result = callback(arg_or_args)
    if inspect.isawaitable(result):
        result = await result
    return result


def _compose_blocks(*blocks: str) -> str:
    """Join non-empty markdown blocks with a blank line between each."""
    parts = [b.strip() for b in blocks if isinstance(b, str) and b.strip()]
    return "\n\n".join(parts)


def _record_callback_error(state: dict[str, Any], where: str, exc: Exception) -> None:
    """Append ``"<where>: <exc>"`` to the per-session callback-errors buffer.

    Used by every callback's outer try/except so a transient submodule
    failure leaves an audit trail (Task 43) without crashing the turn.
    """
    bucket = state.get(_RUNTIME_CALLBACK_ERRORS_KEY)
    if not isinstance(bucket, list):
        bucket = []
        state[_RUNTIME_CALLBACK_ERRORS_KEY] = bucket
    bucket.append(f"{where}: {type(exc).__name__}: {exc}")


def _wrap_user_request(
    text: str,
    agent: Any,
    *,
    classifier_mode: str,
    contract: Any | None,
) -> Any:
    """Return either the open TaskContract (initiative) or a fresh DirectRequest.

    When ``contract`` is present and ``classifier_mode == "initiative"`` we
    treat the open contract as the canonical request envelope. Otherwise a
    :class:`DirectRequest` is synthesized from the user text + agent identity.
    """
    if classifier_mode == "initiative" and contract is not None:
        return contract

    # Synthesize a DirectRequest. user_id / agent_id are stored on the agent
    # as plain attributes; tolerate non-UUID values for unit tests where the
    # agent is a MagicMock.
    raw_user = getattr(agent, "user_id", None)
    if isinstance(raw_user, UUID):
        user_id: UUID = raw_user
    else:
        try:
            user_id = UUID(str(raw_user)) if raw_user else UUID(int=0)
        except (ValueError, AttributeError, TypeError):
            user_id = UUID(int=0)
    return DirectRequest(
        user_id=user_id,
        agent_id=getattr(agent, "agent_id", None),
        persona_id=str(getattr(agent, "persona_id", "") or ""),
        message=text,
        session_id=None,
    )


def _coerce_handoff_packet(raw: Any) -> Any | None:
    """Validate a dict-shaped handoff packet into a :class:`HandoffPacket`.

    Returns ``None`` if ``raw`` cannot be validated. We import HandoffPacket
    lazily because it lives in ``app.agents.handoff_packet`` (not the
    runtime package) and pulling it in at module top would slow the import
    chain for unrelated callers.
    """
    if raw is None:
        return None
    try:
        from app.agents.handoff_packet import HandoffPacket
    except ImportError as exc:  # pragma: no cover - HandoffPacket is shipped
        logger.debug("[lifecycle] HandoffPacket import failed: %s", exc)
        return None
    if isinstance(raw, HandoffPacket):
        return raw
    if isinstance(raw, dict):
        try:
            return HandoffPacket.model_validate(raw)
        except Exception as exc:
            logger.debug("[lifecycle] HandoffPacket validation failed: %s", exc)
            return None
    return None


async def _verify_approval_token(
    *,
    tool_id: str,
    ticket: str,
    token: str | None,
) -> None:
    """Validate ``token`` against an open approval ``ticket`` for ``tool_id``.

    Raises :class:`PersonaPolicyError` when the token is missing or the
    underlying confirmation token cannot be consumed. Always called from
    inside :func:`before_tool`'s ordered gate chain after the action
    threshold check returned a "ticket required" hint.
    """
    if not token:
        raise PersonaPolicyError(
            f"tool '{tool_id}' requires approval ticket '{ticket}' but no "
            f"approval_token was supplied"
        )
    try:
        from app.services.confirmation_tokens import consume_confirmation_token
    except ImportError as exc:  # pragma: no cover - service ships with app
        raise PersonaPolicyError(f"approval-token service unavailable: {exc}") from exc
    try:
        payload = await consume_confirmation_token(token)
    except Exception as exc:
        raise PersonaPolicyError(
            f"approval token check failed for tool '{tool_id}': {exc}"
        ) from exc
    if not payload:
        raise PersonaPolicyError(
            f"approval token for tool '{tool_id}' (ticket {ticket}) is "
            f"missing or already consumed"
        )


async def _persist_task_execution(
    agent: Any,
    state: dict[str, Any],
) -> None:
    """Hook for Section D's ``agent_task_executions`` persistence.

    Section B does not ship the actual writer — Section D layers it in on
    top of the audit + handoff payloads collected here. The function is a
    stable name so tests can patch it with ``AsyncMock`` while Section D
    keeps the contract.
    """
    del agent, state  # implementation provided by Section D
    return None


def apply_injected_blocks(state: dict[str, Any], instruction: str) -> str:
    """Prepend the markdown blocks accumulated in ``state`` to ``instruction``.

    Called by ``PikarBaseAgent``'s ``before_model`` callback (or a similar
    integration point) so the model receives the assembled context block
    in front of the agent's normal instruction.

    Returns ``instruction`` unchanged when no blocks were injected for the
    current turn (or when ``state`` is not a mapping).
    """
    if not isinstance(state, dict):
        return instruction
    blob = state.get(_RUNTIME_BLOCKS_KEY)
    if not blob or not isinstance(blob, str):
        return instruction
    return f"{blob.strip()}\n\n{instruction}"


# ---------------------------------------------------------------------------
# before_agent factory (Tasks 29, 30, 44)
# ---------------------------------------------------------------------------


def before_agent(agent: PikarBaseAgent) -> Callable[..., Any]:
    """Build the ``before_agent_callback`` for ``agent``.

    Orchestrates (in order):

    1. Extract the latest user text from ``callback_context.user_content``.
    2. Load the persona policy (db-first, falls back to registry defaults).
    3. Classify the request (override / rule / persona / LLM waterfall).
    4. Wrap the user input as a ``TaskContract`` (initiative mode with an
       open contract) or a fresh :class:`DirectRequest`.
    5. Run skill injection, memory retrieval, and persona-fragment
       rendering. Concatenate any non-empty blocks plus a cached
       compaction summary into ``state["_runtime_injected_blocks"]`` so the
       before-model integration point can prepend them.
    6. Return ``None`` (ADK convention for "let the model run").

    Per Task 43, every failure inside the body is swallowed and logged
    EXCEPT :class:`InitiativeContractError`, which signals a malformed
    contract and must propagate so the executive can re-route.
    """

    async def _callback(callback_context: Any) -> None:
        state = _safe_state(callback_context)
        try:
            text = _extract_user_text(callback_context)

            # Pre-existing open contract (Section D / executive seeds this).
            contract = state.get(_RUNTIME_CONTRACT_KEY)

            # 1. Persona policy -------------------------------------------
            persona_policy = None
            try:
                persona_policy = await _maybe_await(
                    persona_gate.load_persona_policy(
                        getattr(agent, "user_id", None),
                        getattr(agent, "persona_id", "") or "",
                    )
                )
                state[_RUNTIME_PERSONA_POLICY_KEY] = persona_policy
            except InitiativeContractError:
                raise
            except Exception as exc:
                logger.debug("[before_agent] persona policy load failed: %s", exc)
                _record_callback_error(state, "before_agent.persona", exc)

            # 2. Task router ----------------------------------------------
            classifier = None
            try:
                classifier = await _maybe_await(
                    task_router.classify(
                        text,
                        ops=getattr(agent, "ops", None),
                        persona_policy=persona_policy,
                        session_has_open_contract=contract is not None,
                    )
                )
            except InitiativeContractError:
                raise
            except Exception as exc:
                logger.debug("[before_agent] classifier failed: %s", exc)
                _record_callback_error(state, "before_agent.router", exc)

            classifier_mode = getattr(classifier, "mode", None) or "direct"
            classifier_signal = getattr(classifier, "signal", None) or "rule"
            state[_RUNTIME_CLASSIFIER_MODE_KEY] = classifier_mode
            state[_RUNTIME_CLASSIFIER_SIGNAL_KEY] = classifier_signal

            # 3. Wrap the request as TaskContract or DirectRequest --------
            request = _wrap_user_request(
                text, agent, classifier_mode=classifier_mode, contract=contract
            )

            # 4. Skill injection ------------------------------------------
            skills_block = ""
            try:
                skills_block = await _maybe_await(
                    skill_injection.match_and_inject(
                        request, agent, mode=classifier_mode
                    )
                )
            except InitiativeContractError:
                raise
            except Exception as exc:
                logger.debug("[before_agent] skill_injection failed: %s", exc)
                _record_callback_error(state, "before_agent.skill_injection", exc)

            # 5. Memory layer-3 retrieval ---------------------------------
            memory_block = ""
            try:
                memory_block = await _maybe_await(
                    memory_retrieval.retrieve_relevant_history(request, agent)
                )
            except InitiativeContractError:
                raise
            except Exception as exc:
                logger.debug("[before_agent] memory_retrieval failed: %s", exc)
                _record_callback_error(state, "before_agent.memory_retrieval", exc)

            # 6. Persona-fragment rendering -------------------------------
            persona_block = ""
            try:
                # persona_gate.apply_prompt_fragments accepts a PersonaPolicy
                # or (historical fallback) a persona_id string.
                if persona_policy is not None:
                    persona_block = await _maybe_await(
                        persona_gate.apply_prompt_fragments(persona_policy)
                    )
                else:
                    persona_block = await _maybe_await(
                        persona_gate.apply_prompt_fragments(
                            getattr(agent, "persona_id", "")
                        )
                    )
            except InitiativeContractError:
                raise
            except Exception as exc:
                logger.debug("[before_agent] persona_fragments failed: %s", exc)
                _record_callback_error(state, "before_agent.persona_fragments", exc)

            # 7. Compaction summary already cached on the session by a prior
            #    after_agent run is folded into the same blocks blob so the
            #    next model call sees it as background.
            compaction_summary = state.get(_RUNTIME_COMPACTION_SUMMARY_KEY)
            compaction_block = (
                f"## Prior conversation summary\n\n{compaction_summary}"
                if isinstance(compaction_summary, str) and compaction_summary
                else ""
            )

            # Compose all non-empty blocks into a single blob.
            blob = _compose_blocks(
                compaction_block, skills_block, memory_block, persona_block
            )
            if blob:
                state[_RUNTIME_BLOCKS_KEY] = blob

        except InitiativeContractError:
            # Intentional contract block — surface to the executive.
            raise
        except Exception as exc:
            logger.exception("[before_agent] unexpected failure: %s", exc)
            _record_callback_error(state, "before_agent", exc)
        return None

    _callback.__name__ = f"before_agent::{getattr(agent.agent_id, 'value', 'unknown')}"
    return _callback


# ---------------------------------------------------------------------------
# before_tool factory (Tasks 31, 32, 33, 34)
# ---------------------------------------------------------------------------


def before_tool(agent: PikarBaseAgent) -> Callable[..., Any]:
    """Build the ``before_tool_callback`` for ``agent``.

    Gate order (each gate runs only if the previous passed):

    1. **Persona allow/deny** — :func:`persona_gate.check_tool_allowed`.
       Raises :class:`PersonaPolicyError` on deny; we record the violation
       and propagate so the agent surface can show a refusal.
    2. **Action threshold** — :func:`persona_gate.check_action_threshold`.
       Same propagation rule; the call may also return a dict shaped
       ``{"required": True, "ticket": "..."}`` meaning an approval token
       must be presented for this exact call.
    3. **Approval token** — when (2) signaled a ticket, look up the token
       on ``tool_context.state`` (key ``approval_token::<tool_name>``) and
       verify it against the approvals service.
    4. **Research gate** — if a TaskContract is bound to the session and
       the tool is not in :data:`research_gate.RESEARCH_TOOL_IDS`, refuse
       the call while the gate is open. Raises
       :class:`ResearchGateError`.

    Returning ``None`` lets the tool execute. Per Task 43, only
    :class:`PersonaPolicyError` and :class:`ResearchGateError` propagate —
    every other exception is swallowed and the tool proceeds (with the
    failure recorded on session state for downstream visibility).
    """

    async def _callback(
        tool: Any,
        args: dict[str, Any],
        tool_context: Any,
    ) -> dict[str, Any] | None:
        state = _safe_state(tool_context)
        tool_id = getattr(tool, "name", None) or ""
        args = args if isinstance(args, dict) else {}

        # 1. Persona allow/deny ------------------------------------------
        policy = state.get(_RUNTIME_PERSONA_POLICY_KEY)
        try:
            await _maybe_await(persona_gate.check_tool_allowed(tool_id, policy))
        except PersonaPolicyError:
            # Intentional block — record + re-raise so the agent sees it.
            try:
                violations = state.setdefault(_RUNTIME_VIOLATIONS_KEY, [])
                persona_gate.record_violation(
                    violations,
                    "tool_denied",
                    f"persona denied tool '{tool_id}'",
                    tool_id,
                )
            except Exception as exc:
                logger.debug("[before_tool] record_violation failed: %s", exc)
            raise
        except Exception as exc:
            logger.warning("[before_tool] check_tool_allowed failed: %s", exc)
            _record_callback_error(state, "before_tool.check_tool_allowed", exc)

        # 2. Action threshold --------------------------------------------
        threshold_hint: dict[str, Any] | None = None
        try:
            # Pass kwargs to honour the test contract (Task 32):
            # check_action_threshold(tool_id=, tool_args=, persona_id=)
            # The runtime impl accepts (tool_id, tool_args, policy) too —
            # call the signature flexibly so both shapes are supported.
            try:
                threshold_hint = await _maybe_await(
                    persona_gate.check_action_threshold(
                        tool_id=tool_id,
                        tool_args=args,
                        persona_id=getattr(agent, "persona_id", ""),
                    )
                )
            except TypeError:
                # Fallback to the production positional signature.
                threshold_hint = await _maybe_await(
                    persona_gate.check_action_threshold(tool_id, args, policy)
                )
        except PersonaPolicyError:
            try:
                violations = state.setdefault(_RUNTIME_VIOLATIONS_KEY, [])
                persona_gate.record_violation(
                    violations,
                    "threshold_exceeded",
                    f"action threshold blocked tool '{tool_id}'",
                    tool_id,
                )
            except Exception as exc:
                logger.debug("[before_tool] record_violation failed: %s", exc)
            raise
        except Exception as exc:
            logger.warning("[before_tool] check_action_threshold failed: %s", exc)
            _record_callback_error(state, "before_tool.check_action_threshold", exc)

        # 3. Approval token (only when threshold signaled one is required).
        if isinstance(threshold_hint, dict) and threshold_hint.get("required"):
            ticket = str(threshold_hint.get("ticket") or "")
            token = None
            # Tools may pass the token in args, but our convention is to
            # store the user's submitted token on tool_context.state under
            # a per-tool key so it survives across model retries.
            token = state.get(f"approval_token::{tool_id}") or args.get(
                "approval_token"
            )
            try:
                await _verify_approval_token(
                    tool_id=tool_id, ticket=ticket, token=token
                )
            except PersonaPolicyError:
                try:
                    violations = state.setdefault(_RUNTIME_VIOLATIONS_KEY, [])
                    persona_gate.record_violation(
                        violations,
                        "threshold_exceeded",
                        f"approval token missing/invalid for tool '{tool_id}'",
                        tool_id,
                    )
                except Exception as exc:
                    logger.debug("[before_tool] record_violation failed: %s", exc)
                raise
            except Exception as exc:
                logger.warning("[before_tool] approval token check failed: %s", exc)
                _record_callback_error(state, "before_tool.approval", exc)

        # 4. Research gate -----------------------------------------------
        try:
            contract_id = state.get(_RUNTIME_CONTRACT_ID_KEY)
            if contract_id:
                # is_open / is_research_tool may be async (real impl) or
                # sync (test MagicMock). Tolerate both via _maybe_await.
                gate_open = await _maybe_await(
                    research_gate.is_open(agent, contract_id)
                )
                if gate_open:
                    # Some test mocks expose `is_research_tool`; production
                    # uses the RESEARCH_TOOL_IDS frozenset directly.
                    is_research = False
                    is_research_fn = getattr(research_gate, "is_research_tool", None)
                    if callable(is_research_fn):
                        is_research = bool(await _maybe_await(is_research_fn(tool_id)))
                    else:
                        is_research = tool_id in getattr(
                            research_gate, "RESEARCH_TOOL_IDS", frozenset()
                        )
                    if not is_research:
                        raise ResearchGateError(
                            f"tool '{tool_id}' is blocked while the research "
                            f"gate is open for contract {contract_id}"
                        )
        except ResearchGateError:
            try:
                violations = state.setdefault(_RUNTIME_VIOLATIONS_KEY, [])
                persona_gate.record_violation(
                    violations,
                    "tool_denied",
                    f"research gate blocked tool '{tool_id}'",
                    tool_id,
                )
            except Exception as exc:
                logger.debug("[before_tool] record_violation failed: %s", exc)
            raise
        except Exception as exc:
            logger.warning("[before_tool] research gate check failed: %s", exc)
            _record_callback_error(state, "before_tool.research_gate", exc)

        return None

    _callback.__name__ = f"before_tool::{getattr(agent.agent_id, 'value', 'unknown')}"
    return _callback


# ---------------------------------------------------------------------------
# after_tool factory (Task 35)
# ---------------------------------------------------------------------------


def after_tool(agent: PikarBaseAgent) -> Callable[..., Any]:
    """Build the ``after_tool_callback`` for ``agent``.

    Responsibilities (Task 35 + Task 43):

    1. If the tool is a research tool AND a TaskContract is in session
       state, forward the raw response to
       :func:`research_gate.record_tool_result`.
    2. Emit a workspace progress event via Section D's publication module
       (no-op until that module ships).
    3. Log tool failures (``tool_response`` carries ``"error"``) onto the
       per-session ``_runtime_tool_failures`` buffer for retry book-keeping.

    Nothing in here propagates: a publication outage cannot mask the
    tool's actual output.
    """

    async def _callback(
        tool: Any,
        args: dict[str, Any],
        tool_context: Any,
        tool_response: Any,
    ) -> None:
        state = _safe_state(tool_context)
        tool_id = getattr(tool, "name", None) or ""

        try:
            # 1. Research result accumulation ----------------------------
            contract_id = state.get(_RUNTIME_CONTRACT_ID_KEY)
            research_ids = getattr(research_gate, "RESEARCH_TOOL_IDS", frozenset())
            if contract_id and tool_id in research_ids:
                try:
                    await _maybe_await(
                        research_gate.record_tool_result(
                            contract_id=contract_id,
                            tool_id=tool_id,
                            result=tool_response,
                        )
                    )
                except Exception as exc:
                    logger.warning("[after_tool] record_tool_result failed: %s", exc)
                    _record_callback_error(state, "after_tool.record_tool_result", exc)

                # After accumulating results, check coverage. If complete,
                # close the gate so subsequent execution tools may run.
                try:
                    coverage_fn = getattr(research_gate, "check_coverage", None)
                    if callable(coverage_fn):
                        coverage = await _maybe_await(
                            coverage_fn(contract_id=contract_id)
                        )
                        if coverage is not None:
                            state[_RUNTIME_RESEARCH_RESULT_KEY] = coverage
                            close_fn = getattr(research_gate, "close_gate", None)
                            if callable(close_fn):
                                await _maybe_await(
                                    close_fn(contract_id=contract_id, result=coverage)
                                )
                except Exception as exc:
                    logger.debug("[after_tool] coverage/close_gate skipped: %s", exc)
                    _record_callback_error(state, "after_tool.check_coverage", exc)

            # 2. Workspace progress event --------------------------------
            if publication is not None:
                emit = getattr(publication, "emit_progress_event", None)
                if callable(emit):
                    try:
                        await _maybe_await(
                            emit(
                                user_id=getattr(agent, "user_id", None),
                                agent_id=getattr(agent, "agent_id", None),
                                item=tool_id,
                                status="in_progress",
                            )
                        )
                    except Exception as exc:
                        logger.debug("[after_tool] emit_progress_event failed: %s", exc)
                        _record_callback_error(
                            state, "after_tool.emit_progress_event", exc
                        )

            # 3. Tool failure logging ------------------------------------
            if isinstance(tool_response, dict) and tool_response.get("error"):
                failures = state.setdefault(_RUNTIME_TOOL_FAILURES_KEY, [])
                failures.append(
                    {
                        "tool_id": tool_id,
                        "args": args if isinstance(args, dict) else {},
                        "error": str(tool_response.get("error")),
                    }
                )

        except Exception as exc:
            logger.exception("[after_tool] unexpected failure: %s", exc)
            _record_callback_error(state, "after_tool", exc)
        return None

    _callback.__name__ = f"after_tool::{getattr(agent.agent_id, 'value', 'unknown')}"
    return _callback


# ---------------------------------------------------------------------------
# after_agent factory (Tasks 36, 37, 38)
# ---------------------------------------------------------------------------


def after_agent(agent: PikarBaseAgent) -> Callable[..., Any]:
    """Build the ``after_agent_callback`` for ``agent``.

    Responsibilities (Tasks 36-38 + 43):

    1. **Audit** — if the turn produced artifacts (Task 36) call
       :func:`audit.audit_against_contract`, persist via
       :func:`audit.persist_audit_report`, and attach a summary to the
       initiative checklist evidence via
       :func:`audit.attach_audit_summary_to_evidence`.
    2. **Compaction** — :func:`compaction.maybe_compact` (Task 37). When it
       returns a result, the summary is cached on ``session.state`` so the
       next turn picks it up via :func:`before_agent`.
    3. **Handoff** — when a packet is staged on
       ``state["last_handoff_packet"]`` and we're inside an initiative,
       validate it into a :class:`HandoffPacket` and durably log it via
       :func:`handoff.record_handoff` (Task 38).
    4. **Persistence** — call the Section D hook
       :func:`_persist_task_execution` so downstream code can store the
       audit / handoff / classifier signals on
       ``agent_task_executions``.

    Per Task 43, nothing propagates: a failure here cannot break a turn
    that already produced output.
    """

    async def _callback(callback_context: Any) -> None:
        state = _safe_state(callback_context)
        try:
            classifier_mode = state.get(_RUNTIME_CLASSIFIER_MODE_KEY) or "direct"
            contract = state.get(_RUNTIME_CONTRACT_KEY)
            artifacts = state.get(_RUNTIME_ARTIFACTS_KEY) or []
            research_result = state.get(_RUNTIME_RESEARCH_RESULT_KEY)

            # 1. Audit ----------------------------------------------------
            # Run audit when the turn produced any artifacts (initiative
            # mode is the common case; direct-mode artifact production is
            # rare but supported — spec § 8).
            audit_report = None
            if artifacts:
                try:
                    audit_report = await _maybe_await(
                        audit.audit_against_contract(
                            contract=contract,
                            artifacts=artifacts,
                            research=research_result,
                            ops=getattr(agent, "ops", None),
                        )
                    )
                except Exception as exc:
                    logger.warning("[after_agent] audit failed: %s", exc)
                    _record_callback_error(state, "after_agent.audit", exc)

                if audit_report is not None:
                    contract_id = getattr(contract, "id", None) if contract else None
                    try:
                        await _maybe_await(
                            audit.persist_audit_report(
                                audit_report,
                                agent_id=getattr(agent, "agent_id", None),
                                task_contract_id=contract_id,
                            )
                        )
                    except Exception as exc:
                        logger.warning(
                            "[after_agent] persist_audit_report failed: %s", exc
                        )
                        _record_callback_error(
                            state, "after_agent.persist_audit_report", exc
                        )

                    if contract is not None:
                        try:
                            await _maybe_await(
                                audit.attach_audit_summary_to_evidence(
                                    contract=contract, report=audit_report
                                )
                            )
                        except Exception as exc:
                            logger.warning(
                                "[after_agent] attach_audit_summary failed: %s",
                                exc,
                            )
                            _record_callback_error(
                                state, "after_agent.attach_audit_summary", exc
                            )

            # 2. Compaction ----------------------------------------------
            session = getattr(callback_context, "session", None)
            if session is not None:
                try:
                    compaction_cfg = getattr(
                        getattr(agent, "ops", None), "compaction", None
                    )
                    compaction_result = await _maybe_await(
                        compaction.maybe_compact(session, compaction_cfg)
                    )
                    if compaction_result is not None:
                        # compaction.maybe_compact already mirrors the
                        # summary onto session.state, but ``state`` here may
                        # be a different mapping than ``session.state`` in
                        # contrived test setups — write to both so the
                        # next before_agent picks it up regardless.
                        summary_text = getattr(compaction_result, "summary", None)
                        if summary_text:
                            state[_RUNTIME_COMPACTION_SUMMARY_KEY] = summary_text
                except Exception as exc:
                    logger.warning("[after_agent] compaction failed: %s", exc)
                    _record_callback_error(state, "after_agent.compaction", exc)

            # 3. Handoff recording ---------------------------------------
            raw_packet = state.get(_RUNTIME_PENDING_HANDOFF_KEY)
            initiative_id = state.get(_RUNTIME_INITIATIVE_ID_KEY)
            phase = state.get(_RUNTIME_INITIATIVE_PHASE_KEY)
            if raw_packet and (classifier_mode == "initiative" or initiative_id):
                packet_obj = _coerce_handoff_packet(raw_packet)
                if packet_obj is not None:
                    try:
                        await _maybe_await(
                            handoff.record_handoff(
                                packet=packet_obj,
                                initiative_id=initiative_id,
                                phase=phase,
                            )
                        )
                    except Exception as exc:
                        logger.warning("[after_agent] record_handoff failed: %s", exc)
                        _record_callback_error(state, "after_agent.record_handoff", exc)

            # 4. Section D persistence hook -----------------------------
            try:
                await _maybe_await(_persist_task_execution(agent, state))
            except Exception as exc:
                logger.warning("[after_agent] _persist_task_execution failed: %s", exc)
                _record_callback_error(state, "after_agent.persist_task_execution", exc)

        except Exception as exc:
            logger.exception("[after_agent] unexpected failure: %s", exc)
            _record_callback_error(state, "after_agent", exc)
        return None

    _callback.__name__ = f"after_agent::{getattr(agent.agent_id, 'value', 'unknown')}"
    return _callback
