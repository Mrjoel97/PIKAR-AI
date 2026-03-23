"""Audit logging service for admin actions.

Writes all admin actions to the admin_audit_log table using the service
role client (bypasses RLS). Errors are logged but never raised — the
audit service must never break the action it is logging.
"""

import logging

from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

# Valid source tags for admin actions
_VALID_SOURCES = frozenset({"manual", "ai_agent", "impersonation", "monitoring_loop"})


async def log_admin_action(
    admin_user_id: str | None,
    action: str,
    target_type: str | None,
    target_id: str | None,
    details: dict | None,
    source: str,
    *,
    impersonation_session_id: str | None = None,
) -> None:
    """Log an admin action to the admin_audit_log table.

    Uses the service-role Supabase client to bypass RLS. Errors are caught
    and logged but never re-raised — audit failures must not interrupt the
    action being logged.

    Args:
        admin_user_id: UUID of the admin performing the action, or None for
            monitoring_loop actions.
        action: Action name (e.g. 'check_system_health', 'delete_user').
        target_type: Resource type affected (e.g. 'user', 'system'), or None.
        target_id: UUID of the affected resource, or None.
        details: JSONB-compatible dict with additional context, or None.
        source: One of 'manual', 'ai_agent', 'impersonation', 'monitoring_loop'.
        impersonation_session_id: UUID of the active impersonation session, or
            None for non-impersonation actions. Added in Phase 13 (AUDT-04).
            Keyword-only to preserve backward compat with 30+ existing callers.
    """
    if source not in _VALID_SOURCES:
        logger.warning(
            "log_admin_action called with unknown source '%s'; defaulting to 'manual'",
            source,
        )
        source = "manual"

    row: dict = {
        "admin_user_id": admin_user_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "details": details,
        "source": source,
        "impersonation_session_id": impersonation_session_id,
    }

    try:
        from app.services.supabase_async import execute_async

        client = get_service_client()
        await execute_async(
            client.table("admin_audit_log").insert(row),
            op_name="admin_audit.log_action",
        )
        logger.debug(
            "Audit log: source=%s action=%s user=%s", source, action, admin_user_id
        )
    except Exception as exc:
        # Audit must not break the calling operation
        logger.error(
            "Failed to write audit log for action='%s' source='%s': %s",
            action,
            source,
            exc,
        )
