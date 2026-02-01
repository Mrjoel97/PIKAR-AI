"""CustomSkillsService - CRUD operations for user-created custom skills.

This service provides Create, Read, Update, Delete operations for custom skills
stored in Supabase. All operations are scoped to the user_id for data isolation.
"""

import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from supabase import create_client, Client

from app.skills.registry import AgentID, Skill, skills_registry


class CustomSkillsService:
    """Service for managing user-created custom skills.
    
    All operations are user_id scoped for data isolation.
    RLS policies in Supabase provide additional security layer.
    """
    
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise ValueError("Supabase credentials missing")
        self.client: Client = create_client(url, key)
        self._table_name = "custom_skills"

    # ==========================
    # Create Operations
    # ==========================

    async def create_custom_skill(
        self,
        user_id: str,
        name: str,
        description: str,
        category: str,
        agent_ids: List[str],
        knowledge: Optional[str] = None,
        based_on_skill: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> dict:
        """Create a new custom skill for a user.
        
        Args:
            user_id: The user's UUID.
            name: Unique name for the skill (per user).
            description: What the skill does.
            category: Skill category (e.g., 'marketing', 'content').
            agent_ids: List of AgentID values (e.g., ['MKT', 'CONT']).
            knowledge: Optional knowledge/instructions for the skill.
            based_on_skill: Optional name of skill used as template.
            metadata: Optional additional metadata.
            
        Returns:
            The created skill record.
        """
        data = {
            "user_id": user_id,
            "name": name,
            "description": description,
            "category": category,
            "agent_ids": agent_ids,
            "knowledge": knowledge,
            "based_on_skill": based_on_skill,
            "metadata": metadata or {},
            "is_active": True,
        }
        response = self.client.table(self._table_name).insert(data).execute()
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert custom skill")

    # ==========================
    # Read Operations
    # ==========================

    async def get_custom_skill(self, user_id: str, skill_id: str) -> Optional[dict]:
        """Retrieve a custom skill by ID for a user."""
        response = (
            self.client.table(self._table_name)
            .select("*")
            .eq("id", skill_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return response.data

    async def get_custom_skill_by_name(
        self, user_id: str, name: str
    ) -> Optional[dict]:
        """Retrieve a custom skill by name for a user."""
        response = (
            self.client.table(self._table_name)
            .select("*")
            .eq("name", name)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return response.data

    async def list_custom_skills(
        self,
        user_id: str,
        category: Optional[str] = None,
        agent_id: Optional[str] = None,
        is_active: bool = True
    ) -> List[dict]:
        """List custom skills for a user with optional filters.
        
        Args:
            user_id: The user's UUID.
            category: Optional category filter.
            agent_id: Optional agent ID filter (checks if in agent_ids array).
            is_active: Filter by active status (default True).
            
        Returns:
            List of custom skill records.
        """
        query = (
            self.client.table(self._table_name)
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", is_active)
        )
        
        if category:
            query = query.eq("category", category)
        if agent_id:
            query = query.contains("agent_ids", [agent_id])
            
        response = query.order("created_at", desc=True).execute()
        return response.data

    async def get_skills_for_agent(
        self, user_id: str, agent_id: str
    ) -> List[dict]:
        """Get all active custom skills for a specific agent.

        Args:
            user_id: The user's UUID.
            agent_id: The agent ID (e.g., 'MKT', 'CONT').

        Returns:
            List of skills assigned to this agent.
        """
        response = (
            self.client.table(self._table_name)
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .contains("agent_ids", [agent_id])
            .execute()
        )
        return response.data

    # ==========================
    # Update Operations
    # ==========================

    async def update_custom_skill(
        self,
        user_id: str,
        skill_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        agent_ids: Optional[List[str]] = None,
        knowledge: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None
    ) -> dict:
        """Update a custom skill.

        Args:
            user_id: The user's UUID.
            skill_id: The skill's UUID.
            Other args: Fields to update (only non-None values are updated).

        Returns:
            The updated skill record.
        """
        update_data = {"updated_at": datetime.utcnow().isoformat()}

        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if category is not None:
            update_data["category"] = category
        if agent_ids is not None:
            update_data["agent_ids"] = agent_ids
        if knowledge is not None:
            update_data["knowledge"] = knowledge
        if metadata is not None:
            update_data["metadata"] = metadata
        if is_active is not None:
            update_data["is_active"] = is_active

        response = (
            self.client.table(self._table_name)
            .update(update_data)
            .eq("id", skill_id)
            .eq("user_id", user_id)
            .execute()
        )
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update custom skill")

    async def deactivate_skill(self, user_id: str, skill_id: str) -> dict:
        """Soft-delete a skill by setting is_active=False."""
        return await self.update_custom_skill(
            user_id=user_id,
            skill_id=skill_id,
            is_active=False
        )

    async def activate_skill(self, user_id: str, skill_id: str) -> dict:
        """Reactivate a previously deactivated skill."""
        return await self.update_custom_skill(
            user_id=user_id,
            skill_id=skill_id,
            is_active=True
        )

    # ==========================
    # Delete Operations
    # ==========================

    async def delete_custom_skill(self, user_id: str, skill_id: str) -> bool:
        """Permanently delete a custom skill.

        Note: Consider using deactivate_skill() for soft-delete instead.

        Args:
            user_id: The user's UUID.
            skill_id: The skill's UUID.

        Returns:
            True if deleted successfully.
        """
        response = (
            self.client.table(self._table_name)
            .delete()
            .eq("id", skill_id)
            .eq("user_id", user_id)
            .execute()
        )
        return len(response.data) > 0

    # ==========================
    # Conversion Utilities
    # ==========================

    def to_skill_object(self, custom_skill_record: dict) -> Skill:
        """Convert a database record to a Skill object.

        This allows custom skills to be used like built-in skills.

        Args:
            custom_skill_record: Database record from custom_skills table.

        Returns:
            A Skill object compatible with the skills registry.
        """
        # Convert string agent IDs to AgentID enum values
        agent_ids = []
        for aid in custom_skill_record.get("agent_ids", []):
            try:
                agent_ids.append(AgentID(aid))
            except ValueError:
                # Skip invalid agent IDs
                pass

        return Skill(
            name=custom_skill_record["name"],
            description=custom_skill_record["description"],
            category=custom_skill_record["category"],
            agent_ids=agent_ids,
            knowledge=custom_skill_record.get("knowledge"),
        )

    async def load_user_skills_to_registry(self, user_id: str) -> int:
        """Load all active custom skills for a user into the skills registry.

        This is useful when initializing a user session to make their
        custom skills available to agents.

        Args:
            user_id: The user's UUID.

        Returns:
            Number of skills loaded.
        """
        custom_skills = await self.list_custom_skills(user_id, is_active=True)
        count = 0
        for record in custom_skills:
            skill = self.to_skill_object(record)
            # Use a user-namespaced name to avoid collisions
            namespaced_skill = Skill(
                name=f"custom_{user_id[:8]}_{skill.name}",
                description=skill.description,
                category=skill.category,
                agent_ids=skill.agent_ids,
                knowledge=skill.knowledge,
            )
            skills_registry.register(namespaced_skill)
            count += 1
        return count


# Singleton instance
_custom_skills_service: Optional[CustomSkillsService] = None


def get_custom_skills_service() -> CustomSkillsService:
    """Get the singleton CustomSkillsService instance."""
    global _custom_skills_service
    if _custom_skills_service is None:
        _custom_skills_service = CustomSkillsService()
    return _custom_skills_service

