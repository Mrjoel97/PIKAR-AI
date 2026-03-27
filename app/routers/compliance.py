# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Compliance data endpoints — audits, risks."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compliance", tags=["Compliance"])


@router.get("/audits")
@limiter.limit(get_user_persona_limit)
async def list_audits(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(default=50, le=200),
):
    """List compliance audits ordered by scheduled_date DESC."""
    try:
        supabase = get_service_client()
        response = await execute_async(
            supabase.table("compliance_audits")
            .select("*")
            .eq("user_id", user_id)
            .order("scheduled_date", desc=True)
            .limit(limit),
            op_name="compliance.audits",
        )
        return response.data or []
    except Exception as e:
        logger.error("compliance.audits error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risks")
@limiter.limit(get_user_persona_limit)
async def list_risks(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(default=50, le=200),
):
    """List open compliance risks (excludes resolved)."""
    try:
        supabase = get_service_client()
        response = await execute_async(
            supabase.table("compliance_risks")
            .select("*")
            .eq("user_id", user_id)
            .neq("status", "resolved")
            .order("created_at", desc=True)
            .limit(limit),
            op_name="compliance.risks",
        )
        return response.data or []
    except Exception as e:
        logger.error("compliance.risks error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
