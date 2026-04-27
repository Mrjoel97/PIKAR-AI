"""BYOK (Bring Your Own Key) API Router.

Manages user AI provider configurations — list providers, save/delete
keys, test connectivity, and retrieve available models.
"""


import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id
from app.services.byok_service import (
    SUPPORTED_PROVIDERS,
    get_byok_service,
    get_models_for_provider,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/byok", tags=["BYOK"])


class BYOKSaveRequest(BaseModel):
    provider: str
    model: str
    api_key: str
    org_id: str | None = None


class BYOKStatusResponse(BaseModel):
    enabled: bool
    provider: str | None = None
    model: str | None = None
    org_id: str | None = None


@router.get("/providers")
@limiter.limit(get_user_persona_limit)
async def list_providers(request: Request, user_id: str = Depends(get_current_user_id)):
    """List supported BYOK providers with metadata."""
    return SUPPORTED_PROVIDERS


@router.get("/models/{provider}")
@limiter.limit(get_user_persona_limit)
async def list_models(
    request: Request,
    provider: str,
    user_id: str = Depends(get_current_user_id),
):
    """List available models for a provider."""
    return get_models_for_provider(provider)


@router.get("/status")
@limiter.limit(get_user_persona_limit)
async def get_status(request: Request, user_id: str = Depends(get_current_user_id)):
    """Get user's current BYOK configuration status (never exposes the key)."""
    svc = get_byok_service()
    cfg = await svc.get_config(user_id)
    if cfg and cfg.is_active:
        return BYOKStatusResponse(
            enabled=True,
            provider=cfg.provider,
            model=cfg.model,
            org_id=cfg.org_id,
        )
    return BYOKStatusResponse(enabled=False)


@router.post("/save")
@limiter.limit(get_user_persona_limit)
async def save_config(
    request: Request,
    body: BYOKSaveRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Save BYOK configuration (encrypts API key server-side)."""
    svc = get_byok_service()
    result = await svc.save_config(
        user_id=user_id,
        provider=body.provider,
        model=body.model,
        api_key=body.api_key,
        org_id=body.org_id,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Save failed"))
    return {"success": True}


@router.delete("/delete")
@limiter.limit(get_user_persona_limit)
async def delete_config(request: Request, user_id: str = Depends(get_current_user_id)):
    """Delete user's BYOK configuration and revert to platform Gemini."""
    svc = get_byok_service()
    deleted = await svc.delete_config(user_id)
    return {"deleted": deleted}


@router.post("/test")
@limiter.limit(get_user_persona_limit)
async def test_connection(
    request: Request,
    body: BYOKSaveRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Test a BYOK key by making a minimal API call to the provider."""
    if body.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400, detail=f"Unsupported provider: {body.provider}"
        )

    try:
        import litellm

        response = await litellm.acompletion(
            model=f"{body.provider}/{body.model}",
            messages=[{"role": "user", "content": "Say 'connected' in one word."}],
            api_key=body.api_key,
            max_tokens=5,
        )
        reply = response.choices[0].message.content.strip()
        return {
            "success": True,
            "message": f"Connected to {body.provider}. Response: {reply}",
        }
    except Exception as e:
        logger.warning("BYOK test failed for provider=%s: %s", body.provider, e)
        return {"success": False, "message": str(e)}
