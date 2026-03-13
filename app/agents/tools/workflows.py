# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Workflow Tools for Agents.

Tools to list, start, and manage workflows.
All tools are async because ADK runs inside an async event loop.
"""

from typing import Any, Dict, List

from app.agents.tools.tool_cache import cached_tool


@cached_tool(lambda *args, **kwargs: "list_workflow_templates", ttl=60)
async def list_workflow_templates() -> List[Dict[str, str]]:
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
    context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Start a new workflow execution using the authenticated user context."""
    from app.workflows.engine import get_workflow_engine

    from app.services.request_context import get_current_session_id, get_current_user_id

    user_id = get_current_user_id()
    if not user_id:
        return {"error": "Missing user context for workflow execution"}

    engine = get_workflow_engine()
    workflow_context = dict(context or {})
    current_session_id = get_current_session_id()
    if current_session_id and "session_id" not in workflow_context:
        workflow_context["session_id"] = current_session_id
    if topic and "topic" not in workflow_context:
        workflow_context["topic"] = topic
    result = await engine.start_workflow(
        user_id=user_id,
        template_name=template_name,
        context=workflow_context,
        run_source="agent_ui",
    )
    return result


async def approve_workflow_step(execution_id: str, feedback: str = "") -> Dict[str, Any]:
    """Approve the current step of a running workflow."""
    from app.workflows.engine import get_workflow_engine

    engine = get_workflow_engine()
    result = await engine.approve_step(execution_id, feedback)
    return result


async def get_workflow_status(execution_id: str) -> Dict[str, Any]:
    """Check the status of a specific workflow."""
    from app.workflows.engine import get_workflow_engine

    engine = get_workflow_engine()
    result = await engine.get_execution_status(execution_id)
    return result


async def create_workflow_template(
    name: str,
    description: str,
    category: str,
    phases: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Create a new workflow template."""
    from app.workflows.engine import get_workflow_engine

    from app.services.request_context import get_current_user_id

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



