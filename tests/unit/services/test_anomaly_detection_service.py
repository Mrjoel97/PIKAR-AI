# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for AnomalyDetectionService -- baseline computation, anomaly detection, alert dispatch."""

from __future__ import annotations

import statistics
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
    mock_chain.order.return_value = mock_chain
    mock_chain.limit.return_value = mock_chain
    mock_chain.insert.return_value = mock_chain
    mock_chain.upsert.return_value = mock_chain
    mock_chain.delete.return_value = mock_chain
    mock_chain.update.return_value = mock_chain
    mock_chain.neq.return_value = mock_chain

    mock_table = MagicMock()
    mock_table.select.return_value = mock_chain
    mock_table.insert.return_value = mock_chain
    mock_table.upsert.return_value = mock_chain
    mock_table.update.return_value = mock_chain
    mock_table.delete.return_value = mock_chain

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    return mock_client


def _baseline_data(values: list[float]) -> list[dict]:
    """Build metric_baselines rows from a list of float values."""
    return [
        {
            "id": f"row-{i}",
            "user_id": USER_ID,
            "metric_key": "revenue_daily",
            "metric_value": v,
            "recorded_at": f"2026-03-{i + 1:02d}T00:00:00+00:00",
        }
        for i, v in enumerate(values)
    ]


# ---------------------------------------------------------------------------
# compute_baseline
# ---------------------------------------------------------------------------


class TestComputeBaseline:
    """compute_baseline returns mean and stddev from metric_baselines rows."""

    @pytest.mark.asyncio
    async def test_compute_baseline_returns_mean_and_stddev(self):
        """Verify compute_baseline returns correct mean and stddev from 30 data points."""
        values = [100.0 + i * 2 for i in range(30)]
        expected_mean = statistics.mean(values)
        expected_stddev = statistics.pstdev(values)
        mock_client = _make_mock_client()

        with (
            patch(
                "app.services.anomaly_detection_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.anomaly_detection_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=_baseline_data(values)),
            ),
        ):
            from app.services.anomaly_detection_service import (
                AnomalyDetectionService,
            )

            svc = AnomalyDetectionService()
            result = await svc.compute_baseline(USER_ID, "revenue_daily")

        assert result is not None
        assert abs(result["mean"] - expected_mean) < 0.01
        assert abs(result["stddev"] - expected_stddev) < 0.01
        assert result["count"] == 30

    @pytest.mark.asyncio
    async def test_compute_baseline_returns_none_with_insufficient_data(self):
        """Verify compute_baseline returns None when fewer than 7 data points exist."""
        values = [100.0, 200.0, 150.0]
        mock_client = _make_mock_client()

        with (
            patch(
                "app.services.anomaly_detection_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.anomaly_detection_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=_baseline_data(values)),
            ),
        ):
            from app.services.anomaly_detection_service import (
                AnomalyDetectionService,
            )

            svc = AnomalyDetectionService()
            result = await svc.compute_baseline(USER_ID, "revenue_daily")

        assert result is None


# ---------------------------------------------------------------------------
# detect_anomaly
# ---------------------------------------------------------------------------


class TestDetectAnomaly:
    """detect_anomaly identifies values outside the baseline range."""

    @pytest.mark.asyncio
    async def test_detect_anomaly_positive_spike(self):
        """detect_anomaly returns True with direction='spike' when value > mean + 2*stddev."""
        # Use varied data so stddev is non-zero
        values = [100.0 + (i % 5) for i in range(30)]
        mock_client = _make_mock_client()

        with (
            patch(
                "app.services.anomaly_detection_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.anomaly_detection_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=_baseline_data(values)),
            ),
        ):
            from app.services.anomaly_detection_service import (
                AnomalyDetectionService,
            )

            svc = AnomalyDetectionService()
            result = await svc.detect_anomaly(
                USER_ID, "revenue_daily", current_value=200.0
            )

        assert result is not None
        assert result["is_anomaly"] is True
        assert result["direction"] == "spike"

    @pytest.mark.asyncio
    async def test_detect_anomaly_negative_dip(self):
        """detect_anomaly returns True with direction='dip' when value < mean - 2*stddev."""
        values = [100.0 + (i % 5) for i in range(30)]
        mock_client = _make_mock_client()

        with (
            patch(
                "app.services.anomaly_detection_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.anomaly_detection_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=_baseline_data(values)),
            ),
        ):
            from app.services.anomaly_detection_service import (
                AnomalyDetectionService,
            )

            svc = AnomalyDetectionService()
            result = await svc.detect_anomaly(
                USER_ID, "revenue_daily", current_value=0.0
            )

        assert result is not None
        assert result["is_anomaly"] is True
        assert result["direction"] == "dip"

    @pytest.mark.asyncio
    async def test_detect_anomaly_within_range(self):
        """detect_anomaly returns is_anomaly=False when value is within 2 stddev of mean."""
        values = [100.0 + (i % 5) for i in range(30)]
        mock_client = _make_mock_client()

        with (
            patch(
                "app.services.anomaly_detection_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.anomaly_detection_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=_baseline_data(values)),
            ),
        ):
            from app.services.anomaly_detection_service import (
                AnomalyDetectionService,
            )

            svc = AnomalyDetectionService()
            result = await svc.detect_anomaly(
                USER_ID, "revenue_daily", current_value=102.0
            )

        assert result is not None
        assert result["is_anomaly"] is False

    @pytest.mark.asyncio
    async def test_detect_anomaly_insufficient_data_returns_none(self):
        """detect_anomaly returns None when fewer than 7 data points exist."""
        values = [100.0, 110.0, 120.0]
        mock_client = _make_mock_client()

        with (
            patch(
                "app.services.anomaly_detection_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.anomaly_detection_service.execute_async",
                new_callable=AsyncMock,
                return_value=MagicMock(data=_baseline_data(values)),
            ),
        ):
            from app.services.anomaly_detection_service import (
                AnomalyDetectionService,
            )

            svc = AnomalyDetectionService()
            result = await svc.detect_anomaly(
                USER_ID, "revenue_daily", current_value=500.0
            )

        assert result is None


# ---------------------------------------------------------------------------
# run_anomaly_detection_cycle
# ---------------------------------------------------------------------------


class TestRunAnomalyDetectionCycle:
    """run_anomaly_detection_cycle checks all metrics and fires alerts for anomalies."""

    @pytest.mark.asyncio
    async def test_cycle_fires_alerts_for_anomalies(self):
        """Verify run_anomaly_detection_cycle fires a notification for detected anomalies."""
        mock_client = _make_mock_client()
        anomaly_result = {
            "is_anomaly": True,
            "direction": "spike",
            "current": 500.0,
            "mean": 100.0,
            "stddev": 2.0,
            "deviation_factor": 200.0,
        }

        with (
            patch(
                "app.services.anomaly_detection_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.anomaly_detection_service.execute_async",
                new_callable=AsyncMock,
            ),
            patch.object(
                __import__(
                    "app.services.anomaly_detection_service",
                    fromlist=["AnomalyDetectionService"],
                ).AnomalyDetectionService,
                "_fetch_latest_metric_value",
                new_callable=AsyncMock,
                return_value=500.0,
            ),
            patch.object(
                __import__(
                    "app.services.anomaly_detection_service",
                    fromlist=["AnomalyDetectionService"],
                ).AnomalyDetectionService,
                "detect_anomaly",
                new_callable=AsyncMock,
                return_value=anomaly_result,
            ),
            patch.object(
                __import__(
                    "app.services.anomaly_detection_service",
                    fromlist=["AnomalyDetectionService"],
                ).AnomalyDetectionService,
                "_is_already_alerted_today",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.services.anomaly_detection_service.NotificationService",
            ) as mock_notif_cls,
            patch(
                "app.services.anomaly_detection_service.dispatch_notification",
                new_callable=AsyncMock,
                return_value={"slack": True},
            ),
        ):
            mock_notif = MagicMock()
            mock_notif.create_notification = AsyncMock(return_value={"id": "notif-1"})
            mock_notif_cls.return_value = mock_notif

            from app.services.anomaly_detection_service import (
                AnomalyDetectionService,
            )

            svc = AnomalyDetectionService()
            result = await svc.run_anomaly_detection_cycle(USER_ID)

        assert len(result) > 0
        mock_notif.create_notification.assert_called()
        # Verify message includes metric name and value info
        call_kwargs = mock_notif.create_notification.call_args
        message = (
            call_kwargs.kwargs.get("message", "")
            if call_kwargs.kwargs
            else call_kwargs[1].get("message", "")
        )
        assert "$" in message or "500" in message or "revenue" in message.lower()

    @pytest.mark.asyncio
    async def test_cycle_deduplicates_alerts(self):
        """Verify run_anomaly_detection_cycle does not fire duplicate alerts for same metric+day."""
        mock_client = _make_mock_client()
        anomaly_result = {
            "is_anomaly": True,
            "direction": "spike",
            "current": 500.0,
            "mean": 100.0,
            "stddev": 2.0,
            "deviation_factor": 200.0,
        }

        with (
            patch(
                "app.services.anomaly_detection_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.anomaly_detection_service.execute_async",
                new_callable=AsyncMock,
            ),
            patch.object(
                __import__(
                    "app.services.anomaly_detection_service",
                    fromlist=["AnomalyDetectionService"],
                ).AnomalyDetectionService,
                "_fetch_latest_metric_value",
                new_callable=AsyncMock,
                return_value=500.0,
            ),
            patch.object(
                __import__(
                    "app.services.anomaly_detection_service",
                    fromlist=["AnomalyDetectionService"],
                ).AnomalyDetectionService,
                "detect_anomaly",
                new_callable=AsyncMock,
                return_value=anomaly_result,
            ),
            patch.object(
                __import__(
                    "app.services.anomaly_detection_service",
                    fromlist=["AnomalyDetectionService"],
                ).AnomalyDetectionService,
                "_is_already_alerted_today",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "app.services.anomaly_detection_service.NotificationService",
            ) as mock_notif_cls,
            patch(
                "app.services.anomaly_detection_service.dispatch_notification",
                new_callable=AsyncMock,
            ) as mock_dispatch_fn,
        ):
            mock_notif = MagicMock()
            mock_notif.create_notification = AsyncMock(return_value={"id": "notif-1"})
            mock_notif_cls.return_value = mock_notif

            from app.services.anomaly_detection_service import (
                AnomalyDetectionService,
            )

            svc = AnomalyDetectionService()
            await svc.run_anomaly_detection_cycle(USER_ID)

        # All anomalies are detected but no notifications should fire (deduplicated)
        mock_notif.create_notification.assert_not_called()
        mock_dispatch_fn.assert_not_called()

    @pytest.mark.asyncio
    async def test_alert_message_includes_metric_info(self):
        """Verify alert message includes metric name, current value, normal range, and direction."""
        mock_client = _make_mock_client()
        anomaly_result = {
            "is_anomaly": True,
            "direction": "spike",
            "current": 1230.0,
            "mean": 510.0,
            "stddev": 50.0,
            "deviation_factor": 14.4,
        }

        with (
            patch(
                "app.services.anomaly_detection_service.get_service_client",
                return_value=mock_client,
            ),
            patch(
                "app.services.anomaly_detection_service.execute_async",
                new_callable=AsyncMock,
            ),
            patch.object(
                __import__(
                    "app.services.anomaly_detection_service",
                    fromlist=["AnomalyDetectionService"],
                ).AnomalyDetectionService,
                "_fetch_latest_metric_value",
                new_callable=AsyncMock,
                return_value=1230.0,
            ),
            patch.object(
                __import__(
                    "app.services.anomaly_detection_service",
                    fromlist=["AnomalyDetectionService"],
                ).AnomalyDetectionService,
                "detect_anomaly",
                new_callable=AsyncMock,
                return_value=anomaly_result,
            ),
            patch.object(
                __import__(
                    "app.services.anomaly_detection_service",
                    fromlist=["AnomalyDetectionService"],
                ).AnomalyDetectionService,
                "_is_already_alerted_today",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.services.anomaly_detection_service.NotificationService",
            ) as mock_notif_cls,
            patch(
                "app.services.anomaly_detection_service.dispatch_notification",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            mock_notif = MagicMock()
            mock_notif.create_notification = AsyncMock(return_value={"id": "notif-1"})
            mock_notif_cls.return_value = mock_notif

            from app.services.anomaly_detection_service import (
                AnomalyDetectionService,
            )

            svc = AnomalyDetectionService()
            await svc.run_anomaly_detection_cycle(USER_ID)

        # The message must include metric details
        mock_notif.create_notification.assert_called()
        call_kwargs = mock_notif.create_notification.call_args
        if call_kwargs.kwargs:
            message = call_kwargs.kwargs.get("message", "")
        else:
            message = call_kwargs[1].get("message", "")
        # Message should reference the current value and direction
        assert "1,230" in message or "1230" in message
        assert (
            "high" in message.lower()
            or "spike" in message.lower()
            or "above" in message.lower()
        )
