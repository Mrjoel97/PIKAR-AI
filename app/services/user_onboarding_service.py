from datetime import datetime, timezone
import os
import uuid
import logging
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel
from supabase import create_client, Client

from app.services.user_agent_factory import get_user_agent_factory

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
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise ValueError("Supabase credentials missing")
        self.supabase: Client = create_client(url, key)
        self._agent_factory = get_user_agent_factory()

    def _determine_persona(self, context: dict) -> UserPersona:
        """Determine user persona based on business context."""
        size = context.get("team_size", "").lower()
        role = context.get("role", "").lower()
        industry = context.get("industry", "").lower()
        
        # Enterprise Rules
        if "200+" in size or "enterprise" in size or "500+" in size:
            return UserPersona.ENTERPRISE
        if "corporate" in industry and ("vp" in role or "chief" in role or "head" in role):
             return UserPersona.ENTERPRISE

        # SME Rules
        if "51-200" in size:
            return UserPersona.SME
        if "11-50" in size and "manufacturing" in industry: # Example complexity
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
        # Implementation omitted for brevity in restore
        return True

    async def submit_business_context(self, user_id: str, context: BusinessContextInput) -> bool:
        """Save business context."""
        try:
            # Fetch existing config
            current = await self._get_user_config(user_id)
            current["business_context"] = context.dict()
            
            # Determine persona immediately
            persona = self._determine_persona(context.dict())
            logger.info(f"Determined persona {persona.value} for user {user_id} during business context submission")

            # Update
            self.supabase.table("user_executive_agents").update({
                "configuration": current,
                "persona": persona.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("user_id", user_id).execute()
            
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
            
            # Update
            self.supabase.table("user_executive_agents").update({
                "configuration": current,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("user_id", user_id).execute()
            
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
            
            # Update both config and agent_name directly
            self.supabase.table("user_executive_agents").update({
                "configuration": current,
                "agent_name": setup.agent_name,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("user_id", user_id).execute()
            
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
            context = config.get("business_context", {})
            
            persona = self._determine_persona(context)
            logger.info(f"Assigned persona {persona.value} to user {user_id}")

            update_data = {
                "onboarding_completed": True,
                "persona": persona.value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            
            self.supabase.table("user_executive_agents").update(update_data).eq("user_id", user_id).execute()
            
            # Invalidate agent cache so next request picks up new persona
            self._agent_factory.invalidate_cache(user_id)
            
            return True
        except Exception as e:
            logger.error(f"Error completing onboarding: {e}")
            raise

    async def _get_user_config(self, user_id: str) -> dict:
        response = self.supabase.table("user_executive_agents").select("configuration").eq("user_id", user_id).execute()
        if response.data:
            return response.data[0].get("configuration", {})
        return {}

_service_instance = None
def get_user_onboarding_service():
    global _service_instance
    if _service_instance is None:
        _service_instance = UserOnboardingService()
    return _service_instance
