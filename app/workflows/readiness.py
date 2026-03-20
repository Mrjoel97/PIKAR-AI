"""Workflow readiness preflight reporting utilities.

This module builds a runtime report across workflow templates and tool mappings
to highlight whether workflows are ready for real-user execution.
"""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from typing import Any

from app.agents.tools.registry import TOOL_REGISTRY
from app.services.supabase import get_service_client
from app.workflows.execution_contracts import classify_tool
from app.workflows.template_validation import validate_template_phases


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def classify_workflow(phases: list[dict[str, Any]]) -> tuple[str, Counter, int]:
    """Classify a workflow from phases/steps."""
    required_approval_steps = 0
    kinds: Counter = Counter()

    for phase in phases or []:
        for step in phase.get("steps", []) or []:
            if step.get("required_approval"):
                required_approval_steps += 1
            tool_name = step.get("tool") or step.get("action_type")
            if not tool_name:
                continue
            kinds[classify_tool(tool_name, tool_registry=TOOL_REGISTRY)] += 1

    if required_approval_steps > 0:
        label = "human-gated"
    elif kinds["degraded"] > 0 or kinds["placeholder"] > 0 or kinds["missing"] > 0:
        label = "degraded-simulation-prone"
    elif kinds["integration"] > 0 or kinds["high_risk"] > 0:
        label = "integration-dependent"
    else:
        label = "fully autonomous"

    return label, kinds, required_approval_steps


def build_workflow_readiness_report() -> dict[str, Any]:
    """Build readiness report using current DB templates and registry mappings."""
    client = get_service_client()
    response = (
        client.table("workflow_templates")
        .select("id, name, phases, lifecycle_status")
        .execute()
    )
    templates = response.data or []

    readiness_rows: list[dict[str, Any]] = []
    readiness_error: str | None = None
    try:
        readiness_res = (
            client.table("workflow_readiness")
            .select(
                "template_id, template_name, template_version, status, required_integrations, "
                "requires_human_gate, readiness_owner, reason_codes, notes, updated_at"
            )
            .execute()
        )
        readiness_rows = readiness_res.data or []
    except Exception as exc:
        readiness_error = str(exc)

    status_counts: Counter = Counter()
    tool_kind_counts: Counter = Counter()
    workflow_label_counts: Counter = Counter()
    label_workflows: dict[str, list[str]] = defaultdict(list)
    unknown_tool_workflows: dict[str, list[str]] = defaultdict(list)
    placeholder_tool_workflows: dict[str, list[str]] = defaultdict(list)
    degraded_tool_workflows: dict[str, list[str]] = defaultdict(list)
    strict_contract_workflows: list[dict[str, Any]] = []
    readiness_by_template_id = {
        row.get("template_id"): row for row in readiness_rows if row.get("template_id")
    }

    total_steps = 0
    total_required_approval_steps = 0
    workflow_labels_by_template_id: dict[str, str] = {}
    integration_metadata_gaps: list[dict[str, Any]] = []

    for template in templates:
        name = template.get("name", "Unknown Workflow")
        template_id = template.get("id")
        phases = template.get("phases") or []
        lifecycle_status = template.get("lifecycle_status") or "legacy"

        status_counts[lifecycle_status] += 1

        label, _kinds, approval_steps = classify_workflow(phases)
        workflow_label_counts[label] += 1
        label_workflows[label].append(name)
        if template_id:
            workflow_labels_by_template_id[template_id] = label
        total_required_approval_steps += approval_steps

        if str(lifecycle_status).lower() == "published":
            contract_errors = validate_template_phases(
                phases,
                set(TOOL_REGISTRY.keys()),
                strict_user_visible=True,
                tool_registry=TOOL_REGISTRY,
            )
            if contract_errors:
                strict_contract_workflows.append(
                    {
                        "template_id": template_id,
                        "template_name": name,
                        "errors": contract_errors[:20],
                    }
                )

        for phase in phases:
            for step in phase.get("steps", []) or []:
                tool_name = step.get("tool") or step.get("action_type")
                if not tool_name:
                    continue
                total_steps += 1
                tool_kind = classify_tool(tool_name, tool_registry=TOOL_REGISTRY)
                tool_kind_counts[tool_kind] += 1
                if tool_kind == "missing":
                    unknown_tool_workflows[tool_name].append(name)
                elif tool_kind == "placeholder":
                    placeholder_tool_workflows[tool_name].append(name)
                elif (
                    tool_kind == "degraded"
                    and str(lifecycle_status).lower() == "published"
                ):
                    degraded_tool_workflows[tool_name].append(name)

    readiness_status_counts: Counter = Counter()
    missing_readiness_templates: list[str] = []
    for template in templates:
        template_id = template.get("id")
        template_name = template.get("name", "Unknown Workflow")
        row = readiness_by_template_id.get(template_id)
        if not row:
            missing_readiness_templates.append(template_name)
            continue
        readiness_status_counts[row.get("status") or "unknown"] += 1
        if workflow_labels_by_template_id.get(template_id) == "integration-dependent":
            required_integrations = row.get("required_integrations")
            if not isinstance(required_integrations, list):
                integration_metadata_gaps.append(
                    {
                        "template_id": template_id,
                        "template_name": template_name,
                        "reason": "required_integrations_not_list",
                        "value_type": type(required_integrations).__name__,
                    }
                )
            else:
                normalized = [
                    str(v).strip() for v in required_integrations if str(v).strip()
                ]
                if not normalized:
                    integration_metadata_gaps.append(
                        {
                            "template_id": template_id,
                            "template_name": template_name,
                            "reason": "required_integrations_empty",
                        }
                    )

    strict_tool_resolution = _as_bool(
        os.getenv("WORKFLOW_STRICT_TOOL_RESOLUTION"), default=False
    )
    allow_fallback_simulation = _as_bool(
        os.getenv("WORKFLOW_ALLOW_FALLBACK_SIMULATION"), default=True
    )
    strict_critical_guard = _as_bool(
        os.getenv("WORKFLOW_STRICT_CRITICAL_TOOL_GUARD"), default=False
    )
    enforce_readiness_gate = _as_bool(
        os.getenv("WORKFLOW_ENFORCE_READINESS_GATE"), default=False
    )
    backend_api_url_set = bool((os.getenv("BACKEND_API_URL") or "").strip())
    service_secret_set = bool((os.getenv("WORKFLOW_SERVICE_SECRET") or "").strip())

    checks = {
        "strict_tool_resolution_enabled": strict_tool_resolution,
        "strict_critical_tool_guard_enabled": strict_critical_guard,
        "readiness_gate_enabled": enforce_readiness_gate,
        "fallback_simulation_disabled": not allow_fallback_simulation,
        "backend_api_url_configured": backend_api_url_set,
        "workflow_service_secret_configured": service_secret_set,
        "workflow_readiness_table_accessible": readiness_error is None,
        "all_templates_have_readiness_rows": len(missing_readiness_templates) == 0,
        "integration_workflows_have_required_integrations_metadata": len(
            integration_metadata_gaps
        )
        == 0,
        "no_unknown_tools_in_templates": len(unknown_tool_workflows) == 0,
        "no_placeholder_tools_in_templates": len(placeholder_tool_workflows) == 0,
        "no_degraded_tools_in_published_templates": len(degraded_tool_workflows) == 0,
        "user_visible_templates_have_strict_step_contracts": len(
            strict_contract_workflows
        )
        == 0,
    }

    failing_checks = [name for name, passed in checks.items() if not passed]
    readiness_status = "ready" if not failing_checks else "not_ready"

    return {
        "status": readiness_status,
        "summary": {
            "templates_total": len(templates),
            "steps_total": total_steps,
            "required_approval_steps": total_required_approval_steps,
        },
        "template_lifecycle": dict(status_counts),
        "workflow_labels": dict(workflow_label_counts),
        "workflow_names_by_label": {k: sorted(v) for k, v in label_workflows.items()},
        "workflow_readiness": {
            "status_counts": dict(readiness_status_counts),
            "rows_total": len(readiness_rows),
            "missing_templates": sorted(missing_readiness_templates),
            "integration_required_integrations_gaps": sorted(
                integration_metadata_gaps,
                key=lambda row: (
                    str(row.get("template_name") or ""),
                    str(row.get("template_id") or ""),
                ),
            ),
            "strict_contract_gaps": sorted(
                strict_contract_workflows,
                key=lambda row: (
                    str(row.get("template_name") or ""),
                    str(row.get("template_id") or ""),
                ),
            ),
            "table_error": readiness_error,
        },
        "tool_kinds": dict(tool_kind_counts),
        "checks": checks,
        "failing_checks": sorted(failing_checks),
        "unknown_tool_workflows": {
            k: sorted(set(v)) for k, v in unknown_tool_workflows.items()
        },
        "placeholder_tool_workflows": {
            k: sorted(set(v)) for k, v in placeholder_tool_workflows.items()
        },
        "degraded_tool_workflows": {
            k: sorted(set(v)) for k, v in degraded_tool_workflows.items()
        },
    }
