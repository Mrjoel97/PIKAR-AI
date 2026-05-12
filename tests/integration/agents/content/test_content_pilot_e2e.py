# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""End-to-end integration test for the content agent pilot (W4-Pilot).

Mirrors :mod:`tests.integration.agents.financial.test_financial_pilot_e2e` —
constructs a real content :class:`PikarBaseAgent` (mocking only the ADK
``Agent.__init__`` so we do not need the live ADK runtime), seeds a
single-step :class:`TaskContract`, invokes
:func:`app.agents.runtime.step_runtime.execute_task`, and asserts that
all four publication sinks observed the expected output:

1. ``agent_task_executions`` (Layer-1 history).
2. Knowledge vault (Layer-2/3 retrieval) — :func:`add_document` fired.
3. Workspace SSE channel — :class:`WorkspaceArtifactEvent` published.
4. Reports UI — falls out of (1) via the joined router.

All external services (Supabase, Redis, Gemini) are mocked; the only
real production code in the loop is the content agent factory, the
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
# Builders
# ---------------------------------------------------------------------------


def _todo(title: str = "Draft Q3 campaign brief") -> TodoItem:
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
        goal="Produce a launch campaign bundle for the spring SaaS release.",
        todo_items=todos or [_todo()],
        success_criteria=[
            "Bundle includes 1 hero video concept.",
            "Bundle includes 3 social posts.",
            "All copy aligned to brand voice.",
        ],
        owners=[AgentID.CONT],
        evidence_required=["research_summary", "draft_artifact", "audit_report"],
        initiative_id=uuid4(),
        initiative_phase="ideation",
        sibling_steps=[],
    )


def _complete_research() -> ResearchResult:
    return ResearchResult(
        summary="Brand voice tone: confident, plainspoken. Top channel: LinkedIn.",
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
    """Record every upsert + select :mod:`publication` performs."""

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

    async def execute_async(self, query: Any, op_name: str | None = None) -> MagicMock:
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
# Content PikarBaseAgent factory wrapper.
# ---------------------------------------------------------------------------


def _build_content_pilot(user_id: UUID, persona_id: str = "startup") -> Any:
    """Build a real content :class:`PikarBaseAgent` bound to ``user_id``.

    The ADK parent ``Agent.__init__`` is patched to a no-op so the
    constructor completes without the live ADK runtime; everything else
    (ops config load, instructions read, manifest resolution, identity
    binding via :func:`object.__setattr__`) runs production code.
    """
    from app.agents.content.agent import create_content_agent

    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_content_agent(user_id=user_id, persona_id=persona_id)
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
    """
    object.__setattr__(agent, "research", research)
    object.__setattr__(agent, "audit", audit)
    object.__setattr__(agent, "run_step", run_step)


# ---------------------------------------------------------------------------
# Contract checks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_content_pilot_execute_task_fires_all_four_sinks(
    db: _DBHarness,
    vault: AsyncMock,
    workspace_events: list[tuple[UUID, Any]],
) -> None:
    """End-to-end: a real ContentCreationAgent submits via execute_task.

    Asserts the W2/W4 contract:

    (a) research is consulted before the todos run;
    (b) the audit report records ``overall_status='pass'``;
    (c) the rendered markdown report lands in the knowledge vault;
    (d) at least one ``WorkspaceArtifactEvent`` fires on the SSE bus;
    (e) the ``agent_task_executions`` row is written with every FK
        column populated.
    """
    user_id = uuid4()
    contract = _contract()

    agent = _build_content_pilot(user_id, persona_id="startup")
    research_result = _complete_research()
    audit_report = _pass_audit()
    draft_artifact = Artifact(
        kind="doc",
        ref="vault://campaign-brief-draft",
        summary="Q3 launch campaign brief",
        payload={"markdown": "# Spring Launch\n\nHero video + 3 social posts."},
    )

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

    kinds_published = [a.kind for a in result.artifacts]
    assert kinds_published == ["doc", "report"]

    # (c) Vault sink — knowledge_service.add_document fired for both artifacts.
    assert vault.await_count >= 2, (
        f"expected vault writes for doc + report, got {vault.await_count}"
    )
    vault_kinds_seen = {
        call.kwargs["metadata"]["artifact_kind"] for call in vault.await_args_list
    }
    assert "report" in vault_kinds_seen, "rendered markdown report missing from vault"
    for call in vault.await_args_list:
        meta = call.kwargs["metadata"]
        assert meta["contract_id"] == str(contract.id)
        assert meta["initiative_id"] == str(contract.initiative_id)

    # (d) Workspace sink — WorkspaceArtifactEvent fired.
    artifact_events = [
        ev for _, ev in workspace_events if isinstance(ev, WorkspaceArtifactEvent)
    ]
    assert artifact_events, "no WorkspaceArtifactEvent fired"
    report_events = [ev for ev in artifact_events if ev.artifact_kind == "report"]
    assert report_events, "rendered report did not fire a workspace event"
    for ev in artifact_events:
        assert ev.contract_id == contract.id
        assert ev.agent_id == AgentID.CONT.value

    # (e) Reports / history sink — agent_task_executions row was upserted.
    assert db.upserted_rows, "no agent_task_executions row was upserted"
    for row in db.upserted_rows:
        assert row["user_id"] == str(user_id)
        assert row["agent_id"] == AgentID.CONT.value
        assert row["mode"] == "initiative"
        assert row["contract_id"] == str(contract.id)
        assert row["contract_source"] == "initiative_step"
        assert row["initiative_id"] == str(contract.initiative_id)
        assert row["goal"] == contract.goal
        assert row["status"] == "submitted"
    all_artifact_kinds = {
        artifact["kind"] for row in db.upserted_rows for artifact in row["artifacts"]
    }
    assert "doc" in all_artifact_kinds
    assert "report" in all_artifact_kinds


@pytest.mark.asyncio
async def test_content_pilot_agent_identity_propagates(
    db: _DBHarness,
    vault: AsyncMock,
    workspace_events: list[tuple[UUID, Any]],
) -> None:
    """The pilot agent's identity (user_id, persona_id, agent_id) must
    propagate end-to-end so the row written to ``agent_task_executions``
    can be filtered by any of those fields downstream."""
    user_id = uuid4()
    contract = _contract()
    agent = _build_content_pilot(user_id, persona_id="sme")

    research_result = _complete_research()
    audit_report = _pass_audit()
    draft_artifact = Artifact(
        kind="doc",
        ref="vault://social-bundle",
        summary="Social bundle",
        payload={"markdown": "# 3-post LinkedIn bundle"},
    )
    _bind_test_hooks(
        agent,
        research=AsyncMock(return_value=research_result),
        audit=AsyncMock(return_value=audit_report),
        run_step=AsyncMock(return_value=draft_artifact),
    )

    await step_runtime.execute_task(agent, contract)

    assert db.upserted_rows
    for row in db.upserted_rows:
        assert row["user_id"] == str(user_id)
        assert row["agent_id"] == AgentID.CONT.value


@pytest.mark.asyncio
async def test_content_pilot_ops_config_observable_post_construct() -> None:
    """The agent must carry its loaded ``operations.yaml`` as ``self.ops``."""
    agent = _build_content_pilot(uuid4(), persona_id="startup")

    assert agent.ops.agent_id == "content"
    assert agent.ops.approval.required_for_external_send is True
    assert "ideation" in agent.ops.initiative.phases_owned
    assert "production" in agent.ops.initiative.phases_owned
    assert "content:*" in agent.ops.skills.allowed_ids


def test_content_pilot_factory_constructs_three_sub_agents() -> None:
    """The director must wire video_director / graphic_designer / copywriter
    as ``sub_agents=`` so ADK's delegation path can reach them.

    We patch ``PikarAgent.__init__`` to a no-op (so the ADK pydantic model
    doesn't reject our extra kwargs) and capture the ``sub_agents`` kwarg
    that PikarBaseAgent.__init__ forwards to ``super().__init__``.
    """
    from app.agents.content.agent import create_content_agent

    captured: dict[str, Any] = {}

    def _capture(self: Any, **kwargs: Any) -> None:
        # The director's PikarAgent.__init__ call carries sub_agents.
        if kwargs.get("sub_agents"):
            captured.setdefault("sub_agents", kwargs["sub_agents"])

    with patch("app.agents.base_agent.PikarAgent.__init__", _capture):
        create_content_agent(user_id=uuid4(), persona_id="startup")

    subs = captured.get("sub_agents") or []
    assert len(subs) == 3, f"expected 3 sub-agents, got {len(subs)}"
