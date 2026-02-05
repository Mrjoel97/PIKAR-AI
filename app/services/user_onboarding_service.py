from datetime import datetime, timezone
import os
import uuid
import logging
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel
from supabase import Client

from app.services.supabase import get_service_client
from app.services.supabase import get_service_client
from app.services.user_agent_factory import get_user_agent_factory
from app.services.cache import get_cache_service
from app.models.user import UserExecutiveAgent, Configuration, BusinessContext, UserPreferences

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

    def _validate_configuration(self, config: dict) -> bool:
        """Validate configuration structure matches database schema."""
        try:
            # Attempt to create Configuration model
            Configuration(**config)
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

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
            response = self.supabase.table("user_executive_agents").select("*").eq("user_id", user_id).execute()
            
            if not response.data:
                # No record exists, user hasn't started
                return OnboardingStatus(
                    is_completed=False,
                    current_step=0,
                    business_context_completed=False,
                    preferences_completed=False,
                    agent_setup_completed=False
                )

            data = response.data[0]
            config = data.get("configuration", {})
            
            bc_completed = bool(config.get("business_context"))
            pref_completed = bool(config.get("preferences"))
            agent_setup_done = bool(config.get("agent_setup") or data.get("agent_name"))
            
            # Determine step (0=not started, 1=business done, 2=prefs done, 3=agent done, 4=complete)
            step = 0
            if bc_completed: step = 1
            if pref_completed: step = 2
            if agent_setup_done: step = 3
            if data.get("onboarding_completed"): step = 4

            return OnboardingStatus(
                is_completed=data.get("onboarding_completed", False),
                current_step=step,
                business_context_completed=bc_completed,
                preferences_completed=pref_completed,
                agent_setup_completed=agent_setup_done,
                persona=data.get("persona"),
                agent_name=data.get("agent_name")
            )
        except Exception as e:
            logger.error(f"Error fetching onboarding status: {e}")
            raise

    async def start_onboarding(self, user_id: str) -> bool:
        """Initialize user record if not exists."""
        try:
            # Check if exists
            existing = await self._get_user_config(user_id)
            if existing: # Already exists (checking config vs row existence, but _get_user_config queries table)
                # Actually _get_user_config returns empty dict if no row. 
                # Let's do a direct select to be safe or just Upsert.
                pass
            
            # Upsert (Insert on conflict do nothing)
            # Supabase upsert requires all columns or ignore_duplicates
            data = {
                "user_id": user_id,
                "onboarding_completed": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            # We use upsert to be safe
            self.supabase.table("user_executive_agents").upsert(data, on_conflict="user_id", ignore_duplicates=True).execute()
            return True
        except Exception as e:
            logger.error(f"Error starting onboarding: {e}")
            raise

    async def submit_business_context(self, user_id: str, context: BusinessContextInput) -> bool:
        """Save business context."""
        try:
            logger.info(f"Received business context for user {user_id}: {context.dict()}")
            
            # Ensure record exists
            await self.start_onboarding(user_id)

            # Fetch existing config
            current = await self._get_user_config(user_id)
            current["business_context"] = context.dict()
            
            # Validate before saving
            try:
                Configuration(business_context=BusinessContext(**context.dict()))
            except Exception as e:
                logger.error(f"Invalid configuration structure: {e}")
                raise ValueError(f"Invalid business context structure: {e}")

            if not self._validate_configuration(current):
                raise ValueError("Invalid configuration structure")
            
            # Determine persona immediately
            persona = self._determine_persona(context.dict())
            logger.info(f"Determined persona {persona.value} for user {user_id} during business context submission")

            # Update
            self.supabase.table("user_executive_agents").update({
                "configuration": current,
                "persona": persona.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("user_id", user_id).execute()
            
            # Invalidate cache
            await self._cache.invalidate_user_config(user_id)
            await self._cache.invalidate_user_persona(user_id)
            
            return True
        except Exception as e:
            logger.error(f"Error submitting business context: {e}")
            raise

    async def submit_preferences(self, user_id: str, prefs: UserPreferencesInput) -> bool:
        """Save user preferences."""
        try:
            # Fetch existing config
            current = await self._get_user_config(user_id)
            current["preferences"] = prefs.dict()

            # Validate before saving
            try:
                Configuration(preferences=UserPreferences(**prefs.dict()))
            except Exception as e:
                logger.error(f"Invalid preferences structure: {e}")
                raise ValueError(f"Invalid preferences structure: {e}")
            
            if not self._validate_configuration(current):
                raise ValueError("Invalid configuration structure")
            
            # Update
            self.supabase.table("user_executive_agents").update({
                "configuration": current,
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
            # Fetch existing config
            current = await self._get_user_config(user_id)
            current["agent_setup"] = setup.dict()

            # Validate configuration
            if not self._validate_configuration(current):
                raise ValueError("Invalid configuration structure")
            
            # Update both config and agent_name directly
            self.supabase.table("user_executive_agents").update({
                "configuration": current,
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
        """Finalize onboarding and classify persona."""
        try:
            config = await self._get_user_config(user_id)
            
            # Validate final configuration
            if not self._validate_configuration(config):
                raise ValueError("Cannot complete onboarding: Invalid configuration")

            context = config.get("business_context", {})
            
            persona = self._determine_persona(context)
            logger.info(f"Assigned persona {persona.value} to user {user_id}")

            update_data = {
                "onboarding_completed": True,
                "persona": persona.value,
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
            valid_personas = [p.value for p in UserPersona]
            if new_persona not in valid_personas:
                raise ValueError(f"Invalid persona: {new_persona}. Must be one of {valid_personas}")

            logger.info(f"User {user_id} switching persona to {new_persona}")

            update_data = {
                "persona": new_persona,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            self.supabase.table("user_executive_agents").update(update_data).eq("user_id", user_id).execute()

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
        # Try cache first
        cached = await self._cache.get_user_config(user_id)
        if cached:
            return cached

        response = self.supabase.table("user_executive_agents").select("configuration").eq("user_id", user_id).execute()
        if response.data:
            data = response.data[0].get("configuration", {})
            # Cache the result
            await self._cache.set_user_config(user_id, data)
            return data
        return {}

    async def get_user_persona(self, user_id: str) -> Optional[str]:
        """Get user persona with caching."""
        # Try cache first
        cached = await self._cache.get_user_persona(user_id)
        if cached:
            return cached
        
        # Query database
        try:
            response = self.supabase.table("user_executive_agents").select("persona").eq("user_id", user_id).single().execute()
            if response.data:
                persona = response.data.get("persona")
                if persona:
                    await self._cache.set_user_persona(user_id, persona)
                return persona
        except Exception:
            pass
        return None

_service_instance = None
def get_user_onboarding_service():
    global _service_instance
    if _service_instance is None:
        _service_instance = UserOnboardingService()
    return _service_instance
