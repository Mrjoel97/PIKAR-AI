"""CRM Service - HubSpot integration for lead management."""

from typing import Any, Dict, Optional
import httpx

from app.mcp.config import get_mcp_config
from app.mcp.security.audit_logger import log_mcp_call
from app.mcp.security.external_call_guard import summarize_payload_for_audit


class CRMService:
    """CRM service using HubSpot API."""

    def __init__(self):
        self.config = get_mcp_config()

    async def create_contact(
        self,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        company: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a contact in HubSpot."""
        if not self.config.is_crm_configured():
            return {"success": False, "error": "HubSpot not configured"}

        contact_properties = {"email": email}
        if first_name:
            contact_properties["firstname"] = first_name
        if last_name:
            contact_properties["lastname"] = last_name
        if phone:
            contact_properties["phone"] = phone
        if company:
            contact_properties["company"] = company
        if properties:
            contact_properties.update(properties)

        audit_summary = summarize_payload_for_audit(contact_properties, field_name="crm_contact")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.config.hubspot_base_url}/crm/v3/objects/contacts",
                    headers={
                        "Authorization": f"Bearer {self.config.hubspot_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"properties": contact_properties},
                )

            if response.status_code in (200, 201):
                data = response.json()
                log_mcp_call(
                    tool_name="crm_create_contact",
                    query_sanitized="crm_contact",
                    success=True,
                    response_status="success",
                    metadata={**audit_summary, "status_code": response.status_code},
                )
                return {
                    "success": True,
                    "contact_id": data.get("id"),
                    "properties": data.get("properties"),
                }
            if response.status_code == 409:
                log_mcp_call(
                    tool_name="crm_create_contact",
                    query_sanitized="crm_contact",
                    success=True,
                    response_status="success",
                    metadata={**audit_summary, "status_code": response.status_code, "exists": True},
                )
                return {
                    "success": True,
                    "message": "Contact already exists",
                    "exists": True,
                }

            error_message = f"HubSpot error: {response.status_code}"
            log_mcp_call(
                tool_name="crm_create_contact",
                query_sanitized="crm_contact",
                success=False,
                response_status="error",
                error_message=error_message,
                metadata={**audit_summary, "status_code": response.status_code},
            )
            return {
                "success": False,
                "error": error_message,
                "details": response.text,
            }

        except Exception as e:
            log_mcp_call(
                tool_name="crm_create_contact",
                query_sanitized="crm_contact",
                success=False,
                response_status="error",
                error_message=str(e),
                metadata=audit_summary,
            )
            return {"success": False, "error": str(e)}

    async def create_contact_from_form(
        self,
        form_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create contact from form submission data."""
        email = form_data.get("email") or form_data.get("Email")
        if not email:
            return {"success": False, "error": "Email required for CRM sync"}

        name = form_data.get("name") or form_data.get("Name") or ""
        name_parts = name.split() if name else []
        first_name = name_parts[0] if name_parts else None
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else None

        return await self.create_contact(
            email=email,
            first_name=first_name or form_data.get("first_name") or form_data.get("firstName"),
            last_name=last_name or form_data.get("last_name") or form_data.get("lastName"),
            phone=form_data.get("phone") or form_data.get("Phone"),
            company=form_data.get("company") or form_data.get("Company"),
            properties={
                "message": form_data.get("message") or form_data.get("Message"),
                "hs_lead_status": "NEW",
            },
        )


_crm_service: Optional[CRMService] = None


def _get_crm_service() -> CRMService:
    """Get singleton CRM service."""
    global _crm_service
    if _crm_service is None:
        _crm_service = CRMService()
    return _crm_service


async def create_crm_contact(
    email: str,
    **kwargs,
) -> Dict[str, Any]:
    """Create a CRM contact."""
    service = _get_crm_service()
    return await service.create_contact(email=email, **kwargs)
