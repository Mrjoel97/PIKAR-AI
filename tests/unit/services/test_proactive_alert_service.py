# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for ProactiveAlertService -- dedup, in-app creation, fan-out dispatch."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

USER_ID = "test-user-00000000-0000-0000-0000-000000000001"


def _make_mock_client() -> MagicMock:
    """Build a mock Supabase service client with a chainable query interface."""
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.in_.return_value = mock_chain
    mock_chain.gte.return_value = mock_chain
    mock_chain.lte.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.limit.return_value = mock_chain
    mock_chain.insert.return_value = mock_chain
    mock_chain.upsert.return_value = mock_chain
    mock_chain.delete.return_value = mock_chain
    mock_chain.update.return_value = mock_chain
    mock_chain.neq.return_value = mock_chain
    mock_chain.maybe_single.return_value = mock_chain

    mock_table = MagicMock()
    mock_table.select.return_value = mock_chain
    mock_table.insert.return_value = mock_chain
    mock_table.upsert.return_value = mock_chain
    mock_table.update.return_value = mock_chain
    mock_table.delete.return_value = mock_chain

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    return mock_client


# ---------------------------------------------------------------------------
# dispatch_proactive_alert
# ---------------------------------------------------------------------------


class TestDispatchProactiveAlert:
    """ProactiveAlertService.dispatch_proactive_alert tests."""

    @pytest.mark.asyncio
    async def test_creates_in_app_notification(self):
        """Dispatch creates an in-app notification via NotificationService."""
        mock_client = _make_mock_client()
        mock_notif_svc = MagicMock()
        mock_notif_svc.create_notification = AsyncMock(
            return_value={"id": "notif-1"}
        )

        # Dedup check returns no existing row (not a duplicate)
        dedup_result = MagicMock()
        dedup_result.data = []

        # Insert log returns success
        insert_result = MagicMock()
        insert_result.data = [{"id": "log-1"}]

        with (
            patch(
                "app.services.proactive_alert_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.proactive_alert_service.execute_async",
                new_callable=AsyncMock,
                side_effect=[dedup_result, insert_result],
            ),
            patch(
                "app.services.proactive_alert_service.NotificationService",
                return_value=mock_notif_svc,
            ),
            patch(
                "app.services.proactive_alert_service.dispatch_notification",
                new_callable=AsyncMock,
                return_value={"slack": True},
            ),
        ):
            from app.services.proactive_alert_service import ProactiveAlertService

            svc = ProactiveAlertService()
            result = await svc.dispatch_proactive_alert(
                user_id=USER_ID,
                alert_type="daily_briefing",
                alert_key="2026-04-09",
                title="Daily Briefing",
                message="Here is your briefing.",
            )

            assert result["dispatched"] is True
            mock_notif_svc.create_notification.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fans_out_to_external_channels(self):
        """Dispatch fans out to Slack/Teams via dispatch_notification."""
        mock_client = _make_mock_client()
        mock_notif_svc = MagicMock()
        mock_notif_svc.create_notification = AsyncMock(
            return_value={"id": "notif-1"}
        )

        dedup_result = MagicMock()
        dedup_result.data = []

        insert_result = MagicMock()
        insert_result.data = [{"id": "log-1"}]

        mock_dispatch = AsyncMock(return_value={"slack": True, "teams": True})

        with (
            patch(
                "app.services.proactive_alert_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.proactive_alert_service.execute_async",
                new_callable=AsyncMock,
                side_effect=[dedup_result, insert_result],
            ),
            patch(
                "app.services.proactive_alert_service.NotificationService",
                return_value=mock_notif_svc,
            ),
            patch(
                "app.services.proactive_alert_service.dispatch_notification",
                mock_dispatch,
            ),
        ):
            from app.services.proactive_alert_service import ProactiveAlertService

            svc = ProactiveAlertService()
            result = await svc.dispatch_proactive_alert(
                user_id=USER_ID,
                alert_type="daily_briefing",
                alert_key="2026-04-09",
                title="Daily Briefing",
                message="Here is your briefing.",
            )

            assert result["dispatched"] is True
            assert result["channels"]["slack"] is True
            mock_dispatch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deduplicates_same_alert_type_user_date(self):
        """Dispatch skips when proactive_alert_log already has (user_id, alert_type, alert_key)."""
        mock_client = _make_mock_client()

        # Dedup check returns an existing row -- duplicate
        dedup_result = MagicMock()
        dedup_result.data = [{"id": "existing-log-1"}]

        mock_notif_svc = MagicMock()
        mock_notif_svc.create_notification = AsyncMock()

        with (
            patch(
                "app.services.proactive_alert_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.proactive_alert_service.execute_async",
                new_callable=AsyncMock,
                return_value=dedup_result,
            ),
            patch(
                "app.services.proactive_alert_service.NotificationService",
                return_value=mock_notif_svc,
            ),
            patch(
                "app.services.proactive_alert_service.dispatch_notification",
                new_callable=AsyncMock,
            ) as mock_dispatch,
        ):
            from app.services.proactive_alert_service import ProactiveAlertService

            svc = ProactiveAlertService()
            result = await svc.dispatch_proactive_alert(
                user_id=USER_ID,
                alert_type="daily_briefing",
                alert_key="2026-04-09",
                title="Daily Briefing",
                message="Duplicate should be skipped.",
            )

            assert result["dispatched"] is False
            mock_notif_svc.create_notification.assert_not_awaited()
            mock_dispatch.assert_not_awaited()
