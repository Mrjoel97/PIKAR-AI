# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for IntegrationHealthMonitor -- token expiry, connectivity, alert dispatch."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

USER_ID = "test-user-00000000-0000-0000-0000-000000000001"
USER_ID_2 = "test-user-00000000-0000-0000-0000-000000000002"


def _make_mock_client() -> MagicMock:
    """Build a mock Supabase service client with a chainable query interface."""
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.in_.return_value = mock_chain
    mock_chain.gte.return_value = mock_chain
    mock_chain.lte.return_value = mock_chain
    mock_chain.lt.return_value = mock_chain
    mock_chain.gt.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.limit.return_value = mock_chain
    mock_chain.insert.return_value = mock_chain
    mock_chain.upsert.return_value = mock_chain
    mock_chain.delete.return_value = mock_chain
    mock_chain.update.return_value = mock_chain
    mock_chain.neq.return_value = mock_chain
    mock_chain.not_.return_value = mock_chain
    mock_chain.is_.return_value = mock_chain
    mock_chain.filter.return_value = mock_chain

    mock_table = MagicMock()
    mock_table.select.return_value = mock_chain
    mock_table.insert.return_value = mock_chain
    mock_table.upsert.return_value = mock_chain
    mock_table.update.return_value = mock_chain
    mock_table.delete.return_value = mock_chain

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    return mock_client


def _cred_row(
    user_id: str,
    provider: str,
    expires_at: str | None,
    account_name: str = "Test Account",
) -> dict:
    """Build a mock integration_credentials row."""
    return {
        "id": f"cred-{provider}-{user_id[:8]}",
        "user_id": user_id,
        "provider": provider,
        "access_token": "enc_token_placeholder",
        "refresh_token": "enc_refresh_placeholder",
        "expires_at": expires_at,
        "account_name": account_name,
        "scopes": "read write",
    }


# ---------------------------------------------------------------------------
# check_token_expiry
# ---------------------------------------------------------------------------


class TestCheckTokenExpiry:
    """check_token_expiry returns tokens expiring within the threshold."""

    @pytest.mark.asyncio
    async def test_finds_tokens_expiring_within_3_days(self):
        """Tokens expiring within 3 days are returned with days_remaining."""
        now = datetime.now(tz=timezone.utc)
        expiring_soon = (now + timedelta(days=2)).isoformat()
        safe_token = (now + timedelta(days=10)).isoformat()

        mock_client = _make_mock_client()

        # execute_async returns credentials that the DB would filter
        expiry_result = MagicMock()
        expiry_result.data = [
            _cred_row(USER_ID, "google", expiring_soon),
        ]

        with (
            patch(
                "app.services.integration_health_monitor.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.integration_health_monitor.execute_async",
                new_callable=AsyncMock,
                return_value=expiry_result,
            ),
        ):
            from app.services.integration_health_monitor import (
                IntegrationHealthMonitor,
            )

            monitor = IntegrationHealthMonitor()
            results = await monitor.check_token_expiry(days_threshold=3)

        assert len(results) >= 1
        assert results[0]["provider"] == "google"
        assert results[0]["user_id"] == USER_ID
        assert results[0]["days_remaining"] <= 3

    @pytest.mark.asyncio
    async def test_ignores_tokens_with_no_expires_at(self):
        """Tokens with null expires_at (API keys) are not included."""
        mock_client = _make_mock_client()

        # Query returns empty because DB filters out null expires_at
        empty_result = MagicMock()
        empty_result.data = []

        with (
            patch(
                "app.services.integration_health_monitor.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.integration_health_monitor.execute_async",
                new_callable=AsyncMock,
                return_value=empty_result,
            ),
        ):
            from app.services.integration_health_monitor import (
                IntegrationHealthMonitor,
            )

            monitor = IntegrationHealthMonitor()
            results = await monitor.check_token_expiry()

        assert results == []

    @pytest.mark.asyncio
    async def test_ignores_already_expired_tokens(self):
        """Already expired tokens are filtered out by the DB query (expires_at > now)."""
        mock_client = _make_mock_client()

        # DB would filter these out with expires_at > now()
        empty_result = MagicMock()
        empty_result.data = []

        with (
            patch(
                "app.services.integration_health_monitor.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.integration_health_monitor.execute_async",
                new_callable=AsyncMock,
                return_value=empty_result,
            ),
        ):
            from app.services.integration_health_monitor import (
                IntegrationHealthMonitor,
            )

            monitor = IntegrationHealthMonitor()
            results = await monitor.check_token_expiry()

        assert results == []


# ---------------------------------------------------------------------------
# check_connectivity
# ---------------------------------------------------------------------------


class TestCheckConnectivity:
    """check_connectivity tests for provider health checks."""

    @pytest.mark.asyncio
    async def test_returns_unhealthy_when_provider_fails(self):
        """Unhealthy provider connections are returned."""
        mock_client = _make_mock_client()

        cred_result = MagicMock()
        cred_result.data = [
            _cred_row(USER_ID, "google", None, "My Google"),
        ]

        with (
            patch(
                "app.services.integration_health_monitor.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.integration_health_monitor.execute_async",
                new_callable=AsyncMock,
                return_value=cred_result,
            ),
            patch(
                "app.services.integration_health_monitor.httpx.AsyncClient",
            ) as mock_httpx_cls,
        ):
            # Make the HTTP call raise a timeout
            mock_http_client = AsyncMock()
            mock_http_client.get = AsyncMock(
                side_effect=Exception("Connection timeout")
            )
            mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_http_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx_cls.return_value = mock_http_client

            from app.services.integration_health_monitor import (
                IntegrationHealthMonitor,
            )

            monitor = IntegrationHealthMonitor()
            results = await monitor.check_connectivity()

        # Should contain at least one unhealthy result
        assert len(results) >= 1
        unhealthy = [r for r in results if r["status"] == "unhealthy"]
        assert len(unhealthy) >= 1
        assert unhealthy[0]["user_id"] == USER_ID

    @pytest.mark.asyncio
    async def test_healthy_provider_not_in_results(self):
        """Healthy provider connections are not returned (only unhealthy)."""
        mock_client = _make_mock_client()

        cred_result = MagicMock()
        cred_result.data = [
            _cred_row(USER_ID, "slack", None, "My Slack"),
        ]

        with (
            patch(
                "app.services.integration_health_monitor.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.integration_health_monitor.execute_async",
                new_callable=AsyncMock,
                return_value=cred_result,
            ),
            patch(
                "app.services.integration_health_monitor.httpx.AsyncClient",
            ) as mock_httpx_cls,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()

            mock_http_client = AsyncMock()
            mock_http_client.get = AsyncMock(return_value=mock_response)
            mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_http_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx_cls.return_value = mock_http_client

            from app.services.integration_health_monitor import (
                IntegrationHealthMonitor,
            )

            monitor = IntegrationHealthMonitor()
            results = await monitor.check_connectivity()

        # All healthy => empty result
        assert results == []


# ---------------------------------------------------------------------------
# run_integration_health_check
# ---------------------------------------------------------------------------


class TestRunIntegrationHealthCheck:
    """run_integration_health_check dispatches alerts for expiring tokens and unhealthy providers."""

    @pytest.mark.asyncio
    async def test_dispatches_warning_for_expiring_token(self):
        """Expiring tokens trigger a WARNING alert via dispatch_proactive_alert."""
        now = datetime.now(tz=timezone.utc)
        expiring_in_2_days = (now + timedelta(days=2)).isoformat()

        mock_client = _make_mock_client()

        # check_token_expiry returns one expiring token
        expiry_result = MagicMock()
        expiry_result.data = [
            _cred_row(USER_ID, "google_ads", expiring_in_2_days, "My Google Ads"),
        ]

        # check_connectivity returns no unhealthy
        cred_result = MagicMock()
        cred_result.data = []

        mock_dispatch = AsyncMock(return_value={"dispatched": True, "channels": {}})

        with (
            patch(
                "app.services.integration_health_monitor.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.integration_health_monitor.execute_async",
                new_callable=AsyncMock,
                side_effect=[expiry_result, cred_result],
            ),
            patch(
                "app.services.integration_health_monitor.dispatch_proactive_alert",
                mock_dispatch,
            ),
        ):
            from app.services.integration_health_monitor import (
                IntegrationHealthMonitor,
            )

            monitor = IntegrationHealthMonitor()
            result = await monitor.run_integration_health_check()

        # Should have called dispatch for the expiring token
        assert mock_dispatch.call_count >= 1
        call_kwargs = mock_dispatch.call_args_list[0][1]
        assert call_kwargs["alert_type"] == "integration.token_expiring"
        assert "Google Ads" in call_kwargs["message"]
        assert call_kwargs["notification_type"].value == "warning"
        assert call_kwargs["link"] == "/settings/integrations"
        assert result["tokens_expiring"] >= 1

    @pytest.mark.asyncio
    async def test_dispatches_error_for_unhealthy_connectivity(self):
        """Failed connectivity checks trigger an ERROR alert."""
        mock_client = _make_mock_client()

        # check_token_expiry returns empty
        expiry_result = MagicMock()
        expiry_result.data = []

        # check_connectivity returns unhealthy for google
        cred_result = MagicMock()
        cred_result.data = [
            _cred_row(USER_ID, "google", None, "My Google"),
        ]

        mock_dispatch = AsyncMock(return_value={"dispatched": True, "channels": {}})

        with (
            patch(
                "app.services.integration_health_monitor.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.integration_health_monitor.execute_async",
                new_callable=AsyncMock,
                side_effect=[expiry_result, cred_result],
            ),
            patch(
                "app.services.integration_health_monitor.dispatch_proactive_alert",
                mock_dispatch,
            ),
            patch(
                "app.services.integration_health_monitor.httpx.AsyncClient",
            ) as mock_httpx_cls,
        ):
            mock_http_client = AsyncMock()
            mock_http_client.get = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_http_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx_cls.return_value = mock_http_client

            from app.services.integration_health_monitor import (
                IntegrationHealthMonitor,
            )

            monitor = IntegrationHealthMonitor()
            result = await monitor.run_integration_health_check()

        # Should have dispatched an ERROR alert
        error_calls = [
            c
            for c in mock_dispatch.call_args_list
            if c[1].get("alert_type") == "integration.unhealthy"
        ]
        assert len(error_calls) >= 1
        call_kwargs = error_calls[0][1]
        assert call_kwargs["notification_type"].value == "error"
        assert result["unhealthy"] >= 1

    @pytest.mark.asyncio
    async def test_deduplication_uses_today_in_alert_key(self):
        """Alert key includes today's date for daily deduplication."""
        from datetime import date

        now = datetime.now(tz=timezone.utc)
        expiring = (now + timedelta(days=1)).isoformat()
        today_str = date.today().isoformat()

        mock_client = _make_mock_client()

        expiry_result = MagicMock()
        expiry_result.data = [
            _cred_row(USER_ID, "stripe", expiring, "My Stripe"),
        ]

        cred_result = MagicMock()
        cred_result.data = []

        mock_dispatch = AsyncMock(return_value={"dispatched": True, "channels": {}})

        with (
            patch(
                "app.services.integration_health_monitor.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.integration_health_monitor.execute_async",
                new_callable=AsyncMock,
                side_effect=[expiry_result, cred_result],
            ),
            patch(
                "app.services.integration_health_monitor.dispatch_proactive_alert",
                mock_dispatch,
            ),
        ):
            from app.services.integration_health_monitor import (
                IntegrationHealthMonitor,
            )

            monitor = IntegrationHealthMonitor()
            await monitor.run_integration_health_check()

        assert mock_dispatch.call_count >= 1
        alert_key = mock_dispatch.call_args_list[0][1]["alert_key"]
        assert today_str in alert_key
        assert "stripe" in alert_key

    @pytest.mark.asyncio
    async def test_returns_summary_counts(self):
        """Result includes tokens_checked, tokens_expiring, connectivity_checked, unhealthy, alerts_sent."""
        mock_client = _make_mock_client()

        expiry_result = MagicMock()
        expiry_result.data = []

        cred_result = MagicMock()
        cred_result.data = []

        with (
            patch(
                "app.services.integration_health_monitor.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.integration_health_monitor.execute_async",
                new_callable=AsyncMock,
                side_effect=[expiry_result, cred_result],
            ),
            patch(
                "app.services.integration_health_monitor.dispatch_proactive_alert",
                new_callable=AsyncMock,
                return_value={"dispatched": True, "channels": {}},
            ),
        ):
            from app.services.integration_health_monitor import (
                IntegrationHealthMonitor,
            )

            monitor = IntegrationHealthMonitor()
            result = await monitor.run_integration_health_check()

        assert "tokens_checked" in result
        assert "tokens_expiring" in result
        assert "connectivity_checked" in result
        assert "unhealthy" in result
        assert "alerts_sent" in result


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------


class TestModuleLevelConvenience:
    """Test the module-level run_integration_health_check function."""

    @pytest.mark.asyncio
    async def test_module_level_function_delegates_to_class(self):
        """Module-level run_integration_health_check delegates to IntegrationHealthMonitor."""
        mock_client = _make_mock_client()

        expiry_result = MagicMock()
        expiry_result.data = []

        cred_result = MagicMock()
        cred_result.data = []

        with (
            patch(
                "app.services.integration_health_monitor.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.integration_health_monitor.execute_async",
                new_callable=AsyncMock,
                side_effect=[expiry_result, cred_result],
            ),
            patch(
                "app.services.integration_health_monitor.dispatch_proactive_alert",
                new_callable=AsyncMock,
                return_value={"dispatched": True, "channels": {}},
            ),
        ):
            from app.services.integration_health_monitor import (
                run_integration_health_check,
            )

            result = await run_integration_health_check()

        assert "tokens_checked" in result
        assert "alerts_sent" in result
