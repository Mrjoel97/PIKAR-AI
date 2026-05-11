# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Single publication primitive — four sinks per spec §12.

Every output that leaves an agent goes through ``publish_artifact`` so the
four sinks fire atomically (from the caller's perspective):

  1. ``agent_task_executions`` row — operational history (Layer-1 memory).
  2. Knowledge vault — for ``"agent_report"``, ``"video_render"``, ``"image"``,
     ``"doc"`` artifact kinds (Layer-2 memory + Layer-3 retrieval feedstock).
  3. Workspace SSE channel — ``WorkspaceArtifactEvent`` for the canvas UI.
  4. Reports UI — falls out of (1) for free via the routers/reports.py join.

``emit_progress_event`` is the lighter-weight companion for the ``progress``
event kind. ``render_report_markdown`` produces the Layer-2 markdown body.

Imports defer where they would form runtime cycles. Callers never have to
worry about a sink outage masking the agent's actual output: failures inside
any sink are logged and swallowed — the agent's published artifact is still
returned via ``PublicationResult``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    DirectRequest,
    ResearchResult,
    TaskContract,
    TodoItem,
    WorkspaceArtifactEvent,
    WorkspaceProgressEvent,
)
from app.services import knowledge_service, workspace_event_bus
from app.services.supabase_async import execute_async
from app.services.supabase_client import get_service_client

if TYPE_CHECKING:
    from app.skills.registry import AgentID

logger = logging.getLogger(__name__)


# Artifact kinds whose payloads should land in the knowledge vault for
# Layer-3 retrieval. Anything else (e.g. ``"status_update"``, ``"data_query"``)
# stays in ``agent_task_executions.artifacts`` only.
VAULT_BOUND_KINDS: frozenset[str] = frozenset(
    {"agent_report", "video_render", "image", "doc", "report"}
)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PublicationResult:
    """Return value of :func:`publish_artifact`.

    ``execution_id`` is the ``agent_task_executions`` row id (UUID(int=0) if
    Supabase returned no row — caller can treat that as "best-effort"). The
    other two fields make sink success observable for callers that want to
    surface degraded behavior.
    """

    execution_id: UUID
    vault_document_id: UUID | None
    workspace_event_emitted: bool


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _agent_id_str(agent_id: Any) -> str:
    """Normalize an ``AgentID`` enum or string to a plain string."""
    value = getattr(agent_id, "value", None)
    return value if isinstance(value, str) else str(agent_id)


def _artifact_dict(artifact: Artifact) -> dict[str, Any]:
    """Serialize a frozen-dataclass :class:`Artifact` into JSONB shape."""
    return {
        "kind": artifact.kind,
        "ref": artifact.ref,
        "summary": artifact.summary,
        "payload": artifact.payload,
    }


def _todo_dict(item: TodoItem) -> dict[str, Any]:
    """Serialize a frozen-dataclass :class:`TodoItem` for ``todo_snapshot``."""
    return {
        "id": str(item.id),
        "title": item.title,
        "description": item.description,
        "status": item.status,
        "evidence": item.evidence,
        "sort_order": item.sort_order,
    }


def _contract_meta(contract: TaskContract | DirectRequest) -> dict[str, Any]:
    """Return the ``agent_task_executions`` mode + identity columns.

    Initiative-mode rows carry the contract id, source, initiative id, goal,
    and todo snapshot. Direct-mode rows leave all of those NULL and set
    ``contract_source='direct_request'`` so the reports UI can distinguish
    them.
    """
    if isinstance(contract, TaskContract):
        return {
            "mode": "initiative",
            "contract_id": str(contract.id),
            "contract_source": contract.source,
            "initiative_id": (
                str(contract.initiative_id) if contract.initiative_id else None
            ),
            "goal": contract.goal,
            "todo_snapshot": [_todo_dict(t) for t in contract.todo_items],
        }
    # DirectRequest
    return {
        "mode": "direct",
        "contract_id": None,
        "contract_source": "direct_request",
        "initiative_id": None,
        "goal": None,
        "todo_snapshot": None,
    }


def _status_from_audit(audit: AuditReport | None) -> str:
    """Map an audit report into the constrained ``status`` column value."""
    if audit is None:
        return "running"
    if audit.overall_status == "pass":
        return "submitted"
    if audit.next_action == "escalate":
        return "escalated"
    if audit.next_action == "submit":
        return "submitted"
    return "running"


async def _vault_publish(
    *,
    user_id: UUID,
    agent_id: str,
    contract: TaskContract | DirectRequest,
    artifact: Artifact,
) -> UUID | None:
    """Persist a vault-bound artifact via :mod:`knowledge_service`.

    Returns the new vault document id on success, ``None`` on failure
    (failures are logged but never propagate — see module docstring).
    """
    try:
        payload = artifact.payload if isinstance(artifact.payload, dict) else {}
        content = payload.get("markdown") or payload.get("content") or artifact.summary
        if isinstance(contract, TaskContract):
            title = f"{agent_id} - {contract.goal}"
            contract_id = str(contract.id)
            initiative_id = (
                str(contract.initiative_id) if contract.initiative_id else None
            )
        else:
            title = f"{agent_id} - {artifact.kind}"
            contract_id = None
            initiative_id = None
        metadata = {
            "artifact_kind": artifact.kind,
            "ref": artifact.ref,
            "summary": artifact.summary,
            "contract_id": contract_id,
            "initiative_id": initiative_id,
        }
        result = await knowledge_service.add_document(
            user_id=user_id,
            agent_id=agent_id,
            kind="agent_report",
            title=title,
            content=content,
            metadata=metadata,
        )
        if isinstance(result, UUID):
            return result
        if isinstance(result, str):
            try:
                return UUID(result)
            except ValueError:
                return None
        return None
    except Exception:
        logger.exception("vault publish failed for %s/%s", agent_id, artifact.kind)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def emit_progress_event(
    *,
    user_id: UUID,
    agent_id: AgentID | str,
    contract_id: UUID | None = None,
    item: str,
    status: Literal["started", "in_progress", "blocked"],
) -> None:
    """Convenience wrapper around :func:`workspace_event_bus.publish`.

    ``contract_id`` is optional so the lifecycle ``after_tool`` callback —
    which may run for direct-mode turns — can call this without first
    threading the (possibly absent) contract id through every hop.
    """
    event = WorkspaceProgressEvent(
        agent_id=_agent_id_str(agent_id),
        contract_id=contract_id,
        item=item,
        status=status,
    )
    try:
        await workspace_event_bus.publish(user_id, event)
    except Exception:
        logger.exception("emit_progress_event failed: agent=%s item=%s", agent_id, item)


async def publish_artifact(
    *,
    user_id: UUID,
    agent_id: AgentID | str,
    contract: TaskContract | DirectRequest,
    artifact: Artifact,
    audit: AuditReport | None,
) -> PublicationResult:
    """Publish an artifact to all four sinks (spec §12).

    The DB upsert is keyed on ``contract_id`` for initiative-mode rows, so
    callers may re-invoke this with additional artifacts and the row will be
    merged rather than duplicated. Direct-mode rows get a fresh id every
    call (no natural key).

    Sinks 2/3 are best-effort: their failures are logged but the function
    still returns a ``PublicationResult`` so the caller can keep moving.
    """
    agent_id_str = _agent_id_str(agent_id)
    client = get_service_client()
    meta = _contract_meta(contract)

    # --- Sink 1: agent_task_executions upsert ---------------------------------
    existing_artifacts: list[dict[str, Any]] = []
    existing_id: str | None = None
    if meta["contract_id"]:
        try:
            prior = await execute_async(
                client.table("agent_task_executions")
                .select("id, artifacts")
                .eq("contract_id", meta["contract_id"])
                .eq("user_id", str(user_id))
                .limit(1),
                op_name="agent_task_executions.select",
            )
            if prior and getattr(prior, "data", None):
                row = prior.data[0]
                existing_id = row.get("id")
                existing_artifacts = list(row.get("artifacts") or [])
        except Exception:
            logger.exception("agent_task_executions select failed")

    payload_artifacts = [*existing_artifacts, _artifact_dict(artifact)]
    status_value = _status_from_audit(audit)

    row: dict[str, Any] = {
        "user_id": str(user_id),
        "agent_id": agent_id_str,
        "mode": meta["mode"],
        "contract_id": meta["contract_id"],
        "contract_source": meta["contract_source"],
        "initiative_id": meta["initiative_id"],
        "goal": meta["goal"],
        "todo_snapshot": meta["todo_snapshot"],
        "status": status_value,
        "artifacts": payload_artifacts,
    }
    # When we already have a row id (idempotent retry), include it so the
    # upsert hits the same row even if the conflict key isn't ``id``.
    if existing_id:
        row["id"] = existing_id
    if status_value in {"submitted", "escalated", "failed"}:
        row["completed_at"] = datetime.now(timezone.utc).isoformat()

    execution_id = UUID(int=0)
    try:
        on_conflict = "contract_id" if meta["contract_id"] else "id"
        response = await execute_async(
            client.table("agent_task_executions").upsert(row, on_conflict=on_conflict),
            op_name="agent_task_executions.upsert",
        )
        if response and getattr(response, "data", None):
            data = response.data[0]
            if data.get("id"):
                execution_id = UUID(data["id"])
        elif existing_id:
            execution_id = UUID(existing_id)
    except Exception:
        logger.exception("agent_task_executions upsert failed")
        if existing_id:
            try:
                execution_id = UUID(existing_id)
            except ValueError:
                pass

    # --- Sink 2: knowledge vault ----------------------------------------------
    vault_doc_id: UUID | None = None
    if artifact.kind in VAULT_BOUND_KINDS:
        vault_doc_id = await _vault_publish(
            user_id=user_id,
            agent_id=agent_id_str,
            contract=contract,
            artifact=artifact,
        )

    # --- Sink 3: workspace SSE -------------------------------------------------
    workspace_emitted = False
    preview_url: str | None = None
    if isinstance(artifact.payload, dict):
        candidate = artifact.payload.get("preview_url")
        if isinstance(candidate, str):
            preview_url = candidate

    event = WorkspaceArtifactEvent(
        agent_id=agent_id_str,
        contract_id=(UUID(meta["contract_id"]) if meta["contract_id"] else None),
        artifact_kind=artifact.kind,
        ref=artifact.ref,
        summary=artifact.summary,
        preview_url=preview_url,
    )
    try:
        await workspace_event_bus.publish(user_id, event)
        workspace_emitted = True
    except Exception:
        logger.exception(
            "workspace_event_bus.publish failed: agent=%s kind=%s",
            agent_id_str,
            artifact.kind,
        )

    # --- Sink 4: reports UI ----------------------------------------------------
    # No additional write: ``routers/reports.py`` reads agent_task_executions
    # joined to admin_knowledge_entries. The upsert above is sufficient.

    return PublicationResult(
        execution_id=execution_id,
        vault_document_id=vault_doc_id,
        workspace_event_emitted=workspace_emitted,
    )


# ---------------------------------------------------------------------------
# Layer-2 report renderer (spec §11)
# ---------------------------------------------------------------------------


async def render_report_markdown(
    *,
    contract: TaskContract,
    research: ResearchResult | None,
    audit: AuditReport | None,
    artifacts: list[Artifact],
    agent_id: AgentID | str,
) -> str:
    """Produce the structured markdown report for the knowledge vault.

    Follows the spec §11 template exactly (Goal, To-Do Outcomes,
    Success Criteria, Research Summary, Sources, Contradictions, Artifacts,
    Audit Report, Policy Notes, Follow-ups). Missing optional inputs are
    rendered as ``"_none_"`` placeholders rather than omitted so downstream
    semantic search has a stable field set to chunk against.
    """
    agent_id_str = _agent_id_str(agent_id)
    now_iso = datetime.now(timezone.utc).isoformat()
    lines: list[str] = []

    lines.append(f"# {agent_id_str} - {contract.goal}")
    init_part = (
        f"`{contract.initiative_id}`" if contract.initiative_id else "_(direct)_"
    )
    lines.append(
        f"**Initiative:** {init_part} - "
        f"**Phase:** {contract.initiative_phase or '-'} - "
        f"**Date:** {now_iso}"
    )
    lines.append(f"**Owner:** {agent_id_str} - **Task:** `{contract.id}`")
    lines.append("")

    lines.append("## Goal")
    lines.append(contract.goal)
    lines.append("")

    lines.append("## To-Do Outcomes")
    if contract.todo_items:
        lines.append("| Item | Status | Evidence |")
        lines.append("| --- | --- | --- |")
        for item in contract.todo_items:
            evidence_strs: list[str] = []
            for ev in item.evidence or []:
                if isinstance(ev, dict):
                    label = ev.get("ref") or ev.get("summary") or ev.get("kind") or ""
                    evidence_strs.append(str(label))
                else:
                    evidence_strs.append(str(ev))
            evidence = ", ".join(s for s in evidence_strs if s) or "-"
            lines.append(f"| {item.title} | {item.status} | {evidence} |")
    else:
        lines.append("_none_")
    lines.append("")

    lines.append("## Success Criteria")
    if contract.success_criteria:
        if audit is not None and audit.per_criterion:
            per_crit = {pc.criterion: pc for pc in audit.per_criterion}
            for crit in contract.success_criteria:
                pc = per_crit.get(crit)
                if pc is None:
                    lines.append(f"- {crit} (no audit verdict)")
                else:
                    verdict = "PASS" if pc.met else "FAIL"
                    lines.append(f"- {crit} - **{verdict}** - {pc.justification}")
        else:
            for crit in contract.success_criteria:
                lines.append(f"- {crit}")
    else:
        lines.append("_none declared_")
    lines.append("")

    lines.append("## Research Summary")
    if research is not None:
        lines.append(research.summary or "_(no summary)_")
    else:
        lines.append("_no research captured_")
    lines.append("")

    src_count = len(research.sources) if research is not None else 0
    lines.append(f"### Sources ({src_count})")
    if research is not None and research.sources:
        for src in research.sources:
            retrieved = src.retrieved_at
            if isinstance(retrieved, datetime):
                retrieved_str = retrieved.isoformat()
            else:
                retrieved_str = str(retrieved)
            lines.append(
                f"- [{src.title}]({src.url}) - {src.key_claim} (retrieved {retrieved_str})"
            )
    else:
        lines.append("_no sources_")
    lines.append("")

    lines.append("### Contradictions Flagged")
    if research is not None and research.contradictions:
        for c in research.contradictions:
            lines.append(f"- {c}")
    else:
        lines.append("_none_")
    lines.append("")

    lines.append("## Artifacts")
    if artifacts:
        for art in artifacts:
            lines.append(f"- **{art.kind}** - {art.summary} (`{art.ref}`)")
    else:
        lines.append("_no artifacts produced_")
    lines.append("")

    lines.append("## Audit Report")
    if audit is not None:
        lines.append(f"**Status:** {audit.overall_status}")
        lines.append(f"**Next action:** {audit.next_action}")
        if audit.gaps:
            lines.append("**Gaps:**")
            for g in audit.gaps:
                lines.append(f"- {g}")
    else:
        lines.append("_no audit recorded_")
    lines.append("")

    lines.append("## Policy Notes")
    if audit is not None and audit.policy_violations:
        for v in audit.policy_violations:
            target = f" ({v.tool_id})" if v.tool_id else ""
            lines.append(f"- **{v.kind}**{target}: {v.detail}")
    else:
        lines.append("_none_")
    lines.append("")

    lines.append("## Follow-ups")
    follow_ups: list[str] = []
    if research is not None:
        follow_ups.extend(f"Open: {m}" for m in research.missing_information)
    if audit is not None:
        follow_ups.extend(f"Audit gap: {g}" for g in audit.gaps)
    if follow_ups:
        for f in follow_ups:
            lines.append(f"- {f}")
    else:
        lines.append("_none_")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Render-complete helper (Tasks 102 / 103)
# ---------------------------------------------------------------------------


async def notify_render_complete(
    *,
    user_id: UUID,
    agent_id: AgentID | str,
    contract_id: UUID | None,
    ref: str,
    preview_url: str | None,
    summary: str,
    persona_id: str | None = None,
) -> PublicationResult:
    """Centralized hook for render-completion paths (director, vertex_video).

    Builds a ``video_render`` :class:`Artifact` and routes it through
    :func:`publish_artifact` so the workspace SSE channel receives the event
    and the vault picks up the asset for Layer-3 retrieval. Kept in
    publication.py (rather than each service) so the surgical patch in
    ``director_service`` / ``vertex_video_service`` is one import + one call.

    Falls back to a synthetic :class:`DirectRequest` envelope when no
    contract id is supplied (e.g. ad-hoc generation outside an initiative).
    """
    artifact = Artifact(
        kind="video_render",
        ref=ref,
        summary=summary,
        payload={"preview_url": preview_url},
    )
    contract: TaskContract | DirectRequest
    if contract_id is not None:
        # Minimal contract envelope: the row may already exist from the
        # agent's submit; the upsert merges on contract_id. We deliberately
        # leave goal/todos blank — the surgical fix is just to inform the
        # workspace and vault of the new asset; the agent owns the contract.
        contract = TaskContract(
            id=contract_id,
            source="initiative_step",
            goal=summary,
            todo_items=[],
            success_criteria=[],
            owners=[],
            evidence_required=[],
            initiative_id=None,
            initiative_phase=None,
            sibling_steps=[],
        )
    else:
        # ``DirectRequest.agent_id`` is annotated as ``AgentID`` but the
        # dataclass does not enforce that at runtime; passing the string form
        # is fine for the synthetic envelope we build here and matches what
        # render-pipeline callers actually have on hand.
        contract = DirectRequest(
            user_id=user_id,
            agent_id=_agent_id_str(agent_id),  # type: ignore[arg-type]
            persona_id=persona_id or "default",
            message=summary,
            session_id=None,
        )

    return await publish_artifact(
        user_id=user_id,
        agent_id=agent_id,
        contract=contract,
        artifact=artifact,
        audit=None,
    )


__all__ = [
    "VAULT_BOUND_KINDS",
    "PublicationResult",
    "emit_progress_event",
    "notify_render_complete",
    "publish_artifact",
    "render_report_markdown",
]
