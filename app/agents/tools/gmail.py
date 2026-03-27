# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Gmail tools for agents.

Provides tools for sending emails and delivering reports.
"""

from typing import Any

# Tool context type
ToolContextType = Any


def _get_gmail_service(tool_context: ToolContextType):
    """Get Gmail service from tool context credentials."""
    from app.integrations.google.client import get_google_credentials
    from app.integrations.google.gmail import GmailService

    provider_token = tool_context.state.get("google_provider_token")
    refresh_token = tool_context.state.get("google_refresh_token")

    if not provider_token:
        raise ValueError("Google authentication required for email features.")

    credentials = get_google_credentials(provider_token, refresh_token)
    return GmailService(credentials)


def send_email(
    tool_context: ToolContextType,
    to: list[str],
    subject: str,
    body: str,
    body_html: str | None = None,
    cc: list[str] | None = None,
    attachments: list[str] | None = None,
) -> dict[str, Any]:
    """Send an email.

    Use this to send emails to users or team members.

    Args:
        tool_context: Agent tool context.
        to: List of recipient email addresses.
        subject: Email subject line.
        body: Plain text body.
        body_html: Optional HTML body for rich formatting.
        cc: Optional CC recipients.
        attachments: Optional list of file paths to attach.

    Returns:
        Dict with send status and message ID.
    """
    try:
        service = _get_gmail_service(tool_context)
        result = service.send_email(
            to=to,
            subject=subject,
            body=body,
            body_html=body_html,
            cc=cc,
            attachments=attachments,
        )
        return result
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to send email: {e}"}


def send_report_email(
    tool_context: ToolContextType,
    recipients: list[str],
    report_title: str,
    summary: str,
    report_path: str,
) -> dict[str, Any]:
    """Send a report via email with the file attached.

    Use this to deliver generated reports (PPTX, PDF, XLSX) to recipients.

    Args:
        tool_context: Agent tool context.
        recipients: List of email addresses to send to.
        report_title: Title for the email subject.
        summary: Brief summary of the report contents.
        report_path: Path to the report file to attach.

    Returns:
        Dict with delivery status.
    """
    try:
        service = _get_gmail_service(tool_context)
        result = service.send_report(
            recipients=recipients,
            report_title=report_title,
            summary=summary,
            file_path=report_path,
        )

        if result.get("status") == "success":
            return {
                "status": "success",
                "message": f"Report sent to {len(recipients)} recipient(s)",
                "message_id": result.get("message_id"),
            }
        return result

    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to send report: {e}"}


# Export Gmail tools
GMAIL_TOOLS = [
    send_email,
    send_report_email,
]
