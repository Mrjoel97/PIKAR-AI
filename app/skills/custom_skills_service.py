"""CustomSkillsService - CRUD operations for user-created custom skills.

This service provides Create, Read, Update, Delete operations for custom skills
stored in Supabase. All operations are scoped to the user_id for data isolation.
"""

from datetime import datetime, timezone
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async
from app.skills.registry import AgentID, Skill, skills_registry
from supabase import Client


class CustomSkillsService:
    """Service for managing user-created custom skills.

    All operations are user_id scoped for data isolation.
    RLS policies in Supabase provide additional security layer.
    """

    def __init__(self):
        self.client: Client = get_service_client()
        self._table_name = "custom_skills"

    async def create_custom_skill(
        self,
        user_id: str,
        name: str,
        description: str,
        category: str,
        agent_ids: list[str],
        knowledge: str | None = None,
        based_on_skill: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        """Create a new custom skill for a user."""
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
            "created_by": user_id,
        }
        response = await execute_async(
            self.client.table(self._table_name).insert(data),
            op_name="custom_skills.create",
        )
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert custom skill")

    async def get_custom_skill(self, user_id: str, skill_id: str) -> dict | None:
        """Retrieve a custom skill by ID for a user."""
        response = await execute_async(
            self.client.table(self._table_name)
            .select("*")
            .eq("id", skill_id)
            .eq("user_id", user_id)
            .single(),
            op_name="custom_skills.get",
        )
        return response.data

    async def get_custom_skill_by_name(self, user_id: str, name: str) -> dict | None:
        """Retrieve a custom skill by name for a user."""
        response = await execute_async(
            self.client.table(self._table_name)
            .select("*")
            .eq("name", name)
            .eq("user_id", user_id)
            .single(),
            op_name="custom_skills.get_by_name",
        )
        return response.data

    async def list_custom_skills(
        self,
        user_id: str,
        category: str | None = None,
        agent_id: str | None = None,
        is_active: bool = True,
    ) -> list[dict]:
        """List custom skills for a user with optional filters."""
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

        response = await execute_async(
            query.order("created_at", desc=True),
            op_name="custom_skills.list",
        )
        return response.data or []

    async def get_skills_for_agent(self, user_id: str, agent_id: str) -> list[dict]:
        """Get all active custom skills for a specific agent."""
        response = await execute_async(
            self.client.table(self._table_name)
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .contains("agent_ids", [agent_id]),
            op_name="custom_skills.list_for_agent",
        )
        return response.data or []

    async def update_custom_skill(
        self,
        user_id: str,
        skill_id: str,
        name: str | None = None,
        description: str | None = None,
        category: str | None = None,
        agent_ids: list[str] | None = None,
        knowledge: str | None = None,
        metadata: dict[str, Any] | None = None,
        is_active: bool | None = None,
    ) -> dict:
        """Update a custom skill."""
        update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}

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

        response = await execute_async(
            self.client.table(self._table_name)
            .update(update_data)
            .eq("id", skill_id)
            .eq("user_id", user_id),
            op_name="custom_skills.update",
        )
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update custom skill")

    async def deactivate_skill(self, user_id: str, skill_id: str) -> dict:
        """Soft-delete a skill by setting is_active=False."""
        return await self.update_custom_skill(
            user_id=user_id, skill_id=skill_id, is_active=False
        )

    async def activate_skill(self, user_id: str, skill_id: str) -> dict:
        """Reactivate a previously deactivated skill."""
        return await self.update_custom_skill(
            user_id=user_id, skill_id=skill_id, is_active=True
        )

    async def delete_custom_skill(self, user_id: str, skill_id: str) -> bool:
        """Permanently delete a custom skill."""
        response = await execute_async(
            self.client.table(self._table_name)
            .delete()
            .eq("id", skill_id)
            .eq("user_id", user_id),
            op_name="custom_skills.delete",
        )
        return len(response.data or []) > 0

    def to_skill_object(self, custom_skill_record: dict) -> Skill:
        """Convert a database record to a Skill object."""
        agent_ids = []
        for aid in custom_skill_record.get("agent_ids", []):
            try:
                agent_ids.append(AgentID(aid))
            except ValueError:
                pass

        return Skill(
            name=custom_skill_record["name"],
            description=custom_skill_record["description"],
            category=custom_skill_record["category"],
            agent_ids=agent_ids,
            knowledge=custom_skill_record.get("knowledge"),
        )

    async def load_user_skills_to_registry(self, user_id: str) -> int:
        """Load all active custom skills for a user into the skills registry."""
        custom_skills = await self.list_custom_skills(user_id, is_active=True)
        count = 0
        for record in custom_skills:
            skill = self.to_skill_object(record)
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


_custom_skills_service: CustomSkillsService | None = None


def get_custom_skills_service() -> CustomSkillsService:
    """Get the singleton CustomSkillsService instance."""
    global _custom_skills_service
    if _custom_skills_service is None:
        _custom_skills_service = CustomSkillsService()
    return _custom_skills_service
