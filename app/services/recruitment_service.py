"""RecruitmentService - CRUD operations for jobs and candidates.

This service provides Create, Read, Update, Delete operations for job postings
and candidates stored in Supabase with proper RLS authentication.
Used by HRRecruitmentAgent.
"""

from typing import Optional, List
from app.services.base_service import BaseService


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
        data = {
            "title": title,
            "department": department,
            "description": description,
            "requirements": requirements,
            "status": status,
            "user_id": user_id
        }
        response = self.client.table(self._jobs_table).insert(data).execute()
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert job")

    async def get_job(self, job_id: str) -> dict:
        """Retrieve a job by ID."""
        response = (
            self.client.table(self._jobs_table)
            .select("*")
            .eq("id", job_id)
            .single()
            .execute()
        )
        return response.data

    async def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        description: Optional[str] = None,
        requirements: Optional[str] = None
    ) -> dict:
        """Update a job posting."""
        update_data = {}
        if status:
            update_data["status"] = status
        if description:
            update_data["description"] = description
        if requirements:
            update_data["requirements"] = requirements
            
        response = (
            self.client.table(self._jobs_table)
            .update(update_data)
            .eq("id", job_id)
            .execute()
        )
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update job")

    async def list_jobs(self, status: Optional[str] = None, department: Optional[str] = None) -> List[dict]:
        """List job postings with filters."""
        query = self.client.table(self._jobs_table).select("*")
        if status:
            query = query.eq("status", status)
        if department:
            query = query.eq("department", department)
            
        response = query.order("created_at", desc=True).execute()
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
        status: str = "applied"
    ) -> dict:
        """Add a new candidate application."""
        data = {
            "name": name,
            "email": email,
            "job_id": job_id,
            "resume_url": resume_url,
            "status": status,
        }
        response = self.client.table(self._candidates_table).insert(data).execute()
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert candidate")

    async def get_candidate(self, candidate_id: str) -> dict:
        """Retrieve a candidate by ID."""
        response = (
            self.client.table(self._candidates_table)
            .select("*")
            .eq("id", candidate_id)
            .single()
            .execute()
        )
        return response.data

    async def update_candidate_status(self, candidate_id: str, status: str) -> dict:
        """Update a candidate's status (e.g., interviewing, offer, rejected)."""
        response = (
            self.client.table(self._candidates_table)
            .update({"status": status})
            .eq("id", candidate_id)
            .execute()
        )
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update candidate")

    async def list_candidates(self, job_id: Optional[str] = None, status: Optional[str] = None) -> List[dict]:
        """List candidates, optionally filtered by job or status."""
        query = self.client.table(self._candidates_table).select("*")
        if job_id:
            query = query.eq("job_id", job_id)
        if status:
            query = query.eq("status", status)
            
        response = query.order("created_at", desc=True).execute()
        return response.data
