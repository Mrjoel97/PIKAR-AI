"""Helpers for turning loose workflow drafts into executable step contracts."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any, Callable, Mapping, Optional

from pydantic import BaseModel

from app.workflows.execution_contracts import (
    STRICT_APPROVAL_RISK_LEVELS,
    VALID_RISK_LEVELS,
    classify_tool,
)

SAFE_WORKFLOW_TOOL_ORDER = [
    "create_task",
    "mcp_web_search",
    "mcp_web_scrape",
    "create_initiative",
    "create_campaign",
    "track_event",
    "create_report",
    "save_content",
    "update_content",
    "quick_research",
    "deep_research",
    "market_research",
    "competitor_research",
    "add_business_knowledge",
    "list_initiatives",
    "update_initiative",
    "query_events",
    "get_revenue_stats",
    "record_campaign_metrics",
    "manage_comments",
    "generate_image",
    "mcp_generate_landing_page",
    "create_landing_page",
    "publish_page",
]

PARALLEL_FRIENDLY_TOOLS = {
    "mcp_web_search",
    "mcp_web_scrape",
    "track_event",
    "quick_research",
    "market_research",
    "competitor_research",
    "query_events",
    "list_initiatives",
    "get_revenue_stats",
}

TOOL_EXPECTED_OUTPUTS: dict[str, list[str]] = {
    "create_task": ["task.id"],
    "mcp_web_search": ["results"],
    "mcp_web_scrape": ["results"],
    "create_initiative": ["initiative.id"],
    "create_campaign": ["campaign.id"],
    "track_event": ["event.id"],
    "create_report": ["report.id"],
    "save_content": ["success"],
    "update_content": ["success"],
    "quick_research": ["results"],
    "deep_research": ["results"],
    "market_research": ["results"],
    "competitor_research": ["results"],
    "add_business_knowledge": ["success"],
    "list_initiatives": ["success"],
    "update_initiative": ["success"],
    "query_events": ["success"],
    "get_revenue_stats": ["success"],
    "record_campaign_metrics": ["success"],
    "manage_comments": ["success"],
    "generate_image": ["success"],
    "mcp_generate_landing_page": ["html"],
    "create_landing_page": ["page_id", "url"],
    "publish_page": ["url"],
}

TOOL_REQUIRED_INTEGRATIONS: dict[str, list[str]] = {}


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", (value or "").strip().lower())
    return normalized.strip("_") or "workflow_event"


def _schema_field_names(input_schema: type[BaseModel] | None) -> list[str]:
    if input_schema is None:
        return []
    return list(getattr(input_schema, "model_fields", {}).keys())


def _required_schema_fields(input_schema: type[BaseModel] | None) -> list[str]:
    if input_schema is None:
        return []

    required: list[str] = []
    for field_name, field_info in getattr(input_schema, "model_fields", {}).items():
        is_required = getattr(field_info, "is_required", None)
        if callable(is_required):
            if is_required():
                required.append(field_name)
            continue
        if getattr(field_info, "default", None) is ...:
            required.append(field_name)
    return required


def _value_binding(value: Any) -> dict[str, Any]:
    return {"value": value}


def _default_binding_for_field(
    field_name: str,
    *,
    tool_name: str,
    step_name: str,
    step_description: str,
    template_name: str,
    category: str,
    persona: str | None,
    goal: str,
) -> Any:
    topic_fallback = goal or step_description or step_name or template_name or "workflow goal"
    report_title = f"{template_name or step_name or 'Workflow'} - {step_name or 'Summary'}"

    shared_defaults: dict[str, Any] = {
        "user_id": "user_id",
        "topic": "topic",
        "query": "topic",
        "page_id": "page_id",
        "html_content": "html",
        "title": _value_binding(step_name or template_name or topic_fallback),
        "name": _value_binding(step_name or template_name or topic_fallback),
        "description": _value_binding(step_description or topic_fallback),
        "priority": _value_binding("medium"),
        "category": _value_binding(category or "operations"),
        "report_type": _value_binding((category or "operations").lower()),
        "data": _value_binding("{}"),
        "event_name": _value_binding(_slugify(step_name or template_name or "workflow_event")),
        "properties": _value_binding(json.dumps({"source": "workflow", "step": step_name or template_name or "workflow"})),
        "campaign_type": _value_binding((category or "custom").lower()),
        "target_audience": _value_binding((persona or "general_audience").replace(" ", "_")),
        "headline": "topic",
        "subheadline": _value_binding(step_description or goal or template_name or "Get started"),
        "style": _value_binding("modern"),
        "include_form": _value_binding(True),
        "cta_text": _value_binding("Get Started"),
        "publish": _value_binding(False),
    }

    tool_specific_defaults: dict[str, dict[str, Any]] = {
        "create_task": {
            "description": _value_binding(step_description or f"Complete workflow step: {step_name or template_name}"),
        },
        "mcp_web_search": {
            "query": _value_binding(step_description or goal or step_name or template_name or "business research"),
        },
        "mcp_web_scrape": {
            "url": "url",
        },
        "create_initiative": {
            "title": _value_binding(goal or step_name or template_name or "New initiative"),
            "description": _value_binding(step_description or goal or "Workflow-generated initiative"),
        },
        "create_campaign": {
            "name": _value_binding(step_name or template_name or "Workflow Campaign"),
            "campaign_type": _value_binding((category or "custom").lower()),
            "target_audience": _value_binding(persona or "business_users"),
        },
        "track_event": {
            "event_name": _value_binding(_slugify(step_name or template_name or "workflow_event")),
            "category": _value_binding(category or "operations"),
        },
        "create_report": {
            "title": _value_binding(report_title),
            "report_type": _value_binding((category or "operations").lower()),
            "data": _value_binding("{}"),
            "description": _value_binding(step_description or goal or step_name or template_name),
        },
        "save_content": {
            "title": _value_binding(step_name or template_name or topic_fallback),
            "content": _value_binding(step_description or goal or topic_fallback),
        },
        "update_content": {
            "content_id": "content_id",
            "title": _value_binding(step_name or template_name or topic_fallback),
            "content": _value_binding(step_description or goal or topic_fallback),
        },
        "quick_research": {
            "topic": _value_binding(step_description or goal or step_name or template_name or "business research"),
        },
        "deep_research": {
            "topic": _value_binding(step_description or goal or step_name or template_name or "business research"),
        },
        "market_research": {
            "topic": _value_binding(step_description or goal or step_name or template_name or "market analysis"),
        },
        "competitor_research": {
            "topic": _value_binding(step_description or goal or step_name or template_name or "competitor analysis"),
        },
        "add_business_knowledge": {
            "content": _value_binding(step_description or goal or topic_fallback),
            "title": _value_binding(step_name or template_name or topic_fallback),
        },
        "list_initiatives": {},
        "update_initiative": {
            "initiative_id": "initiative_id",
        },
        "query_events": {},
        "get_revenue_stats": {},
        "record_campaign_metrics": {
            "campaign_id": "campaign_id",
        },
        "manage_comments": {
            "platform": _value_binding("social"),
            "action": _value_binding("reply"),
        },
        "generate_image": {
            "prompt": _value_binding(step_description or goal or step_name or template_name or "business image"),
        },
        "mcp_generate_landing_page": {
            "title": _value_binding(goal or template_name or step_name or "Landing Page"),
            "description": _value_binding(step_description or goal or "Launch-ready landing page"),
            "headline": _value_binding(goal or step_name or template_name or "Grow your business"),
            "subheadline": _value_binding(step_description or "Turn interest into action"),
        },
        "create_landing_page": {
            "user_id": "user_id",
            "title": _value_binding(goal or template_name or step_name or "Landing Page"),
            "html_content": "html",
        },
        "publish_page": {
            "user_id": "user_id",
            "page_id": "page_id",
        },
    }

    specific = tool_specific_defaults.get(tool_name, {})
    if field_name in specific:
        return specific[field_name]
    if field_name in shared_defaults:
        return shared_defaults[field_name]
    return _value_binding(step_description or topic_fallback)


def _build_input_bindings(
    *,
    tool_name: str,
    step_name: str,
    step_description: str,
    template_name: str,
    category: str,
    persona: str | None,
    goal: str,
    input_schema: type[BaseModel] | None,
    existing_bindings: Mapping[str, Any] | None,
) -> dict[str, Any]:
    field_names = _schema_field_names(input_schema)
    required_fields = _required_schema_fields(input_schema)
    bindings: dict[str, Any] = {}

    if isinstance(existing_bindings, Mapping):
        if field_names:
            bindings.update({name: value for name, value in existing_bindings.items() if name in field_names})
        else:
            bindings.update(dict(existing_bindings))

    for field_name in required_fields:
        if field_name not in bindings:
            bindings[field_name] = _default_binding_for_field(
                field_name,
                tool_name=tool_name,
                step_name=step_name,
                step_description=step_description,
                template_name=template_name,
                category=category,
                persona=persona,
                goal=goal,
            )

    if not bindings and field_names:
        primary_field = field_names[0]
        bindings[primary_field] = _default_binding_for_field(
            primary_field,
            tool_name=tool_name,
            step_name=step_name,
            step_description=step_description,
            template_name=template_name,
            category=category,
            persona=persona,
            goal=goal,
        )

    return bindings


def _default_risk_level(tool_name: str, *, required_approval: bool) -> str:
    if tool_name == "publish_page":
        return "publish"
    if required_approval:
        return "high"
    return "medium"


def _default_verification_checks(expected_outputs: list[str]) -> list[Any]:
    checks: list[Any] = ["success"]
    concrete_keys = [value for value in expected_outputs if value and value != "success"]
    if concrete_keys:
        checks.append({"type": "require_output_keys", "keys": concrete_keys})
    return checks


def list_contract_safe_tool_names(
    tool_registry: Optional[Mapping[str, Callable[..., Any]]] = None,
) -> list[str]:
    from app.agents.tools.registry import TOOL_REGISTRY

    registry = tool_registry or TOOL_REGISTRY
    safe_tools: list[str] = []
    for tool_name in SAFE_WORKFLOW_TOOL_ORDER:
        tool_fn = registry.get(tool_name)
        if tool_fn is None:
            continue
        if getattr(tool_fn, "input_schema", None) is None:
            continue
        if classify_tool(tool_name, tool_registry=registry) in {"missing", "placeholder", "degraded"}:
            continue
        safe_tools.append(tool_name)
    return safe_tools


def enrich_template_phases_for_execution(
    phases: list[dict[str, Any]],
    *,
    template_name: str = "",
    category: str = "operations",
    persona: str | None = None,
    goal: str = "",
    tool_registry: Optional[Mapping[str, Callable[..., Any]]] = None,
) -> list[dict[str, Any]]:
    """Fill strict workflow-contract metadata for loose draft steps."""
    from app.agents.tools.registry import TOOL_REGISTRY

    registry = tool_registry or TOOL_REGISTRY
    normalized_phases = deepcopy(phases or [])

    for phase_index, phase in enumerate(normalized_phases):
        if not isinstance(phase, dict):
            normalized_phases[phase_index] = {"name": f"Phase {phase_index + 1}", "steps": []}
            continue

        phase.setdefault("name", f"Phase {phase_index + 1}")
        steps = phase.get("steps")
        if not isinstance(steps, list):
            phase["steps"] = []
            continue

        for step_index, raw_step in enumerate(steps):
            step = raw_step if isinstance(raw_step, dict) else {}
            tool_name = str(step.get("tool") or step.get("action_type") or "create_task").strip() or "create_task"
            step_name = str(step.get("name") or f"Step {step_index + 1}").strip() or f"Step {step_index + 1}"
            step_description = str(step.get("description") or "").strip()
            required_approval = bool(step.get("required_approval"))
            tool_fn = registry.get(tool_name)
            input_schema: type[BaseModel] | None = getattr(tool_fn, "input_schema", None) if tool_fn else None

            input_bindings = _build_input_bindings(
                tool_name=tool_name,
                step_name=step_name,
                step_description=step_description,
                template_name=template_name,
                category=category,
                persona=persona,
                goal=goal,
                input_schema=input_schema,
                existing_bindings=step.get("input_bindings") if isinstance(step.get("input_bindings"), Mapping) else None,
            )

            risk_level = str(step.get("risk_level") or "").strip().lower()
            if risk_level not in VALID_RISK_LEVELS:
                risk_level = _default_risk_level(tool_name, required_approval=required_approval)
            if risk_level in STRICT_APPROVAL_RISK_LEVELS:
                required_approval = True

            required_integrations = step.get("required_integrations")
            if not isinstance(required_integrations, list):
                required_integrations = TOOL_REQUIRED_INTEGRATIONS.get(tool_name, [])

            expected_outputs = step.get("expected_outputs")
            if not isinstance(expected_outputs, list) or not expected_outputs:
                expected_outputs = TOOL_EXPECTED_OUTPUTS.get(tool_name, ["success"])

            verification_checks = step.get("verification_checks")
            if not isinstance(verification_checks, list) or not verification_checks:
                verification_checks = _default_verification_checks(expected_outputs)

            allow_parallel = step.get("allow_parallel")
            if not isinstance(allow_parallel, bool):
                allow_parallel = tool_name in PARALLEL_FRIENDLY_TOOLS

            phase["steps"][step_index] = {
                **step,
                "name": step_name,
                "tool": tool_name,
                "description": step_description,
                "required_approval": required_approval,
                "input_bindings": input_bindings,
                "risk_level": risk_level,
                "required_integrations": required_integrations,
                "verification_checks": verification_checks,
                "expected_outputs": expected_outputs,
                "allow_parallel": allow_parallel,
            }

    return normalized_phases


__all__ = [
    "SAFE_WORKFLOW_TOOL_ORDER",
    "enrich_template_phases_for_execution",
    "list_contract_safe_tool_names",
]

