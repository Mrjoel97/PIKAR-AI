# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""End-to-end integration test for the financial agent pilot (Task 112).

This is the load-bearing proof-of-life for the W2 operating model. It
constructs a real financial :class:`PikarBaseAgent` (mocking only the
ADK ``Agent.__init__`` so we do not need the live ADK runtime), seeds a
single-step :class:`TaskContract`, invokes
:func:`app.agents.runtime.step_runtime.execute_task`, and asserts that
**all four publication sinks** observed the expected output:

1. ``agent_task_executions`` (Layer-1 history) — row upserted with every
   FK column populated.
2. Knowledge vault (Layer-2 + Layer-3 retrieval) — :func:`add_document`
   fired for the doc artifact AND the rendered markdown report.
3. Workspace SSE channel — :class:`WorkspaceArtifactEvent` published for
   each artifact.
4. Reports UI — falls out of (1) via the joined router; the row's
   ``status`` field is the readable signal.

All external services (Supabase, Redis, Gemini) are mocked; the only
real production code in the loop is the financial agent factory, the
manifest resolver, ``step_runtime.execute_task``, and the publication
primitive itself.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.agents.runtime import publication, step_runtime
from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    ResearchResult,
    TaskContract,
    TodoItem,
    WorkspaceArtifactEvent,
)
from app.skills.registry import AgentID


# ---------------------------------------------------------------------------
# Builders — small fixtures keep individual tests readable.
# ---------------------------------------------------------------------------


def _todo(title: str = "Pull 12mo historicals") -> TodoItem:
    return TodoItem(
        id=uuid4(),
        title=title,
        description=None,
        status="pending",
        evidence=[],
        sort_order=0,
    )


def _contract(*, todos: list[TodoItem] | None = None) -> TaskContract:
    return TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="Produce a 6-month revenue forecast for FY26 H1.",
        todo_items=todos or [_todo()],
        success_criteria=[
            "Forecast covers 6 future months.",
            "Confidence level reported per month.",
        ],
        owners=[AgentID.FIN],
        evidence_required=["research_summary", "draft_artifact", "audit_report"],
        initiative_id=uuid4(),
        initiative_phase="validation",
        sibling_steps=[],
    )


def _complete_research() -> ResearchResult:
    return ResearchResult(
        summary="FY25 revenue grew 12% QoQ; 14 months of Stripe data on hand.",
        sources=[],
        contradictions=[],
        coverage_assessment="complete",
        missing_information=[],
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


# ---------------------------------------------------------------------------
# Supabase + workspace + vault mocking harness.
# ---------------------------------------------------------------------------


class _DBHarness:
    """Record every upsert + select :mod:`publication` performs.

    Mirrors the production Supabase chain ``client.table(...).upsert(...)``
    and ``.select().eq().limit()`` so :func:`publication.publish_artifact`
    can execute its real code path unchanged.
    """

    def __init__(self) -> None:
        self.upserted_rows: list[dict[str, Any]] = []
        self.upsert_id: UUID = uuid4()
        self.execution_id: UUID = self.upsert_id
        self.select_calls: int = 0

        client = MagicMock(name="supabase_client")
        table = MagicMock(name="supabase_table")
        for attr in (
            "select",
            "eq",
            "limit",
            "single",
            "in_",
            "order",
            "neq",
            "update",
        ):
            getattr(table, attr).return_value = table

        def _record_upsert(row: dict[str, Any], **_kwargs: Any) -> MagicMock:
            self.upserted_rows.append(row)
            return table

        table.upsert.side_effect = _record_upsert
        client.table = MagicMock(return_value=table)
        self.client = client
        self.table = table

    async def execute_async(
        self, query: Any, op_name: str | None = None
    ) -> MagicMock:
        if op_name == "agent_task_executions.select":
            self.select_calls += 1
            return MagicMock(data=[])
        if op_name == "agent_task_executions.upsert":
            return MagicMock(data=[{"id": str(self.upsert_id)}])
        return MagicMock(data=[{"id": str(uuid4()), "artifacts": []}])


@pytest.fixture
def db(monkeypatch) -> _DBHarness:
    """Wire the Supabase-shaped harness into the publication module."""
    harness = _DBHarness()
    monkeypatch.setattr(publication, "get_service_client", lambda: harness.client)
    monkeypatch.setattr(publication, "execute_async", harness.execute_async)
    # step_runtime writes back todo statuses to a different table; the
    # E2E test doesn't care about those writes, so stub them.
    monkeypatch.setattr(step_runtime, "_update_todo_status", AsyncMock())
    return harness


@pytest.fixture
def vault(monkeypatch) -> AsyncMock:
    """Replace :func:`knowledge_service.add_document` with an AsyncMock."""
    fake_doc_id = uuid4()
    mock = AsyncMock(return_value=fake_doc_id)
    monkeypatch.setattr(publication.knowledge_service, "add_document", mock)
    return mock


@pytest.fixture
def workspace_events(monkeypatch) -> list[tuple[UUID, Any]]:
    """Capture every workspace event published during the run."""
    captured: list[tuple[UUID, Any]] = []

    async def fake_publish(user_id: UUID, event: Any) -> None:
        captured.append((user_id, event))

    monkeypatch.setattr(publication.workspace_event_bus, "publish", fake_publish)
    return captured


# ---------------------------------------------------------------------------
# Financial PikarBaseAgent factory — wraps the real ``create_financial_agent``
# with the necessary mocks so the parent ADK ``Agent.__init__`` does not run.
# ---------------------------------------------------------------------------


def _build_financial_pilot(user_id: UUID, persona_id: str = "startup") -> Any:
    """Build a real financial :class:`PikarBaseAgent` bound to ``user_id``.

    The ADK parent ``Agent.__init__`` is patched to a no-op so the
    constructor completes without the live ADK runtime; everything else
    (ops config load, instructions read, manifest resolution, identity
    binding via :func:`object.__setattr__`) runs production code.
    """
    from app.agents.financial.agent import create_financial_agent

    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_financial_agent(user_id=user_id, persona_id=persona_id)
    return agent


def _bind_test_hooks(
    agent: Any,
    *,
    research: Any,
    audit: Any,
    run_step: Any,
) -> None:
    """Attach the ``research`` / ``audit`` / ``run_step`` hooks the
    ``step_runtime.execute_task`` loop calls into.

    ADK's ``Agent`` is a pydantic ``BaseModel`` with ``extra='forbid'``;
    we use :func:`object.__setattr__` to bypass the model's validator,
    matching what :class:`PikarBaseAgent`'s constructor itself does for
    its identity / ops attributes.
    """
    object.__setattr__(agent, "research", research)
    object.__setattr__(agent, "audit", audit)
    object.__setattr__(agent, "run_step", run_step)


# ---------------------------------------------------------------------------
# The five contract checks from spec § 17.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_financial_pilot_execute_task_fires_all_four_sinks(
    db: _DBHarness,
    vault: AsyncMock,
    workspace_events: list[tuple[UUID, Any]],
) -> None:
    """End-to-end: a real FinancialAnalysisAgent submits via execute_task.

    Asserts the W2 contract:

    (a) research is consulted before the todos run;
    (b) the audit report records ``overall_status='pass'``;
    (c) the rendered markdown report lands in the knowledge vault;
    (d) at least one ``WorkspaceArtifactEvent`` fires on the SSE bus;
    (e) the ``agent_task_executions`` row is written with every FK
        column populated.
    """
    user_id = uuid4()
    contract = _contract()

    agent = _build_financial_pilot(user_id, persona_id="startup")
    research_result = _complete_research()
    audit_report = _pass_audit()
    draft_artifact = Artifact(
        kind="doc",
        ref="vault://forecast-draft",
        summary="6-month revenue forecast",
        payload={"markdown": "# Forecast\n\nFY26 H1 projected at $1.2M."},
    )

    # ``step_runtime.execute_task`` calls ``agent.research``,
    # ``agent.run_step``, and ``agent.audit`` — Section D bodies for these
    # are not in scope for W2 Section E. We supply them as instance
    # attributes (AsyncMock) so the pipeline can flow end-to-end.
    _bind_test_hooks(
        agent,
        research=AsyncMock(return_value=research_result),
        audit=AsyncMock(return_value=audit_report),
        run_step=AsyncMock(return_value=draft_artifact),
    )

    result = await step_runtime.execute_task(agent, contract)

    # (a) Research was the first call.
    agent.research.assert_awaited_once_with(contract=contract)

    # (b) Audit produced overall_status='pass'.
    assert result.status == "submitted"
    assert result.audit.overall_status == "pass"
    agent.audit.assert_awaited_once()
    audit_kwargs = agent.audit.await_args.kwargs
    assert audit_kwargs["contract"] is contract
    assert audit_kwargs["artifacts"] == [draft_artifact]

    # The publication pipeline produced two artifacts (the doc draft +
    # the rendered Layer-2 report).
    kinds_published = [a.kind for a in result.artifacts]
    assert kinds_published == ["doc", "report"]

    # (c) Vault sink — ``knowledge_service.add_document`` fired for the
    # rendered markdown report. (The doc artifact also lands in the vault
    # because ``doc`` is in :data:`publication.VAULT_BOUND_KINDS`.)
    assert vault.await_count >= 2, (
        f"expected vault writes for doc + report, got {vault.await_count}"
    )
    vault_kinds_seen = {
        call.kwargs["metadata"]["artifact_kind"]
        for call in vault.await_args_list
    }
    assert "report" in vault_kinds_seen, "rendered markdown report missing from vault"
    for call in vault.await_args_list:
        meta = call.kwargs["metadata"]
        # Every vault doc carries the contract id so Layer-3 retrieval
        # can scope hits to the producing initiative.
        assert meta["contract_id"] == str(contract.id)
        assert meta["initiative_id"] == str(contract.initiative_id)

    # (d) Workspace sink — at least one WorkspaceArtifactEvent fired,
    # one of which carries the rendered report.
    artifact_events = [
        ev for _, ev in workspace_events if isinstance(ev, WorkspaceArtifactEvent)
    ]
    assert artifact_events, "no WorkspaceArtifactEvent fired"
    report_events = [ev for ev in artifact_events if ev.artifact_kind == "report"]
    assert report_events, "rendered report did not fire a workspace event"
    for ev in artifact_events:
        assert ev.contract_id == contract.id
        assert ev.agent_id == AgentID.FIN.value

    # (e) Reports / history sink — at least one ``agent_task_executions``
    # row was upserted with every FK column populated.
    assert db.upserted_rows, "no agent_task_executions row was upserted"
    for row in db.upserted_rows:
        assert row["user_id"] == str(user_id)
        assert row["agent_id"] == AgentID.FIN.value
        assert row["mode"] == "initiative"
        assert row["contract_id"] == str(contract.id)
        assert row["contract_source"] == "initiative_step"
        assert row["initiative_id"] == str(contract.initiative_id)
        assert row["goal"] == contract.goal
        assert row["status"] == "submitted"
    # Both the doc artifact AND the report appear across the upserts.
    all_artifact_kinds = {
        artifact["kind"]
        for row in db.upserted_rows
        for artifact in row["artifacts"]
    }
    assert "doc" in all_artifact_kinds
    assert "report" in all_artifact_kinds


@pytest.mark.asyncio
async def test_financial_pilot_agent_identity_propagates(
    db: _DBHarness,
    vault: AsyncMock,
    workspace_events: list[tuple[UUID, Any]],
) -> None:
    """The pilot agent's identity (user_id, persona_id, agent_id) must
    propagate end-to-end so the row written to ``agent_task_executions``
    can be filtered by any of those fields downstream."""
    user_id = uuid4()
    contract = _contract()
    agent = _build_financial_pilot(user_id, persona_id="sme")

    research_result = _complete_research()
    audit_report = _pass_audit()
    draft_artifact = Artifact(
        kind="doc",
        ref="vault://burn-runway",
        summary="Burn & runway",
        payload={"markdown": "# Burn\n\n6 months."},
    )
    _bind_test_hooks(
        agent,
        research=AsyncMock(return_value=research_result),
        audit=AsyncMock(return_value=audit_report),
        run_step=AsyncMock(return_value=draft_artifact),
    )

    await step_runtime.execute_task(agent, contract)

    # Every history row carries the binding identity values.
    assert db.upserted_rows
    for row in db.upserted_rows:
        assert row["user_id"] == str(user_id)
        assert row["agent_id"] == AgentID.FIN.value


@pytest.mark.asyncio
async def test_financial_pilot_ops_config_observable_post_construct() -> None:
    """The agent must carry its loaded ``operations.yaml`` as ``self.ops``."""
    agent = _build_financial_pilot(uuid4(), persona_id="startup")

    assert agent.ops.agent_id == "financial"
    assert agent.ops.approval.required_above_usd == 1000
    assert "validation" in agent.ops.initiative.phases_owned
    assert "finance:*" in agent.ops.skills.allowed_ids
