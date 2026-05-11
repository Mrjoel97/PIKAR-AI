# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Shared contracts for the agent runtime.

These types are imported across the runtime package, BaseAgent, and the
section-specific modules (lifecycle, research_gate, persona_gate, ...).
They are intentionally lightweight: frozen dataclasses for value objects
and pydantic BaseModels for anything that crosses a JSON boundary
(DB rows, SSE events, audit reports).

Tasks 9-16 of the agent operating model W1+W2 plan are collected here so
downstream modules can import a single, stable namespace.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.skills.registry import AgentID

# ---------------------------------------------------------------------------
# Mode + TodoItem + StepSummary  (Task 9)
# ---------------------------------------------------------------------------

Mode = Literal["direct", "initiative"]


@dataclass(frozen=True)
class TodoItem:
    """A single checklist item inside a TaskContract."""

    id: UUID
    title: str
    description: str | None
    status: Literal["pending", "in_progress", "completed", "blocked", "skipped"]
    evidence: list[dict]
    sort_order: int


@dataclass(frozen=True)
class StepSummary:
    """Read-only sibling-step view exposed inside a TaskContract."""

    id: UUID
    title: str
    status: str
    assigned_agent_id: str | None


# ---------------------------------------------------------------------------
# TaskContract  (Task 10)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskContract:
    """Frozen contract describing a unit of work executed by an agent.

    Initiative mode only - direct mode uses :class:`DirectRequest`. Sibling
    steps are read-only context; mutations require :func:`propose_plan_change`.
    """

    id: UUID
    source: Literal["initiative_step", "department_task"]
    goal: str
    todo_items: list[TodoItem]
    success_criteria: list[str]
    owners: list[AgentID]
    evidence_required: list[str]
    initiative_id: UUID | None
    initiative_phase: str | None
    sibling_steps: list[StepSummary]


# ---------------------------------------------------------------------------
# DirectRequest + Artifact  (Task 11)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DirectRequest:
    """Lightweight envelope for a direct-mode (non-initiative) user turn."""

    user_id: UUID
    agent_id: AgentID
    persona_id: str
    message: str
    session_id: UUID | None


@dataclass(frozen=True)
class Artifact:
    """A concrete deliverable produced inside execute_task / respond_directly.

    `kind` matches the publication-sink dispatcher in
    app/agents/runtime/publication.py (e.g. ``"video_render"``, ``"image"``,
    ``"doc"``, ``"report"``, ``"data_query"``).
    """

    kind: str
    ref: str
    summary: str
    payload: dict | None


# ---------------------------------------------------------------------------
# Source + ResearchResult  (Task 12)
# ---------------------------------------------------------------------------


class Source(BaseModel):
    """A single cited source backing a research run."""

    url: str
    title: str
    key_claim: str
    retrieved_at: datetime


class ResearchResult(BaseModel):
    """Structured result persisted to ``agent_research_runs.result``.

    `coverage_assessment == "complete"` is the gate that unblocks
    non-research tool calls inside ``execute_task``.
    """

    summary: str
    sources: list[Source]
    contradictions: list[str]
    coverage_assessment: Literal["complete", "partial"]
    missing_information: list[str]


# ---------------------------------------------------------------------------
# ItemAudit + CriterionAudit + PolicyViolation + AuditReport  (Task 13)
# ---------------------------------------------------------------------------


class ItemAudit(BaseModel):
    """Per-TodoItem result inside an AuditReport."""

    item_id: UUID
    status: Literal["pass", "fail", "partial"]
    evidence_pointers: list[str]
    gaps: list[str]


class CriterionAudit(BaseModel):
    """Per-success-criterion result inside an AuditReport."""

    criterion: str
    met: bool
    justification: str


class PolicyViolation(BaseModel):
    """A policy block raised during ``before_tool_callback``.

    Populated by the persona gate, action-threshold check, or rate limiter
    and appended to the audit report so enforcement is *visible*.
    """

    kind: Literal["tool_denied", "threshold_exceeded", "rate_limited"]
    detail: str
    tool_id: str | None


class AuditReport(BaseModel):
    """Output of ``audit_against_contract`` - persisted to ``agent_audit_reports``."""

    overall_status: Literal["pass", "fail", "partial"]
    per_item: list[ItemAudit]
    per_criterion: list[CriterionAudit]
    gaps: list[str]
    policy_violations: list[PolicyViolation] = []
    recoverable: bool
    next_action: Literal["submit", "retry", "escalate"]


# ---------------------------------------------------------------------------
# ActionThresholds + RateLimits + PersonaPolicy  (Task 14)
# ---------------------------------------------------------------------------


class ActionThresholds(BaseModel):
    """Action-risk thresholds enforced inside ``before_tool_callback``."""

    max_spend_usd: float | None
    require_approval_for_external_send: bool
    custom: dict


class RateLimits(BaseModel):
    """Per-persona rate limits enforced inside ``before_tool_callback``."""

    requests_per_minute: int | None
    tokens_per_day: int | None


class PersonaPolicy(BaseModel):
    """Resolved per-(user, persona) policy. Mirrors ``persona_policies`` rows.

    `allowed_tool_ids` may be the literal string ``"*"`` to mean *no allow-list*
    (deny-only mode), matching the JSONB default in the table DDL.
    """

    persona_id: str
    allowed_tool_ids: list[str] | Literal["*"]
    denied_tool_ids: list[str]
    action_thresholds: ActionThresholds
    rate_limits: RateLimits
    prompt_fragments: list[str]
    classifier_default_mode: Mode | None
    initiative_phases_blocked: list[str]


# ---------------------------------------------------------------------------
# ClassifierResult  (Task 15)
# ---------------------------------------------------------------------------


class ClassifierResult(BaseModel):
    """Output of :mod:`app.agents.runtime.task_router`.

    `signal` records which of the three layers (override, rule heuristics,
    LLM fallback) produced the decision - used for tuning.
    """

    mode: Mode
    confidence: float
    reasoning: str
    signal: Literal["override", "rule", "llm"]


# ---------------------------------------------------------------------------
# WorkspaceProgressEvent + WorkspaceArtifactEvent  (Task 16)
# ---------------------------------------------------------------------------


class WorkspaceProgressEvent(BaseModel):
    """Progress tick emitted to the per-user workspace SSE channel."""

    kind: Literal["progress"] = "progress"
    agent_id: str
    contract_id: UUID | None
    item: str
    status: Literal["started", "in_progress", "blocked"]


class WorkspaceArtifactEvent(BaseModel):
    """Artifact event emitted whenever ``publish_artifact`` produces output.

    `artifact_kind` is open-ended on purpose: known values include
    ``"video_render"``, ``"image"``, ``"doc"``, ``"report"``, ``"data_query"``.
    """

    kind: Literal["artifact"] = "artifact"
    agent_id: str
    contract_id: UUID | None
    artifact_kind: str
    ref: str
    summary: str
    preview_url: str | None


# ---------------------------------------------------------------------------
# Exception classes
# ---------------------------------------------------------------------------


class InitiativeContractError(RuntimeError):
    """Raised when a :class:`TaskContract` is malformed, missing required
    initiative metadata, or used outside the initiative-mode lifecycle."""


class PersonaPolicyError(RuntimeError):
    """Raised when a :class:`PersonaPolicy` cannot be resolved, is invalid,
    or denies a tool call inside ``before_tool_callback``."""


class ResearchGateError(RuntimeError):
    """Raised when the research-completion gate blocks a non-research tool
    call before :class:`ResearchResult` with ``coverage_assessment="complete"``
    has been recorded."""


__all__ = [
    "ActionThresholds",
    "AgentID",
    "Artifact",
    "AuditReport",
    "ClassifierResult",
    "CriterionAudit",
    "DirectRequest",
    "InitiativeContractError",
    "ItemAudit",
    "Mode",
    "PersonaPolicy",
    "PersonaPolicyError",
    "PolicyViolation",
    "RateLimits",
    "ResearchGateError",
    "ResearchResult",
    "Source",
    "StepSummary",
    "TaskContract",
    "TodoItem",
    "WorkspaceArtifactEvent",
    "WorkspaceProgressEvent",
]
