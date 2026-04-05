# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for NotificationRuleService — CRUD, matching rules, channel config."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

USER_ID = "test-user-00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# CRUD — create / list / update / delete
# ---------------------------------------------------------------------------


class TestRuleCrud:
    """Basic CRUD operations on notification_rules rows."""

    @pytest.mark.asyncio
    async def test_create_rule(self):
        """Verify create_rule upserts a notification_rules row."""
        pytest.skip("Wave 0 stub — implementation pending in subsequent tasks")

    @pytest.mark.asyncio
    async def test_list_rules_by_provider(self):
        """Verify list_rules filters rows by provider."""
        pytest.skip("Wave 0 stub — implementation pending in subsequent tasks")

    @pytest.mark.asyncio
    async def test_toggle_rule_enabled(self):
        """Verify update_rule toggles the enabled flag on a rule."""
        pytest.skip("Wave 0 stub — implementation pending in subsequent tasks")

    @pytest.mark.asyncio
    async def test_delete_rule(self):
        """Verify delete_rule removes the notification_rules row."""
        pytest.skip("Wave 0 stub — implementation pending in subsequent tasks")


# ---------------------------------------------------------------------------
# Rule matching
# ---------------------------------------------------------------------------


class TestRuleMatching:
    """get_matching_rules returns only enabled rules for a given event_type."""

    @pytest.mark.asyncio
    async def test_get_matching_rules(self):
        """Verify get_matching_rules returns only enabled rules for event_type."""
        pytest.skip("Wave 0 stub — implementation pending in subsequent tasks")


# ---------------------------------------------------------------------------
# Channel config upsert
# ---------------------------------------------------------------------------


class TestChannelConfig:
    """Channel config upsert is idempotent on (user_id, provider)."""

    @pytest.mark.asyncio
    async def test_upsert_channel_config(self):
        """Verify channel config upsert on (user_id, provider) is idempotent."""
        pytest.skip("Wave 0 stub — implementation pending in subsequent tasks")
