"""Shared initiative operational-state helpers."""

from __future__ import annotations

from typing import Any, Optional

OPERATIONAL_STATE_KEY = "operational_state"


def ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def default_trust_summary() -> dict[str, Any]:
    return {
        "trust_counts": {},
        "verification_counts": {},
        "approval_state": "not_required",
        "verification_status": "not_started",
        "last_failure_reason": None,
    }


def normalize_operational_state(
    initiative: dict[str, Any],
    *,
    metadata_override: Optional[dict[str, Any]] = None,
    workflow_execution_id: Optional[str] = None,
) -> dict[str, Any]:
    initiative_copy = dict(initiative or {})
    metadata = metadata_override if metadata_override is not None else initiative_copy.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    op = metadata.get(OPERATIONAL_STATE_KEY)
    if not isinstance(op, dict):
        op = {}

    trust_summary = op.get("trust_summary")
    if not isinstance(trust_summary, dict):
        trust_summary = default_trust_summary()
    else:
        trust_summary = {**default_trust_summary(), **trust_summary}

    normalized = {
        "goal": op.get("goal") or metadata.get("goal") or initiative_copy.get("description") or initiative_copy.get("title") or "",
        "success_criteria": ensure_list(op.get("success_criteria") or metadata.get("success_criteria")),
        "owner_agents": ensure_list(op.get("owner_agents") or metadata.get("owner_agents")),
        "primary_workflow": op.get("primary_workflow") or metadata.get("workflow_template_name") or metadata.get("primary_workflow"),
        "deliverables": ensure_list(op.get("deliverables") or metadata.get("deliverables")),
        "evidence": ensure_list(op.get("evidence") or metadata.get("evidence")),
        "blockers": ensure_list(op.get("blockers") or metadata.get("blockers")),
        "next_actions": ensure_list(op.get("next_actions") or metadata.get("next_actions")),
        "current_phase": op.get("current_phase") or initiative_copy.get("phase") or metadata.get("current_phase") or "ideation",
        "verification_status": op.get("verification_status") or metadata.get("verification_status") or "not_started",
        "trust_summary": trust_summary,
        "workflow_execution_id": workflow_execution_id or op.get("workflow_execution_id") or initiative_copy.get("workflow_execution_id"),
    }
    metadata[OPERATIONAL_STATE_KEY] = normalized
    initiative_copy["metadata"] = metadata
    for key in (
        "goal",
        "success_criteria",
        "owner_agents",
        "primary_workflow",
        "deliverables",
        "evidence",
        "blockers",
        "next_actions",
        "verification_status",
        "trust_summary",
        "workflow_execution_id",
    ):
        initiative_copy[key] = normalized.get(key)
    initiative_copy["current_phase"] = normalized.get("current_phase")
    return initiative_copy
