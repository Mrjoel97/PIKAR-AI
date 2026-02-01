"""Email Service - Email notifications via SendGrid.

This module provides email notification capabilities using SendGrid API.
"""

from typing import Any, Dict, List, Optional
import httpx

from app.mcp.config import get_mcp_config


class EmailService:
    """Email service using SendGrid API."""
    
    def __init__(self):
        self.config = get_mcp_config()
        self.api_url = "https://api.sendgrid.com/v3/mail/send"
    
    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an email using SendGrid.
        
        Args:
            to_emails: List of recipient email addresses.
            subject: Email subject line.
            html_content: HTML content of the email.
            text_content: Plain text fallback (optional).
            from_email: Sender email (default from config).
            reply_to: Reply-to email address.
            
        Returns:
            Result dictionary with success status.
        """
        if not self.config.is_email_configured():
            return {"success": False, "error": "SendGrid not configured"}
        
        try:
            personalizations = [{"to": [{"email": email} for email in to_emails]}]
            
            content = [{"type": "text/html", "value": html_content}]
            if text_content:
                content.insert(0, {"type": "text/plain", "value": text_content})
            
            email_data = {
                "personalizations": personalizations,
                "from": {"email": from_email or self.config.sendgrid_from_email},
                "subject": subject,
                "content": content,
            }
            
            if reply_to:
                email_data["reply_to"] = {"email": reply_to}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.config.sendgrid_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=email_data
                )
                
                if response.status_code in (200, 202):
                    return {"success": True, "message": "Email sent successfully"}
                else:
                    return {
                        "success": False,
                        "error": f"SendGrid error: {response.status_code}",
                        "details": response.text,
                    }
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_form_notification(
        self,
        form_id: str,
        submission_id: str,
        form_data: Dict[str, Any],
        recipient_email: str,
    ) -> Dict[str, Any]:
        """Send notification email for form submission.
        
        Args:
            form_id: ID of the form.
            submission_id: ID of the submission.
            form_data: Submitted form data.
            recipient_email: Email to receive notification.
            
        Returns:
            Result dictionary.
        """
        fields_html = "<br>".join([
            f"<strong>{key}:</strong> {value}"
            for key, value in form_data.items()
        ])
        
        html_content = f"""
        <h2>New Form Submission</h2>
        <p><strong>Form ID:</strong> {form_id}</p>
        <p><strong>Submission ID:</strong> {submission_id}</p>
        <hr>
        <h3>Form Data:</h3>
        <p>{fields_html}</p>
        """
        
        return await self.send_email(
            to_emails=[recipient_email],
            subject=f"New Form Submission - {form_id}",
            html_content=html_content,
        )


# Module-level convenience functions
_email_service: Optional[EmailService] = None


def _get_email_service() -> EmailService:
    """Get singleton email service."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


async def send_notification_email(
    to_emails: List[str],
    subject: str,
    html_content: str,
    **kwargs,
) -> Dict[str, Any]:
    """Send a notification email.
    
    Convenience function for sending emails.
    """
    service = _get_email_service()
    return await service.send_email(
        to_emails=to_emails,
        subject=subject,
        html_content=html_content,
        **kwargs,
    )

