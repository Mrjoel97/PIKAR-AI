# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Workflow Tools for Agents.

Tools to list, start, and manage workflows.
All tools are async because ADK runs inside an async event loop.
"""

import json
import re
from typing import Any

from app.agents.tools.tool_cache import cached_tool
from app.autonomy.agent_kernel import get_agent_kernel


@cached_tool(lambda *args, **kwargs: "list_workflow_templates", ttl=60)
async def list_workflow_templates() -> list[dict[str, str]]:
    """List all available workflow templates."""
    from app.workflows.engine import get_workflow_engine

    engine = get_workflow_engine()
    templates = await engine.list_templates()
    return [
        {"name": t["name"], "description": t["description"], "category": t["category"]}
        for t in templates
    ]


async def start_workflow(
    template_name: str,
    topic: str = "",
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Start a new workflow execution using the authenticated user context."""
    from app.services.request_context import get_current_session_id, get_current_user_id
    from app.workflows.engine import get_workflow_engine

    user_id = get_current_user_id()
    if not user_id:
        return {"error": "Missing user context for workflow execution"}

    engine = get_workflow_engine()
    kernel = get_agent_kernel(workflow_engine=engine)
    workflow_context = _coerce_context_dict(context)
    current_session_id = get_current_session_id()
    if current_session_id and "session_id" not in workflow_context:
        workflow_context["session_id"] = current_session_id
    if topic and "topic" not in workflow_context:
        workflow_context["topic"] = topic
    result = await kernel.start_workflow_mission(
        user_id=user_id,
        template_name=template_name,
        context=workflow_context,
        run_source="agent_ui",
        session_id=current_session_id,
    )
    return result


async def approve_workflow_step(
    execution_id: str, feedback: str = ""
) -> dict[str, Any]:
    """Approve the current step of a running workflow."""
    from app.workflows.engine import get_workflow_engine

    normalized_execution_id, normalized_feedback = _coerce_approval_args(
        execution_id, feedback
    )
    engine = get_workflow_engine()
    result = await engine.approve_step(normalized_execution_id, normalized_feedback)
    return result


async def get_workflow_status(execution_id: str) -> dict[str, Any]:
    """Check the status of a specific workflow."""
    from app.workflows.engine import get_workflow_engine

    normalized_execution_id, _ = _coerce_approval_args(execution_id, "")
    engine = get_workflow_engine()
    result = await engine.get_execution_status(normalized_execution_id)
    return result


async def create_workflow_template(
    name: str,
    description: str,
    category: str,
    phases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create a new workflow template."""
    from app.services.request_context import get_current_user_id
    from app.workflows.engine import get_workflow_engine

    user_id = get_current_user_id()
    if not user_id:
        return {"error": "Missing user context for workflow template creation"}

    engine = get_workflow_engine()
    result = await engine.create_template(
        user_id=user_id,
        name=name,
        description=description,
        category=category,
        phases=phases,
    )
    return result


WORKFLOW_TOOLS = [
    list_workflow_templates,
    start_workflow,
    approve_workflow_step,
    get_workflow_status,
    create_workflow_template,
]


def _coerce_context_dict(context: Any) -> dict[str, Any]:
    if context is None:
        return {}
    if isinstance(context, dict):
        return dict(context)
    if isinstance(context, str):
        raw = context.strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"context": raw}
        return dict(parsed) if isinstance(parsed, dict) else {"context": raw}

    try:
        return dict(context)
    except (TypeError, ValueError):
        return {"context": str(context)}


def _coerce_approval_args(execution_id: Any, feedback: Any) -> tuple[str, str]:
    if isinstance(execution_id, dict):
        parsed_execution_id = execution_id.get("execution_id")
        parsed_feedback = execution_id.get("feedback", feedback)
        execution_id = parsed_execution_id if parsed_execution_id is not None else execution_id
        feedback = parsed_feedback
    elif isinstance(execution_id, str):
        raw = execution_id.strip()
        if raw.startswith("{"):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                return _coerce_approval_args(
                    parsed.get("execution_id", ""), parsed.get("feedback", feedback)
                )

        match = re.search(r'execution_id\s*:\s*"?(?P<id>[0-9a-fA-F-]{36})"?', raw)
        if match:
            execution_id = match.group("id")

    normalized_execution_id = str(execution_id or "").strip()
    normalized_feedback = "" if feedback is None else str(feedback)
    return normalized_execution_id, normalized_feedback
