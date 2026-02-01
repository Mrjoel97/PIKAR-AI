# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tools for the Compliance & Risk Agent."""


async def create_audit(title: str, scope: str, auditor: str, scheduled_date: str) -> dict:
    """Create a new compliance audit.
    
    Args:
        title: Audit title.
        scope: Audit scope.
        auditor: Auditor name.
        scheduled_date: Scheduled date (YYYY-MM-DD).
        
    Returns:
        Dictionary containing the created audit.
    """
    from app.services.compliance_service import ComplianceService
    
    try:
        service = ComplianceService()
        audit = await service.create_audit(title, scope, auditor, scheduled_date)
        return {"success": True, "audit": audit}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_audit(audit_id: str) -> dict:
    """Retrieve an audit by ID.
    
    Args:
        audit_id: The unique audit ID.
        
    Returns:
        Dictionary containing the audit details.
    """
    from app.services.compliance_service import ComplianceService
    
    try:
        service = ComplianceService()
        audit = await service.get_audit(audit_id)
        return {"success": True, "audit": audit}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_audit(audit_id: str, status: str = None, findings: str = None) -> dict:
    """Update an audit record.
    
    Args:
        audit_id: The unique audit ID.
        status: New status (scheduled, in_progress, completed, failed).
        findings: Audit findings description.
        
    Returns:
        Dictionary confirming the update.
    """
    from app.services.compliance_service import ComplianceService
    
    try:
        service = ComplianceService()
        audit = await service.update_audit(audit_id, status=status, findings=findings)
        return {"success": True, "audit": audit}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_audits(status: str = None) -> dict:
    """List audits with optional filters.
    
    Args:
        status: Filter by status.
        
    Returns:
        Dictionary containing list of audits.
    """
    from app.services.compliance_service import ComplianceService
    
    try:
        service = ComplianceService()
        audits = await service.list_audits(status=status)
        return {"success": True, "audits": audits, "count": len(audits)}
    except Exception as e:
        return {"success": False, "error": str(e), "audits": []}


async def create_risk(title: str, description: str, severity: str, mitigation_plan: str) -> dict:
    """Register a new risk item.
    
    Args:
        title: Risk title.
        description: Description of the risk.
        severity: Risk severity (low, medium, high, critical).
        mitigation_plan: Plan to mitigate the risk.
        
    Returns:
        Dictionary containing the created risk.
    """
    from app.services.compliance_service import ComplianceService
    
    try:
        service = ComplianceService()
        risk = await service.create_risk(title, description, severity, mitigation_plan)
        return {"success": True, "risk": risk}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_risk(risk_id: str) -> dict:
    """Retrieve a risk by ID.
    
    Args:
        risk_id: The unique risk ID.
        
    Returns:
        Dictionary containing the risk details.
    """
    from app.services.compliance_service import ComplianceService
    
    try:
        service = ComplianceService()
        risk = await service.get_risk(risk_id)
        return {"success": True, "risk": risk}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_risk(risk_id: str, status: str = None, severity: str = None, mitigation_plan: str = None) -> dict:
    """Update a risk record.
    
    Args:
        risk_id: The unique risk ID.
        status: New status (active, mitigated, accepted).
        severity: New severity.
        mitigation_plan: Update mitigation plan.
        
    Returns:
        Dictionary confirming the update.
    """
    from app.services.compliance_service import ComplianceService
    
    try:
        service = ComplianceService()
        risk = await service.update_risk(risk_id, status=status, severity=severity, mitigation_plan=mitigation_plan)
        return {"success": True, "risk": risk}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_risks(severity: str = None, status: str = "active") -> dict:
    """List risk items with optional filters.
    
    Args:
        severity: Filter by severity.
        status: Filter by status (default: active).
        
    Returns:
        Dictionary containing list of risks.
    """
    from app.services.compliance_service import ComplianceService
    
    try:
        service = ComplianceService()
        risks = await service.list_risks(severity=severity, status=status)
        return {"success": True, "risks": risks, "count": len(risks)}
    except Exception as e:
        return {"success": False, "error": str(e), "risks": []}
