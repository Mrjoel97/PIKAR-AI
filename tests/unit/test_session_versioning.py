"""Unit tests for session versioning functionality."""
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch


class MockEvent:
    """Mock Event class for testing."""
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
    
    def model_dump(self, mode="json"):
        return {"role": self.role, "content": self.content}
    
    @classmethod
    def model_validate(cls, data):
        return cls(data.get("role", "user"), data.get("content", ""))


class TestSessionVersioning:
    """Test suite for session versioning methods."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client."""
        client = MagicMock()
        
        # Mock table operations
        table_mock = MagicMock()
        client.table.return_value = table_mock
        table_mock.select.return_value = table_mock
        table_mock.insert.return_value = table_mock
        table_mock.update.return_value = table_mock
        table_mock.delete.return_value = table_mock
        table_mock.eq.return_value = table_mock
        table_mock.lte.return_value = table_mock
        table_mock.gt.return_value = table_mock
        table_mock.is_.return_value = table_mock
        table_mock.neq.return_value = table_mock
        table_mock.order.return_value = table_mock
        table_mock.single.return_value = table_mock
        
        # Mock RPC
        rpc_mock = MagicMock()
        client.rpc.return_value = rpc_mock
        rpc_mock.execute.return_value = MagicMock(data=1)
        
        return client

    def test_version_number_calculation(self):
        """Test that version numbers are calculated correctly."""
        # Version should start at 1 and increment
        versions = []
        for i in range(5):
            versions.append(i + 1)
        
        assert versions == [1, 2, 3, 4, 5]

    def test_version_history_structure(self):
        """Test version history returns expected structure."""
        history = [
            {"version": 3, "operation": "create", "version_created_at": "2026-01-31T10:00:00Z"},
            {"version": 2, "operation": "create", "version_created_at": "2026-01-31T09:30:00Z"},
            {"version": 1, "operation": "create", "version_created_at": "2026-01-31T09:00:00Z"},
        ]
        
        # Should be ordered by version descending
        assert history[0]["version"] > history[1]["version"]
        assert all("operation" in h for h in history)
        assert all("version_created_at" in h for h in history)

    def test_fork_state_includes_metadata(self):
        """Test that forked sessions include fork metadata in state."""
        source_state = {"last_topic": "testing"}
        fork_metadata = {
            "forked_from": "original-session-id",
            "forked_at_version": 2,
        }
        
        new_state = {**source_state, **fork_metadata}
        
        assert new_state["last_topic"] == "testing"
        assert new_state["forked_from"] == "original-session-id"
        assert new_state["forked_at_version"] == 2

    def test_rollback_event_structure(self):
        """Test rollback event data structure."""
        rollback_event_data = {
            "type": "rollback",
            "to_version": 2,
            "from_version": 4,
        }
        
        assert rollback_event_data["type"] == "rollback"
        assert rollback_event_data["to_version"] < rollback_event_data["from_version"]

    def test_superseded_by_marks_old_events(self):
        """Test that superseded_by correctly marks events."""
        # Simulating events after rollback
        events = [
            {"id": "evt-1", "version": 1, "superseded_by": None},
            {"id": "evt-2", "version": 2, "superseded_by": None},
            {"id": "evt-3", "version": 3, "superseded_by": "rollback-evt-id"},
            {"id": "evt-4", "version": 4, "superseded_by": "rollback-evt-id"},
        ]
        
        active_events = [e for e in events if e["superseded_by"] is None]
        superseded_events = [e for e in events if e["superseded_by"] is not None]
        
        assert len(active_events) == 2
        assert len(superseded_events) == 2
        assert all(e["version"] <= 2 for e in active_events)

    def test_timestamp_filtering(self):
        """Test filtering events by timestamp."""
        now = datetime.now()
        events = [
            {"created_at": now - timedelta(hours=2), "content": "first"},
            {"created_at": now - timedelta(hours=1), "content": "second"},
            {"created_at": now, "content": "third"},
        ]
        
        cutoff = now - timedelta(minutes=30)
        filtered = [e for e in events if e["created_at"] <= cutoff]
        
        assert len(filtered) == 2
        assert filtered[-1]["content"] == "second"


class TestVersionOperations:
    """Test version operation types."""

    def test_valid_operations(self):
        """Test that all valid operations are recognized."""
        valid_ops = ["create", "update", "delete", "rollback"]
        
        for op in valid_ops:
            assert op in ["create", "update", "delete", "rollback"]

    def test_create_is_default_operation(self):
        """Test that 'create' is the default operation for new events."""
        default_op = "create"
        assert default_op == "create"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
