# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""GoogleAdsService — Google Ads REST API client.

Provides campaign CRUD and performance reporting via the Google Ads REST API
(v17).  All HTTP calls use ``httpx.AsyncClient`` with a 30-second timeout.

Authentication is delegated to ``IntegrationManager.get_valid_token``, which
handles token refresh transparently.  The Google Ads developer token and
optional login-customer-id are read from environment variables at call time
so the service never caches credentials in memory.

Usage::

    service = GoogleAdsService(user_token=jwt)
    campaigns = await service.list_campaigns(user_id, customer_id)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from app.services.base_service import BaseService
from app.services.integration_manager import IntegrationManager

logger = logging.getLogger(__name__)

_GAQL_BASE_URL = "https://googleads.googleapis.com/v17"

# Status mapping: Google Ads enum -> internal status string
_STATUS_FROM_GOOGLE: dict[str, str] = {
    "ENABLED": "active",
    "PAUSED": "paused",
    "REMOVED": "removed",
}

# Status mapping: internal string -> Google Ads enum
_STATUS_TO_GOOGLE: dict[str, str] = {
    "active": "ENABLED",
    "paused": "PAUSED",
}


class GoogleAdsService(BaseService):
    """Google Ads REST API client with campaign CRUD and performance reporting.

    All budget-modifying operations must be validated by ``AdBudgetCapService``
    before calling methods on this service.  New campaigns are always created
    in PAUSED status — activation requires a separate approval gate.

    Args:
        user_token: User JWT for Supabase RLS (passed to BaseService).
    """

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    async def _get_headers(self, user_id: str) -> dict[str, str]:
        """Build authenticated request headers for the Google Ads REST API.

        Retrieves the OAuth access token via ``IntegrationManager`` and
        combines it with the developer token and optional MCC login customer
        ID from environment variables.

        Args:
            user_id: The user's UUID.

        Returns:
            Dict of HTTP headers ready for use with ``httpx``.

        Raises:
            ValueError: If the user has not connected Google Ads.
        """
        manager = IntegrationManager(self._user_token)
        token = await manager.get_valid_token(user_id, "google_ads")
        if not token:
            raise ValueError(
                f"User {user_id} has not connected Google Ads. "
                "Complete OAuth flow at /integrations/google_ads/connect."
            )

        developer_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "")
        headers: dict[str, str] = {
            "Authorization": f"Bearer {token}",
            "developer-token": developer_token,
            "Content-Type": "application/json",
        }

        login_customer_id = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")
        if login_customer_id:
            headers["login-customer-id"] = login_customer_id

        return headers

    # -------------------------------------------------------------------------
    # Account discovery
    # -------------------------------------------------------------------------

    async def get_accessible_customers(self, user_id: str) -> list[str]:
        """List Google Ads customer resource names accessible to this account.

        Used during initial setup so the user can select their ad account.
        Each entry is a resource name like ``"customers/1234567890"``.

        Args:
            user_id: The user's UUID.

        Returns:
            List of customer resource name strings.
        """
        import httpx  # noqa: PLC0415 — lazy import

        headers = await self._get_headers(user_id)
        url = f"{_GAQL_BASE_URL}/customers:listAccessibleCustomers"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data.get("resourceNames", [])
        except Exception:
            logger.exception(
                "GoogleAdsService.get_accessible_customers failed for user=%s",
                user_id,
            )
            return []

    # -------------------------------------------------------------------------
    # Campaign listing
    # -------------------------------------------------------------------------

    async def list_campaigns(
        self, user_id: str, customer_id: str
    ) -> list[dict[str, Any]]:
        """List active and paused campaigns for a Google Ads customer.

        Queries the GAQL searchStream endpoint for all non-REMOVED campaigns,
        returning normalised dicts with a consistent internal shape.

        Args:
            user_id: The user's UUID.
            customer_id: Google Ads customer ID (digits only, no dashes).

        Returns:
            List of campaign dicts with keys: id, name, status, type,
            budget (USD), start_date, end_date.
        """
        import httpx  # noqa: PLC0415

        headers = await self._get_headers(user_id)
        url = f"{_GAQL_BASE_URL}/customers/{customer_id}/googleAds:searchStream"
        gaql = (
            "SELECT campaign.id, campaign.name, campaign.status, "
            "campaign.advertising_channel_type, campaign_budget.amount_micros, "
            "campaign.start_date, campaign.end_date "
            "FROM campaign "
            "WHERE campaign.status != 'REMOVED' "
            "ORDER BY campaign.id"
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url, headers=headers, json={"query": gaql}
                )
                resp.raise_for_status()
                batches = resp.json()

            campaigns: list[dict[str, Any]] = []
            # searchStream returns a list of batch response objects
            if isinstance(batches, list):
                for batch in batches:
                    for row in batch.get("results", []):
                        campaign = row.get("campaign", {})
                        budget = row.get("campaignBudget", {})
                        micros = budget.get("amountMicros", 0)
                        google_status = campaign.get("status", "PAUSED")
                        campaigns.append({
                            "id": campaign.get("id"),
                            "name": campaign.get("name"),
                            "status": _STATUS_FROM_GOOGLE.get(
                                google_status, google_status.lower()
                            ),
                            "type": campaign.get("advertisingChannelType"),
                            "budget": int(micros) / 1_000_000,
                            "start_date": campaign.get("startDate"),
                            "end_date": campaign.get("endDate"),
                            "resource_name": campaign.get("resourceName"),
                        })
            return campaigns
        except Exception:
            logger.exception(
                "GoogleAdsService.list_campaigns failed for user=%s customer=%s",
                user_id,
                customer_id,
            )
            return []

    # -------------------------------------------------------------------------
    # Campaign creation
    # -------------------------------------------------------------------------

    async def create_campaign(
        self,
        user_id: str,
        customer_id: str,
        name: str,
        budget_amount: float,
        campaign_type: str = "SEARCH",
        status: str = "PAUSED",  # noqa: ARG002 — always PAUSED for safety
    ) -> dict[str, Any]:
        """Create a new Google Ads campaign with a dedicated budget.

        Campaigns are ALWAYS created in PAUSED status regardless of the
        ``status`` parameter — activation requires a separate approval gate.

        Steps:
        1. Create a campaign budget resource.
        2. Create a campaign linked to that budget.

        Args:
            user_id: The user's UUID.
            customer_id: Google Ads customer ID.
            name: Human-readable campaign name.
            budget_amount: Daily budget in USD (converted to micros internally).
            campaign_type: ``advertising_channel_type`` (e.g. ``"SEARCH"``).
            status: Ignored — always PAUSED for safety.

        Returns:
            Dict with keys: campaign_resource_name, budget_resource_name,
            campaign_id (numeric string), budget_amount.
            On failure: {"error": "<message>"}.
        """
        import httpx  # noqa: PLC0415

        headers = await self._get_headers(user_id)
        amount_micros = int(budget_amount * 1_000_000)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: create campaign budget
                budget_url = (
                    f"{_GAQL_BASE_URL}/customers/{customer_id}/campaignBudgets:mutate"
                )
                budget_resp = await client.post(
                    budget_url,
                    headers=headers,
                    json={
                        "operations": [
                            {
                                "create": {
                                    "amountMicros": amount_micros,
                                    "deliveryMethod": "STANDARD",
                                }
                            }
                        ]
                    },
                )
                budget_resp.raise_for_status()
                budget_data = budget_resp.json()
                budget_resource = (
                    budget_data.get("results", [{}])[0].get("resourceName", "")
                )

                # Step 2: create campaign (always PAUSED)
                campaign_url = (
                    f"{_GAQL_BASE_URL}/customers/{customer_id}/campaigns:mutate"
                )
                campaign_resp = await client.post(
                    campaign_url,
                    headers=headers,
                    json={
                        "operations": [
                            {
                                "create": {
                                    "name": name,
                                    "campaignBudget": budget_resource,
                                    "advertisingChannelType": campaign_type,
                                    "status": "PAUSED",
                                }
                            }
                        ]
                    },
                )
                campaign_resp.raise_for_status()
                campaign_data = campaign_resp.json()
                campaign_resource = (
                    campaign_data.get("results", [{}])[0].get("resourceName", "")
                )
                # Extract numeric campaign ID from resource name
                # e.g. "customers/123/campaigns/456" -> "456"
                campaign_id = (
                    campaign_resource.split("/")[-1] if campaign_resource else ""
                )

                return {
                    "campaign_resource_name": campaign_resource,
                    "budget_resource_name": budget_resource,
                    "campaign_id": campaign_id,
                    "budget_amount": budget_amount,
                    "status": "paused",
                }
        except Exception:
            logger.exception(
                "GoogleAdsService.create_campaign failed user=%s customer=%s name=%s",
                user_id,
                customer_id,
                name,
            )
            return {"error": "Failed to create campaign. Check logs for details."}

    # -------------------------------------------------------------------------
    # Status and budget updates
    # -------------------------------------------------------------------------

    async def update_campaign_status(
        self,
        user_id: str,
        customer_id: str,
        campaign_id: str,
        status: str,
    ) -> dict[str, Any]:
        """Update a campaign's serving status (active <-> paused).

        Args:
            user_id: The user's UUID.
            customer_id: Google Ads customer ID.
            campaign_id: Numeric campaign ID string.
            status: Internal status string — ``"active"`` or ``"paused"``.

        Returns:
            Dict with resource_name and new status, or {"error": ...}.
        """
        import httpx  # noqa: PLC0415

        google_status = _STATUS_TO_GOOGLE.get(status, "PAUSED")
        resource_name = f"customers/{customer_id}/campaigns/{campaign_id}"
        headers = await self._get_headers(user_id)
        url = f"{_GAQL_BASE_URL}/customers/{customer_id}/campaigns:mutate"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    headers=headers,
                    json={
                        "operations": [
                            {
                                "update": {
                                    "resourceName": resource_name,
                                    "status": google_status,
                                },
                                "updateMask": "status",
                            }
                        ]
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                updated_resource = (
                    data.get("results", [{}])[0].get("resourceName", resource_name)
                )
                return {"resource_name": updated_resource, "status": status}
        except Exception:
            logger.exception(
                "GoogleAdsService.update_campaign_status failed user=%s campaign=%s",
                user_id,
                campaign_id,
            )
            return {"error": "Failed to update campaign status."}

    async def update_campaign_budget(
        self,
        user_id: str,
        customer_id: str,
        campaign_budget_id: str,
        new_amount: float,
    ) -> dict[str, Any]:
        """Update a campaign budget's daily amount.

        Args:
            user_id: The user's UUID.
            customer_id: Google Ads customer ID.
            campaign_budget_id: Numeric campaign budget ID string.
            new_amount: New daily budget amount in USD.

        Returns:
            Dict with resource_name and new budget_amount, or {"error": ...}.
        """
        import httpx  # noqa: PLC0415

        resource_name = (
            f"customers/{customer_id}/campaignBudgets/{campaign_budget_id}"
        )
        amount_micros = int(new_amount * 1_000_000)
        headers = await self._get_headers(user_id)
        url = f"{_GAQL_BASE_URL}/customers/{customer_id}/campaignBudgets:mutate"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    headers=headers,
                    json={
                        "operations": [
                            {
                                "update": {
                                    "resourceName": resource_name,
                                    "amountMicros": amount_micros,
                                },
                                "updateMask": "amountMicros",
                            }
                        ]
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                updated_resource = (
                    data.get("results", [{}])[0].get("resourceName", resource_name)
                )
                return {
                    "resource_name": updated_resource,
                    "budget_amount": new_amount,
                }
        except Exception:
            logger.exception(
                "GoogleAdsService.update_campaign_budget failed for user=%s budget=%s",
                user_id,
                campaign_budget_id,
            )
            return {"error": "Failed to update campaign budget."}

    # -------------------------------------------------------------------------
    # Performance reporting
    # -------------------------------------------------------------------------

    async def get_campaign_performance(
        self,
        user_id: str,
        customer_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """Pull daily campaign performance metrics for a date range.

        Args:
            user_id: The user's UUID.
            customer_id: Google Ads customer ID.
            start_date: ISO date string, e.g. ``"2026-01-01"``.
            end_date: ISO date string, e.g. ``"2026-01-31"``.

        Returns:
            List of dicts with keys: campaign_id, campaign_name, date,
            impressions, clicks, conversions, cost (USD), conversion_value.
        """
        import httpx  # noqa: PLC0415

        headers = await self._get_headers(user_id)
        url = f"{_GAQL_BASE_URL}/customers/{customer_id}/googleAds:searchStream"
        gaql = (
            "SELECT campaign.id, campaign.name, metrics.impressions, "
            "metrics.clicks, metrics.conversions, metrics.cost_micros, "
            "metrics.conversions_value, segments.date "
            "FROM campaign "
            f"WHERE segments.date BETWEEN '{start_date}' AND '{end_date}' "
            "AND campaign.status != 'REMOVED'"
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url, headers=headers, json={"query": gaql}
                )
                resp.raise_for_status()
                batches = resp.json()

            rows: list[dict[str, Any]] = []
            if isinstance(batches, list):
                for batch in batches:
                    for row in batch.get("results", []):
                        campaign = row.get("campaign", {})
                        metrics = row.get("metrics", {})
                        segment = row.get("segments", {})
                        cost_micros = int(metrics.get("costMicros", 0))
                        rows.append({
                            "campaign_id": campaign.get("id"),
                            "campaign_name": campaign.get("name"),
                            "date": segment.get("date"),
                            "impressions": int(metrics.get("impressions", 0)),
                            "clicks": int(metrics.get("clicks", 0)),
                            "conversions": float(metrics.get("conversions", 0)),
                            "cost": cost_micros / 1_000_000,
                            "conversion_value": float(
                                metrics.get("conversionsValue", 0)
                            ),
                        })
            return rows
        except Exception:
            logger.exception(
                "GoogleAdsService.get_campaign_performance failed user=%s customer=%s",
                user_id,
                customer_id,
            )
            return []


__all__ = ["GoogleAdsService"]
