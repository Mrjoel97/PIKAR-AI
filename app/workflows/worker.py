# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Workflow Worker.

Background process that polls for active workflow steps and executes them.
"""

import asyncio
import inspect
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from app.services.supabase_client import get_service_client
from app.workflows.engine import get_workflow_engine
from app.workflows.step_executor import StepExecutor
from supabase import Client

# Configure Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("WorkflowWorker")


class WorkflowWorker:
    """Background process that polls for workflow steps and ai_jobs.

    Features:
    - Workflow step execution
    - ai_jobs processing with atomic claiming
    - Scheduled maintenance (session cleanup, version pruning)
    - Periodic execution of saved report schedules
    """

    def __init__(self):
        self.running = False
        self.worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        self.client = self._get_supabase()
        self.engine = get_workflow_engine()
        self.step_executor = StepExecutor(self.client)
        self.last_maintenance = datetime.min
        self.maintenance_interval_hours = 1
        self.last_report_schedule_tick = datetime.min
        self.report_schedule_interval_seconds = 60
        self.last_workflow_trigger_tick = datetime.min
        self.workflow_trigger_interval_seconds = 60

    def _get_supabase(self) -> Client:
        return get_service_client()

    async def start(self, interval_seconds: int = 5):
        """Start the polling loop with maintenance and schedule ticks."""
        self.running = True
        logger.info("Workflow Worker %s started. Polling for tasks...", self.worker_id)

        while self.running:
            try:
                await self.process_pending_steps()
                await self.process_ai_jobs()
                await self.run_report_scheduler_if_due()
                await self.run_workflow_trigger_scheduler_if_due()
                await self.run_maintenance_if_due()
            except Exception as e:
                logger.error("Error in worker loop: %s", e, exc_info=True)

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

    async def claim_next_job(self) -> dict | None:
        """Atomically claim the next pending job."""
        try:
            result = self.client.rpc(
                "claim_next_ai_job", {"p_worker_id": self.worker_id}
            ).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("Failed to claim job: %s", e)
            return None

    async def execute_ai_job(self, job: dict):
        """Execute a claimed ai_job."""
        job_id = job["id"]
        job_type = job["job_type"]
        input_data = job.get("input_data") or {}

        logger.info("Executing ai_job %s: %s", job_id, job_type)

        try:
            result = await self.handle_job_type(job_type, input_data)
            self.client.rpc(
                "complete_ai_job", {"p_job_id": str(job_id), "p_output_data": result}
            ).execute()
            logger.info("ai_job %s completed successfully", job_id)
        except Exception as e:
            logger.error("ai_job %s failed: %s", job_id, e, exc_info=True)
            self.client.rpc(
                "fail_ai_job", {"p_job_id": str(job_id), "p_error_message": str(e)}
            ).execute()

    async def handle_job_type(self, job_type: str, input_data: dict) -> dict:
        """Route job to appropriate handler."""
        handlers = {
            "daily_report": self.handle_daily_report,
            "weekly_digest": self.handle_weekly_digest,
            "workflow_trigger_start": self.handle_workflow_trigger_start,
        }
        handler = handlers.get(job_type)
        if handler:
            return await handler(input_data)

        from app.agents.tools.registry import get_tool

        tool_func = get_tool(job_type)
        if tool_func:
            return await self._invoke_tool(tool_func, input_data)
        raise ValueError(f"Unknown job type: {job_type}")

    async def _invoke_tool(
        self, tool_func, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute sync or async tools safely from the worker."""
        result = tool_func(**input_data)
        if inspect.isawaitable(result):
            return await result
        return result

    async def handle_daily_report(self, input_data: dict) -> dict:
        """Generate daily business report."""
        logger.info("Generating daily report with input: %s", input_data)
        return {"status": "completed", "report_type": "daily"}

    async def handle_weekly_digest(self, input_data: dict) -> dict:
        """Generate weekly digest."""
        logger.info("Generating weekly digest with input: %s", input_data)
        return {"status": "completed", "report_type": "weekly"}

    async def run_report_scheduler_if_due(self):
        """Run saved report schedules at a controlled cadence."""
        now = datetime.now()
        seconds_since_last = (now - self.last_report_schedule_tick).total_seconds()
        if seconds_since_last < self.report_schedule_interval_seconds:
            return

        self.last_report_schedule_tick = now

        try:
            from app.services.report_scheduler import run_scheduler_tick

            results = await run_scheduler_tick()
            if results:
                logger.info("Executed %s saved report schedules", len(results))
            for result in results:
                if result.get("status") == "error":
                    logger.warning("Scheduled report execution failed: %s", result)
        except Exception as exc:
            logger.error("Report scheduler tick failed: %s", exc, exc_info=True)

    async def handle_workflow_trigger_start(self, input_data: dict) -> dict:
        """Execute a workflow mission that was queued by a durable trigger."""
        from app.services.workflow_trigger_service import get_workflow_trigger_service

        return await get_workflow_trigger_service().execute_trigger_job(input_data)

    async def run_workflow_trigger_scheduler_if_due(self):
        """Run saved workflow triggers at a controlled cadence."""
        now = datetime.now()
        seconds_since_last = (now - self.last_workflow_trigger_tick).total_seconds()
        if seconds_since_last < self.workflow_trigger_interval_seconds:
            return

        self.last_workflow_trigger_tick = now

        try:
            from app.services.workflow_trigger_service import (
                run_workflow_trigger_scheduler_tick,
            )

            results = await run_workflow_trigger_scheduler_tick()
            if results:
                logger.info("Queued %s workflow triggers", len(results))
            for result in results:
                if result.get("status") == "error":
                    logger.warning(
                        "Workflow trigger scheduler execution failed: %s", result
                    )
        except Exception as exc:
            logger.error(
                "Workflow trigger scheduler tick failed: %s", exc, exc_info=True
            )

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
                logger.error("Maintenance failed: %s", e, exc_info=True)

    async def cleanup_old_sessions(self, days: int = 30):
        """Delete sessions older than N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        result = (
            self.client.table("sessions").delete().lt("updated_at", cutoff).execute()
        )
        count = len(result.data) if result.data else 0
        logger.info(f"Cleaned up {count} old sessions")

    async def prune_old_versions(self, keep_versions: int = 50):
        """Prune version history to keep only last N versions per session."""
        result = self.client.rpc(
            "prune_session_versions", {"p_keep_count": keep_versions}
        ).execute()
        deleted = result.data if result.data else 0
        logger.info(f"Pruned {deleted} old version entries")

    async def reap_stale_jobs(self, timeout_hours: int = 1):
        """Mark stuck jobs as failed."""
        cutoff = (datetime.now() - timedelta(hours=timeout_hours)).isoformat()
        result = (
            self.client.table("ai_jobs")
            .update(
                {
                    "status": "failed",
                    "error_message": f"Timed out after {timeout_hours} hour(s)",
                    "completed_at": datetime.now().isoformat(),
                }
            )
            .eq("status", "processing")
            .lt("locked_at", cutoff)
            .execute()
        )
        count = len(result.data) if result.data else 0
        if count > 0:
            logger.warning(f"Reaped {count} stale jobs")

    # =========================================================================
    # Workflow Steps Processing (Existing)
    # =========================================================================

    async def get_runnable_steps(self) -> list[dict]:
        """Fetch steps that are 'running'."""
        # Join with template definition to get the tool name
        # Supabase join syntax via API is limited, so we might need two queries or a view.
        # But wait, workflow_steps stores 'phase_name' and 'step_name'.
        # We need to look up the 'tool' from the template.

        # 1. Get running steps
        res = (
            self.client.table("workflow_steps")
            .select("*, workflow_executions(template_id, context)")
            .eq("status", "running")
            .execute()
        )
        steps = res.data

        runnable_steps = []

        for step in steps:
            # 2. Get Template info (could cache this)
            # We need to find the specific step definition in the template JSON
            template_id = step["workflow_executions"]["template_id"]
            # Optimization: Cache templates in memory
            res_temp = (
                self.client.table("workflow_templates")
                .select("phases")
                .eq("id", template_id)
                .execute()
            )
            if not res_temp.data:
                continue

            phases = res_temp.data[0]["phases"]

            # Find the matching step definition
            target_phase = next(
                (p for p in phases if p["name"] == step["phase_name"]), None
            )
            if not target_phase:
                continue

            target_step_def = next(
                (s for s in target_phase["steps"] if s["name"] == step["step_name"]),
                None,
            )
            if not target_step_def:
                continue

            # Check if approval is actually required but was missed (double check)
            if target_step_def.get("required_approval", False):
                # Should be 'waiting_approval', not 'running'. Fix it.
                logger.warning(
                    f"Step {step['id']} needs approval but is RUNNING. Fixing status."
                )
                self.client.table("workflow_steps").update(
                    {"status": "waiting_approval"}
                ).eq("id", step["id"]).execute()
                continue

            # It's runnable!
            step["tool_name"] = target_step_def["tool"]
            runnable_steps.append(step)

        return runnable_steps

    async def process_pending_steps(self):
        """Find and execute steps, supporting parallel execution groups."""
        steps = await self.get_runnable_steps()
        if not steps:
            return

        logger.info(f"Found {len(steps)} runnable steps.")

        # Group steps by execution_id + phase_index for parallel detection
        parallel_groups: dict[str, list] = {}
        sequential_steps: list = []

        for step in steps:
            step_def = step.get("step_definition") or {}
            if step_def.get("parallel"):
                group_key = f"{step['execution_id']}:{step.get('phase_index', 0)}"
                parallel_groups.setdefault(group_key, []).append(step)
            else:
                sequential_steps.append(step)

        # Execute parallel groups
        for group_key, group_steps in parallel_groups.items():
            if len(group_steps) > 1:
                logger.info(
                    "Executing %d parallel steps for group %s",
                    len(group_steps),
                    group_key,
                )
                await self.step_executor.execute_parallel_steps(
                    group_steps, self.engine
                )
            else:
                await self.execute_step(group_steps[0])

        # Execute sequential steps
        for step in sequential_steps:
            await self.execute_step(step)

    async def execute_step(self, step: dict):
        """Execute a single step using the unified StepExecutor."""
        try:
            await self.step_executor.execute_step(step, self.engine)
        except Exception as e:
            # Errors are logged and updated in StepExecutor, but we log here too
            logger.error(f"Worker execution failed for step {step['id']}: {e}")


if __name__ == "__main__":
    worker = WorkflowWorker()
    asyncio.run(worker.start())
