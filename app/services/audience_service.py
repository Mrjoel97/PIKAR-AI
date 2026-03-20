"""AudienceService - CRUD for marketing audiences and buyer personas.

Manages reusable audience segments and buyer personas stored in
marketing_audiences and marketing_personas tables.
Used by MarketingAutomationAgent for campaign targeting.
"""

from app.services.base_service import AdminService, BaseService
from app.services.request_context import get_current_user_id
from app.services.supabase_async import execute_async


class AudienceService(BaseService):
    """Service for managing marketing audiences.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: str | None = None):
        super().__init__(user_token)

    async def create_audience(
        self,
        name: str,
        description: str = None,
        demographics: dict = None,
        psychographics: dict = None,
        behavioral: dict = None,
        estimated_size: int = None,
        tags: list[str] = None,
        user_id: str | None = None,
    ) -> dict:
        """Create a reusable audience segment.

        Args:
            name: Audience name (e.g., 'Tech-savvy millennials').
            description: Audience description.
            demographics: {age_range, gender, location, income_bracket, education, job_title}.
            psychographics: {interests[], values[], pain_points[], motivations[], lifestyle}.
            behavioral: {purchase_frequency, brand_loyalty, channel_preferences[], device_usage}.
            estimated_size: Estimated audience size.
            tags: Tags for organization.
            user_id: Optional user ID override.

        Returns:
            The created audience record.
        """
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for audience creation")

        data = {
            "user_id": effective_user_id,
            "name": name,
            "description": description,
            "demographics": demographics or {},
            "psychographics": psychographics or {},
            "behavioral": behavioral or {},
            "estimated_size": estimated_size,
            "tags": tags or [],
        }
        data = {k: v for k, v in data.items() if v is not None}

        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(client.table("marketing_audiences").insert(data))
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert")

    async def get_audience(self, audience_id: str, user_id: str | None = None) -> dict:
        """Retrieve an audience by ID."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table("marketing_audiences").select("*").eq("id", audience_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query.single())
        return response.data

    async def update_audience(
        self,
        audience_id: str,
        name: str | None = None,
        description: str | None = None,
        demographics: dict | None = None,
        psychographics: dict | None = None,
        behavioral: dict | None = None,
        estimated_size: int | None = None,
        tags: list[str] | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Update an audience segment."""
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if demographics is not None:
            update_data["demographics"] = demographics
        if psychographics is not None:
            update_data["psychographics"] = psychographics
        if behavioral is not None:
            update_data["behavioral"] = behavioral
        if estimated_size is not None:
            update_data["estimated_size"] = estimated_size
        if tags is not None:
            update_data["tags"] = tags

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table("marketing_audiences")
            .update(update_data)
            .eq("id", audience_id)
        )
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update")

    async def delete_audience(
        self, audience_id: str, user_id: str | None = None
    ) -> bool:
        """Delete an audience segment."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table("marketing_audiences").delete().eq("id", audience_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        return len(response.data) > 0

    async def list_audiences(
        self,
        user_id: str | None = None,
        limit: int = 50,
    ) -> list:
        """List all audience segments."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table("marketing_audiences").select("*")
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(
            query.order("created_at", desc=True).limit(limit)
        )
        return response.data


class PersonaService(BaseService):
    """Service for managing buyer personas.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: str | None = None):
        super().__init__(user_token)

    async def create_persona(
        self,
        name: str,
        role_title: str = None,
        company_type: str = None,
        bio: str = None,
        goals: list[str] = None,
        pain_points: list[str] = None,
        objections: list[str] = None,
        preferred_channels: list[str] = None,
        content_preferences: dict = None,
        buying_journey_stage: str = "awareness",
        audience_id: str = None,
        tags: list[str] = None,
        user_id: str | None = None,
    ) -> dict:
        """Create a buyer persona.

        Args:
            name: Persona name (e.g., 'Startup Sarah').
            role_title: Job title (e.g., 'VP of Marketing').
            company_type: Company type (e.g., 'SaaS startup, 20-50 employees').
            bio: Background narrative.
            goals: List of goals.
            pain_points: List of pain points.
            objections: Common objections to address.
            preferred_channels: Preferred communication channels.
            content_preferences: {formats[], tone, length, frequency}.
            buying_journey_stage: awareness, consideration, decision, retention.
            audience_id: Link to a marketing_audiences record.
            tags: Tags for organization.
            user_id: Optional user ID override.

        Returns:
            The created persona record.
        """
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for persona creation")

        data = {
            "user_id": effective_user_id,
            "name": name,
            "role_title": role_title,
            "company_type": company_type,
            "bio": bio,
            "goals": goals or [],
            "pain_points": pain_points or [],
            "objections": objections or [],
            "preferred_channels": preferred_channels or [],
            "content_preferences": content_preferences or {},
            "buying_journey_stage": buying_journey_stage,
            "audience_id": audience_id,
            "tags": tags or [],
        }
        data = {k: v for k, v in data.items() if v is not None}

        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(client.table("marketing_personas").insert(data))
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert")

    async def get_persona(self, persona_id: str, user_id: str | None = None) -> dict:
        """Retrieve a persona by ID."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table("marketing_personas").select("*").eq("id", persona_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query.single())
        return response.data

    async def update_persona(
        self,
        persona_id: str,
        name: str | None = None,
        role_title: str | None = None,
        company_type: str | None = None,
        bio: str | None = None,
        goals: list[str] | None = None,
        pain_points: list[str] | None = None,
        objections: list[str] | None = None,
        preferred_channels: list[str] | None = None,
        content_preferences: dict | None = None,
        buying_journey_stage: str | None = None,
        audience_id: str | None = None,
        tags: list[str] | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Update a buyer persona."""
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if role_title is not None:
            update_data["role_title"] = role_title
        if company_type is not None:
            update_data["company_type"] = company_type
        if bio is not None:
            update_data["bio"] = bio
        if goals is not None:
            update_data["goals"] = goals
        if pain_points is not None:
            update_data["pain_points"] = pain_points
        if objections is not None:
            update_data["objections"] = objections
        if preferred_channels is not None:
            update_data["preferred_channels"] = preferred_channels
        if content_preferences is not None:
            update_data["content_preferences"] = content_preferences
        if buying_journey_stage is not None:
            update_data["buying_journey_stage"] = buying_journey_stage
        if audience_id is not None:
            update_data["audience_id"] = audience_id
        if tags is not None:
            update_data["tags"] = tags

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table("marketing_personas").update(update_data).eq("id", persona_id)
        )
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update")

    async def delete_persona(self, persona_id: str, user_id: str | None = None) -> bool:
        """Delete a buyer persona."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table("marketing_personas").delete().eq("id", persona_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        return len(response.data) > 0

    async def list_personas(
        self,
        audience_id: str | None = None,
        buying_journey_stage: str | None = None,
        user_id: str | None = None,
        limit: int = 50,
    ) -> list:
        """List buyer personas with optional filters."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table("marketing_personas").select("*")
        if audience_id:
            query = query.eq("audience_id", audience_id)
        if buying_journey_stage:
            query = query.eq("buying_journey_stage", buying_journey_stage)
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(
            query.order("created_at", desc=True).limit(limit)
        )
        return response.data
