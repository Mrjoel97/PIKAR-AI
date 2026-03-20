# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tools for the HR & Recruitment Agent."""


async def create_job(
    title: str, department: str, description: str, requirements: str
) -> dict:
    """Create a new job posting.

    Args:
        title: Job title.
        department: Department name.
        description: Job description.
        requirements: Job requirements.

    Returns:
        Dictionary containing the created job.
    """
    from app.services.recruitment_service import RecruitmentService

    try:
        from app.services.request_context import get_current_user_id

        service = RecruitmentService()
        job = await service.create_job(
            title, department, description, requirements, user_id=get_current_user_id()
        )
        return {"success": True, "job": job}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_job(job_id: str) -> dict:
    """Retrieve a job by ID.

    Args:
        job_id: The unique job ID.

    Returns:
        Dictionary containing the job details.
    """
    from app.services.recruitment_service import RecruitmentService

    try:
        from app.services.request_context import get_current_user_id

        service = RecruitmentService()
        job = await service.get_job(job_id, user_id=get_current_user_id())
        return {"success": True, "job": job}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_job(job_id: str, status: str = None, description: str = None) -> dict:
    """Update a job posting.

    Args:
        job_id: The unique job ID.
        status: New status (draft, published, closed).
        description: New description.

    Returns:
        Dictionary confirming the update.
    """
    from app.services.recruitment_service import RecruitmentService

    try:
        from app.services.request_context import get_current_user_id

        service = RecruitmentService()
        job = await service.update_job(
            job_id,
            status=status,
            description=description,
            user_id=get_current_user_id(),
        )
        return {"success": True, "job": job}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_jobs(status: str = None, department: str = None) -> dict:
    """List job postings with optional filters.

    Args:
        status: Filter by status.
        department: Filter by department.

    Returns:
        Dictionary containing list of jobs.
    """
    from app.services.recruitment_service import RecruitmentService

    try:
        from app.services.request_context import get_current_user_id

        service = RecruitmentService()
        jobs = await service.list_jobs(
            status=status, department=department, user_id=get_current_user_id()
        )
        return {"success": True, "jobs": jobs, "count": len(jobs)}
    except Exception as e:
        return {"success": False, "error": str(e), "jobs": []}


async def add_candidate(
    name: str, email: str, job_id: str, resume_url: str = None
) -> dict:
    """Add a new candidate application.

    Args:
        name: Candidate name.
        email: Candidate email.
        job_id: ID of the job they are applying for.
        resume_url: Optional URL to resume.

    Returns:
        Dictionary containing the new candidate record.
    """
    from app.services.recruitment_service import RecruitmentService

    try:
        from app.services.request_context import get_current_user_id

        service = RecruitmentService()
        candidate = await service.add_candidate(
            name, email, job_id, resume_url=resume_url, user_id=get_current_user_id()
        )
        return {"success": True, "candidate": candidate}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_candidate_status(candidate_id: str, status: str) -> dict:
    """Update a candidate's status.

    Args:
        candidate_id: The unique candidate ID.
        status: New status (applied, interviewing, offer, rejected, hired).

    Returns:
        Dictionary confirming the update.
    """
    from app.services.recruitment_service import RecruitmentService

    try:
        from app.services.request_context import get_current_user_id

        service = RecruitmentService()
        candidate = await service.update_candidate_status(
            candidate_id, status, user_id=get_current_user_id()
        )
        return {"success": True, "candidate": candidate}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_candidates(job_id: str = None, status: str = None) -> dict:
    """List candidates filtered by job or status.

    Args:
        job_id: Filter by job ID.
        status: Filter by candidate status.

    Returns:
        Dictionary containing list of candidates.
    """
    from app.services.recruitment_service import RecruitmentService

    try:
        from app.services.request_context import get_current_user_id

        service = RecruitmentService()
        candidates = await service.list_candidates(
            job_id=job_id, status=status, user_id=get_current_user_id()
        )
        return {"success": True, "candidates": candidates, "count": len(candidates)}
    except Exception as e:
        return {"success": False, "error": str(e), "candidates": []}
