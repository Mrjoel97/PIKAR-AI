from datetime import datetime, timezone
import logging
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel
from supabase import Client

from app.services.supabase_client import get_service_client
from app.personas.policy_registry import list_persona_policies
from app.services.user_agent_factory import get_user_agent_factory
from app.services.cache import get_cache_service

logger = logging.getLogger(__name__)

class UserPersona(Enum):
    SOLOPRENEUR = "solopreneur"
    STARTUP = "startup"
    SME = "sme"
    ENTERPRISE = "enterprise"

class BusinessContextInput(BaseModel):
    company_name: str
    industry: str
    description: str
    goals: List[str]
    team_size: Optional[str] = None
    role: Optional[str] = None
    website: Optional[str] = None

class UserPreferencesInput(BaseModel):
    tone: str = "professional"
    verbosity: str = "concise"
    communication_style: str = "direct"
    notification_frequency: str = "daily"


class AgentSetupInput(BaseModel):
    agent_name: str
    focus_areas: Optional[List[str]] = None

class OnboardingStatus(BaseModel):
    is_completed: bool
    current_step: int
    total_steps: int = 4
    business_context_completed: bool
    preferences_completed: bool
    agent_setup_completed: bool
    persona: Optional[str] = None
    agent_name: Optional[str] = None

class UserOnboardingService:
    """Service to handle user onboarding flow."""

    def __init__(self):
        try:
            self.supabase: Client = get_service_client()
        except ValueError as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
        self._agent_factory = get_user_agent_factory()
        self._cache = get_cache_service()

    def _determine_persona(self, context: dict) -> UserPersona:
        """Determine user persona based on business context."""
        size = context.get("team_size", "").lower()
        role = context.get("role", "").lower()
        industry = context.get("industry", "").lower()
        
        # Explicit Frontend ID Checks
        if size == "solo":
            return UserPersona.SOLOPRENEUR
        if size == "enterprise":
            return UserPersona.ENTERPRISE
        if size in ["sme-small", "sme-large"]:
            return UserPersona.SME
        if size == "startup":
            return UserPersona.STARTUP

        # Fallback Heuristics (for legacy or text inputs)
        # Enterprise Rules
        if "200+" in size or "enterprise" in size or "500+" in size:
            return UserPersona.ENTERPRISE
        if "corporate" in industry and ("vp" in role or "chief" in role or "head" in role):
             return UserPersona.ENTERPRISE

        # SME Rules
        if "51-200" in size:
            return UserPersona.SME
        if "11-50" in size and "manufacturing" in industry: 
            return UserPersona.SME

        # Solopreneur Rules
        if size in ["1", "just me", "freelancer", "solopreneur"]:
            return UserPersona.SOLOPRENEUR
        if "freelance" in role or "consultant" in role:
            return UserPersona.SOLOPRENEUR

        # Default to Startup
        return UserPersona.STARTUP

    async def get_onboarding_status(self, user_id: str) -> OnboardingStatus:
        """Get the current onboarding status for a user."""
        try:
            # Fetch from users_profile
            profile_response = self.supabase.table("users_profile").select("*").eq("user_id", user_id).execute()
            
            # Fetch agent name from agents table or fallback to user_executive_agents
            agent_response = self.supabase.table("user_executive_agents").select("agent_name, onboarding_completed").eq("user_id", user_id).execute()
            
            agent_data = agent_response.data[0] if agent_response.data else {}
            profile_data = profile_response.data[0] if profile_response.data else {}

            bc_completed = bool(profile_data.get("business_context"))
            pref_completed = bool(profile_data.get("preferences"))
            agent_setup_done = bool(agent_data.get("agent_name"))
            
            # Determine step (0=not started, 1=business done, 2=prefs done, 3=agent done, 4=complete)
            step = 0
            if bc_completed: step = 1
            if pref_completed: step = 2
            if agent_setup_done: step = 3
            if agent_data.get("onboarding_completed"): step = 4

            return OnboardingStatus(
                is_completed=agent_data.get("onboarding_completed", False),
                current_step=step,
                business_context_completed=bc_completed,
                preferences_completed=pref_completed,
                agent_setup_completed=agent_setup_done,
                persona=profile_data.get("persona"),
                agent_name=agent_data.get("agent_name")
            )
        except Exception as e:
            logger.error(f"Error fetching onboarding status: {e}")
            raise

    async def start_onboarding(self, user_id: str) -> bool:
        """Initialize user record if not exists."""
        try:
            # Create profile if not exists
            profile_data = {
                "user_id": user_id,
                "storage_bucket_id": "user-content",
                "storage_path_prefix": f"{user_id}/",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            self.supabase.table("users_profile").upsert(profile_data, on_conflict="user_id", ignore_duplicates=True).execute()

            # Create agent record if not exists
            agent_data = {
                "user_id": user_id,
                "onboarding_completed": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            self.supabase.table("user_executive_agents").upsert(agent_data, on_conflict="user_id", ignore_duplicates=True).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error starting onboarding: {e}")
            raise

    async def submit_business_context(self, user_id: str, context: BusinessContextInput) -> bool:
        """Save business context to users_profile."""
        try:
            logger.info(f"Received business context for user {user_id}: {context.dict()}")
            
            # Ensure records exist
            await self.start_onboarding(user_id)
            
            # Determine persona immediately
            persona = self._determine_persona(context.dict())
            logger.info(f"Determined persona {persona.value} for user {user_id} during business context submission")

            # Update users_profile
            self.supabase.table("users_profile").update({
                "business_context": context.dict(),
                "persona": persona.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("user_id", user_id).execute()
            
            # Legacy sync (keep user_executive_agents in sync strictly for backward compatibility if needed, 
            # but we are moving away. We'll update configuration JSONB just in case)
            # Actually, per plan, we migrate away. But let's keep config column for safety for now?
            # No, let's commit to the new table. 
            
            # Invalidate cache
            await self._cache.invalidate_user_config(user_id)
            await self._cache.invalidate_user_persona(user_id)
            
            return True
        except Exception as e:
            logger.error(f"Error submitting business context: {e}")
            raise

    async def submit_preferences(self, user_id: str, prefs: UserPreferencesInput) -> bool:
        """Save user preferences to users_profile."""
        try:
            # Ensure records exist (just in case)
            await self.start_onboarding(user_id)

            # Update users_profile
            self.supabase.table("users_profile").update({
                "preferences": prefs.dict(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("user_id", user_id).execute()
            
            # Invalidate cache
            await self._cache.invalidate_user_config(user_id)
            
            return True
        except Exception as e:
            logger.error(f"Error submitting user preferences: {e}")
            raise

    async def submit_agent_setup(self, user_id: str, setup: "AgentSetupInput") -> bool:
        """Save agent setup configuration."""
        try:
            # Ensure records exist
            await self.start_onboarding(user_id)

            # Fetch current configuration (merged from profile)
            current_config = await self._get_user_config(user_id)
            current_config["agent_setup"] = setup.dict()

            # Update both config and agent_name directly
            self.supabase.table("user_executive_agents").update({
                "configuration": current_config,
                "agent_name": setup.agent_name,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("user_id", user_id).execute()
            
            # Invalidate configuration cache
            await self._cache.invalidate_user_config(user_id)
            
            # Invalidate agent cache since name changed
            self._agent_factory.invalidate_cache(user_id)
            
            return True
        except Exception as e:
            logger.error(f"Error submitting agent setup: {e}")
            raise

    async def complete_onboarding(self, user_id: str) -> bool:
        """Finalize onboarding."""
        try:
            # Fetch profile to verify
            profile = self.supabase.table("users_profile").select("business_context, persona").eq("user_id", user_id).single().execute()
            
            if not profile.data or not profile.data.get("business_context"):
                 raise ValueError("Cannot complete onboarding: Missing business context")

            # Finalize user_executive_agents
            update_data = {
                "onboarding_completed": True,
                "persona": profile.data.get("persona"), # Sync persona to agent table for easy access by agent system if needed, or remove?
                # Let's sync it for now as a cached value, but source of truth is profile.
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            
            self.supabase.table("user_executive_agents").update(update_data).eq("user_id", user_id).execute()
            
            # Invalidate all user caches
            await self._cache.invalidate_user_all(user_id)
            
            # Invalidate agent cache so next request picks up new persona
            self._agent_factory.invalidate_cache(user_id)
            
            return True
        except Exception as e:
            logger.error(f"Error completing onboarding: {e}")
            raise

    async def switch_persona(self, user_id: str, new_persona: str) -> bool:
        """Allow user to switch their persona manually."""
        try:
            # Validate persona
            valid_personas = list(list_persona_policies().keys())
            if new_persona not in valid_personas:
                raise ValueError(f"Invalid persona: {new_persona}. Must be one of {valid_personas}")

            logger.info(f"User {user_id} switching persona to {new_persona}")

            # Update users_profile (Source of Truth)
            self.supabase.table("users_profile").update({
                "persona": new_persona,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("user_id", user_id).execute()

            # Sync to user_executive_agents (for backward compat)
            self.supabase.table("user_executive_agents").update({
                "persona": new_persona,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("user_id", user_id).execute()

            # Invalidate persona and config caches
            await self._cache.invalidate_user_persona(user_id)
            await self._cache.invalidate_user_config(user_id)

            # Invalidate agent cache so next request picks up new persona
            self._agent_factory.invalidate_cache(user_id)

            return True
        except Exception as e:
            logger.error(f"Error switching persona for user {user_id}: {e}")
            raise

    async def _get_user_config(self, user_id: str) -> dict:
        # Compatibility wrapper: tries to fetch from profile but structure as config
        # This is strictly for internal calls that might expect the old dict structure
        # We should refactor those calls eventually.
        
        # Try cache first
        cached = await self._cache.get_user_config(user_id)
        if cached:
            return cached

        # Construct config from profile + agent
        profile = self.supabase.table("users_profile").select("*").eq("user_id", user_id).single().execute()
        agent = self.supabase.table("user_executive_agents").select("configuration").eq("user_id", user_id).single().execute()
        
        config = {}
        if profile.data:
            config["business_context"] = profile.data.get("business_context")
            config["preferences"] = profile.data.get("preferences")
        
        if agent.data and agent.data.get("configuration"):
             config["agent_setup"] = agent.data.get("configuration").get("agent_setup")
             
        # Cache the result
        await self._cache.set_user_config(user_id, config)
        return config

    async def get_user_persona(self, user_id: str) -> Optional[str]:
        """Get user persona with caching from users_profile."""
        # Try cache first
        cached = await self._cache.get_user_persona(user_id)
        if cached:
            return cached
        
        # Query database (users_profile)
        try:
            response = self.supabase.table("users_profile").select("persona").eq("user_id", user_id).single().execute()
            if response.data:
                persona = response.data.get("persona")
                if persona:
                    await self._cache.set_user_persona(user_id, persona)
                return persona
        except Exception as e:
            logger.warning(f"Failed to get user persona for {user_id}: {e}")
            return None

_service_instance = None
def get_user_onboarding_service():
    global _service_instance
    if _service_instance is None:
        _service_instance = UserOnboardingService()
    return _service_instance

