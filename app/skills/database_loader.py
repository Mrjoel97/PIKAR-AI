"""Dynamic skill loader that loads skills from database.

This module provides a DatabaseSkillLoader that fetches skills from the
Supabase database instead of loading from the large auto_mapped_skills.py file.
"""

import json
import logging
from typing import Any, Optional

from supabase import Client

from app.services.cache import CacheResult, get_cache_service
from app.skills.registry import AgentID, Skill

logger = logging.getLogger(__name__)


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

    async def get_all_skills(self) -> list[Skill]:
        """Get all skills from database with caching."""
        cache_key = "skills:all"
        cached = await self.cache.get_user_persona(cache_key)

        if cached and isinstance(cached, CacheResult) and cached.found:
            try:
                skills_data = json.loads(cached.value)
                return [Skill(**s) for s in skills_data]
            except Exception as exc:
                logger.warning("Failed to parse cached skills: %s", exc)

        try:
            response = self.supabase.table("skills").select("*").execute()
            if not response.data:
                return []

            skills = [_skill_from_row(row) for row in response.data]
            cache_data = json.dumps([s.model_dump() for s in skills])
            await self.cache._redis.set(  # type: ignore[attr-defined]
                f"persona:{cache_key}",
                cache_data,
                ex=3600,
            )
            return skills
        except Exception as exc:
            logger.error("Failed to load skills from database: %s", exc)
            return []

    async def get_skills_by_category(self, category: str) -> list[Skill]:
        """Get skills filtered by category."""
        try:
            response = self.supabase.table("skills").select("*").eq("category", category).execute()
            if not response.data:
                return []
            return [_skill_from_row(row) for row in response.data]
        except Exception as exc:
            logger.error("Failed to load skills by category: %s", exc)
            return []

    async def get_skills_for_agent(self, agent_id: AgentID) -> list[Skill]:
        """Get skills available to a specific agent."""
        try:
            response = self.supabase.table("skills").select("*").contains("agent_ids", [agent_id.value]).execute()
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

    async def get_skill_by_name(self, name: str) -> Optional[Skill]:
        """Get a specific skill by name."""
        try:
            response = self.supabase.table("skills").select("*").eq("name", name).limit(1).execute()
            if not response.data:
                return None
            return _skill_from_row(response.data[0])
        except Exception as exc:
            logger.error("Failed to load skill by name: %s", exc)
            return None

    async def search_skills(self, query: str) -> list[Skill]:
        """Search skills by name or description."""
        try:
            response = self.supabase.table("skills").select("*").or_(
                f"name.ilike.%{query}%,description.ilike.%{query}%"
            ).execute()
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
            self.supabase.table("skill_usage_log").insert(
                {
                    "skill_id": skill_id,
                    "user_id": user_id,
                    "agent_id": agent_id,
                    "session_id": session_id,
                    "duration_ms": duration_ms,
                    "success": success,
                }
            ).execute()
            return True
        except Exception as exc:
            logger.error("Failed to log skill usage: %s", exc)
            return False


def get_skill_loader(supabase_client: Optional[Client] = None) -> DatabaseSkillLoader:
    """Get a DatabaseSkillLoader instance."""
    if supabase_client is None:
        from app.services.supabase import get_supabase_client

        supabase_client = get_supabase_client()

    return DatabaseSkillLoader(supabase_client)

