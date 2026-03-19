"""Unit tests for EmailTriageWorker.

Tests shadow mode isolation, user skipping, and failure isolation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestShadowMode:
    """Tests for shadow mode logic (auto_act_enabled=False)."""

    @pytest.fixture
    def mock_supabase(self):
        """Create a mock Supabase client."""
        return MagicMock()

    @pytest.fixture
    def worker(self, mock_supabase):
        """Create EmailTriageWorker with mocked Supabase."""
        from app.services.email_triage_worker import EmailTriageWorker

        return EmailTriageWorker(supabase_client=mock_supabase)

    @pytest.mark.asyncio
    async def test_shadow_mode_records_without_acting(self, worker):
        """When auto_act_enabled=False, shadow action is recorded but modify_message is NOT called."""
        user_id = "user-shadow-001"
        prefs = {
            "auto_act_enabled": False,
            "email_triage_enabled": True,
            "auto_act_daily_cap": 10,
        }

        email = {
            "id": "msg-001",
            "gmail_message_id": "msg-001",
            "sender": "newsletter@news.com",
            "sender_name": "News Corp",
            "subject": "Weekly Newsletter",
            "body": "Here is your weekly update.",
            "received_at": "2026-03-19T10:00:00Z",
            "labels": [],
        }

        classification = {
            "action_type": "auto_handle",
            "confidence": 0.92,
            "priority": "low",
            "category": "newsletter",
            "reasoning": "Newsletter, safe to auto-archive",
        }

        mock_reader = MagicMock()
        mock_reader.list_messages.return_value = {
            "status": "success",
            "messages": [{"id": "msg-001"}],
            "count": 1,
        }
        mock_reader.get_message.return_value = {
            "status": "success",
            "message": email,
        }
        mock_reader.modify_message = MagicMock()

        worker.triage_service.classify_email = AsyncMock(return_value=classification)
        worker.triage_service.generate_draft = AsyncMock(return_value={"draft": None, "confidence": 0.0})
        worker.triage_service.store_triage_result = AsyncMock(return_value={"id": "triage-001"})
        worker._get_user_refresh_token = AsyncMock(return_value="fake-refresh-token")
        worker._get_existing_message_ids = AsyncMock(return_value=set())
        worker._get_auto_act_count_today = AsyncMock(return_value=0)

        with patch("app.services.email_triage_worker.get_user_gmail_credentials") as mock_creds, \
             patch("app.services.email_triage_worker.GmailReader") as MockGmailReader:
            mock_creds.return_value = MagicMock()
            MockGmailReader.return_value = mock_reader

            await worker.process_user(user_id, prefs)

        # modify_message should NOT have been called (shadow mode)
        mock_reader.modify_message.assert_not_called()

        # store_triage_result should have been called with a shadow auto_action
        call_kwargs = worker.triage_service.store_triage_result.call_args
        stored_auto_action = call_kwargs.kwargs.get("auto_action") or (
            call_kwargs.args[4] if len(call_kwargs.args) > 4 else None
        )
        assert stored_auto_action is not None
        assert "shadow" in str(stored_auto_action)


class TestUserProcessing:
    """Tests for per-user processing behavior."""

    @pytest.fixture
    def mock_supabase(self):
        """Create a mock Supabase client."""
        return MagicMock()

    @pytest.fixture
    def worker(self, mock_supabase):
        """Create EmailTriageWorker with mocked Supabase."""
        from app.services.email_triage_worker import EmailTriageWorker

        return EmailTriageWorker(supabase_client=mock_supabase)

    @pytest.mark.asyncio
    async def test_skips_user_without_refresh_token(self, worker):
        """User without a refresh token is skipped with 'skipped' status."""
        user_id = "user-no-token-001"
        prefs = {
            "email_triage_enabled": True,
            "auto_act_enabled": False,
        }

        worker._get_user_refresh_token = AsyncMock(return_value=None)

        result = await worker.process_user(user_id, prefs)

        assert result["status"] == "skipped"
        assert result["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_isolates_user_failures(self, worker):
        """One user error does not prevent other users from being processed."""
        users = [
            {"user_id": "user-fail-001", "preferences": {"email_triage_enabled": True}},
            {"user_id": "user-ok-002", "preferences": {"email_triage_enabled": True}},
        ]

        call_count = 0

        async def fake_process_user(user_id, prefs):
            nonlocal call_count
            call_count += 1
            if user_id == "user-fail-001":
                raise RuntimeError("Simulated failure for user-fail-001")
            return {"status": "ok", "user_id": user_id, "processed": 0, "auto_acted": 0}

        worker.process_user = fake_process_user

        results = await worker.process_all_users(users)

        # Both users should have been attempted
        assert call_count == 2

        # The result for the failing user should indicate an error
        fail_result = next((r for r in results if r.get("user_id") == "user-fail-001"), None)
        ok_result = next((r for r in results if r.get("user_id") == "user-ok-002"), None)

        assert fail_result is not None
        assert fail_result.get("status") == "error"

        assert ok_result is not None
        assert ok_result.get("status") == "ok"
