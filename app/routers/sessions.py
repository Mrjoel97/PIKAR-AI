# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""User-scoped chat sessions API.

Returns the authenticated user's chat session list with derived title and
preview. This replaces the frontend's direct Supabase queries (which did
N+1 lookups for titles/previews) with a single optimized backend call,
and also gives sign-in-from-another-device users a way to recover sessions
whose ids are not in this device's localStorage.
"""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions"])

AGENTS_APP_NAME = "agents"
DEFAULT_LIMIT = 50
MAX_LIMIT = 200
TITLE_MAX_LEN = 60
PREVIEW_MAX_LEN = 100


class SessionSummary(BaseModel):
    id: str = Field(description="Session id (matches frontend session_id)")
    title: str
    preview: str | None = None
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]
    count: int


def _truncate(text: str, max_len: int) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[:max_len].rstrip() + "..."


def _extract_message_text(event_data: dict[str, Any] | None) -> str:
    """Pull the user-visible text from an ADK event payload."""
    if not isinstance(event_data, dict):
        return ""
    content = event_data.get("content")
    if isinstance(content, dict):
        parts = content.get("parts")
        if isinstance(parts, list):
            return "".join(
                str(part.get("text", "")) for part in parts if isinstance(part, dict)
            )
    if isinstance(content, str):
        return content
    text = event_data.get("text")
    if isinstance(text, str):
        return text
    return ""


def _is_user_event(event_data: dict[str, Any] | None) -> bool:
    if not isinstance(event_data, dict):
        return False
    role = (
        event_data.get("source") or event_data.get("role") or event_data.get("author")
    )
    return role in {"user", "human"}


def _is_agent_event(event_data: dict[str, Any] | None) -> bool:
    if not isinstance(event_data, dict):
        return False
    role = (
        event_data.get("source") or event_data.get("role") or event_data.get("author")
    )
    if not role:
        return False
    return role not in {"user", "human", "system"}


def _fallback_title_from_session_id(session_id: str) -> str:
    if session_id.startswith("session-"):
        try:
            ts_str = session_id.split("-", 2)[1]
            ts_ms = int(ts_str)
            from datetime import datetime, timezone

            return f"Chat from {datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime('%b %-d')}"
        except (IndexError, ValueError):
            pass
    return "Untitled Chat"


@router.get("", response_model=SessionListResponse)
@limiter.limit(get_user_persona_limit)
async def list_sessions(
    request: Request,
    user_id: Annotated[str, Depends(get_current_user_id)],
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
):
    """List the authenticated user's chat sessions, most recent first.

    Each session entry includes a derived title and preview, computed once
    on the server to avoid N+1 lookups from the client. Title falls back to
    the first user message (truncated) when ``state.title`` is not cached;
    preview falls back to the most recent agent message text.
    """
    supabase = get_service_client()

    try:
        sessions_resp = (
            supabase.table("sessions")
            .select("session_id, state, created_at, updated_at")
            .eq("user_id", user_id)
            .eq("app_name", AGENTS_APP_NAME)
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        )
    except Exception as exc:
        logger.error(
            "Failed to load sessions for user=%s: %r", user_id, exc, exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to load sessions") from exc

    rows: list[dict[str, Any]] = list(sessions_resp.data or [])
    if not rows:
        return SessionListResponse(sessions=[], count=0)

    cached_titles: dict[str, str] = {}
    cached_previews: dict[str, str] = {}
    for row in rows:
        state = row.get("state") or {}
        if not isinstance(state, dict):
            state = {}
        sid = row["session_id"]
        title = state.get("title")
        preview = state.get("lastMessage")
        if isinstance(title, str) and title.strip():
            cached_titles[sid] = title.strip()
        if isinstance(preview, str) and preview.strip():
            cached_previews[sid] = preview.strip()

    sessions_needing_lookup = [
        row["session_id"]
        for row in rows
        if row["session_id"] not in cached_titles
        or row["session_id"] not in cached_previews
    ]

    derived_titles: dict[str, str] = {}
    derived_previews: dict[str, str] = {}

    if sessions_needing_lookup:
        try:
            events_resp = (
                supabase.table("session_events")
                .select("session_id, event_data, event_index")
                .in_("session_id", sessions_needing_lookup)
                .eq("app_name", AGENTS_APP_NAME)
                .eq("user_id", user_id)
                .is_("superseded_by", None)
                .order("event_index", desc=False)
                .execute()
            )
            for event in events_resp.data or []:
                sid = event.get("session_id")
                event_data = event.get("event_data")
                if not sid:
                    continue
                if sid not in derived_titles and _is_user_event(event_data):
                    text = _extract_message_text(event_data)
                    if text.strip():
                        derived_titles[sid] = _truncate(text, TITLE_MAX_LEN)
                if _is_agent_event(event_data):
                    text = _extract_message_text(event_data)
                    if text.strip():
                        derived_previews[sid] = _truncate(text, PREVIEW_MAX_LEN)
        except Exception as exc:
            logger.warning(
                "Failed to derive session titles/previews for user=%s: %r",
                user_id,
                exc,
            )

    summaries: list[SessionSummary] = []
    for row in rows:
        sid = row["session_id"]
        title = (
            cached_titles.get(sid)
            or derived_titles.get(sid)
            or _fallback_title_from_session_id(sid)
        )
        preview = cached_previews.get(sid) or derived_previews.get(sid)
        summaries.append(
            SessionSummary(
                id=sid,
                title=title,
                preview=preview,
                created_at=str(row.get("created_at") or ""),
                updated_at=str(row.get("updated_at") or ""),
            )
        )

    return SessionListResponse(sessions=summaries, count=len(summaries))
