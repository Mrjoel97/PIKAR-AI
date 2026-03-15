from fastapi import APIRouter, Depends, HTTPException, Request
from app.middleware.rate_limiter import limiter, get_user_persona_limit
from typing import Annotated

from app.services.user_onboarding_service import (
    UserOnboardingService,
    get_user_onboarding_service,
    BusinessContextInput,
    UserPreferencesInput,
    AgentSetupInput,
    OnboardingStatus
)

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
import logging

from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])
security = HTTPBearer()


def get_supabase_client() -> Client:
    """Get Supabase client from centralized service."""
    return get_service_client()


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> str:
    """
    Verifies the JWT token using Supabase and returns the user_id.
    
    Returns:
        str: The user's UUID as a string (from Supabase Auth).
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
@limiter.limit(get_user_persona_limit)
async def get_status(
    request: Request,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[UserOnboardingService, Depends(get_user_onboarding_service)]
):
    """Returns the current onboarding status for the user."""
    return await service.get_onboarding_status(user_id)

@router.post("/business-context")
@limiter.limit(get_user_persona_limit)
async def submit_business_context(
    request: Request,
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
@limiter.limit(get_user_persona_limit)
async def submit_preferences(
    request: Request,
    prefs: UserPreferencesInput,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[UserOnboardingService, Depends(get_user_onboarding_service)]
):
    """Submits the user preferences step."""
    success = await service.submit_preferences(user_id, prefs)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save preferences")
    return {"status": "success"}


@router.post("/agent-setup")
@limiter.limit(get_user_persona_limit)
async def submit_agent_setup(
    request: Request,
    setup: AgentSetupInput,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[UserOnboardingService, Depends(get_user_onboarding_service)]
):
    """Submits the agent setup/customization step."""
    success = await service.submit_agent_setup(user_id, setup)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save agent setup")
    return {"status": "success"}


from pydantic import BaseModel

class PersonaSwitchInput(BaseModel):
    new_persona: str

@router.post("/complete")
@limiter.limit(get_user_persona_limit)
async def complete_onboarding(
    request: Request,
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

@router.post("/switch-persona")
@limiter.limit(get_user_persona_limit)
async def switch_persona(
    request: Request,
    input_data: PersonaSwitchInput,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[UserOnboardingService, Depends(get_user_onboarding_service)]
):
    """Allows a user to switch their persona."""
    try:
        success = await service.switch_persona(user_id, input_data.new_persona)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to switch persona")
        return {"status": "success", "persona": input_data.new_persona}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in switch_persona endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class ConversationExtractionInput(BaseModel):
    messages: list[str]

class ExtractionResult(BaseModel):
    extracted_context: BusinessContextInput
    persona_preview: str
    confidence: float


@router.post("/extract-context", response_model=ExtractionResult)
@limiter.limit(get_user_persona_limit)
async def extract_context(
    request: Request,
    payload: ConversationExtractionInput,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[UserOnboardingService, Depends(get_user_onboarding_service)],
):
    """Extract structured business context from conversational onboarding messages using Gemini."""
    import asyncio
    import json
    from app.agents.shared import get_model, GEMINI_AGENT_MODEL_FALLBACK
    from google.genai import types

    logger.info("Context extraction requested by user %s", user_id)
    conversation_text = "\n".join(payload.messages)

    extraction_prompt = f"""You are extracting structured business information from a casual onboarding conversation.

The user was chatting about their business/idea. Extract the following fields from their messages.
If a field cannot be determined, use reasonable defaults based on context.

Conversation:
{conversation_text}

Return ONLY valid JSON with these fields:
{{
    "company_name": "string - the company/project/business name, or 'My Business' if not mentioned",
    "industry": "string - best matching from: Technology / SaaS, E-commerce / Retail, Financial Services / Fintech, Healthcare / MedTech, Manufacturing, Professional Services, Education / EdTech, Real Estate, Media / Entertainment, Hospitality / Travel, Logistics / Supply Chain, Energy / CleanTech, Other",
    "description": "string - 1-2 sentence business description synthesized from conversation",
    "goals": ["array of goal IDs from: growth, efficiency, automation, cost_reduction, innovation, risk, customer, talent"],
    "team_size": "string - one of: solo, startup, sme-small, sme-large, enterprise",
    "role": "string - user's role/title, or 'founder' if not mentioned",
    "website": "string or null",
    "confidence": 0.0 to 1.0
}}"""

    try:
        model = get_model(GEMINI_AGENT_MODEL_FALLBACK)  # Use Flash for speed
        response = await asyncio.to_thread(
            lambda: model.api_client.models.generate_content(
                model=model.model,
                contents=[types.Content(role="user", parts=[types.Part.from_text(text=extraction_prompt)])],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=1024,
                    response_mime_type="application/json",
                )
            )
        )

        result_text = response.text.strip()
        # Parse JSON from response
        parsed = json.loads(result_text)

        confidence = parsed.pop("confidence", 0.7)

        # Build BusinessContextInput
        extracted = BusinessContextInput(
            company_name=parsed.get("company_name", "My Business"),
            industry=parsed.get("industry", "Other"),
            description=parsed.get("description", ""),
            goals=parsed.get("goals", ["growth"]),
            team_size=parsed.get("team_size", "startup"),
            role=parsed.get("role", "founder"),
            website=parsed.get("website"),
        )

        # Determine persona preview using injected service
        persona = service._determine_persona(extracted.model_dump())

        return ExtractionResult(
            extracted_context=extracted,
            persona_preview=persona.value,
            confidence=confidence,
        )
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini extraction response: {e}")
        # Fallback with defaults
        return ExtractionResult(
            extracted_context=BusinessContextInput(
                company_name="My Business",
                industry="Other",
                description=conversation_text[:200],
                goals=["growth"],
                team_size="startup",
                role="founder",
            ),
            persona_preview="startup",
            confidence=0.3,
        )
    except Exception as e:
        logger.error(f"Context extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Context extraction failed: {str(e)}")
