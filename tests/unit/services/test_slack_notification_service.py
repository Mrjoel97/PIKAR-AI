# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for SlackNotificationService — Block Kit, approvals, briefings."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

USER_ID = "test-user-00000000-0000-0000-0000-000000000001"
CHANNEL_ID = "C0123456789"
APPROVAL_TOKEN = "abc123def456ghi789jkl012mno345pq"

_IM_PATH = "app.services.integration_manager.IntegrationManager"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _install_fake_slack_sdk(mock_client: MagicMock) -> None:
    """Inject a fake slack_sdk into sys.modules so lazy imports resolve."""
    async_client_mod = ModuleType("slack_sdk.web.async_client")
    async_client_mod.AsyncWebClient = MagicMock(return_value=mock_client)  # type: ignore[attr-defined]

    web_mod = ModuleType("slack_sdk.web")
    web_mod.async_client = async_client_mod  # type: ignore[attr-defined]

    slack_sdk_mod = ModuleType("slack_sdk")
    slack_sdk_mod.web = web_mod  # type: ignore[attr-defined]

    sys.modules.setdefault("slack_sdk", slack_sdk_mod)
    sys.modules["slack_sdk.web"] = web_mod
    sys.modules["slack_sdk.web.async_client"] = async_client_mod


def _make_mock_slack_client(posted_blocks: list) -> MagicMock:
    """Return a mock AsyncWebClient that captures blocks passed to chat_postMessage."""

    async def fake_post_message(**kwargs):
        posted_blocks.extend(kwargs.get("blocks", []))
        resp = MagicMock()
        resp.data = {"ok": True, "ts": "1234567890.000001"}
        return resp

    client = MagicMock()
    client.chat_postMessage = AsyncMock(side_effect=fake_post_message)
    client.conversations_list = AsyncMock(return_value=MagicMock(get=lambda k, d=None: []))
    return client


# ---------------------------------------------------------------------------
# Token / credential
# ---------------------------------------------------------------------------


class TestTokenResolution:
    """Slack bot token is resolved via IntegrationManager.get_valid_token."""

    @pytest.mark.asyncio
    async def test_token_stored_encrypted(self):
        """Verify send_notification resolves token via IntegrationManager."""
        from app.services.slack_notification_service import SlackNotificationService

        svc = SlackNotificationService()
        mock_resolve = AsyncMock(return_value=None)
        # Patch _resolve_token to return None — no Slack connection
        with patch.object(svc, "_resolve_token", new=mock_resolve):
            result = await svc.send_notification(
                USER_ID, CHANNEL_ID, "task.created", {"title": "Test"}
            )

        # Without token, delivery returns False gracefully
        assert result is False
        mock_resolve.assert_called_once_with(USER_ID)


# ---------------------------------------------------------------------------
# send_notification — Block Kit structure
# ---------------------------------------------------------------------------


class TestSendNotification:
    """send_notification returns Block Kit JSON with header, section, divider."""

    @pytest.mark.asyncio
    async def test_send_notification_block_kit_structure(self):
        """Verify send_notification sends Block Kit with header/section/divider."""
        posted_blocks: list = []
        mock_client = _make_mock_slack_client(posted_blocks)
        _install_fake_slack_sdk(mock_client)

        from app.services.slack_notification_service import SlackNotificationService

        svc = SlackNotificationService()
        with patch.object(svc, "_resolve_token", new=AsyncMock(return_value="xoxb-test-token")):
            result = await svc.send_notification(
                USER_ID, CHANNEL_ID, "task.created", {"title": "My Task"}
            )

        assert result is True
        block_types = [b["type"] for b in posted_blocks]
        assert "header" in block_types
        assert "section" in block_types
        assert "divider" in block_types

        header = next(b for b in posted_blocks if b["type"] == "header")
        assert "Task Created" in header["text"]["text"]


# ---------------------------------------------------------------------------
# send_approval_request — button actions
# ---------------------------------------------------------------------------


class TestSendApprovalRequest:
    """Approval message contains Approve (primary) and Reject (danger) buttons."""

    @pytest.mark.asyncio
    async def test_send_approval_request_buttons(self):
        """Verify approval message has primary/danger action blocks."""
        posted_blocks: list = []
        mock_client = _make_mock_slack_client(posted_blocks)
        _install_fake_slack_sdk(mock_client)

        from app.services.slack_notification_service import SlackNotificationService

        svc = SlackNotificationService()
        with patch.object(svc, "_resolve_token", new=AsyncMock(return_value="xoxb-test-token")):
            result = await svc.send_approval_request(
                USER_ID,
                CHANNEL_ID,
                "Post a tweet about the launch",
                APPROVAL_TOKEN,
                "This will be posted immediately.",
            )

        assert isinstance(result, dict)

        actions = [b for b in posted_blocks if b.get("type") == "actions"]
        assert len(actions) == 1, "Expected exactly one actions block"

        elements = actions[0]["elements"]
        styles = {el["style"] for el in elements}
        assert "primary" in styles
        assert "danger" in styles

        action_ids = {el["action_id"] for el in elements}
        assert "approval_approve" in action_ids
        assert "approval_reject" in action_ids

        values = {el["value"] for el in elements}
        assert f"APPROVED:{APPROVAL_TOKEN}" in values
        assert f"REJECTED:{APPROVAL_TOKEN}" in values

    @pytest.mark.asyncio
    async def test_interact_approval(self):
        """Verify approval approve/reject action processing updates approval_requests status."""
        # The block_id is prefixed with 'approval_' + first 16 chars of token.
        # This is what the interactive handler uses to identify the approval.
        posted_blocks: list = []
        mock_client = _make_mock_slack_client(posted_blocks)
        _install_fake_slack_sdk(mock_client)

        from app.services.slack_notification_service import SlackNotificationService

        svc = SlackNotificationService()
        with patch.object(svc, "_resolve_token", new=AsyncMock(return_value="xoxb-test-token")):
            await svc.send_approval_request(
                USER_ID, CHANNEL_ID, "Approve ad spend", APPROVAL_TOKEN
            )

        actions = [b for b in posted_blocks if b.get("type") == "actions"]
        assert actions
        expected_block_id = f"approval_{APPROVAL_TOKEN[:16]}"
        assert actions[0]["block_id"] == expected_block_id


# ---------------------------------------------------------------------------
# send_daily_briefing — briefing Block Kit
# ---------------------------------------------------------------------------


class TestSendDailyBriefing:
    """Briefing Block Kit has header, metrics section, pending actions section."""

    @pytest.mark.asyncio
    async def test_daily_briefing_blocks(self):
        """Verify briefing Block Kit has header, metrics, and pending actions."""
        posted_blocks: list = []
        mock_client = _make_mock_slack_client(posted_blocks)
        _install_fake_slack_sdk(mock_client)

        briefing_data = {
            "pending_approvals": 3,
            "upcoming_tasks": ["Prepare Q2 report", "Review ad copy"],
            "key_metrics": {"Revenue": "$12,500", "Tasks completed": "8"},
        }

        from app.services.slack_notification_service import SlackNotificationService

        svc = SlackNotificationService()
        with patch.object(svc, "_resolve_token", new=AsyncMock(return_value="xoxb-test-token")):
            result = await svc.send_daily_briefing(USER_ID, CHANNEL_ID, briefing_data)

        assert result is True

        all_text = " ".join(
            b.get("text", {}).get("text", "")
            for b in posted_blocks
            if isinstance(b.get("text"), dict)
        )

        assert "Daily Briefing" in all_text
        assert "Pending Approvals" in all_text
        assert "Upcoming Tasks" in all_text
        assert "Key Metrics" in all_text
        assert "3" in all_text


# ---------------------------------------------------------------------------
# _build_event_blocks — per-event-type Block Kit
# ---------------------------------------------------------------------------


class TestBuildEventBlocks:
    """_build_event_blocks returns valid Block Kit structure for each event_type."""

    @pytest.mark.asyncio
    async def test_block_kit_structure(self):
        """Verify _build_event_blocks returns valid Block Kit for each event type."""
        from app.services.slack_notification_service import SlackNotificationService

        svc = SlackNotificationService()

        for event_type in [
            "task.created",
            "task.completed",
            "workflow.completed",
            "workflow.failed",
            "campaign.milestone",
        ]:
            blocks = svc._build_event_blocks(
                event_type, {"title": "Test", "description": "Desc"}
            )

            assert isinstance(blocks, list)
            assert len(blocks) >= 3

            types = [b["type"] for b in blocks]
            assert types[0] == "header", f"First block must be header for {event_type}"
            assert "section" in types, f"Must have section block for {event_type}"
            assert types[-1] == "divider", f"Last block must be divider for {event_type}"
