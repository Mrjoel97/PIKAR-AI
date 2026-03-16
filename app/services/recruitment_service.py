"""RecruitmentService - CRUD operations for jobs and candidates.

This service provides Create, Read, Update, Delete operations for job postings
and candidates stored in Supabase with proper RLS authentication.
Used by HRRecruitmentAgent.
"""

from typing import Optional, List
from app.services.base_service import BaseService, AdminService
from app.services.request_context import get_current_user_id
from app.services.supabase_async import execute_async


class RecruitmentService(BaseService):
    """Service for managing recruitment, jobs, and candidates.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: Optional[str] = None):
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
        user_id: Optional[str] = None
    ) -> dict:
        """Create a new job posting."""
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for job creation")

        data = {
            "title": title,
            "department": department,
            "description": description,
            "requirements": requirements,
            "status": status,
            "user_id": effective_user_id
        }
        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(client.table(self._jobs_table).insert(data))
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert job")

    async def get_job(self, job_id: str, user_id: Optional[str] = None) -> dict:
        """Retrieve a job by ID."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table(self._jobs_table)
            .select("*")
            .eq("id", job_id)
        )
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query.single())
        return response.data

    async def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        description: Optional[str] = None,
        requirements: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> dict:
        """Update a job posting."""
        update_data = {}
        if status:
            update_data["status"] = status
        if description:
            update_data["description"] = description
        if requirements:
            update_data["requirements"] = requirements
            
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table(self._jobs_table)
            .update(update_data)
            .eq("id", job_id)
        )
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update job")

    async def list_jobs(
        self,
        status: Optional[str] = None,
        department: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[dict]:
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
        resume_url: Optional[str] = None,
        status: str = "applied",
        user_id: Optional[str] = None
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
        response = await execute_async(client.table(self._candidates_table).insert(data))
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert candidate")

    async def get_candidate(self, candidate_id: str, user_id: Optional[str] = None) -> dict:
        """Retrieve a candidate by ID."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table(self._candidates_table)
            .select("*")
            .eq("id", candidate_id)
        )
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query.single())
        return response.data

    async def update_candidate_status(
        self,
        candidate_id: str,
        status: str,
        user_id: Optional[str] = None
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
        job_id: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[dict]:
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
