# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Workflow Tools for Agents.

Tools to list, start, and manage workflows.
All tools are async because ADK runs inside an async event loop.
"""

from typing import Dict, List, Any
from app.agents.tools.tool_cache import cached_tool

# from app.workflows.engine import get_workflow_engine


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

async def start_workflow(user_id: str, template_name: str, topic: str = "") -> Dict[str, Any]:
    """Start a new workflow execution.
    
    Args:
        user_id: The ID of the user.
        template_name: Exact name of the template (e.g. 'Lead Generation Workflow').
        topic: Context or topic for this workflow (e.g. 'Q1 Sales Push').
    """
    from app.workflows.engine import get_workflow_engine
    engine = get_workflow_engine()
    result = await engine.start_workflow(user_id, template_name, {"topic": topic})
    return result

async def approve_workflow_step(execution_id: str, feedback: str = "") -> Dict[str, Any]:
    """Approve the current step of a running workflow.
    
    Args:
        execution_id: The ID of the execution to approve.
        feedback: Optional feedback or instructions.
    """
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

async def create_workflow_template(name: str, description: str, category: str, phases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a new workflow template."""
    from app.workflows.engine import get_workflow_engine
    engine = get_workflow_engine()
    # This is a simplification. In a real scenario, we'd need a user ID.
    # For this agent-driven scenario, we'll need to consider how to handle ownership.
    # For now, we'll proceed without a user ID, which may require changes to the engine.
    result = await engine.create_template(
        user_id="agent_user",  # Using a placeholder user ID
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
