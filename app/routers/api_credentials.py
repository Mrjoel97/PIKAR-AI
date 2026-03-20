"""API Credentials CRUD — list/create/delete user API keys.

Security: GET never returns credential values, only metadata.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-credentials", tags=["API Credentials"])


class CredentialCreate(BaseModel):
    name: str
    value: str
    auth_scheme: str = "api_key"  # api_key, bearer, basic, oauth2
    metadata: dict | None = None


@router.get("")
@limiter.limit(get_user_persona_limit)
async def list_credentials(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """List stored API credentials — names and schemes only, NEVER values."""
    try:
        supabase = get_service_client()
        response = await execute_async(
            supabase.table("api_credentials")
            .select("id, name, auth_scheme, metadata, created_at, updated_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True),
            op_name="api_credentials.list",
        )
        return response.data or []
    except Exception as e:
        logger.error("api_credentials.list error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
@limiter.limit(get_user_persona_limit)
async def create_credential(
    request: Request,
    body: CredentialCreate,
    user_id: str = Depends(get_current_user_id),
):
    """Store a new API credential."""
    try:
        supabase = get_service_client()
        data = {
            "user_id": user_id,
            "name": body.name,
            "encrypted_value": body.value,
            "auth_scheme": body.auth_scheme,
            "metadata": body.metadata or {},
        }
        response = await execute_async(
            supabase.table("api_credentials").insert(data),
            op_name="api_credentials.create",
        )
        row = (response.data or [{}])[0]
        return {
            "id": row.get("id"),
            "name": row.get("name"),
            "auth_scheme": row.get("auth_scheme"),
            "created_at": row.get("created_at"),
        }
    except Exception as e:
        logger.error("api_credentials.create error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{name}")
@limiter.limit(get_user_persona_limit)
async def delete_credential(
    request: Request,
    name: str,
    user_id: str = Depends(get_current_user_id),
):
    """Delete an API credential by name."""
    try:
        supabase = get_service_client()
        response = await execute_async(
            supabase.table("api_credentials")
            .delete()
            .eq("user_id", user_id)
            .eq("name", name),
            op_name="api_credentials.delete",
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Credential not found")
        return {"deleted": True, "name": name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("api_credentials.delete error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
