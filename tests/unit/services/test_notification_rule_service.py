# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for NotificationRuleService — CRUD, matching rules, channel config."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

USER_ID = "test-user-00000000-0000-0000-0000-000000000001"
RULE_ID = "rule-00000000-0000-0000-0000-000000000001"


def _make_mock_client() -> MagicMock:
    """Build a mock Supabase service client with a chainable query interface."""
    mock_result = MagicMock()
    mock_result.data = []

    # Build a chainable mock — every method returns self so .eq().eq().execute() works
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.limit.return_value = mock_chain
    mock_chain.update.return_value = mock_chain
    mock_chain.delete.return_value = mock_chain
    mock_chain.insert.return_value = mock_chain
    mock_chain.upsert.return_value = mock_chain

    mock_table = MagicMock()
    mock_table.select.return_value = mock_chain
    mock_table.update.return_value = mock_chain
    mock_table.delete.return_value = mock_chain
    mock_table.insert.return_value = mock_chain
    mock_table.upsert.return_value = mock_chain

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    return mock_client


# ---------------------------------------------------------------------------
# CRUD — create / list / update / delete
# ---------------------------------------------------------------------------


class TestRuleCrud:
    """Basic CRUD operations on notification_rules rows."""

    @pytest.mark.asyncio
    async def test_create_rule(self):
        """Verify create_rule upserts a notification_rules row with on_conflict."""
        mock_client = _make_mock_client()
        mock_row = {
            "id": RULE_ID,
            "user_id": USER_ID,
            "provider": "slack",
            "event_type": "approval.pending",
            "channel_id": "C12345",
            "channel_name": "#approvals",
            "enabled": True,
        }

        with (
            patch(
                "app.services.notification_rule_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.notification_rule_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=[mock_row]),
            ) as mock_exec,
        ):
            from app.services.notification_rule_service import NotificationRuleService

            svc = NotificationRuleService()
            result = await svc.create_rule(
                user_id=USER_ID,
                provider="slack",
                event_type="approval.pending",
                channel_id="C12345",
                channel_name="#approvals",
            )

        # Verify upsert was called on the correct table
        mock_client.table.assert_called_with("notification_rules")
        mock_client.table().upsert.assert_called_once()
        call_args = mock_client.table().upsert.call_args
        # First positional arg is the row dict
        row_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("json")
        assert row_arg is not None
        # on_conflict kwarg must be set
        on_conflict = call_args.kwargs.get("on_conflict", "")
        assert "user_id" in on_conflict
        assert "provider" in on_conflict
        assert "event_type" in on_conflict
        assert "channel_id" in on_conflict
        # execute_async was called
        mock_exec.assert_called_once()
        # Returned the upserted row
        assert result["id"] == RULE_ID

    @pytest.mark.asyncio
    async def test_list_rules_by_provider(self):
        """Verify list_rules adds a provider eq filter when provider is given."""
        mock_client = _make_mock_client()

        with (
            patch(
                "app.services.notification_rule_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.notification_rule_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=[]),
            ) as mock_exec,
        ):
            from app.services.notification_rule_service import NotificationRuleService

            svc = NotificationRuleService()
            await svc.list_rules(USER_ID, provider="slack")

        mock_exec.assert_called_once()
        # Verify the chain includes a provider eq filter
        table_mock = mock_client.table.return_value
        # .eq should have been called at least twice: user_id + provider
        eq_calls = [str(c) for c in table_mock.select.return_value.eq.call_args_list]
        combined = " ".join(str(c) for c in table_mock.select.return_value.eq.call_args_list)
        assert "provider" in combined or "slack" in combined

    @pytest.mark.asyncio
    async def test_toggle_rule_enabled(self):
        """Verify update_rule filters by both rule_id and user_id."""
        mock_client = _make_mock_client()
        mock_updated = {"id": RULE_ID, "user_id": USER_ID, "enabled": False}

        with (
            patch(
                "app.services.notification_rule_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.notification_rule_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=[mock_updated]),
            ) as mock_exec,
        ):
            from app.services.notification_rule_service import NotificationRuleService

            svc = NotificationRuleService()
            result = await svc.update_rule(
                user_id=USER_ID,
                rule_id=RULE_ID,
                enabled=False,
            )

        mock_exec.assert_called_once()
        # update was called with the enabled flag
        table_mock = mock_client.table.return_value
        table_mock.update.assert_called_once_with({"enabled": False})
        # The chain must filter by id and user_id
        eq_calls_str = str(table_mock.update.return_value.eq.call_args_list)
        assert RULE_ID in eq_calls_str
        assert USER_ID in eq_calls_str
        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_delete_rule(self):
        """Verify delete_rule filters by both rule_id and user_id."""
        mock_client = _make_mock_client()
        mock_deleted = {"id": RULE_ID}

        with (
            patch(
                "app.services.notification_rule_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.notification_rule_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=[mock_deleted]),
            ) as mock_exec,
        ):
            from app.services.notification_rule_service import NotificationRuleService

            svc = NotificationRuleService()
            deleted = await svc.delete_rule(user_id=USER_ID, rule_id=RULE_ID)

        mock_exec.assert_called_once()
        # delete() must have been called
        table_mock = mock_client.table.return_value
        table_mock.delete.assert_called_once()
        # Both rule_id and user_id must appear in the eq filter chain
        eq_calls_str = str(table_mock.delete.return_value.eq.call_args_list)
        assert RULE_ID in eq_calls_str
        assert USER_ID in eq_calls_str
        assert deleted is True


# ---------------------------------------------------------------------------
# Rule matching
# ---------------------------------------------------------------------------


class TestRuleMatching:
    """get_matching_rules returns only enabled rules for a given event_type."""

    @pytest.mark.asyncio
    async def test_get_matching_rules(self):
        """Verify get_matching_rules query includes enabled=True filter."""
        mock_client = _make_mock_client()
        matching_rule = {
            "id": RULE_ID,
            "user_id": USER_ID,
            "provider": "slack",
            "event_type": "task.created",
            "channel_id": "C99999",
            "enabled": True,
        }

        with (
            patch(
                "app.services.notification_rule_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.notification_rule_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=[matching_rule]),
            ) as mock_exec,
        ):
            from app.services.notification_rule_service import NotificationRuleService

            svc = NotificationRuleService()
            results = await svc.get_matching_rules(USER_ID, "task.created")

        mock_exec.assert_called_once()
        # eq chain must include enabled=True filter
        table_mock = mock_client.table.return_value
        all_eq_calls = str(table_mock.select.return_value.eq.call_args_list)
        assert "enabled" in all_eq_calls or "True" in all_eq_calls
        assert len(results) == 1
        assert results[0]["event_type"] == "task.created"


# ---------------------------------------------------------------------------
# Channel config upsert
# ---------------------------------------------------------------------------


class TestChannelConfig:
    """Channel config upsert is idempotent on (user_id, provider)."""

    @pytest.mark.asyncio
    async def test_upsert_channel_config(self):
        """Verify upsert_channel_config calls upsert on notification_channel_config."""
        mock_client = _make_mock_client()
        expected_row = {
            "user_id": USER_ID,
            "provider": "slack",
            "daily_briefing": True,
            "briefing_channel_id": "C11111",
            "briefing_channel_name": "#daily",
            "briefing_time_utc": "09:00",
        }

        with (
            patch(
                "app.services.notification_rule_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.notification_rule_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=[expected_row]),
            ) as mock_exec,
        ):
            from app.services.notification_rule_service import NotificationRuleService

            svc = NotificationRuleService()
            result = await svc.upsert_channel_config(
                user_id=USER_ID,
                provider="slack",
                daily_briefing=True,
                briefing_channel_id="C11111",
                briefing_channel_name="#daily",
                briefing_time_utc="09:00",
            )

        mock_exec.assert_called_once()
        # upsert must target the channel_config table
        mock_client.table.assert_called_with("notification_channel_config")
        table_mock = mock_client.table.return_value
        table_mock.upsert.assert_called_once()
        upsert_kwargs = table_mock.upsert.call_args.kwargs
        assert upsert_kwargs.get("on_conflict") == "user_id,provider"
        # Returned row has expected values
        assert result["daily_briefing"] is True
        assert result["briefing_channel_id"] == "C11111"
