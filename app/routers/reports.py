# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Reports API: list and get user reports (workflow/initiative summaries, scheduled)."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.app_utils.auth import get_supabase_client
from app.middleware.rate_limiter import limiter, get_user_persona_limit
from app.routers.onboarding import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("", response_model=List[Dict[str, Any]])
@limiter.limit(get_user_persona_limit)
async def list_reports(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    category: Optional[str] = None,
    source_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """List reports for the current user. Filter by category or source_type; search in title and summary."""
    try:
        client = get_supabase_client()
        q = (
            client.table("user_reports")
            .select("id, title, category, status, summary, source_type, source_id, metadata, created_at, updated_at", count="exact")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if category:
            q = q.eq("category", category)
        if source_type:
            q = q.eq("source_type", source_type)
        if search and search.strip():
            # Sanitize search term to prevent SQL injection
            # Use parameterized query via ilike with escaped wildcards
            term = search.strip()
            # Escape special PostgreSQL LIKE characters
            term = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            # Use text search for safer pattern matching
            q = q.or_(f"title.ilike.%{term}%,summary.ilike.%{term}%")
        res = q.execute()
        return res.data or []
    except Exception as e:
        logger.exception("list_reports error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
@limiter.limit(get_user_persona_limit)
async def list_report_categories(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Return distinct categories for the current user's reports (for filter dropdown)."""
    try:
        client = get_supabase_client()
        res = (
            client.table("user_reports")
            .select("category")
            .eq("user_id", user_id)
        ).execute()
        categories = sorted({r["category"] for r in (res.data or []) if r.get("category")})
        return {"categories": categories}
    except Exception as e:
        logger.exception("list_report_categories error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{report_id}", response_model=Dict[str, Any])
@limiter.limit(get_user_persona_limit)
async def get_report(
    request: Request,
    report_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get a single report by id. Returns full content."""
    try:
        client = get_supabase_client()
        res = (
            client.table("user_reports")
            .select("*")
            .eq("id", report_id)
            .eq("user_id", user_id)
            .single()
        ).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Report not found")
        return res.data
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_report error")
        raise HTTPException(status_code=500, detail=str(e))
