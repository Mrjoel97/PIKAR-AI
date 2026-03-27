# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Audit Logger - Track all MCP calls for compliance and debugging.

This module logs all MCP tool invocations to Supabase for:
- Compliance and audit trails
- Usage tracking and analytics
- Debugging and error investigation
- Cost monitoring (API call counts)
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from supabase import Client

logger = logging.getLogger(__name__)
from app.mcp.config import get_mcp_config
from app.services.supabase_client import get_service_client


@dataclass
class AuditLogEntry:
    """Represents an audit log entry for an MCP call."""

    timestamp: str
    tool_name: str
    agent_name: str | None
    user_id: str | None
    session_id: str | None
    query_sanitized: str  # Always sanitized, never raw PII
    success: bool
    response_status: str  # "success", "error", "rate_limited"
    error_message: str | None
    duration_ms: int | None
    metadata: dict[str, Any] | None


class AuditLogger:
    """Logger for MCP tool invocations.

    Logs are stored in Supabase for persistence and querying.
    If Supabase is not configured, logs are written to stdout.
    """

    def __init__(self, table_name: str | None = None):
        """Initialize the audit logger.

        Args:
            table_name: Override the default audit log table name.
        """
        self.config = get_mcp_config()
        self.table_name = table_name or self.config.audit_log_table
        self._client: Client | None = None

    @property
    def client(self) -> Client | None:
        """Get the Supabase client, creating it if needed."""
        if self._client is None and self.config.is_supabase_configured():
            try:
                self._client = get_service_client()
            except Exception as e:
                # If cached client fails (e.g. missing env vars), fallback to None
                logger.warning(
                    "Failed to get cached Supabase client for audit log: %s", e
                )
                self._client = None
        return self._client

    def log(
        self,
        tool_name: str,
        query_sanitized: str,
        success: bool,
        response_status: str = "success",
        agent_name: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        error_message: str | None = None,
        duration_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an MCP tool invocation.

        Args:
            tool_name: Name of the MCP tool invoked.
            query_sanitized: The sanitized query (PII already removed).
            success: Whether the call succeeded.
            response_status: Status string ("success", "error", "rate_limited").
            agent_name: Name of the agent making the call.
            user_id: User ID associated with the call.
            session_id: Session ID for the conversation.
            error_message: Error message if the call failed.
            duration_ms: Duration of the call in milliseconds.
            metadata: Additional metadata to log.
        """
        if not self.config.audit_log_enabled:
            return

        entry = AuditLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            tool_name=tool_name,
            agent_name=agent_name,
            user_id=user_id,
            session_id=session_id,
            query_sanitized=query_sanitized,
            success=success,
            response_status=response_status,
            error_message=error_message,
            duration_ms=duration_ms,
            metadata=metadata,
        )

        if self.client:
            try:
                self.client.table(self.table_name).insert(asdict(entry)).execute()
            except Exception as e:
                # Fallback to stdout if Supabase insert fails
                logger.error("[AUDIT LOG] Failed to write to Supabase: %s", e)
                logger.info("[AUDIT LOG] %s", json.dumps(asdict(entry)))
        else:
            # No Supabase configured, log via structured logger
            logger.info("[AUDIT LOG] %s", json.dumps(asdict(entry)))


# Module-level singleton logger
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Get the singleton audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def log_mcp_call(tool_name: str, query_sanitized: str, success: bool, **kwargs) -> None:
    """Convenience function to log an MCP call.

    Args:
        tool_name: Name of the MCP tool invoked.
        query_sanitized: The sanitized query (PII already removed).
        success: Whether the call succeeded.
        **kwargs: Additional arguments passed to AuditLogger.log().
    """
    get_audit_logger().log(
        tool_name=tool_name, query_sanitized=query_sanitized, success=success, **kwargs
    )
