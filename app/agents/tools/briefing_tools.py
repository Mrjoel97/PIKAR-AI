"""Briefing tools for agents.

Provides tools for daily email briefing: viewing, refreshing,
approving drafts, dismissing items, and undoing auto-actions.
"""

from datetime import datetime, timezone
from typing import Any

# Tool context type
ToolContextType = Any


def _get_supabase():
    """Get Supabase service client."""
    from app.services.supabase import get_service_client

    return get_service_client()


def get_daily_briefing(tool_context: ToolContextType) -> dict[str, Any]:
    """Get the daily email briefing grouped by section.

    Queries email_triage for today's items and groups them by section:
    urgent, needs_reply, auto_handled, fyi.

    Args:
        tool_context: Agent tool context.

    Returns:
        Dict with sections (urgent, needs_reply, auto_handled, fyi) and counts.
    """
    try:
        db = _get_supabase()
        today = datetime.now(timezone.utc).date().isoformat()
        response = (
            db.table("email_triage")
            .select(
                "id, section, subject, sender, priority, status, action_type, created_at"
            )
            .gte("created_at", today)
            .execute()
        )
        items = response.data or []

        sections: dict[str, list[dict]] = {
            "urgent": [],
            "needs_reply": [],
            "auto_handled": [],
            "fyi": [],
        }

        for item in items:
            section = item.get("section") or item.get("action_type") or "fyi"
            if item.get("priority") == "urgent" or section == "urgent":
                sections["urgent"].append(item)
            elif section == "needs_reply":
                sections["needs_reply"].append(item)
            elif section in ("auto_handle", "auto_handled") or item.get("status") in (
                "auto_handled",
                "sent",
            ):
                sections["auto_handled"].append(item)
            else:
                sections["fyi"].append(item)

        return {
            "status": "ok",
            "date": today,
            "total": len(items),
            "sections": sections,
            "counts": {k: len(v) for k, v in sections.items()},
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to get briefing: {e}"}


def refresh_briefing(tool_context: ToolContextType) -> dict[str, Any]:
    """Trigger an on-demand email triage for the current user.

    Imports and calls EmailTriageWorker.process_user() to re-fetch
    and classify unread emails.

    Args:
        tool_context: Agent tool context.

    Returns:
        Dict with triage result status and counts.
    """
    try:
        import asyncio

        from app.services.email_triage_worker import EmailTriageWorker

        db = _get_supabase()
        user_id = tool_context.state.get("user_id", "")
        if not user_id:
            return {"status": "error", "message": "user_id not found in context state."}

        worker = EmailTriageWorker(supabase_client=db)

        # Fetch user prefs
        prefs_resp = (
            db.table("user_briefing_preferences")
            .select("preferences")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        prefs = (
            (prefs_resp.data or {}).get("preferences") or {} if prefs_resp.data else {}
        )

        result = asyncio.get_event_loop().run_until_complete(
            worker.process_user(user_id, prefs)
        )
        return result
    except Exception as e:
        return {"status": "error", "message": f"Failed to refresh briefing: {e}"}


def approve_draft(tool_context: ToolContextType, triage_item_id: str) -> dict[str, Any]:
    """Approve and send a draft reply for a triage item.

    Fetches the triage item, gets Gmail credentials from tool_context.state,
    sends the draft reply via GmailService.send_email(), and updates status to 'sent'.

    Args:
        tool_context: Agent tool context (must have google_provider_token in state).
        triage_item_id: UUID of the email_triage row to approve.

    Returns:
        Dict with send status and message ID.
    """
    try:
        from app.integrations.google.client import get_google_credentials
        from app.integrations.google.gmail import GmailService

        db = _get_supabase()

        # Fetch the triage item
        resp = (
            db.table("email_triage")
            .select("*")
            .eq("id", triage_item_id)
            .single()
            .execute()
        )
        item = resp.data
        if not item:
            return {
                "status": "error",
                "message": f"Triage item {triage_item_id} not found.",
            }

        draft_reply = item.get("draft_reply")
        if not draft_reply:
            return {
                "status": "error",
                "message": "No draft reply available for this item.",
            }

        # Build credentials from context state
        provider_token = tool_context.state.get("google_provider_token")
        refresh_token = tool_context.state.get("google_refresh_token")
        if not provider_token:
            return {
                "status": "error",
                "message": "Google authentication required.",
                "auth_required": True,
            }

        credentials = get_google_credentials(provider_token, refresh_token)
        gmail_service = GmailService(credentials)

        sender = item.get("sender", "")
        subject = item.get("subject", "")
        result = gmail_service.send_email(
            to=[sender],
            subject=f"Re: {subject}",
            body=draft_reply,
        )

        # Update status to sent
        db.table("email_triage").update(
            {"status": "sent", "acted_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", triage_item_id).execute()

        return {
            "status": "ok",
            "message": "Draft approved and sent.",
            "send_result": result,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to approve draft: {e}"}


def dismiss_item(tool_context: ToolContextType, triage_item_id: str) -> dict[str, Any]:
    """Dismiss a triage item by updating its status to 'dismissed'.

    Args:
        tool_context: Agent tool context.
        triage_item_id: UUID of the email_triage row to dismiss.

    Returns:
        Dict with success status.
    """
    try:
        db = _get_supabase()
        db.table("email_triage").update(
            {"status": "dismissed", "acted_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", triage_item_id).execute()
        return {"status": "ok", "message": f"Item {triage_item_id} dismissed."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to dismiss item: {e}"}


def undo_auto_action(
    tool_context: ToolContextType, triage_item_id: str
) -> dict[str, Any]:
    """Undo an auto-action on a triage item by reverting its status to 'pending'.

    Args:
        tool_context: Agent tool context.
        triage_item_id: UUID of the email_triage row to revert.

    Returns:
        Dict with success status.
    """
    try:
        db = _get_supabase()
        db.table("email_triage").update({"status": "pending", "acted_at": None}).eq(
            "id", triage_item_id
        ).execute()
        return {
            "status": "ok",
            "message": f"Auto-action undone for item {triage_item_id}.",
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to undo auto-action: {e}"}


# Export briefing tools
BRIEFING_TOOLS = [
    get_daily_briefing,
    refresh_briefing,
    approve_draft,
    dismiss_item,
    undo_auto_action,
]
