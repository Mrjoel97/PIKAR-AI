"""Sales data endpoints — contacts, activities, accounts, campaigns, analytics."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.get("/contacts")
@limiter.limit(get_user_persona_limit)
async def list_contacts(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    stage: str | None = Query(default=None),
    limit: int = Query(default=200, le=500),
):
    """List contacts, optionally filtered by lifecycle stage."""
    try:
        supabase = get_service_client()
        query = (
            supabase.table("contacts")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .limit(limit)
        )
        if stage and stage != "all":
            query = query.eq("lifecycle_stage", stage)

        response = await execute_async(query, op_name="sales.contacts")
        return response.data or []
    except Exception as e:
        logger.error("sales.contacts error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contacts/activities")
@limiter.limit(get_user_persona_limit)
async def list_contact_activities(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(default=10, le=100),
):
    """List recent contact activities."""
    try:
        supabase = get_service_client()
        response = await execute_async(
            supabase.table("contact_activities")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit),
            op_name="sales.contact_activities",
        )
        return response.data or []
    except Exception as e:
        logger.error("sales.contact_activities error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connected-accounts")
@limiter.limit(get_user_persona_limit)
async def list_connected_accounts(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """List connected social/platform accounts."""
    try:
        supabase = get_service_client()
        response = await execute_async(
            supabase.table("connected_accounts")
            .select(
                "id, user_id, platform, account_name, account_id, status, connected_at, last_synced_at"
            )
            .eq("user_id", user_id)
            .order("connected_at", desc=True),
            op_name="sales.connected_accounts",
        )
        return response.data or []
    except Exception as e:
        logger.error("sales.connected_accounts error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns")
@limiter.limit(get_user_persona_limit)
async def list_campaigns(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(default=50, le=200),
):
    """List campaigns with metrics."""
    try:
        supabase = get_service_client()
        response = await execute_async(
            supabase.table("campaigns")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit),
            op_name="sales.campaigns",
        )
        return response.data or []
    except Exception as e:
        logger.error("sales.campaigns error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/page-analytics")
@limiter.limit(get_user_persona_limit)
async def list_page_analytics(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(default=50, le=200),
):
    """List page analytics data."""
    try:
        supabase = get_service_client()
        response = await execute_async(
            supabase.table("page_analytics")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit),
            op_name="sales.page_analytics",
        )
        return response.data or []
    except Exception as e:
        logger.error("sales.page_analytics error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
