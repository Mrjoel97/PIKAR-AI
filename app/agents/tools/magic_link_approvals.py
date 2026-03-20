"""Magic Link Approval Tools - Create approvals and send email notifications.

Provides a tool that creates an approval request in Supabase, then sends
an HTML email with Approve / Reject buttons via Gmail. The recipient can
act on the request without logging in.
"""

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Tool context type (same convention as gmail.py, briefing_tools.py)
ToolContextType = Any


def _hash_token(token: str) -> str:
    """Hash token using SHA-256 for storage (mirrors approvals router)."""
    return hashlib.sha256(token.encode()).hexdigest()


def _build_approval_email_html(
    description: str,
    details: str,
    approve_url: str,
    reject_url: str,
    expires_at: str,
) -> str:
    """Build a mobile-friendly HTML email with Approve / Reject buttons."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Approval Required</title>
</head>
<body style="margin:0;padding:0;background-color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8fafc;padding:40px 16px;">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background-color:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(15,23,42,0.08);">

<!-- Header -->
<tr><td style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:28px 32px;">
  <table role="presentation" cellpadding="0" cellspacing="0"><tr>
    <td style="padding-right:12px;">
      <div style="width:36px;height:36px;border-radius:10px;background:rgba(255,255,255,0.2);text-align:center;line-height:36px;font-size:18px;color:#fff;">&#x2714;</div>
    </td>
    <td>
      <div style="font-size:13px;font-weight:600;letter-spacing:0.05em;color:rgba(255,255,255,0.85);text-transform:uppercase;">Approval Required</div>
      <div style="font-size:11px;color:rgba(255,255,255,0.65);margin-top:2px;">Pikar AI</div>
    </td>
  </tr></table>
</td></tr>

<!-- Body -->
<tr><td style="padding:28px 32px;">
  <h2 style="margin:0 0 16px;font-size:20px;font-weight:700;color:#1e293b;">{description}</h2>
  {"<p style='margin:0 0 20px;font-size:14px;line-height:1.6;color:#475569;'>" + details + "</p>" if details else ""}
  <p style="margin:0 0 8px;font-size:12px;color:#94a3b8;">Expires: {expires_at}</p>
</td></tr>

<!-- Buttons -->
<tr><td style="padding:0 32px 32px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
    <td width="48%" align="center" style="padding-right:8px;">
      <a href="{reject_url}" target="_blank" style="display:block;padding:14px 0;border-radius:12px;border:1px solid #e2e8f0;background:#ffffff;color:#64748b;font-size:15px;font-weight:600;text-decoration:none;text-align:center;">
        &#x2716;  Reject
      </a>
    </td>
    <td width="48%" align="center" style="padding-left:8px;">
      <a href="{approve_url}" target="_blank" style="display:block;padding:14px 0;border-radius:12px;background:#6366f1;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;text-align:center;box-shadow:0 4px 14px rgba(99,102,241,0.3);">
        &#x2714;  Approve
      </a>
    </td>
  </tr></table>
</td></tr>

<!-- Footer -->
<tr><td style="padding:16px 32px;border-top:1px solid #f1f5f9;text-align:center;">
  <p style="margin:0;font-size:11px;color:#94a3b8;">You received this because an action requires your approval. If you did not expect this, you can safely ignore it.</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def send_approval_request(
    tool_context: ToolContextType,
    action_type: str,
    description: str,
    recipient_email: str,
    details: str = "",
    expires_in_hours: int = 24,
) -> dict[str, Any]:
    """Create an approval request and send a magic link via email.

    The recipient receives an email with Approve/Reject buttons that work
    without requiring login. Use this for any action that needs user approval:
    financial transactions, content publishing, hiring decisions, etc.

    Args:
        tool_context: Agent tool context (provides Google auth for sending email).
        action_type: Category of approval (e.g., 'financial_transaction', 'content_publish', 'hiring_decision').
        description: Human-readable description of what's being approved.
        recipient_email: Email address to send the approval link to.
        details: Additional context about the approval (optional).
        expires_in_hours: How long the link remains valid (default: 24 hours).

    Returns:
        Dict with approval_link, token, expires_at, and email_sent status.
    """
    try:
        # --- Step 1: Create the approval request in Supabase ---
        from app.services.supabase import get_service_client

        supabase = get_service_client()
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

        payload = {
            "description": description,
            "details": details,
            "recipient_email": recipient_email,
            "action_type": action_type,
            "public_token": token,
        }

        # Attach requester user_id from tool context if available
        user_id = None
        if tool_context and hasattr(tool_context, "state"):
            user_id = tool_context.state.get("user_id")
        if user_id:
            payload["requester_user_id"] = user_id

        data = {
            "token": token_hash,
            "action_type": action_type,
            "payload": payload,
            "expires_at": expires_at.isoformat(),
            "status": "PENDING",
        }

        supabase.table("approval_requests").insert(data).execute()

        base_url = os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")
        approval_link = f"{base_url}/approval/{token}"
        approve_url = f"{approval_link}?action=APPROVED"
        reject_url = f"{approval_link}?action=REJECTED"
        expires_display = expires_at.strftime("%B %d, %Y at %H:%M UTC")

        # --- Step 2: Send the email notification ---
        email_sent = False
        email_error = None

        try:
            from app.agents.tools.gmail import _get_gmail_service

            gmail = _get_gmail_service(tool_context)
            html_body = _build_approval_email_html(
                description=description,
                details=details,
                approve_url=approve_url,
                reject_url=reject_url,
                expires_at=expires_display,
            )

            plain_body = (
                f"Approval Required: {description}\n\n"
                f"{details}\n\n"
                f"Approve: {approve_url}\n"
                f"Reject: {reject_url}\n\n"
                f"This link expires {expires_display}."
            )

            gmail.send_email(
                to=[recipient_email],
                subject=f"Approval Required: {description}",
                body=plain_body,
                body_html=html_body,
            )
            email_sent = True

        except Exception as email_exc:
            email_error = str(email_exc)
            logger.warning(
                "Magic link approval created but email failed: %s", email_exc
            )

        return {
            "status": "success",
            "approval_link": approval_link,
            "token": token,
            "expires_at": expires_at.isoformat(),
            "email_sent": email_sent,
            "email_error": email_error,
            "recipient_email": recipient_email,
            "message": (
                f"Approval link sent to {recipient_email}."
                if email_sent
                else f"Approval link created but email delivery failed: {email_error}. "
                f"Share this link manually: {approval_link}"
            ),
        }

    except Exception as e:
        logger.exception("Failed to create magic link approval request")
        return {
            "status": "error",
            "message": f"Failed to create approval request: {e}",
        }


# Export tools list (follows GMAIL_TOOLS, NOTIFICATION_TOOLS pattern)
MAGIC_LINK_TOOLS = [send_approval_request]
