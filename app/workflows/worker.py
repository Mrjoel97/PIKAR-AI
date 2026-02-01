# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Workflow Worker.

Background process that polls for active workflow steps and executes them.
"""

import asyncio
import logging
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from supabase import create_client, Client

from app.workflows.engine import get_workflow_engine
from app.agents.tools.registry import get_tool

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WorkflowWorker")

class WorkflowWorker:
    """Background process that polls for workflow steps and ai_jobs.
    
    Features:
    - Workflow step execution
    - ai_jobs processing with atomic claiming
    - Scheduled maintenance (session cleanup, version pruning)
    """
    
    def __init__(self):
        self.running = False
        self.worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        self.client = self._get_supabase()
        self.engine = get_workflow_engine()
        self.last_maintenance = datetime.min
        self.maintenance_interval_hours = 1

    def _get_supabase(self) -> Client:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            from dotenv import load_dotenv
            load_dotenv()
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        return create_client(url, key)

    async def start(self, interval_seconds: int = 5):
        """Start the polling loop with maintenance."""
        self.running = True
        logger.info(f"Workflow Worker {self.worker_id} started. Polling for tasks...")
        
        while self.running:
            try:
                # Process workflow steps
                await self.process_pending_steps()
                
                # Process ai_jobs queue
                await self.process_ai_jobs()
                
                # Run scheduled maintenance
                await self.run_maintenance_if_due()
                
            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
            
            await asyncio.sleep(interval_seconds)

    # =========================================================================
    # AI Jobs Processing
    # =========================================================================

    async def process_ai_jobs(self):
        """Process pending ai_jobs from the queue."""
        while True:
            job = await self.claim_next_job()
            if not job:
                break
            await self.execute_ai_job(job)

    async def claim_next_job(self) -> Optional[Dict]:
        """Atomically claim the next pending job."""
        try:
            result = self.client.rpc("claim_next_ai_job", {
                "p_worker_id": self.worker_id
            }).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to claim job: {e}")
            return None

    async def execute_ai_job(self, job: Dict):
        """Execute a claimed ai_job."""
        job_id = job["id"]
        job_type = job["job_type"]
        input_data = job.get("input_data") or {}
        
        logger.info(f"Executing ai_job {job_id}: {job_type}")
        
        try:
            # Route to appropriate handler based on job_type
            result = await self.handle_job_type(job_type, input_data)
            
            # Mark job as completed
            self.client.rpc("complete_ai_job", {
                "p_job_id": str(job_id),
                "p_output_data": result
            }).execute()
            
            logger.info(f"ai_job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"ai_job {job_id} failed: {e}", exc_info=True)
            self.client.rpc("fail_ai_job", {
                "p_job_id": str(job_id),
                "p_error_message": str(e)
            }).execute()

    async def handle_job_type(self, job_type: str, input_data: Dict) -> Dict:
        """Route job to appropriate handler."""
        handlers = {
            "daily_report": self.handle_daily_report,
            "weekly_digest": self.handle_weekly_digest,
        }
        handler = handlers.get(job_type)
        if handler:
            return await handler(input_data)
        else:
            # Generic tool execution
            tool_func = get_tool(job_type)
            if tool_func:
                return await tool_func(**input_data)
            raise ValueError(f"Unknown job type: {job_type}")

    async def handle_daily_report(self, input_data: Dict) -> Dict:
        """Generate daily business report."""
        # Placeholder - integrate with actual report generation
        logger.info("Generating daily report...")
        return {"status": "completed", "report_type": "daily"}

    async def handle_weekly_digest(self, input_data: Dict) -> Dict:
        """Generate weekly digest."""
        logger.info("Generating weekly digest...")
        return {"status": "completed", "report_type": "weekly"}

    # =========================================================================
    # Scheduled Maintenance
    # =========================================================================

    async def run_maintenance_if_due(self):
        """Run maintenance tasks on schedule."""
        now = datetime.now()
        hours_since_last = (now - self.last_maintenance).total_seconds() / 3600
        
        if hours_since_last >= self.maintenance_interval_hours:
            logger.info("Running scheduled maintenance...")
            try:
                await self.cleanup_old_sessions()
                await self.prune_old_versions()
                await self.reap_stale_jobs()
                self.last_maintenance = now
                logger.info("Maintenance completed successfully")
            except Exception as e:
                logger.error(f"Maintenance failed: {e}", exc_info=True)

    async def cleanup_old_sessions(self, days: int = 30):
        """Delete sessions older than N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        result = self.client.table("sessions").delete().lt(
            "updated_at", cutoff
        ).execute()
        count = len(result.data) if result.data else 0
        logger.info(f"Cleaned up {count} old sessions")

    async def prune_old_versions(self, keep_versions: int = 50):
        """Prune version history to keep only last N versions per session."""
        result = self.client.rpc("prune_session_versions", {
            "p_keep_count": keep_versions
        }).execute()
        deleted = result.data if result.data else 0
        logger.info(f"Pruned {deleted} old version entries")

    async def reap_stale_jobs(self, timeout_hours: int = 1):
        """Mark stuck jobs as failed."""
        cutoff = (datetime.now() - timedelta(hours=timeout_hours)).isoformat()
        result = self.client.table("ai_jobs").update({
            "status": "failed",
            "error_message": f"Timed out after {timeout_hours} hour(s)",
            "completed_at": datetime.now().isoformat()
        }).eq("status", "processing").lt("locked_at", cutoff).execute()
        count = len(result.data) if result.data else 0
        if count > 0:
            logger.warning(f"Reaped {count} stale jobs")

    # =========================================================================
    # Workflow Steps Processing (Existing)
    # =========================================================================

    async def get_runnable_steps(self) -> List[Dict]:
        """Fetch steps that are 'running'."""
        # Join with template definition to get the tool name
        # Supabase join syntax via API is limited, so we might need two queries or a view.
        # But wait, workflow_steps stores 'phase_name' and 'step_name'.
        # We need to look up the 'tool' from the template.
        
        # 1. Get running steps
        res = self.client.table("workflow_steps").select("*, workflow_executions(template_id, context)").eq("status", "running").execute()
        steps = res.data
        
        runnable_steps = []
        
        for step in steps:
            # 2. Get Template info (could cache this)
            # We need to find the specific step definition in the template JSON
            template_id = step['workflow_executions']['template_id']
            # Optimization: Cache templates in memory
            res_temp = self.client.table("workflow_templates").select("phases").eq("id", template_id).execute()
            if not res_temp.data:
                continue
                
            phases = res_temp.data[0]['phases']
            
            # Find the matching step definition
            target_phase = next((p for p in phases if p['name'] == step['phase_name']), None)
            if not target_phase: continue
            
            target_step_def = next((s for s in target_phase['steps'] if s['name'] == step['step_name']), None)
            if not target_step_def: continue
            
            # Check if approval is actually required but was missed (double check)
            if target_step_def.get("required_approval", False):
                # Should be 'waiting_approval', not 'running'. Fix it.
                logger.warning(f"Step {step['id']} needs approval but is RUNNING. Fixing status.")
                self.client.table("workflow_steps").update({"status": "waiting_approval"}).eq("id", step['id']).execute()
                continue
                
            # It's runnable!
            step['tool_name'] = target_step_def['tool']
            runnable_steps.append(step)
            
        return runnable_steps

    async def process_pending_steps(self):
        """Find and execute steps."""
        steps = await self.get_runnable_steps()
        if not steps:
            return

        logger.info(f"Found {len(steps)} runnable steps.")
        
        for step in steps:
            await self.execute_step(step)

    async def execute_step(self, step: Dict):
        """Execute a single step."""
        step_id = step['id']
        tool_name = step['tool_name']
        logger.info(f"Executing Step {step_id}: {tool_name}")
        
        try:
            # Get Context/Input
            # Input is combination of Workflow Initial Context + Outputs of previous steps?
            # For simplicity: Input = Workflow Context
            workflow_context = step['workflow_executions']['context'] or {}
            input_data = step.get('input_data') or {}
            
            # Merge (input_data overrides workflow_context)
            sys_context = {**workflow_context, **input_data}
            
            # Get Tool
            tool_func = get_tool(tool_name)
            
            # Execute
            # Note: Tool calling signature might vary. 
            # Ideally tools accept **kwargs matching the context.
            # Only pass keys that the tool accepts? Or pass all?
            # For Safety in this MVp, we assume tools accept **kwargs or we wrap them.
            # Our registry wrapper handles it.
            
            # If tool_func expects specific args, we rely on it ignoring extras or accepting **kwargs
            # Our 'placeholder_tool' accepts anything.
            # Real tools like 'mcp_web_search' expect 'query'.
            # We need to map context keys to tool args.
            # Simple heuristic: if context has 'query', pass it.
            
            # FIXME: Argument mapping is the hard part of automation.
            # Approach: Pass the whole context dictionary as 'context' arg if tool accepts it,
            # OR pass context as kwargs.
            try:
                output = await tool_func(**sys_context)
            except TypeError:
                # Retry with single 'context' arg? or just no args?
                # Simple fallback
                output = await tool_func()
            
            # Update Step Record
            self.client.table("workflow_steps").update({
                "status": "completed",
                "output_data": output, # Store result
                "completed_at": datetime.now().isoformat()
            }).eq("id", step_id).execute()
            
            logger.info(f"Step {step_id} completed successfully.")
            
            # Advance Workflow
            # We need to pass the Execution Dict and Phases.
            # Re-fetch is safest.
            status = await self.engine.get_execution_status(step['execution_id'])
            if "error" not in status:
                template_phases = status['execution']['workflow_templates']['phases']
                await self.engine._advance_workflow(status['execution'], template_phases)
            
        except Exception as e:
            logger.error(f"Step {step_id} failed: {e}", exc_info=True)
            self.client.table("workflow_steps").update({
                "status": "failed",
                "error_message": str(e)
            }).eq("id", step_id).execute()


if __name__ == "__main__":
    worker = WorkflowWorker()
    asyncio.run(worker.start())
