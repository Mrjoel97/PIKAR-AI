"""UserOnboardingService - User onboarding flow with business context collection.

This service handles the user onboarding process, collecting business context
and preferences to personalize the ExecutiveAgent experience.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from supabase import create_client, Client

from app.services.user_agent_factory import get_user_agent_factory

logger = logging.getLogger(__name__)


class BusinessContextInput(BaseModel):
    """Input model for business context collection."""
    company_name: Optional[str] = Field(None, description="Name of the company")
    industry: Optional[str] = Field(None, description="Industry sector")
    team_size: Optional[str] = Field(None, description="Size of the team (e.g., '1-10', '11-50')")
    business_model: Optional[str] = Field(None, description="Business model (B2B, B2C, etc.)")
    goals: Optional[List[str]] = Field(default_factory=list, description="Business goals")
    challenges: Optional[List[str]] = Field(default_factory=list, description="Current challenges")
    additional_context: Optional[str] = Field(None, description="Any additional context")


class PreferencesInput(BaseModel):
    """Input model for user preferences."""
    tone: Optional[str] = Field(None, description="Preferred tone (professional, casual, etc.)")
    verbosity: Optional[str] = Field(None, description="Response length (concise, detailed, etc.)")
    format_preference: Optional[str] = Field(None, description="Preferred format (bullets, paragraphs)")
    notification_preferences: Optional[Dict[str, bool]] = Field(
        default_factory=dict, description="Notification settings"
    )


class OnboardingProgress(BaseModel):
    """Model for tracking onboarding progress."""
    user_id: str
    step: str  # 'welcome', 'business_context', 'preferences', 'complete'
    completed_steps: List[str] = Field(default_factory=list)
    business_context: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
    onboarding_completed: bool = False


class OnboardingResult(BaseModel):
    """Result of an onboarding step."""
    success: bool
    step: str
    next_step: Optional[str] = None
    message: str
    progress: Optional[OnboardingProgress] = None


class UserOnboardingService:
    """Service for managing user onboarding flow.
    
    The onboarding flow consists of:
    1. Welcome - Introduction to Pikar AI
    2. Business Context - Collect company and business information
    3. Preferences - Collect communication preferences
    4. Complete - Create personalized agent configuration
    """
    
    ONBOARDING_STEPS = ["welcome", "business_context", "preferences", "complete"]
    
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise ValueError("Supabase credentials missing")
        self.client: Client = create_client(url, key)
        self._table_name = "user_executive_agents"
        self._agent_factory = get_user_agent_factory()

    async def get_onboarding_status(self, user_id: str) -> OnboardingProgress:
        """Get the current onboarding status for a user.
        
        Args:
            user_id: The user's UUID.
            
        Returns:
            OnboardingProgress with current status.
        """
        try:
            response = (
                self.client.table(self._table_name)
                .select("*")
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            
            if response.data:
                config = response.data
                return OnboardingProgress(
                    user_id=user_id,
                    step="complete" if config.get("onboarding_completed") else "business_context",
                    completed_steps=self._get_completed_steps(config),
                    business_context=config.get("business_context"),
                    preferences=config.get("preferences"),
                    onboarding_completed=config.get("onboarding_completed", False),
                )
            
        except Exception as e:
            logger.debug(f"No onboarding record for user {user_id}: {e}")
        
        # New user - start from welcome
        return OnboardingProgress(
            user_id=user_id,
            step="welcome",
            completed_steps=[],
            onboarding_completed=False,
        )

    def _get_completed_steps(self, config: dict) -> List[str]:
        """Determine which onboarding steps are complete."""
        completed = ["welcome"]  # Welcome is always complete if record exists
        
        if config.get("business_context"):
            completed.append("business_context")
        if config.get("preferences"):
            completed.append("preferences")
        if config.get("onboarding_completed"):
            completed.append("complete")
        
        return completed

    async def start_onboarding(self, user_id: str) -> OnboardingResult:
        """Start or resume the onboarding flow.
        
        Args:
            user_id: The user's UUID.
            
        Returns:
            OnboardingResult with welcome message and next step.
        """
        progress = await self.get_onboarding_status(user_id)
        
        if progress.onboarding_completed:
            return OnboardingResult(
                success=True,
                step="complete",
                message="Welcome back! Your personalized assistant is ready.",
                progress=progress,
            )
        
        # Create initial record if doesn't exist
        if progress.step == "welcome":
            try:
                self.client.table(self._table_name).upsert({
                    "user_id": user_id,
                    "onboarding_completed": False,
                }, on_conflict="user_id").execute()
            except Exception as e:
                logger.warning(f"Error creating onboarding record: {e}")
        
        return OnboardingResult(
            success=True,
            step="welcome",
            next_step="business_context",
            message="Welcome to Pikar AI! Let's personalize your experience.",
            progress=progress,
        )

    async def submit_business_context(
        self,
        user_id: str,
        context: BusinessContextInput
    ) -> OnboardingResult:
        """Submit business context during onboarding.

        Args:
            user_id: The user's UUID.
            context: Business context information.

        Returns:
            OnboardingResult with next step.
        """
        business_context = context.model_dump(exclude_none=True)

        try:
            response = (
                self.client.table(self._table_name)
                .update({
                    "business_context": business_context,
                })
                .eq("user_id", user_id)
                .execute()
            )

            if not response.data:
                # Record doesn't exist, create it
                self.client.table(self._table_name).insert({
                    "user_id": user_id,
                    "business_context": business_context,
                    "onboarding_completed": False,
                }).execute()

            progress = await self.get_onboarding_status(user_id)

            return OnboardingResult(
                success=True,
                step="business_context",
                next_step="preferences",
                message="Great! We've saved your business context. Now let's set your preferences.",
                progress=progress,
            )

        except Exception as e:
            logger.error(f"Error saving business context: {e}")
            return OnboardingResult(
                success=False,
                step="business_context",
                message=f"Error saving business context: {str(e)}",
            )

    async def submit_preferences(
        self,
        user_id: str,
        preferences: PreferencesInput
    ) -> OnboardingResult:
        """Submit user preferences during onboarding.

        Args:
            user_id: The user's UUID.
            preferences: User preferences.

        Returns:
            OnboardingResult with completion status.
        """
        prefs_dict = preferences.model_dump(exclude_none=True)

        try:
            response = (
                self.client.table(self._table_name)
                .update({
                    "preferences": prefs_dict,
                })
                .eq("user_id", user_id)
                .execute()
            )

            progress = await self.get_onboarding_status(user_id)

            return OnboardingResult(
                success=True,
                step="preferences",
                next_step="complete",
                message="Preferences saved! Ready to complete your setup.",
                progress=progress,
            )

        except Exception as e:
            logger.error(f"Error saving preferences: {e}")
            return OnboardingResult(
                success=False,
                step="preferences",
                message=f"Error saving preferences: {str(e)}",
            )

    async def complete_onboarding(
        self,
        user_id: str,
        agent_name: Optional[str] = None
    ) -> OnboardingResult:
        """Complete the onboarding process.

        This creates the final personalized agent configuration
        and marks onboarding as complete.

        Args:
            user_id: The user's UUID.
            agent_name: Optional custom name for the agent.

        Returns:
            OnboardingResult with completion status.
        """
        try:
            update_data = {
                "onboarding_completed": True,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            if agent_name:
                update_data["agent_name"] = agent_name

            self.client.table(self._table_name).update(
                update_data
            ).eq("user_id", user_id).execute()

            # Invalidate any cached agent to force recreation with new config
            self._agent_factory.invalidate_cache(user_id)

            # Get the personalized agent to verify it works
            agent = await self._agent_factory.create_executive_agent(user_id)

            progress = await self.get_onboarding_status(user_id)

            return OnboardingResult(
                success=True,
                step="complete",
                message=f"Welcome aboard! Your personalized assistant '{agent.name}' is ready to help.",
                progress=progress,
            )

        except Exception as e:
            logger.error(f"Error completing onboarding: {e}")
            return OnboardingResult(
                success=False,
                step="complete",
                message=f"Error completing onboarding: {str(e)}",
            )

    async def skip_onboarding(self, user_id: str) -> OnboardingResult:
        """Skip detailed onboarding and use defaults.

        Args:
            user_id: The user's UUID.

        Returns:
            OnboardingResult with completion status.
        """
        try:
            self.client.table(self._table_name).upsert({
                "user_id": user_id,
                "onboarding_completed": True,
                "business_context": {},
                "preferences": {},
            }, on_conflict="user_id").execute()

            progress = await self.get_onboarding_status(user_id)

            return OnboardingResult(
                success=True,
                step="complete",
                message="Setup complete! You can update your preferences anytime.",
                progress=progress,
            )

        except Exception as e:
            logger.error(f"Error skipping onboarding: {e}")
            return OnboardingResult(
                success=False,
                step="complete",
                message=f"Error: {str(e)}",
            )

    async def reset_onboarding(self, user_id: str) -> OnboardingResult:
        """Reset onboarding to start fresh.

        Args:
            user_id: The user's UUID.

        Returns:
            OnboardingResult with welcome step.
        """
        try:
            self.client.table(self._table_name).update({
                "business_context": None,
                "preferences": None,
                "system_prompt_override": None,
                "onboarding_completed": False,
            }).eq("user_id", user_id).execute()

            self._agent_factory.invalidate_cache(user_id)

            progress = await self.get_onboarding_status(user_id)

            return OnboardingResult(
                success=True,
                step="welcome",
                next_step="business_context",
                message="Onboarding has been reset. Let's start fresh!",
                progress=progress,
            )

        except Exception as e:
            logger.error(f"Error resetting onboarding: {e}")
            return OnboardingResult(
                success=False,
                step="welcome",
                message=f"Error: {str(e)}",
            )


# =============================================================================
# Module-level helpers
# =============================================================================

_user_onboarding_service: Optional[UserOnboardingService] = None


def get_user_onboarding_service() -> UserOnboardingService:
    """Get the singleton UserOnboardingService instance."""
    global _user_onboarding_service
    if _user_onboarding_service is None:
        _user_onboarding_service = UserOnboardingService()
    return _user_onboarding_service


__all__ = [
    "UserOnboardingService",
    "get_user_onboarding_service",
    "BusinessContextInput",
    "PreferencesInput",
    "OnboardingProgress",
    "OnboardingResult",
]

