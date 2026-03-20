"""MCP Integrations Module.

This module provides integration services for the MCP connector:
- Email service for notifications
- CRM service for lead management
"""

from app.mcp.integrations.crm_service import CRMService, create_crm_contact
from app.mcp.integrations.email_service import EmailService, send_notification_email

__all__ = [
    "CRMService",
    "EmailService",
    "create_crm_contact",
    "send_notification_email",
]
