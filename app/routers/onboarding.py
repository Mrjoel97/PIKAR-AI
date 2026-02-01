from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated

from app.services.user_onboarding_service import (
    UserOnboardingService,
    get_user_onboarding_service,
    BusinessContextInput,
    UserPreferencesInput,
    AgentSetupInput,
    OnboardingStatus
)

# Assuming we have a dependency to get the current user, similar to other routers.
# I will check other routers to see how authentication is handled. 
# For now I will mock the user dependency or try to find a standard ONE.
# Looking at the context, the user request says: "Ensure endpoints invoke supabase to verify the Bearer token and extract user_id."
# I'll try to find a `get_current_user` or similar dependency. 
# If not found immediately, I will implement a basic extraction.

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client, create_client
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])
security = HTTPBearer()

def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("Supabase credentials missing")
    return create_client(url, key)

async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> str:
    """
    Verifies the JWT token using Supabase and returns the user_id.
    """
    token = credentials.credentials
    supabase = get_supabase_client()
    try:
        # Verify the session/user
        user = supabase.auth.get_user(token)
        if not user or not user.user:
             raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return user.user.id
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")


@router.get("/status", response_model=OnboardingStatus)
async def get_status(
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[UserOnboardingService, Depends(get_user_onboarding_service)]
):
    """Returns the current onboarding status for the user."""
    return await service.get_onboarding_status(user_id)

@router.post("/business-context")
async def submit_business_context(
    context: BusinessContextInput,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[UserOnboardingService, Depends(get_user_onboarding_service)]
):
    """Submits the business context step."""
    success = await service.submit_business_context(user_id, context)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save business context")
    return {"status": "success"}

@router.post("/preferences")
async def submit_preferences(
    prefs: UserPreferencesInput,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[UserOnboardingService, Depends(get_user_onboarding_service)]
):
    """Submits the user preferences step."""
    # The service doesn't have a direct 'submit_preferences' method in the interface I saw in the view_file of UserOnboardingService?
    # Let me check the file content again.
    # Ah, I see `submit_business_context` and `complete_onboarding`. I don't see `submit_preferences`.
    # I might need to ADD `submit_preferences` to the service, or `submit_business_context` handles both?
    # Looking at UserOnboardingService.py lines 127-140, it takes `BusinessContextInput`.
    # I need to check if there is a method for preferences. 
    # The service code had `submit_business_context` and `complete_onboarding`. 
    # Wait, line 102 checks `config.get("preferences")`. 
    # I probably need to add `submit_preferences` to the service.
    # I'll implement the router assuming I'll add the method to the service in the next step or right now.
    
    # Actually, looking at the file content in Step 4: 
    # Line 20 defines BusinessContextInput
    # Line 30 defines UserPreferencesInput
    # Line 127 defines submit_business_context
    # Line 145 defines complete_onboarding
    # There is NO submit_preferences method. I must add it.
    
    # I will add the method implementation logic here in the router temporarily or ideally update the service first.
    # To keep things clean, I will assume the method exists and I will UPDATE the service file as well.
    
    success = await service.submit_preferences(user_id, prefs)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save preferences")
    return {"status": "success"}


@router.post("/agent-setup")
async def submit_agent_setup(
    setup: AgentSetupInput,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[UserOnboardingService, Depends(get_user_onboarding_service)]
):
    """Submits the agent setup/customization step."""
    success = await service.submit_agent_setup(user_id, setup)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save agent setup")
    return {"status": "success"}


@router.post("/complete")
async def complete_onboarding(
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[UserOnboardingService, Depends(get_user_onboarding_service)]
):
    """Completes the onboarding process."""
    success = await service.complete_onboarding(user_id)
    if not success:
         raise HTTPException(status_code=500, detail="Failed to complete onboarding")
         
    # Fetch status to get the persona
    status = await service.get_onboarding_status(user_id)
    return {"status": "success", "persona": status.persona}
