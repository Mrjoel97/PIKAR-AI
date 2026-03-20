"""Workflow execution contract helpers.

These helpers keep template validation, runtime binding, trust labeling, and
verification logic aligned for strict user-visible workflow execution.
"""

from __future__ import annotations

import inspect
import os
from collections.abc import Callable, Mapping
from typing import Any

from pydantic import BaseModel, ValidationError

USER_VISIBLE_RUN_SOURCES = {"user_ui", "agent_ui"}
STRICT_APPROVAL_RISK_LEVELS = {
    "publish",
    "spend",
    "legal",
    "contract",
    "payroll",
    "hr_sensitive",
    "customer_outbound",
}
VALID_RISK_LEVELS = {
    "low",
    "medium",
    "high",
    "publish",
    "spend",
    "legal",
    "contract",
    "payroll",
    "hr_sensitive",
    "customer_outbound",
}


class WorkflowContractError(RuntimeError):
    """Structured workflow execution contract failure."""

    def __init__(
        self,
        message: str,
        *,
        reason_code: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": str(self),
            "reason_code": self.reason_code,
            "details": self.details,
        }


def is_user_visible_run_source(run_source: str) -> bool:
    """Whether a run source is user-visible and must be strictly truthful."""
    return (run_source or "").strip().lower() in USER_VISIBLE_RUN_SOURCES


def is_production_execution_environment() -> bool:
    """Whether workflow execution should enforce production truthfulness rules."""
    env = (
        (os.environ.get("ENVIRONMENT") or os.environ.get("ENV") or "development")
        .strip()
        .lower()
    )
    return env in {"production", "prod"}


def classify_tool(
    tool_name: str,
    *,
    tool_registry: Mapping[str, Callable[..., Any]] | None = None,
) -> str:
    """Classify a tool by implementation style for trust reporting."""
    from app.agents.tools.registry import TOOL_REGISTRY, placeholder_tool

    registry = tool_registry or TOOL_REGISTRY
    if tool_name not in registry:
        return "missing"

    tool_fn = registry[tool_name]
    if tool_fn is placeholder_tool:
        return "placeholder"

    fn_name = getattr(tool_fn, "__name__", "")
    fn_module = getattr(tool_fn, "__module__", "")

    if fn_name.startswith("alias_"):
        return "alias"
    if "degraded_tools" in fn_module:
        return "degraded"
    if "integration_tools" in fn_module:
        return "integration"
    if "high_risk_workflow" in fn_module:
        return "high_risk"
    return "direct"


def requires_approval(step_definition: Mapping[str, Any] | None) -> bool:
    """Infer whether a step requires explicit user approval."""
    if not isinstance(step_definition, Mapping):
        return False
    if bool(step_definition.get("required_approval")):
        return True
    risk_level = str(step_definition.get("risk_level") or "").strip().lower()
    return risk_level in STRICT_APPROVAL_RISK_LEVELS


def determine_trust_class(
    tool_name: str,
    *,
    step_definition: Mapping[str, Any] | None = None,
    tool_registry: Mapping[str, Callable[..., Any]] | None = None,
) -> str:
    """Return the user-facing trust class for a step."""
    tool_kind = classify_tool(tool_name, tool_registry=tool_registry)
    if requires_approval(step_definition):
        return "human_gated"
    if tool_kind in {"degraded", "placeholder", "missing"}:
        return "degraded"
    if tool_kind in {"integration", "high_risk"}:
        return "integration_dependent"
    return "real"


def _normalize_binding_map(step_definition: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(step_definition, Mapping):
        return {}
    input_bindings = step_definition.get("input_bindings")
    if not isinstance(input_bindings, Mapping):
        return {}
    return dict(input_bindings)


def _resolve_path(source: Any, path: str) -> Any:
    normalized = (path or "").strip()
    if not normalized:
        return None

    for prefix in ("$.", "context.", "output."):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break

    value = source
    for part in normalized.split("."):
        if part == "":
            continue
        if isinstance(value, Mapping):
            value = value.get(part)
            continue
        if isinstance(value, list) and part.isdigit():
            index = int(part)
            if 0 <= index < len(value):
                value = value[index]
                continue
        return None
    return value


def _resolve_binding_value(binding: Any, context: Mapping[str, Any]) -> Any:
    if isinstance(binding, str):
        return _resolve_path(context, binding)
    if not isinstance(binding, Mapping):
        return binding
    if "value" in binding:
        return binding.get("value")
    if "path" in binding:
        return _resolve_path(context, str(binding.get("path") or ""))
    if "default" in binding:
        return binding.get("default")
    return binding


def _build_payload_from_bindings(
    *,
    input_bindings: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field_name, binding in input_bindings.items():
        payload[field_name] = _resolve_binding_value(binding, context)
    return payload


def _build_payload_from_signature(
    *,
    tool_fn: Callable[..., Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    signature = inspect.signature(tool_fn)
    payload: dict[str, Any] = {}
    for name, param in signature.parameters.items():
        if name == "self":
            continue
        if param.kind in (inspect.Parameter.VAR_POSITIONAL,):
            continue
        if name in context:
            payload[name] = context[name]
    return payload


def _required_parameter_names(tool_fn: Callable[..., Any]) -> list[str]:
    signature = inspect.signature(tool_fn)
    required: list[str] = []
    for name, param in signature.parameters.items():
        if name == "self":
            continue
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        if param.default is inspect._empty:
            required.append(name)
    return required


def build_tool_kwargs(
    tool_fn: Callable[..., Any],
    tool_name: str,
    context: Mapping[str, Any] | None,
    *,
    step_name: str = "",
    step_description: str = "",
    step_definition: Mapping[str, Any] | None = None,
    run_source: str = "user_ui",
    tool_registry: Mapping[str, Callable[..., Any]] | None = None,
) -> dict[str, Any]:
    """Build validated kwargs for a workflow tool call."""
    ctx = dict(context or {})
    user_visible = is_user_visible_run_source(run_source)
    strict_truth_enforced = user_visible or is_production_execution_environment()
    execution_scope = (
        "user-visible execution" if user_visible else "production execution"
    )
    tool_kind = classify_tool(tool_name, tool_registry=tool_registry)

    if strict_truth_enforced and tool_kind == "missing":
        raise WorkflowContractError(
            f"Workflow step '{step_name or tool_name}' references unknown tool '{tool_name}'.",
            reason_code="unknown_tool",
        )
    if strict_truth_enforced and tool_kind == "placeholder":
        raise WorkflowContractError(
            f"Workflow step '{step_name or tool_name}' uses placeholder tool '{tool_name}', which is blocked for {execution_scope}.",
            reason_code="unknown_tool",
        )
    if strict_truth_enforced and tool_kind == "degraded":
        raise WorkflowContractError(
            f"Workflow step '{step_name or tool_name}' uses degraded tool '{tool_name}', which is blocked for {execution_scope}.",
            reason_code="degraded_tool_not_allowed",
        )

    input_bindings = _normalize_binding_map(step_definition)
    input_schema: type[BaseModel] | None = getattr(tool_fn, "input_schema", None)

    if user_visible and not input_bindings:
        raise WorkflowContractError(
            f"Workflow step '{step_name or tool_name}' is missing input bindings.",
            reason_code="missing_input_bindings",
            details={"tool": tool_name, "step_description": step_description},
        )

    if user_visible and input_schema is None:
        raise WorkflowContractError(
            f"Workflow step '{step_name or tool_name}' cannot execute without a typed input schema.",
            reason_code="missing_schema",
            details={"tool": tool_name},
        )

    if input_bindings:
        raw_payload = _build_payload_from_bindings(
            input_bindings=input_bindings, context=ctx
        )
    elif input_schema is not None:
        raw_payload = {
            field_name: ctx.get(field_name)
            for field_name in input_schema.model_fields.keys()
            if field_name in ctx
        }
    else:
        raw_payload = _build_payload_from_signature(tool_fn=tool_fn, context=ctx)

    if input_schema is not None:
        try:
            validated = input_schema(**raw_payload)
        except ValidationError as exc:
            raise WorkflowContractError(
                f"Workflow step '{step_name or tool_name}' failed input validation.",
                reason_code="schema_validation_failed",
                details={"errors": exc.errors(), "tool": tool_name},
            ) from exc
        return validated.model_dump(exclude_none=True)

    required_params = _required_parameter_names(tool_fn)
    missing_params = [name for name in required_params if raw_payload.get(name) is None]
    if missing_params:
        raise WorkflowContractError(
            f"Workflow step '{step_name or tool_name}' is missing required inputs: {', '.join(missing_params)}.",
            reason_code="missing_required_input",
            details={"missing_inputs": missing_params, "tool": tool_name},
        )
    return {k: v for k, v in raw_payload.items() if v is not None}


def extract_evidence_refs(output: Any) -> list[Any]:
    """Extract evidence-like references from a tool result."""
    if not isinstance(output, Mapping):
        return []

    evidence_refs = output.get("evidence_refs")
    if isinstance(evidence_refs, list):
        return evidence_refs

    evidence: list[Any] = []
    if "evidence" in output and output.get("evidence") is not None:
        evidence.append(output.get("evidence"))

    key_map = {
        "url": "url",
        "page_url": "url",
        "live_url": "url",
        "page_id": "page",
        "invoice_id": "invoice",
        "report_id": "report",
        "task_id": "task",
        "campaign_id": "campaign",
        "initiative_id": "initiative",
        "ticket_id": "ticket",
        "execution_id": "workflow_execution",
    }
    for key, evidence_type in key_map.items():
        value = output.get(key)
        if value:
            evidence.append({"type": evidence_type, "key": key, "value": value})

    urls = output.get("urls")
    if isinstance(urls, list):
        evidence.extend(
            {"type": "url", "key": "urls", "value": url} for url in urls if url
        )

    return evidence


def verify_step_output(
    output: Any,
    *,
    step_definition: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run simple verification checks against a step output."""
    if not isinstance(step_definition, Mapping):
        return {"status": "skipped", "errors": []}

    errors: list[str] = []
    expected_outputs = step_definition.get("expected_outputs") or []
    verification_checks = step_definition.get("verification_checks") or []

    if isinstance(output, Mapping):
        if output.get("success") is False:
            errors.append("tool reported success=false")
        status = str(output.get("status") or "").strip().lower()
        if status in {"failed", "error"}:
            errors.append(f"tool reported status={status}")
    elif output is None:
        errors.append("tool returned no output")

    if isinstance(expected_outputs, list):
        for expected in expected_outputs:
            if not isinstance(expected, str) or not expected.strip():
                continue
            if _resolve_path(output, expected) is None:
                errors.append(f"missing expected output '{expected}'")

    if isinstance(verification_checks, list):
        for check in verification_checks:
            if check == "success":
                if isinstance(output, Mapping) and output.get("success") is False:
                    errors.append("verification check 'success' failed")
                continue
            if not isinstance(check, Mapping):
                continue
            check_type = str(check.get("type") or "").strip().lower()
            if check_type == "require_output_keys":
                for key in check.get("keys") or []:
                    if _resolve_path(output, str(key)) is None:
                        errors.append(f"verification missing output key '{key}'")
            elif check_type == "output_field_truthy":
                field_name = str(check.get("field") or "").strip()
                if field_name and not _resolve_path(output, field_name):
                    errors.append(f"verification expected truthy field '{field_name}'")

    if errors:
        return {"status": "failed", "errors": errors}
    if expected_outputs or verification_checks:
        return {"status": "verified", "errors": []}
    return {"status": "skipped", "errors": []}


def validate_step_contract(
    step: Mapping[str, Any],
    *,
    tool_name: str,
    user_visible: bool,
    tool_registry: Mapping[str, Callable[..., Any]] | None = None,
) -> list[str]:
    """Validate strict step metadata and tool constraints."""
    errors: list[str] = []
    input_bindings = step.get("input_bindings")
    risk_level = step.get("risk_level")
    required_integrations = step.get("required_integrations")
    verification_checks = step.get("verification_checks")
    expected_outputs = step.get("expected_outputs")
    allow_parallel = step.get("allow_parallel")

    if not isinstance(input_bindings, Mapping) or not input_bindings:
        errors.append("missing non-empty input_bindings")

    if (
        not isinstance(risk_level, str)
        or risk_level.strip().lower() not in VALID_RISK_LEVELS
    ):
        errors.append("missing valid risk_level")

    if not isinstance(required_integrations, list):
        errors.append("missing required_integrations list")

    if not isinstance(verification_checks, list):
        errors.append("missing verification_checks list")

    if not isinstance(expected_outputs, list) or not expected_outputs:
        errors.append("missing non-empty expected_outputs list")

    if not isinstance(allow_parallel, bool):
        errors.append("missing boolean allow_parallel")

    if user_visible:
        from app.agents.tools.registry import TOOL_REGISTRY

        registry = tool_registry or TOOL_REGISTRY
        tool_kind = classify_tool(tool_name, tool_registry=registry)
        tool_fn = registry.get(tool_name)
        input_schema = getattr(tool_fn, "input_schema", None) if tool_fn else None

        if tool_kind == "missing":
            errors.append(f"unresolved tool '{tool_name}'")
        elif tool_kind == "placeholder":
            errors.append(
                f"placeholder tool '{tool_name}' is not allowed for user-visible execution"
            )
        elif tool_kind == "degraded":
            errors.append(
                f"degraded tool '{tool_name}' is not allowed for user-visible execution"
            )
        if input_schema is None:
            errors.append(f"tool '{tool_name}' is missing typed input schema")
        if str(
            risk_level or ""
        ).strip().lower() in STRICT_APPROVAL_RISK_LEVELS and not bool(
            step.get("required_approval")
        ):
            errors.append(
                f"risk level '{risk_level}' requires required_approval=true for user-visible execution"
            )
        if (
            tool_kind in {"integration", "high_risk"}
            and isinstance(required_integrations, list)
            and not required_integrations
        ):
            errors.append(
                f"tool '{tool_name}' requires non-empty required_integrations"
            )

    return errors
