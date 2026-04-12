# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tools for the Compliance & Risk Agent."""

import json
import logging

from google import genai

logger = logging.getLogger(__name__)

# Valid legal document types for generate_legal_document
VALID_DOC_TYPES = ("privacy_policy", "terms_of_service", "refund_policy")


async def create_audit(
    title: str, scope: str, auditor: str, scheduled_date: str
) -> dict:
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
        from app.services.request_context import get_current_user_id

        service = ComplianceService()
        audit = await service.create_audit(
            title, scope, auditor, scheduled_date, user_id=get_current_user_id()
        )
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
        from app.services.request_context import get_current_user_id

        service = ComplianceService()
        audit = await service.get_audit(audit_id, user_id=get_current_user_id())
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
        from app.services.request_context import get_current_user_id

        service = ComplianceService()
        audit = await service.update_audit(
            audit_id, status=status, findings=findings, user_id=get_current_user_id()
        )
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
        from app.services.request_context import get_current_user_id

        service = ComplianceService()
        audits = await service.list_audits(status=status, user_id=get_current_user_id())
        return {"success": True, "audits": audits, "count": len(audits)}
    except Exception as e:
        return {"success": False, "error": str(e), "audits": []}


async def create_risk(
    title: str, description: str, severity: str, mitigation_plan: str
) -> dict:
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
        from app.services.request_context import get_current_user_id

        service = ComplianceService()
        risk = await service.create_risk(
            title, description, severity, mitigation_plan, user_id=get_current_user_id()
        )
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
        from app.services.request_context import get_current_user_id

        service = ComplianceService()
        risk = await service.get_risk(risk_id, user_id=get_current_user_id())
        return {"success": True, "risk": risk}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_risk(
    risk_id: str, status: str = None, severity: str = None, mitigation_plan: str = None
) -> dict:
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
        from app.services.request_context import get_current_user_id

        service = ComplianceService()
        risk = await service.update_risk(
            risk_id,
            status=status,
            severity=severity,
            mitigation_plan=mitigation_plan,
            user_id=get_current_user_id(),
        )
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
        from app.services.request_context import get_current_user_id

        service = ComplianceService()
        risks = await service.list_risks(
            severity=severity, status=status, user_id=get_current_user_id()
        )
        return {"success": True, "risks": risks, "count": len(risks)}
    except Exception as e:
        return {"success": False, "error": str(e), "risks": []}


# ===========================================================================
# Legal Document Generation & Contract Clause Explanation
# ===========================================================================

_LEGAL_DISCLAIMER = "This document was AI-generated and should be reviewed by qualified legal counsel before use."


async def generate_legal_document(
    doc_type: str,
    business_name: str,
    business_description: str,
    jurisdiction: str = "United States",
    additional_context: str = "",
) -> dict:
    """Generate a legal document (privacy policy, terms of service, or refund policy).

    Uses the Gemini LLM to produce a complete, professional legal document
    customized to the user's business and jurisdiction.

    Args:
        doc_type: Type of document. One of: privacy_policy, terms_of_service, refund_policy.
        business_name: Name of the business.
        business_description: Brief description of the business and its activities.
        jurisdiction: Legal jurisdiction (e.g., "United States", "European Union").
        additional_context: Optional extra context (industry-specific requirements, etc.).

    Returns:
        Dictionary with generated document content or error.
    """
    if doc_type not in VALID_DOC_TYPES:
        return {
            "success": False,
            "error": (
                f"Invalid doc_type '{doc_type}'. "
                f"Must be one of: {', '.join(VALID_DOC_TYPES)}"
            ),
        }

    doc_type_label = doc_type.replace("_", " ").title()

    prompt = (
        f"Generate a complete, professional {doc_type_label} for the following business.\n\n"
        f"Business Name: {business_name}\n"
        f"Business Description: {business_description}\n"
        f"Jurisdiction: {jurisdiction}\n"
    )
    if additional_context:
        prompt += f"Additional Context: {additional_context}\n"

    prompt += (
        f"\nRequirements:\n"
        f"- Produce a complete {doc_type_label} appropriate for {jurisdiction}\n"
        f"- Include all standard sections expected in a {doc_type_label}\n"
        f"- Use clear, professional language\n"
        f"- Customize the content to the specific business described\n"
        f"- Include jurisdiction-appropriate boilerplate and legal clauses\n"
        f"- Add a note at the end that this document is AI-generated and should be reviewed by legal counsel\n"
    )

    try:
        from app.agents.shared import GEMINI_AGENT_MODEL_FALLBACK

        client = genai.Client()
        response = await client.aio.models.generate_content(
            model=GEMINI_AGENT_MODEL_FALLBACK,
            contents=prompt,
        )
        content = response.text

        return {
            "success": True,
            "document_type": doc_type,
            "business_name": business_name,
            "jurisdiction": jurisdiction,
            "content": content,
            "disclaimer": _LEGAL_DISCLAIMER,
        }
    except Exception as e:
        logger.exception("generate_legal_document failed: %s", e)
        return {"success": False, "error": str(e)}


async def explain_contract_clause(
    clause_text: str,
    contract_type: str = "general",
) -> dict:
    """Explain a contract clause in plain English with risk assessment.

    Analyzes a contract clause and returns a structured explanation
    including implications, risk level, and items to watch for.

    Args:
        clause_text: The contract clause text to analyze.
        contract_type: Type of contract (e.g., "general", "service_agreement", "nda").

    Returns:
        Dictionary with explanation, implications, risk level, and watch items.
    """
    if not clause_text or not clause_text.strip():
        return {
            "success": False,
            "error": "Clause text is empty. Please provide a contract clause to analyze.",
        }

    clause_text = clause_text.strip()

    prompt = (
        "Analyze the following contract clause and return a JSON object with these fields:\n"
        '- "explanation": A plain-English explanation of what this clause means in everyday language.\n'
        '- "implications": A list of strings describing what obligations/rights this creates.\n'
        '- "risk_level": One of "low", "medium", or "high" with justification embedded in the explanation.\n'
        '- "watch_items": A list of strings noting red flags, negotiation points, or unusual/non-standard terms.\n\n'
        f"Contract type: {contract_type}\n\n"
        f"Clause:\n{clause_text}\n\n"
        "Respond with ONLY valid JSON, no markdown code fences."
    )

    try:
        from app.agents.shared import GEMINI_AGENT_MODEL_FALLBACK

        client = genai.Client()
        response = await client.aio.models.generate_content(
            model=GEMINI_AGENT_MODEL_FALLBACK,
            contents=prompt,
        )

        raw = response.text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3].strip()

        parsed = json.loads(raw)

        # Truncate clause_text for response readability
        truncated_clause = (
            clause_text[:500] + "..." if len(clause_text) > 500 else clause_text
        )

        return {
            "success": True,
            "clause_text": truncated_clause,
            "explanation": parsed.get("explanation", ""),
            "implications": parsed.get("implications", []),
            "risk_level": parsed.get("risk_level", "medium"),
            "watch_items": parsed.get("watch_items", []),
        }
    except Exception as e:
        logger.exception("explain_contract_clause failed: %s", e)
        return {"success": False, "error": str(e)}
