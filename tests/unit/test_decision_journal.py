"""Tests for decision journal service and ADK tools.

Tests that DecisionJournalService logs and queries decisions correctly,
that tools wrap the service and return expected shapes, and that logging
also writes to the unified action history.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


def _make_mock_response(data):
    """Create a mock Supabase response with .data attribute."""
    resp = MagicMock()
    resp.data = data
    return resp


class TestDecisionJournalService:
    """Tests for DecisionJournalService."""

    def _get_fresh_service(self):
        """Get a fresh service instance (bypass singleton for isolation)."""
        import app.services.decision_journal_service as mod

        mod._service_instance = None
        return mod.DecisionJournalService()

    @patch("app.services.decision_journal_service.execute_async")
    @patch("app.services.decision_journal_service.get_service_client")
    def test_log_decision_inserts_row(self, mock_client, mock_exec):
        """log_decision inserts a row with topic, rationale, decision_text, agent_name, outcome, user_id."""
        mock_client.return_value = MagicMock()
        inserted = {
            "id": "dec-001",
            "user_id": "user-1",
            "topic": "Pricing",
            "decision_text": "Set price at $99",
            "rationale": "Market research",
            "agent_name": "StrategicPlanningAgent",
            "outcome": "Approved",
        }
        mock_exec.return_value = _make_mock_response([inserted])

        service = self._get_fresh_service()
        result = _run(
            service.log_decision(
                user_id="user-1",
                topic="Pricing",
                decision_text="Set price at $99",
                rationale="Market research",
                agent_name="StrategicPlanningAgent",
                outcome="Approved",
            )
        )

        assert result is not None
        assert result["id"] == "dec-001"
        assert result["topic"] == "Pricing"
        mock_exec.assert_called_once()

    @patch("app.services.decision_journal_service.execute_async")
    @patch("app.services.decision_journal_service.get_service_client")
    def test_query_decisions_with_topic(self, mock_client, mock_exec):
        """query_decisions with topic keyword returns matching decisions ordered by created_at DESC."""
        mock_client.return_value = MagicMock()
        decisions = [
            {"id": "d1", "topic": "Marketing budget", "created_at": "2026-04-10"},
            {"id": "d2", "topic": "Marketing strategy", "created_at": "2026-04-09"},
        ]
        mock_exec.return_value = _make_mock_response(decisions)

        service = self._get_fresh_service()
        result = _run(service.query_decisions("user-1", topic="marketing"))

        assert len(result) == 2
        assert result[0]["topic"] == "Marketing budget"

    @patch("app.services.decision_journal_service.execute_async")
    @patch("app.services.decision_journal_service.get_service_client")
    def test_query_decisions_no_keyword(self, mock_client, mock_exec):
        """query_decisions with no keyword returns recent decisions for user."""
        mock_client.return_value = MagicMock()
        decisions = [
            {"id": "d1", "topic": "Hiring plan", "created_at": "2026-04-10"},
        ]
        mock_exec.return_value = _make_mock_response(decisions)

        service = self._get_fresh_service()
        result = _run(service.query_decisions("user-1"))

        assert len(result) == 1
        assert result[0]["topic"] == "Hiring plan"


class TestDecisionJournalTools:
    """Tests for decision journal ADK tool functions."""

    @patch("app.agents.tools.decision_journal.log_agent_action", new_callable=AsyncMock)
    @patch("app.agents.tools.decision_journal.get_decision_journal_service")
    @patch(
        "app.agents.tools.decision_journal.get_current_user_id",
        return_value="user-abc",
    )
    def test_tool_log_decision_returns_success(self, mock_uid, mock_get_svc, mock_log_action):
        """Tool log_decision returns success with decision_id."""
        mock_svc = MagicMock()
        mock_svc.log_decision = AsyncMock(
            return_value={"id": "dec-123", "topic": "Pricing"}
        )
        mock_get_svc.return_value = mock_svc

        from app.agents.tools.decision_journal import log_decision

        result = _run(log_decision(topic="Pricing", decision_text="Set $99"))

        assert result["success"] is True
        assert result["decision_id"] == "dec-123"
        assert result["topic"] == "Pricing"

    @patch("app.agents.tools.decision_journal.get_decision_journal_service")
    @patch(
        "app.agents.tools.decision_journal.get_current_user_id",
        return_value="user-abc",
    )
    def test_tool_query_decisions_with_topic(self, mock_uid, mock_get_svc):
        """Tool query_decisions with topic 'marketing' returns matching entries."""
        mock_svc = MagicMock()
        mock_svc.query_decisions = AsyncMock(
            return_value=[
                {"id": "d1", "topic": "Marketing budget", "decision_text": "Allocate 10K"},
            ]
        )
        mock_get_svc.return_value = mock_svc

        from app.agents.tools.decision_journal import query_decisions

        result = _run(query_decisions(topic="marketing"))

        assert result["success"] is True
        assert result["count"] == 1
        assert "instruction" in result

    @patch("app.agents.tools.decision_journal.log_agent_action", new_callable=AsyncMock)
    @patch("app.agents.tools.decision_journal.get_decision_journal_service")
    @patch(
        "app.agents.tools.decision_journal.get_current_user_id",
        return_value="user-abc",
    )
    def test_log_decision_calls_log_agent_action(self, mock_uid, mock_get_svc, mock_log_action):
        """log_decision also calls log_agent_action to record in unified action history."""
        mock_svc = MagicMock()
        mock_svc.log_decision = AsyncMock(
            return_value={"id": "dec-456", "topic": "Hiring"}
        )
        mock_get_svc.return_value = mock_svc

        from app.agents.tools.decision_journal import log_decision

        _run(log_decision(topic="Hiring", decision_text="Hire 2 engineers"))

        mock_log_action.assert_awaited_once()
        call_kwargs = mock_log_action.call_args
        assert call_kwargs[0][0] == "user-abc"  # user_id
        assert call_kwargs[0][1] == "StrategicPlanningAgent"  # agent_name
        assert call_kwargs[0][2] == "decision_logged"  # action_type
