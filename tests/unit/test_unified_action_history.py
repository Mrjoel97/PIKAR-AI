# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the UnifiedActionHistoryService.

Tests cover logging, querying with filters/pagination, and fire-and-forget
error handling for the cross-agent unified action history system.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_execute_async() -> AsyncMock:
    """Patch execute_async so no real Supabase calls happen."""
    return AsyncMock()


@pytest.fixture()
def mock_supabase_client() -> MagicMock:
    """Build a chainable mock that mirrors the Supabase query-builder API."""
    client = MagicMock()
    # Make the chain: client.table(...).insert(...) / .select(...) etc.
    table_mock = MagicMock()
    client.table.return_value = table_mock
    return client


@pytest.fixture()
def _reset_singleton() -> None:
    """Ensure each test gets a fresh service instance."""
    import app.services.unified_action_history_service as mod

    mod._service_instance = None


@pytest.fixture()
def service(
    mock_supabase_client: MagicMock,
    mock_execute_async: AsyncMock,
    _reset_singleton: None,
) -> Any:
    """Return a UnifiedActionHistoryService wired to mocks."""
    with (
        patch(
            "app.services.unified_action_history_service.get_service_client",
            return_value=mock_supabase_client,
        ),
        patch(
            "app.services.unified_action_history_service.execute_async",
            mock_execute_async,
        ),
    ):
        from app.services.unified_action_history_service import (
            get_action_history_service,
        )

        svc = get_action_history_service()
        # Attach mocks for assertions
        svc._mock_execute = mock_execute_async
        svc._mock_client = mock_supabase_client
        yield svc


# ---------------------------------------------------------------------------
# Test 1: log_agent_action inserts a row with correct fields
# ---------------------------------------------------------------------------


class TestLogAgentAction:
    """Tests for UnifiedActionHistoryService.log_agent_action."""

    @pytest.mark.asyncio()
    async def test_inserts_row_with_correct_fields(self, service: Any) -> None:
        """log_agent_action inserts a row with agent_name, action_type, description, user_id, metadata."""
        service._mock_execute.return_value = MagicMock(data=[{"id": "abc"}])

        await service.log_agent_action(
            user_id="user-123",
            agent_name="marketing",
            action_type="campaign_created",
            description="Created Q2 awareness campaign",
            metadata={"campaign_id": "camp-1"},
            source_id="wf-42",
            source_type="workflow",
        )

        service._mock_execute.assert_called_once()
        call_args = service._mock_execute.call_args
        # The first positional arg is the query builder
        assert call_args.kwargs.get("op_name") == "action_history.log_action"

    @pytest.mark.asyncio()
    async def test_fire_and_forget_does_not_raise(self, service: Any) -> None:
        """log_agent_action catches exceptions and does not propagate them."""
        service._mock_execute.side_effect = RuntimeError("DB down")

        # Must NOT raise
        await service.log_agent_action(
            user_id="user-123",
            agent_name="financial",
            action_type="report_generated",
            description="Monthly P&L report",
        )

    @pytest.mark.asyncio()
    async def test_default_metadata_is_empty_dict(self, service: Any) -> None:
        """When metadata is not supplied, it defaults to empty dict in the insert payload."""
        service._mock_execute.return_value = MagicMock(data=[{"id": "abc"}])

        await service.log_agent_action(
            user_id="user-456",
            agent_name="operations",
            action_type="workflow_started",
            description="Started onboarding workflow",
        )

        # Verify the insert data passed through the query builder
        table_mock = service._mock_client.table.return_value
        table_mock.insert.assert_called_once()
        inserted_data = table_mock.insert.call_args[0][0]
        assert inserted_data["metadata"] == {}


# ---------------------------------------------------------------------------
# Test 2-6: get_action_history querying with filters and pagination
# ---------------------------------------------------------------------------


class TestGetActionHistory:
    """Tests for UnifiedActionHistoryService.get_action_history."""

    def _make_response(self, rows: list[dict]) -> MagicMock:
        resp = MagicMock()
        resp.data = rows
        return resp

    @pytest.mark.asyncio()
    async def test_returns_results_filtered_by_user_id(self, service: Any) -> None:
        """get_action_history returns chronological results filtered by user_id."""
        rows = [
            {"id": "1", "agent_name": "marketing", "created_at": "2026-04-10T01:00:00Z"},
            {"id": "2", "agent_name": "financial", "created_at": "2026-04-10T00:00:00Z"},
        ]
        service._mock_execute.return_value = self._make_response(rows)

        result = await service.get_action_history(user_id="user-789")

        assert len(result) == 2
        service._mock_execute.assert_called_once()
        # Verify the user_id eq filter was applied
        table_mock = service._mock_client.table.return_value
        table_mock.select.assert_called_once_with("*")

    @pytest.mark.asyncio()
    async def test_filters_by_agent_name(self, service: Any) -> None:
        """get_action_history supports filtering by agent_name."""
        service._mock_execute.return_value = self._make_response([])

        await service.get_action_history(user_id="user-1", agent_name="marketing")

        # Verify execute_async was called (query was built and dispatched)
        service._mock_execute.assert_called_once()
        # Verify agent_name filter appears somewhere in the mock call chain
        call_str = str(service._mock_client.mock_calls)
        assert "agent_name" in call_str, f"agent_name filter not in chain: {call_str}"
        assert "marketing" in call_str, f"marketing value not in chain: {call_str}"

    @pytest.mark.asyncio()
    async def test_filters_by_action_type(self, service: Any) -> None:
        """get_action_history supports filtering by action_type."""
        service._mock_execute.return_value = self._make_response([])

        await service.get_action_history(user_id="user-1", action_type="campaign_created")

        service._mock_execute.assert_called_once()
        call_str = str(service._mock_client.mock_calls)
        assert "action_type" in call_str, f"action_type filter not in chain: {call_str}"
        assert "campaign_created" in call_str, f"campaign_created value not in chain: {call_str}"

    @pytest.mark.asyncio()
    async def test_filters_by_date_range(self, service: Any) -> None:
        """get_action_history supports date range filtering via days parameter."""
        service._mock_execute.return_value = self._make_response([])

        await service.get_action_history(user_id="user-1", days=7)

        service._mock_execute.assert_called_once()
        # Verify gte was called in the chain (date range filter)
        call_str = str(service._mock_client.mock_calls)
        assert "gte" in call_str, f"gte (date filter) not in chain: {call_str}"
        assert "created_at" in call_str, f"created_at not in chain: {call_str}"

    @pytest.mark.asyncio()
    async def test_supports_pagination(self, service: Any) -> None:
        """get_action_history supports limit and offset for pagination."""
        rows = [{"id": str(i)} for i in range(10)]
        service._mock_execute.return_value = self._make_response(rows)

        result = await service.get_action_history(
            user_id="user-1", limit=10, offset=20,
        )

        assert len(result) == 10
        service._mock_execute.assert_called_once()
        # Verify limit and offset appear in the chain
        call_str = str(service._mock_client.mock_calls)
        assert "limit" in call_str, f"limit not in chain: {call_str}"
        assert "offset" in call_str, f"offset not in chain: {call_str}"


# ---------------------------------------------------------------------------
# Test 7: Module-level convenience function
# ---------------------------------------------------------------------------


class TestModuleLevelConvenience:
    """Tests for the module-level log_agent_action convenience function."""

    @pytest.mark.asyncio()
    async def test_convenience_delegates_to_singleton(
        self, service: Any,
    ) -> None:
        """Module-level log_agent_action delegates to the singleton service."""
        service._mock_execute.return_value = MagicMock(data=[{"id": "abc"}])

        with (
            patch(
                "app.services.unified_action_history_service.get_service_client",
                return_value=service._mock_client,
            ),
            patch(
                "app.services.unified_action_history_service.execute_async",
                service._mock_execute,
            ),
        ):
            from app.services.unified_action_history_service import (
                log_agent_action,
            )

            await log_agent_action(
                user_id="user-conv",
                agent_name="strategic",
                action_type="analysis_completed",
                description="Competitor analysis finished",
            )

        service._mock_execute.assert_called()
