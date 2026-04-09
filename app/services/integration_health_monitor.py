# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Integration Health Monitor -- proactive token expiry and connectivity checks.

Detects OAuth tokens expiring within a configurable threshold (default 3 days)
and checks connectivity to key integration providers.  Dispatches alerts via
``ProactiveAlertService`` for expiring tokens (WARNING) and unhealthy
connections (ERROR).

Usage::

    from app.services.integration_health_monitor import run_integration_health_check

    result = await run_integration_health_check()
    # => {"tokens_checked": 5, "tokens_expiring": 1, ...}

Triggered by Cloud Scheduler via ``POST /scheduled/integration-health-tick``.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from app.notifications.notification_service import NotificationType
from app.services.proactive_alert_service import dispatch_proactive_alert
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider display names and health-check URLs
# ---------------------------------------------------------------------------

PROVIDER_DISPLAY_NAMES: dict[str, str] = {
    "google": "Google Workspace",
    "google_ads": "Google Ads",
    "meta_ads": "Meta Ads",
    "slack": "Slack",
    "stripe": "Stripe",
    "hubspot": "HubSpot",
    "shopify": "Shopify",
}

# MVP: only providers with simple, unauthenticated or token-bearer health endpoints.
# Key = provider name, Value = (url, method) for lightweight health check.
CONNECTIVITY_CHECK_PROVIDERS: dict[str, str] = {
    "google": "https://www.googleapis.com/oauth2/v1/userinfo",
    "slack": "https://slack.com/api/auth.test",
    "stripe": "https://api.stripe.com/v1/balance",
}

# Mapping of providers to features they affect (for user-facing messages).
PROVIDER_FEATURES: dict[str, str] = {
    "google": "email sync, calendar, and Google Docs",
    "google_ads": "ad campaign management and reporting",
    "meta_ads": "Meta advertising management",
    "slack": "Slack notifications and daily briefings",
    "stripe": "billing, payments, and revenue tracking",
    "hubspot": "CRM contacts and deal tracking",
    "shopify": "e-commerce order and product sync",
}


class IntegrationHealthMonitor:
    """Proactive integration health checker.

    Queries ``integration_credentials`` for expiring tokens and checks
    connectivity for key providers.  Dispatches alerts via the proactive
    alert service with per-user+provider+date deduplication.
    """

    def __init__(self) -> None:
        """Initialize with a service-role Supabase client."""
        self._client = get_service_client()

    # ------------------------------------------------------------------
    # Token expiry check
    # ------------------------------------------------------------------

    async def check_token_expiry(self, days_threshold: int = 3) -> list[dict[str, Any]]:
        """Find tokens expiring within ``days_threshold`` days.

        Queries ``integration_credentials`` for rows where ``expires_at``
        is NOT NULL, is in the future, and falls within the threshold.

        Args:
            days_threshold: Number of days to look ahead (default 3).

        Returns:
            List of dicts with ``user_id``, ``provider``, ``account_name``,
            ``expires_at``, and ``days_remaining``.
        """
        now = datetime.now(tz=timezone.utc)

        # Use RPC or raw filter:
        # expires_at IS NOT NULL AND expires_at > now() AND expires_at < now() + interval
        result = await execute_async(
            self._client.table("integration_credentials")
            .select("user_id, provider, account_name, expires_at")
            .gt("expires_at", now.isoformat())
            .lt(
                "expires_at",
                (now + timedelta(days=days_threshold)).isoformat(),
            ),
            op_name="integration_health.check_expiry",
        )

        expiring: list[dict[str, Any]] = []
        for row in result.data or []:
            expires_at_str = row.get("expires_at", "")
            try:
                expires_at = datetime.fromisoformat(
                    expires_at_str.replace("Z", "+00:00")
                )
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                days_remaining = max(0, (expires_at - now).days)
            except (ValueError, TypeError):
                days_remaining = 0

            expiring.append(
                {
                    "user_id": row["user_id"],
                    "provider": row["provider"],
                    "account_name": row.get("account_name", ""),
                    "expires_at": expires_at_str,
                    "days_remaining": days_remaining,
                }
            )

        return expiring

    # ------------------------------------------------------------------
    # Connectivity check
    # ------------------------------------------------------------------

    async def check_connectivity(self) -> list[dict[str, Any]]:
        """Check connectivity for key integration providers.

        For each provider in ``CONNECTIVITY_CHECK_PROVIDERS``, queries active
        users and performs a lightweight API call.  Only unhealthy results
        are returned.

        Returns:
            List of unhealthy results: ``{user_id, provider, status, error}``.
        """
        unhealthy: list[dict[str, Any]] = []

        for provider, health_url in CONNECTIVITY_CHECK_PROVIDERS.items():
            # Get all users with credentials for this provider
            cred_result = await execute_async(
                self._client.table("integration_credentials")
                .select("user_id, provider, access_token, account_name")
                .eq("provider", provider),
                op_name=f"integration_health.creds_{provider}",
            )

            for cred in cred_result.data or []:
                user_id = cred["user_id"]
                token = cred.get("access_token", "")

                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.get(
                            health_url,
                            headers={"Authorization": f"Bearer {token}"},
                        )
                        response.raise_for_status()
                    # Healthy -- skip
                except Exception as exc:
                    unhealthy.append(
                        {
                            "user_id": user_id,
                            "provider": provider,
                            "account_name": cred.get("account_name", ""),
                            "status": "unhealthy",
                            "error": str(exc)[:200],
                        }
                    )

        return unhealthy

    # ------------------------------------------------------------------
    # Main orchestrator
    # ------------------------------------------------------------------

    async def run_integration_health_check(self) -> dict[str, Any]:
        """Run all integration health checks and dispatch alerts.

        1. Check token expiry -- dispatch WARNING for each expiring token.
        2. Check connectivity -- dispatch ERROR for each unhealthy provider.

        Returns:
            Summary dict with counts.
        """
        today_str = date.today().isoformat()
        alerts_sent = 0

        # --- Token expiry ---
        expiring_tokens = await self.check_token_expiry()

        for token_info in expiring_tokens:
            provider = token_info["provider"]
            display_name = PROVIDER_DISPLAY_NAMES.get(provider, provider.title())
            days_remaining = token_info["days_remaining"]
            day_word = "day" if days_remaining == 1 else "days"

            message = (
                f"Your {display_name} connection will expire in "
                f"{days_remaining} {day_word}. "
                f"Please reconnect to avoid service disruption."
            )

            try:
                result = await dispatch_proactive_alert(
                    user_id=token_info["user_id"],
                    alert_type="integration.token_expiring",
                    alert_key=f"{provider}:{today_str}",
                    title="Integration Expiring",
                    message=message,
                    notification_type=NotificationType.WARNING,
                    link="/settings/integrations",
                    metadata={
                        "provider": provider,
                        "days_remaining": days_remaining,
                        "expires_at": token_info["expires_at"],
                    },
                )
                if result.get("dispatched"):
                    alerts_sent += 1
            except Exception:
                logger.exception(
                    "Failed to dispatch token expiry alert for user=%s provider=%s",
                    token_info["user_id"],
                    provider,
                )

        # --- Connectivity ---
        unhealthy_results = await self.check_connectivity()

        for unhealthy in unhealthy_results:
            provider = unhealthy["provider"]
            display_name = PROVIDER_DISPLAY_NAMES.get(provider, provider.title())
            affected = PROVIDER_FEATURES.get(provider, "connected services")

            message = (
                f"Your {display_name} connection is not responding. "
                f"This may affect {affected}. "
                f"Try reconnecting from Settings."
            )

            try:
                result = await dispatch_proactive_alert(
                    user_id=unhealthy["user_id"],
                    alert_type="integration.unhealthy",
                    alert_key=f"{provider}:{today_str}",
                    title="Integration Issue",
                    message=message,
                    notification_type=NotificationType.ERROR,
                    link="/settings/integrations",
                    metadata={
                        "provider": provider,
                        "error": unhealthy["error"],
                    },
                )
                if result.get("dispatched"):
                    alerts_sent += 1
            except Exception:
                logger.exception(
                    "Failed to dispatch connectivity alert for user=%s provider=%s",
                    unhealthy["user_id"],
                    provider,
                )

        return {
            "tokens_checked": len(expiring_tokens),
            "tokens_expiring": len(expiring_tokens),
            "connectivity_checked": len(unhealthy_results),
            "unhealthy": len(unhealthy_results),
            "alerts_sent": alerts_sent,
        }


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------


async def run_integration_health_check() -> dict[str, Any]:
    """Instantiate IntegrationHealthMonitor and run the health check.

    This is the entry point called by the ``/scheduled/integration-health-tick``
    endpoint.

    Returns:
        Summary dict with counts.
    """
    monitor = IntegrationHealthMonitor()
    return await monitor.run_integration_health_check()
