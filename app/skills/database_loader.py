"""Dynamic skill loader that loads skills from database.

This module provides a DatabaseSkillLoader that fetches skills from the
Supabase database instead of loading from the large auto_mapped_skills.py file.
"""

import logging
from typing import Optional
from supabase import Client

from app.skills.registry import Skill, AgentID
from app.services.cache import get_cache_service, CacheResult

logger = logging.getLogger(__name__)


class DatabaseSkillLoader:
    """Loads skills from database with caching support."""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.cache = get_cache_service()
    
    async def get_all_skills(self) -> list[Skill]:
        """Get all skills from database with caching."""
        
        # Try cache first
        cache_key = "skills:all"
        cached = await self.cache.get_user_persona(cache_key)  # Reusing get for string cache
        
        if cached and isinstance(cached, CacheResult) and cached.found:
            import json
            try:
                skills_data = json.loads(cached.value)
                return [Skill(**s) for s in skills_data]
            except Exception as e:
                logger.warning(f"Failed to parse cached skills: {e}")
        
        # Fetch from database
        try:
            response = self.supabase.table("skills").select("*").execute()
            
            if not response.data:
                return []
            
            skills = []
            for row in response.data:
                skill = Skill(
                    name=row["name"],
                    description=row["description"],
                    category=row.get("category", "general"),
                    knowledge=row.get("knowledge", ""),
                    metadata=row.get("metadata", {}),
                    agent_ids=[AgentID(a) for a in row.get("agent_ids", [])],
                )
                skills.append(skill)
            
            # Cache the result
            import json
            cache_data = json.dumps([s.model_dump() for s in skills])
            await self.cache._redis.set(  # type: ignore
                f"persona:{cache_key}",  # Reusing pattern
                cache_data, 
                ex=3600  # 1 hour cache
            )
            
            return skills
            
        except Exception as e:
            logger.error(f"Failed to load skills from database: {e}")
            return []
    
    async def get_skills_by_category(self, category: str) -> list[Skill]:
        """Get skills filtered by category."""
        
        cache_key = f"skills:category:{category}"
        
        try:
            response = self.supabase.table("skills").select("*").eq("category", category).execute()
            
            if not response.data:
                return []
            
            return [
                Skill(
                    name=row["name"],
                    description=row["description"],
                    category=row.get("category", "general"),
                    knowledge=row.get("knowledge", ""),
                    metadata=row.get("metadata", {}),
                    agent_ids=[AgentID(a) for a in row.get("agent_ids", [])],
                )
                for row in response.data
            ]
            
        except Exception as e:
            logger.error(f"Failed to load skills by category: {e}")
            return []
    
    async def get_skills_for_agent(self, agent_id: AgentID) -> list[Skill]:
        """Get skills available to a specific agent."""
        
        try:
            # Query using contains for array column
            response = self.supabase.table("skills").select("*").contains("agent_ids", [agent_id.value]).execute()
            
            if not response.data:
                return []
            
            skills = []
            for row in response.data:
                # Check if skill is restricted
                if row.get("is_restricted", False):
                    # Skip restricted skills for regular agents
                    # They should go through the restricted skills module
                    continue
                
                skill = Skill(
                    name=row["name"],
                    description=row["description"],
                    category=row.get("category", "general"),
                    knowledge=row.get("knowledge", ""),
                    metadata=row.get("metadata", {}),
                    agent_ids=[AgentID(a) for a in row.get("agent_ids", [])],
                )
                skills.append(skill)
            
            return skills
            
        except Exception as e:
            logger.error(f"Failed to load skills for agent: {e}")
            return []
    
    async def get_skill_by_name(self, name: str) -> Optional[Skill]:
        """Get a specific skill by name."""
        
        try:
            response = self.supabase.table("skills").select("*").eq("name", name).limit(1).execute()
            
            if not response.data:
                return None
            
            row = response.data[0]
            return Skill(
                name=row["name"],
                description=row["description"],
                category=row.get("category", "general"),
                knowledge=row.get("knowledge", ""),
                metadata=row.get("metadata", {}),
                agent_ids=[AgentID(a) for a in row.get("agent_ids", [])],
            )
            
        except Exception as e:
            logger.error(f"Failed to load skill by name: {e}")
            return None
    
    async def search_skills(self, query: str) -> list[Skill]:
        """Search skills by name or description."""
        
        try:
            # Use ilike for simple search
            response = self.supabase.table("skills").select("*").or_(
                f"name.ilike.%{query}%,description.ilike.%{query}%"
            ).execute()
            
            if not response.data:
                return []
            
            return [
                Skill(
                    name=row["name"],
                    description=row["description"],
                    category=row.get("category", "general"),
                    knowledge=row.get("knowledge", ""),
                    metadata=row.get("metadata", {}),
                    agent_ids=[AgentID(a) for a in row.get("agent_ids", [])],
                )
                for row in response.data[:20]  # Limit results
            ]
            
        except Exception as e:
            logger.error(f"Failed to search skills: {e}")
            return []
    
    async def log_skill_usage(
        self, 
        skill_id: str, 
        user_id: str, 
        agent_id: str,
        session_id: str,
        duration_ms: int,
        success: bool
    ) -> bool:
        """Log skill usage for analytics."""
        
        try:
            self.supabase.table("skill_usage_log").insert({
                "skill_id": skill_id,
                "user_id": user_id,
                "agent_id": agent_id,
                "session_id": session_id,
                "duration_ms": duration_ms,
                "success": success
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to log skill usage: {e}")
            return False


def get_skill_loader(supabase_client: Optional[Client] = None) -> DatabaseSkillLoader:
    """Get a DatabaseSkillLoader instance."""
    if supabase_client is None:
        from app.services.supabase import get_supabase_client
        supabase_client = get_supabase_client()
    
    return DatabaseSkillLoader(supabase_client)
