# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Supabase-backed Session Service.

Provides persistent session storage using Supabase PostgreSQL,
replacing the volatile InMemorySessionService.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from google.adk.events import Event
from google.adk.sessions import Session, BaseSessionService
from google.genai import types

from app.rag.knowledge_vault import get_supabase_client
from app.services.cache import get_cache_service

logger = logging.getLogger(__name__)


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
            self.client.table(self.sessions_table).insert(data).execute()
            
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
            
            if cached_meta:
                 session_data = cached_meta
            else:
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
                # Cache the metadata
                await self._cache.set_session_metadata(session_id, session_data)
            
            # Get events ordered by index
            events_response = (
                self.client.table(self.events_table)
                .select("event_data")
                .eq("app_name", app_name)
                .eq("user_id", user_id_str)
                .eq("session_id", session_id)
                .order("event_index")
                .execute()
            )
            
            # Deserialize events
            events = []
            for row in events_response.data or []:
                try:
                    event = Event.model_validate(row["event_data"])
                    events.append(event)
                except Exception as e:
                    logger.warning(f"Failed to deserialize event: {e}")
            
            return Session(
                app_name=app_name,
                user_id=user_id_str,
                id=session_id,
                state=session_data.get("state", {}),
                events=events,
            )
        except Exception as e:
            logger.warning(f"Failed to get session {session_id}: {e}")
            return None

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
            # Get current event count for index
            count_response = (
                self.client.table(self.events_table)
                .select("id", count="exact")
                .eq("app_name", session.app_name)
                .eq("user_id", self._ensure_uuid_str(session.user_id))
                .eq("session_id", session.id)
                .execute()
            )
            event_index = count_response.count or 0
            
            # Get next version number using database function
            version_result = self.client.rpc(
                "get_next_session_version",
                {
                    "p_app_name": session.app_name,
                    "p_user_id": self._ensure_uuid_str(session.user_id),
                    "p_session_id": session.id,
                }
            ).execute()
            next_version = version_result.data if version_result.data else 1
            
            # Insert event with version tracking
            data = {
                "app_name": session.app_name,
                "user_id": self._ensure_uuid_str(session.user_id),
                "session_id": session.id,
                "event_data": event.model_dump(mode="json"),
                "event_index": event_index,
                "version": next_version,
                "operation": "create",
            }
            self.client.table(self.events_table).insert(data).execute()
            
            # Update session timestamp and current version
            (
                self.client.table(self.sessions_table)
                .update({"updated_at": "now()", "current_version": next_version})
                .eq("app_name", session.app_name)
                .eq("user_id", self._ensure_uuid_str(session.user_id))
                .eq("session_id", session.id)
                .execute()
            )
            
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
            (
                self.client.table(self.sessions_table)
                .update({"state": new_state})
                .eq("app_name", app_name)
                .eq("user_id", self._ensure_uuid_str(user_id))
                .eq("session_id", session_id)
                .execute()
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
            
            # Deserialize events
            events = []
            for row in events_result.data or []:
                try:
                    event = Event.model_validate(row["event_data"])
                    events.append(event)
                except Exception as e:
                    logger.warning(f"Failed to deserialize event: {e}")
            
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
            
            # Deserialize events
            events = []
            for row in events_response.data or []:
                try:
                    event = Event.model_validate(row["event_data"])
                    events.append(event)
                except Exception as e:
                    logger.warning(f"Failed to deserialize event: {e}")
            
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
            
            # Get next version number for the rollback
            version_result = self.client.rpc(
                "get_next_session_version",
                {
                    "p_app_name": app_name,
                    "p_user_id": self._ensure_uuid_str(user_id),
                    "p_session_id": session_id,
                }
            ).execute()
            rollback_version = version_result.data if version_result.data else 1
            
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
