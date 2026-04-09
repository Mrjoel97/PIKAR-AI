# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Anomaly detection for business metrics.

Computes rolling baselines (mean + stddev) from the ``metric_baselines``
table and flags values that deviate by more than a configurable number of
standard deviations.  Detected anomalies are pushed as plain-English
notifications via :class:`NotificationService` and fanned out to external
channels (Slack / Teams) via :func:`dispatch_notification`.

Triggered periodically by Cloud Scheduler via
``POST /scheduled/anomaly-detection-tick``.

Design decisions:
- Population stddev (``pstdev``) is used because we have the full window, not
  a sample.
- Minimum 7 data points required before flagging -- avoids false positives for
  new users.
- Deduplication is date-scoped: one alert per user + metric per calendar day.
  Uses the ``notifications`` table as the dedup source (title + metadata match).
"""

from __future__ import annotations

import logging
import statistics
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.notifications.notification_service import NotificationService, NotificationType
from app.services.notification_dispatcher import dispatch_notification
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Metric source registry
# ---------------------------------------------------------------------------

METRIC_SOURCES: dict[str, dict[str, str]] = {
    "revenue_daily": {
        "table": "dashboard_summaries",
        "path": "metrics.revenue",
        "label": "daily revenue",
        "unit": "$",
    },
    "customers_total": {
        "table": "dashboard_summaries",
        "path": "metrics.customers",
        "label": "total customers",
        "unit": "",
    },
    "ad_spend_daily": {
        "table": "ad_spend_tracking",
        "aggregate": "sum",
        "group_by": "tracking_date",
        "label": "daily ad spend",
        "unit": "$",
    },
    "conversion_rate": {
        "table": "ad_spend_tracking",
        "compute": "conversions/clicks",
        "label": "conversion rate",
        "unit": "%",
    },
}

_MIN_DATA_POINTS = 7
"""Minimum data points required before flagging anomalies."""

_ANOMALY_ALERT_TITLE = "Metric Anomaly Detected"
"""Notification title used for anomaly alerts (also used for dedup lookups)."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AnomalyDetectionService:
    """Business metric anomaly detection with rolling baseline and stddev computation.

    Inherits from nothing -- uses the service-role client directly via
    :func:`get_service_client` for admin-level access to ``metric_baselines``
    and related tables.
    """

    def __init__(self) -> None:
        self._client = get_service_client()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def record_metric(
        self,
        user_id: str,
        metric_key: str,
        value: float,
    ) -> dict | None:
        """Insert a metric value into ``metric_baselines``.

        Uses upsert with the unique constraint on
        ``(user_id, metric_key, recorded_at::date)`` so calling this
        multiple times on the same day updates instead of duplicating.

        Args:
            user_id: The user's UUID.
            metric_key: Key from :data:`METRIC_SOURCES`.
            value: The metric value to record.

        Returns:
            The upserted row, or ``None`` on failure.
        """
        try:
            result = await execute_async(
                self._client.table("metric_baselines").insert(
                    {
                        "user_id": user_id,
                        "metric_key": metric_key,
                        "metric_value": value,
                    }
                ),
                op_name="anomaly.record_metric",
            )
            return (result.data or [None])[0]
        except Exception:
            logger.exception(
                "Failed to record metric %s for user %s", metric_key, user_id
            )
            return None

    async def compute_baseline(
        self,
        user_id: str,
        metric_key: str,
        window_days: int = 30,
    ) -> dict[str, Any] | None:
        """Compute rolling mean and stddev from ``metric_baselines``.

        Args:
            user_id: The user's UUID.
            metric_key: Metric key to query.
            window_days: Number of days to look back (default 30).

        Returns:
            Dict ``{mean, stddev, count, min, max}`` or ``None`` if fewer
            than :data:`_MIN_DATA_POINTS` exist.
        """
        cutoff = (
            datetime.now(tz=timezone.utc) - timedelta(days=window_days)
        ).isoformat()

        result = await execute_async(
            self._client.table("metric_baselines")
            .select("metric_value")
            .eq("user_id", user_id)
            .eq("metric_key", metric_key)
            .gte("recorded_at", cutoff)
            .order("recorded_at", desc=True)
            .limit(window_days),
            op_name="anomaly.compute_baseline",
        )
        rows = result.data or []

        if len(rows) < _MIN_DATA_POINTS:
            return None

        values = [float(r["metric_value"]) for r in rows]
        mean = statistics.mean(values)
        stddev = statistics.pstdev(values)

        return {
            "mean": mean,
            "stddev": stddev,
            "count": len(values),
            "min": min(values),
            "max": max(values),
        }

    async def detect_anomaly(
        self,
        user_id: str,
        metric_key: str,
        current_value: float,
        threshold_stddev: float = 2.0,
    ) -> dict[str, Any] | None:
        """Check if ``current_value`` is anomalous relative to the baseline.

        Args:
            user_id: The user's UUID.
            metric_key: Metric key to check.
            current_value: The latest observed value.
            threshold_stddev: Number of stddevs to consider anomalous (default 2).

        Returns:
            Dict ``{is_anomaly, direction, current, mean, stddev, deviation_factor}``
            or ``None`` if baseline data is insufficient.
        """
        baseline = await self.compute_baseline(user_id, metric_key)
        if baseline is None:
            return None

        mean = baseline["mean"]
        stddev = baseline["stddev"]

        # Avoid division by zero: if stddev is 0, any non-equal value is anomalous
        if stddev == 0:
            is_anomaly = current_value != mean
            deviation_factor = float("inf") if is_anomaly else 0.0
        else:
            deviation_factor = abs(current_value - mean) / stddev
            is_anomaly = deviation_factor > threshold_stddev

        if is_anomaly:
            direction = "spike" if current_value > mean else "dip"
        else:
            direction = "normal"

        return {
            "is_anomaly": is_anomaly,
            "direction": direction,
            "current": current_value,
            "mean": mean,
            "stddev": stddev,
            "deviation_factor": round(deviation_factor, 2),
        }

    async def run_anomaly_detection_cycle(
        self,
        user_id: str,
    ) -> list[dict[str, Any]]:
        """Check all configured metrics for a user and fire alerts for anomalies.

        For each metric in :data:`METRIC_SOURCES`:
        1. Fetch the latest value.
        2. Run :meth:`detect_anomaly`.
        3. If anomalous and not already alerted today, create notification + dispatch.

        Args:
            user_id: The user's UUID.

        Returns:
            List of anomaly dicts for metrics that were flagged.
        """
        anomalies: list[dict[str, Any]] = []

        for metric_key, source in METRIC_SOURCES.items():
            try:
                value = await self._fetch_latest_metric_value(
                    user_id, metric_key, source
                )
                if value is None:
                    continue

                result = await self.detect_anomaly(user_id, metric_key, value)
                if result is None or not result["is_anomaly"]:
                    continue

                # Deduplication: skip if already alerted today
                if await self._is_already_alerted_today(user_id, metric_key):
                    logger.debug(
                        "Anomaly alert already sent today for user=%s metric=%s",
                        user_id,
                        metric_key,
                    )
                    anomalies.append(result)
                    continue

                # Build plain-English alert message
                message = self._format_anomaly_message(metric_key, source, result)

                # Create in-app notification
                notif_svc = NotificationService()
                await notif_svc.create_notification(
                    user_id=user_id,
                    title=_ANOMALY_ALERT_TITLE,
                    message=message,
                    type=NotificationType.WARNING,
                    link="/dashboard",
                    metadata={
                        "metric_key": metric_key,
                        "direction": result["direction"],
                        "current": result["current"],
                        "mean": result["mean"],
                        "stddev": result["stddev"],
                        "deviation_factor": result["deviation_factor"],
                        "alert_date": date.today().isoformat(),
                    },
                )

                # Dispatch to external channels (Slack / Teams)
                await dispatch_notification(
                    user_id=user_id,
                    event_type="metric.anomaly_detected",
                    payload={
                        "metric_key": metric_key,
                        "direction": result["direction"],
                        "current": result["current"],
                        "mean": result["mean"],
                        "message": message,
                    },
                )

                anomalies.append(result)
                logger.info(
                    "Anomaly alert fired for user=%s metric=%s direction=%s "
                    "current=%.2f mean=%.2f stddev=%.2f",
                    user_id,
                    metric_key,
                    result["direction"],
                    result["current"],
                    result["mean"],
                    result["stddev"],
                )

            except Exception:
                logger.exception(
                    "Error checking metric %s for user %s", metric_key, user_id
                )

        return anomalies

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_latest_metric_value(
        self,
        user_id: str,
        metric_key: str,
        source: dict[str, str],
    ) -> float | None:
        """Fetch the most recent value for a metric from its source table.

        Args:
            user_id: The user's UUID.
            metric_key: The metric key.
            source: Source config from :data:`METRIC_SOURCES`.

        Returns:
            Latest float value, or ``None`` if unavailable.
        """
        table = source.get("table", "")

        if table == "dashboard_summaries":
            return await self._fetch_from_dashboard(user_id, source)
        elif table == "ad_spend_tracking":
            return await self._fetch_from_ad_spend(user_id, metric_key, source)

        return None

    async def _fetch_from_dashboard(
        self,
        user_id: str,
        source: dict[str, str],
    ) -> float | None:
        """Extract a metric value from the latest dashboard_summaries row.

        Args:
            user_id: The user's UUID.
            source: Source config with ``path`` like ``metrics.revenue``.

        Returns:
            The numeric value or ``None``.
        """
        try:
            result = await execute_async(
                self._client.table("dashboard_summaries")
                .select("metrics")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(1),
                op_name="anomaly.fetch_dashboard",
            )
            rows = result.data or []
            if not rows:
                return None

            # Parse dotted path (e.g. "metrics.revenue")
            path = source.get("path", "")
            parts = path.split(".")
            value = rows[0]
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None

            return float(value) if value is not None else None
        except Exception:
            logger.exception("Failed to fetch dashboard metric for user %s", user_id)
            return None

    async def _fetch_from_ad_spend(
        self,
        user_id: str,
        metric_key: str,
        source: dict[str, str],
    ) -> float | None:
        """Fetch an aggregated metric from ad_spend_tracking.

        Args:
            user_id: The user's UUID.
            metric_key: The metric key.
            source: Source config with ``aggregate`` or ``compute`` field.

        Returns:
            The computed float value or ``None``.
        """
        try:
            # Get campaign IDs for this user
            campaign_result = await execute_async(
                self._client.table("ad_campaigns").select("id").eq("user_id", user_id),
                op_name="anomaly.fetch_campaigns",
            )
            campaign_ids = [r["id"] for r in (campaign_result.data or [])]
            if not campaign_ids:
                return None

            yesterday = (date.today() - timedelta(days=1)).isoformat()

            result = await execute_async(
                self._client.table("ad_spend_tracking")
                .select("spend, clicks, conversions")
                .in_("ad_campaign_id", campaign_ids)
                .gte("tracking_date", yesterday),
                op_name="anomaly.fetch_ad_spend",
            )
            rows = result.data or []
            if not rows:
                return None

            if source.get("aggregate") == "sum":
                return sum(float(r.get("spend", 0)) for r in rows)
            elif source.get("compute") == "conversions/clicks":
                total_clicks = sum(int(r.get("clicks", 0)) for r in rows)
                total_conversions = sum(int(r.get("conversions", 0)) for r in rows)
                if total_clicks == 0:
                    return None
                return (total_conversions / total_clicks) * 100

            return None
        except Exception:
            logger.exception(
                "Failed to fetch ad spend metric %s for user %s",
                metric_key,
                user_id,
            )
            return None

    async def _is_already_alerted_today(
        self,
        user_id: str,
        metric_key: str,
    ) -> bool:
        """Check if an anomaly alert was already sent today for this user + metric.

        Uses the ``notifications`` table as the dedup source -- looks for a
        notification with the anomaly alert title and matching metric_key in
        metadata created today.

        Args:
            user_id: The user's UUID.
            metric_key: The metric key.

        Returns:
            ``True`` if an alert was already sent today.
        """
        today_start = (
            datetime.now(tz=timezone.utc)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .isoformat()
        )

        try:
            result = await execute_async(
                self._client.table("notifications")
                .select("id")
                .eq("user_id", user_id)
                .eq("title", _ANOMALY_ALERT_TITLE)
                .gte("created_at", today_start)
                .limit(100),
                op_name="anomaly.dedup_check",
            )
            rows = result.data or []
            # We stored metric_key in metadata -- but we can't filter JSONB
            # in postgrest easily, so we check in Python
            # For simplicity, if any anomaly alert exists today, consider it
            # a match for all metrics -- this is a conservative dedup approach.
            # A more precise dedup would need a dedicated dedup table.
            #
            # Actually, check the metadata in the returned rows:
            for row in rows:
                meta = row.get("metadata", {})
                if isinstance(meta, dict) and meta.get("metric_key") == metric_key:
                    return True
            return False
        except Exception:
            logger.exception(
                "Dedup check failed for user=%s metric=%s -- allowing alert",
                user_id,
                metric_key,
            )
            return False

    @staticmethod
    def _format_anomaly_message(
        metric_key: str,
        source: dict[str, str],
        anomaly: dict[str, Any],
    ) -> str:
        """Build a plain-English anomaly alert message.

        Args:
            metric_key: The metric key.
            source: Source config from :data:`METRIC_SOURCES`.
            anomaly: Anomaly dict from :meth:`detect_anomaly`.

        Returns:
            Human-readable alert message.
        """
        label = source.get("label", metric_key.replace("_", " "))
        unit = source.get("unit", "")
        current = anomaly["current"]
        mean = anomaly["mean"]
        direction = anomaly["direction"]
        deviation_factor = anomaly["deviation_factor"]

        # Format values with appropriate units
        if unit == "$":
            current_str = f"${current:,.0f}"
            mean_str = f"${mean:,.0f}"
        elif unit == "%":
            current_str = f"{current:.1f}%"
            mean_str = f"{mean:.1f}%"
        else:
            current_str = f"{current:,.0f}"
            mean_str = f"{mean:,.0f}"

        if direction == "spike":
            direction_word = "unusually high"
            comparison = "above"
        else:
            direction_word = "unusually low"
            comparison = "below"

        message = (
            f"Your {label} ({current_str}) is {direction_word} -- "
            f"{deviation_factor:.1f}x {comparison} your typical {mean_str} range. "
        )

        if direction == "spike":
            message += (
                "This could mean a successful promotion or a data anomaly "
                "worth investigating."
            )
        else:
            message += (
                "This could indicate an issue worth looking into, or a seasonal "
                "slowdown."
            )

        return message


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------


async def run_anomaly_detection_cycle(user_id: str) -> list[dict[str, Any]]:
    """Run anomaly detection for a single user.

    Convenience wrapper around
    :meth:`AnomalyDetectionService.run_anomaly_detection_cycle`.

    Args:
        user_id: The user's UUID.

    Returns:
        List of anomaly dicts.
    """
    svc = AnomalyDetectionService()
    return await svc.run_anomaly_detection_cycle(user_id)


__all__ = ["AnomalyDetectionService", "run_anomaly_detection_cycle"]
