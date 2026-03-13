# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Supabase-backed Session Service.

Provides persistent session storage using Supabase PostgreSQL,
replacing the volatile InMemorySessionService.
"""

import copy
import json
import logging
import os
import asyncio
import httpx
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

# Cap loaded events per session to avoid exceeding model context (e.g. Gemini 1M token limit).
# Only the most recent events are loaded; older events remain in DB but are not sent to the model.
# Default 80 ≈ 30-40 conversation turns; increase via SESSION_MAX_EVENTS if needed.
# Key user facts are also persisted to session.state via context_memory tools,
# ensuring critical information survives even aggressive event pruning.
SESSION_MAX_EVENTS = int(os.environ.get("SESSION_MAX_EVENTS", "80"))
SESSION_MAX_CONTEXT_CHARS = int(os.environ.get("SESSION_MAX_CONTEXT_CHARS", "600000"))

# Widget types that carry large payloads (image/video URLs or base64) — compact when loading for context.
_HEAVY_WIDGET_TYPES = frozenset({"image", "video"})
# URLs longer than this (e.g. data: URLs) are replaced with a placeholder to stay under token limit.
_MAX_URL_LEN_IN_CONTEXT = 300
_MAX_STRING_LEN_IN_CONTEXT = int(os.environ.get("SESSION_MAX_STRING_LEN_IN_CONTEXT", "12000"))

from google.adk.events import Event
from google.adk.sessions import Session, BaseSessionService

from app.rag.knowledge_vault import get_supabase_client
from app.services.cache import get_cache_service

logger = logging.getLogger(__name__)


def _truncate_string_for_context(value: str, max_len: int = _MAX_STRING_LEN_IN_CONTEXT) -> str:
    """Trim oversized strings while preserving both the start and end."""
    if len(value) <= max_len:
        return value

    head = max(256, max_len // 5)
    tail = max(256, max_len - head - 64)
    if head + tail >= len(value):
        return value

    omitted = len(value) - head - tail
    return (
        f"{value[:head]}\n\n"
        f"[... {omitted} characters omitted to fit context window ...]\n\n"
        f"{value[-tail:]}"
    )


def _compact_value_for_context(value: Any, depth: int = 0) -> Any:
    """Recursively shrink oversized strings inside event payloads."""
    if depth > 8:
        return "[nested content omitted for context window]"

    if isinstance(value, str):
        if value.startswith("data:") and len(value) > _MAX_URL_LEN_IN_CONTEXT:
            return "[inline data omitted for context window]"
        return _truncate_string_for_context(value)

    if isinstance(value, list):
        return [_compact_value_for_context(item, depth + 1) for item in value]

    if isinstance(value, dict):
        return {key: _compact_value_for_context(item, depth + 1) for key, item in value.items()}

    return value


def _compact_event_for_context(event_data: dict[str, Any]) -> dict[str, Any]:
    """Replace large payloads in event so context stays under model token limit (e.g. 1M).

    - Parts with inline_data (images/audio) are replaced by a short text placeholder.
    - function_response parts containing image/video widgets have long URLs replaced
      with a short placeholder so the model still knows an image/video was shown.
    - Oversized text fields are truncated so a single tool result cannot consume the
      whole context window.
    """
    if not event_data or not isinstance(event_data, dict):
        return event_data
    data = copy.deepcopy(event_data)
    content = data.get("content")
    if not content or not isinstance(content, dict):
        return _compact_value_for_context(data)
    parts = content.get("parts")
    if not parts or not isinstance(parts, list):
        return _compact_value_for_context(data)
    new_parts: list[dict[str, Any]] = []
    for part in parts:
        if not isinstance(part, dict):
            new_parts.append(part)
            continue
        if "inline_data" in part:
            new_parts.append({"text": "[Image or media omitted for context window]"})
            continue
        if "function_response" in part:
            fr = part.get("function_response")
            if isinstance(fr, dict):
                resp = fr.get("response")
                if isinstance(resp, dict) and resp.get("type") in _HEAVY_WIDGET_TYPES:
                    data_obj = resp.get("data")
                    if isinstance(data_obj, dict):
                        new_data = dict(data_obj)
                        for key in ("imageUrl", "videoUrl"):
                            val = new_data.get(key)
                            if isinstance(val, str) and len(val) > _MAX_URL_LEN_IN_CONTEXT:
                                new_data[key] = "[stored in knowledge vault]"
                        resp = {**resp, "data": new_data}
                    fr = {**fr, "response": resp}
                elif isinstance(resp, dict) and "result" in resp:
                    result = resp.get("result")
                    if isinstance(result, dict) and result.get("type") in _HEAVY_WIDGET_TYPES:
                        data_obj = result.get("data")
                        if isinstance(data_obj, dict):
                            new_data = dict(data_obj)
                            for key in ("imageUrl", "videoUrl"):
                                val = new_data.get(key)
                                if isinstance(val, str) and len(val) > _MAX_URL_LEN_IN_CONTEXT:
                                    new_data[key] = "[stored in knowledge vault]"
                            result = {**result, "data": new_data}
                        resp = {**resp, "result": result}
                    fr = {**fr, "response": resp}
                part = {**part, "function_response": fr}
        new_parts.append(_compact_value_for_context(part))
    data["content"] = {**content, "parts": new_parts}
    return data


def _estimate_event_context_chars(event_data: dict[str, Any]) -> int:
    try:
        return len(json.dumps(event_data, ensure_ascii=False, default=str))
    except Exception:
        return len(str(event_data))


def _load_context_bounded_events(
    rows: list[dict[str, Any]],
    *,
    session_id: str,
    source: str,
) -> list[Event]:
    """Keep the newest events that fit within an approximate context budget."""
    selected: list[dict[str, Any]] = []
    total_chars = 0
    skipped = 0

    for row in reversed(rows):
        try:
            compacted = _compact_event_for_context(row.get("event_data") or {})
            event_chars = _estimate_event_context_chars(compacted)
            if selected and total_chars + event_chars > SESSION_MAX_CONTEXT_CHARS:
                skipped += 1
                continue
            selected.append(compacted)
            total_chars += event_chars
        except Exception as exc:
            logger.warning("Failed to compact event for session %s: %s", session_id, exc)

    if skipped:
        logger.info(
            "Session %s: skipped %d older %s events to stay within approx %d-char context budget",
            session_id,
            skipped,
            source,
            SESSION_MAX_CONTEXT_CHARS,
        )

    events: list[Event] = []
    for compacted in reversed(selected):
        try:
            events.append(Event.model_validate(compacted))
        except Exception as exc:
            logger.warning("Failed to deserialize event for session %s: %s", session_id, exc)
    return events


class SupabaseSessionService(BaseSessionService):
    """A SessionService implementation backed by Supabase (PostgreSQL).
    
    This provides persistent session storage that survives container restarts,
    enabling conversation continuity for users.
    """

    def __init__(self):
        self.client = get_supabase_client()
        self.sessions_table = "sessions"
        self.events_table = "session_events"
        self._cache = get_cache_service()

    async def _execute_with_retry(self, query_builder: Any, max_retries: int = 3) -> Any:
        """Execute a Supabase query with retry logic for transient network errors.
        
        This wraps the blocking .execute() call in run_in_executor to avoid blocking the event loop,
        and retries on httpx.ConnectError (DNS/Connection issues).
        """
        loop = asyncio.get_running_loop()
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                # Run blocking execute in thread pool
                return await loop.run_in_executor(None, query_builder.execute)
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
                last_exception = e
                wait_time = (2 ** attempt) * 0.5  # 0.5s, 1s, 2s
                logger.warning(f"Supabase query failed (attempt {attempt+1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            except Exception as e:
                # Other errors (e.g. 400 Bad Request from API) shouldn't be retried blindly
                logger.error(f"Supabase query failed with non-retryable error: {e}")
                raise e
                
        logger.error(f"Supabase query failed after {max_retries} attempts")
        if last_exception:
            raise last_exception
        raise Exception("Supabase query failed unknown")

    def _ensure_uuid_str(self, user_id: str | UUID) -> str:
        """Convert UUID to string for database queries."""
        return str(user_id) if isinstance(user_id, UUID) else user_id

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str | UUID,
        session_id: str,
        state: Optional[dict] = None,
    ) -> Session:
        """Create a new session.
        
        Args:
            app_name: Application name.
            user_id: User identifier.
            session_id: Unique session identifier.
            state: Optional initial state.
            
        Returns:
            The created Session object.
        """
        try:
            user_id_str = self._ensure_uuid_str(user_id)
            data = {
                "app_name": app_name,
                "user_id": user_id_str,
                "session_id": session_id,
                "state": state or {},
            }
            result = await self._execute_with_retry(self.client.table(self.sessions_table).insert(data))
            logger.info(f"Session insert result for {session_id}: {result.data}")
            
            # Cache the new session metadata
            await self._cache.set_session_metadata(
                session_id, 
                {"state": state or {}, "created_at": "now"}
            )

            
            return Session(
                app_name=app_name,
                user_id=user_id_str,
                id=session_id,
                state=state or {},
                events=[],
            )
        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            raise

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str | UUID,
        session_id: str,
    ) -> Optional[Session]:
        """Retrieve an existing session with all its events.
        
        Args:
            app_name: Application name.
            user_id: User identifier.
            session_id: Session identifier.
            
        Returns:
            Session object if found, None otherwise.
        """
        try:
            # Get session metadata
            user_id_str = self._ensure_uuid_str(user_id)
            # Try cache for session metadata first
            cached_meta = await self._cache.get_session_metadata(session_id)
            session_data = None
            
            if cached_meta and cached_meta.found:
                 session_data = cached_meta.value
            else:
                session_response = await self._execute_with_retry(
                    self.client.table(self.sessions_table)
                    .select("*")
                    .eq("app_name", app_name)
                    .eq("user_id", user_id_str)
                    .eq("session_id", session_id)
                    .limit(1)
                )
                
                if not session_response.data:
                    # Lazy initialization: Create session if it doesn't exist
                    logger.info(f"Session {session_id} not found, auto-creating...")
                    return await self.create_session(
                        app_name=app_name,
                        user_id=user_id,
                        session_id=session_id,
                        state={},
                    )
                
                session_data = session_response.data[0]
                # Cache the metadata
                await self._cache.set_session_metadata(session_id, session_data)
        
            # Get events: cap at SESSION_MAX_EVENTS to stay under model context limit (~1M tokens).
            # Load the most recent events (order desc, limit), then reverse to chronological order.
            events_response = await self._execute_with_retry(
                self.client.table(self.events_table)
                .select("event_data")
                .eq("app_name", app_name)
                .eq("user_id", user_id_str)
                .eq("session_id", session_id)
                .order("event_index", desc=True)
                .limit(SESSION_MAX_EVENTS)
            )
            rows = list(events_response.data or [])
            rows.reverse()  # chronological order (oldest of the window first)

            # Deserialize events; compact large payloads and enforce a total context budget.
            events = _load_context_bounded_events(rows, session_id=session_id, source="recent")

            if len(rows) >= SESSION_MAX_EVENTS:
                logger.info(
                    f"Session {session_id}: truncated to last {SESSION_MAX_EVENTS} events to fit context window"
                )

            return Session(
                app_name=app_name,
                user_id=user_id_str,
                id=session_id,
                state=session_data.get("state", {}),
                events=events,
            )
        except Exception as e:
            logger.warning(f"Failed to get session {session_id}: {e}")
            return Session(
                app_name=app_name,
                user_id=user_id_str if 'user_id_str' in locals() else str(user_id),
                id=session_id,
                state={},
                events=[],
            )

    async def delete_session(
        self,
        *,
        app_name: str,
        user_id: str | UUID,
        session_id: str,
    ) -> None:
        """Delete a session and all its events.
        
        Args:
            app_name: Application name.
            user_id: User identifier.
            session_id: Session identifier.
        """
        try:
            # Events deleted via CASCADE
            (
                self.client.table(self.sessions_table)
                .delete()
                .eq("app_name", app_name)
                .eq("user_id", self._ensure_uuid_str(user_id))
                .eq("session_id", session_id)
                .execute()
            )
            
            # Invalidate cache
            await self._cache.invalidate_session(session_id)
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            raise

    async def list_sessions(
        self,
        *,
        app_name: str,
        user_id: str | UUID,
    ) -> list[Session]:
        """List all sessions for a user.
        
        Args:
            app_name: Application name.
            user_id: User identifier.
            
        Returns:
            List of Session objects (without events for performance).
        """
        try:
            user_id_str = self._ensure_uuid_str(user_id)
            response = (
                self.client.table(self.sessions_table)
                .select("*")
                .eq("app_name", app_name)
                .eq("user_id", user_id_str)
                .order("updated_at", desc=True)
                .execute()
            )
            
            sessions = []
            for row in response.data or []:
                sessions.append(
                    Session(
                        app_name=app_name,
                        user_id=user_id_str,
                        id=row["session_id"],
                        state=row.get("state", {}),
                        events=[],  # Don't load events for list
                    )
                )
            return sessions
        except Exception as e:
            logger.error(f"Failed to list sessions for user {user_id}: {e}")
            return []

    async def append_event(
        self,
        *,
        session: Session,
        event: Event,
    ) -> Event:
        """Append an event to a session.
        
        Args:
            session: The session to append to.
            event: The event to append.
            
        Returns:
            The appended event.
        """
        try:
            user_id_str = self._ensure_uuid_str(session.user_id)
            
            # Use atomic stored procedure to insert event with proper versioning
            # This prevents race conditions in concurrent event insertion
            event_data_json = event.model_dump(mode="json")
            
            # Call the atomic insert function
            response = await self._execute_with_retry(
                self.client.rpc(
                    "insert_session_event",
                    {
                        "p_app_name": session.app_name,
                        "p_user_id": user_id_str,
                        "p_session_id": session.id,
                        "p_event_data": event_data_json,
                        "p_operation": "create",
                    }
                )
            )
            
            if not response.data or len(response.data) == 0:
                raise Exception("Failed to insert session event - no data returned from stored procedure")
            
            insert_result = response.data[0]
            event_index = insert_result["event_index"]
            next_version = insert_result["version"]
            
            # Invalidate session metadata cache (version/timestamp changed)
            await self._cache.invalidate_session(session.id)
            
            # Add to in-memory session
            session.events.append(event)
            
            return event
        except Exception as e:
            logger.error(f"Failed to append event to session {session.id}: {e}")
            raise

    async def update_state(
        self,
        *,
        app_name: str,
        user_id: str | UUID,
        session_id: str,
        state_updates: dict,
    ) -> None:
        """Update session state with new values.
        
        Args:
            app_name: Application name.
            user_id: User identifier.
            session_id: Session identifier.
            state_updates: Dictionary of state updates to merge.
        """
        try:
            # Get current state
            session = await self.get_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
            )
            
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            # Merge state
            new_state = {**session.state, **state_updates}
            
            # Update in database
            await self._execute_with_retry(
                self.client.table(self.sessions_table)
                .update({"state": new_state})
                .eq("app_name", app_name)
                .eq("user_id", self._ensure_uuid_str(user_id))
                .eq("session_id", session_id)
            )
            
            # Invalidate cache to force refresh next time
            await self._cache.invalidate_session(session_id)
        except Exception as e:
            logger.error(f"Failed to update state for session {session_id}: {e}")
            raise

    # =========================================================================
    # Versioning & Time-Travel Methods
    # =========================================================================

    async def get_session_at_version(
        self,
        *,
        app_name: str,
        user_id: str | UUID,
        session_id: str,
        version: int,
    ) -> Optional[Session]:
        """Retrieve session state at a specific version (time-travel).
        
        Args:
            app_name: Application name.
            user_id: User identifier.
            session_id: Session identifier.
            version: The version number to retrieve (1-based).
            
        Returns:
            Session with events up to and including the specified version.
        """
        try:
            # Get session metadata
            user_id_str = self._ensure_uuid_str(user_id)
            session_response = (
                self.client.table(self.sessions_table)
                .select("*")
                .eq("app_name", app_name)
                .eq("user_id", user_id_str)
                .eq("session_id", session_id)
                .single()
                .execute()
            )
            
            if not session_response.data:
                return None
            
            session_data = session_response.data
            
            # Get events at the specified version using database function
            events_result = self.client.rpc(
                "get_session_at_version",
                {
                    "p_app_name": app_name,
                    "p_user_id": user_id_str,
                    "p_session_id": session_id,
                    "p_version": version,
                }
            ).execute()
            
            # Deserialize events; compact large payloads and enforce a total context budget.
            version_rows = list(events_result.data or [])
            events = _load_context_bounded_events(version_rows, session_id=session_id, source="versioned")
            
            return Session(
                app_name=app_name,
                user_id=user_id_str,
                id=session_id,
                state=session_data.get("state", {}),
                events=events,
            )
        except Exception as e:
            logger.warning(f"Failed to get session {session_id} at version {version}: {e}")
            return None

    async def get_session_at_timestamp(
        self,
        *,
        app_name: str,
        user_id: str | UUID,
        session_id: str,
        timestamp: datetime,
    ) -> Optional[Session]:
        """Retrieve session state at a specific point in time.
        
        Args:
            app_name: Application name.
            user_id: User identifier.
            session_id: Session identifier.
            timestamp: The point in time to retrieve state at.
            
        Returns:
            Session with events created before the timestamp.
        """
        try:
            # Get session metadata
            user_id_str = self._ensure_uuid_str(user_id)
            session_response = (
                self.client.table(self.sessions_table)
                .select("*")
                .eq("app_name", app_name)
                .eq("user_id", user_id_str)
                .eq("session_id", session_id)
                .single()
                .execute()
            )
            
            if not session_response.data:
                return None
            
            session_data = session_response.data
            
            # Get events created before the timestamp
            events_response = (
                self.client.table(self.events_table)
                .select("event_data")
                .eq("app_name", app_name)
                .eq("user_id", user_id_str)
                .eq("session_id", session_id)
                .lte("created_at", timestamp.isoformat())
                .is_("superseded_by", "null")
                .neq("operation", "delete")
                .order("event_index")
                .execute()
            )
            
            # Deserialize events; compact large payloads and enforce a total context budget.
            timestamp_rows = list(events_response.data or [])
            events = _load_context_bounded_events(timestamp_rows, session_id=session_id, source="timestamp")
            
            return Session(
                app_name=app_name,
                user_id=user_id_str,
                id=session_id,
                state=session_data.get("state", {}),
                events=events,
            )
        except Exception as e:
            logger.warning(f"Failed to get session {session_id} at timestamp {timestamp}: {e}")
            return None

    async def get_version_history(
        self,
        *,
        app_name: str,
        user_id: str | UUID,
        session_id: str,
    ) -> list[dict]:
        """Get the version history for a session.
        
        Args:
            app_name: Application name.
            user_id: User identifier.
            session_id: Session identifier.
            
        Returns:
            List of version metadata dicts with version, operation, timestamp.
        """
        try:
            response = (
                self.client.table("session_version_history")
                .select("*")
                .eq("app_name", app_name)
                .eq("user_id", self._ensure_uuid_str(user_id))
                .eq("session_id", session_id)
                .order("version", desc=True)
                .execute()
            )
            
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to get version history for session {session_id}: {e}")
            return []

    async def fork_session(
        self,
        *,
        app_name: str,
        user_id: str | UUID,
        source_session_id: str,
        new_session_id: str,
        at_version: Optional[int] = None,
    ) -> Session:
        """Fork/clone a session, optionally from a specific version.
        
        Args:
            app_name: Application name.
            user_id: User identifier.
            source_session_id: Session to clone from.
            new_session_id: ID for the new session.
            at_version: Optional version to fork from (defaults to latest).
            
        Returns:
            The newly created forked session.
        """
        try:
            # Get source session (at specific version if provided)
            if at_version:
                source = await self.get_session_at_version(
                    app_name=app_name,
                    user_id=user_id,
                    session_id=source_session_id,
                    version=at_version,
                )
            else:
                source = await self.get_session(
                    app_name=app_name,
                    user_id=user_id,
                    session_id=source_session_id,
                )
            
            if not source:
                raise ValueError(f"Source session {source_session_id} not found")
            
            # Create new session with same state
            new_session = await self.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=new_session_id,
                state={**source.state, "forked_from": source_session_id, "forked_at_version": at_version},
            )
            
            # Copy events to new session
            for event in source.events:
                await self.append_event(session=new_session, event=event)
            
            return new_session
        except Exception as e:
            logger.error(f"Failed to fork session {source_session_id}: {e}")
            raise

    async def rollback_session(
        self,
        *,
        app_name: str,
        user_id: str | UUID,
        session_id: str,
        to_version: int,
    ) -> Session:
        """Rollback a session to a previous version.
        
        Creates a new version that represents the rollback.
        Original events are marked as superseded but not deleted.
        
        Args:
            app_name: Application name.
            user_id: User identifier.
            session_id: Session identifier.
            to_version: The version to rollback to.
            
        Returns:
            Session at the rolled-back state.
        """
        try:
            # Get events at target version
            target_session = await self.get_session_at_version(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                version=to_version,
            )
            
            if not target_session:
                raise ValueError(f"Session {session_id} at version {to_version} not found")
            
            # Get next version number via direct query instead of broken RPC
            user_id_str = self._ensure_uuid_str(user_id)
            version_response = (
                self.client.table(self.events_table)
                .select("version")
                .eq("app_name", app_name)
                .eq("user_id", user_id_str)
                .eq("session_id", session_id)
                .order("version", desc=True)
                .limit(1)
                .execute()
            )
            rollback_version = (version_response.data[0]["version"] + 1) if version_response.data else 1
            
            # Mark events after target version as superseded
            # Get IDs of events to supersede
            events_to_supersede = (
                self.client.table(self.events_table)
                .select("id")
                .eq("app_name", app_name)
                .eq("user_id", self._ensure_uuid_str(user_id))
                .eq("session_id", session_id)
                .gt("version", to_version)
                .is_("superseded_by", "null")
                .execute()
            )
            
            # Insert a rollback marker event
            rollback_event_data = {
                "app_name": app_name,
                "user_id": self._ensure_uuid_str(user_id),
                "session_id": session_id,
                "event_data": {"type": "rollback", "to_version": to_version, "from_version": rollback_version - 1},
                "event_index": len(target_session.events),
                "version": rollback_version,
                "operation": "rollback",
            }
            rollback_insert = self.client.table(self.events_table).insert(rollback_event_data).execute()
            rollback_event_id = rollback_insert.data[0]["id"] if rollback_insert.data else None
            
            # Mark superseded events
            if rollback_event_id and events_to_supersede.data:
                for evt in events_to_supersede.data:
                    self.client.table(self.events_table).update(
                        {"superseded_by": rollback_event_id}
                    ).eq("id", evt["id"]).execute()
            
            # Update session current version
            (
                self.client.table(self.sessions_table)
                .update({"current_version": rollback_version, "updated_at": "now()"})
                .eq("app_name", app_name)
                .eq("user_id", self._ensure_uuid_str(user_id))
                .eq("session_id", session_id)
                .execute()
            )
            
            # Return session at rolled-back state
            return await self.get_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
            )
        except Exception as e:
            logger.error(f"Failed to rollback session {session_id} to version {to_version}: {e}")
            raise
