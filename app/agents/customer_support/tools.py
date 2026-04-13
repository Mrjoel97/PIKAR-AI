# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

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
    ticket_id: str, status: str | None = None, resolution: str | None = None
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


async def list_tickets(status: str | None = None, priority: str | None = None) -> dict:
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


_SCENARIO_TEMPLATES: dict[str, dict[str, str]] = {
    "refund": {
        "subject": "Your Refund Request — We're On It",
        "tone": "empathetic",
        "body_template": (
            "Dear {customer_name},\n\n"
            "Thank you for reaching out. I completely understand your concern and sincerely "
            "apologize for the inconvenience caused.\n\n"
            "Regarding your request: {context}\n\n"
            "We have initiated your refund. Here's what to expect:\n"
            "1. Your refund request has been logged and approved.\n"
            "2. Funds will be returned to your original payment method within 3-5 business days.\n"
            "3. You will receive a confirmation email once the refund is processed.\n\n"
            "If you have any further questions, please don't hesitate to reach out — we're here to help.\n\n"
            "Warm regards,\n"
            "Customer Success Team"
        ),
    },
    "shipping_delay": {
        "subject": "Update on Your Order — We Apologize for the Delay",
        "tone": "apologetic",
        "body_template": (
            "Dear {customer_name},\n\n"
            "I sincerely apologize for the delay with your order. I understand how frustrating "
            "it can be when an expected delivery doesn't arrive on time.\n\n"
            "Details: {context}\n\n"
            "Here's what we're doing to resolve this:\n"
            "1. We are actively investigating the cause of the delay with our shipping partner.\n"
            "2. Your order is being prioritized for the next available dispatch.\n"
            "3. We will send you an updated tracking link as soon as your package is on its way.\n\n"
            "As a gesture of goodwill for this inconvenience, please let us know if there is "
            "anything further we can do to make this right.\n\n"
            "Sincerely,\n"
            "Customer Success Team"
        ),
    },
    "complaint": {
        "subject": "We Hear You — Taking Action on Your Concern",
        "tone": "validating",
        "body_template": (
            "Dear {customer_name},\n\n"
            "Thank you for bringing this to our attention. Your experience matters to us, "
            "and I want to assure you that we take your concern very seriously.\n\n"
            "I understand your frustration regarding: {context}\n\n"
            "Here is our action plan to address this:\n"
            "1. We are investigating the root cause of the issue immediately.\n"
            "2. A specialist has been assigned to your case.\n"
            "3. We will follow up with a resolution within 24 hours.\n\n"
            "Your satisfaction is our top priority. We are committed to making this right "
            "and ensuring this doesn't happen again.\n\n"
            "With sincere apologies,\n"
            "Customer Success Team"
        ),
    },
    "follow_up": {
        "subject": "Following Up on Your Support Request",
        "tone": "professional",
        "body_template": (
            "Dear {customer_name},\n\n"
            "I wanted to reach out and provide you with a status update on your request.\n\n"
            "Context: {context}\n\n"
            "Current status:\n"
            "1. Your case is actively being worked on by our team.\n"
            "2. We have made the following progress: please see the details below.\n"
            "3. Expected resolution: we will keep you updated every 24 hours until resolved.\n\n"
            "Please feel free to reply to this email if you have any questions or additional "
            "information to share. We appreciate your patience.\n\n"
            "Best regards,\n"
            "Customer Success Team"
        ),
    },
    "apology": {
        "subject": "Our Sincere Apology",
        "tone": "sincere",
        "body_template": (
            "Dear {customer_name},\n\n"
            "I am writing to sincerely apologize for the experience you had.\n\n"
            "Regarding: {context}\n\n"
            "We take full responsibility for what occurred and want to assure you that:\n"
            "1. We have identified the root cause of the issue.\n"
            "2. Corrective steps have been implemented to prevent recurrence.\n"
            "3. We are reviewing our processes to ensure this standard of service is never repeated.\n\n"
            "Your trust means everything to us, and we are committed to earning it back. "
            "Please let us know how we can make this right for you.\n\n"
            "With deepest apologies,\n"
            "Customer Success Team"
        ),
    },
    "general": {
        "subject": "Re: Your Inquiry — We're Here to Help",
        "tone": "professional",
        "body_template": (
            "Dear {customer_name},\n\n"
            "Thank you for contacting us. We're happy to assist you.\n\n"
            "Regarding your inquiry: {context}\n\n"
            "Here are the next steps:\n"
            "1. Our team has reviewed your request.\n"
            "2. We will provide a detailed response within 1 business day.\n"
            "3. If you need immediate assistance, please contact us at your preferred channel.\n\n"
            "We appreciate you reaching out and look forward to resolving this for you.\n\n"
            "Best regards,\n"
            "Customer Success Team"
        ),
    },
}


async def draft_customer_response(
    scenario: str,
    context: str,
    customer_name: str = "Customer",
) -> dict:
    """Draft a professional customer-facing response for common support scenarios.

    Args:
        scenario: Type of scenario - 'refund', 'shipping_delay', 'complaint',
            'follow_up', 'apology', or 'general'.
        context: Specific details about the customer's situation.
        customer_name: Customer's name for personalization.

    Returns:
        Dict with success flag and draft containing subject, body, tone, and scenario fields.
    """
    try:
        template = _SCENARIO_TEMPLATES.get(scenario, _SCENARIO_TEMPLATES["general"])
        body = template["body_template"].format(
            customer_name=customer_name,
            context=context,
        )
        return {
            "success": True,
            "draft": {
                "subject": template["subject"],
                "body": body,
                "tone": template["tone"],
                "scenario": scenario,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_customer_health_dashboard() -> dict:
    """Get customer health dashboard showing ticket metrics, sentiment, and churn risk.

    Returns a comprehensive dashboard with:
    - Open ticket count and resolution rate
    - Average resolution time in hours
    - Sentiment breakdown (positive/neutral/negative)
    - Churn risk level and contributing factors

    Returns:
        Dictionary containing the health dashboard data.
    """
    from app.services.customer_health_service import CustomerHealthService

    try:
        from app.services.request_context import get_current_user_id

        result = await CustomerHealthService().get_health_dashboard(
            user_id=get_current_user_id()
        )
        return {"success": True, "dashboard": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def create_ticket_from_channel(
    channel: str,
    sender_email: str,
    subject: str,
    body: str,
    channel_message_id: str = "",
) -> dict:
    """Auto-create a support ticket from an inbound channel message.

    Use this when processing incoming emails, chat messages, or webhook
    notifications that should become support tickets.

    Args:
        channel: Source channel - 'email', 'chat', 'webhook', or 'api'.
        sender_email: Email of the person who sent the message.
        subject: Subject or title from the channel message.
        body: Full message body content.
        channel_message_id: Optional ID from the source channel for dedup.

    Returns:
        Dictionary containing the created ticket with source metadata.
    """
    from app.services.support_ticket_service import SupportTicketService

    try:
        from app.services.request_context import get_current_user_id

        description = body
        if channel_message_id:
            description = (
                f"{body}\n\n[Source: {channel}, Message ID: {channel_message_id}]"
            )

        service = SupportTicketService()
        ticket = await service.create_ticket(
            subject=subject,
            description=description,
            customer_email=sender_email,
            priority="normal",
            status="new",
            user_id=get_current_user_id(),
            source=channel,
        )
        return {"success": True, "ticket": ticket}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def suggest_faq_from_tickets(min_similar: int = 3) -> dict:
    """Analyze resolved tickets for patterns and suggest FAQ entries.

    Looks for 3+ resolved tickets with similar subjects and auto-generates
    FAQ content from the resolution patterns.

    Args:
        min_similar: Minimum number of similar resolved tickets to trigger suggestion (default 3).

    Returns:
        Dict with faq_suggestions list, each containing title, content,
        source_ticket_count, and source_ticket_ids.
    """
    from app.services.support_ticket_service import SupportTicketService

    try:
        service = SupportTicketService()
        groups = await service.find_similar_resolved_tickets(min_count=min_similar)

        if not groups:
            return {
                "success": True,
                "faq_suggestions": [],
                "message": (
                    f"Not enough similar resolved tickets to suggest FAQ entries. "
                    f"Need at least {min_similar} similar resolved tickets."
                ),
            }

        faq_suggestions = []
        for group in groups:
            subject_pattern = group["subject_pattern"]
            tickets = group["tickets"]

            # Collect unique resolutions (non-empty)
            seen: set[str] = set()
            unique_resolutions: list[str] = []
            for ticket in tickets:
                resolution = (ticket.get("resolution") or "").strip()
                normalized = resolution.lower()
                if resolution and normalized not in seen:
                    seen.add(normalized)
                    unique_resolutions.append(resolution)

            # Build FAQ content from resolution steps
            if unique_resolutions:
                steps = "\n".join(
                    f"{i + 1}. {step}" for i, step in enumerate(unique_resolutions)
                )
                content = f"Common solutions for this issue:\n\n{steps}"
            else:
                content = "Please contact support for assistance with this issue."

            # Clean title
            title_text = subject_pattern.strip().title()
            title = f"How to resolve: {title_text}"

            faq_suggestions.append(
                {
                    "title": title,
                    "content": content,
                    "source_ticket_count": group["count"],
                    "source_ticket_ids": [t["id"] for t in tickets],
                }
            )

        return {"success": True, "faq_suggestions": faq_suggestions}
    except Exception as e:
        return {"success": False, "error": str(e)}
