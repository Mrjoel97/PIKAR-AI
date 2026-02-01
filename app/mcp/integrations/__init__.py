"""MCP Integrations Module.

This module provides integration services for the MCP connector:
- Email service for notifications
- CRM service for lead management
"""

from app.mcp.integrations.email_service import EmailService, send_notification_email
from app.mcp.integrations.crm_service import CRMService, create_crm_contact

__all__ = [
    "EmailService",
    "send_notification_email",
    "CRMService",
    "create_crm_contact",
]

