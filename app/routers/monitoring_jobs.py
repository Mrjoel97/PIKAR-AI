# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""REST endpoints for monitoring job CRUD.

Provides frontend-consumable endpoints for creating, listing, updating,
and deleting user monitoring jobs. All endpoints require authentication.
"""


import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.routers.onboarding import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring-jobs", tags=["Monitoring Jobs"])


# ============================================================================
# Request/Response Models
# ============================================================================


class CreateMonitoringJobRequest(BaseModel):
    """Request body for creating a monitoring job."""

    topic: str
    monitoring_type: str = "competitor"
    importance: str = "normal"
    keyword_triggers: list[str] | None = None
    pinned_urls: list[str] | None = None
    excluded_urls: list[str] | None = None


class UpdateMonitoringJobRequest(BaseModel):
    """Request body for updating a monitoring job (all fields optional)."""

    is_active: bool | None = None
    importance: str | None = None
    keyword_triggers: list[str] | None = None
    pinned_urls: list[str] | None = None
    excluded_urls: list[str] | None = None


# ============================================================================
# Endpoints
# ============================================================================


@router.get("")
async def list_monitoring_jobs(
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """List the authenticated user's monitoring jobs.

    Returns:
        Dict with jobs list and count.
    """
    from app.services.monitoring_job_service import MonitoringJobService

    service = MonitoringJobService()
    jobs = await service.list_jobs(user_id=user_id)
    return {"jobs": jobs, "count": len(jobs)}


@router.post("")
async def create_monitoring_job(
    body: CreateMonitoringJobRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Create a new monitoring job for the authenticated user.

    Args:
        body: Job configuration — topic, type, importance, triggers, URLs.

    Returns:
        Created job dict.
    """
    from app.services.monitoring_job_service import MonitoringJobService

    service = MonitoringJobService()
    job = await service.create_job(
        user_id=user_id,
        topic=body.topic,
        monitoring_type=body.monitoring_type,
        importance=body.importance,
        keyword_triggers=body.keyword_triggers,
        pinned_urls=body.pinned_urls,
        excluded_urls=body.excluded_urls,
    )
    return {"job": job}


@router.patch("/{job_id}")
async def update_monitoring_job(
    job_id: str,
    body: UpdateMonitoringJobRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Update a monitoring job owned by the authenticated user.

    Args:
        job_id: UUID of the monitoring job.
        body: Fields to update (all optional).

    Returns:
        Updated job dict.
    """
    from app.services.monitoring_job_service import MonitoringJobService

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    service = MonitoringJobService()
    job = await service.update_job(job_id=job_id, user_id=user_id, **updates)
    if not job:
        raise HTTPException(status_code=404, detail="Monitoring job not found")
    return {"job": job}


@router.delete("/{job_id}")
async def delete_monitoring_job(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Delete a monitoring job owned by the authenticated user.

    Args:
        job_id: UUID of the monitoring job to delete.

    Returns:
        Deletion confirmation.
    """
    from app.services.monitoring_job_service import MonitoringJobService

    service = MonitoringJobService()
    result = await service.delete_job(job_id=job_id, user_id=user_id)
    return result
