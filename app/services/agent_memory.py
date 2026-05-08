# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Per-agent persistent memory keyed by (user_id, agent_name).

Backed by the public.agent_memory table (see
supabase/migrations/20260508120000_agent_memory.sql). One row per
(user_id, agent_name) holds an arbitrary JSONB ``facts`` blob the agent
can read on every turn and update across conversations.

Both async and sync helpers are exposed:

* ``get_agent_memory`` / ``upsert_agent_memory_facts`` — async, intended
  for use from API handlers, services, and tools.
* ``get_agent_memory_sync`` — sync convenience used from ADK
  ``before_model_callback`` hooks (which are themselves sync).

All helpers are best-effort: errors are logged and swallowed so a
failing memory store never crashes an agent turn.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_TABLE = "agent_memory"


def _normalize_facts(raw: Any) -> dict[str, Any]:
    """Return the ``facts`` column as a dict, regardless of how Supabase serialized it."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw:
        try:
            import json

            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


async def get_agent_memory(user_id: str, agent_name: str) -> dict[str, Any]:
    """Fetch the agent's memory facts for ``user_id``.

    Args:
        user_id: Supabase auth user UUID.
        agent_name: Stable agent identifier (the ADK agent.name, e.g.
            ``"FinancialAnalysisAgent"``).

    Returns:
        The ``facts`` dict, or ``{}`` if no row exists or on error.
    """
    if not user_id or not agent_name:
        return {}

    try:
        from app.services.supabase_client import get_async_client

        client = await get_async_client()
        response = (
            await client.table(_TABLE)
            .select("facts")
            .eq("user_id", user_id)
            .eq("agent_name", agent_name)
            .limit(1)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        if not rows:
            return {}
        return _normalize_facts(rows[0].get("facts"))
    except Exception as exc:  # pragma: no cover - best-effort
        logger.debug(
            "[AgentMemory] get_agent_memory(user=%s, agent=%s) failed: %s",
            user_id,
            agent_name,
            exc,
        )
        return {}


async def upsert_agent_memory_facts(
    user_id: str, agent_name: str, facts: dict[str, Any]
) -> None:
    """Merge ``facts`` into the agent's memory row.

    Performs a JSONB merge: existing keys with the same name are
    overwritten by ``facts``; other existing keys are preserved.

    Args:
        user_id: Supabase auth user UUID.
        agent_name: Stable agent identifier.
        facts: Dict of facts to merge. Empty dicts are no-ops.
    """
    if not user_id or not agent_name or not isinstance(facts, dict) or not facts:
        return

    try:
        from app.services.supabase_client import get_async_client

        client = await get_async_client()
        existing = await get_agent_memory(user_id, agent_name)
        merged = {**existing, **facts}

        await (
            client.table(_TABLE)
            .upsert(
                {
                    "user_id": user_id,
                    "agent_name": agent_name,
                    "facts": merged,
                },
                on_conflict="user_id,agent_name",
            )
            .execute()
        )
    except Exception as exc:  # pragma: no cover - best-effort
        logger.debug(
            "[AgentMemory] upsert_agent_memory_facts(user=%s, agent=%s) failed: %s",
            user_id,
            agent_name,
            exc,
        )


def get_agent_memory_sync(user_id: str, agent_name: str) -> dict[str, Any]:
    """Sync variant used from ADK ``before_model_callback`` hooks.

    ADK does not currently support async before_model callbacks, so we
    fall back to the sync service-role client for this single-row read.
    The result is intended to be cached by the caller in session state.
    """
    if not user_id or not agent_name:
        return {}

    try:
        from app.services.supabase_client import get_service_client

        supabase = get_service_client()
        if not supabase:
            return {}
        response = (
            supabase.table(_TABLE)
            .select("facts")
            .eq("user_id", user_id)
            .eq("agent_name", agent_name)
            .limit(1)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        if not rows:
            return {}
        return _normalize_facts(rows[0].get("facts"))
    except Exception as exc:  # pragma: no cover - best-effort
        logger.debug(
            "[AgentMemory] get_agent_memory_sync(user=%s, agent=%s) failed: %s",
            user_id,
            agent_name,
            exc,
        )
        return {}


__all__ = [
    "get_agent_memory",
    "get_agent_memory_sync",
    "upsert_agent_memory_facts",
]
