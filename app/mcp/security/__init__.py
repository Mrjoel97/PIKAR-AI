"""MCP Security Module.

This module provides security features for the MCP connector:
- PII filtering to sanitize queries before sending to external services
- Shared outbound-call guardrails for redaction and audit-only inspection
- Audit logging to track all MCP calls for compliance and debugging
"""

from app.mcp.security.pii_filter import PIIFilter, sanitize_query
from app.mcp.security.external_call_guard import (
    ExternalCallGuardResult,
    protect_text_payload,
    protect_url_payload,
    summarize_payload_for_audit,
)
from app.mcp.security.audit_logger import AuditLogger, log_mcp_call

__all__ = [
    "PIIFilter",
    "sanitize_query",
    "ExternalCallGuardResult",
    "protect_text_payload",
    "protect_url_payload",
    "summarize_payload_for_audit",
    "AuditLogger",
    "log_mcp_call",
]
