# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Self-Improvement Settings Service.

Reads and writes admin-configurable settings for the self-improvement engine
from the ``self_improvement_settings`` table.

Settings:
    auto_execute_enabled (bool): Whether the engine auto-executes low-risk actions.
    auto_execute_risk_tiers (list[str]): Action types considered low-risk for auto-execution.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# Defaults used when the DB is empty or unreachable
_DEFAULTS: dict[str, Any] = {
    "auto_execute_enabled": False,
    "auto_execute_risk_tiers": ["skill_demoted", "pattern_extract"],
}


async def get_self_improvement_settings() -> dict[str, Any]:
    """Read self-improvement settings from the database.

    Returns a dict with ``auto_execute_enabled`` (bool) and
    ``auto_execute_risk_tiers`` (list[str]).  Falls back to defaults on
    DB error or missing rows.
    """
    try:
        client = get_service_client()
        result = await execute_async(
            client.table("self_improvement_settings").select("key, value"),
            op_name="self_improvement_settings.get_all",
        )
        rows = result.data or []
    except Exception:
        logger.warning(
            "Failed to read self_improvement_settings; using defaults",
            exc_info=True,
        )
        return dict(_DEFAULTS)

    settings: dict[str, Any] = dict(_DEFAULTS)
    for row in rows:
        key = row.get("key")
        raw_value = row.get("value")
        if key == "auto_execute_enabled":
            # JSONB 'false' / 'true' stored as Python bool or string
            if isinstance(raw_value, bool):
                settings["auto_execute_enabled"] = raw_value
            elif isinstance(raw_value, str):
                settings["auto_execute_enabled"] = raw_value.lower() == "true"
            else:
                settings["auto_execute_enabled"] = bool(raw_value)
        elif key == "auto_execute_risk_tiers":
            if isinstance(raw_value, list):
                settings["auto_execute_risk_tiers"] = raw_value
            elif isinstance(raw_value, str):
                try:
                    settings["auto_execute_risk_tiers"] = json.loads(raw_value)
                except (json.JSONDecodeError, TypeError):
                    pass  # keep default

    return settings


async def update_self_improvement_settings(
    key: str,
    value: Any,
    updated_by: str,
) -> None:
    """Upsert a single setting row in self_improvement_settings.

    Args:
        key: Setting key (e.g. ``auto_execute_enabled``).
        value: Setting value (will be stored as JSONB).
        updated_by: Identifier of who made the change (user_id or system label).
    """
    client = get_service_client()

    # Convert Python value to JSON-compatible for JSONB storage
    json_value: Any
    if isinstance(value, bool):
        json_value = value
    elif isinstance(value, (list, dict)):
        json_value = value
    else:
        json_value = value

    await execute_async(
        client.table("self_improvement_settings").upsert(
            {
                "key": key,
                "value": json_value,
                "updated_by": updated_by,
            },
            on_conflict="key",
        ),
        op_name="self_improvement_settings.upsert",
    )
    logger.info(
        "Updated self_improvement_settings: %s = %s (by %s)", key, value, updated_by
    )
