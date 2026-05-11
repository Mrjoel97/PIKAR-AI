# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Task execution runtime — adapters + the ``execute_task`` loop.

Implements spec section 6 of the agent operating model:

* Two contract adapters convert backing rows (initiative checklist items or
  department tasks) into the canonical :class:`TaskContract` that
  ``execute_task`` operates on.
* The :func:`execute_task` loop wires research → todo-execution → audit →
  submit/retry/escalate, persisting per-item status updates back to the
  source table as work progresses.

Covers Tasks 87-93 + 101 in ``.planning/_subagent_tasks.json``.

The publication primitive is owned by ``app.agents.runtime.publication``
and is imported lazily so this module remains importable during the brief
window when the parallel publication sub-agent has not yet landed its
module. Tests monkeypatch ``step_runtime.publication.<fn>`` directly.
"""

from __future__ import annotations

import logging
import types as _types
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    ResearchResult,
    StepSummary,
    TaskContract,
    TodoItem,
)
from app.services.supabase_async import execute_async
from app.services.supabase_client import get_service_client

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.agents.base_agent import PikarBaseAgent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Publication import — graceful fallback while the parallel agent ships it.
# ---------------------------------------------------------------------------

try:  # pragma: no cover - exercised in production when module lands
    from app.agents.runtime import publication as publication
except ImportError:  # pragma: no cover - exercised pre-publication-merge
    # Create a stub module with the *names* tests expect, all set to None.
    # Tests always monkeypatch these attributes anyway, so the stub never
    # has to do real work; it just keeps ``step_runtime.publication`` a
    # valid reference for ``monkeypatch.setattr`` to write into.
    publication = _types.ModuleType("app.agents.runtime.publication")
    publication.publish_artifact = None  # type: ignore[attr-defined]
    publication.emit_progress_event = None  # type: ignore[attr-defined]
    publication.render_report_markdown = None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# TaskResult — the public return shape of ``execute_task``.
# ---------------------------------------------------------------------------


@dataclass
class TaskResult:
    """The outcome of a single :func:`execute_task` invocation.

    ``execution_id`` is the ``agent_task_executions`` row id minted by
    ``publication.publish_artifact``; it is propagated back so downstream
    observers (workspace SSE, telemetry) can link runtime state to the
    persisted execution row.
    """

    status: Literal["submitted", "retrying", "escalated", "failed"]
    artifacts: list[Artifact]
    audit: AuditReport
    execution_id: UUID


# ---------------------------------------------------------------------------
# Helpers — parse + coerce raw Supabase rows into the dataclass types.
# ---------------------------------------------------------------------------


def _coerce_todo(row: dict[str, Any]) -> TodoItem | None:
    """Best-effort coerce a raw JSONB / row dict into a :class:`TodoItem`."""
    try:
        return TodoItem(
            id=UUID(str(row["id"])),
            title=str(row.get("title") or ""),
            description=row.get("description"),
            status=row.get("status") or "pending",
            evidence=list(row.get("evidence") or []),
            sort_order=int(row.get("sort_order") or 0),
        )
    except Exception:
        logger.warning("dropping malformed todo_item: %r", row)
        return None


def _todo_items_from_metadata(meta: dict | None) -> list[TodoItem]:
    """Hydrate todo items from a checklist row's ``metadata.todo_items``."""
    if not meta:
        return []
    items: list[TodoItem] = []
    for raw in meta.get("todo_items") or []:
        coerced = _coerce_todo(raw)
        if coerced is not None:
            items.append(coerced)
    return items


def _coerce_sibling(row: dict[str, Any]) -> StepSummary:
    """Coerce a raw sibling-step row into a :class:`StepSummary`."""
    return StepSummary(
        id=UUID(str(row["id"])),
        title=str(row.get("title") or ""),
        status=str(row.get("status") or "pending"),
        assigned_agent_id=row.get("assigned_agent_id"),
    )


# ---------------------------------------------------------------------------
# Task 87 — initiative-step adapter.
# ---------------------------------------------------------------------------


async def contract_from_initiative_step(checklist_item_id: UUID) -> TaskContract:
    """Build a :class:`TaskContract` from an ``initiative_checklist_items`` row.

    Hydrates ``sibling_steps`` from the same ``(initiative_id, phase)`` set
    so the agent can see — but not mutate — the rest of the plan.
    """
    client = get_service_client()
    item_res = await execute_async(
        client.table("initiative_checklist_items")
        .select("*")
        .eq("id", str(checklist_item_id))
        .single(),
        op_name="initiative_checklist_items.contract",
    )
    item = item_res.data
    if not item:
        raise ValueError(f"checklist item {checklist_item_id} not found")

    sibling_res = await execute_async(
        client.table("initiative_checklist_items")
        .select("id, title, status, phase, sort_order, assigned_agent_id")
        .eq("initiative_id", item["initiative_id"])
        .eq("phase", item["phase"])
        .neq("id", str(checklist_item_id)),
        op_name="initiative_checklist_items.siblings",
    )
    siblings = [_coerce_sibling(s) for s in (sibling_res.data or [])]

    metadata = item.get("metadata") or {}
    owners: list[str] = []
    if item.get("assigned_agent_id"):
        owners.append(item["assigned_agent_id"])

    return TaskContract(
        id=UUID(str(item["id"])),
        source="initiative_step",
        goal=item.get("goal") or item.get("title") or "",
        todo_items=_todo_items_from_metadata(metadata),
        success_criteria=list(metadata.get("success_criteria") or []),
        owners=owners,
        evidence_required=list(metadata.get("evidence_required") or []),
        initiative_id=UUID(str(item["initiative_id"])),
        initiative_phase=item.get("phase"),
        sibling_steps=siblings,
    )


# ---------------------------------------------------------------------------
# Task 88 — department-task adapter.
# ---------------------------------------------------------------------------


async def contract_from_department_task(task_id: UUID) -> TaskContract:
    """Build a :class:`TaskContract` from a ``department_tasks`` row + todos."""
    client = get_service_client()
    task_res = await execute_async(
        client.table("department_tasks").select("*").eq("id", str(task_id)).single(),
        op_name="department_tasks.contract",
    )
    task = task_res.data
    if not task:
        raise ValueError(f"department task {task_id} not found")

    todos_res = await execute_async(
        client.table("department_task_todo_items")
        .select("*")
        .eq("task_id", str(task_id))
        .order("sort_order"),
        op_name="department_task_todo_items.list",
    )
    todos: list[TodoItem] = []
    for raw in todos_res.data or []:
        coerced = _coerce_todo(raw)
        if coerced is not None:
            todos.append(coerced)

    metadata = task.get("metadata") or {}
    owners: list[str] = []
    if task.get("assigned_agent_id"):
        owners.append(task["assigned_agent_id"])

    return TaskContract(
        id=UUID(str(task["id"])),
        source="department_task",
        goal=task.get("goal") or task.get("title") or "",
        todo_items=todos,
        success_criteria=list(metadata.get("success_criteria") or []),
        owners=owners,
        evidence_required=list(metadata.get("evidence_required") or []),
        initiative_id=None,
        initiative_phase=None,
        sibling_steps=[],
    )


# ---------------------------------------------------------------------------
# Per-todo status persistence — writes back to the source table.
# ---------------------------------------------------------------------------


async def _update_todo_status(
    *, contract: TaskContract, item_id: UUID, status: str
) -> None:
    """Persist a single todo's status to its backing table.

    * ``initiative_step``: lives inside the parent checklist item's
      ``metadata.todo_items`` JSONB array → read-modify-write.
    * ``department_task``: lives in ``department_task_todo_items`` →
      direct update by ``id``.
    """
    client = get_service_client()
    if contract.source == "initiative_step":
        cur = await execute_async(
            client.table("initiative_checklist_items")
            .select("metadata")
            .eq("id", str(contract.id))
            .single(),
            op_name="initiative_checklist_items.todo.read",
        )
        meta = (cur.data or {}).get("metadata") or {}
        items = list(meta.get("todo_items") or [])
        for entry in items:
            if str(entry.get("id")) == str(item_id):
                entry["status"] = status
                break
        meta["todo_items"] = items
        await execute_async(
            client.table("initiative_checklist_items")
            .update({"metadata": meta})
            .eq("id", str(contract.id)),
            op_name="initiative_checklist_items.todo.update",
        )
    elif contract.source == "department_task":
        await execute_async(
            client.table("department_task_todo_items")
            .update({"status": status})
            .eq("id", str(item_id)),
            op_name="department_task_todo_items.update",
        )


# ---------------------------------------------------------------------------
# Task 89 / 101 — _execute_todo_items walks each todo and emits progress.
# ---------------------------------------------------------------------------


async def _execute_todo_items(
    agent: PikarBaseAgent,
    contract: TaskContract,
    research: ResearchResult,
) -> list[Artifact]:
    """Iterate todo items one at a time, with status updates + progress events.

    For each item the loop:
      1. Flips status ``pending → in_progress`` and emits a ``started`` event.
      2. Invokes ``agent.run_step(item=, research=)``.
      3. On success — appends the artifact and flips to ``completed``.
      4. On exception — flips to ``blocked`` and emits a ``blocked`` workspace
         event (Task 101) instead of bubbling, so other items can still run.
    """
    artifacts: list[Artifact] = []
    for item in contract.todo_items:
        await _update_todo_status(
            contract=contract, item_id=item.id, status="in_progress"
        )
        await publication.emit_progress_event(
            user_id=agent.user_id,
            agent_id=agent.agent_id,
            contract_id=contract.id,
            item=item.title,
            status="started",
        )
        try:
            artifact = await agent.run_step(item=item, research=research)
        except Exception as exc:
            logger.exception("todo %s failed: %s", item.id, exc)
            await _update_todo_status(
                contract=contract, item_id=item.id, status="blocked"
            )
            await publication.emit_progress_event(
                user_id=agent.user_id,
                agent_id=agent.agent_id,
                contract_id=contract.id,
                item=item.title,
                status="blocked",
            )
            continue
        if artifact is not None:
            artifacts.append(artifact)
        await _update_todo_status(
            contract=contract, item_id=item.id, status="completed"
        )
    return artifacts


# ---------------------------------------------------------------------------
# Self-audit shim — defers to ``agent.audit`` when available.
# ---------------------------------------------------------------------------


async def _self_audit(
    agent: PikarBaseAgent,
    contract: TaskContract,
    artifacts: list[Artifact],
) -> AuditReport:
    """Defer to the agent's audit method; fall back to a passing report.

    The real audit lives in ``app.agents.runtime.audit.audit_against_contract``
    and is wired in by ``PikarBaseAgent.audit``. This wrapper keeps
    ``step_runtime`` testable in isolation.
    """
    if hasattr(agent, "audit"):
        return await agent.audit(contract=contract, artifacts=artifacts)
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
# Task 90 — _submit publishes every artifact + the rendered report.
# ---------------------------------------------------------------------------


async def _submit(
    agent: PikarBaseAgent,
    contract: TaskContract,
    artifacts: list[Artifact],
    research: ResearchResult,
    audit: AuditReport,
) -> TaskResult:
    """Publish each artifact through ``publication.publish_artifact``, then a
    final Layer-2 report rendered from the contract + audit + research."""
    last_publication = None
    for art in artifacts:
        last_publication = await publication.publish_artifact(
            user_id=agent.user_id,
            agent_id=agent.agent_id,
            contract=contract,
            artifact=art,
            audit=audit,
        )

    report_md = await publication.render_report_markdown(
        contract=contract,
        research=research,
        audit=audit,
        artifacts=artifacts,
        agent_id=agent.agent_id,
    )
    report_artifact = Artifact(
        kind="report",
        ref=f"agent_report://{contract.id}",
        summary=f"Submission report — {contract.goal}",
        payload={"markdown": report_md},
    )
    last_publication = await publication.publish_artifact(
        user_id=agent.user_id,
        agent_id=agent.agent_id,
        contract=contract,
        artifact=report_artifact,
        audit=audit,
    )

    execution_id = (
        last_publication.execution_id if last_publication is not None else UUID(int=0)
    )
    return TaskResult(
        status="submitted",
        artifacts=[*artifacts, report_artifact],
        audit=audit,
        execution_id=execution_id,
    )


# ---------------------------------------------------------------------------
# Task 91 — _retry_failed_items only re-runs todos flagged in the audit.
# ---------------------------------------------------------------------------


async def _retry_failed_items(
    agent: PikarBaseAgent,
    contract: TaskContract,
    audit: AuditReport,
) -> TaskResult:
    """Re-run only the todos the audit marked ``!= 'pass'``, then re-submit.

    If the audit produced no per-item rows (nothing concrete to retry), the
    loop escalates immediately rather than spinning on empty work.
    """
    failed_ids = {a.item_id for a in audit.per_item if a.status != "pass"}
    failed_items = [t for t in contract.todo_items if t.id in failed_ids]
    if not failed_items:
        return await _escalate(agent, contract, audit)

    new_artifacts: list[Artifact] = []
    for item in failed_items:
        await _update_todo_status(
            contract=contract, item_id=item.id, status="in_progress"
        )
        await publication.emit_progress_event(
            user_id=agent.user_id,
            agent_id=agent.agent_id,
            contract_id=contract.id,
            item=item.title,
            status="started",
        )
        try:
            artifact = await agent.run_step(item=item, research=None)
        except Exception:
            logger.exception("retry of %s failed", item.id)
            await _update_todo_status(
                contract=contract, item_id=item.id, status="blocked"
            )
            await publication.emit_progress_event(
                user_id=agent.user_id,
                agent_id=agent.agent_id,
                contract_id=contract.id,
                item=item.title,
                status="blocked",
            )
            continue
        if artifact is not None:
            new_artifacts.append(artifact)
        await _update_todo_status(
            contract=contract, item_id=item.id, status="completed"
        )

    new_audit = await _self_audit(agent, contract, new_artifacts)
    if new_audit.overall_status != "pass":
        return await _escalate(agent, contract, new_audit)

    # Empty research is fine on retry — the report renderer tolerates it.
    empty_research = ResearchResult(
        summary="",
        sources=[],
        contradictions=[],
        coverage_assessment="complete",
        missing_information=[],
    )
    return await _submit(agent, contract, new_artifacts, empty_research, new_audit)


# ---------------------------------------------------------------------------
# Task 92 — _escalate marks status='escalated' and emits blocked events.
# ---------------------------------------------------------------------------


async def _escalate(
    agent: PikarBaseAgent,
    contract: TaskContract,
    audit: AuditReport,
) -> TaskResult:
    """Surface an unrecoverable failure to workspace + reports UI.

    Emits a ``blocked`` workspace event per todo for visibility and writes
    an escalation report artifact so the user can read what went wrong.
    """
    for item in contract.todo_items:
        await publication.emit_progress_event(
            user_id=agent.user_id,
            agent_id=agent.agent_id,
            contract_id=contract.id,
            item=item.title,
            status="blocked",
        )

    report_md = await publication.render_report_markdown(
        contract=contract,
        research=ResearchResult(
            summary="(escalation — see audit gaps)",
            sources=[],
            contradictions=[],
            coverage_assessment="partial",
            missing_information=list(audit.gaps),
        ),
        audit=audit,
        artifacts=[],
        agent_id=agent.agent_id,
    )
    report_artifact = Artifact(
        kind="report",
        ref=f"agent_escalation://{contract.id}",
        summary=f"Escalation — {contract.goal}",
        payload={"markdown": report_md},
    )
    publication_result = await publication.publish_artifact(
        user_id=agent.user_id,
        agent_id=agent.agent_id,
        contract=contract,
        artifact=report_artifact,
        audit=audit,
    )
    execution_id = (
        publication_result.execution_id
        if publication_result is not None
        else UUID(int=0)
    )
    return TaskResult(
        status="escalated",
        artifacts=[report_artifact],
        audit=audit,
        execution_id=execution_id,
    )


# ---------------------------------------------------------------------------
# Task 93 — execute_task: research → todos → audit → submit/retry/escalate.
# ---------------------------------------------------------------------------


async def execute_task(agent: PikarBaseAgent, contract: TaskContract) -> TaskResult:
    """The main loop from spec § 6.

    Order is fixed and enforced: research must complete (gated by
    ``research_gate``) before ``_execute_todo_items`` runs; audit runs over
    whatever artifacts the todo loop produced; then routing splits on
    ``audit.overall_status`` and ``audit.recoverable``.
    """
    research = await agent.research(contract=contract)
    artifacts = await _execute_todo_items(agent, contract, research)
    audit = await agent.audit(contract=contract, artifacts=artifacts)
    if audit.overall_status == "pass":
        return await _submit(agent, contract, artifacts, research, audit)
    if audit.recoverable:
        return await _retry_failed_items(agent, contract, audit)
    return await _escalate(agent, contract, audit)


__all__ = [
    "TaskResult",
    "contract_from_department_task",
    "contract_from_initiative_step",
    "execute_task",
]
