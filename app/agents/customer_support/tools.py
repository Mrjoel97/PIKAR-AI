# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tools for the Customer Support Agent."""


async def create_ticket(
    subject: str, description: str, customer_email: str, priority: str = "normal"
) -> dict:
    """Create a new support ticket.

    Args:
        subject: Ticket subject.
        description: Problem description.
        customer_email: Email of the customer.
        priority: Priority (low, normal, high, urgent).

    Returns:
        Dictionary containing the created ticket.
    """
    from app.services.support_ticket_service import SupportTicketService

    try:
        from app.services.request_context import get_current_user_id

        service = SupportTicketService()
        ticket = await service.create_ticket(
            subject,
            description,
            customer_email,
            priority,
            user_id=get_current_user_id(),
        )
        return {"success": True, "ticket": ticket}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_ticket(ticket_id: str) -> dict:
    """Retrieve a ticket by ID.

    Args:
        ticket_id: The unique ticket ID.

    Returns:
        Dictionary containing the ticket details.
    """
    from app.services.support_ticket_service import SupportTicketService

    try:
        from app.services.request_context import get_current_user_id

        service = SupportTicketService()
        ticket = await service.get_ticket(ticket_id, user_id=get_current_user_id())
        return {"success": True, "ticket": ticket}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_ticket(
    ticket_id: str, status: str = None, resolution: str = None
) -> dict:
    """Update a ticket status or resolution.

    Args:
        ticket_id: The unique ticket ID.
        status: New status (new, assigned, in_progress, resolved, closed).
        resolution: Internal note or resolution details.

    Returns:
        Dictionary confirming the update.
    """
    from app.services.support_ticket_service import SupportTicketService

    try:
        from app.services.request_context import get_current_user_id

        service = SupportTicketService()
        ticket = await service.update_ticket(
            ticket_id,
            status=status,
            resolution=resolution,
            user_id=get_current_user_id(),
        )
        return {"success": True, "ticket": ticket}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_tickets(status: str = None, priority: str = None) -> dict:
    """List tickets with optional filters.

    Args:
        status: Filter by status.
        priority: Filter by priority.

    Returns:
        Dictionary containing list of tickets.
    """
    from app.services.support_ticket_service import SupportTicketService

    try:
        from app.services.request_context import get_current_user_id

        service = SupportTicketService()
        tickets = await service.list_tickets(
            status=status, priority=priority, user_id=get_current_user_id()
        )
        return {"success": True, "tickets": tickets, "count": len(tickets)}
    except Exception as e:
        return {"success": False, "error": str(e), "tickets": []}
