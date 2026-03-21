"""Admin audit log API endpoint.

Provides:
- GET /admin/audit-log — paginated, filterable audit log entries

Queries the ``admin_audit_log`` table via a service-role client (bypasses RLS).
Requires admin authentication via :func:`require_admin`.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request

from app.middleware.admin_auth import require_admin
from app.middleware.rate_limiter import limiter
from app.services.supabase_client import get_service_client

logger = logging.getLogger(__name__)

router = APIRouter()

# Valid source filter values matching admin_audit_log.source CHECK constraint
_VALID_SOURCES = frozenset({"manual", "ai_agent", "impersonation", "monitoring_loop"})


@router.get("/audit-log")
@limiter.limit("120/minute")
async def list_audit_log(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
    source: Literal["manual", "ai_agent", "impersonation", "monitoring_loop"]
    | None = None,
    limit: int = 50,
    offset: int = 0,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return paginated, filterable admin audit log entries.

    Queries ``admin_audit_log`` ordered by ``created_at`` descending.  Optional
    filters narrow results by source tag and/or a date range.  Pagination is
    controlled via ``limit`` (max 100) and ``offset``.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin; confirms caller is an admin.
        source: Optional filter — one of ``manual``, ``ai_agent``,
            ``impersonation``, ``monitoring_loop``.
        limit: Maximum number of entries to return (default 50, max 100).
        offset: Zero-based row offset for pagination (default 0).
        start_date: ISO 8601 date/datetime string — only entries at or after
            this timestamp are returned.
        end_date: ISO 8601 date/datetime string — only entries at or before
            this timestamp are returned.

    Returns:
        JSON with ``entries`` list, ``total`` count, ``limit``, and ``offset``.

    Raises:
        HTTPException 400: If ``limit`` exceeds 100 or ``offset`` is negative.
        HTTPException 500: If the Supabase query fails.
    """
    # --- input validation ---
    if limit > 100:
        raise HTTPException(
            status_code=400,
            detail="limit must be 100 or less",
        )
    if offset < 0:
        raise HTTPException(
            status_code=400,
            detail="offset must be 0 or greater",
        )

    client = get_service_client()

    try:
        # Base query — select all columns, count included for pagination metadata
        query = (
            client.table("admin_audit_log")
            .select("*", count="exact")
            .order("created_at", desc=True)
        )

        # Optional filters
        if source is not None:
            query = query.eq("source", source)
        if start_date is not None:
            query = query.gte("created_at", start_date)
        if end_date is not None:
            query = query.lte("created_at", end_date)

        # Pagination
        query = query.range(offset, offset + limit - 1)

        result = query.execute()
        total: int = result.count if result.count is not None else len(result.data)

        return {
            "entries": result.data,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to query admin_audit_log: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve audit log entries",
        ) from exc
