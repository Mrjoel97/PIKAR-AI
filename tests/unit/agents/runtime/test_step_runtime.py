# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Consolidated tests for ``app.agents.runtime.step_runtime``.

Covers tasks 87-93 and 101 of the agent operating model W1+W2 plan:

* Task 87 — ``contract_from_initiative_step`` reads the checklist row and
  hydrates sibling steps from the same ``(initiative_id, phase)`` set.
* Task 88 — ``contract_from_department_task`` reads the task row and joins
  ``department_task_todo_items``.
* Task 89 — ``_execute_todo_items`` flips per-item status
  ``pending → in_progress → completed`` on the source table.
* Task 90 — ``_submit`` publishes every artifact AND a rendered report.
* Task 91 — ``_retry_failed_items`` only re-runs todos flagged in the
  audit; the rest are left alone.
* Task 92 — ``_escalate`` records ``status='escalated'`` and emits a
  ``workspace.status='blocked'`` event for each todo.
* Task 93 — ``execute_task`` orchestrates the full
  research → todos → audit → submit/retry/escalate flow.
* Task 101 — when a single todo raises, the loop emits a
  ``workspace.status='blocked'`` event for that item rather than crashing.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.agents.runtime import step_runtime
from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    ItemAudit,
    ResearchResult,
    StepSummary,
    TaskContract,
    TodoItem,
)

# ---------------------------------------------------------------------------
# Fixtures — small builders to keep individual tests readable.
# ---------------------------------------------------------------------------


def _make_todo(
    *,
    item_id: UUID | None = None,
    title: str = "Step",
    status: str = "pending",
) -> TodoItem:
    return TodoItem(
        id=item_id or uuid4(),
        title=title,
        description=None,
        status=status,  # type: ignore[arg-type]
        evidence=[],
        sort_order=0,
    )


def _make_contract(
    *,
    todo_items: list[TodoItem] | None = None,
    source: str = "initiative_step",
    initiative_id: UUID | None = None,
) -> TaskContract:
    return TaskContract(
        id=uuid4(),
        source=source,  # type: ignore[arg-type]
        goal="g",
        todo_items=todo_items or [_make_todo()],
        success_criteria=[],
        owners=["data"],
        evidence_required=[],
        initiative_id=initiative_id
        or (uuid4() if source == "initiative_step" else None),
        initiative_phase="build" if source == "initiative_step" else None,
        sibling_steps=[],
    )


def _make_research_complete() -> ResearchResult:
    return ResearchResult(
        summary="x",
        sources=[],
        contradictions=[],
        coverage_assessment="complete",
        missing_information=[],
    )


def _make_pass_audit() -> AuditReport:
    return AuditReport(
        overall_status="pass",
        per_item=[],
        per_criterion=[],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )


def _make_publication_result() -> MagicMock:
    """Mimic publication.PublicationResult — only ``.execution_id`` is read."""
    result = MagicMock()
    result.execution_id = uuid4()
    result.vault_document_id = None
    result.workspace_event_emitted = True
    return result


@pytest.fixture(autouse=True)
def _patch_publication(monkeypatch):
    """Ensure step_runtime.publication has callable async stubs.

    The publication module may not exist on disk (a parallel sub-agent
    ships it); even when it does, the production functions are not safe
    to call from unit tests. Individual tests override these as needed.
    """
    monkeypatch.setattr(
        step_runtime.publication,
        "publish_artifact",
        AsyncMock(return_value=_make_publication_result()),
    )
    monkeypatch.setattr(step_runtime.publication, "emit_progress_event", AsyncMock())
    monkeypatch.setattr(
        step_runtime.publication,
        "render_report_markdown",
        AsyncMock(return_value="# report\n"),
    )


# ---------------------------------------------------------------------------
# Task 87 — contract_from_initiative_step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_contract_from_initiative_step_loads_siblings(monkeypatch):
    initiative_id = uuid4()
    item_id = uuid4()
    sibling_id = uuid4()
    todo_id = uuid4()
    item_row = {
        "id": str(item_id),
        "initiative_id": str(initiative_id),
        "phase": "validation",
        "title": "Build forecast",
        "goal": "Forecast Q3 revenue",
        "metadata": {
            "todo_items": [
                {
                    "id": str(todo_id),
                    "title": "Pull data",
                    "status": "pending",
                    "evidence": [],
                    "sort_order": 0,
                }
            ],
            "success_criteria": ["+/- 5%"],
            "evidence_required": ["draft_artifact"],
        },
        "assigned_agent_id": "financial",
    }
    sibling_row = {
        "id": str(sibling_id),
        "initiative_id": str(initiative_id),
        "phase": "validation",
        "title": "Review forecast",
        "status": "pending",
        "assigned_agent_id": "executive",
    }

    fake_client = MagicMock()
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.neq.return_value = table

    responses = iter([MagicMock(data=item_row), MagicMock(data=[sibling_row])])

    async def fake_execute_async(q, op_name=None):
        return next(responses)

    monkeypatch.setattr(step_runtime, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(step_runtime, "execute_async", fake_execute_async)
    fake_client.table = MagicMock(return_value=table)

    contract = await step_runtime.contract_from_initiative_step(item_id)

    assert contract.source == "initiative_step"
    assert contract.goal == "Forecast Q3 revenue"
    assert contract.initiative_id == initiative_id
    assert contract.initiative_phase == "validation"
    assert "financial" in contract.owners
    assert len(contract.todo_items) == 1
    assert contract.todo_items[0].title == "Pull data"
    assert any(s.id == sibling_id for s in contract.sibling_steps)
    assert contract.success_criteria == ["+/- 5%"]
    assert contract.evidence_required == ["draft_artifact"]


@pytest.mark.asyncio
async def test_contract_from_initiative_step_raises_when_missing(monkeypatch):
    fake_client = MagicMock()
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table

    async def fake_execute_async(q, op_name=None):
        return MagicMock(data=None)

    monkeypatch.setattr(step_runtime, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(step_runtime, "execute_async", fake_execute_async)
    fake_client.table = MagicMock(return_value=table)

    with pytest.raises(ValueError, match="not found"):
        await step_runtime.contract_from_initiative_step(uuid4())


# ---------------------------------------------------------------------------
# Task 88 — contract_from_department_task
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_contract_from_department_task_joins_todos(monkeypatch):
    task_id = uuid4()
    todo_id = uuid4()
    task_row = {
        "id": str(task_id),
        "goal": "Reply to Acme RFP",
        "assigned_agent_id": "sales",
        "metadata": {
            "success_criteria": ["Customer accepts pricing"],
            "evidence_required": ["draft_artifact"],
        },
    }
    todo_rows = [
        {
            "id": str(todo_id),
            "task_id": str(task_id),
            "title": "Draft pricing summary",
            "status": "pending",
            "sort_order": 0,
            "evidence": [],
        }
    ]

    fake_client = MagicMock()
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.order.return_value = table

    responses = iter([MagicMock(data=task_row), MagicMock(data=todo_rows)])

    async def fake_execute_async(q, op_name=None):
        return next(responses)

    monkeypatch.setattr(step_runtime, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(step_runtime, "execute_async", fake_execute_async)
    fake_client.table = MagicMock(return_value=table)

    contract = await step_runtime.contract_from_department_task(task_id)

    assert contract.source == "department_task"
    assert contract.goal == "Reply to Acme RFP"
    assert contract.initiative_id is None
    assert contract.initiative_phase is None
    assert contract.owners == ["sales"]
    assert len(contract.todo_items) == 1
    assert contract.todo_items[0].title == "Draft pricing summary"
    assert contract.success_criteria == ["Customer accepts pricing"]
    assert contract.sibling_steps == []


@pytest.mark.asyncio
async def test_contract_from_department_task_raises_when_missing(monkeypatch):
    fake_client = MagicMock()
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table

    async def fake_execute_async(q, op_name=None):
        return MagicMock(data=None)

    monkeypatch.setattr(step_runtime, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(step_runtime, "execute_async", fake_execute_async)
    fake_client.table = MagicMock(return_value=table)

    with pytest.raises(ValueError, match="not found"):
        await step_runtime.contract_from_department_task(uuid4())


# ---------------------------------------------------------------------------
# Task 89 — _execute_todo_items flips status pending → in_progress → completed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_todo_items_walks_each_item(monkeypatch):
    contract = _make_contract(
        todo_items=[
            _make_todo(title="Step A"),
            _make_todo(title="Step B"),
        ]
    )
    research = _make_research_complete()

    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "financial"
    agent.run_step = AsyncMock(
        side_effect=[
            Artifact(kind="doc", ref="a", summary="A done", payload={}),
            Artifact(kind="doc", ref="b", summary="B done", payload={}),
        ]
    )

    update_status = AsyncMock()
    monkeypatch.setattr(step_runtime, "_update_todo_status", update_status)

    artifacts = await step_runtime._execute_todo_items(agent, contract, research)

    assert len(artifacts) == 2
    # Each todo: in_progress then completed → 4 calls total in order.
    states = [c.kwargs["status"] for c in update_status.await_args_list]
    assert states == ["in_progress", "completed", "in_progress", "completed"]
    # The workspace heard about both starts.
    progress_statuses = [
        c.kwargs["status"]
        for c in step_runtime.publication.emit_progress_event.await_args_list
    ]
    assert progress_statuses.count("started") == 2


# ---------------------------------------------------------------------------
# Task 101 — blocked items emit workspace.status='blocked'
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_todo_items_emits_blocked_on_run_step_failure(monkeypatch):
    contract = _make_contract(todo_items=[_make_todo(title="Step A")])
    research = _make_research_complete()

    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "data"
    agent.run_step = AsyncMock(side_effect=RuntimeError("boom"))

    monkeypatch.setattr(step_runtime, "_update_todo_status", AsyncMock())

    out = await step_runtime._execute_todo_items(agent, contract, research)

    # Nothing produced — the only todo blew up.
    assert out == []
    statuses = [
        c.kwargs["status"]
        for c in step_runtime.publication.emit_progress_event.await_args_list
    ]
    assert "blocked" in statuses
    assert "started" in statuses


# ---------------------------------------------------------------------------
# Task 90 — _submit publishes every artifact + the rendered report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_publishes_artifacts_then_report():
    contract = _make_contract(todo_items=[_make_todo(title="x", status="completed")])
    research = _make_research_complete()
    audit = _make_pass_audit()
    artifacts = [Artifact(kind="doc", ref="r1", summary="draft", payload={})]

    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "data"

    result = await step_runtime._submit(agent, contract, artifacts, research, audit)

    publish = step_runtime.publication.publish_artifact
    assert result.status == "submitted"
    assert publish.await_count == 2  # one artifact + one report
    second_call = publish.await_args_list[1]
    assert second_call.kwargs["artifact"].kind == "report"
    assert "# report" in second_call.kwargs["artifact"].payload["markdown"]
    # The report is appended to the returned artifact list.
    assert result.artifacts[-1].kind == "report"


# ---------------------------------------------------------------------------
# Task 91 — _retry_failed_items only re-runs failed todos
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_only_failed_items(monkeypatch):
    good = _make_todo(title="Step A", status="completed")
    bad = _make_todo(title="Step B", status="completed")
    contract = _make_contract(todo_items=[good, bad])
    audit = AuditReport(
        overall_status="partial",
        per_item=[
            ItemAudit(item_id=good.id, status="pass", evidence_pointers=[], gaps=[]),
            ItemAudit(
                item_id=bad.id,
                status="fail",
                evidence_pointers=[],
                gaps=["missing chart"],
            ),
        ],
        per_criterion=[],
        gaps=["chart missing"],
        policy_violations=[],
        recoverable=True,
        next_action="retry",
    )

    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "data"
    agent.run_step = AsyncMock(
        return_value=Artifact(kind="doc", ref="b2", summary="retry", payload={})
    )

    monkeypatch.setattr(step_runtime, "_update_todo_status", AsyncMock())
    monkeypatch.setattr(
        step_runtime,
        "_self_audit",
        AsyncMock(return_value=_make_pass_audit()),
    )

    submit_mock = AsyncMock(
        return_value=step_runtime.TaskResult(
            status="submitted",
            artifacts=[],
            audit=_make_pass_audit(),
            execution_id=uuid4(),
        )
    )
    monkeypatch.setattr(step_runtime, "_submit", submit_mock)

    result = await step_runtime._retry_failed_items(agent, contract, audit)

    assert result.status == "submitted"
    # Only one run_step call — the one failed item.
    assert agent.run_step.await_count == 1
    assert agent.run_step.await_args.kwargs["item"].id == bad.id
    submit_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_retry_escalates_when_no_failed_items(monkeypatch):
    """If per_item is empty (or all pass), retry has nothing to do → escalate."""
    contract = _make_contract()
    audit = AuditReport(
        overall_status="partial",
        per_item=[],  # nothing concrete to retry
        per_criterion=[],
        gaps=["high-level gap"],
        policy_violations=[],
        recoverable=True,
        next_action="retry",
    )

    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "data"

    escalate_mock = AsyncMock(
        return_value=step_runtime.TaskResult(
            status="escalated",
            artifacts=[],
            audit=audit,
            execution_id=uuid4(),
        )
    )
    monkeypatch.setattr(step_runtime, "_escalate", escalate_mock)

    result = await step_runtime._retry_failed_items(agent, contract, audit)

    assert result.status == "escalated"
    escalate_mock.assert_awaited_once()


# ---------------------------------------------------------------------------
# Task 92 — _escalate emits blocked + publishes escalation report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_escalate_emits_blocked_and_persists():
    contract = _make_contract(
        todo_items=[
            _make_todo(title="x", status="completed"),
            _make_todo(title="y", status="pending"),
        ]
    )
    audit = AuditReport(
        overall_status="fail",
        per_item=[],
        per_criterion=[],
        gaps=["unrecoverable: source unavailable"],
        policy_violations=[],
        recoverable=False,
        next_action="escalate",
    )
    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "data"

    result = await step_runtime._escalate(agent, contract, audit)

    assert result.status == "escalated"
    # Blocked event for each todo.
    statuses = [
        c.kwargs["status"]
        for c in step_runtime.publication.emit_progress_event.await_args_list
    ]
    assert statuses.count("blocked") == 2
    # The escalation writes one report artifact for visibility.
    publish = step_runtime.publication.publish_artifact
    assert publish.await_count == 1
    assert publish.await_args.kwargs["artifact"].kind == "report"
    # And the rendered missing_information echoes the audit gaps.
    render = step_runtime.publication.render_report_markdown
    render.assert_awaited_once()
    research_arg = render.await_args.kwargs["research"]
    assert research_arg.missing_information == ["unrecoverable: source unavailable"]


# ---------------------------------------------------------------------------
# Task 93 — execute_task orchestrates the full flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_task_submitted_path(monkeypatch):
    contract = _make_contract()
    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "data"
    agent.research = AsyncMock(return_value=_make_research_complete())
    agent.audit = AsyncMock(return_value=_make_pass_audit())

    monkeypatch.setattr(
        step_runtime,
        "_execute_todo_items",
        AsyncMock(
            return_value=[Artifact(kind="doc", ref="r", summary="s", payload={})]
        ),
    )
    submit_mock = AsyncMock(
        return_value=step_runtime.TaskResult(
            status="submitted",
            artifacts=[],
            audit=_make_pass_audit(),
            execution_id=uuid4(),
        )
    )
    monkeypatch.setattr(step_runtime, "_submit", submit_mock)

    result = await step_runtime.execute_task(agent, contract)

    assert result.status == "submitted"
    submit_mock.assert_awaited_once()
    agent.research.assert_awaited_once_with(contract=contract)
    agent.audit.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_task_routes_to_retry_when_recoverable(monkeypatch):
    contract = _make_contract()
    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "data"
    agent.research = AsyncMock(return_value=_make_research_complete())
    agent.audit = AsyncMock(
        return_value=AuditReport(
            overall_status="partial",
            per_item=[],
            per_criterion=[],
            gaps=["gap"],
            policy_violations=[],
            recoverable=True,
            next_action="retry",
        )
    )
    monkeypatch.setattr(step_runtime, "_execute_todo_items", AsyncMock(return_value=[]))
    retry_mock = AsyncMock(
        return_value=step_runtime.TaskResult(
            status="submitted",
            artifacts=[],
            audit=agent.audit.return_value,
            execution_id=uuid4(),
        )
    )
    monkeypatch.setattr(step_runtime, "_retry_failed_items", retry_mock)

    result = await step_runtime.execute_task(agent, contract)

    assert result.status == "submitted"
    retry_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_task_routes_to_escalate_when_unrecoverable(monkeypatch):
    contract = _make_contract()
    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "data"
    agent.research = AsyncMock(return_value=_make_research_complete())
    agent.audit = AsyncMock(
        return_value=AuditReport(
            overall_status="fail",
            per_item=[],
            per_criterion=[],
            gaps=["unrecoverable"],
            policy_violations=[],
            recoverable=False,
            next_action="escalate",
        )
    )
    monkeypatch.setattr(step_runtime, "_execute_todo_items", AsyncMock(return_value=[]))
    escalate_mock = AsyncMock(
        return_value=step_runtime.TaskResult(
            status="escalated",
            artifacts=[],
            audit=agent.audit.return_value,
            execution_id=uuid4(),
        )
    )
    monkeypatch.setattr(step_runtime, "_escalate", escalate_mock)

    result = await step_runtime.execute_task(agent, contract)

    assert result.status == "escalated"
    escalate_mock.assert_awaited_once()


# ---------------------------------------------------------------------------
# _update_todo_status — exercises both source-table branches.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_todo_status_initiative_step_rewrites_metadata(monkeypatch):
    contract = _make_contract()
    item_id = uuid4()

    fake_client = MagicMock()
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.update.return_value = table

    read_response = MagicMock(
        data={
            "metadata": {
                "todo_items": [
                    {"id": str(item_id), "title": "x", "status": "in_progress"},
                    {"id": str(uuid4()), "title": "y", "status": "pending"},
                ]
            }
        }
    )
    write_response = MagicMock(data=[{"id": str(contract.id)}])
    responses = iter([read_response, write_response])
    update_payloads: list[dict] = []

    async def fake_execute_async(q, op_name=None):
        return next(responses)

    def update_capture(payload):
        update_payloads.append(payload)
        return table

    table.update = update_capture
    monkeypatch.setattr(step_runtime, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(step_runtime, "execute_async", fake_execute_async)
    fake_client.table = MagicMock(return_value=table)

    await step_runtime._update_todo_status(
        contract=contract, item_id=item_id, status="completed"
    )

    # The matching todo entry was flipped to 'completed' inside the write.
    assert len(update_payloads) == 1
    new_items = update_payloads[0]["metadata"]["todo_items"]
    matched = next(it for it in new_items if str(it["id"]) == str(item_id))
    assert matched["status"] == "completed"


@pytest.mark.asyncio
async def test_update_todo_status_department_task_direct_update(monkeypatch):
    contract = _make_contract(source="department_task")
    item_id = uuid4()

    fake_client = MagicMock()
    table = MagicMock()
    table.update.return_value = table
    table.eq.return_value = table

    call_log: list[tuple[str, Any]] = []

    async def fake_execute_async(q, op_name=None):
        call_log.append(("execute", op_name))
        return MagicMock(data=[])

    monkeypatch.setattr(step_runtime, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(step_runtime, "execute_async", fake_execute_async)
    fake_client.table = MagicMock(return_value=table)

    await step_runtime._update_todo_status(
        contract=contract, item_id=item_id, status="completed"
    )

    # Exactly one execute_async — direct update by id.
    assert call_log == [("execute", "department_task_todo_items.update")]
    table.update.assert_called_once_with({"status": "completed"})


# ---------------------------------------------------------------------------
# Sanity — module surface matches the documented public API.
# ---------------------------------------------------------------------------


def test_module_exports_public_api():
    for name in (
        "contract_from_initiative_step",
        "contract_from_department_task",
        "execute_task",
        "TaskResult",
    ):
        assert hasattr(step_runtime, name), f"missing public symbol: {name}"


def test_step_summary_unused_import_guard():
    """The module imports StepSummary; ensure it stays importable downstream."""
    assert StepSummary is not None
