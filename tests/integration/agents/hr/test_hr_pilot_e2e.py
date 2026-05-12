# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""End-to-end integration test for the HR agent migration (W4)."""

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


def _todo(title: str = "Screen 5 SWE candidates") -> TodoItem:
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
        goal="Screen the senior SWE candidate pipeline and shortlist 3.",
        todo_items=todos or [_todo()],
        success_criteria=[
            "Shortlist contains exactly 3 candidates.",
            "Each candidate has a documented rationale tied to job requirements.",
        ],
        owners=[AgentID.HR],
        evidence_required=["research_summary", "draft_artifact", "audit_report"],
        initiative_id=uuid4(),
        initiative_phase="validation",
        sibling_steps=[],
    )


def _complete_research() -> ResearchResult:
    return ResearchResult(
        summary="Pipeline has 18 candidates; structured screening produces top 3.",
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


class _DBHarness:
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
    harness = _DBHarness()
    monkeypatch.setattr(publication, "get_service_client", lambda: harness.client)
    monkeypatch.setattr(publication, "execute_async", harness.execute_async)
    monkeypatch.setattr(step_runtime, "_update_todo_status", AsyncMock())
    return harness


@pytest.fixture
def vault(monkeypatch) -> AsyncMock:
    fake_doc_id = uuid4()
    mock = AsyncMock(return_value=fake_doc_id)
    monkeypatch.setattr(publication.knowledge_service, "add_document", mock)
    return mock


@pytest.fixture
def workspace_events(monkeypatch) -> list[tuple[UUID, Any]]:
    captured: list[tuple[UUID, Any]] = []

    async def fake_publish(user_id: UUID, event: Any) -> None:
        captured.append((user_id, event))

    monkeypatch.setattr(publication.workspace_event_bus, "publish", fake_publish)
    return captured


def _build_hr_pilot(user_id: UUID, persona_id: str = "startup") -> Any:
    from app.agents.hr.agent import create_hr_agent

    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_hr_agent(user_id=user_id, persona_id=persona_id)
    return agent


def _bind_test_hooks(
    agent: Any,
    *,
    research: Any,
    audit: Any,
    run_step: Any,
) -> None:
    object.__setattr__(agent, "research", research)
    object.__setattr__(agent, "audit", audit)
    object.__setattr__(agent, "run_step", run_step)


@pytest.mark.asyncio
async def test_hr_pilot_execute_task_fires_all_four_sinks(
    db: _DBHarness,
    vault: AsyncMock,
    workspace_events: list[tuple[UUID, Any]],
) -> None:
    user_id = uuid4()
    contract = _contract()

    agent = _build_hr_pilot(user_id, persona_id="startup")
    draft_artifact = Artifact(
        kind="doc",
        ref="vault://shortlist",
        summary="Senior SWE shortlist",
        payload={"markdown": "# Shortlist\n\n3 candidates with rationales."},
    )

    _bind_test_hooks(
        agent,
        research=AsyncMock(return_value=_complete_research()),
        audit=AsyncMock(return_value=_pass_audit()),
        run_step=AsyncMock(return_value=draft_artifact),
    )

    result = await step_runtime.execute_task(agent, contract)

    agent.research.assert_awaited_once_with(contract=contract)
    assert result.status == "submitted"
    assert result.audit.overall_status == "pass"

    kinds_published = [a.kind for a in result.artifacts]
    assert kinds_published == ["doc", "report"]

    assert vault.await_count >= 2
    vault_kinds_seen = {
        call.kwargs["metadata"]["artifact_kind"]
        for call in vault.await_args_list
    }
    assert "report" in vault_kinds_seen

    artifact_events = [
        ev for _, ev in workspace_events if isinstance(ev, WorkspaceArtifactEvent)
    ]
    assert artifact_events
    for ev in artifact_events:
        assert ev.contract_id == contract.id
        assert ev.agent_id == AgentID.HR.value

    assert db.upserted_rows
    for row in db.upserted_rows:
        assert row["user_id"] == str(user_id)
        assert row["agent_id"] == AgentID.HR.value
        assert row["mode"] == "initiative"
        assert row["status"] == "submitted"


@pytest.mark.asyncio
async def test_hr_pilot_agent_identity_propagates(
    db: _DBHarness,
    vault: AsyncMock,
    workspace_events: list[tuple[UUID, Any]],
) -> None:
    user_id = uuid4()
    contract = _contract()
    agent = _build_hr_pilot(user_id, persona_id="sme")

    _bind_test_hooks(
        agent,
        research=AsyncMock(return_value=_complete_research()),
        audit=AsyncMock(return_value=_pass_audit()),
        run_step=AsyncMock(
            return_value=Artifact(
                kind="doc",
                ref="vault://onboarding",
                summary="Onboarding checklist",
                payload={"markdown": "# Day 1\n\n..."},
            )
        ),
    )

    await step_runtime.execute_task(agent, contract)

    assert db.upserted_rows
    for row in db.upserted_rows:
        assert row["user_id"] == str(user_id)
        assert row["agent_id"] == AgentID.HR.value


@pytest.mark.asyncio
async def test_hr_pilot_ops_config_observable_post_construct() -> None:
    agent = _build_hr_pilot(uuid4(), persona_id="startup")
    assert agent.ops.agent_id == "hr"
    assert agent.ops.approval.required_for_external_send is True
    assert "validation" in agent.ops.initiative.phases_owned
    assert "hr:*" in agent.ops.skills.allowed_ids
