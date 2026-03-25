# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Shared autonomy check for admin agent tools.

Queries admin_agent_permissions to determine if an action is blocked,
requires confirmation, or can proceed automatically.
"""

import logging
import uuid

from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)


async def check_autonomy(action_name: str) -> dict | None:
    """Query admin_agent_permissions and return a gate dict if blocked/confirm.

    Returns None when execution should proceed (auto tier or unknown).

    Args:
        action_name: The tool function name registered in admin_agent_permissions.

    Returns:
        A ``{"error": ...}`` dict if blocked, a ``{"requires_confirmation": True, ...}``
        dict if confirmation is required, or None to proceed.
    """
    try:
        client = get_service_client()
        res = (
            client.table("admin_agent_permissions")
            .select("autonomy_level")
            .eq("action_name", action_name)
            .limit(1)
            .execute()
        )
        if res.data:
            level = res.data[0].get("autonomy_level", "auto")
            if level == "blocked":
                return {
                    "error": (
                        f"{action_name} is blocked by admin configuration. "
                        "Contact a super-admin to change the autonomy level."
                    )
                }
            if level == "confirm":
                token = str(uuid.uuid4())
                return {
                    "requires_confirmation": True,
                    "confirmation_token": token,
                    "action_details": {
                        "action": action_name,
                        "risk_level": "low",
                        "description": f"Admin operation: {action_name}",
                    },
                }
            # level == "auto" — proceed
    except Exception as exc:
        logger.warning(
            "Could not verify autonomy level for %s, defaulting to auto: %s",
            action_name,
            exc,
        )
    return None
