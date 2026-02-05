# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Workflow Engine.

Executes structured workflows defined in the database.
Handles phase transitions, step execution, and approval gates.
"""

import os
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from supabase import Client
from app.services.supabase import get_service_client
from app.services.edge_functions import edge_function_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkflowEngine:
    def __init__(self):
        self.client = self._get_supabase()

    def _get_supabase(self) -> Client:
        return get_service_client()

    async def list_templates(self, category: Optional[str] = None) -> List[Dict]:
        """List available workflow templates."""
        query = self.client.table("workflow_templates").select("id, name, description, category")
        if category:
            query = query.eq("category", category)
        res = query.execute()
        return res.data

    async def start_workflow(self, user_id: str, template_name: str, context: Dict[str, Any] = {}) -> Dict[str, Any]:
        """Start a new workflow execution from a template."""
        
        # 1. Get Template
        res = self.client.table("workflow_templates").select("*").eq("name", template_name).execute()
        if not res.data:
            return {"error": f"Template '{template_name}' not found"}
        
        template = res.data[0]
        phases = template["phases"] # JSONB
        
        # 2. Create Execution
        execution_data = {
            "user_id": user_id,
            "template_id": template["id"],
            "name": f"{template_name} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "status": "running",
            "current_phase_index": 0,
            "current_step_index": 0,
            "context": context
        }
        res_exec = self.client.table("workflow_executions").insert(execution_data).execute()
        execution_id = res_exec.data[0]["id"]
        
        # 3. Create First Step Record
        first_phase = phases[0]
        first_step = first_phase["steps"][0]
        
        step_data = {
            "execution_id": execution_id,
            "phase_name": first_phase["name"],
            "step_name": first_step["name"],
            "status": "running" if not first_step.get("required_approval") else "waiting_approval",
            "input_data": context,
            "started_at": datetime.now().isoformat()
        }
        self.client.table("workflow_steps").insert(step_data).execute()
        
        # 4. Trigger Execution Logic (if not waiting for approval)
        if step_data["status"] == "running":
            # Invoke the execute-workflow edge function
            asyncio.create_task(edge_function_client.execute_workflow(execution_id, action="start"))
            
        return {
            "execution_id": execution_id,
            "status": step_data["status"],
            "current_step": f"{first_phase['name']}: {first_step['name']}",
            "message": f"Workflow started. Next step: {first_step['description']}"
        }

    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get full status of an execution."""
        res_exec = self.client.table("workflow_executions").select("*, workflow_templates(name, phases)").eq("id", execution_id).execute()
        if not res_exec.data:
            return {"error": "Execution not found"}
            
        execution = res_exec.data[0]
        template = execution['workflow_templates']
        
        # Get history
        res_steps = self.client.table("workflow_steps").select("*").eq("execution_id", execution_id).order("started_at").execute()
        
        return {
            "execution": execution,
            "template_name": template['name'],
            "history": res_steps.data,
            "current_phase_index": execution['current_phase_index'],
            "current_step_index": execution['current_step_index']
        }

    async def list_executions(self, user_id: str, status: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """List workflow executions for a user."""
        query = self.client.table("workflow_executions")\
            .select("*, workflow_templates(name)")\
            .eq("user_id", user_id)
            
        if status:
            query = query.eq("status", status)
            
        res = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        # Flatten template name for easier consumption if needed, 
        # or just return as is matching the join structure.
        # The router expects a list of dicts.
        executions = []
        for exc in res.data:
            exc["template_name"] = exc["workflow_templates"]["name"] if exc.get("workflow_templates") else "Unknown"
            executions.append(exc)
            
        return executions

    async def approve_step(self, execution_id: str, step_message: str = "Approved by user") -> Dict[str, Any]:
        """Approve the current step if it is waiting for approval."""
        status = await self.get_execution_status(execution_id)
        if "error" in status: return status
        
        exec_data = status["execution"]
        
        # Find current active step
        res_step = self.client.table("workflow_steps").select("*")\
            .eq("execution_id", execution_id)\
            .eq("status", "waiting_approval")\
            .order("started_at", desc=True)\
            .limit(1).execute()
            
        if not res_step.data:
            return {"error": "No step is currently waiting for approval"}
            
        step = res_step.data[0]
        
        # Mark completed
        self.client.table("workflow_steps").update({
            "status": "completed",
            "output_data": {"approval_message": step_message},
            "completed_at": datetime.now().isoformat()
        }).eq("id", step["id"]).execute()
        
        # Advance to next step
        # Trigger the workflow execution to proceed
        asyncio.create_task(edge_function_client.execute_workflow(execution_id, action="advance"))
        
        return {
            "status": "approved", 
            "message": "Step approved. Workflow execution continuing in background."
        }

    async def _advance_workflow(self, execution: Dict, phases: List[Dict]) -> Dict[str, Any]:
        """Move to the next step using Edge Function.
        
        Deprecated: Logic is now handled by 'execute-workflow' Edge Function.
        This method is kept for manual invocation compatibility if needed, 
        but should ideally delegate to the EF.
        """
        await edge_function_client.execute_workflow(execution["id"], action="advance")
        return {"status": "processing", "message": "Workflow advancement triggered"}

# Singleton
_engine = None
def get_workflow_engine():
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine
