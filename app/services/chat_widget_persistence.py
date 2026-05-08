# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Server-side persistence for chat-generated widgets.

The `chat_widgets` table mirrors the client-side `WidgetDisplayService`
storage so that durable agent deliverables (charts, generated documents,
markdown reports, media previews, …) survive cache wipes, browser
swaps and stale auth tokens.

Historically the only writer was the browser's fire-and-forget upsert,
which silently fails when the user's Supabase auth token has aged out.
This module gives backend tools and the SSE post-processor a service-role
write path so persistence is RLS-bypassing and never auth-stale.

The contract is intentionally tiny:

    persist_chat_widget(
        user_id=...,            # may be None — we no-op rather than crash
        widget=...,             # standard `WidgetDefinition` dict
        session_id=...,         # may be None — we resolve from widget.data
        is_pinned=False,
    )

All errors are caught and logged: persistence is best-effort by design,
the agent's reply must never fail because Supabase blinked.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


def _resolve_widget_id(widget: dict[str, Any]) -> str:
    """Return the widget's stable id, minting a UUID4 if missing.

    Mirrors the frontend `WidgetDisplayService.saveWidget` behaviour so
    re-upserts from either side land on the same row.
    """
    candidate = widget.get("widget_id") or widget.get("id")
    if isinstance(candidate, str) and candidate:
        return candidate
    minted = str(uuid.uuid4())
    widget["widget_id"] = minted
    return minted


def _resolve_session_id(
    widget: dict[str, Any], session_id: str | None
) -> str | None:
    """Pull the session id from the explicit kwarg or the widget envelope."""
    if session_id:
        return session_id
    data = widget.get("data")
    if isinstance(data, dict):
        candidate = data.get("session_id") or data.get("sessionId")
        if isinstance(candidate, str) and candidate:
            return candidate
    workspace = widget.get("workspace")
    if isinstance(workspace, dict):
        candidate = workspace.get("sessionId") or workspace.get("session_id")
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def persist_chat_widget(
    *,
    user_id: str | None,
    widget: dict[str, Any],
    session_id: str | None = None,
    is_pinned: bool = False,
    is_minimized: bool = False,
) -> bool:
    """Best-effort upsert of a widget envelope into `chat_widgets`.

    Returns True when the row was written, False otherwise. Failures are
    logged at WARNING and never raised — callers should treat this as
    fire-and-forget.
    """
    if not user_id:
        logger.debug("persist_chat_widget skipped: missing user_id")
        return False
    if not isinstance(widget, dict) or not widget.get("type"):
        logger.debug("persist_chat_widget skipped: invalid widget shape")
        return False

    resolved_session = _resolve_session_id(widget, session_id)
    if not resolved_session:
        logger.debug("persist_chat_widget skipped: missing session_id")
        return False

    widget_id = _resolve_widget_id(widget)

    try:
        from app.services.supabase import get_service_client

        client = get_service_client()
        if client is None:
            logger.debug("persist_chat_widget skipped: no service client")
            return False

        client.table("chat_widgets").upsert(
            {
                "id": widget_id,
                "user_id": user_id,
                "session_id": resolved_session,
                "widget": widget,
                "is_pinned": is_pinned,
                "is_minimized": is_minimized,
            }
        ).execute()
        return True
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning("chat_widgets persistence failed: %s", exc)
        return False


__all__ = ["persist_chat_widget"]
