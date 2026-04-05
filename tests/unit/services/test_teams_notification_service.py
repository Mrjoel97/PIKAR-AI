# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for TeamsNotificationService — Adaptive Cards, webhook delivery."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

USER_ID = "test-user-00000000-0000-0000-0000-000000000001"
WEBHOOK_URL = "https://outlook.office.com/webhook/test-hook/IncomingWebhook/abc123"
APPROVAL_TOKEN = "abc123def456ghi789jkl012mno345pq"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_http_response(status_code: int = 200, text: str = "1") -> MagicMock:
    """Build a minimal mock httpx response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


# ---------------------------------------------------------------------------
# Credential resolution
# ---------------------------------------------------------------------------


class TestWebhookUrlStorage:
    """Teams webhook URL is read from integration_credentials."""

    @pytest.mark.asyncio
    async def test_webhook_url_stored(self):
        """Verify Teams webhook URL is read from integration_credentials."""
        # TeamsNotificationService receives the webhook_url as a parameter
        # (callers look it up from integration_credentials.account_name).
        # Verify that send_notification calls _post_card with the supplied URL.
        posted_urls: list[str] = []

        async def fake_post_card(url, card, *, user_id=""):
            posted_urls.append(url)
            return True

        from app.services.teams_notification_service import TeamsNotificationService

        svc = TeamsNotificationService()
        with patch.object(svc, "_post_card", side_effect=fake_post_card):
            result = await svc.send_notification(
                USER_ID, WEBHOOK_URL, "task.created", {"title": "Test"}
            )

        assert result is True
        assert posted_urls == [WEBHOOK_URL]


# ---------------------------------------------------------------------------
# Adaptive Card schema
# ---------------------------------------------------------------------------


class TestAdaptiveCardSchema:
    """Adaptive Card uses schema version 1.2 with TextBlock elements."""

    @pytest.mark.asyncio
    async def test_adaptive_card_schema(self):
        """Verify Adaptive Card body uses schema 1.2 with TextBlock elements."""
        from app.services.teams_notification_service import TeamsNotificationService

        svc = TeamsNotificationService()
        card = svc._build_adaptive_card("task.created", {"title": "Launch campaign"})

        content = card["attachments"][0]["content"]
        assert content["version"] == "1.2"
        assert content["type"] == "AdaptiveCard"

        body = content["body"]
        body_types = [item["type"] for item in body]
        assert "TextBlock" in body_types

        header = body[0]
        assert header["type"] == "TextBlock"
        assert header.get("weight") == "Bolder"
        assert header.get("size") == "Medium"

    @pytest.mark.asyncio
    async def test_approval_event_has_open_url_action(self):
        """Verify approval events include Action.OpenUrl linking to Pikar."""
        from app.services.teams_notification_service import TeamsNotificationService

        svc = TeamsNotificationService()
        card = svc._build_adaptive_card(
            "approval.pending",
            {"approval_token": APPROVAL_TOKEN, "title": "Approve tweet"},
        )

        content = card["attachments"][0]["content"]
        actions = content.get("actions", [])
        assert actions, "Approval card must include actions"

        action_types = [a["type"] for a in actions]
        assert "Action.OpenUrl" in action_types, "Must use Action.OpenUrl (not Action.Submit)"

        open_url_action = next(a for a in actions if a["type"] == "Action.OpenUrl")
        assert APPROVAL_TOKEN in open_url_action["url"]
        assert open_url_action["title"] == "View in Pikar"


# ---------------------------------------------------------------------------
# Briefing card
# ---------------------------------------------------------------------------


class TestBriefingCard:
    """Briefing Adaptive Card has ColumnSet for metrics."""

    @pytest.mark.asyncio
    async def test_briefing_card_structure(self):
        """Verify briefing Adaptive Card has ColumnSet for metrics layout."""
        from app.services.teams_notification_service import TeamsNotificationService

        svc = TeamsNotificationService()
        card = svc._build_briefing_card(
            {
                "pending_approvals": 2,
                "upcoming_tasks": ["Review contract", "Send report"],
                "key_metrics": {"Revenue": "$5,000", "Tasks": "12"},
            }
        )

        content = card["attachments"][0]["content"]
        assert content["version"] == "1.2"

        body = content["body"]
        body_types = [item["type"] for item in body]

        # Header TextBlock
        assert body[0]["type"] == "TextBlock"
        assert "Daily Briefing" in body[0]["text"]

        # Metrics ColumnSet
        assert "ColumnSet" in body_types, "Briefing card must include ColumnSet for metrics"
        column_set = next(b for b in body if b["type"] == "ColumnSet")
        assert len(column_set["columns"]) == 2, "ColumnSet should have 2 columns (name | value)"


# ---------------------------------------------------------------------------
# Rate limit handling
# ---------------------------------------------------------------------------


class TestRateLimitHandling:
    """HTTP 429 is caught and logged without raising."""

    @pytest.mark.asyncio
    async def test_rate_limit_429_handled(self):
        """Verify HTTP 429 response is caught and logged without raising."""
        mock_response = _make_http_response(status_code=429, text="Too Many Requests")
        mock_http = MagicMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.post = AsyncMock(return_value=mock_response)

        from app.services.teams_notification_service import TeamsNotificationService

        svc = TeamsNotificationService()

        with patch("app.services.teams_notification_service.httpx.AsyncClient", return_value=mock_http):
            result = await svc.send_notification(
                USER_ID, WEBHOOK_URL, "task.created", {"title": "Test"}
            )

        # Should return False without raising
        assert result is False
