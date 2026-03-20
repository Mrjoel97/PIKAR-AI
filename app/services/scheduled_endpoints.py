# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Cloud Scheduler triggered endpoints.

These endpoints are designed to be triggered by Cloud Scheduler for automated
tasks like daily reports and weekly digests.
"""

import logging
import os

from fastapi import APIRouter, Header, HTTPException
from supabase import Client

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduled", tags=["scheduled"])


def _get_supabase() -> Client:
    """Get Supabase client."""
    return get_service_client()


def _verify_scheduler(x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret")):
    """Verify request comes from Cloud Scheduler."""
    expected = (os.environ.get("SCHEDULER_SECRET") or "").strip()
    if not expected:
        logger.error("Scheduler request rejected because SCHEDULER_SECRET is not configured")
        raise HTTPException(status_code=503, detail="Scheduler is not configured")
    if not x_scheduler_secret or x_scheduler_secret != expected:
        logger.warning("Unauthorized scheduler request")
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


@router.post("/daily-report")
async def trigger_daily_report(x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret")):
    """Trigger daily business report generation."""
    _verify_scheduler(x_scheduler_secret)
    client = _get_supabase()
    job = await execute_async(
        client.table("ai_jobs").insert(
            {
                "job_type": "daily_report",
                "status": "pending",
                "priority": 10,
                "input_data": {"trigger": "scheduled", "type": "daily"},
            }
        ),
        op_name="scheduled.daily_report",
    )
    job_id = job.data[0]["id"] if job.data else None
    logger.info("Daily report job created: %s", job_id)
    return {"status": "queued", "job_id": job_id}


@router.post("/weekly-digest")
async def trigger_weekly_digest(x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret")):
    """Trigger weekly digest email generation."""
    _verify_scheduler(x_scheduler_secret)
    client = _get_supabase()
    job = await execute_async(
        client.table("ai_jobs").insert(
            {
                "job_type": "weekly_digest",
                "status": "pending",
                "priority": 10,
                "input_data": {"trigger": "scheduled", "type": "weekly"},
            }
        ),
        op_name="scheduled.weekly_digest",
    )
    job_id = job.data[0]["id"] if job.data else None
    logger.info("Weekly digest job created: %s", job_id)
    return {"status": "queued", "job_id": job_id}


@router.post("/workflow-triggers/tick")
async def trigger_workflow_trigger_tick(x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret")):
    """Trigger a scheduler tick for durable workflow triggers."""
    _verify_scheduler(x_scheduler_secret)

    from app.services.workflow_trigger_service import run_workflow_trigger_scheduler_tick

    results = await run_workflow_trigger_scheduler_tick()
    logger.info("Workflow trigger scheduler tick queued %s trigger job(s)", len(results))
    return {"status": "queued", "count": len(results), "results": results}


@router.post("/triage-tick")
async def trigger_email_triage(x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret")):
    """Trigger email triage for all enabled users."""
    _verify_scheduler(x_scheduler_secret)
    from app.services.email_triage_worker import EmailTriageWorker

    client = _get_supabase()
    worker = EmailTriageWorker(supabase_client=client)
    result = await worker.run()
    logger.info("Email triage completed: %s", result)
    return result


@router.post("/department-tick")
async def trigger_department_tick(
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Trigger autonomous department execution cycles."""
    _verify_scheduler(x_scheduler_secret)

    from app.services.department_runner import runner

    results = await runner.tick()
    logger.info("Department tick completed: %s department(s) processed", len(results))
    return {
        "status": "ok",
        "departments_processed": len(results),
        "results": results,
    }


@router.get("/health")
async def scheduler_health():
    """Health check endpoint for Cloud Scheduler."""
    return {"status": "healthy", "service": "pikar-ai-scheduler"}


@router.post("/trigger-job")
async def trigger_custom_job(
    job_type: str,
    priority: int = 5,
    input_data: dict = None,
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Trigger a custom ai_job."""
    _verify_scheduler(x_scheduler_secret)
    client = _get_supabase()
    job = await execute_async(
        client.table("ai_jobs").insert(
            {
                "job_type": job_type,
                "status": "pending",
                "priority": priority,
                "input_data": input_data or {"trigger": "scheduled"},
            }
        ),
        op_name="scheduled.custom_job",
    )
    job_id = job.data[0]["id"] if job.data else None
    logger.info("Custom job created: %s (type: %s)", job_id, job_type)
    return {"status": "queued", "job_id": job_id, "job_type": job_type}

