"""Form Handler Tool - Handle form submissions with storage, email, and CRM.

This module provides form submission handling with:
- Supabase storage for form data
- Email notifications via SendGrid
- CRM integration via HubSpot API
"""

import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from supabase import Client

from app.mcp.config import get_mcp_config
from app.mcp.security.audit_logger import log_mcp_call
from app.mcp.security.external_call_guard import (
    protect_text_payload,
    summarize_payload_for_audit,
)

logger = logging.getLogger(__name__)


class FormHandlerTool:
    """Form submission handler with storage, email, and CRM integration."""

    def __init__(self):
        self.config = get_mcp_config()
        self._client: Optional[Client] = None

    @property
    def client(self) -> Optional[Client]:
        """Get Supabase client."""
        if self._client is None:
            try:
                from app.services.supabase import get_service_client
                self._client = get_service_client()
            except Exception as e:
                logger.warning(f"Failed to get Supabase client: {e}")
        return self._client

    async def store_submission(
        self,
        form_id: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Store form submission in Supabase."""
        if not self.client:
            return {"success": False, "error": "Supabase not configured"}

        try:
            submission_id = str(uuid.uuid4())
            record = {
                "id": submission_id,
                "form_id": form_id,
                "user_id": user_id,
                "data": data,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "email_sent": False,
                "crm_synced": False,
            }
            result = self.client.table("form_submissions").insert(record).execute()
            return {"success": True, "submission_id": submission_id, "data": result.data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def send_email_notification(
        self,
        submission_id: str,
        form_id: str,
        data: Dict[str, Any],
        recipient_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send email notification for form submission."""
        if not self.config.is_email_configured():
            return {"success": False, "error": "Email service not configured"}

        try:
            import httpx

            fields_html = "<br>".join([f"<b>{k}:</b> {v}" for k, v in data.items()])

            email_data = {
                "personalizations": [{
                    "to": [{"email": recipient_email or self.config.sendgrid_from_email}]
                }],
                "from": {"email": self.config.sendgrid_from_email},
                "subject": f"New Form Submission - {form_id}",
                "content": [{
                    "type": "text/html",
                    "value": f"<h2>New Submission</h2><p>Form: {form_id}</p><p>ID: {submission_id}</p><hr>{fields_html}"
                }]
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={
                        "Authorization": f"Bearer {self.config.sendgrid_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=email_data
                )

                if response.status_code in (200, 202):
                    return {"success": True, "message": "Email sent"}
                return {"success": False, "error": f"SendGrid error: {response.status_code}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def sync_to_crm(
        self,
        submission_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Sync form submission to HubSpot CRM."""
        if not self.config.is_crm_configured():
            return {"success": False, "error": "CRM not configured"}

        try:
            import httpx

            contact_data = {
                "properties": {
                    "email": data.get("email"),
                    "firstname": data.get("name", "").split()[0] if data.get("name") else None,
                    "lastname": " ".join(data.get("name", "").split()[1:]) if data.get("name") else None,
                    "phone": data.get("phone"),
                    "company": data.get("company"),
                    "message": data.get("message"),
                    "hs_lead_status": "NEW",
                }
            }
            contact_data["properties"] = {k: v for k, v in contact_data["properties"].items() if v}

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.hubspot_base_url}/crm/v3/objects/contacts",
                    headers={
                        "Authorization": f"Bearer {self.config.hubspot_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=contact_data
                )

                if response.status_code in (200, 201):
                    return {"success": True, "contact_id": response.json().get("id")}
                return {"success": False, "error": f"HubSpot error: {response.status_code}"}

        except Exception as e:
            return {"success": False, "error": str(e)}


_form_tool: Optional[FormHandlerTool] = None


def _get_form_tool() -> FormHandlerTool:
    """Get the singleton form handler instance."""
    global _form_tool
    if _form_tool is None:
        _form_tool = FormHandlerTool()
    return _form_tool


async def handle_form_submission(
    form_id: str,
    data: Dict[str, Any],
    send_email: bool = True,
    sync_crm: bool = True,
    recipient_email: Optional[str] = None,
    agent_name: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle a form submission with storage, email, and CRM sync."""
    start_time = time.time()
    tool = _get_form_tool()
    form_guard = protect_text_payload(form_id, field_name="form_id", redact_for_outbound=False)
    submission_guard = summarize_payload_for_audit(data, field_name="submission")

    store_result = await tool.store_submission(form_id, data, user_id)

    if not store_result.get("success"):
        log_mcp_call(
            tool_name="handle_form_submission",
            query_sanitized=f"form_id={form_guard.audit_value}",
            success=False,
            error_message=store_result.get("error"),
            agent_name=agent_name,
            user_id=user_id,
            metadata={
                "form_guard": form_guard.metadata,
                "submission_guard": submission_guard,
            },
        )
        return store_result

    submission_id = store_result.get("submission_id")
    result = {
        "success": True,
        "submission_id": submission_id,
        "form_id": form_id,
        "stored": True,
        "email_sent": False,
        "crm_synced": False,
    }

    if send_email:
        email_result = await tool.send_email_notification(
            submission_id, form_id, data, recipient_email
        )
        result["email_sent"] = email_result.get("success", False)
        result["email_error"] = email_result.get("error")

    if sync_crm:
        crm_result = await tool.sync_to_crm(submission_id, data)
        result["crm_synced"] = crm_result.get("success", False)
        result["crm_contact_id"] = crm_result.get("contact_id")
        result["crm_error"] = crm_result.get("error")

    duration_ms = int((time.time() - start_time) * 1000)

    log_mcp_call(
        tool_name="handle_form_submission",
        query_sanitized=f"form_id={form_guard.audit_value}",
        success=True,
        agent_name=agent_name,
        user_id=user_id,
        duration_ms=duration_ms,
        metadata={
            "email_sent": result["email_sent"],
            "crm_synced": result["crm_synced"],
            "form_guard": form_guard.metadata,
            "submission_guard": submission_guard,
        },
    )

    return result


async def get_form_submissions(
    form_id: str,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """Retrieve form submissions from Supabase."""
    tool = _get_form_tool()

    if not tool.client:
        return {"success": False, "error": "Supabase not configured"}

    try:
        result = tool.client.table("form_submissions")\
            .select("*")\
            .eq("form_id", form_id)\
            .order("submitted_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()

        return {
            "success": True,
            "form_id": form_id,
            "submissions": result.data,
            "count": len(result.data),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
