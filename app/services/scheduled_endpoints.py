# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Cloud Scheduler triggered endpoints.

These endpoints are designed to be triggered by Cloud Scheduler for automated
tasks like daily reports and weekly digests.
"""

import os
import logging
from fastapi import APIRouter, Header, HTTPException
from supabase import Client
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduled", tags=["scheduled"])


def _get_supabase() -> Client:
    """Get Supabase client."""
    return get_service_client()


def _verify_scheduler(x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret")):
    """Verify request comes from Cloud Scheduler."""
    expected = os.environ.get("SCHEDULER_SECRET")
    if expected and x_scheduler_secret != expected:
        logger.warning("Unauthorized scheduler request")
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


@router.post("/daily-report")
async def trigger_daily_report(
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret")
):
    """Trigger daily business report generation.
    
    Creates an ai_job that will be picked up by the worker.
    """
    _verify_scheduler(x_scheduler_secret)
    
    client = _get_supabase()
    job = client.table("ai_jobs").insert({
        "job_type": "daily_report",
        "status": "pending",
        "priority": 10,
        "input_data": {"trigger": "scheduled", "type": "daily"}
    }).execute()
    
    job_id = job.data[0]["id"] if job.data else None
    logger.info(f"Daily report job created: {job_id}")
    
    return {"status": "queued", "job_id": job_id}


@router.post("/weekly-digest")
async def trigger_weekly_digest(
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret")
):
    """Trigger weekly digest email generation.
    
    Creates an ai_job that will be picked up by the worker.
    """
    _verify_scheduler(x_scheduler_secret)
    
    client = _get_supabase()
    job = client.table("ai_jobs").insert({
        "job_type": "weekly_digest",
        "status": "pending",
        "priority": 10,
        "input_data": {"trigger": "scheduled", "type": "weekly"}
    }).execute()
    
    job_id = job.data[0]["id"] if job.data else None
    logger.info(f"Weekly digest job created: {job_id}")
    
    return {"status": "queued", "job_id": job_id}


@router.get("/health")
async def scheduler_health():
    """Health check endpoint for Cloud Scheduler.
    
    Can be used for keep-warm pings.
    """
    return {"status": "healthy", "service": "pikar-ai-scheduler"}


@router.post("/trigger-job")
async def trigger_custom_job(
    job_type: str,
    priority: int = 5,
    input_data: dict = None,
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret")
):
    """Trigger a custom ai_job.
    
    Allows flexible job creation for various scheduled tasks.
    """
    _verify_scheduler(x_scheduler_secret)
    
    client = _get_supabase()
    job = client.table("ai_jobs").insert({
        "job_type": job_type,
        "status": "pending",
        "priority": priority,
        "input_data": input_data or {"trigger": "scheduled"}
    }).execute()
    
    job_id = job.data[0]["id"] if job.data else None
    logger.info(f"Custom job created: {job_id} (type: {job_type})")
    
    return {"status": "queued", "job_id": job_id, "job_type": job_type}
