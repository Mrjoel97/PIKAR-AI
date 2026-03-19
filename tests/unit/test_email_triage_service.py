"""Unit tests for EmailTriageService.

Tests AI classification, draft generation, and auto-act safety guardrails.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestClassification:
    """Tests for email classification logic."""

    @pytest.fixture
    def mock_supabase(self):
        """Create a mock Supabase client."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_supabase):
        """Create EmailTriageService with mocked Supabase."""
        from app.services.email_triage_service import EmailTriageService

        return EmailTriageService(supabase_client=mock_supabase)

    @pytest.mark.asyncio
    async def test_classify_urgent_email(self, service):
        """Classifier returns urgent/needs_reply/deal classification."""
        email = {
            "gmail_message_id": "msg-001",
            "sender": "ceo@bigco.com",
            "sender_name": "Big CEO",
            "subject": "URGENT: Contract deadline tomorrow",
            "body": "We need your signature today or the deal is off.",
        }
        prefs = {"vip_senders": ["ceo@bigco.com"], "ignored_senders": []}

        classifier_result = {
            "priority": "urgent",
            "action_type": "needs_reply",
            "category": "deal",
            "confidence": 0.95,
            "reasoning": "VIP sender, urgent contract matter",
        }

        service._call_classifier = AsyncMock(return_value=classifier_result)

        result = await service.classify_email(email, prefs)

        assert result["priority"] == "urgent"
        assert result["action_type"] == "needs_reply"
        assert result["category"] == "deal"
        assert result["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_classify_newsletter(self, service):
        """Classifier correctly identifies newsletters as fyi/low priority."""
        email = {
            "gmail_message_id": "msg-002",
            "sender": "news@techcrunch.com",
            "sender_name": "TechCrunch",
            "subject": "Top stories this week",
            "body": "Here are the top tech stories from this week...",
        }
        prefs = {"vip_senders": [], "ignored_senders": []}

        classifier_result = {
            "priority": "low",
            "action_type": "fyi",
            "category": "newsletter",
            "confidence": 0.88,
            "reasoning": "Newsletter from news outlet, no action required",
        }

        service._call_classifier = AsyncMock(return_value=classifier_result)

        result = await service.classify_email(email, prefs)

        assert result["priority"] == "low"
        assert result["action_type"] == "fyi"
        assert result["category"] == "newsletter"

    @pytest.mark.asyncio
    async def test_classify_invalid_values_fall_back_to_defaults(self, service):
        """Invalid classifier output falls back to safe defaults."""
        email = {
            "gmail_message_id": "msg-003",
            "sender": "unknown@example.com",
            "sender_name": "Unknown",
            "subject": "Hello",
            "body": "Test email",
        }
        prefs = {}

        # Classifier returns bogus values
        classifier_result = {
            "priority": "SUPER_URGENT",  # invalid
            "action_type": "do_magic",   # invalid
            "category": "spaceship",     # invalid
            "confidence": 1.5,           # out of range
            "reasoning": "test",
        }

        service._call_classifier = AsyncMock(return_value=classifier_result)

        result = await service.classify_email(email, prefs)

        assert result["priority"] == "normal"
        assert result["action_type"] == "needs_review"
        assert result["category"] is None
        assert result["confidence"] == 1.0  # clamped to max, not reset to default


class TestAutoActSafety:
    """Critical tests for auto-act safety guardrails."""

    @pytest.fixture
    def service(self):
        """Create EmailTriageService with mocked Supabase."""
        mock_supabase = MagicMock()
        from app.services.email_triage_service import EmailTriageService

        return EmailTriageService(supabase_client=mock_supabase)

    def test_low_confidence_never_auto_acts(self, service):
        """Confidence below 0.85 must never trigger auto-act."""
        result = service.should_auto_act(
            action_type="auto_handle",
            confidence=0.80,
            prefs={"auto_act_enabled": True, "auto_act_daily_cap": 10},
            auto_acted_today=0,
        )
        assert result is False

    def test_daily_cap_enforced(self, service):
        """Daily cap prevents auto-act when limit is reached."""
        result = service.should_auto_act(
            action_type="auto_handle",
            confidence=0.95,
            prefs={"auto_act_enabled": True, "auto_act_daily_cap": 10},
            auto_acted_today=10,
        )
        assert result is False

    def test_auto_act_disabled(self, service):
        """auto_act_enabled=False prevents auto-act regardless of other conditions."""
        result = service.should_auto_act(
            action_type="auto_handle",
            confidence=0.95,
            prefs={"auto_act_enabled": False, "auto_act_daily_cap": 10},
            auto_acted_today=0,
        )
        assert result is False

    def test_auto_act_wrong_action_type(self, service):
        """Only action_type='auto_handle' qualifies for auto-act."""
        result = service.should_auto_act(
            action_type="needs_reply",
            confidence=0.99,
            prefs={"auto_act_enabled": True, "auto_act_daily_cap": 10},
            auto_acted_today=0,
        )
        assert result is False

    def test_auto_act_allowed(self, service):
        """All conditions met → auto-act is allowed."""
        result = service.should_auto_act(
            action_type="auto_handle",
            confidence=0.95,
            prefs={"auto_act_enabled": True, "auto_act_daily_cap": 10},
            auto_acted_today=5,
        )
        assert result is True

    def test_auto_act_at_cap_boundary_not_allowed(self, service):
        """auto_acted_today exactly equal to cap → not allowed."""
        result = service.should_auto_act(
            action_type="auto_handle",
            confidence=0.95,
            prefs={"auto_act_enabled": True, "auto_act_daily_cap": 5},
            auto_acted_today=5,
        )
        assert result is False

    def test_auto_act_defaults_disabled_when_pref_missing(self, service):
        """Missing auto_act_enabled defaults to False (safe by default)."""
        result = service.should_auto_act(
            action_type="auto_handle",
            confidence=0.95,
            prefs={},
            auto_acted_today=0,
        )
        assert result is False


class TestDraftGeneration:
    """Tests for AI draft generation."""

    @pytest.fixture
    def service(self):
        """Create EmailTriageService with mocked Supabase."""
        mock_supabase = MagicMock()
        from app.services.email_triage_service import EmailTriageService

        return EmailTriageService(supabase_client=mock_supabase)

    @pytest.mark.asyncio
    async def test_generate_draft_for_needs_reply(self, service):
        """Draft generator returns a reply draft with confidence score."""
        email = {
            "sender": "partner@company.com",
            "sender_name": "Partner",
            "subject": "Partnership proposal",
            "body": "We'd like to explore a partnership with your team.",
        }

        draft_result = {
            "draft": "Thank you for reaching out. I'd be happy to explore this partnership opportunity. Let's schedule a call to discuss further.",
            "confidence": 0.82,
        }

        service._call_draft_generator = AsyncMock(return_value=draft_result)

        result = await service.generate_draft(email)

        assert "draft" in result
        assert result["draft"] is not None
        assert len(result["draft"]) > 0
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_generate_draft_returns_structure(self, service):
        """generate_draft always returns dict with draft and confidence keys."""
        email = {
            "sender": "someone@example.com",
            "sender_name": "Someone",
            "subject": "Hi",
            "body": "Just checking in.",
        }

        service._call_draft_generator = AsyncMock(
            return_value={"draft": "Thanks for reaching out.", "confidence": 0.7}
        )

        result = await service.generate_draft(email)

        assert isinstance(result, dict)
        assert "draft" in result
        assert "confidence" in result
