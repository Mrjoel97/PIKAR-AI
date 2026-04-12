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


@router.get("/org-chart/{department}")
@limiter.limit(get_user_persona_limit)
async def get_org_chart_by_department(
    request: Request,
    department: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Get the team org chart filtered by department.

    Returns team members with reporting relationships and open positions
    for the specified department.

    Args:
        request: FastAPI request (required by rate limiter).
        department: Department name to filter by.
        user_id: Authenticated user ID from JWT.

    Returns:
        Org chart data with members, open_positions, and departments.
    """
    from app.services.team_org_service import TeamOrgService

    service = TeamOrgService()
    data = await service.get_org_chart(user_id=user_id)

    # Filter to requested department
    dept_lower = department.lower().strip()
    data["members"] = [
        m for m in data["members"]
        if (m.get("department") or "").lower().strip() == dept_lower
    ]
    data["open_positions"] = [
        p for p in data["open_positions"]
        if (p.get("department") or "").lower().strip() == dept_lower
    ]
    data["departments"] = [
        d for d in data["departments"]
        if d.lower().strip() == dept_lower
    ]
    return data


@router.get("/org-chart")
@limiter.limit(get_user_persona_limit)
async def get_org_chart(
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Get the full team org chart.

    Returns all team members with reporting relationships and open
    positions from published recruitment jobs.

    Args:
        request: FastAPI request (required by rate limiter).
        user_id: Authenticated user ID from JWT.

    Returns:
        Org chart data with members, open_positions, and departments.
    """
    from app.services.team_org_service import TeamOrgService

    service = TeamOrgService()
    return await service.get_org_chart(user_id=user_id)


@router.post("/onboarding/{candidate_id}")
@limiter.limit(get_user_persona_limit)
async def generate_onboarding(
    request: Request,
    candidate_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Generate an onboarding checklist for a hired candidate.

    Creates a department-specific onboarding checklist and registers
    the candidate as a team member in the org chart.

    Args:
        request: FastAPI request (required by rate limiter).
        candidate_id: The UUID of the hired candidate.
        user_id: Authenticated user ID from JWT.

    Returns:
        Onboarding checklist and team member record.
    """
    from app.agents.hr.tools import auto_generate_onboarding

    return await auto_generate_onboarding(candidate_id=candidate_id)
