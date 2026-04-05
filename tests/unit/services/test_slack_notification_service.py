# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for SlackNotificationService — Block Kit, approvals, briefings."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

USER_ID = "test-user-00000000-0000-0000-0000-000000000001"
CHANNEL_ID = "C0123456789"


# ---------------------------------------------------------------------------
# Token / credential
# ---------------------------------------------------------------------------


class TestTokenResolution:
    """Slack bot token is resolved via IntegrationManager.get_valid_token."""

    @pytest.mark.asyncio
    async def test_token_stored_encrypted(self):
        """Verify send_notification resolves token via IntegrationManager."""
        pytest.skip("Wave 0 stub — implementation pending in subsequent tasks")


# ---------------------------------------------------------------------------
# send_notification — Block Kit structure
# ---------------------------------------------------------------------------


class TestSendNotification:
    """send_notification returns Block Kit JSON with header, section, divider."""

    @pytest.mark.asyncio
    async def test_send_notification_block_kit_structure(self):
        """Verify send_notification sends Block Kit with header/section/divider."""
        pytest.skip("Wave 0 stub — implementation pending in subsequent tasks")


# ---------------------------------------------------------------------------
# send_approval_request — button actions
# ---------------------------------------------------------------------------


class TestSendApprovalRequest:
    """Approval message contains Approve (primary) and Reject (danger) buttons."""

    @pytest.mark.asyncio
    async def test_send_approval_request_buttons(self):
        """Verify approval message has primary/danger action blocks."""
        pytest.skip("Wave 0 stub — implementation pending in subsequent tasks")

    @pytest.mark.asyncio
    async def test_interact_approval(self):
        """Verify approve/reject action processing updates approval_requests status."""
        pytest.skip("Wave 0 stub — implementation pending in subsequent tasks")


# ---------------------------------------------------------------------------
# send_daily_briefing — briefing Block Kit
# ---------------------------------------------------------------------------


class TestSendDailyBriefing:
    """Briefing Block Kit has header, metrics section, pending actions section."""

    @pytest.mark.asyncio
    async def test_daily_briefing_blocks(self):
        """Verify briefing Block Kit has header, metrics, and pending actions."""
        pytest.skip("Wave 0 stub — implementation pending in subsequent tasks")


# ---------------------------------------------------------------------------
# _build_event_blocks — per-event-type Block Kit
# ---------------------------------------------------------------------------


class TestBuildEventBlocks:
    """_build_event_blocks returns valid Block Kit structure for each event_type."""

    @pytest.mark.asyncio
    async def test_block_kit_structure(self):
        """Verify _build_event_blocks returns valid Block Kit for each event type."""
        pytest.skip("Wave 0 stub — implementation pending in subsequent tasks")
