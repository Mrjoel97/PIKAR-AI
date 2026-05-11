# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Consolidated tests for ``app.agents.runtime.types``.

Covers all types added in Tasks 9-16 of the agent operating model W1+W2 plan:
  - Mode (Literal)
  - TodoItem, StepSummary, TaskContract, DirectRequest, Artifact (frozen)
  - Source, ResearchResult, ItemAudit, CriterionAudit, PolicyViolation,
    AuditReport, ActionThresholds, RateLimits, PersonaPolicy,
    ClassifierResult, WorkspaceProgressEvent, WorkspaceArtifactEvent (pydantic)
  - InitiativeContractError, PersonaPolicyError, ResearchGateError
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from typing import get_args
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Task 9: Mode + TodoItem + StepSummary
# ---------------------------------------------------------------------------


def test_mode_literal_values():
    from app.agents.runtime.types import Mode

    assert set(get_args(Mode)) == {"direct", "initiative"}


def test_todo_item_is_frozen_and_immutable():
    from app.agents.runtime.types import TodoItem

    item = TodoItem(
        id=uuid4(),
        title="Draft outline",
        description=None,
        status="pending",
        evidence=[],
        sort_order=0,
    )
    assert item.title == "Draft outline"
    assert item.status == "pending"
    with pytest.raises(FrozenInstanceError):
        item.title = "Mutated"  # type: ignore[misc]


def test_step_summary_carries_assigned_agent():
    from app.agents.runtime.types import StepSummary

    summary = StepSummary(
        id=uuid4(),
        title="Run financial model",
        status="in_progress",
        assigned_agent_id="FIN",
    )
    assert summary.assigned_agent_id == "FIN"


def test_step_summary_allows_unassigned():
    from app.agents.runtime.types import StepSummary

    summary = StepSummary(
        id=uuid4(),
        title="Backlog step",
        status="pending",
        assigned_agent_id=None,
    )
    assert summary.assigned_agent_id is None


def test_step_summary_is_frozen():
    from app.agents.runtime.types import StepSummary

    summary = StepSummary(
        id=uuid4(),
        title="x",
        status="pending",
        assigned_agent_id=None,
    )
    with pytest.raises(FrozenInstanceError):
        summary.title = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Task 10: TaskContract
# ---------------------------------------------------------------------------


def test_task_contract_initiative_step():
    from app.agents.runtime.types import StepSummary, TaskContract, TodoItem
    from app.skills.registry import AgentID

    cid = uuid4()
    init_id = uuid4()
    todo = TodoItem(
        id=uuid4(),
        title="Outline",
        description=None,
        status="pending",
        evidence=[],
        sort_order=0,
    )
    sibling = StepSummary(
        id=uuid4(), title="Sibling", status="pending", assigned_agent_id="MKT"
    )

    contract = TaskContract(
        id=cid,
        source="initiative_step",
        goal="Produce Q3 forecast",
        todo_items=[todo],
        success_criteria=["revenue numbers cited", "variance < 5%"],
        owners=[AgentID.FIN],
        evidence_required=["research_summary", "audit_report"],
        initiative_id=init_id,
        initiative_phase="validation",
        sibling_steps=[sibling],
    )

    assert contract.id == cid
    assert contract.source == "initiative_step"
    assert contract.owners == [AgentID.FIN]
    assert contract.sibling_steps[0].assigned_agent_id == "MKT"


def test_task_contract_is_frozen():
    from app.agents.runtime.types import TaskContract
    from app.skills.registry import AgentID

    contract = TaskContract(
        id=uuid4(),
        source="department_task",
        goal="Triage support backlog",
        todo_items=[],
        success_criteria=[],
        owners=[AgentID.SUPP],
        evidence_required=[],
        initiative_id=None,
        initiative_phase=None,
        sibling_steps=[],
    )

    with pytest.raises(FrozenInstanceError):
        contract.goal = "tampered"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Task 11: DirectRequest + Artifact
# ---------------------------------------------------------------------------


def test_direct_request_with_session():
    from app.agents.runtime.types import DirectRequest
    from app.skills.registry import AgentID

    uid = uuid4()
    sid = uuid4()
    req = DirectRequest(
        user_id=uid,
        agent_id=AgentID.FIN,
        persona_id="founder",
        message="What's our Q3 revenue?",
        session_id=sid,
    )
    assert req.message.startswith("What's")
    assert req.session_id == sid


def test_direct_request_without_session():
    from app.agents.runtime.types import DirectRequest
    from app.skills.registry import AgentID

    req = DirectRequest(
        user_id=uuid4(),
        agent_id=AgentID.SUPP,
        persona_id="cs_lead",
        message="summarize ticket #42",
        session_id=None,
    )
    assert req.session_id is None


def test_direct_request_is_frozen():
    from app.agents.runtime.types import DirectRequest
    from app.skills.registry import AgentID

    req = DirectRequest(
        user_id=uuid4(),
        agent_id=AgentID.FIN,
        persona_id="founder",
        message="hi",
        session_id=None,
    )
    with pytest.raises(FrozenInstanceError):
        req.message = "bye"  # type: ignore[misc]


def test_artifact_payload_optional():
    from app.agents.runtime.types import Artifact

    a = Artifact(
        kind="video_render",
        ref="vault://videos/abc.mp4",
        summary="60s explainer",
        payload=None,
    )
    assert a.kind == "video_render"
    assert a.payload is None

    b = Artifact(
        kind="doc",
        ref="docs/123",
        summary="brief",
        payload={"word_count": 480},
    )
    assert b.payload == {"word_count": 480}


def test_artifact_is_frozen():
    from app.agents.runtime.types import Artifact

    a = Artifact(kind="doc", ref="r", summary="s", payload=None)
    with pytest.raises(FrozenInstanceError):
        a.kind = "image"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Task 12: Source + ResearchResult
# ---------------------------------------------------------------------------


def test_research_result_complete_with_sources():
    from app.agents.runtime.types import ResearchResult, Source

    src = Source(
        url="https://example.com/q3",
        title="Q3 results",
        key_claim="Revenue grew 12% QoQ.",
        retrieved_at=datetime.now(timezone.utc),
    )
    result = ResearchResult(
        summary="Revenue growth is on track.",
        sources=[src],
        contradictions=[],
        coverage_assessment="complete",
        missing_information=[],
    )
    assert result.coverage_assessment == "complete"
    assert result.sources[0].title == "Q3 results"


def test_research_result_partial_with_gaps():
    from app.agents.runtime.types import ResearchResult

    result = ResearchResult(
        summary="Some context found.",
        sources=[],
        contradictions=["price differs across two sources"],
        coverage_assessment="partial",
        missing_information=["margin data", "headcount"],
    )
    assert result.coverage_assessment == "partial"
    assert "headcount" in result.missing_information


def test_research_result_rejects_unknown_coverage_value():
    from app.agents.runtime.types import ResearchResult

    with pytest.raises(ValidationError):
        ResearchResult(
            summary="",
            sources=[],
            contradictions=[],
            coverage_assessment="kinda",  # type: ignore[arg-type]
            missing_information=[],
        )


def test_source_roundtrip():
    from app.agents.runtime.types import Source

    src = Source(
        url="https://example.com",
        title="t",
        key_claim="c",
        retrieved_at=datetime.now(timezone.utc),
    )
    dumped = src.model_dump()
    restored = Source.model_validate(dumped)
    assert restored == src


def test_research_result_roundtrip():
    from app.agents.runtime.types import ResearchResult, Source

    src = Source(
        url="https://example.com",
        title="t",
        key_claim="c",
        retrieved_at=datetime.now(timezone.utc),
    )
    result = ResearchResult(
        summary="s",
        sources=[src],
        contradictions=["x"],
        coverage_assessment="complete",
        missing_information=[],
    )
    restored = ResearchResult.model_validate(result.model_dump())
    assert restored == result


# ---------------------------------------------------------------------------
# Task 13: ItemAudit + CriterionAudit + PolicyViolation + AuditReport
# ---------------------------------------------------------------------------


def test_item_audit_pass_with_evidence():
    from app.agents.runtime.types import ItemAudit

    audit = ItemAudit(
        item_id=uuid4(),
        status="pass",
        evidence_pointers=["vault://reports/123#section-2"],
        gaps=[],
    )
    assert audit.status == "pass"


def test_criterion_audit_met():
    from app.agents.runtime.types import CriterionAudit

    c = CriterionAudit(
        criterion="variance < 5%",
        met=True,
        justification="Computed variance = 3.1% on line 28.",
    )
    assert c.met


def test_policy_violation_known_kind():
    from app.agents.runtime.types import PolicyViolation

    v = PolicyViolation(
        kind="tool_denied",
        detail="sendgrid_send not in persona allow-list",
        tool_id="sendgrid_send",
    )
    assert v.kind == "tool_denied"


def test_policy_violation_rejects_unknown_kind():
    from app.agents.runtime.types import PolicyViolation

    with pytest.raises(ValidationError):
        PolicyViolation(
            kind="mystery",  # type: ignore[arg-type]
            detail="unknown",
            tool_id=None,
        )


def test_audit_report_pass_recoverable_submit():
    from app.agents.runtime.types import (
        AuditReport,
        CriterionAudit,
        ItemAudit,
    )

    report = AuditReport(
        overall_status="pass",
        per_item=[
            ItemAudit(
                item_id=uuid4(),
                status="pass",
                evidence_pointers=["vault://x"],
                gaps=[],
            )
        ],
        per_criterion=[
            CriterionAudit(criterion="x", met=True, justification="ok")
        ],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )
    assert report.overall_status == "pass"
    assert report.next_action == "submit"


def test_audit_report_policy_violations_defaults_to_empty():
    from app.agents.runtime.types import AuditReport

    report = AuditReport(
        overall_status="pass",
        per_item=[],
        per_criterion=[],
        gaps=[],
        recoverable=True,
        next_action="submit",
    )
    assert report.policy_violations == []


def test_audit_report_rejects_bad_next_action():
    from app.agents.runtime.types import AuditReport

    with pytest.raises(ValidationError):
        AuditReport(
            overall_status="fail",
            per_item=[],
            per_criterion=[],
            gaps=["nothing audited"],
            policy_violations=[],
            recoverable=False,
            next_action="ignore",  # type: ignore[arg-type]
        )


def test_audit_report_roundtrip():
    from app.agents.runtime.types import (
        AuditReport,
        CriterionAudit,
        ItemAudit,
        PolicyViolation,
    )

    iid = uuid4()
    report = AuditReport(
        overall_status="partial",
        per_item=[
            ItemAudit(
                item_id=iid,
                status="partial",
                evidence_pointers=["v://x"],
                gaps=["missing source"],
            )
        ],
        per_criterion=[
            CriterionAudit(criterion="c", met=False, justification="not yet")
        ],
        gaps=["x"],
        policy_violations=[
            PolicyViolation(
                kind="rate_limited",
                detail="exceeded RPM",
                tool_id="search",
            )
        ],
        recoverable=True,
        next_action="retry",
    )
    restored = AuditReport.model_validate(report.model_dump())
    assert restored == report


# ---------------------------------------------------------------------------
# Task 14: ActionThresholds + RateLimits + PersonaPolicy
# ---------------------------------------------------------------------------


def test_persona_policy_with_explicit_allow_list():
    from app.agents.runtime.types import (
        ActionThresholds,
        PersonaPolicy,
        RateLimits,
    )

    p = PersonaPolicy(
        persona_id="founder",
        allowed_tool_ids=["search", "calc"],
        denied_tool_ids=["sendgrid_send"],
        action_thresholds=ActionThresholds(
            max_spend_usd=500.0,
            require_approval_for_external_send=True,
            custom={"max_emails": 10},
        ),
        rate_limits=RateLimits(requests_per_minute=60, tokens_per_day=100_000),
        prompt_fragments=["You are speaking as founder."],
        classifier_default_mode="direct",
        initiative_phases_blocked=[],
    )
    assert p.allowed_tool_ids == ["search", "calc"]
    assert p.classifier_default_mode == "direct"


def test_persona_policy_wildcard_allow():
    from app.agents.runtime.types import (
        ActionThresholds,
        PersonaPolicy,
        RateLimits,
    )

    p = PersonaPolicy(
        persona_id="admin",
        allowed_tool_ids="*",
        denied_tool_ids=[],
        action_thresholds=ActionThresholds(
            max_spend_usd=None,
            require_approval_for_external_send=False,
            custom={},
        ),
        rate_limits=RateLimits(requests_per_minute=None, tokens_per_day=None),
        prompt_fragments=[],
        classifier_default_mode="initiative",
        initiative_phases_blocked=[],
    )
    assert p.allowed_tool_ids == "*"
    assert p.classifier_default_mode == "initiative"


def test_persona_policy_rejects_bad_default_mode():
    from app.agents.runtime.types import (
        ActionThresholds,
        PersonaPolicy,
        RateLimits,
    )

    with pytest.raises(ValidationError):
        PersonaPolicy(
            persona_id="x",
            allowed_tool_ids=["a"],
            denied_tool_ids=[],
            action_thresholds=ActionThresholds(
                max_spend_usd=None,
                require_approval_for_external_send=False,
                custom={},
            ),
            rate_limits=RateLimits(
                requests_per_minute=None, tokens_per_day=None
            ),
            prompt_fragments=[],
            classifier_default_mode="lol",  # type: ignore[arg-type]
            initiative_phases_blocked=[],
        )


def test_persona_policy_roundtrip():
    from app.agents.runtime.types import (
        ActionThresholds,
        PersonaPolicy,
        RateLimits,
    )

    p = PersonaPolicy(
        persona_id="founder",
        allowed_tool_ids="*",
        denied_tool_ids=["x"],
        action_thresholds=ActionThresholds(
            max_spend_usd=100.0,
            require_approval_for_external_send=True,
            custom={"k": "v"},
        ),
        rate_limits=RateLimits(requests_per_minute=10, tokens_per_day=1000),
        prompt_fragments=["frag"],
        classifier_default_mode=None,
        initiative_phases_blocked=["launch"],
    )
    restored = PersonaPolicy.model_validate(p.model_dump())
    assert restored == p


def test_action_thresholds_roundtrip():
    from app.agents.runtime.types import ActionThresholds

    a = ActionThresholds(
        max_spend_usd=None,
        require_approval_for_external_send=False,
        custom={"a": 1},
    )
    assert ActionThresholds.model_validate(a.model_dump()) == a


def test_rate_limits_roundtrip():
    from app.agents.runtime.types import RateLimits

    r = RateLimits(requests_per_minute=5, tokens_per_day=None)
    assert RateLimits.model_validate(r.model_dump()) == r


# ---------------------------------------------------------------------------
# Task 15: ClassifierResult
# ---------------------------------------------------------------------------


def test_classifier_result_override():
    from app.agents.runtime.types import ClassifierResult

    r = ClassifierResult(
        mode="direct",
        confidence=1.0,
        reasoning="User typed /quick prefix.",
        signal="override",
    )
    assert r.mode == "direct"
    assert r.signal == "override"


def test_classifier_result_llm_low_confidence():
    from app.agents.runtime.types import ClassifierResult

    r = ClassifierResult(
        mode="initiative",
        confidence=0.62,
        reasoning="Verbs 'plan' and 'launch' present.",
        signal="llm",
    )
    assert r.signal == "llm"


def test_classifier_result_rejects_invalid_signal():
    from app.agents.runtime.types import ClassifierResult

    with pytest.raises(ValidationError):
        ClassifierResult(
            mode="direct",
            confidence=0.5,
            reasoning="",
            signal="vibes",  # type: ignore[arg-type]
        )


def test_classifier_result_rejects_invalid_mode():
    from app.agents.runtime.types import ClassifierResult

    with pytest.raises(ValidationError):
        ClassifierResult(
            mode="hybrid",  # type: ignore[arg-type]
            confidence=0.5,
            reasoning="",
            signal="rule",
        )


def test_classifier_result_roundtrip():
    from app.agents.runtime.types import ClassifierResult

    r = ClassifierResult(
        mode="direct", confidence=0.9, reasoning="r", signal="rule"
    )
    assert ClassifierResult.model_validate(r.model_dump()) == r


# ---------------------------------------------------------------------------
# Task 16: WorkspaceProgressEvent + WorkspaceArtifactEvent
# ---------------------------------------------------------------------------


def test_progress_event_started():
    from app.agents.runtime.types import WorkspaceProgressEvent

    cid = uuid4()
    evt = WorkspaceProgressEvent(
        agent_id="FIN",
        contract_id=cid,
        item="Outline forecast",
        status="started",
    )
    assert evt.kind == "progress"
    assert evt.contract_id == cid


def test_progress_event_rejects_bad_status():
    from app.agents.runtime.types import WorkspaceProgressEvent

    with pytest.raises(ValidationError):
        WorkspaceProgressEvent(
            agent_id="FIN",
            contract_id=None,
            item="x",
            status="finished",  # type: ignore[arg-type]
        )


def test_artifact_event_video_render_with_preview():
    from app.agents.runtime.types import WorkspaceArtifactEvent

    evt = WorkspaceArtifactEvent(
        agent_id="CONT",
        contract_id=uuid4(),
        artifact_kind="video_render",
        ref="vault://videos/abc.mp4",
        summary="60s demo",
        preview_url="https://cdn.pikar/abc.png",
    )
    assert evt.kind == "artifact"
    assert evt.artifact_kind == "video_render"


def test_artifact_event_preview_optional():
    from app.agents.runtime.types import WorkspaceArtifactEvent

    evt = WorkspaceArtifactEvent(
        agent_id="DATA",
        contract_id=None,
        artifact_kind="data_query",
        ref="bq://result/42",
        summary="98 rows",
        preview_url=None,
    )
    assert evt.preview_url is None


def test_progress_event_default_kind_is_locked():
    """`kind` is a Literal default; model must not accept a different value."""
    from app.agents.runtime.types import WorkspaceProgressEvent

    with pytest.raises(ValidationError):
        WorkspaceProgressEvent(
            kind="artifact",  # type: ignore[arg-type]
            agent_id="FIN",
            contract_id=None,
            item="x",
            status="started",
        )


def test_artifact_event_default_kind_is_locked():
    from app.agents.runtime.types import WorkspaceArtifactEvent

    with pytest.raises(ValidationError):
        WorkspaceArtifactEvent(
            kind="progress",  # type: ignore[arg-type]
            agent_id="X",
            contract_id=None,
            artifact_kind="doc",
            ref="r",
            summary="s",
            preview_url=None,
        )


def test_progress_event_json_roundtrip():
    """kind discriminator must round-trip through model_dump(mode='json')."""
    from app.agents.runtime.types import WorkspaceProgressEvent

    cid = uuid4()
    evt = WorkspaceProgressEvent(
        agent_id="FIN",
        contract_id=cid,
        item="step",
        status="in_progress",
    )
    dumped = evt.model_dump(mode="json")
    assert dumped["kind"] == "progress"
    # contract_id should round-trip as a string in mode='json'
    assert dumped["contract_id"] == str(cid)
    restored = WorkspaceProgressEvent.model_validate(dumped)
    assert restored == evt


def test_artifact_event_json_roundtrip():
    from app.agents.runtime.types import WorkspaceArtifactEvent

    evt = WorkspaceArtifactEvent(
        agent_id="CONT",
        contract_id=None,
        artifact_kind="image",
        ref="vault://img/1.png",
        summary="logo",
        preview_url="https://cdn/preview.png",
    )
    dumped = evt.model_dump(mode="json")
    assert dumped["kind"] == "artifact"
    restored = WorkspaceArtifactEvent.model_validate(dumped)
    assert restored == evt


# ---------------------------------------------------------------------------
# Exception classes
# ---------------------------------------------------------------------------


def test_exceptions_importable_and_inherit_runtimeerror():
    from app.agents.runtime.types import (
        InitiativeContractError,
        PersonaPolicyError,
        ResearchGateError,
    )

    assert issubclass(InitiativeContractError, RuntimeError)
    assert issubclass(PersonaPolicyError, RuntimeError)
    assert issubclass(ResearchGateError, RuntimeError)


def test_exceptions_can_be_raised():
    from app.agents.runtime.types import (
        InitiativeContractError,
        PersonaPolicyError,
        ResearchGateError,
    )

    with pytest.raises(InitiativeContractError):
        raise InitiativeContractError("bad contract")
    with pytest.raises(PersonaPolicyError):
        raise PersonaPolicyError("bad policy")
    with pytest.raises(ResearchGateError):
        raise ResearchGateError("gate closed")


# ---------------------------------------------------------------------------
# Convenience helpers (UUID type is correct on dataclass fields)
# ---------------------------------------------------------------------------


def test_todo_item_id_is_uuid_type():
    from app.agents.runtime.types import TodoItem

    item = TodoItem(
        id=uuid4(),
        title="t",
        description=None,
        status="pending",
        evidence=[],
        sort_order=0,
    )
    assert isinstance(item.id, UUID)
