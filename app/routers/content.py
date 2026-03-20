"""Content data endpoints — bundles, deliverables, campaigns."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["Content"])


@router.get("/bundles")
@limiter.limit(get_user_persona_limit)
async def list_bundles(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(default=100, le=500),
):
    """List content bundles ordered by target_date ASC."""
    try:
        supabase = get_service_client()
        response = await execute_async(
            supabase.table("content_bundles")
            .select("*")
            .eq("user_id", user_id)
            .order("target_date")
            .limit(limit),
            op_name="content.bundles",
        )
        return response.data or []
    except Exception as e:
        logger.error("content.bundles error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bundles/deliverables")
@limiter.limit(get_user_persona_limit)
async def list_deliverables(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    bundle_ids: str | None = Query(default=None),
):
    """List deliverables for given bundle IDs (comma-separated)."""
    try:
        if not bundle_ids:
            return []

        ids = [bid.strip() for bid in bundle_ids.split(",") if bid.strip()]
        if not ids:
            return []

        supabase = get_service_client()
        response = await execute_async(
            supabase.table("content_bundle_deliverables")
            .select("*")
            .eq("user_id", user_id)
            .in_("bundle_id", ids),
            op_name="content.deliverables",
        )
        return response.data or []
    except Exception as e:
        logger.error("content.deliverables error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns")
@limiter.limit(get_user_persona_limit)
async def list_campaigns(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(default=50, le=200),
):
    """List campaigns ordered by created_at DESC."""
    try:
        supabase = get_service_client()
        response = await execute_async(
            supabase.table("campaigns")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit),
            op_name="content.campaigns",
        )
        return response.data or []
    except Exception as e:
        logger.error("content.campaigns error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
