# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Gmail inbox tools for agents.

Provides tools for reading and managing inbox emails.
"""

import asyncio
from typing import Any

# Tool context type
ToolContextType = Any


def _get_gmail_reader(tool_context: ToolContextType):
    """Get GmailReader from tool context credentials.

    Args:
        tool_context: ADK tool context carrying auth state.

    Returns:
        Configured GmailReader instance.

    Raises:
        ValueError: When Google tokens are absent from tool context state.
    """
    from app.integrations.google.client import get_google_credentials
    from app.integrations.google.gmail_reader import GmailReader

    provider_token = tool_context.state.get("google_provider_token")
    refresh_token = tool_context.state.get("google_refresh_token")

    if not provider_token:
        raise ValueError("Google authentication required to access Gmail inbox.")

    credentials = get_google_credentials(provider_token, refresh_token)
    return GmailReader(credentials)


def read_inbox(
    tool_context: ToolContextType,
    max_results: int = 20,
    query: str = "is:unread",
) -> dict[str, Any]:
    """Read emails from the Gmail inbox.

    Lists messages matching the query, then fetches metadata for each one.

    Args:
        tool_context: Agent tool context.
        max_results: Maximum number of messages to retrieve (default 20).
        query: Gmail search query string (default "is:unread").

    Returns:
        Dict with status, emails list, and count.
    """
    try:
        reader = _get_gmail_reader(tool_context)
        list_result = reader.list_messages(query=query, max_results=max_results)

        if list_result["status"] != "success":
            return {
                "status": "error",
                "message": f"Failed to list messages: {list_result.get('error', 'unknown error')}",
            }

        messages = list_result.get("messages", [])
        emails: list[dict[str, Any]] = []

        for msg_stub in messages:
            msg_result = reader.get_message(msg_stub["id"], msg_format="metadata")
            if msg_result["status"] == "success":
                emails.append(msg_result["message"])

        return {
            "status": "success",
            "emails": emails,
            "count": len(emails),
        }
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to read inbox: {e}"}


def read_email(
    tool_context: ToolContextType,
    message_id: str,
) -> dict[str, Any]:
    """Read the full content of a single Gmail message.

    Args:
        tool_context: Agent tool context.
        message_id: The Gmail message ID to retrieve.

    Returns:
        Dict with status and full parsed message fields.
    """
    try:
        reader = _get_gmail_reader(tool_context)
        return reader.get_message(message_id, msg_format="full")
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to read email: {e}"}


def classify_email(
    tool_context: ToolContextType,
    message_id: str,
) -> dict[str, Any]:
    """Classify and triage a Gmail message.

    Fetches the full email then classifies it via EmailTriageService,
    persisting the result for briefing generation.

    Args:
        tool_context: Agent tool context.
        message_id: The Gmail message ID to classify.

    Returns:
        Dict with status and classification result.
    """
    try:
        reader = _get_gmail_reader(tool_context)
        msg_result = reader.get_message(message_id, msg_format="full")

        if msg_result["status"] != "success":
            return {
                "status": "error",
                "message": f"Could not fetch email for classification: {msg_result.get('error', 'unknown')}",
            }

        # EmailTriageService requires async — bridge via event loop
        try:
            from app.services.email_triage import (
                EmailTriageService,  # type: ignore[import-not-found]
            )

            user_id: str | None = tool_context.state.get("user_id")
            triage_service = EmailTriageService()
            loop = asyncio.get_event_loop()
            classification = loop.run_until_complete(
                triage_service.classify_email(
                    email=msg_result["message"],
                    user_id=user_id,
                )
            )
            return {
                "status": "success",
                "message_id": message_id,
                "classification": classification,
            }
        except ImportError:
            # EmailTriageService not yet available — return raw message data
            return {
                "status": "success",
                "message_id": message_id,
                "classification": None,
                "note": "Email triage service not available; returning unclassified message.",
                "message": msg_result["message"],
            }
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to classify email: {e}"}


def archive_email(
    tool_context: ToolContextType,
    message_id: str,
) -> dict[str, Any]:
    """Archive a Gmail message by removing it from the inbox.

    Removes the INBOX and UNREAD labels from the message.

    Args:
        tool_context: Agent tool context.
        message_id: The Gmail message ID to archive.

    Returns:
        Dict with status and updated label state.
    """
    try:
        reader = _get_gmail_reader(tool_context)
        return reader.modify_message(message_id, remove_labels=["INBOX", "UNREAD"])
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to archive email: {e}"}


def label_email(
    tool_context: ToolContextType,
    message_id: str,
    add_labels: list[str] | None = None,
    remove_labels: list[str] | None = None,
) -> dict[str, Any]:
    """Modify labels on a Gmail message.

    Use this to star, mark read/unread, or apply custom labels.

    Args:
        tool_context: Agent tool context.
        message_id: The Gmail message ID to modify.
        add_labels: Label IDs to add (e.g. ["STARRED"]).
        remove_labels: Label IDs to remove (e.g. ["UNREAD"]).

    Returns:
        Dict with status and updated label state.
    """
    try:
        reader = _get_gmail_reader(tool_context)
        return reader.modify_message(
            message_id,
            add_labels=add_labels,
            remove_labels=remove_labels,
        )
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to label email: {e}"}


# Export Gmail inbox tools
GMAIL_INBOX_TOOLS = [
    read_inbox,
    read_email,
    classify_email,
    archive_email,
    label_email,
]
