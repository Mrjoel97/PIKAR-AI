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

from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkflowEngine:
    def __init__(self):
        self.client = self._get_supabase()

    def _get_supabase(self) -> Client:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            from dotenv import load_dotenv
            load_dotenv()
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        return create_client(url, key)

    async def list_templates(self) -> List[Dict]:
        """List available workflow templates."""
        res = self.client.table("workflow_templates").select("id, name, description, category").execute()
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
            # In a real async worker system, we'd queue this.
            # Here we might just return the status and let the agent invoke 'advance'
            pass
            
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
        return await self._advance_workflow(exec_data, status['execution']['workflow_templates']['phases'])

    async def _advance_workflow(self, execution: Dict, phases: List[Dict]) -> Dict[str, Any]:
        """Move to the next step in the sequence."""
        c_phase_idx = execution['current_phase_index']
        c_step_idx = execution['current_step_index']
        
        current_phase = phases[c_phase_idx]
        
        # Increment step
        next_step_idx = c_step_idx + 1
        next_phase_idx = c_phase_idx
        
        if next_step_idx >= len(current_phase['steps']):
            # Phase complete, move to next phase
            next_step_idx = 0
            next_phase_idx += 1
            
        if next_phase_idx >= len(phases):
            # Workflow complete
            self.client.table("workflow_executions").update({
                "status": "completed",
                "completed_at": datetime.now().isoformat()
            }).eq("id", execution["id"]).execute()
            return {"status": "completed", "message": "Workflow completed successfully!"}
            
        # Update Pointers
        self.client.table("workflow_executions").update({
            "current_phase_index": next_phase_idx,
            "current_step_index": next_step_idx
        }).eq("id", execution["id"]).execute()
        
        # Create Record for next step
        next_phase = phases[next_phase_idx]
        next_step = next_phase["steps"][next_step_idx]
        
        step_data = {
            "execution_id": execution["id"],
            "phase_name": next_phase["name"],
            "step_name": next_step["name"],
            "status": "running" if not next_step.get("required_approval") else "waiting_approval",
            "started_at": datetime.now().isoformat()
        }
        self.client.table("workflow_steps").insert(step_data).execute()
        
        msg = f"Advanced to {next_phase['name']}: {next_step['name']}"
        if step_data["status"] == "waiting_approval":
            msg += " (Waiting for Approval)"
            
        return {
            "status": step_data["status"],
            "current_step": f"{next_phase['name']}: {next_step['name']}",
            "message": msg
        }

# Singleton
_engine = None
def get_workflow_engine():
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine
