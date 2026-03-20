# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Google Forms tools for agents.

Provides tools for creating surveys and collecting customer feedback.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Tool context type
ToolContextType = Any


def _track_created_form(
    user_id: str | None,
    agent_id: str | None,
    form_id: str,
    title: str,
    url: str,
    form_type: str = "form",
    metadata: dict | None = None,
) -> None:
    """Track a created Google Form in the database for Knowledge Vault."""
    try:
        from app.services.supabase import get_service_client

        if not user_id:
            logger.warning("Cannot track form: missing user_id")
            return

        client = get_service_client()
        client.table("agent_google_docs").insert(
            {
                "user_id": user_id,
                "agent_id": agent_id,
                "doc_id": form_id,
                "title": title,
                "doc_url": url,
                "doc_type": form_type,
                "metadata": metadata or {},
            }
        ).execute()

        logger.info(f"Tracked Google Form: {title} ({form_id}) for user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to track created form: {e}")


def _get_forms_service(tool_context: ToolContextType):
    """Get Forms service from tool context credentials."""
    from app.integrations.google.client import get_google_credentials
    from app.integrations.google.forms import GoogleFormsService

    provider_token = tool_context.state.get("google_provider_token")
    refresh_token = tool_context.state.get("google_refresh_token")

    if not provider_token:
        raise ValueError("Google authentication required for Forms features.")

    credentials = get_google_credentials(provider_token, refresh_token)
    return GoogleFormsService(credentials)


def create_feedback_form(
    tool_context: ToolContextType,
    title: str,
    business_name: str,
    custom_questions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a customer feedback survey form.

    Use this to set up customer feedback collection for a business.
    Creates a form with standard satisfaction questions plus any custom ones.

    Args:
        tool_context: Agent tool context.
        title: Form title (e.g., "Customer Satisfaction Survey").
        business_name: Name of the business collecting feedback.
        custom_questions: Optional custom questions. Each dict has:
            - title: Question text
            - type: "text", "paragraph", "multiple_choice", "checkbox", "scale"
            - options: For multiple_choice/checkbox types
            - required: Whether answer is required

    Returns:
        Dict with form URL for sharing.
    """
    try:
        service = _get_forms_service(tool_context)
        form = service.create_feedback_form(
            title=title,
            business_name=business_name,
            questions=custom_questions,
        )

        # Store form ID for later response retrieval
        tool_context.state["feedback_form_id"] = form.id
        tool_context.state["feedback_form_url"] = form.url

        # Track the created form for the Knowledge Vault
        user_id = tool_context.state.get("user_id")
        agent_id = tool_context.state.get("agent_id")
        _track_created_form(
            user_id=user_id,
            agent_id=agent_id,
            form_id=form.id,
            title=form.title,
            url=form.url,
            form_type="feedback_form",
            metadata={"business_name": business_name},
        )

        return {
            "status": "success",
            "message": f"Feedback form '{title}' created",
            "form": {
                "id": form.id,
                "title": form.title,
                "share_url": form.url,
                "edit_url": form.edit_url,
            },
            "next_steps": [
                "Share the form URL with customers",
                "Use get_form_responses to analyze feedback",
            ],
        }
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to create form: {e}"}


def create_custom_form(
    tool_context: ToolContextType,
    title: str,
    description: str,
    questions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create a custom Google Form with specific questions.

    Args:
        tool_context: Agent tool context.
        title: Form title.
        description: Form description.
        questions: List of questions. Each dict has:
            - title: Question text
            - type: "text", "paragraph", "multiple_choice", "checkbox", "scale", "date"
            - options: For multiple_choice/checkbox (list of strings)
            - required: Whether answer is required

    Returns:
        Dict with form details.
    """
    try:
        service = _get_forms_service(tool_context)

        # Create the form
        form = service.create_form(title, description)

        # Add each question
        for i, q in enumerate(questions):
            service.add_question(
                form_id=form.id,
                title=q.get("title", ""),
                question_type=q.get("type", "text"),
                options=q.get("options"),
                required=q.get("required", False),
                index=i,
            )

        # Track the created form for the Knowledge Vault
        user_id = tool_context.state.get("user_id")
        agent_id = tool_context.state.get("agent_id")
        _track_created_form(
            user_id=user_id,
            agent_id=agent_id,
            form_id=form.id,
            title=form.title,
            url=form.url,
            form_type="custom_form",
            metadata={"description": description, "question_count": len(questions)},
        )

        return {
            "status": "success",
            "message": f"Form '{title}' created with {len(questions)} questions",
            "form": {
                "id": form.id,
                "title": form.title,
                "share_url": form.url,
                "edit_url": form.edit_url,
            },
        }
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to create form: {e}"}


def get_form_responses(
    tool_context: ToolContextType,
    form_id: str | None = None,
) -> dict[str, Any]:
    """Get responses from a Google Form.

    Use this to analyze feedback collected from customers.

    Args:
        tool_context: Agent tool context.
        form_id: The form ID. Uses stored feedback form if not provided.

    Returns:
        Dict with responses and summary.
    """
    try:
        service = _get_forms_service(tool_context)

        # Use stored form if not specified
        if not form_id:
            form_id = tool_context.state.get("feedback_form_id")

        if not form_id:
            return {
                "status": "error",
                "message": "No form ID provided. Create a form first or specify form_id.",
            }

        # Get form details for question mapping
        form = service.get_form(form_id)
        responses = service.get_responses(form_id)

        return {
            "status": "success",
            "form_title": form.get("title"),
            "response_count": len(responses),
            "questions": form.get("questions", []),
            "responses": responses,
        }
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to get responses: {e}"}


def analyze_feedback(
    tool_context: ToolContextType,
    form_id: str | None = None,
) -> dict[str, Any]:
    """Analyze customer feedback from a form.

    Retrieves responses and provides analysis summary.

    Args:
        tool_context: Agent tool context.
        form_id: Optional form ID.

    Returns:
        Dict with feedback analysis.
    """
    try:
        service = _get_forms_service(tool_context)

        if not form_id:
            form_id = tool_context.state.get("feedback_form_id")

        if not form_id:
            return {"status": "error", "message": "No form ID available."}

        responses = service.get_responses(form_id)

        if not responses:
            return {
                "status": "success",
                "message": "No responses yet",
                "response_count": 0,
            }

        # Basic analysis
        return {
            "status": "success",
            "response_count": len(responses),
            "first_response": responses[0].get("submitted_at") if responses else None,
            "latest_response": responses[-1].get("submitted_at") if responses else None,
            "summary": f"Collected {len(responses)} feedback responses",
            "next_steps": [
                "Review individual responses for insights",
                "Create a report summarizing key themes",
                "Identify improvement areas from feedback",
            ],
        }
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to analyze: {e}"}


# Export Forms tools
FORMS_TOOLS = [
    create_feedback_form,
    create_custom_form,
    get_form_responses,
    analyze_feedback,
]
