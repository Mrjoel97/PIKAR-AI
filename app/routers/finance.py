"""Finance data endpoints — invoices, assumptions, revenue time-series."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.middleware.rate_limiter import limiter, get_user_persona_limit
from app.routers.onboarding import get_current_user_id
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/finance", tags=["Finance"])


@router.get("/invoices")
@limiter.limit(get_user_persona_limit)
async def list_invoices(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(default=50, le=200),
):
    """List user invoices ordered by created_at DESC."""
    try:
        supabase = get_service_client()
        response = await execute_async(
            supabase.table("invoices")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit),
            op_name="finance.invoices",
        )
        return response.data or []
    except Exception as e:
        logger.error("finance.invoices error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assumptions")
@limiter.limit(get_user_persona_limit)
async def list_assumptions(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """List active financial assumptions."""
    try:
        supabase = get_service_client()
        response = await execute_async(
            supabase.table("finance_assumptions_ledger")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .order("created_at", desc=True),
            op_name="finance.assumptions",
        )
        return response.data or []
    except Exception as e:
        logger.error("finance.assumptions error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/revenue-timeseries")
@limiter.limit(get_user_persona_limit)
async def revenue_timeseries(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    months: int = Query(default=6, le=24),
):
    """Aggregate succeeded payment transactions by month."""
    try:
        supabase = get_service_client()
        since = datetime.now(timezone.utc) - timedelta(days=months * 30)
        response = await execute_async(
            supabase.table("payment_transactions")
            .select("amount, created_at")
            .eq("user_id", user_id)
            .eq("status", "succeeded")
            .gte("created_at", since.isoformat())
            .order("created_at"),
            op_name="finance.revenue_timeseries",
        )
        rows = response.data or []

        by_month: dict[str, float] = {}
        for row in rows:
            d = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            key = f"{d.year}-{d.month:02d}"
            by_month[key] = by_month.get(key, 0) + float(row.get("amount", 0))

        return [
            {"month": month, "total": total}
            for month, total in sorted(by_month.items())
        ]
    except Exception as e:
        logger.error("finance.revenue_timeseries error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
