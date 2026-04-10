"""Tests for cross-agent business synthesis service and tool.

Tests that the CrossAgentSynthesisService fans out to multiple domain data
sources, merges results with graceful degradation, and that the ADK tool
wraps the service correctly.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Helper: build a mock Supabase client whose .table().select()... chains
# return controlled data via execute_async.
# ---------------------------------------------------------------------------


def _make_mock_response(data):
    """Create a mock Supabase response with .data attribute."""
    resp = MagicMock()
    resp.data = data
    return resp


class TestCrossAgentSynthesisService:
    """Tests for CrossAgentSynthesisService."""

    def _get_fresh_service(self):
        """Get a fresh service instance (bypass singleton for isolation)."""
        from app.services.cross_agent_synthesis_service import (
            CrossAgentSynthesisService,
        )

        # Reset singleton so each test gets a clean instance
        CrossAgentSynthesisService._instance = None
        return CrossAgentSynthesisService()

    @patch("app.services.cross_agent_synthesis_service.execute_async")
    @patch("app.services.cross_agent_synthesis_service.get_service_client")
    def test_gather_all_sources_succeed(self, mock_client, mock_exec):
        """Service returns dict with financial, sales, marketing, data keys when all succeed."""
        mock_client.return_value = MagicMock()

        # Each execute_async call returns a mock response with some data
        mock_exec.return_value = _make_mock_response(
            [{"id": "1", "summary": "test data"}]
        )

        service = self._get_fresh_service()
        result = _run(service.gather_business_health("user-123"))

        assert "financial" in result
        assert "sales" in result
        assert "marketing" in result
        assert "data" in result
        assert "gathered_at" in result

        # Each section should have status "ok"
        for domain in ["financial", "sales", "marketing", "data"]:
            assert result[domain]["status"] == "ok"
            assert "highlights" in result[domain]
            assert "metrics" in result[domain]

    @patch("app.services.cross_agent_synthesis_service.execute_async")
    @patch("app.services.cross_agent_synthesis_service.get_service_client")
    def test_partial_failure_returns_partial_results(self, mock_client, mock_exec):
        """Service returns partial results when one source fails."""
        mock_client.return_value = MagicMock()

        call_count = 0

        async def side_effect_fn(query_builder, *, op_name=None):
            nonlocal call_count
            call_count += 1
            # Fail the first call (financial) by raising
            if "financial" in (op_name or ""):
                raise ConnectionError("DB timeout on financial")
            return _make_mock_response([{"id": "1", "summary": "ok"}])

        mock_exec.side_effect = side_effect_fn

        service = self._get_fresh_service()
        result = _run(service.gather_business_health("user-123"))

        # Financial should be unavailable
        assert result["financial"]["status"] == "unavailable"
        assert "error" in result["financial"]

        # Others should still succeed
        assert result["sales"]["status"] == "ok"
        assert result["marketing"]["status"] == "ok"
        assert result["data"]["status"] == "ok"

    @patch("app.services.cross_agent_synthesis_service.execute_async")
    @patch("app.services.cross_agent_synthesis_service.get_service_client")
    def test_all_sources_fail_returns_empty_with_errors(self, mock_client, mock_exec):
        """Service returns all sections as unavailable when everything fails."""
        mock_client.return_value = MagicMock()
        mock_exec.side_effect = ConnectionError("All DB connections failed")

        service = self._get_fresh_service()
        result = _run(service.gather_business_health("user-123"))

        for domain in ["financial", "sales", "marketing", "data"]:
            assert result[domain]["status"] == "unavailable"
            assert "error" in result[domain]

        assert "gathered_at" in result

    @patch("app.services.cross_agent_synthesis_service.execute_async")
    @patch("app.services.cross_agent_synthesis_service.get_service_client")
    def test_user_id_scoping(self, mock_client, mock_exec):
        """Service passes user_id to data queries for scoping."""
        mock_table = MagicMock()
        mock_client.return_value.table.return_value = mock_table

        # Set up chained query builder mocks
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_gte = MagicMock()
        mock_eq.gte.return_value = mock_gte
        mock_gte.limit.return_value = mock_gte
        mock_gte.order.return_value = mock_gte
        mock_eq.limit.return_value = mock_eq
        mock_eq.order.return_value = mock_eq
        mock_select.gte.return_value = mock_gte
        mock_select.limit.return_value = mock_select
        mock_select.order.return_value = mock_select

        mock_exec.return_value = _make_mock_response([])

        service = self._get_fresh_service()
        _run(service.gather_business_health("user-xyz-789"))

        # Verify user_id was used in at least one .eq("user_id", ...) call
        all_eq_calls = mock_select.eq.call_args_list + mock_eq.eq.call_args_list
        user_id_calls = [
            c for c in all_eq_calls if len(c.args) >= 2 and c.args[0] == "user_id"
        ]
        assert len(user_id_calls) > 0, "user_id should be passed to at least one query"
        for call in user_id_calls:
            assert call.args[1] == "user-xyz-789"


class TestSynthesizeBusinessHealthTool:
    """Tests for the synthesize_business_health ADK tool function."""

    @patch(
        "app.agents.tools.cross_agent_synthesis.get_cross_agent_synthesis_service"
    )
    @patch(
        "app.agents.tools.cross_agent_synthesis.get_current_user_id",
        return_value="user-abc",
    )
    def test_tool_returns_expected_keys(self, mock_uid, mock_get_svc):
        """Tool returns dict with success, health_snapshot, and sections keys."""
        mock_svc = MagicMock()
        mock_svc.gather_business_health = AsyncMock(
            return_value={
                "financial": {"status": "ok", "highlights": [], "metrics": {}},
                "sales": {"status": "ok", "highlights": [], "metrics": {}},
                "marketing": {"status": "ok", "highlights": [], "metrics": {}},
                "data": {"status": "ok", "highlights": [], "metrics": {}},
                "gathered_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        mock_get_svc.return_value = mock_svc

        from app.agents.tools.cross_agent_synthesis import synthesize_business_health

        result = _run(synthesize_business_health())

        assert result["success"] is True
        assert "health_snapshot" in result
        assert "sections" in result
        assert "instruction" in result
        assert set(result["sections"]) >= {
            "financial",
            "sales",
            "marketing",
            "data",
        }

    def test_tool_export_list(self):
        """CROSS_AGENT_SYNTHESIS_TOOLS export list contains the tool function."""
        from app.agents.tools.cross_agent_synthesis import (
            CROSS_AGENT_SYNTHESIS_TOOLS,
            synthesize_business_health,
        )

        assert synthesize_business_health in CROSS_AGENT_SYNTHESIS_TOOLS
