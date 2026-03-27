# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Admin audit log API endpoint.

Provides:
- GET /admin/audit-log — paginated, filterable audit log entries

Queries the ``admin_audit_log`` table via a service-role client (bypasses RLS).
Requires admin authentication via :func:`require_admin`.

Each returned entry includes an ``admin_email`` field resolved from the stored
``admin_user_id`` UUID via the Supabase auth admin API.  Rows with a null
``admin_user_id`` (e.g. monitoring_loop actions) receive ``"System"`` as the
email value.
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


async def _resolve_admin_emails(client, rows: list[dict]) -> list[dict]:
    """Resolve admin_user_id UUIDs to email addresses for each audit row.

    Fetches each unique non-null ``admin_user_id`` from the Supabase auth
    admin API in a single pass, then annotates every row with an
    ``admin_email`` field.  Rows with ``admin_user_id=None`` receive the
    sentinel value ``"System"``.  Any individual lookup failure falls back
    to the raw UUID so the page still renders rather than crashing.

    Args:
        client: Supabase service-role client (must have auth.admin access).
        rows: Raw audit log rows from the DB query.

    Returns:
        The same rows list, each dict augmented with ``admin_email``.
    """
    # Collect unique UUIDs that need resolution
    unique_ids: set[str] = {
        row["admin_user_id"]
        for row in rows
        if row.get("admin_user_id") is not None
    }

    # Build id → email mapping via Supabase auth admin API (parallelized)
    import asyncio

    async def _resolve_email(uid: str) -> tuple[str, str]:
        try:
            response = await asyncio.to_thread(
                client.auth.admin.get_user_by_id, uid
            )
            email = (
                response.user.email
                if response and response.user
                else None
            )
            return uid, email or uid
        except Exception:
            logger.warning(
                "Could not resolve admin_user_id %s to email; using raw UUID", uid
            )
            return uid, uid

    resolved = await asyncio.gather(*[_resolve_email(uid) for uid in unique_ids])
    id_to_email: dict[str, str] = dict(resolved)

    # Annotate rows — mutate a copy to avoid side-effects on caller's data
    annotated: list[dict] = []
    for row in rows:
        uid = row.get("admin_user_id")
        annotated.append(
            {
                **row,
                "admin_email": id_to_email[uid] if uid is not None else "System",
            }
        )
    return annotated


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

        entries = await _resolve_admin_emails(client, result.data)

        return {
            "entries": entries,
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
