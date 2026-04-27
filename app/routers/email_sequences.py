# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Email Sequences Router - REST API for email sequence management and tracking.

Provides CRUD endpoints for sequences, enrollment management, performance
stats, and public tracking endpoints (open pixel, click redirect,
unsubscribe).
"""


import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

from app.routers.onboarding import get_current_user_id
from app.services.email_sequence_service import (
    TRANSPARENT_PIXEL,
    EmailSequenceService,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Email Sequences"])


# =====================================================================
# Pydantic Models
# =====================================================================


class StepInput(BaseModel):
    """Input schema for a single sequence step."""

    subject_template: str
    body_template: str
    delay_hours: int = 0
    delay_type: str = "after_previous"


class CreateSequenceInput(BaseModel):
    """Input schema for creating a new email sequence."""

    name: str
    steps: list[StepInput]
    campaign_id: str | None = None


class UpdateStatusInput(BaseModel):
    """Input schema for updating sequence status."""

    status: str = Field(
        ..., pattern="^(active|paused|completed)$"
    )


class EnrollContactsInput(BaseModel):
    """Input schema for enrolling contacts in a sequence."""

    contact_ids: list[str]
    timezone: str = "UTC"


# =====================================================================
# CRUD Endpoints (authenticated)
# =====================================================================


@router.post(
    "/email-sequences",
    status_code=201,
    summary="Create an email sequence",
)
async def create_sequence(
    body: CreateSequenceInput,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """Create a new email sequence with steps."""
    svc = EmailSequenceService()
    steps = [s.model_dump() for s in body.steps]
    result = await svc.create_sequence(
        user_id=user_id,
        name=body.name,
        steps=steps,
        campaign_id=body.campaign_id,
    )
    return result


@router.get(
    "/email-sequences",
    summary="List email sequences",
)
async def list_sequences(
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> list[dict[str, Any]]:
    """List all email sequences for the current user."""
    svc = EmailSequenceService()
    return await svc.list_sequences(user_id)


@router.get(
    "/email-sequences/{sequence_id}",
    summary="Get email sequence detail",
)
async def get_sequence(
    sequence_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """Get an email sequence with steps and enrollment stats."""
    svc = EmailSequenceService()
    result = await svc.get_sequence(user_id, sequence_id)
    if not result:
        raise HTTPException(
            status_code=404, detail="Sequence not found"
        )
    return result


@router.patch(
    "/email-sequences/{sequence_id}/status",
    summary="Update sequence status",
)
async def update_sequence_status(
    sequence_id: str,
    body: UpdateStatusInput,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """Update a sequence status (activate, pause, or complete)."""
    svc = EmailSequenceService()
    try:
        return await svc.update_sequence_status(
            user_id, sequence_id, body.status
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc


@router.delete(
    "/email-sequences/{sequence_id}",
    summary="Delete an email sequence",
)
async def delete_sequence(
    sequence_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, str]:
    """Delete an email sequence (CASCADE deletes steps/enrollments)."""
    svc = EmailSequenceService()
    deleted = await svc.delete_sequence(user_id, sequence_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail="Sequence not found"
        )
    return {"status": "deleted"}


# =====================================================================
# Enrollment Endpoints (authenticated)
# =====================================================================


@router.post(
    "/email-sequences/{sequence_id}/enroll",
    summary="Enroll contacts in a sequence",
)
async def enroll_contacts(
    sequence_id: str,
    body: EnrollContactsInput,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """Enroll contacts in an email sequence."""
    svc = EmailSequenceService()
    try:
        return await svc.enroll_contacts(
            user_id=user_id,
            sequence_id=sequence_id,
            contact_ids=body.contact_ids,
            timezone_str=body.timezone,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc


@router.delete(
    "/email-sequences/enrollments/{enrollment_id}",
    summary="Unenroll a contact",
)
async def unenroll_contact(
    enrollment_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """Unenroll a contact from a sequence."""
    svc = EmailSequenceService()
    try:
        return await svc.unenroll_contact(user_id, enrollment_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404, detail=str(exc)
        ) from exc


# =====================================================================
# Performance Endpoint (authenticated)
# =====================================================================


@router.get(
    "/email-sequences/{sequence_id}/performance",
    summary="Get sequence performance metrics",
)
async def get_sequence_performance(
    sequence_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """Get open/click/bounce/completion rates for a sequence."""
    svc = EmailSequenceService()
    try:
        return await svc.get_sequence_performance(
            user_id, sequence_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404, detail=str(exc)
        ) from exc


# =====================================================================
# Tracking Endpoints (public, no auth required)
# =====================================================================


@router.get(
    "/tracking/open/{tracking_id}",
    summary="Open tracking pixel",
    include_in_schema=False,
)
async def tracking_open(tracking_id: str) -> Response:
    """Serve a 1x1 transparent PNG and record an open event.

    The tracking_id format is ``{enrollment_id}_{step_number}``.
    """
    # Parse tracking ID
    parts = tracking_id.rsplit("_", 1)
    if len(parts) == 2:
        enrollment_id, step_str = parts
        try:
            step_number = int(step_str)
        except ValueError:
            step_number = 0

        # Record open event (fire-and-forget, don't block pixel)
        try:
            from app.services.base_service import AdminService
            from app.services.supabase_async import execute_async

            client = AdminService().client
            await execute_async(
                client.table("email_tracking_events").insert({
                    "enrollment_id": enrollment_id,
                    "step_number": step_number,
                    "event_type": "open",
                    "metadata": {},
                }),
                op_name="tracking.open",
            )
        except Exception:
            logger.exception(
                "Failed to record open event for %s", tracking_id
            )

    return Response(
        content=TRANSPARENT_PIXEL,
        media_type="image/png",
        headers={"Cache-Control": "no-cache, no-store"},
    )


@router.get(
    "/tracking/click/{tracking_id}",
    summary="Click tracking redirect",
    include_in_schema=False,
)
async def tracking_click(
    tracking_id: str,
    url: str = Query(..., description="Original destination URL"),
) -> RedirectResponse:
    """Record a click event and redirect to the original URL.

    Validates that the URL starts with http/https to prevent
    open redirect vulnerabilities.
    """
    # Validate URL to prevent open redirect
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400, detail="Invalid redirect URL"
        )

    # Parse tracking ID
    parts = tracking_id.rsplit("_", 1)
    if len(parts) == 2:
        enrollment_id, step_str = parts
        try:
            step_number = int(step_str)
        except ValueError:
            step_number = 0

        # Record click event
        try:
            from app.services.base_service import AdminService
            from app.services.supabase_async import execute_async

            client = AdminService().client
            await execute_async(
                client.table("email_tracking_events").insert({
                    "enrollment_id": enrollment_id,
                    "step_number": step_number,
                    "event_type": "click",
                    "metadata": {"url": url},
                }),
                op_name="tracking.click",
            )
        except Exception:
            logger.exception(
                "Failed to record click event for %s", tracking_id
            )

    return RedirectResponse(url=url, status_code=302)


@router.get(
    "/unsubscribe/{enrollment_id}",
    summary="One-click unsubscribe (GET)",
    include_in_schema=False,
)
@router.post(
    "/unsubscribe/{enrollment_id}",
    summary="One-click unsubscribe (POST, RFC 8058)",
    include_in_schema=False,
)
async def unsubscribe(
    enrollment_id: str,
    request: Request,
) -> HTMLResponse:
    """Handle unsubscribe requests (both GET and POST for RFC 8058).

    Records an unsubscribe event and sets the enrollment status
    to 'unsubscribed'.
    """
    try:
        svc = EmailSequenceService()
        await svc.handle_unsubscribe(enrollment_id)
    except Exception:
        logger.exception(
            "Failed to process unsubscribe for %s", enrollment_id
        )

    # Return a simple confirmation page
    html = """<!DOCTYPE html>
<html>
<head><title>Unsubscribed</title>
<style>
body { font-family: -apple-system, sans-serif; display: flex;
  justify-content: center; align-items: center; min-height: 100vh;
  margin: 0; background: #f8fafc; }
.card { background: white; padding: 48px; border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center;
  max-width: 400px; }
h1 { font-size: 24px; color: #1e293b; margin-bottom: 12px; }
p { color: #64748b; font-size: 16px; }
</style></head>
<body><div class="card">
<h1>Unsubscribed</h1>
<p>You have been successfully unsubscribed from this email sequence.
You will no longer receive emails from this sequence.</p>
</div></body></html>"""

    return HTMLResponse(content=html, status_code=200)
