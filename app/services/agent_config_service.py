"""Agent configuration and feature flag service.

Provides backend operations for reading/writing agent instruction sets and
feature flags through the admin panel.

Exports:
    generate_instruction_diff  — Unified diff of two instruction strings
    validate_instruction_content — Prompt injection + length validation
    get_flag                   — Redis-cached feature flag read
    set_flag                   — DB write + Redis cache invalidation for flags
    get_agent_config           — Read current agent config row
    save_agent_config          — Validated write + history recording
    get_config_history         — Ordered config change history
    rollback_agent_config      — Restore previous instruction version

Redis cache key format for flags: ``admin:feature_flag:{flag_key}`` (60 s TTL).
All Supabase calls use the service-role client via ``execute_async`` to avoid
blocking the event loop.
"""

from __future__ import annotations

import difflib
import json
import logging
import re
from typing import Any

from app.services.cache import get_cache_service
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_INSTRUCTION_LENGTH = 32_000

# Compiled regex patterns for prompt injection detection.
# Each tuple is (pattern_regex, human_readable_description).
_INJECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"ignore\s+all\s+previous\s+instructions", re.IGNORECASE),
        "Contains 'ignore all previous instructions'",
    ),
    (
        re.compile(r"you\s+are\s+now\s+a\b", re.IGNORECASE),
        "Contains 'you are now a'",
    ),
    (
        re.compile(r"\bsystem\s*:", re.IGNORECASE),
        "Contains 'system:' marker",
    ),
    (
        re.compile(r"<\s*system\s*>", re.IGNORECASE),
        "Contains '<system>' XML tag",
    ),
    (
        re.compile(r"disregard\s+previous", re.IGNORECASE),
        "Contains 'disregard previous'",
    ),
    (
        re.compile(r"your\s+new\s+instructions\s+are", re.IGNORECASE),
        "Contains 'your new instructions are'",
    ),
]

# Redis TTL for feature flag cache entries (seconds)
_FLAG_CACHE_TTL = 60

# Redis key prefix for feature flags
_FLAG_CACHE_PREFIX = "admin:feature_flag:"


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def generate_instruction_diff(old: str, new: str) -> str:
    """Return a unified diff of two instruction strings.

    Uses ``difflib.unified_diff`` to produce a human-readable +/- diff.
    Returns an empty string when ``old == new``.

    Args:
        old: The current (before) instruction text.
        new: The proposed (after) instruction text.

    Returns:
        A multi-line unified diff string, or ``""`` when no changes.
    """
    if old == new:
        return ""
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff_lines = list(
        difflib.unified_diff(old_lines, new_lines, fromfile="current", tofile="proposed")
    )
    return "".join(diff_lines)


def validate_instruction_content(text: str) -> list[str]:
    """Validate agent instruction text for prompt injection patterns and length.

    Checks the text against known injection phrases and enforces a maximum
    character limit. Returns an empty list when the text passes all checks.

    Args:
        text: The instruction text to validate.

    Returns:
        A list of human-readable violation strings. Empty means valid.
    """
    violations: list[str] = []

    if len(text) > _MAX_INSTRUCTION_LENGTH:
        violations.append(
            f"Instruction text exceeds maximum length of {_MAX_INSTRUCTION_LENGTH} characters "
            f"(got {len(text)})"
        )

    for pattern, description in _INJECTION_PATTERNS:
        if pattern.search(text):
            violations.append(description)

    return violations


# ---------------------------------------------------------------------------
# Feature flag read/write
# ---------------------------------------------------------------------------


async def get_flag(key: str, default: bool = False) -> bool:
    """Read a feature flag value, using Redis as a read-through cache.

    Cache key: ``admin:feature_flag:{key}`` with a 60-second TTL.
    Falls back to Supabase when Redis is unavailable (circuit-breaker safe).
    Returns ``default`` when the flag key does not exist in the database.

    Args:
        key: The ``flag_key`` to look up in ``admin_feature_flags``.
        default: Value returned when the flag is absent. Defaults to False.

    Returns:
        The boolean value of the flag.
    """
    cache_key = f"{_FLAG_CACHE_PREFIX}{key}"

    # 1. Try Redis cache first
    try:
        cache = get_cache_service()
        redis_client = await cache._get_redis()
        if redis_client is not None:
            raw = await redis_client.get(cache_key)
            if raw is not None:
                return bool(json.loads(raw))
    except Exception as exc:
        logger.warning("Redis read failed for flag %s: %s", key, exc)

    # 2. Fall back to Supabase
    try:
        client = get_service_client()
        result = await execute_async(
            client.table("admin_feature_flags")
            .select("is_enabled")
            .eq("flag_key", key)
            .limit(1),
            op_name=f"get_flag.{key}",
        )
        rows: list[dict[str, Any]] = result.data or []
        if not rows:
            return default

        value: bool = bool(rows[0]["is_enabled"])

        # 3. Store in Redis cache with TTL (best-effort)
        try:
            cache = get_cache_service()
            redis_client = await cache._get_redis()
            if redis_client is not None:
                await redis_client.setex(cache_key, _FLAG_CACHE_TTL, json.dumps(value))
        except Exception as exc:
            logger.warning("Redis write failed for flag %s: %s", key, exc)

        return value

    except Exception as exc:
        logger.error("DB read failed for flag %s: %s", key, exc)
        return default


async def set_flag(
    key: str,
    enabled: bool,
    changed_by: str | None = None,
) -> dict:
    """Enable or disable a feature flag.

    Upserts the flag in ``admin_feature_flags``, records a change in
    ``admin_config_history``, and updates the Redis cache with a fresh value.

    Args:
        key: The ``flag_key`` to update.
        enabled: The new boolean state.
        changed_by: Optional UUID string of the admin who made the change.

    Returns:
        Dict with keys ``flag_key``, ``is_enabled``, and ``status``.
    """
    client = get_service_client()

    # 1. Read current value for history record
    prev_result = await execute_async(
        client.table("admin_feature_flags")
        .select("is_enabled")
        .eq("flag_key", key)
        .limit(1),
        op_name=f"set_flag.read.{key}",
    )
    prev_rows: list[dict[str, Any]] = prev_result.data or []
    previous_enabled: bool | None = prev_rows[0]["is_enabled"] if prev_rows else None

    # 2. Upsert flag value
    upsert_data: dict[str, Any] = {
        "flag_key": key,
        "is_enabled": enabled,
        "updated_at": "now()",
    }
    if changed_by:
        upsert_data["updated_by"] = changed_by

    await execute_async(
        client.table("admin_feature_flags")
        .upsert(upsert_data, on_conflict="flag_key"),
        op_name=f"set_flag.upsert.{key}",
    )

    # 3. Write history row
    history_data: dict[str, Any] = {
        "config_type": "feature_flag",
        "config_key": key,
        "previous_value": json.dumps({"is_enabled": previous_enabled}),
        "new_value": json.dumps({"is_enabled": enabled}),
        "change_source": "admin_agent",
    }
    if changed_by:
        history_data["changed_by"] = changed_by

    await execute_async(
        client.table("admin_config_history").insert(history_data),
        op_name=f"set_flag.history.{key}",
    )

    # 4. Update Redis cache (best-effort)
    cache_key = f"{_FLAG_CACHE_PREFIX}{key}"
    try:
        cache = get_cache_service()
        redis_client = await cache._get_redis()
        if redis_client is not None:
            await redis_client.setex(cache_key, _FLAG_CACHE_TTL, json.dumps(enabled))
    except Exception as exc:
        logger.warning("Redis update failed for flag %s: %s", key, exc)

    return {"flag_key": key, "is_enabled": enabled, "status": "updated"}


# ---------------------------------------------------------------------------
# Agent config CRUD
# ---------------------------------------------------------------------------


async def get_agent_config(agent_name: str) -> dict | None:
    """Read the current configuration row for a named agent.

    Args:
        agent_name: The ``agent_name`` value in ``admin_agent_configs``
            (e.g. ``"financial"``, ``"marketing"``).

    Returns:
        Dict with keys ``agent_name``, ``current_instructions``, ``version``,
        and ``updated_at``, or ``None`` if no row exists.
    """
    client = get_service_client()
    result = await execute_async(
        client.table("admin_agent_configs")
        .select("agent_name, current_instructions, version, updated_at")
        .eq("agent_name", agent_name)
        .limit(1),
        op_name=f"get_agent_config.{agent_name}",
    )
    rows: list[dict[str, Any]] = result.data or []
    return rows[0] if rows else None


async def save_agent_config(
    agent_name: str,
    new_instructions: str,
    changed_by: str | None = None,
) -> dict:
    """Validate and persist updated instructions for an agent.

    Runs injection validation before writing. On success, increments the
    version counter, generates a diff, and records the change in
    ``admin_config_history``.

    Args:
        agent_name: Name of the agent whose config is being updated.
        new_instructions: The proposed new instruction text.
        changed_by: Optional UUID string of the admin who made the change.

    Returns:
        On validation failure: ``{"error": "...", "violations": [...]}``.
        On success: ``{"agent_name": ..., "version": N, "diff": "...", "status": "updated"}``.
    """
    # 1. Injection validation
    violations = validate_instruction_content(new_instructions)
    if violations:
        return {"error": "Injection validation failed", "violations": violations}

    client = get_service_client()

    # 2. Read current state
    current = await get_agent_config(agent_name)
    old_instructions = current["current_instructions"] if current else ""
    old_version: int = current["version"] if current else 0
    new_version = old_version + 1

    # 3. Generate diff
    diff_str = generate_instruction_diff(old_instructions, new_instructions)

    # 4. Upsert updated config
    upsert_data: dict[str, Any] = {
        "agent_name": agent_name,
        "current_instructions": new_instructions,
        "version": new_version,
        "updated_at": "now()",
    }
    if changed_by:
        upsert_data["updated_by"] = changed_by

    await execute_async(
        client.table("admin_agent_configs")
        .upsert(upsert_data, on_conflict="agent_name"),
        op_name=f"save_agent_config.upsert.{agent_name}",
    )

    # 5. Record history
    history_data: dict[str, Any] = {
        "config_type": "agent_instruction",
        "config_key": agent_name,
        "previous_value": json.dumps({"instructions": old_instructions, "version": old_version}),
        "new_value": json.dumps({"instructions": new_instructions, "version": new_version}),
        "change_source": "admin_agent",
    }
    if changed_by:
        history_data["changed_by"] = changed_by

    await execute_async(
        client.table("admin_config_history").insert(history_data),
        op_name=f"save_agent_config.history.{agent_name}",
    )

    return {
        "agent_name": agent_name,
        "version": new_version,
        "diff": diff_str,
        "status": "updated",
    }


async def get_config_history(
    agent_name: str | None = None,
    config_type: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Return configuration change history rows.

    Queries ``admin_config_history`` ordered by most recent first.
    Optionally filters by agent/config key and/or config type.

    Args:
        agent_name: Filter to rows where ``config_key == agent_name``.
        config_type: Filter to rows where ``config_type == config_type``.
        limit: Maximum number of rows to return (default 20).

    Returns:
        List of history row dicts.
    """
    client = get_service_client()
    query = (
        client.table("admin_config_history")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if agent_name is not None:
        query = query.eq("config_key", agent_name)
    if config_type is not None:
        query = query.eq("config_type", config_type)

    result = await execute_async(query, op_name="get_config_history")
    return result.data or []


async def rollback_agent_config(
    history_id: str,
    agent_name: str,
    changed_by: str | None = None,
) -> dict:
    """Restore a previous agent instruction version from history.

    Fetches the history row by ID, extracts ``previous_value``, re-validates
    the restored text for injection (defence-in-depth), and applies via
    ``save_agent_config``.

    Args:
        history_id: UUID of the ``admin_config_history`` row to restore from.
        agent_name: Agent name being rolled back (used for validation).
        changed_by: Optional UUID string of the admin performing the rollback.

    Returns:
        Result dict from ``save_agent_config``, or an error dict.
    """
    client = get_service_client()

    # 1. Fetch target history row
    result = await execute_async(
        client.table("admin_config_history")
        .select("*")
        .eq("id", history_id)
        .limit(1),
        op_name="rollback_agent_config.fetch",
    )
    rows: list[dict[str, Any]] = result.data or []
    if not rows:
        return {"error": f"History row {history_id} not found"}

    row = rows[0]
    previous_value_raw = row.get("previous_value")
    if previous_value_raw is None:
        return {"error": f"History row {history_id} has no previous_value to restore"}

    # previous_value is stored as JSON string or dict (Supabase jsonb)
    if isinstance(previous_value_raw, str):
        previous_value = json.loads(previous_value_raw)
    else:
        previous_value = previous_value_raw

    restored_instructions: str = previous_value.get("instructions", "")
    if not restored_instructions:
        return {"error": "No instruction text found in history row's previous_value"}

    # 2. Defence-in-depth: re-validate the restored text
    violations = validate_instruction_content(restored_instructions)
    if violations:
        return {
            "error": "Restored instructions failed injection validation",
            "violations": violations,
        }

    # 3. Apply via save_agent_config (which will also validate and record history)
    return await save_agent_config(
        agent_name=agent_name,
        new_instructions=restored_instructions,
        changed_by=changed_by,
    )
