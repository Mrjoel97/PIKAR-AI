# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Workflow Tools for Agents.

Tools to list, start, and manage workflows.
"""

import asyncio
from typing import Dict, List, Any

from app.workflows.engine import get_workflow_engine

def list_workflow_templates() -> List[Dict[str, str]]:
    """List all available workflow templates."""
    engine = get_workflow_engine()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    templates = loop.run_until_complete(engine.list_templates())
    return [
        {"name": t["name"], "description": t["description"], "category": t["category"]}
        for t in templates
    ]

def start_workflow(user_id: str, template_name: str, topic: str = "") -> Dict[str, Any]:
    """Start a new workflow execution.
    
    Args:
        user_id: The ID of the user.
        template_name: Exact name of the template (e.g. 'Lead Generation Workflow').
        topic: Context or topic for this workflow (e.g. 'Q1 Sales Push').
    """
    engine = get_workflow_engine()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    result = loop.run_until_complete(
        engine.start_workflow(user_id, template_name, {"topic": topic})
    )
    return result

def approve_workflow_step(execution_id: str, feedback: str = "") -> Dict[str, Any]:
    """Approve the current step of a running workflow.
    
    Args:
        execution_id: The ID of the execution to approve.
        feedback: Optional feedback or instructions.
    """
    engine = get_workflow_engine()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    result = loop.run_until_complete(
        engine.approve_step(execution_id, feedback)
    )
    return result

def get_workflow_status(execution_id: str) -> Dict[str, Any]:
    """Check the status of a specific workflow."""
    engine = get_workflow_engine()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    result = loop.run_until_complete(
        engine.get_execution_status(execution_id)
    )
    return result

WORKFLOW_TOOLS = [
    list_workflow_templates,
    start_workflow,
    approve_workflow_step,
    get_workflow_status
]
