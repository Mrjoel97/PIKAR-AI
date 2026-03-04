# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Step Executor for Workflow Automation.

Centralizes the logic for executing a single workflow step, including
tool resolution, deterministic argument mapping, and state updates.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Type
from pydantic import BaseModel, ValidationError

from app.agents.tools.registry import get_tool
from app.services.supabase_client import get_service_client

logger = logging.getLogger(__name__)

class StepExecutor:
    """Handles the execution of a single workflow step with deterministic mapping."""

    def __init__(self, supabase_client=None):
        self.client = supabase_client or get_service_client()

    async def execute_step(self, step: Dict, workflow_engine=None) -> Dict[str, Any]:
        """Execute a single step with schema-based validation.
        
        Args:
            step: The step record from the database.
            workflow_engine: Optional engine instance to advance the workflow after success.
            
        Returns:
            The output of the tool execution.
        """
        step_id = step['id']
        tool_name = step['tool_name']
        execution_id = step['execution_id']
        
        logger.info(f"StepExecutor: Executing Step {step_id} ({tool_name})")
        
        try:
            # 1. Resolve Tool
            tool_func = get_tool(tool_name)
            
            # 2. Build Context
            workflow_context = step.get('workflow_executions', {}).get('context') or {}
            input_data = step.get('input_data') or {}
            
            # Merge (input_data overrides workflow_context)
            sys_context = {**workflow_context, **input_data}
            
            # 3. Deterministic Argument Mapping
            args = {}
            input_schema: Optional[Type[BaseModel]] = getattr(tool_func, "input_schema", None)
            
            if input_schema:
                logger.info(f"StepExecutor: Using input schema for {tool_name}")
                try:
                    # Validate and extract only fields defined in the schema
                    validated_input = input_schema(**sys_context)
                    args = validated_input.model_dump()
                except ValidationError as e:
                    logger.error(f"StepExecutor: Input validation failed for {tool_name}: {e}")
                    raise RuntimeError(f"Input validation failed: {e}")
            else:
                # Fallback to heuristic or broad mapping if no schema is provided
                logger.warning(f"StepExecutor: No input schema for {tool_name}, using broad mapping.")
                args = sys_context

            # 4. Execute Tool
            try:
                # Try calling with mapped args
                if asyncio.iscoroutinefunction(tool_func):
                    output = await tool_func(**args)
                else:
                    # Handle sync tools wrapped via to_thread or similar if needed
                    output = tool_func(**args)
            except TypeError as te:
                logger.warning(f"StepExecutor: TypeError in {tool_name}, falling back to no-arg call: {te}")
                # Fallback for tools that don't accept **kwargs or specific args yet
                if asyncio.iscoroutinefunction(tool_func):
                    output = await tool_func()
                else:
                    output = tool_func()
            
            # 5. Update Step Record
            self.client.table("workflow_steps").update({
                "status": "completed",
                "output_data": output,
                "completed_at": datetime.now().isoformat()
            }).eq("id", step_id).execute()
            
            logger.info(f"StepExecutor: Step {step_id} completed successfully.")
            
            # 6. Advance Workflow if engine provided
            if workflow_engine:
                from app.workflows.engine import WorkflowEngine
                if isinstance(workflow_engine, WorkflowEngine):
                    status = await workflow_engine.get_execution_status(execution_id)
                    if "error" not in status:
                        template_phases = status['execution']['workflow_templates']['phases']
                        await workflow_engine._advance_workflow(status['execution'], template_phases)
            
            return output
            
        except Exception as e:
            logger.error(f"StepExecutor: Step {step_id} failed: {e}", exc_info=True)
            self.client.table("workflow_steps").update({
                "status": "failed",
                "error_message": str(e)
            }).eq("id", step_id).execute()
            raise
