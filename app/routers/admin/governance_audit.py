# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Admin governance audit log viewer endpoint.

Phase 49 Plan 05 (AUTH-05): surfaces the user-action audit trail written to
``governance_audit_log`` by :mod:`app.middleware.audit_log` (Plan 04) to an
admin-facing filterable table.

Endpoints
---------
* ``GET /admin/governance-audit-log`` — paginated, filterable user-action log
* ``GET /admin/governance-audit-log/actions`` — sorted distinct ``action_type``
  list for the filter dropdown

Query parameters
----------------
The list endpoint accepts:

``user_id``   UUID, exact match on ``user_id`` column.
``email``     Case-insensitive email; resolved to ``user_id`` via
              :meth:`auth.admin.list_users`, then filtered on ``user_id``.
              If the email matches no user, returns an empty envelope
              without hitting ``governance_audit_log``.
``action_type``   Exact match on ``action_type`` column
                  (e.g. ``initiative.created``).
``start_date``    ISO 8601 lower bound on ``created_at`` (``.gte``).
``end_date``      ISO 8601 upper bound on ``created_at`` (``.lte``).
``limit``         1-200 inclusive, default 50.
``offset``        >= 0, default 0.

Every returned entry is annotated with an ``actor_email`` field resolved
from ``user_id`` via the Supabase auth admin API. Resolution is best-effort
— if the auth lookup fails for a row, we fall back to the raw UUID so the
page still renders rather than blanking out.

The endpoint is a sibling of :mod:`app.routers.admin.audit`, which serves a
different table (``admin_audit_log``) produced by
:mod:`app.services.admin_audit` for admin-only actions. Both live under the
existing admin route group and inherit ``require_admin`` auth.
"""


import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.middleware.admin_auth import require_admin
from app.middleware.rate_limiter import limiter
from app.services.supabase_client import get_service_client

logger = logging.getLogger(__name__)

router = APIRouter()


async def _resolve_actor_emails(client, rows: list[dict]) -> list[dict]:
    """Resolve ``user_id`` UUIDs to emails for each governance_audit_log row.

    Fetches each unique ``user_id`` from the Supabase auth admin API in a
    single parallel pass, then annotates every row with an ``actor_email``
    field. Rows whose auth lookup raises fall back to the raw UUID so the
    page still renders rather than crashing.

    Args:
        client: Supabase service-role client.
        rows: Raw rows from ``governance_audit_log``.

    Returns:
        A new list of row dicts each augmented with ``actor_email``.
    """
    unique_ids: set[str] = {
        row["user_id"] for row in rows if row.get("user_id")
    }

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
                "Could not resolve user_id %s to email; using raw UUID", uid
            )
            return uid, uid

    if unique_ids:
        resolved = await asyncio.gather(
            *[_resolve_email(uid) for uid in unique_ids]
        )
        id_to_email: dict[str, str] = dict(resolved)
    else:
        id_to_email = {}

    return [
        {**row, "actor_email": id_to_email.get(row.get("user_id"), "Unknown")}
        for row in rows
    ]


async def _resolve_email_to_user_id(client, email: str) -> str | None:
    """Look up a user_id by email via ``auth.admin.list_users``.

    The match is case-insensitive. Returns ``None`` when no user has the
    given email.

    Args:
        client: Supabase service-role client.
        email: The email address to resolve.

    Returns:
        The matched ``user.id`` or ``None`` if no user matches.

    Raises:
        HTTPException 503: Propagated when the auth API call itself fails,
            because the caller cannot distinguish "no match" from "auth
            outage" otherwise.
    """
    try:
        users_resp = await asyncio.to_thread(client.auth.admin.list_users)
    except Exception as exc:
        logger.error("email->user_id resolve failed: %s", exc)
        raise HTTPException(
            status_code=503, detail="User lookup unavailable"
        ) from exc

    email_lower = email.strip().lower()
    for user in users_resp or []:
        user_email = (getattr(user, "email", "") or "").lower()
        if user_email == email_lower:
            return getattr(user, "id", None)
    return None


@router.get("/governance-audit-log")
@limiter.limit("120/minute")
async def list_governance_audit_log(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
    user_id: str | None = None,
    email: str | None = None,
    action_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return paginated, filterable ``governance_audit_log`` entries.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by ``require_admin``; confirms caller is an admin.
        user_id: Optional exact match on ``user_id``.
        email: Optional case-insensitive email; resolved to ``user_id``
            via ``auth.admin.list_users`` before filtering. Ignored when
            ``user_id`` is also supplied.
        action_type: Optional exact match on ``action_type`` column.
        start_date: Optional ISO-8601 lower bound on ``created_at``.
        end_date: Optional ISO-8601 upper bound on ``created_at``.
        limit: Page size (1-200, default 50).
        offset: Zero-based row offset (default 0).

    Returns:
        JSON envelope ``{entries, total, limit, offset}`` where each entry
        is augmented with an ``actor_email`` field.

    Raises:
        HTTPException 400: ``limit`` out of range or ``offset`` negative.
        HTTPException 500: Underlying Supabase query failed.
        HTTPException 503: Auth admin API unavailable during email lookup.
    """
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=400, detail="limit must be between 1 and 200"
        )
    if offset < 0:
        raise HTTPException(
            status_code=400, detail="offset must be 0 or greater"
        )

    client = get_service_client()

    # --- Resolve email -> user_id (only when user_id not explicit) ---
    target_user_id = user_id
    if email and not target_user_id:
        target_user_id = await _resolve_email_to_user_id(client, email)
        if target_user_id is None:
            # Unknown email — short-circuit to empty envelope without
            # touching the table.
            return {
                "entries": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
            }

    # --- Query governance_audit_log ---
    try:
        query = (
            client.table("governance_audit_log")
            .select("*", count="exact")
            .order("created_at", desc=True)
        )

        if target_user_id:
            query = query.eq("user_id", target_user_id)
        if action_type:
            query = query.eq("action_type", action_type)
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            query = query.lte("created_at", end_date)

        query = query.range(offset, offset + limit - 1)
        result = query.execute()

        total: int = (
            result.count if result.count is not None else len(result.data)
        )
        entries = await _resolve_actor_emails(client, result.data)

        return {
            "entries": entries,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to query governance_audit_log: %s", exc, exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve governance audit log entries",
        ) from exc


@router.get("/governance-audit-log/actions")
@limiter.limit("60/minute")
async def list_distinct_actions(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Return the sorted distinct list of ``action_type`` values.

    Populates the action-type dropdown in the admin filter UI. Pulls up to
    5000 rows and dedupes in Python — cheaper than adding a Postgres RPC
    for the current row growth (~34k/day at 100-user beta).

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by ``require_admin``.

    Returns:
        ``{"actions": [...]}`` sorted alphabetically.

    Raises:
        HTTPException 500: Underlying Supabase query failed.
    """
    client = get_service_client()
    try:
        result = (
            client.table("governance_audit_log")
            .select("action_type")
            .limit(5000)
            .execute()
        )
        actions = sorted(
            {r["action_type"] for r in result.data if r.get("action_type")}
        )
        return {"actions": actions}
    except Exception as exc:
        logger.error(
            "Failed to fetch distinct actions: %s", exc, exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="Failed to fetch action types"
        ) from exc
