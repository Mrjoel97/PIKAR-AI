# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Admin chat SSE endpoint with session persistence and confirmation handling.

Provides:
- POST /admin/chat — streams AdminAgent responses via SSE
- GET /admin/chat/sessions — list admin's chat sessions
- GET /admin/chat/history/{session_id} — load message history for a session

Session persistence is managed in admin_chat_sessions and
admin_chat_messages Supabase tables (from migration 20260321300000).
Confirmation tokens are stored in Redis and consumed atomically.
All interactions are logged to admin_audit_log.
"""

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.middleware.admin_auth import require_admin
from app.middleware.rate_limiter import limiter
from app.services.admin_audit import log_admin_action
from app.services.confirmation_tokens import (
    consume_confirmation_token,
    store_confirmation_token,
)
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

router = APIRouter()

# SSE stream maximum duration (seconds)
_SSE_MAX_DURATION_S = 300

# ADK app name used for admin sessions (separate from the executive agent)
_ADMIN_APP_NAME = "admin"


# =============================================================================
# Request / response models
# =============================================================================


class AdminChatRequest(BaseModel):
    """Request body for POST /admin/chat."""

    session_id: str | None = None
    message: str
    confirmation_token: str | None = None


# =============================================================================
# Helper functions (also imported by unit tests)
# =============================================================================


async def _get_or_create_session(
    session_id: str | None,
    admin_user_id: str,
    message: str,
) -> str:
    """Return an existing session id (after ownership check) or create a new one.

    Args:
        session_id: Existing session id, or None to create a new session.
        admin_user_id: The id of the authenticated admin user.
        message: The user's message (used as session title on creation).

    Returns:
        The resolved session id string.

    Raises:
        HTTPException 403: If session_id is provided but is not owned by
            admin_user_id.
    """
    client = get_service_client()

    if session_id is None:
        # Create a new session
        title = message[:50]
        result = (
            client.table("admin_chat_sessions")
            .insert({"admin_user_id": admin_user_id, "title": title})
            .execute()
        )
        new_id: str = result.data[0]["id"]
        logger.debug("Created admin_chat_session %s for user %s", new_id, admin_user_id)
        return new_id

    # Verify ownership
    result = (
        client.table("admin_chat_sessions")
        .select("id")
        .eq("id", session_id)
        .eq("admin_user_id", admin_user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=403,
            detail="Session not found or not owned by this admin user",
        )

    # Touch updated_at
    try:
        client.table("admin_chat_sessions").update({"updated_at": "now()"}).eq(
            "id", session_id
        ).execute()
    except Exception as exc:
        logger.warning("Failed to update session updated_at: %s", exc)

    return session_id


async def _persist_message(
    session_id: str,
    role: str,
    content: str,
) -> None:
    """Insert a single message row into admin_chat_messages.

    Args:
        session_id: The owning session's id.
        role: Message author: "user" or "agent".
        content: The plain-text message content.
    """
    client = get_service_client()
    try:
        client.table("admin_chat_messages").insert(
            {
                "session_id": session_id,
                "role": role,
                "content": content,
            }
        ).execute()
        logger.debug("Persisted %s message for session %s", role, session_id)
    except Exception as exc:
        logger.error(
            "Failed to persist %s message for session %s: %s", role, session_id, exc
        )


async def _consume_token_or_error(token: str) -> dict | None:
    """Atomically consume a confirmation token.

    Args:
        token: The UUID token string to consume.

    Returns:
        The token payload dict if valid, or None if expired / already used.
    """
    payload = await consume_confirmation_token(token)
    if payload is None:
        logger.warning("Confirmation token %s expired or already consumed", token)
    return payload


# =============================================================================
# ADK runner factory (per-request, lightweight)
# =============================================================================

# Alias for easier patching in unit tests
from app.services.agent_config_service import (
    get_agent_config as get_agent_config_from_service,
)


async def _make_admin_runner():  # type: ignore[return]
    """Create a one-shot ADK Runner wrapping a per-request AdminAgent instance.

    Fetches live instructions for the AdminAgent from ``admin_agent_configs``
    before each request (RESEARCH.md Pitfall 1). When the DB returns a custom
    instruction that is not a placeholder, it is passed to
    ``create_admin_agent(instruction_override=...)`` so admin-edited
    instructions take effect on the very next chat message without a redeploy.

    Falls back to the hardcoded ``ADMIN_AGENT_INSTRUCTION`` constant when:
    - DB lookup fails or times out
    - The row's instruction text contains the placeholder sentinel
      ("Default instructions for")
    - No row exists yet for "admin"

    Returns None if ADK is unavailable (e.g. during unit tests that mock
    the runner directly).
    """
    try:
        from google.adk.apps import App
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService

        from app.agents.admin.agent import create_admin_agent

        # Fetch live instructions from DB — falls back to hardcoded constant on any failure
        instruction_override: str | None = None
        try:
            config = await get_agent_config_from_service("admin")
            if config and "Default instructions for" not in config.get("current_instructions", ""):
                instruction_override = config["current_instructions"]
        except Exception as exc:
            logger.warning(
                "Failed to fetch admin agent config from DB, using default: %s", exc
            )

        agent = create_admin_agent(instruction_override=instruction_override)
        admin_app = App(name=_ADMIN_APP_NAME, root_agent=agent)
        return Runner(
            app=admin_app,
            # NOTE: InMemorySessionService is intentional here (Phase 7 decision).
            # Each admin chat turn gets a fresh isolated ADK Runner. Admin chat
            # persistence is handled by admin_chat_sessions/admin_chat_messages
            # tables, not by ADK's session service.
            session_service=InMemorySessionService(),
        )
    except Exception as exc:
        logger.error("Failed to create admin ADK runner: %s", exc)
        return None


# =============================================================================
# SSE event generator
# =============================================================================


async def _admin_sse_generator(
    raw_request: Request,
    session_id: str,
    message: str,
    admin_user_id: str,
    confirmation_token: str | None,
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE events for one admin chat turn.

    Sequence:
    1. Yield session_id in first event
    2. If confirmation_token provided, consume atomically; yield error on failure
    3. Persist user message
    4. Run AdminAgent via ADK Runner, yield each event
    5. Collect response text; persist agent message
    6. Audit log the interaction
    """
    stream_start = time.monotonic()

    # 1. Announce session_id so frontend can persist it across page reloads
    yield f"data: {json.dumps({'session_id': session_id})}\n\n"

    # 2. Confirmation token handling
    confirmed_action: dict | None = None
    if confirmation_token:
        payload = await _consume_token_or_error(confirmation_token)
        if payload is None:
            yield f"data: {json.dumps({'error': 'Confirmation token expired or already used'})}\n\n"
            return
        confirmed_action = payload.get("action_details")

    # 3. Persist user message
    await _persist_message(session_id=session_id, role="user", content=message)

    # 4. Run AdminAgent via ADK Runner
    runner = await _make_admin_runner()
    response_texts: list[str] = []

    if runner is None:
        error_msg = "Admin agent runner unavailable"
        yield f"data: {json.dumps({'error': error_msg})}\n\n"
        await _persist_message(session_id=session_id, role="agent", content=error_msg)
        return

    # Build the ADK message
    try:
        from google.genai import types as genai_types

        run_message_text = message
        if confirmed_action:
            run_message_text = (
                f"[CONFIRMED ACTION]\n{json.dumps(confirmed_action)}\n\n"
                f"Original request: {message}"
            )

        adk_message = genai_types.Content(
            role="user", parts=[genai_types.Part(text=run_message_text)]
        )
    except Exception as exc:
        logger.error("Failed to build ADK message: %s", exc)
        yield f"data: {json.dumps({'error': 'Failed to build agent message'})}\n\n"
        return

    adk_session_id = f"admin-{session_id}"
    adk_event_queue: asyncio.Queue[str] = asyncio.Queue()
    stream_done = asyncio.Event()

    async def _run_agent() -> None:
        """Run ADK runner in background, push events to queue."""
        try:
            # Ensure session exists for the ADK runner
            try:
                await runner.session_service.create_session(
                    app_name=_ADMIN_APP_NAME,
                    user_id=admin_user_id,
                    session_id=adk_session_id,
                )
            except Exception:
                pass  # Session may already exist

            response_stream = runner.run_async(
                session_id=adk_session_id,
                new_message=adk_message,
                user_id=admin_user_id,
            )
            async for event in response_stream:
                if hasattr(event, "model_dump_json"):
                    data = event.model_dump_json()
                elif hasattr(event, "to_json"):
                    data = event.to_json()
                else:
                    data = json.dumps(event, default=lambda o: str(o))

                # Extract text for persistence
                try:
                    evt = json.loads(data)
                    content = evt.get("content")
                    if isinstance(content, dict):
                        for part in content.get("parts") or []:
                            if isinstance(part, dict) and part.get("text"):
                                response_texts.append(part["text"])
                    # Check if agent returned a confirmation request
                    actions = evt.get("actions") or {}
                    state_delta = actions.get("state_delta") or {}
                    conf_token = state_delta.get("requires_confirmation_token")
                    if conf_token:
                        action_details = state_delta.get("action_details", {})
                        await store_confirmation_token(
                            token=conf_token,
                            action_details=action_details,
                            admin_user_id=admin_user_id,
                        )
                except (json.JSONDecodeError, TypeError):
                    pass

                await adk_event_queue.put(data)
        except Exception as exc:
            logger.error("Admin agent stream error: %s", exc, exc_info=True)
            await adk_event_queue.put(json.dumps({"error": str(exc)}))
        finally:
            stream_done.set()

    runner_task = asyncio.create_task(_run_agent())
    last_keepalive = time.monotonic()
    deadline = time.monotonic() + _SSE_MAX_DURATION_S

    try:
        while True:
            if await raw_request.is_disconnected():
                break
            if stream_done.is_set() and adk_event_queue.empty():
                break
            if time.monotonic() >= deadline:
                yield f"data: {json.dumps({'error': 'Stream timeout — please retry your request.'})}\n\n"
                break

            try:
                item = await asyncio.wait_for(adk_event_queue.get(), timeout=0.5)
                yield f"data: {item}\n\n"
                last_keepalive = time.monotonic()
            except TimeoutError:
                if time.monotonic() - last_keepalive >= 10:
                    last_keepalive = time.monotonic()
                    yield ": keepalive\n\n"

        await runner_task
    except Exception as exc:
        logger.error("SSE generator error: %s", exc, exc_info=True)
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"
    finally:
        if not runner_task.done():
            runner_task.cancel()

    # 5. Persist agent response
    agent_response = " ".join(response_texts).strip()
    if agent_response:
        await _persist_message(
            session_id=session_id, role="agent", content=agent_response
        )

    # 6. Audit log
    elapsed_ms = int((time.monotonic() - stream_start) * 1000)
    await log_admin_action(
        admin_user_id=admin_user_id,
        action="admin_chat",
        target_type="chat_session",
        target_id=session_id,
        details={
            "message_preview": message[:200],
            "response_ms": elapsed_ms,
            "confirmed_action": bool(confirmed_action),
        },
        source="ai_agent",
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/chat", response_class=StreamingResponse)
@limiter.limit("30/minute")
async def admin_chat(
    request: Request,
    body: AdminChatRequest,
    admin_user: dict = Depends(require_admin),  # noqa: B008
):
    """Stream AdminAgent responses over SSE.

    Accepts a JSON body with session_id (optional), message (required), and
    optional confirmation_token for confirmed-action flows.

    The first SSE event always contains ``{"session_id": "..."}`` so the
    frontend can persist new session ids.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        body: AdminChatRequest with session_id, message, confirmation_token.
        admin_user: Injected by require_admin; contains id, email, admin_source.

    Returns:
        StreamingResponse with ``text/event-stream`` media type.

    Raises:
        HTTPException 403: If session_id is provided but not owned by caller.
    """
    admin_user_id: str = admin_user["id"]

    # Resolve / create session (may raise 403)
    session_id = await _get_or_create_session(
        session_id=body.session_id,
        admin_user_id=admin_user_id,
        message=body.message,
    )

    generator = _admin_sse_generator(
        raw_request=request,
        session_id=session_id,
        message=body.message,
        admin_user_id=admin_user_id,
        confirmation_token=body.confirmation_token,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/sessions")
@limiter.limit("60/minute")
async def list_admin_chat_sessions(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Return all chat sessions for the authenticated admin user.

    Sessions are ordered by updated_at descending (most recent first).

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin.

    Returns:
        JSON with ``sessions`` list of session rows.
    """
    admin_user_id: str = admin_user["id"]
    client = get_service_client()
    try:
        result = (
            client.table("admin_chat_sessions")
            .select("id, title, created_at, updated_at")
            .eq("admin_user_id", admin_user_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return {"sessions": result.data}
    except Exception as exc:
        logger.error("Failed to list admin sessions for %s: %s", admin_user_id, exc)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve sessions"
        ) from exc


@router.get("/chat/history/{session_id}")
@limiter.limit("60/minute")
async def get_admin_chat_history(
    request: Request,
    session_id: str,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Return all messages for a session, ordered by created_at ascending.

    Verifies session ownership before returning messages.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        session_id: UUID of the session whose history to load.
        admin_user: Injected by require_admin.

    Returns:
        JSON with ``messages`` list ordered by created_at.

    Raises:
        HTTPException 403: If session is not owned by the calling admin.
        HTTPException 404: If session does not exist.
    """
    admin_user_id: str = admin_user["id"]
    client = get_service_client()

    # Ownership check
    session_result = (
        client.table("admin_chat_sessions")
        .select("id")
        .eq("id", session_id)
        .eq("admin_user_id", admin_user_id)
        .execute()
    )
    if not session_result.data:
        raise HTTPException(
            status_code=403,
            detail="Session not found or not owned by this admin user",
        )

    # Fetch messages
    try:
        msg_result = (
            client.table("admin_chat_messages")
            .select("id, role, content, created_at")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )
        return {"messages": msg_result.data}
    except Exception as exc:
        logger.error("Failed to fetch history for session %s: %s", session_id, exc)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve message history"
        ) from exc
