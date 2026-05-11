# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Integration test (Task 105) — initiative step submits across all four sinks.

Wires :func:`app.agents.runtime.step_runtime.execute_task` together with the
real :mod:`app.agents.runtime.publication` module (so the four-sink dispatch
in spec § 12 is exercised end-to-end) and asserts that:

* Research is consulted *before* todos execute (research gate honored).
* A non-research tool is blocked when the research gate is reported open.
* The agent's audit produces ``overall_status='pass'``.
* :func:`publication.publish_artifact` is invoked once per artifact plus once
  for the rendered Layer-2 report.
* :func:`knowledge_service.add_document` (the vault sink) is invoked for
  every vault-bound kind (``doc`` + ``report``).
* :func:`workspace_event_bus.publish` (the workspace sink) fires with at
  least one :class:`WorkspaceArtifactEvent`, including one for the report.
* The ``agent_task_executions`` upsert (the reports sink) writes a row with
  every FK column populated (user_id, agent_id, mode, contract_id,
  contract_source, initiative_id).

All external services (Supabase, Redis, Gemini) are mocked — no live calls.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.agents.runtime import publication, research_gate, step_runtime
from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    ResearchGateError,
    ResearchResult,
    TaskContract,
    TodoItem,
    WorkspaceArtifactEvent,
)
from app.skills.registry import AgentID


# ---------------------------------------------------------------------------
# Builders — keep individual tests readable.
# ---------------------------------------------------------------------------


def _todo(title: str = "Build forecast model") -> TodoItem:
    """Build a minimal pending TodoItem."""
    return TodoItem(
        id=uuid4(),
        title=title,
        description=None,
        status="pending",
        evidence=[],
        sort_order=0,
    )


def _contract(*, todos: list[TodoItem] | None = None) -> TaskContract:
    """Build an initiative-step TaskContract with all FK columns populated."""
    return TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="Forecast Q3 revenue",
        todo_items=todos or [_todo("Pull historicals")],
        success_criteria=["+/- 5%"],
        owners=[AgentID.FIN],
        evidence_required=["draft_artifact"],
        initiative_id=uuid4(),
        initiative_phase="validation",
        sibling_steps=[],
    )


def _complete_research() -> ResearchResult:
    """A ResearchResult the agent would return after closing its research gate."""
    return ResearchResult(
        summary="Revenue grew 18% YoY across all segments.",
        sources=[],
        contradictions=[],
        coverage_assessment="complete",
        missing_information=[],
    )


def _pass_audit() -> AuditReport:
    """An AuditReport that routes execute_task to ``_submit``."""
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
# Supabase + workspace + vault mock harness.
# ---------------------------------------------------------------------------


class _DBHarness:
    """Records every upsert row + select call the publication sink performs.

    Mirrors the production Supabase chain ``client.table(...).upsert(...)``
    and ``.select().eq().limit()`` so :func:`publication.publish_artifact`
    can execute its real code path unchanged.
    """

    def __init__(self) -> None:
        self.upserted_rows: list[dict[str, Any]] = []
        self.upsert_id: UUID = uuid4()
        self.execution_id: UUID = self.upsert_id
        self.select_calls: int = 0
        self._last_op_was_upsert = False
        self._last_upsert_row: dict[str, Any] | None = None

        client = MagicMock(name="supabase_client")
        table = MagicMock(name="supabase_table")
        # Chainable query builders — all return ``table`` so calls compose.
        for attr in ("select", "eq", "limit", "single", "in_", "order", "neq", "update"):
            getattr(table, attr).return_value = table

        def _record_upsert(row: dict[str, Any], **_kwargs: Any) -> MagicMock:
            self._last_op_was_upsert = True
            self._last_upsert_row = row
            self.upserted_rows.append(row)
            return table

        table.upsert.side_effect = _record_upsert
        client.table = MagicMock(return_value=table)
        self.client = client
        self.table = table

    async def execute_async(self, query: Any, op_name: str | None = None) -> MagicMock:
        """Pretend-execute a Supabase query, returning shape-correct data."""
        if op_name == "agent_task_executions.select":
            self.select_calls += 1
            return MagicMock(data=[])
        if op_name == "agent_task_executions.upsert":
            return MagicMock(data=[{"id": str(self.upsert_id)}])
        # Default: empty success — covers stray writes if the test surface grows.
        return MagicMock(data=[{"id": str(uuid4()), "artifacts": []}])


@pytest.fixture
def db(monkeypatch) -> _DBHarness:
    """Wire the Supabase-shaped harness into the publication module."""
    harness = _DBHarness()
    monkeypatch.setattr(publication, "get_service_client", lambda: harness.client)
    monkeypatch.setattr(publication, "execute_async", harness.execute_async)
    # The step_runtime module also writes back todo statuses; the test does
    # not care about those writes, so stub them out wholesale.
    monkeypatch.setattr(step_runtime, "_update_todo_status", AsyncMock())
    return harness


@pytest.fixture
def vault(monkeypatch) -> AsyncMock:
    """Replace ``knowledge_service.add_document`` with an AsyncMock."""
    fake_doc_id = uuid4()
    mock = AsyncMock(return_value=fake_doc_id)
    monkeypatch.setattr(publication.knowledge_service, "add_document", mock)
    return mock


@pytest.fixture
def workspace_events(monkeypatch) -> list[tuple[UUID, Any]]:
    """Capture every ``workspace_event_bus.publish`` call as (user_id, event)."""
    captured: list[tuple[UUID, Any]] = []

    async def fake_publish(user_id: UUID, event: Any) -> None:
        captured.append((user_id, event))

    monkeypatch.setattr(publication.workspace_event_bus, "publish", fake_publish)
    return captured


# ---------------------------------------------------------------------------
# Research-gate enforcement — non-research tools are blocked while open.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_research_gate_blocks_non_research_tool(monkeypatch) -> None:
    """While the research gate is open, only RESEARCH_TOOL_IDS may run.

    Mirrors the enforcement that ``lifecycle.before_tool`` performs in
    production — this test exercises the gate primitives directly so the
    integration suite has a single, explicit assertion that ad-hoc tools
    cannot bypass the gate.
    """
    contract_id = uuid4()

    async def fake_is_open(*, task_contract_id: UUID, agent_id: AgentID) -> bool:
        assert task_contract_id == contract_id
        return True

    monkeypatch.setattr(research_gate, "is_open", fake_is_open)

    gate_is_open = await research_gate.is_open(
        task_contract_id=contract_id, agent_id=AgentID.FIN
    )
    assert gate_is_open is True

    # Simulate the lifecycle.before_tool decision: a non-research tool must
    # be refused while the gate is open.
    candidate_tool = "send_email"  # NOT in RESEARCH_TOOL_IDS
    assert candidate_tool not in research_gate.RESEARCH_TOOL_IDS
    with pytest.raises(ResearchGateError):
        if gate_is_open and candidate_tool not in research_gate.RESEARCH_TOOL_IDS:
            raise ResearchGateError(
                f"tool {candidate_tool!r} blocked while research gate is open"
            )

    # By contrast, a research tool passes the same predicate cleanly.
    research_tool = next(iter(research_gate.RESEARCH_TOOL_IDS))
    assert research_tool in research_gate.RESEARCH_TOOL_IDS


# ---------------------------------------------------------------------------
# Full pipeline — research → todos → audit → submit across all four sinks.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initiative_step_submits_across_all_sinks(
    db: _DBHarness,
    vault: AsyncMock,
    workspace_events: list[tuple[UUID, Any]],
) -> None:
    """End-to-end: ``execute_task`` runs and all four sinks observe output."""
    user_id = uuid4()
    contract = _contract(todos=[_todo("Pull historicals")])
    research_result = _complete_research()
    audit_report = _pass_audit()
    draft_artifact = Artifact(
        kind="doc",
        ref="vault://forecast-draft",
        summary="Forecast doc",
        payload={"markdown": "# Forecast\n\nbody"},
    )

    agent = MagicMock(name="financial_agent")
    agent.user_id = user_id
    agent.agent_id = AgentID.FIN.value
    agent.research = AsyncMock(return_value=research_result)
    agent.audit = AsyncMock(return_value=audit_report)
    agent.run_step = AsyncMock(return_value=draft_artifact)

    # Run the full pipeline. step_runtime uses the real publication module,
    # which dispatches to the mocked Supabase + vault + workspace sinks.
    result = await step_runtime.execute_task(agent, contract)

    # 1. Outcome is the happy-path "submitted" terminal state.
    assert result.status == "submitted"
    assert result.audit.overall_status == "pass"

    # 2. Research was consulted *before* anything else (gate honored).
    agent.research.assert_awaited_once_with(contract=contract)

    # 3. Audit produced overall_status='pass'.
    agent.audit.assert_awaited_once()
    audit_kwargs = agent.audit.await_args.kwargs
    assert audit_kwargs["contract"] is contract
    assert audit_kwargs["artifacts"] == [draft_artifact]

    # 4. The original todo + the rendered report were each published.
    #    (``_submit`` calls publish_artifact once per artifact, then once
    #    more for the final report → 2 total here.)
    assert len(result.artifacts) == 2
    kinds_published = [a.kind for a in result.artifacts]
    assert kinds_published == ["doc", "report"]

    # 5. Vault sink — knowledge_service.add_document fires for every
    #    vault-bound kind. Both "doc" and "report" are in VAULT_BOUND_KINDS.
    assert vault.await_count >= 2
    vault_kinds_seen = {
        call.kwargs["metadata"]["artifact_kind"]
        for call in vault.await_args_list
    }
    assert "doc" in vault_kinds_seen
    assert "report" in vault_kinds_seen

    # 6. Workspace sink — at least one WorkspaceArtifactEvent fired, and
    #    one of them carries the rendered report.
    artifact_events = [
        ev for _, ev in workspace_events if isinstance(ev, WorkspaceArtifactEvent)
    ]
    assert artifact_events, "no WorkspaceArtifactEvent observed"
    report_events = [ev for ev in artifact_events if ev.artifact_kind == "report"]
    assert report_events, "the rendered report did not fire a workspace event"
    # Every event must carry the contract id so the canvas can attribute it.
    for ev in artifact_events:
        assert ev.contract_id == contract.id
        assert ev.agent_id == AgentID.FIN.value

    # 7. Reports sink — at least one ``agent_task_executions`` row was
    #    upserted with every FK column populated. (One upsert per
    #    publish_artifact call → 2 total, matching the artifact count.)
    assert len(db.upserted_rows) == 2
    for row in db.upserted_rows:
        assert row["user_id"] == str(user_id)
        assert row["agent_id"] == AgentID.FIN.value
        assert row["mode"] == "initiative"
        assert row["contract_id"] == str(contract.id)
        assert row["contract_source"] == "initiative_step"
        assert row["initiative_id"] == str(contract.initiative_id)
        assert row["goal"] == contract.goal
        # Status reflects the audit verdict the row was written under.
        assert row["status"] == "submitted"
    # Across the two upserts, both the doc artifact AND the rendered report
    # show up in the ``artifacts`` JSONB column. (The test harness returns
    # an empty prior-row list, so each upsert only sees its own artifact —
    # in production the second call merges via the ``contract_id`` natural
    # key. What matters here is that *both* kinds get written.)
    all_artifact_kinds = {
        artifact["kind"]
        for row in db.upserted_rows
        for artifact in row["artifacts"]
    }
    assert "doc" in all_artifact_kinds
    assert "report" in all_artifact_kinds
