"""Workflow template validation helpers.

Pure validation utilities are split from ``engine.py`` to keep the runtime
orchestrator focused on persistence and execution.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from app.workflows.execution_contracts import validate_step_contract

DEPRECATED_WORKFLOW_TOOLS = {"sent_contract"}


def validate_template_phases(
    phases: list[dict[str, Any]],
    known_tools: set[str],
    *,
    strict_user_visible: bool = False,
    tool_registry: Mapping[str, Callable[..., Any]] | None = None,
) -> list[str]:
    """Validate phase/step schema and tool references for a single template."""
    errors: list[str] = []
    if not isinstance(phases, list) or not phases:
        return ["phases must be a non-empty list"]

    for p_idx, phase in enumerate(phases):
        if not isinstance(phase, dict):
            errors.append(f"phase[{p_idx}] must be an object")
            continue
        phase_name = phase.get("name")
        if not isinstance(phase_name, str) or not phase_name.strip():
            errors.append(f"phase[{p_idx}] missing non-empty name")
        steps = phase.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append(f"phase[{p_idx}] must have non-empty steps list")
            continue

        for s_idx, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"phase[{p_idx}].steps[{s_idx}] must be an object")
                continue
            step_name = step.get("name")
            tool = step.get("tool") or step.get("action_type")
            if not isinstance(step_name, str) or not step_name.strip():
                errors.append(f"phase[{p_idx}].steps[{s_idx}] missing non-empty name")
            if not isinstance(tool, str) or not tool.strip():
                errors.append(f"phase[{p_idx}].steps[{s_idx}] missing non-empty tool")
                continue
            if tool in DEPRECATED_WORKFLOW_TOOLS:
                errors.append(
                    f"phase[{p_idx}].steps[{s_idx}] uses deprecated tool '{tool}'"
                )
            if tool not in known_tools:
                errors.append(f"phase[{p_idx}].steps[{s_idx}] unresolved tool '{tool}'")

            if strict_user_visible:
                contract_errors = validate_step_contract(
                    step,
                    tool_name=tool,
                    user_visible=True,
                    tool_registry=tool_registry,
                )
                for contract_error in contract_errors:
                    errors.append(f"phase[{p_idx}].steps[{s_idx}] {contract_error}")

    return errors
