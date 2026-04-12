# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""TeamOrgService - Team organization structure and org chart.

Manages human team members with reporting relationships and provides
org chart data including open positions from recruitment jobs.
Separate from the AI agent org chart (app/routers/org.py).
"""

from __future__ import annotations

import logging

from app.services.base_service import AdminService, BaseService
from app.services.request_context import get_current_user_id
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


class TeamOrgService(BaseService):
    """Service for managing team organization structure.

    Provides CRUD operations for team members and org chart
    visualization data including open positions from recruitment jobs.
    """

    def __init__(self, user_token: str | None = None):
        """Initialize the team org service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)
        self._members_table = "team_members"
        self._jobs_table = "recruitment_jobs"

    async def add_team_member(
        self,
        name: str,
        email: str | None = None,
        position: str = "",
        department: str | None = None,
        reports_to: str | None = None,
        candidate_id: str | None = None,
        job_id: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Add a new team member record.

        Args:
            name: Team member's full name.
            email: Team member's email address.
            position: Job title / position.
            department: Department name.
            reports_to: UUID of the team member this person reports to.
            candidate_id: UUID of the recruitment candidate (if hired from pipeline).
            job_id: UUID of the recruitment job (if hired from pipeline).
            user_id: Owner user ID for RLS scoping.

        Returns:
            The created team member record as a dictionary.
        """
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise ValueError("Missing user_id for team member creation")

        data: dict = {
            "user_id": effective_user_id,
            "name": name,
            "position": position,
        }
        if email is not None:
            data["email"] = email
        if department is not None:
            data["department"] = department
        if reports_to is not None:
            data["reports_to"] = reports_to
        if candidate_id is not None:
            data["candidate_id"] = candidate_id
        if job_id is not None:
            data["job_id"] = job_id

        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(
            client.table(self._members_table).insert(data)
        )
        if response.data:
            return response.data[0]
        raise ValueError("No data returned from insert team_member")

    async def get_team_members(
        self,
        department: str | None = None,
        user_id: str | None = None,
    ) -> list[dict]:
        """List team members, optionally filtered by department.

        Args:
            department: Filter by department name.
            user_id: Owner user ID for scoping.

        Returns:
            List of team member records.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._members_table).select("*")
        if department:
            query = query.eq("department", department)
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)

        response = await execute_async(query.order("department"))
        return response.data or []

    async def get_org_chart(self, user_id: str | None = None) -> dict:
        """Get complete org chart data with members and open positions.

        Fetches all team members for the user ordered by department,
        then fetches published recruitment jobs that do not have a
        matching team_member record (open positions / vacancies).

        Args:
            user_id: Owner user ID for scoping.

        Returns:
            Dictionary with members, open_positions, and departments lists.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client

        # Fetch all team members
        members_query = client.table(self._members_table).select("*")
        if effective_user_id:
            members_query = members_query.eq("user_id", effective_user_id)
        members_response = await execute_async(members_query.order("department"))
        members = members_response.data or []

        # Fetch all published jobs
        jobs_query = (
            client.table(self._jobs_table)
            .select("id, title, department, status")
            .eq("status", "published")
        )
        if effective_user_id:
            jobs_query = jobs_query.eq("user_id", effective_user_id)
        jobs_response = await execute_async(jobs_query)
        jobs = jobs_response.data or []

        # Filter to open positions (jobs without a team_member match)
        filled_job_ids = {m.get("job_id") for m in members if m.get("job_id")}
        open_positions = [
            {
                "job_id": j["id"],
                "title": j.get("title", ""),
                "department": j.get("department", ""),
                "status": "vacant",
            }
            for j in jobs
            if j["id"] not in filled_job_ids
        ]

        # Collect unique departments
        dept_set: set[str] = set()
        for m in members:
            if m.get("department"):
                dept_set.add(m["department"])
        for p in open_positions:
            if p.get("department"):
                dept_set.add(p["department"])

        return {
            "members": members,
            "open_positions": open_positions,
            "departments": sorted(dept_set),
        }

    async def update_team_member(
        self,
        member_id: str,
        user_id: str | None = None,
        **kwargs: str | None,
    ) -> dict:
        """Update a team member record.

        Args:
            member_id: UUID of the team member to update.
            user_id: Owner user ID for RLS scoping.
            **kwargs: Fields to update (name, email, position, department,
                reports_to, status).

        Returns:
            The updated team member record.
        """
        allowed_fields = {
            "name", "email", "position", "department",
            "reports_to", "status",
        }
        update_data = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
        if not update_data:
            raise ValueError("No valid fields to update")

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table(self._members_table)
            .update(update_data)
            .eq("id", member_id)
        )
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)

        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise ValueError("No data returned from update team_member")
