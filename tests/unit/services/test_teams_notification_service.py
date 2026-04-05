# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for TeamsNotificationService — Adaptive Cards, webhook delivery."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

USER_ID = "test-user-00000000-0000-0000-0000-000000000001"
WEBHOOK_URL = "https://outlook.office.com/webhook/test-hook/IncomingWebhook/abc123"


# ---------------------------------------------------------------------------
# Credential resolution
# ---------------------------------------------------------------------------


class TestWebhookUrlStorage:
    """Teams webhook URL is read from integration_credentials."""

    @pytest.mark.asyncio
    async def test_webhook_url_stored(self):
        """Verify Teams webhook URL is read from integration_credentials."""
        pytest.skip("Wave 0 stub — implementation pending in subsequent tasks")


# ---------------------------------------------------------------------------
# Adaptive Card schema
# ---------------------------------------------------------------------------


class TestAdaptiveCardSchema:
    """Adaptive Card uses schema version 1.2 with TextBlock elements."""

    @pytest.mark.asyncio
    async def test_adaptive_card_schema(self):
        """Verify Adaptive Card body uses schema 1.2 with TextBlock elements."""
        pytest.skip("Wave 0 stub — implementation pending in subsequent tasks")

    @pytest.mark.asyncio
    async def test_approval_event_has_open_url_action(self):
        """Verify approval events include Action.OpenUrl linking to Pikar."""
        pytest.skip("Wave 0 stub — implementation pending in subsequent tasks")


# ---------------------------------------------------------------------------
# Briefing card
# ---------------------------------------------------------------------------


class TestBriefingCard:
    """Briefing Adaptive Card has ColumnSet for metrics."""

    @pytest.mark.asyncio
    async def test_briefing_card_structure(self):
        """Verify briefing Adaptive Card has ColumnSet for metrics layout."""
        pytest.skip("Wave 0 stub — implementation pending in subsequent tasks")


# ---------------------------------------------------------------------------
# Rate limit handling
# ---------------------------------------------------------------------------


class TestRateLimitHandling:
    """HTTP 429 is caught and logged without raising."""

    @pytest.mark.asyncio
    async def test_rate_limit_429_handled(self):
        """Verify HTTP 429 response is caught and logged without raising."""
        pytest.skip("Wave 0 stub — implementation pending in subsequent tasks")
