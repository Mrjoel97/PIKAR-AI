"""ComplianceService - CRUD operations for audits and risk assessments.

This service provides management for compliance audits and risk items,
stored in Supabase with proper RLS authentication.
Used by ComplianceRiskAgent.
"""

from typing import Optional, List
from app.services.base_service import BaseService


class ComplianceService(BaseService):
    """Service for managing compliance audits and risk assessments.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: Optional[str] = None):
        """Initialize the compliance service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)
        self._audits_table = "compliance_audits"
        self._risks_table = "compliance_risks"

    # ==========================
    # Audit Operations
    # ==========================

    async def create_audit(
        self,
        title: str,
        scope: str,
        auditor: str,
        scheduled_date: str,
        status: str = "scheduled"
    ) -> dict:
        """Create a new compliance audit."""
        data = {
            "title": title,
            "scope": scope,
            "auditor": auditor,
            "scheduled_date": scheduled_date,
            "status": status,
        }
        response = self.client.table(self._audits_table).insert(data).execute()
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert audit")

    async def get_audit(self, audit_id: str) -> dict:
        """Retrieve an audit by ID."""
        response = (
            self.client.table(self._audits_table)
            .select("*")
            .eq("id", audit_id)
            .single()
            .execute()
        )
        return response.data

    async def update_audit(
        self,
        audit_id: str,
        status: Optional[str] = None,
        findings: Optional[str] = None
    ) -> dict:
        """Update an audit record."""
        update_data = {}
        if status:
            update_data["status"] = status
        if findings:
            update_data["findings"] = findings
            
        response = (
            self.client.table(self._audits_table)
            .update(update_data)
            .eq("id", audit_id)
            .execute()
        )
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update audit")

    async def list_audits(self, status: Optional[str] = None) -> List[dict]:
        """List audits with optional filters."""
        query = self.client.table(self._audits_table).select("*")
        if status:
            query = query.eq("status", status)
            
        response = query.order("scheduled_date", desc=True).execute()
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
        owner: Optional[str] = None
    ) -> dict:
        """Register a new risk item."""
        data = {
            "title": title,
            "description": description,
            "severity": severity,
            "mitigation_plan": mitigation_plan,
            "owner": owner,
            "status": "active"
        }
        response = self.client.table(self._risks_table).insert(data).execute()
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert risk")

    async def get_risk(self, risk_id: str) -> dict:
        """Retrieve a risk by ID."""
        response = (
            self.client.table(self._risks_table)
            .select("*")
            .eq("id", risk_id)
            .single()
            .execute()
        )
        return response.data

    async def update_risk(
        self,
        risk_id: str,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        mitigation_plan: Optional[str] = None
    ) -> dict:
        """Update a risk record."""
        update_data = {}
        if status:
            update_data["status"] = status
        if severity:
            update_data["severity"] = severity
        if mitigation_plan:
            update_data["mitigation_plan"] = mitigation_plan
            
        response = (
            self.client.table(self._risks_table)
            .update(update_data)
            .eq("id", risk_id)
            .execute()
        )
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update risk")

    async def list_risks(self, severity: Optional[str] = None, status: Optional[str] = "active") -> List[dict]:
        """List and query risk items."""
        query = self.client.table(self._risks_table).select("*")
        if severity:
            query = query.eq("severity", severity)
        if status:
            query = query.eq("status", status)
            
        response = query.order("created_at", desc=True).execute()
        return response.data
