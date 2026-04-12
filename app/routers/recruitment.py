# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Recruitment Router - Hiring funnel visualization endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recruitment", tags=["Recruitment"])


@router.get("/funnel/{job_id}")
@limiter.limit(get_user_persona_limit)
async def get_hiring_funnel_for_job(
    request: Request,
    job_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Get the hiring funnel data for a specific job.

    Returns stage counts and conversion rates for the given job position.

    Args:
        request: FastAPI request (required by rate limiter).
        job_id: The job posting ID.
        user_id: Authenticated user ID from JWT.

    Returns:
        Funnel data with stages, rejected count, total, and conversion rates.
    """
    from app.services.hiring_funnel_service import HiringFunnelService

    service = HiringFunnelService()
    return await service.get_funnel_for_job(job_id, user_id=user_id)


@router.get("/funnel")
@limiter.limit(get_user_persona_limit)
async def get_hiring_funnel_summary(
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    """Get the hiring funnel summary for all open positions.

    Returns funnel data for every published/draft job.

    Args:
        request: FastAPI request (required by rate limiter).
        user_id: Authenticated user ID from JWT.

    Returns:
        List of job funnel summaries.
    """
    from app.services.hiring_funnel_service import HiringFunnelService

    service = HiringFunnelService()
    return await service.get_funnel_summary(user_id=user_id)
