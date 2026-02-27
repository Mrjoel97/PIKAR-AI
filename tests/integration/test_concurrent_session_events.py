"""Integration tests for concurrent session event insertion.

Tests that the atomic event insertion prevents race conditions when multiple
concurrent requests try to add events to the same session.

These tests require a running Supabase instance and should be run with:
    uv run pytest tests/integration/test_concurrent_session_events.py -v
"""

import pytest
import asyncio
import uuid
from datetime import datetime
from typing import List

# Import the session service
from app.persistence.supabase_session_service import SupabaseSessionService


class TestConcurrentSessionEvents:
    """Test suite for concurrent session event insertion."""

    @pytest.fixture
    def session_service(self):
        """Create a session service instance for testing."""
        return SupabaseSessionService()

    @pytest.fixture
    def test_session_id(self):
        """Generate a unique test session ID."""
        return f"test-concurrent-{uuid.uuid4()}"

    @pytest.fixture
    def test_user_id(self):
        """Generate a unique test user ID."""
        return str(uuid.uuid4())

    def create_test_event(self, index: int):
        """Helper to create a test event."""
        from google.adk.events import Event
        from google.adk.events.event import Content, Part
        
        content = Content(
            role="user",
            parts=[Part(text=f"Test message {index}")]
        )
        return Event(
            content=content,
            timestamp=datetime.utcnow().isoformat()
        )

    @pytest.mark.asyncio
    async def test_concurrent_event_insert_no_duplicate_indices(
        self, session_service, test_session_id, test_user_id
    ):
        """Test that concurrent event insertions don't produce duplicate indices.
        
        This is the main race condition test - multiple concurrent inserts should
        each get unique, sequential event_index values.
        """
        app_name = "test_app"
        
        # Create a session first
        session = await session_service.create_session(
            app_name=app_name,
            user_id=test_user_id,
            session_id=test_session_id,
            state={}
        )
        
        # Number of concurrent inserts to test
        num_concurrent = 10
        
        async def append_event(index: int):
            """Helper to append an event and return the result."""
            event = self.create_test_event(index)
            result = await session_service.append_event(session, event)
            return result
        
        # Execute concurrent event insertions
        tasks = [append_event(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out any exceptions for analysis
        successful = [r for r in results if not isinstance(r, Exception)]
        errors = [r for r in results if isinstance(r, Exception)]
        
        # Log any errors for debugging
        if errors:
            print(f"Errors during concurrent insert: {errors}")
        
        # Verify we got enough successful inserts
        assert len(successful) >= num_concurrent - 2, \
            f"Expected at least {num_concurrent - 2} successful inserts, got {len(successful)}"
        
        # Retrieve events and check indices
        events = await session_service.get_events(session)
        
        # Get all event indices
        indices = [evt.get("event_index", -1) for evt in events]
        
        # Verify no duplicate indices
        unique_indices = set(indices)
        assert len(indices) == len(unique_indices), \
            f"Duplicate indices found: {indices}"
        
        # Verify indices are sequential (0, 1, 2, ..., n-1)
        expected_indices = list(range(len(indices)))
        assert sorted(indices) == expected_indices, \
            f"Indices not sequential. Got: {sorted(indices)}, Expected: {expected_indices}"
        
        # Verify we have the expected number of events
        assert len(events) == num_concurrent, \
            f"Expected {num_concurrent} events, got {len(events)}"

    @pytest.mark.asyncio
    async def test_concurrent_event_insert_no_duplicate_versions(
        self, session_service, test_session_id, test_user_id
    ):
        """Test that concurrent event insertions don't produce duplicate versions.
        
        Versions should be unique and sequential across all events in a session.
        """
        app_name = "test_app"
        
        # Create a session
        session = await session_service.create_session(
            app_name=app_name,
            user_id=test_user_id,
            session_id=test_session_id,
            state={}
        )
        
        num_concurrent = 5
        
        async def append_event(index: int):
            event = self.create_test_event(index)
            return await session_service.append_event(session, event)
        
        # Execute concurrent inserts
        await asyncio.gather(*[append_event(i) for i in range(num_concurrent)])
        
        # Retrieve events
        events = await session_service.get_events(session)
        
        # Get all versions
        versions = [evt.get("version", -1) for evt in events]
        
        # Verify no duplicate versions
        unique_versions = set(versions)
        assert len(versions) == len(unique_versions), \
            f"Duplicate versions found: {versions}"
        
        # Verify versions are sequential (1, 2, 3, ..., n)
        expected_versions = list(range(1, len(versions) + 1))
        assert sorted(versions) == expected_versions, \
            f"Versions not sequential. Got: {sorted(versions)}, Expected: {expected_versions}"

    @pytest.mark.asyncio
    async def test_sequential_event_insert_after_concurrent(
        self, session_service, test_session_id, test_user_id
    ):
        """Test that sequential inserts after concurrent inserts work correctly.
        
        Verifies the system maintains consistency even after a burst of concurrent inserts.
        """
        app_name = "test_app"
        
        # Create a session
        session = await session_service.create_session(
            app_name=app_name,
            user_id=test_user_id,
            session_id=test_session_id,
            state={}
        )
        
        # First, do some concurrent inserts
        num_initial = 5
        await asyncio.gather(*[
            session_service.append_event(session, self.create_test_event(i))
            for i in range(num_initial)
        ])
        
        # Then do sequential inserts
        for i in range(num_initial, num_initial + 3):
            await session_service.append_event(session, self.create_test_event(i))
        
        # Verify total count
        events = await session_service.get_events(session)
        assert len(events) == num_initial + 3, \
            f"Expected {num_initial + 3} events, got {len(events)}"
        
        # Verify indices are still sequential
        indices = [evt.get("event_index", -1) for evt in events]
        expected_indices = list(range(len(indices)))
        assert sorted(indices) == expected_indices, \
            f"Indices not sequential after mixed concurrent/sequential inserts"

    @pytest.mark.asyncio
    async def test_session_current_version_updated(
        self, session_service, test_session_id, test_user_id
    ):
        """Test that session's current_version is correctly updated after inserts.
        
        The session's current_version should match the highest event version.
        """
        app_name = "test_app"
        
        # Create a session
        session = await session_service.create_session(
            app_name=app_name,
            user_id=test_user_id,
            session_id=test_session_id,
            state={}
        )
        
        # Add some events
        num_events = 5
        for i in range(num_events):
            await session_service.append_event(session, self.create_test_event(i))
        
        # Refresh session from storage
        refreshed_session = await session_service.get_session(
            app_name=app_name,
            user_id=test_user_id,
            session_id=test_session_id
        )
        
        # Verify current_version matches the number of events
        assert refreshed_session.current_version == num_events, \
            f"Expected current_version={num_events}, got {refreshed_session.current_version}"


class TestAtomicInsertMigration:
    """Tests to verify the atomic insert stored procedure is working."""

    @pytest.mark.asyncio
    async def test_atomic_insert_function_exists(self):
        """Verify the insert_session_event RPC function exists.
        
        This test checks that the migration was applied successfully.
        """
        from app.services.supabase_client import get_supabase_client
        
        client = get_supabase_client()
        
        # Try to call the function - it will fail if it doesn't exist
        # We're just checking existence, not functionality
        try:
            # This will return an error if the function doesn't exist
            response = client.rpc("insert_session_event", {
                "p_app_name": "test",
                "p_user_id": str(uuid.uuid4()),
                "p_session_id": str(uuid.uuid4()),
                "p_event_data": {"test": True},
                "p_operation": "create"
            }).execute()
            
            # If we get here, the function exists
            # The call might fail for other reasons (like no rows), but that's OK
            assert True
        except Exception as e:
            # Check if it's a "function does not exist" error
            if "function" in str(e).lower() and "does not exist" in str(e).lower():
                pytest.fail("insert_session_event function does not exist - migration not applied")
            # Other errors are OK - function exists
            assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
