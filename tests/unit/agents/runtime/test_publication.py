# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Consolidated tests for ``app.agents.runtime.publication`` (Tasks 82-86, 100, 102, 103).

Covers:
  * Task 82 — ``render_report_markdown`` emits the Layer-2 template (spec §11).
  * Task 83 — ``emit_progress_event`` is a thin wrapper around
    ``workspace_event_bus.publish``.
  * Task 84 — ``publish_artifact`` upserts ``agent_task_executions`` on first
    artifact and appends on subsequent ones.
  * Task 85 — ``_vault_publish`` calls ``knowledge_service.add_document`` for
    vault-bound kinds and is skipped for ephemeral kinds.
  * Task 86 — ``publish_artifact`` always emits a ``WorkspaceArtifactEvent``.
  * Task 100 — ``publish_artifact`` handles ``DirectRequest`` (mode='direct').
  * Task 102 — ``director_service.notify_render_complete`` builds a
    ``video_render`` artifact and calls ``publish_artifact``.
  * Task 103 — ``vertex_video_service.on_render_finished`` routes through
    ``director_service.notify_render_complete``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.agents.runtime import publication
from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    CriterionAudit,
    DirectRequest,
    ItemAudit,
    PolicyViolation,
    ResearchResult,
    Source,
    TaskContract,
    TodoItem,
    WorkspaceArtifactEvent,
    WorkspaceProgressEvent,
)
from app.skills.registry import AgentID

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _todo(title: str = "step", status: str = "completed") -> TodoItem:
    return TodoItem(
        id=uuid4(),
        title=title,
        description=None,
        status=status,  # type: ignore[arg-type]
        evidence=[],
        sort_order=0,
    )


def _contract(
    *,
    todo_items: list[TodoItem] | None = None,
    success_criteria: list[str] | None = None,
    contract_id: UUID | None = None,
    initiative_id: UUID | None = None,
) -> TaskContract:
    return TaskContract(
        id=contract_id or uuid4(),
        source="initiative_step",
        goal="Forecast Q3 revenue",
        todo_items=list(todo_items or []),
        success_criteria=list(success_criteria or []),
        owners=[AgentID.FIN],
        evidence_required=["draft_artifact"],
        initiative_id=initiative_id if initiative_id is not None else uuid4(),
        initiative_phase="validation",
        sibling_steps=[],
    )


def _audit_pass() -> AuditReport:
    return AuditReport(
        overall_status="pass",
        per_item=[],
        per_criterion=[],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )


def _supabase_mocks(monkeypatch, *, prior_rows: list[dict] | None = None) -> MagicMock:
    """Wire ``publication.get_service_client`` + ``execute_async`` mocks.

    The first ``execute_async`` call (the select for prior artifacts) returns
    ``prior_rows`` if supplied; the upsert call returns a row with a new id.
    """
    fake_client = MagicMock()
    table = MagicMock()
    table.upsert.return_value = table
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.single.return_value = table
    fake_client.table = MagicMock(return_value=table)

    upsert_id = uuid4()

    async def fake_execute_async(q, op_name=None):
        if op_name == "agent_task_executions.select":
            return MagicMock(data=list(prior_rows or []))
        return MagicMock(data=[{"id": str(upsert_id)}])

    monkeypatch.setattr(publication, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(publication, "execute_async", fake_execute_async)
    # Track the upsert id on the returned client so tests can assert against it.
    fake_client._upsert_id = upsert_id  # type: ignore[attr-defined]
    fake_client._table = table  # type: ignore[attr-defined]
    return fake_client


# ---------------------------------------------------------------------------
# Task 82 — render_report_markdown (Layer-2 template, spec §11)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_render_report_markdown_contains_all_required_sections() -> None:
    contract = _contract(
        todo_items=[
            _todo("Pull historicals", status="completed"),
            _todo("Build model", status="completed"),
        ],
        success_criteria=["Forecast within 5 percent", "Three scenarios"],
    )
    research = ResearchResult(
        summary="Revenue grew 18 percent YoY across all segments.",
        sources=[
            Source(
                url="https://example.com/r1",
                title="ARR trend",
                key_claim="ARR plus 18 percent",
                retrieved_at=datetime(2026, 5, 11, 10, 0, tzinfo=timezone.utc),
            )
        ],
        contradictions=["Q1 vs Q2 churn delta unresolved"],
        coverage_assessment="complete",
        missing_information=[],
    )
    audit = _audit_pass()
    artifacts = [
        Artifact(
            kind="agent_report",
            ref="vault://draft-forecast",
            summary="Forecast doc",
            payload={},
        )
    ]

    md = await publication.render_report_markdown(
        contract=contract,
        research=research,
        audit=audit,
        artifacts=artifacts,
        agent_id=AgentID.FIN,
    )

    for required in (
        "## Goal",
        "## To-Do Outcomes",
        "## Success Criteria",
        "## Research Summary",
        "### Sources",
        "### Contradictions Flagged",
        "## Artifacts",
        "## Audit Report",
        "## Policy Notes",
        "## Follow-ups",
    ):
        assert required in md, f"missing section: {required}"
    assert "Forecast Q3 revenue" in md
    assert "Pull historicals" in md
    assert "Build model" in md
    assert "ARR trend" in md
    assert "Q1 vs Q2 churn delta unresolved" in md


@pytest.mark.asyncio
async def test_render_report_markdown_renders_audit_per_criterion() -> None:
    contract = _contract(success_criteria=["accuracy"])
    research = ResearchResult(
        summary="",
        sources=[],
        contradictions=[],
        coverage_assessment="complete",
        missing_information=[],
    )
    audit = AuditReport(
        overall_status="partial",
        per_item=[],
        per_criterion=[
            CriterionAudit(criterion="accuracy", met=False, justification="off by 12%")
        ],
        gaps=["accuracy gap"],
        policy_violations=[
            PolicyViolation(kind="tool_denied", detail="blocked send", tool_id="email")
        ],
        recoverable=True,
        next_action="retry",
    )
    md = await publication.render_report_markdown(
        contract=contract,
        research=research,
        audit=audit,
        artifacts=[],
        agent_id="financial",
    )
    assert "FAIL" in md
    assert "off by 12%" in md
    assert "tool_denied" in md
    assert "accuracy gap" in md  # surfaced as a follow-up
    assert "_no artifacts produced_" in md


@pytest.mark.asyncio
async def test_render_report_markdown_handles_missing_research_and_audit() -> None:
    contract = _contract(success_criteria=[])
    md = await publication.render_report_markdown(
        contract=contract,
        research=None,
        audit=None,
        artifacts=[],
        agent_id="financial",
    )
    assert "_no research captured_" in md
    assert "_no audit recorded_" in md


# ---------------------------------------------------------------------------
# Task 83 — emit_progress_event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_emit_progress_event_publishes_workspace_progress(monkeypatch) -> None:
    user_id = uuid4()
    contract_id = uuid4()
    publish = AsyncMock()
    monkeypatch.setattr(publication.workspace_event_bus, "publish", publish)

    await publication.emit_progress_event(
        user_id=user_id,
        agent_id=AgentID.FIN,
        contract_id=contract_id,
        item="Pull income statement",
        status="in_progress",
    )

    publish.assert_awaited_once()
    args, _ = publish.await_args
    assert args[0] == user_id
    event = args[1]
    assert isinstance(event, WorkspaceProgressEvent)
    assert event.item == "Pull income statement"
    assert event.status == "in_progress"
    assert event.agent_id == AgentID.FIN.value
    assert event.contract_id == contract_id


@pytest.mark.asyncio
async def test_emit_progress_event_allows_null_contract(monkeypatch) -> None:
    publish = AsyncMock()
    monkeypatch.setattr(publication.workspace_event_bus, "publish", publish)
    await publication.emit_progress_event(
        user_id=uuid4(),
        agent_id="marketing",
        item="draft tweet",
        status="started",
    )
    publish.assert_awaited_once()
    event = publish.await_args.args[1]
    assert event.contract_id is None
    assert event.kind == "progress"


@pytest.mark.asyncio
async def test_emit_progress_event_swallows_publish_failures(monkeypatch) -> None:
    async def boom(*_args, **_kwargs):
        raise RuntimeError("redis down")

    monkeypatch.setattr(publication.workspace_event_bus, "publish", boom)
    # Should not raise.
    await publication.emit_progress_event(
        user_id=uuid4(),
        agent_id="financial",
        item="anything",
        status="in_progress",
    )


# ---------------------------------------------------------------------------
# Task 84 — publish_artifact upserts agent_task_executions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_artifact_inserts_execution_row_initiative_mode(
    monkeypatch,
) -> None:
    user_id = uuid4()
    contract = _contract(todo_items=[_todo("x")], success_criteria=["sent"])
    artifact = Artifact(
        kind="agent_report",
        ref="vault://draft",
        summary="Newsletter draft",
        payload={"chars": 1200},
    )

    fake_client = _supabase_mocks(monkeypatch)
    monkeypatch.setattr(publication.workspace_event_bus, "publish", AsyncMock())
    monkeypatch.setattr(publication, "_vault_publish", AsyncMock(return_value=None))

    result = await publication.publish_artifact(
        user_id=user_id,
        agent_id=AgentID.MKT,
        contract=contract,
        artifact=artifact,
        audit=None,
    )

    assert isinstance(result, publication.PublicationResult)
    assert result.execution_id == fake_client._upsert_id
    fake_client.table.assert_any_call("agent_task_executions")

    payload = fake_client._table.upsert.call_args.args[0]
    assert payload["agent_id"] == AgentID.MKT.value
    assert payload["user_id"] == str(user_id)
    assert payload["contract_id"] == str(contract.id)
    assert payload["mode"] == "initiative"
    assert payload["contract_source"] == "initiative_step"
    assert payload["initiative_id"] == str(contract.initiative_id)
    assert payload["goal"] == "Forecast Q3 revenue"
    assert isinstance(payload["todo_snapshot"], list)
    assert any(a["ref"] == "vault://draft" for a in payload["artifacts"])


@pytest.mark.asyncio
async def test_publish_artifact_marks_status_submitted_on_pass(monkeypatch) -> None:
    user_id = uuid4()
    contract = _contract()
    artifact = Artifact(kind="doc", ref="vault://doc", summary="d", payload={})
    fake_client = _supabase_mocks(monkeypatch)
    monkeypatch.setattr(publication.workspace_event_bus, "publish", AsyncMock())
    monkeypatch.setattr(publication, "_vault_publish", AsyncMock(return_value=None))

    await publication.publish_artifact(
        user_id=user_id,
        agent_id="financial",
        contract=contract,
        artifact=artifact,
        audit=_audit_pass(),
    )
    payload = fake_client._table.upsert.call_args.args[0]
    assert payload["status"] == "submitted"
    assert payload.get("completed_at") is not None


@pytest.mark.asyncio
async def test_publish_artifact_appends_to_prior_artifacts(monkeypatch) -> None:
    """Idempotent retry: existing artifacts are preserved, the new one is appended."""
    user_id = uuid4()
    contract = _contract()
    prior_id = uuid4()
    prior_artifact = {
        "kind": "draft",
        "ref": "vault://prior",
        "summary": "first cut",
        "payload": {},
    }
    fake_client = _supabase_mocks(
        monkeypatch,
        prior_rows=[{"id": str(prior_id), "artifacts": [prior_artifact]}],
    )
    monkeypatch.setattr(publication.workspace_event_bus, "publish", AsyncMock())
    monkeypatch.setattr(publication, "_vault_publish", AsyncMock(return_value=None))

    artifact = Artifact(
        kind="agent_report",
        ref="vault://final",
        summary="final cut",
        payload={},
    )
    await publication.publish_artifact(
        user_id=user_id,
        agent_id="financial",
        contract=contract,
        artifact=artifact,
        audit=None,
    )
    payload = fake_client._table.upsert.call_args.args[0]
    refs = [a["ref"] for a in payload["artifacts"]]
    assert "vault://prior" in refs
    assert "vault://final" in refs
    # Idempotent: the upsert payload carries the prior row's id so a repeat
    # publication does not create a duplicate row.
    assert payload.get("id") == str(prior_id)


# ---------------------------------------------------------------------------
# Task 85 — vault sink fires only for vault-bound kinds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vault_publish_invoked_for_report_kind(monkeypatch) -> None:
    user_id = uuid4()
    contract = _contract(todo_items=[_todo()])
    artifact = Artifact(
        kind="agent_report",
        ref="vault://draft",
        summary="Quarterly review",
        payload={"markdown": "# Quarterly review\n\nbody"},
    )
    _supabase_mocks(monkeypatch)
    monkeypatch.setattr(publication.workspace_event_bus, "publish", AsyncMock())

    add_doc_id = uuid4()
    add_document = AsyncMock(return_value=add_doc_id)
    monkeypatch.setattr(publication.knowledge_service, "add_document", add_document)

    result = await publication.publish_artifact(
        user_id=user_id,
        agent_id="data",
        contract=contract,
        artifact=artifact,
        audit=None,
    )

    add_document.assert_awaited_once()
    kwargs = add_document.await_args.kwargs
    assert kwargs["agent_id"] == "data"
    assert kwargs["kind"] == "agent_report"
    assert kwargs["user_id"] == user_id
    assert "Quarterly review" in kwargs["content"]
    assert result.vault_document_id == add_doc_id


@pytest.mark.asyncio
async def test_vault_publish_fires_for_video_render(monkeypatch) -> None:
    user_id = uuid4()
    contract = _contract()
    artifact = Artifact(
        kind="video_render",
        ref="storage://videos/hero.mp4",
        summary="Hero spot",
        payload={"preview_url": "https://cdn/x.jpg"},
    )
    _supabase_mocks(monkeypatch)
    monkeypatch.setattr(publication.workspace_event_bus, "publish", AsyncMock())
    add_document = AsyncMock(return_value=uuid4())
    monkeypatch.setattr(publication.knowledge_service, "add_document", add_document)

    await publication.publish_artifact(
        user_id=user_id,
        agent_id="content_creation",
        contract=contract,
        artifact=artifact,
        audit=None,
    )
    add_document.assert_awaited_once()


@pytest.mark.asyncio
async def test_vault_publish_skipped_for_status_update_kind(monkeypatch) -> None:
    user_id = uuid4()
    contract = _contract()
    artifact = Artifact(
        kind="status_update",
        ref="-",
        summary="step done",
        payload={},
    )
    _supabase_mocks(monkeypatch)
    monkeypatch.setattr(publication.workspace_event_bus, "publish", AsyncMock())
    add_document = AsyncMock()
    monkeypatch.setattr(publication.knowledge_service, "add_document", add_document)

    result = await publication.publish_artifact(
        user_id=user_id,
        agent_id="data",
        contract=contract,
        artifact=artifact,
        audit=None,
    )
    add_document.assert_not_awaited()
    assert result.vault_document_id is None


@pytest.mark.asyncio
async def test_vault_publish_swallows_knowledge_service_errors(monkeypatch) -> None:
    user_id = uuid4()
    contract = _contract()
    artifact = Artifact(
        kind="agent_report", ref="vault://x", summary="summary", payload={}
    )
    _supabase_mocks(monkeypatch)
    monkeypatch.setattr(publication.workspace_event_bus, "publish", AsyncMock())

    async def boom(**_kwargs):
        raise RuntimeError("embedder offline")

    monkeypatch.setattr(publication.knowledge_service, "add_document", boom)

    # Must NOT raise, even when vault is offline.
    result = await publication.publish_artifact(
        user_id=user_id,
        agent_id="financial",
        contract=contract,
        artifact=artifact,
        audit=None,
    )
    assert result.vault_document_id is None
    assert result.workspace_event_emitted is True


# ---------------------------------------------------------------------------
# Task 86 — workspace event always emitted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_workspace_event_emitted_for_video_render(monkeypatch) -> None:
    user_id = uuid4()
    contract = _contract()
    artifact = Artifact(
        kind="video_render",
        ref="storage://videos/hero.mp4",
        summary="Final render",
        payload={"duration_s": 60, "preview_url": "https://cdn/x.jpg"},
    )
    _supabase_mocks(monkeypatch)
    publish = AsyncMock()
    monkeypatch.setattr(publication.workspace_event_bus, "publish", publish)
    monkeypatch.setattr(publication, "_vault_publish", AsyncMock(return_value=None))

    await publication.publish_artifact(
        user_id=user_id,
        agent_id="content_creation",
        contract=contract,
        artifact=artifact,
        audit=None,
    )

    publish.assert_awaited_once()
    args, _ = publish.await_args
    assert args[0] == user_id
    event = args[1]
    assert isinstance(event, WorkspaceArtifactEvent)
    assert event.kind == "artifact"
    assert event.artifact_kind == "video_render"
    assert event.ref == "storage://videos/hero.mp4"
    assert event.preview_url == "https://cdn/x.jpg"


@pytest.mark.asyncio
async def test_workspace_event_emitted_for_status_update(monkeypatch) -> None:
    """Workspace SSE must fire even for kinds that skip the vault."""
    _supabase_mocks(monkeypatch)
    publish = AsyncMock()
    monkeypatch.setattr(publication.workspace_event_bus, "publish", publish)
    monkeypatch.setattr(publication, "_vault_publish", AsyncMock(return_value=None))

    artifact = Artifact(kind="status_update", ref="-", summary="ok", payload={})
    result = await publication.publish_artifact(
        user_id=uuid4(),
        agent_id="financial",
        contract=_contract(),
        artifact=artifact,
        audit=None,
    )
    publish.assert_awaited_once()
    assert result.workspace_event_emitted is True


@pytest.mark.asyncio
async def test_workspace_event_failure_does_not_break_publish(monkeypatch) -> None:
    _supabase_mocks(monkeypatch)

    async def boom(*_args, **_kwargs):
        raise RuntimeError("redis offline")

    monkeypatch.setattr(publication.workspace_event_bus, "publish", boom)
    monkeypatch.setattr(publication, "_vault_publish", AsyncMock(return_value=None))

    artifact = Artifact(kind="status_update", ref="-", summary="ok", payload={})
    result = await publication.publish_artifact(
        user_id=uuid4(),
        agent_id="financial",
        contract=_contract(),
        artifact=artifact,
        audit=None,
    )
    assert result.workspace_event_emitted is False


# ---------------------------------------------------------------------------
# Task 100 — DirectRequest (mode='direct') publication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_artifact_direct_mode_marks_row(monkeypatch) -> None:
    user_id = uuid4()
    request = DirectRequest(
        user_id=user_id,
        agent_id=AgentID.FIN,
        persona_id="founder",
        message="What is Q3 revenue?",
        session_id=None,
    )
    fake_client = _supabase_mocks(monkeypatch)
    monkeypatch.setattr(publication.workspace_event_bus, "publish", AsyncMock())
    monkeypatch.setattr(publication, "_vault_publish", AsyncMock(return_value=None))

    artifact = Artifact(
        kind="status_update",
        ref="-",
        summary="$1.4M",
        payload={"answer": "$1.4M"},
    )
    await publication.publish_artifact(
        user_id=user_id,
        agent_id=AgentID.FIN,
        contract=request,
        artifact=artifact,
        audit=None,
    )

    upsert_payload = fake_client._table.upsert.call_args.args[0]
    assert upsert_payload["mode"] == "direct"
    assert upsert_payload["contract_id"] is None
    assert upsert_payload["contract_source"] == "direct_request"
    assert upsert_payload["initiative_id"] is None
    assert upsert_payload["goal"] is None
    assert upsert_payload["todo_snapshot"] is None


@pytest.mark.asyncio
async def test_publish_artifact_direct_mode_skips_prior_select(monkeypatch) -> None:
    """Direct mode has no contract id so it must NOT issue the prior-select."""
    user_id = uuid4()
    request = DirectRequest(
        user_id=user_id,
        agent_id=AgentID.SUPP,
        persona_id="cs",
        message="hi",
        session_id=None,
    )

    fake_client = MagicMock()
    table = MagicMock()
    table.upsert.return_value = table
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    fake_client.table = MagicMock(return_value=table)
    op_names: list[str | None] = []

    async def fake_execute_async(q, op_name=None):
        op_names.append(op_name)
        return MagicMock(data=[{"id": str(uuid4())}])

    monkeypatch.setattr(publication, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(publication, "execute_async", fake_execute_async)
    monkeypatch.setattr(publication.workspace_event_bus, "publish", AsyncMock())
    monkeypatch.setattr(publication, "_vault_publish", AsyncMock(return_value=None))

    await publication.publish_artifact(
        user_id=user_id,
        agent_id="support",
        contract=request,
        artifact=Artifact(kind="status_update", ref="-", summary="ok", payload={}),
        audit=None,
    )
    assert "agent_task_executions.select" not in op_names
    assert "agent_task_executions.upsert" in op_names


# ---------------------------------------------------------------------------
# Task 102 — director_service.notify_render_complete publishes a video_render
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_director_notify_render_complete_calls_publish_artifact(
    monkeypatch,
) -> None:
    from app.services import director_service

    publish = AsyncMock()
    monkeypatch.setattr(director_service, "publish_artifact", publish)

    user_id = uuid4()
    contract_id = uuid4()
    await director_service.notify_render_complete(
        user_id=user_id,
        agent_id="content_creation",
        contract_id=contract_id,
        ref="storage://videos/hero.mp4",
        preview_url="https://cdn/hero.jpg",
        summary="60s hero cut",
    )

    publish.assert_awaited_once()
    kwargs = publish.await_args.kwargs
    art = kwargs["artifact"]
    # Use class-name based assertions to be robust against test-suite-level
    # namespace pollution (test_package_init.py pops ``app.agents.runtime.types``
    # from sys.modules, which can cause director_service and this test to
    # hold *different* class objects for the same type).
    assert type(art).__name__ == "Artifact"
    assert art.kind == "video_render"
    assert art.ref == "storage://videos/hero.mp4"
    assert art.payload == {"preview_url": "https://cdn/hero.jpg"}
    assert kwargs["agent_id"] == "content_creation"
    assert kwargs["user_id"] == user_id
    # Initiative-mode TaskContract because we have a contract id.
    assert type(kwargs["contract"]).__name__ == "TaskContract"
    assert kwargs["contract"].id == contract_id


@pytest.mark.asyncio
async def test_director_notify_render_complete_direct_mode_when_no_contract(
    monkeypatch,
) -> None:
    from app.services import director_service

    publish = AsyncMock()
    monkeypatch.setattr(director_service, "publish_artifact", publish)

    await director_service.notify_render_complete(
        user_id=uuid4(),
        agent_id="content_creation",
        contract_id=None,
        ref="storage://videos/oneoff.mp4",
        preview_url=None,
        summary="one-off render",
    )

    publish.assert_awaited_once()
    kwargs = publish.await_args.kwargs
    assert type(kwargs["contract"]).__name__ == "DirectRequest"


# ---------------------------------------------------------------------------
# Task 103 — vertex_video_service.on_render_finished routes to director
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vertex_video_on_render_finished_routes_to_director(monkeypatch) -> None:
    from app.services import vertex_video_service

    notify = AsyncMock()
    monkeypatch.setattr(vertex_video_service, "notify_render_complete", notify)

    user_id = uuid4()
    contract_id = uuid4()
    await vertex_video_service.on_render_finished(
        user_id=user_id,
        agent_id="content_creation",
        contract_id=contract_id,
        storage_ref="storage://videos/abc.mp4",
        preview_url=None,
        summary="generated clip",
    )

    notify.assert_awaited_once()
    kwargs = notify.await_args.kwargs
    assert kwargs["ref"] == "storage://videos/abc.mp4"
    assert kwargs["agent_id"] == "content_creation"
    assert kwargs["user_id"] == user_id
    assert kwargs["contract_id"] == contract_id
    assert kwargs["summary"] == "generated clip"


# ---------------------------------------------------------------------------
# Cross-cutting: PublicationResult shape + idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publication_result_carries_execution_id(monkeypatch) -> None:
    fake_client = _supabase_mocks(monkeypatch)
    monkeypatch.setattr(publication.workspace_event_bus, "publish", AsyncMock())
    monkeypatch.setattr(publication, "_vault_publish", AsyncMock(return_value=None))

    result = await publication.publish_artifact(
        user_id=uuid4(),
        agent_id="financial",
        contract=_contract(),
        artifact=Artifact(kind="doc", ref="x", summary="s", payload={}),
        audit=None,
    )
    assert isinstance(result, publication.PublicationResult)
    assert isinstance(result.execution_id, UUID)
    assert result.execution_id == fake_client._upsert_id


@pytest.mark.asyncio
async def test_publish_artifact_unknown_kind_does_not_call_vault(monkeypatch) -> None:
    _supabase_mocks(monkeypatch)
    monkeypatch.setattr(publication.workspace_event_bus, "publish", AsyncMock())
    add_document = AsyncMock()
    monkeypatch.setattr(publication.knowledge_service, "add_document", add_document)

    artifact = Artifact(
        kind="data_query",
        ref="duckdb://q1",
        summary="SQL result",
        payload={"rows": 12},
    )
    await publication.publish_artifact(
        user_id=uuid4(),
        agent_id="data",
        contract=_contract(),
        artifact=artifact,
        audit=None,
    )
    add_document.assert_not_awaited()


# Suppress unused-import lint for types only referenced via isinstance checks.
_ = (ItemAudit,)
