"""Tests for onboarding nudge service and ADK tool.

Tests that OnboardingNudgeService detects stalled users within the 7-day
window, generates contextual nudges for specific stalled steps, and that
the ADK tool wraps the service correctly.
"""

import asyncio
from datetime import datetime, timedelta, timezone
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


def _make_onboarding_status(
    is_completed=False,
    current_step=0,
    business_context_completed=False,
    preferences_completed=False,
    agent_setup_completed=False,
    persona="startup",
    agent_name=None,
):
    """Build a mock OnboardingStatus."""
    from app.services.user_onboarding_service import OnboardingStatus

    return OnboardingStatus(
        is_completed=is_completed,
        current_step=current_step,
        business_context_completed=business_context_completed,
        preferences_completed=preferences_completed,
        agent_setup_completed=agent_setup_completed,
        persona=persona,
        agent_name=agent_name,
    )


class TestOnboardingNudgeService:
    """Tests for OnboardingNudgeService."""

    def _get_fresh_service(self):
        """Get a fresh service instance (bypass singleton for isolation)."""
        import app.services.onboarding_nudge_service as mod

        mod._service_instance = None
        return mod.OnboardingNudgeService()

    @patch("app.services.onboarding_nudge_service.execute_async")
    @patch("app.services.onboarding_nudge_service.get_service_client")
    @patch("app.services.onboarding_nudge_service.get_user_onboarding_service")
    def test_completed_onboarding_no_checklist_returns_empty(
        self, mock_onb_svc, mock_client, mock_exec
    ):
        """check_nudges returns empty list for completed onboarding user with all checklist done."""
        mock_client.return_value = MagicMock()
        mock_svc_inst = MagicMock()
        mock_svc_inst.get_onboarding_status = AsyncMock(
            return_value=_make_onboarding_status(is_completed=True, current_step=4)
        )
        mock_onb_svc.return_value = mock_svc_inst

        now = datetime.now(timezone.utc)
        # Profile created 2 days ago (within 7-day window)
        mock_exec.side_effect = [
            # onboarding_checklist query -- all items completed
            _make_mock_response([{
                "items": [
                    {"id": "brain_dump", "completed": True},
                    {"id": "first_workflow", "completed": True},
                ]
            }]),
            # users_profile created_at
            _make_mock_response([{"created_at": (now - timedelta(days=2)).isoformat()}]),
            # interaction_logs last activity
            _make_mock_response([{"created_at": (now - timedelta(hours=25)).isoformat()}]),
        ]

        service = self._get_fresh_service()
        result = _run(service.check_nudges("user-1"))

        assert result == []

    @patch("app.services.onboarding_nudge_service.execute_async")
    @patch("app.services.onboarding_nudge_service.get_service_client")
    @patch("app.services.onboarding_nudge_service.get_user_onboarding_service")
    def test_user_older_than_7_days_returns_empty(
        self, mock_onb_svc, mock_client, mock_exec
    ):
        """check_nudges returns empty list for user older than 7 days."""
        mock_client.return_value = MagicMock()
        mock_svc_inst = MagicMock()
        mock_svc_inst.get_onboarding_status = AsyncMock(
            return_value=_make_onboarding_status(
                is_completed=False,
                current_step=1,
                business_context_completed=True,
            )
        )
        mock_onb_svc.return_value = mock_svc_inst

        now = datetime.now(timezone.utc)
        mock_exec.side_effect = [
            # users_profile created_at -- 10 days ago
            _make_mock_response([{"created_at": (now - timedelta(days=10)).isoformat()}]),
        ]

        service = self._get_fresh_service()
        result = _run(service.check_nudges("user-1"))

        assert result == []

    @patch("app.services.onboarding_nudge_service.execute_async")
    @patch("app.services.onboarding_nudge_service.get_service_client")
    @patch("app.services.onboarding_nudge_service.get_user_onboarding_service")
    def test_stalled_step2_returns_nudge(
        self, mock_onb_svc, mock_client, mock_exec
    ):
        """check_nudges returns a nudge for user who completed step 1 but not step 2 and last activity >24h ago."""
        mock_client.return_value = MagicMock()
        mock_svc_inst = MagicMock()
        mock_svc_inst.get_onboarding_status = AsyncMock(
            return_value=_make_onboarding_status(
                is_completed=False,
                current_step=1,
                business_context_completed=True,
                preferences_completed=False,
            )
        )
        mock_onb_svc.return_value = mock_svc_inst

        now = datetime.now(timezone.utc)
        mock_exec.side_effect = [
            # users_profile created_at -- 3 days ago
            _make_mock_response([{"created_at": (now - timedelta(days=3)).isoformat()}]),
            # interaction_logs last activity -- 26 hours ago
            _make_mock_response([{"created_at": (now - timedelta(hours=26)).isoformat()}]),
        ]

        service = self._get_fresh_service()
        result = _run(service.check_nudges("user-1"))

        assert len(result) >= 1
        nudge = result[0]
        assert nudge["nudge_type"] == "onboarding_step"
        assert "preferences" in nudge["step_name"].lower()

    @patch("app.services.onboarding_nudge_service.execute_async")
    @patch("app.services.onboarding_nudge_service.get_service_client")
    @patch("app.services.onboarding_nudge_service.get_user_onboarding_service")
    def test_checklist_nudge_when_onboarding_complete(
        self, mock_onb_svc, mock_client, mock_exec
    ):
        """check_nudges returns persona-specific checklist nudge when checklist items are incomplete."""
        mock_client.return_value = MagicMock()
        mock_svc_inst = MagicMock()
        mock_svc_inst.get_onboarding_status = AsyncMock(
            return_value=_make_onboarding_status(
                is_completed=True,
                current_step=4,
                persona="solopreneur",
            )
        )
        mock_onb_svc.return_value = mock_svc_inst

        now = datetime.now(timezone.utc)
        mock_exec.side_effect = [
            # onboarding_checklist -- one incomplete item
            _make_mock_response([{
                "items": [
                    {"id": "revenue_strategy", "completed": True},
                    {"id": "brain_dump", "completed": False, "title": "Do a brain dump"},
                    {"id": "weekly_plan", "completed": False, "title": "Plan your week"},
                ]
            }]),
            # users_profile created_at -- 2 days ago
            _make_mock_response([{"created_at": (now - timedelta(days=2)).isoformat()}]),
            # interaction_logs last activity -- 25 hours ago
            _make_mock_response([{"created_at": (now - timedelta(hours=25)).isoformat()}]),
        ]

        service = self._get_fresh_service()
        result = _run(service.check_nudges("user-1"))

        assert len(result) >= 1
        nudge = result[0]
        assert nudge["nudge_type"] == "checklist_item"

    @patch("app.services.onboarding_nudge_service.execute_async")
    @patch("app.services.onboarding_nudge_service.get_service_client")
    @patch("app.services.onboarding_nudge_service.get_user_onboarding_service")
    def test_nudge_text_is_contextual(
        self, mock_onb_svc, mock_client, mock_exec
    ):
        """Nudge text is contextual to the specific stalled step, not generic."""
        mock_client.return_value = MagicMock()
        mock_svc_inst = MagicMock()
        mock_svc_inst.get_onboarding_status = AsyncMock(
            return_value=_make_onboarding_status(
                is_completed=False,
                current_step=2,
                business_context_completed=True,
                preferences_completed=True,
                agent_setup_completed=False,
            )
        )
        mock_onb_svc.return_value = mock_svc_inst

        now = datetime.now(timezone.utc)
        mock_exec.side_effect = [
            # users_profile created_at
            _make_mock_response([{"created_at": (now - timedelta(days=1)).isoformat()}]),
            # interaction_logs last activity
            _make_mock_response([{"created_at": (now - timedelta(hours=30)).isoformat()}]),
        ]

        service = self._get_fresh_service()
        result = _run(service.check_nudges("user-1"))

        assert len(result) >= 1
        nudge = result[0]
        # Message should reference agent setup specifically, not be generic
        assert "agent" in nudge["message"].lower() or "name" in nudge["message"].lower()
        assert nudge["step_name"] == "agent_setup"

    @patch("app.agents.tools.onboarding_nudges.get_onboarding_nudge_service")
    @patch(
        "app.agents.tools.onboarding_nudges.get_current_user_id",
        return_value="user-xyz",
    )
    def test_tool_returns_nudges_with_instructions(self, mock_uid, mock_get_svc):
        """Tool check_onboarding_nudges returns nudges with clear instructions for the agent."""
        mock_svc = MagicMock()
        mock_svc.check_nudges = AsyncMock(
            return_value=[
                {
                    "nudge_type": "onboarding_step",
                    "step_name": "preferences",
                    "message": "Setting your preferences takes about 30 seconds.",
                    "suggested_action": "Set up your preferences",
                }
            ]
        )
        mock_get_svc.return_value = mock_svc

        from app.agents.tools.onboarding_nudges import check_onboarding_nudges

        result = _run(check_onboarding_nudges())

        assert result["has_nudges"] is True
        assert len(result["nudges"]) == 1
        assert "instruction" in result
