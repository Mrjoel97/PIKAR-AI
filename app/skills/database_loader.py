# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Dynamic skill loader that loads skills from database.

This module provides a DatabaseSkillLoader that fetches skills from the
Supabase database instead of loading from the large auto_mapped_skills.py file.
"""

import json
import logging
from typing import Any

from app.services.cache import CacheResult, get_cache_service
from app.services.supabase_async import execute_async
from app.skills.registry import AgentID, Skill
from supabase import Client

logger = logging.getLogger(__name__)

_SKILL_CACHE_TTL_SECONDS = 3600


def _coerce_agent_ids(raw_value: Any) -> list[AgentID]:
    """Normalize agent ID payloads from jsonb arrays, text arrays, or strings."""
    if raw_value in (None, ""):
        return []

    values: list[Any]
    if isinstance(raw_value, list):
        values = raw_value
    elif isinstance(raw_value, (tuple, set)):
        values = list(raw_value)
    elif isinstance(raw_value, str):
        text = raw_value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            values = parsed if isinstance(parsed, list) else [parsed]
        except Exception:
            values = [part.strip() for part in text.split(",") if part.strip()]
    else:
        values = [raw_value]

    agent_ids: list[AgentID] = []
    for value in values:
        try:
            agent_ids.append(AgentID(str(value).upper()))
        except ValueError:
            logger.warning("Skipping unknown agent id from skills row: %s", value)
    return agent_ids


def _skill_from_row(row: dict[str, Any]) -> Skill:
    """Build a Skill object from either the legacy or aligned schema."""
    return Skill(
        name=row["name"],
        description=row["description"],
        category=row.get("category", "general"),
        knowledge=row.get("knowledge") or row.get("content", ""),
        metadata=row.get("metadata") or {},
        agent_ids=_coerce_agent_ids(row.get("agent_ids")),
    )


class DatabaseSkillLoader:
    """Loads skills from database with caching support."""

    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.cache = get_cache_service()

    async def _run_query(self, query_builder: Any, op_name: str):
        return await execute_async(query_builder, op_name=op_name)

    async def get_all_skills(self) -> list[Skill]:
        """Get all skills from database with caching."""
        cache_key = "skills:all"
        cached = await self.cache.get_user_persona(cache_key)

        if isinstance(cached, CacheResult) and cached.found:
            try:
                skills_data = json.loads(cached.value)
                return [Skill(**skill_data) for skill_data in skills_data]
            except Exception as exc:
                logger.warning("Failed to parse cached skills: %s", exc)

        try:
            query = self.supabase.table("skills").select("*")
            response = await self._run_query(query, "skills.get_all")
            if not response.data:
                return []

            skills = [_skill_from_row(row) for row in response.data]
            cache_data = json.dumps([skill.model_dump() for skill in skills])
            await self.cache.set_user_persona(
                cache_key, cache_data, ttl=_SKILL_CACHE_TTL_SECONDS
            )
            return skills
        except Exception as exc:
            logger.error("Failed to load skills from database: %s", exc)
            return []

    async def get_skills_by_category(self, category: str) -> list[Skill]:
        """Get skills filtered by category."""
        try:
            query = self.supabase.table("skills").select("*").eq("category", category)
            response = await self._run_query(query, "skills.get_by_category")
            if not response.data:
                return []
            return [_skill_from_row(row) for row in response.data]
        except Exception as exc:
            logger.error("Failed to load skills by category: %s", exc)
            return []

    async def get_skills_for_agent(self, agent_id: AgentID) -> list[Skill]:
        """Get skills available to a specific agent."""
        try:
            query = (
                self.supabase.table("skills")
                .select("*")
                .contains("agent_ids", [agent_id.value])
            )
            response = await self._run_query(query, "skills.get_for_agent")
            if not response.data:
                return []

            skills = []
            for row in response.data:
                if row.get("is_restricted", False):
                    continue
                skills.append(_skill_from_row(row))
            return skills
        except Exception as exc:
            logger.error("Failed to load skills for agent: %s", exc)
            return []

    async def get_skill_by_name(self, name: str) -> Skill | None:
        """Get a specific skill by name."""
        try:
            query = self.supabase.table("skills").select("*").eq("name", name).limit(1)
            response = await self._run_query(query, "skills.get_by_name")
            if not response.data:
                return None
            return _skill_from_row(response.data[0])
        except Exception as exc:
            logger.error("Failed to load skill by name: %s", exc)
            return None

    async def search_skills(self, query: str) -> list[Skill]:
        """Search skills by name or description."""
        try:
            built_query = (
                self.supabase.table("skills")
                .select("*")
                .or_(f"name.ilike.%{query}%,description.ilike.%{query}%")
            )
            response = await self._run_query(built_query, "skills.search")
            if not response.data:
                return []
            return [_skill_from_row(row) for row in response.data[:20]]
        except Exception as exc:
            logger.error("Failed to search skills: %s", exc)
            return []

    async def log_skill_usage(
        self,
        skill_id: str,
        user_id: str,
        agent_id: str,
        session_id: str,
        duration_ms: int,
        success: bool,
    ) -> bool:
        """Log skill usage for analytics."""
        try:
            query = self.supabase.table("skill_usage_log").insert(
                {
                    "skill_id": skill_id,
                    "user_id": user_id,
                    "agent_id": agent_id,
                    "session_id": session_id,
                    "duration_ms": duration_ms,
                    "success": success,
                }
            )
            await self._run_query(query, "skills.log_usage")
            return True
        except Exception as exc:
            logger.error("Failed to log skill usage: %s", exc)
            return False


def get_skill_loader(supabase_client: Client | None = None) -> DatabaseSkillLoader:
    """Get a DatabaseSkillLoader instance."""
    if supabase_client is None:
        from app.services.supabase import get_supabase_client

        supabase_client = get_supabase_client()

    return DatabaseSkillLoader(supabase_client)
