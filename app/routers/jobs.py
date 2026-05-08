# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""REST endpoints for long-running job polling (LONGTASK-01).

The frontend uses ``GET /jobs/{job_id}/progress`` to poll the state of
an ``ai_jobs`` row after receiving a ``long_task_started`` SSE event.
This endpoint enforces ownership (jobs may only be read by the user who
submitted them).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.routers.onboarding import get_current_user_id
from app.services.long_job import get_job_row

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _project_row(row: dict[str, Any]) -> dict[str, Any]:
    """Project a raw ``ai_jobs`` row into a frontend-friendly response.

    Surfaces the fields the frontend job-poller actually consumes —
    ``status``, ``progress_pct``, ``message``, ``result``, timestamps —
    while pulling progress markers out of ``output_data`` if the worker
    stashed them there.
    """
    output_data = row.get("output_data") or {}
    progress_pct = None
    message = None
    if isinstance(output_data, dict):
        progress_pct = output_data.get("progress_pct")
        message = output_data.get("message")

    status = (row.get("status") or "pending").lower()
    response: dict[str, Any] = {
        "job_id": str(row.get("id")),
        "kind": row.get("job_type"),
        "status": status,
        "progress_pct": progress_pct,
        "message": message,
        "started_at": row.get("started_at"),
        "completed_at": row.get("completed_at"),
        "created_at": row.get("created_at"),
        "attempt_count": row.get("attempt_count"),
    }
    if status == "completed":
        response["result"] = output_data
    elif status in {"failed", "cancelled"}:
        response["error"] = row.get("error_message")
        response["result"] = output_data
    return response


@router.get("/{job_id}/progress")
async def get_job_progress(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Return the current state of an ``ai_jobs`` row.

    Args:
        job_id: The job id (UUID) returned from ``run_as_long_job``.
        user_id: Authenticated user from the bearer token.

    Returns:
        Dict with ``status``, ``progress_pct``, ``message``, optional
        ``result``/``error``, and timestamps.

    Raises:
        HTTPException 404: When no row matches ``job_id``.
        HTTPException 403: When the row belongs to another user.
    """
    # First fetch without ownership filter so we can disambiguate 404 vs 403.
    row = await get_job_row(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if str(row.get("user_id") or "") != str(user_id):
        # Don't leak existence to non-owners (RLS already blocks DB-side,
        # but this gives a cleaner HTTP signal).
        raise HTTPException(status_code=403, detail="Forbidden")

    return _project_row(row)
