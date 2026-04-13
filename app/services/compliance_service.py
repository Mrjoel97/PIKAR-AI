# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""ComplianceService - CRUD operations for audits, risk assessments, and deadlines.

This service provides management for compliance audits, risk items, and
compliance calendar deadlines, stored in Supabase with proper RLS
authentication.  Used by ComplianceRiskAgent.
"""

from app.services.base_service import AdminService, BaseService
from app.services.request_context import get_current_user_id
from app.services.supabase_async import execute_async


class ComplianceService(BaseService):
    """Service for managing compliance audits and risk assessments.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    # Valid deadline categories
    VALID_DEADLINE_CATEGORIES = (
        "sox",
        "gdpr",
        "hipaa",
        "license",
        "policy_review",
        "custom",
    )

    def __init__(self, user_token: str | None = None):
        """Initialize the compliance service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)
        self._audits_table = "compliance_audits"
        self._risks_table = "compliance_risks"
        self._deadlines_table = "compliance_deadlines"

    # ==========================
    # Audit Operations
    # ==========================

    async def create_audit(
        self,
        title: str,
        scope: str,
        auditor: str,
        scheduled_date: str,
        status: str = "scheduled",
        user_id: str | None = None,
    ) -> dict:
        """Create a new compliance audit."""
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for audit creation")
        data = {
            "title": title,
            "scope": scope,
            "auditor": auditor,
            "scheduled_date": scheduled_date,
            "status": status,
            "user_id": effective_user_id,
        }
        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(client.table(self._audits_table).insert(data))
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert audit")

    async def get_audit(self, audit_id: str, user_id: str | None = None) -> dict:
        """Retrieve an audit by ID."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._audits_table).select("*").eq("id", audit_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query.single())
        return response.data

    async def update_audit(
        self,
        audit_id: str,
        status: str | None = None,
        findings: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Update an audit record."""
        update_data = {}
        if status:
            update_data["status"] = status
        if findings:
            update_data["findings"] = findings

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._audits_table).update(update_data).eq("id", audit_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update audit")

    async def list_audits(
        self, status: str | None = None, user_id: str | None = None
    ) -> list[dict]:
        """List audits with optional filters."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._audits_table).select("*")
        if status:
            query = query.eq("status", status)
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)

        response = await execute_async(query.order("scheduled_date", desc=True))
        return response.data

    # ==========================
    # Risk Operations
    # ==========================

    async def create_risk(
        self,
        title: str,
        description: str,
        severity: str,
        mitigation_plan: str,
        owner: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Register a new risk item."""
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for risk creation")
        data = {
            "title": title,
            "description": description,
            "severity": severity,
            "mitigation_plan": mitigation_plan,
            "owner": owner,
            "status": "active",
            "user_id": effective_user_id,
        }
        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(client.table(self._risks_table).insert(data))
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert risk")

    async def get_risk(self, risk_id: str, user_id: str | None = None) -> dict:
        """Retrieve a risk by ID."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._risks_table).select("*").eq("id", risk_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query.single())
        return response.data

    async def update_risk(
        self,
        risk_id: str,
        status: str | None = None,
        severity: str | None = None,
        mitigation_plan: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Update a risk record."""
        update_data = {}
        if status:
            update_data["status"] = status
        if severity:
            update_data["severity"] = severity
        if mitigation_plan:
            update_data["mitigation_plan"] = mitigation_plan

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._risks_table).update(update_data).eq("id", risk_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update risk")

    async def list_risks(
        self,
        severity: str | None = None,
        status: str | None = "active",
        user_id: str | None = None,
    ) -> list[dict]:
        """List and query risk items."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._risks_table).select("*")
        if severity:
            query = query.eq("severity", severity)
        if status:
            query = query.eq("status", status)
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)

        response = await execute_async(query.order("created_at", desc=True))
        return response.data

    # ==========================
    # Deadline Operations
    # ==========================

    async def create_deadline(
        self,
        title: str,
        due_date: str,
        category: str = "custom",
        description: str | None = None,
        recurrence: str = "none",
        reminder_days_before: int = 14,
        user_id: str | None = None,
    ) -> dict:
        """Create a new compliance deadline.

        Args:
            title: Deadline title (e.g. 'GDPR Annual Review').
            due_date: Due date in YYYY-MM-DD format.
            category: One of sox, gdpr, hipaa, license, policy_review, custom.
            description: Optional description of the deadline.
            recurrence: One of none, monthly, quarterly, annual.
            reminder_days_before: Days before due date to send reminder.
            user_id: User ID override.

        Returns:
            The inserted deadline row.

        Raises:
            ValueError: If category is not in the valid set.
            Exception: If user_id cannot be resolved.
        """
        if category not in self.VALID_DEADLINE_CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. "
                f"Must be one of: {', '.join(self.VALID_DEADLINE_CATEGORIES)}"
            )
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for deadline creation")
        data = {
            "title": title,
            "due_date": due_date,
            "category": category,
            "description": description or "",
            "recurrence": recurrence,
            "reminder_days_before": reminder_days_before,
            "status": "upcoming",
            "user_id": effective_user_id,
        }
        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(
            client.table(self._deadlines_table).insert(data)
        )
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert deadline")

    async def get_deadline(
        self, deadline_id: str, user_id: str | None = None
    ) -> dict:
        """Retrieve a deadline by ID.

        Args:
            deadline_id: The unique deadline ID.
            user_id: User ID override.

        Returns:
            The deadline row.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table(self._deadlines_table)
            .select("*")
            .eq("id", deadline_id)
        )
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query.single())
        return response.data

    async def update_deadline(
        self,
        deadline_id: str,
        status: str | None = None,
        due_date: str | None = None,
        title: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Update a deadline record.

        Args:
            deadline_id: The unique deadline ID.
            status: New status (upcoming, completed, overdue, snoozed).
            due_date: New due date (YYYY-MM-DD).
            title: New title.
            user_id: User ID override.

        Returns:
            The updated deadline row.
        """
        update_data: dict = {}
        if status:
            update_data["status"] = status
        if due_date:
            update_data["due_date"] = due_date
        if title:
            update_data["title"] = title

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table(self._deadlines_table)
            .update(update_data)
            .eq("id", deadline_id)
        )
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update deadline")

    async def list_deadlines(
        self,
        status: str | None = None,
        category: str | None = None,
        upcoming_only: bool = False,
        user_id: str | None = None,
    ) -> list[dict]:
        """List compliance deadlines with optional filters.

        Args:
            status: Filter by status (upcoming, completed, overdue, snoozed).
            category: Filter by category (sox, gdpr, hipaa, etc.).
            upcoming_only: If True, only return deadlines with due_date >= today.
            user_id: User ID override.

        Returns:
            List of deadline rows ordered by due_date ascending.
        """
        from datetime import date

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._deadlines_table).select("*")
        if status:
            query = query.eq("status", status)
        if category:
            query = query.eq("category", category)
        if upcoming_only:
            query = query.gte("due_date", date.today().isoformat())
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)

        response = await execute_async(query.order("due_date", desc=False))
        return response.data
