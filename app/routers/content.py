# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Content data endpoints — bundles, deliverables, campaigns."""


import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async
from app.services.workspace_data_filter import get_workspace_user_ids

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["Content"])


@router.get("/bundles")
@limiter.limit(get_user_persona_limit)
async def list_bundles(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(default=100, le=500),
):
    """List content bundles ordered by newest first."""
    try:
        scoped_user_ids = await get_workspace_user_ids(user_id)
        supabase = get_service_client()
        query = supabase.table("content_bundles").select("*")
        if len(scoped_user_ids) > 1:
            query = query.in_("user_id", scoped_user_ids)
        else:
            query = query.eq("user_id", user_id)
        response = await execute_async(
            query.order("created_at", desc=True).limit(limit),
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

        scoped_user_ids = await get_workspace_user_ids(user_id)
        supabase = get_service_client()
        query = supabase.table("content_bundle_deliverables").select("*")
        if len(scoped_user_ids) > 1:
            query = query.in_("user_id", scoped_user_ids)
        else:
            query = query.eq("user_id", user_id)
        response = await execute_async(
            query.in_("bundle_id", ids),
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
        scoped_user_ids = await get_workspace_user_ids(user_id)
        supabase = get_service_client()
        query = supabase.table("campaigns").select("*")
        if len(scoped_user_ids) > 1:
            query = query.in_("user_id", scoped_user_ids)
        else:
            query = query.eq("user_id", user_id)
        response = await execute_async(
            query.order("created_at", desc=True).limit(limit),
            op_name="content.campaigns",
        )
        return response.data or []
    except Exception as e:
        logger.error("content.campaigns error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

