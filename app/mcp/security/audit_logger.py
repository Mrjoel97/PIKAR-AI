"""Audit Logger - Track all MCP calls for compliance and debugging.

This module logs all MCP tool invocations to Supabase for:
- Compliance and audit trails
- Usage tracking and analytics
- Debugging and error investigation
- Cost monitoring (API call counts)
"""

import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict

from supabase import create_client, Client

from app.mcp.config import get_mcp_config


@dataclass
class AuditLogEntry:
    """Represents an audit log entry for an MCP call."""
    timestamp: str
    tool_name: str
    agent_name: Optional[str]
    user_id: Optional[str]
    session_id: Optional[str]
    query_sanitized: str  # Always sanitized, never raw PII
    success: bool
    response_status: str  # "success", "error", "rate_limited"
    error_message: Optional[str]
    duration_ms: Optional[int]
    metadata: Optional[Dict[str, Any]]


class AuditLogger:
    """Logger for MCP tool invocations.
    
    Logs are stored in Supabase for persistence and querying.
    If Supabase is not configured, logs are written to stdout.
    """
    
    def __init__(self, table_name: Optional[str] = None):
        """Initialize the audit logger.
        
        Args:
            table_name: Override the default audit log table name.
        """
        self.config = get_mcp_config()
        self.table_name = table_name or self.config.audit_log_table
        self._client: Optional[Client] = None
    
    @property
    def client(self) -> Optional[Client]:
        """Get the Supabase client, creating it if needed."""
        if self._client is None and self.config.is_supabase_configured():
            self._client = create_client(
                self.config.supabase_url,
                self.config.supabase_service_key
            )
        return self._client
    
    def log(
        self,
        tool_name: str,
        query_sanitized: str,
        success: bool,
        response_status: str = "success",
        agent_name: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
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
                print(f"[AUDIT LOG ERROR] Failed to write to Supabase: {e}")
                print(f"[AUDIT LOG] {json.dumps(asdict(entry))}")
        else:
            # No Supabase configured, log to stdout
            print(f"[AUDIT LOG] {json.dumps(asdict(entry))}")


# Module-level singleton logger
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the singleton audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def log_mcp_call(
    tool_name: str,
    query_sanitized: str,
    success: bool,
    **kwargs
) -> None:
    """Convenience function to log an MCP call.
    
    Args:
        tool_name: Name of the MCP tool invoked.
        query_sanitized: The sanitized query (PII already removed).
        success: Whether the call succeeded.
        **kwargs: Additional arguments passed to AuditLogger.log().
    """
    get_audit_logger().log(
        tool_name=tool_name,
        query_sanitized=query_sanitized,
        success=success,
        **kwargs
    )

