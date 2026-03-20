"""Support tickets router — CRUD for customer support tickets."""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id
from app.services.support_ticket_service import SupportTicketService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support", tags=["Support"])


class CreateTicketRequest(BaseModel):
    """Request body for creating a support ticket."""

    subject: str
    description: str
    customer_email: str
    priority: Literal["low", "normal", "high", "urgent"] = "normal"


class UpdateTicketRequest(BaseModel):
    """Request body for updating a support ticket."""

    status: (
        Literal["new", "open", "in_progress", "waiting", "resolved", "closed"] | None
    ) = None
    priority: Literal["low", "normal", "high", "urgent"] | None = None
    assigned_to: str | None = None
    resolution: str | None = None


class TicketResponse(BaseModel):
    """Response model for a support ticket."""

    id: str
    user_id: str
    subject: str
    description: str
    customer_email: str
    priority: str
    status: str
    assigned_to: str | None = None
    resolution: str | None = None
    created_at: str
    updated_at: str


@router.get("/tickets", response_model=list[TicketResponse])
@limiter.limit(get_user_persona_limit)
async def list_tickets(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    status: str | None = None,
    priority: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List support tickets for the current user."""
    service = SupportTicketService()
    tickets = await service.list_tickets(
        status=status,
        priority=priority,
        user_id=user_id,
    )
    return tickets[offset : offset + limit]


@router.post("/tickets", response_model=TicketResponse, status_code=201)
@limiter.limit(get_user_persona_limit)
async def create_ticket(
    request: Request,
    body: CreateTicketRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Create a new support ticket."""
    service = SupportTicketService()
    ticket = await service.create_ticket(
        subject=body.subject,
        description=body.description,
        customer_email=body.customer_email,
        priority=body.priority,
        user_id=user_id,
    )
    return ticket


@router.patch("/tickets/{ticket_id}", response_model=TicketResponse)
@limiter.limit(get_user_persona_limit)
async def update_ticket(
    request: Request,
    ticket_id: str,
    body: UpdateTicketRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Update a support ticket."""
    service = SupportTicketService()
    try:
        ticket = await service.update_ticket(
            ticket_id=ticket_id,
            status=body.status,
            priority=body.priority,
            assigned_to=body.assigned_to,
            resolution=body.resolution,
            user_id=user_id,
        )
        return ticket
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/tickets/{ticket_id}", status_code=204)
@limiter.limit(get_user_persona_limit)
async def delete_ticket(
    request: Request,
    ticket_id: str,
    user_id: str = Depends(get_current_user_id),
) -> None:
    """Delete a support ticket."""
    service = SupportTicketService()
    deleted = await service.delete_ticket(ticket_id=ticket_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Ticket not found")
