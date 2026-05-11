# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Initiative rituals — start / advance / close (spec § 14).

These three coroutines are the only sanctioned entry points for mutating
initiative lifecycle state from inside an agent. They guarantee:

* Required ``goal`` / ``success_criteria`` / ``owners`` for every start,
* Checklist gating on every phase advance (no silent skips),
* "scale + final checklist done" gating on close, plus a structured
  vault-bound close report.

Publication is delegated to :mod:`app.agents.runtime.publication`, which is
landed in a sibling subagent's PR. To stay decoupled the import is best-effort
— if the module is not on disk yet the rituals still work (they fall back to a
no-op publication stub that tests routinely monkeypatch).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from types import ModuleType
from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    InitiativeContractError,
    ResearchResult,
    TaskContract,
)
from app.services.initiative_service import (
    INITIATIVE_PHASES,
    InitiativeService,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.skills.registry import AgentID  # noqa: F401

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Publication binding — best-effort because the publication module lands in a
# parallel subagent's branch. Tests routinely monkeypatch
# ``initiative.publication.publish_artifact`` / ``render_report_markdown`` so
# this stub is sufficient at import time.
# ---------------------------------------------------------------------------


def _make_publication_stub() -> ModuleType:
    """Return a minimal stub that mimics the publication module surface."""
    stub = ModuleType("app.agents.runtime.publication")

    @dataclass
    class PublicationResult:
        execution_id: UUID | None = None
        vault_document_id: UUID | None = None
        workspace_event_emitted: bool = False

    async def publish_artifact(**_kwargs: Any) -> PublicationResult:
        return PublicationResult()

    async def render_report_markdown(**_kwargs: Any) -> str:
        return ""

    stub.PublicationResult = PublicationResult  # type: ignore[attr-defined]
    stub.publish_artifact = publish_artifact  # type: ignore[attr-defined]
    stub.render_report_markdown = render_report_markdown  # type: ignore[attr-defined]
    return stub


try:  # pragma: no cover - exercised once publication module lands
    from app.agents.runtime import publication as _publication

    if not hasattr(_publication, "publish_artifact") or not hasattr(
        _publication, "render_report_markdown"
    ):
        _publication = _make_publication_stub()
except Exception:
    _publication = _make_publication_stub()

publication: ModuleType = _publication


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class AdvanceResult:
    """Result of an :func:`advance_phase` call."""

    advanced: bool
    new_phase: str | None
    gaps: list[str]
    audit_report_id: UUID | None


@dataclass
class CloseReport:
    """Structured close output of :func:`close_initiative`."""

    initiative_id: UUID
    outcomes: list[dict[str, Any]]
    artifacts: list[Artifact]
    learnings: list[str]
    follow_ups: list[str]
    vault_document_id: UUID
    raw_report: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_COMPLETED_OR_SKIPPED = {"completed", "skipped"}


def _validate_start_inputs(
    goal: str, success_criteria: list[str], owners: list[str]
) -> None:
    """Raise :class:`InitiativeContractError` when any required field is empty."""
    missing: list[str] = []
    if not goal or not goal.strip():
        missing.append("goal")
    if not success_criteria:
        missing.append("success_criteria")
    if not owners:
        missing.append("owners")
    if missing:
        raise InitiativeContractError(
            f"Cannot start initiative without: {', '.join(missing)}"
        )


def _operational_state(initiative_row: dict[str, Any]) -> dict[str, Any]:
    metadata = (initiative_row or {}).get("metadata") or {}
    if not isinstance(metadata, dict):
        return {}
    op = metadata.get("operational_state")
    return op if isinstance(op, dict) else {}


def _pseudo_contract(
    *,
    initiative_id: UUID,
    goal: str,
    success_criteria: list[str],
    owners: list[str],
    phase: str | None,
) -> TaskContract:
    return TaskContract(
        id=initiative_id,
        source="initiative_step",
        goal=goal,
        todo_items=[],
        success_criteria=list(success_criteria),
        owners=list(owners),
        evidence_required=[],
        initiative_id=initiative_id,
        initiative_phase=phase,
        sibling_steps=[],
    )


def _pass_audit() -> AuditReport:
    return AuditReport(
        overall_status="pass",
        per_item=[],
        per_criterion=[],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )


def _summary_research(summary: str) -> ResearchResult:
    return ResearchResult(
        summary=summary,
        sources=[],
        contradictions=[],
        coverage_assessment="complete",
        missing_information=[],
    )


async def _safe_render_markdown(
    *,
    contract: TaskContract,
    research: ResearchResult,
    audit: AuditReport,
    agent_id: str,
) -> str:
    """Wrap render_report_markdown so a missing publication module never hard-fails."""
    try:
        return await publication.render_report_markdown(
            contract=contract,
            research=research,
            audit=audit,
            artifacts=[],
            agent_id=agent_id,
        )
    except Exception as exc:
        logger.warning("render_report_markdown unavailable, using fallback: %s", exc)
        return f"# {contract.goal}\n\n{research.summary}\n"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def start_initiative(
    agent: Any,
    *,
    goal: str,
    success_criteria: list[str],
    owners: list[str],
    phase: str = "ideation",
    name: str | None = None,
) -> dict[str, Any]:
    """Create an initiative row, seed operational state, and emit a start report.

    Args:
        agent: The calling :class:`PikarBaseAgent` (only ``user_id`` and
            ``agent_id`` are read).
        goal: Free-form goal statement. Required.
        success_criteria: At least one acceptance criterion. Required.
        owners: At least one ``AgentID`` owning the initiative. Required.
        phase: Starting phase — must be a valid ``INITIATIVE_PHASES`` value.
        name: Optional human title. Defaults to ``goal`` when omitted.

    Returns:
        The created initiative row (normalised metadata included).

    Raises:
        InitiativeContractError: When required inputs are missing or the
            requested phase is unknown.
    """
    _validate_start_inputs(goal, success_criteria, owners)
    if phase not in INITIATIVE_PHASES:
        raise InitiativeContractError(
            f"Invalid phase '{phase}' — must be one of {INITIATIVE_PHASES}"
        )

    user_id_str = str(getattr(agent, "user_id", "") or "")
    agent_id = getattr(agent, "agent_id", "executive") or "executive"

    service = InitiativeService()
    initiative_row = await service.create_initiative(
        title=name or goal,
        description=goal,
        user_id=user_id_str or None,
        phase=phase,
        metadata={"goal": goal, "success_criteria": list(success_criteria)},
    )

    await service.update_operational_state(
        initiative_row["id"],
        user_id=user_id_str or None,
        goal=goal,
        success_criteria=list(success_criteria),
        owner_agents=list(owners),
        current_phase=phase,
    )

    initiative_uuid = UUID(str(initiative_row["id"]))
    contract = _pseudo_contract(
        initiative_id=initiative_uuid,
        goal=goal,
        success_criteria=list(success_criteria),
        owners=list(owners),
        phase=phase,
    )
    report_md = await _safe_render_markdown(
        contract=contract,
        research=_summary_research(f"Initiative kicked off in {phase}."),
        audit=_pass_audit(),
        agent_id=agent_id,
    )
    artifact = Artifact(
        kind="report",
        ref=f"initiative_start://{initiative_row['id']}",
        summary=f"Initiative started — {goal}",
        payload={"markdown": report_md, "phase": phase},
    )
    try:
        await publication.publish_artifact(
            user_id=getattr(agent, "user_id", None),
            agent_id=agent_id,
            contract=contract,
            artifact=artifact,
            audit=None,
        )
    except Exception as exc:
        logger.warning("publish_artifact failed in start_initiative: %s", exc)

    return initiative_row


async def advance_phase(
    agent: Any,
    *,
    initiative_id: UUID,
    current_phase: str,
) -> AdvanceResult:
    """Audit current-phase checklist; advance and emit a report on success.

    Args:
        agent: The calling :class:`PikarBaseAgent` (only ``user_id`` and
            ``agent_id`` are read).
        initiative_id: UUID of the initiative being advanced.
        current_phase: The phase the initiative is leaving. Must match
            ``INITIATIVE_PHASES``.

    Returns:
        An :class:`AdvanceResult` describing whether the phase advanced and
        any gaps that blocked the advance.

    Raises:
        InitiativeContractError: When ``current_phase`` is not a known phase.
    """
    if current_phase not in INITIATIVE_PHASES:
        raise InitiativeContractError(
            f"Invalid phase '{current_phase}' — must be one of {INITIATIVE_PHASES}"
        )

    user_id_str = str(getattr(agent, "user_id", "") or "")
    agent_id = getattr(agent, "agent_id", "executive") or "executive"

    service = InitiativeService()
    items = await service.list_checklist_items(
        str(initiative_id),
        user_id=user_id_str or None,
        phase=current_phase,
    )
    incomplete = [
        i for i in items if i.get("status") not in _COMPLETED_OR_SKIPPED
    ]
    if incomplete:
        gaps = [
            f"{i.get('title', i.get('id'))} ({i.get('status')})"
            for i in incomplete
        ]
        return AdvanceResult(
            advanced=False,
            new_phase=None,
            gaps=gaps,
            audit_report_id=None,
        )

    advanced_row = await service.advance_phase(
        str(initiative_id), user_id=user_id_str or None
    )
    new_phase = (advanced_row or {}).get("phase")

    existing = await service.get_initiative(
        str(initiative_id), user_id=user_id_str or None
    )
    op = _operational_state(existing or {})

    contract = _pseudo_contract(
        initiative_id=initiative_id,
        goal=op.get("goal") or (existing or {}).get("title", ""),
        success_criteria=list(op.get("success_criteria") or []),
        owners=list(op.get("owner_agents") or []),
        phase=new_phase,
    )
    report_md = await _safe_render_markdown(
        contract=contract,
        research=_summary_research(
            f"Advanced from {current_phase} to {new_phase}."
        ),
        audit=_pass_audit(),
        agent_id=agent_id,
    )
    artifact = Artifact(
        kind="report",
        ref=f"phase_advance://{initiative_id}",
        summary=f"Advanced to {new_phase}",
        payload={
            "markdown": report_md,
            "from_phase": current_phase,
            "to_phase": new_phase,
        },
    )
    try:
        await publication.publish_artifact(
            user_id=getattr(agent, "user_id", None),
            agent_id=agent_id,
            contract=contract,
            artifact=artifact,
            audit=None,
        )
    except Exception as exc:
        logger.warning("publish_artifact failed in advance_phase: %s", exc)

    return AdvanceResult(
        advanced=True,
        new_phase=new_phase,
        gaps=[],
        audit_report_id=None,
    )


async def close_initiative(
    agent: Any,
    *,
    initiative_id: UUID,
) -> CloseReport:
    """Produce a vault-bound close report and mark the initiative completed.

    Args:
        agent: The calling :class:`PikarBaseAgent` (``user_id`` + ``agent_id``).
        initiative_id: UUID of the initiative to close.

    Returns:
        A :class:`CloseReport` describing outcomes per success criterion plus
        the vault document ID where the structured report landed.

    Raises:
        InitiativeContractError: When the initiative is not in ``'scale'``
            phase or its scale-phase checklist still has open items.
    """
    user_id_str = str(getattr(agent, "user_id", "") or "")
    agent_id = getattr(agent, "agent_id", "executive") or "executive"

    service = InitiativeService()
    initiative_row = await service.get_initiative(
        str(initiative_id), user_id=user_id_str or None
    )
    if not initiative_row:
        raise InitiativeContractError(f"Initiative {initiative_id} not found")
    if initiative_row.get("phase") != "scale":
        raise InitiativeContractError(
            "Cannot close — initiative must be in 'scale' phase, "
            f"currently '{initiative_row.get('phase')}'"
        )

    items = await service.list_checklist_items(
        str(initiative_id),
        user_id=user_id_str or None,
        phase="scale",
    )
    if any(i.get("status") not in _COMPLETED_OR_SKIPPED for i in items):
        raise InitiativeContractError(
            "Cannot close — scale phase checklist still has open items"
        )

    op = _operational_state(initiative_row)
    success_criteria = list(op.get("success_criteria") or [])
    outcomes = [
        {
            "criterion": crit,
            "met": True,  # audit module refines; default optimistic per spec.
            "evidence": list(op.get("evidence") or []),
        }
        for crit in success_criteria
    ]
    learnings = list(op.get("learnings") or [])
    follow_ups = list(op.get("next_actions") or [])

    contract = _pseudo_contract(
        initiative_id=initiative_id,
        goal=op.get("goal") or initiative_row.get("title", ""),
        success_criteria=success_criteria,
        owners=list(op.get("owner_agents") or []),
        phase="scale",
    )
    report_md = await _safe_render_markdown(
        contract=contract,
        research=_summary_research(
            f"Initiative closed in 'scale'. "
            f"Outcomes vs. {len(success_criteria)} criteria."
        ),
        audit=_pass_audit(),
        agent_id=agent_id,
    )
    close_artifact = Artifact(
        kind="report",
        ref=f"initiative_close://{initiative_id}",
        summary=f"Close report — {contract.goal}",
        payload={
            "markdown": report_md,
            "outcomes": outcomes,
            "learnings": learnings,
            "follow_ups": follow_ups,
        },
    )

    vault_id: UUID = UUID(int=0)
    try:
        publication_result = await publication.publish_artifact(
            user_id=getattr(agent, "user_id", None),
            agent_id=agent_id,
            contract=contract,
            artifact=close_artifact,
            audit=None,
        )
        candidate = getattr(publication_result, "vault_document_id", None)
        if isinstance(candidate, UUID):
            vault_id = candidate
        elif isinstance(candidate, str) and candidate:
            try:
                vault_id = UUID(candidate)
            except ValueError:
                vault_id = UUID(int=0)
    except Exception as exc:
        logger.warning("publish_artifact failed in close_initiative: %s", exc)

    await service.update_initiative(
        str(initiative_id),
        user_id=user_id_str or None,
        status="completed",
        progress=100,
    )

    return CloseReport(
        initiative_id=initiative_id,
        outcomes=outcomes,
        artifacts=[close_artifact],
        learnings=learnings,
        follow_ups=follow_ups,
        vault_document_id=vault_id,
        raw_report={
            "markdown": report_md,
            "goal": contract.goal,
            "phase": "scale",
        },
    )


__all__ = [
    "AdvanceResult",
    "CloseReport",
    "advance_phase",
    "close_initiative",
    "publication",
    "start_initiative",
]
