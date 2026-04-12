# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""RecruitmentService - CRUD operations for jobs and candidates.

This service provides Create, Read, Update, Delete operations for job postings
and candidates stored in Supabase with proper RLS authentication.
Used by HRRecruitmentAgent.
"""

from app.services.base_service import AdminService, BaseService
from app.services.request_context import get_current_user_id
from app.services.supabase_async import execute_async


class RecruitmentService(BaseService):
    """Service for managing recruitment, jobs, and candidates.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: str | None = None):
        """Initialize the recruitment service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)
        self._jobs_table = "recruitment_jobs"
        self._candidates_table = "recruitment_candidates"

    # ==========================
    # Job Operations
    # ==========================

    async def create_job(
        self,
        title: str,
        department: str,
        description: str,
        requirements: str,
        status: str = "draft",
        user_id: str | None = None,
        salary_min: int | None = None,
        salary_max: int | None = None,
        seniority_level: str | None = None,
        responsibilities: str | None = None,
    ) -> dict:
        """Create a new job posting.

        Args:
            title: Job title.
            department: Department name.
            description: Job description text.
            requirements: Job requirements text.
            status: Job status (default: draft).
            user_id: Owner user ID.
            salary_min: Minimum salary range from compensation benchmarking.
            salary_max: Maximum salary range from compensation benchmarking.
            seniority_level: Seniority tier (junior, mid, senior, lead, executive).
            responsibilities: Structured responsibilities section.
        """
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for job creation")

        data = {
            "title": title,
            "department": department,
            "description": description,
            "requirements": requirements,
            "status": status,
            "user_id": effective_user_id,
        }
        if salary_min is not None:
            data["salary_min"] = salary_min
        if salary_max is not None:
            data["salary_max"] = salary_max
        if seniority_level is not None:
            data["seniority_level"] = seniority_level
        if responsibilities is not None:
            data["responsibilities"] = responsibilities
        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(client.table(self._jobs_table).insert(data))
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert job")

    async def get_job(self, job_id: str, user_id: str | None = None) -> dict:
        """Retrieve a job by ID."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._jobs_table).select("*").eq("id", job_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query.single())
        return response.data

    async def update_job(
        self,
        job_id: str,
        status: str | None = None,
        description: str | None = None,
        requirements: str | None = None,
        user_id: str | None = None,
        salary_min: int | None = None,
        salary_max: int | None = None,
        seniority_level: str | None = None,
        responsibilities: str | None = None,
    ) -> dict:
        """Update a job posting.

        Args:
            job_id: The unique job ID.
            status: New status (draft, published, closed).
            description: New description.
            requirements: New requirements.
            user_id: Owner user ID.
            salary_min: Minimum salary range.
            salary_max: Maximum salary range.
            seniority_level: Seniority tier.
            responsibilities: Structured responsibilities section.
        """
        update_data = {}
        if status:
            update_data["status"] = status
        if description:
            update_data["description"] = description
        if requirements:
            update_data["requirements"] = requirements
        if salary_min is not None:
            update_data["salary_min"] = salary_min
        if salary_max is not None:
            update_data["salary_max"] = salary_max
        if seniority_level is not None:
            update_data["seniority_level"] = seniority_level
        if responsibilities is not None:
            update_data["responsibilities"] = responsibilities

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._jobs_table).update(update_data).eq("id", job_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update job")

    async def list_jobs(
        self,
        status: str | None = None,
        department: str | None = None,
        user_id: str | None = None,
    ) -> list[dict]:
        """List job postings with filters."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._jobs_table).select("*")
        if status:
            query = query.eq("status", status)
        if department:
            query = query.eq("department", department)
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)

        response = await execute_async(query.order("created_at", desc=True))
        return response.data

    # ==========================
    # Candidate Operations
    # ==========================

    async def add_candidate(
        self,
        name: str,
        email: str,
        job_id: str,
        resume_url: str | None = None,
        status: str = "applied",
        user_id: str | None = None,
    ) -> dict:
        """Add a new candidate application."""
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for candidate creation")
        data = {
            "name": name,
            "email": email,
            "job_id": job_id,
            "resume_url": resume_url,
            "status": status,
            "user_id": effective_user_id,
        }
        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(
            client.table(self._candidates_table).insert(data)
        )
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert candidate")

    async def get_candidate(
        self, candidate_id: str, user_id: str | None = None
    ) -> dict:
        """Retrieve a candidate by ID."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._candidates_table).select("*").eq("id", candidate_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query.single())
        return response.data

    async def update_candidate_status(
        self, candidate_id: str, status: str, user_id: str | None = None
    ) -> dict:
        """Update a candidate's status (e.g., interviewing, offer, rejected)."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table(self._candidates_table)
            .update({"status": status})
            .eq("id", candidate_id)
        )
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update candidate")

    async def list_candidates(
        self,
        job_id: str | None = None,
        status: str | None = None,
        user_id: str | None = None,
    ) -> list[dict]:
        """List candidates, optionally filtered by job or status."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._candidates_table).select("*")
        if job_id:
            query = query.eq("job_id", job_id)
        if status:
            query = query.eq("status", status)
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)

        response = await execute_async(query.order("created_at", desc=True))
        return response.data
