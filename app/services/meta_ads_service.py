# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""MetaAdsService — Meta Marketing API client.

Provides campaign CRUD and insights reporting via the Meta Graph API (v19.0).
All HTTP calls use ``httpx.AsyncClient`` with a 30-second timeout.

Meta budget values are expressed in **cents** on the wire:
- On write: multiply USD value by 100 before sending.
- On read: divide raw value by 100 to get USD.

Authentication is delegated to ``IntegrationManager.get_valid_token``.
All new campaigns are created in PAUSED status — activation requires a
separate approval gate.

Usage::

    service = MetaAdsService(user_token=jwt)
    accounts = await service.get_ad_accounts(user_id)
    campaigns = await service.list_campaigns(user_id, ad_account_id)
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.base_service import BaseService
from app.services.integration_manager import IntegrationManager

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.facebook.com/v19.0"

# Status mapping: Meta API status -> internal status string
_STATUS_FROM_META: dict[str, str] = {
    "ACTIVE": "active",
    "PAUSED": "paused",
    "DELETED": "deleted",
    "ARCHIVED": "archived",
}

# Status mapping: internal status string -> Meta API status
_STATUS_TO_META: dict[str, str] = {
    "active": "ACTIVE",
    "paused": "PAUSED",
}


class MetaAdsService(BaseService):
    """Meta Marketing API client with campaign CRUD and insights reporting.

    All budget-modifying operations must be validated by ``AdBudgetCapService``
    before calling methods on this service.  New campaigns are always created
    in PAUSED status — activation requires a separate approval gate.

    Meta budgets are always in cents (USD × 100) on the API surface.  This
    service accepts and returns USD values, converting internally.

    Args:
        user_token: User JWT for Supabase RLS (passed to BaseService).
    """

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    async def _get_token(self, user_id: str) -> str:
        """Retrieve the valid Meta OAuth access token for a user.

        Args:
            user_id: The user's UUID.

        Returns:
            Decrypted access token string.

        Raises:
            ValueError: If the user has not connected Meta Ads.
        """
        manager = IntegrationManager(self._user_token)
        token = await manager.get_valid_token(user_id, "meta_ads")
        if not token:
            raise ValueError(
                f"User {user_id} has not connected Meta Ads. "
                "Complete OAuth flow at /integrations/meta_ads/connect."
            )
        return token

    # -------------------------------------------------------------------------
    # Account discovery
    # -------------------------------------------------------------------------

    async def get_ad_accounts(self, user_id: str) -> list[dict[str, Any]]:
        """List Meta ad accounts accessible to the connected user.

        Args:
            user_id: The user's UUID.

        Returns:
            List of ad account dicts with keys: id, name, account_status,
            currency, balance (USD).
        """
        import httpx  # noqa: PLC0415

        token = await self._get_token(user_id)
        url = (
            f"{_GRAPH_BASE}/me/adaccounts"
            "?fields=id,name,account_status,currency,balance"
            f"&access_token={token}"
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                accounts = data.get("data", [])
                # Normalise balance from cents to USD
                for acct in accounts:
                    raw_balance = acct.get("balance", 0)
                    try:
                        acct["balance"] = int(raw_balance) / 100
                    except (TypeError, ValueError):
                        acct["balance"] = 0.0
                return accounts
        except Exception:
            logger.exception(
                "MetaAdsService.get_ad_accounts failed for user=%s", user_id
            )
            return []

    # -------------------------------------------------------------------------
    # Campaign listing
    # -------------------------------------------------------------------------

    async def list_campaigns(
        self, user_id: str, ad_account_id: str
    ) -> list[dict[str, Any]]:
        """List campaigns for a Meta ad account.

        Args:
            user_id: The user's UUID.
            ad_account_id: Meta ad account ID (digits only, without ``act_`` prefix).

        Returns:
            List of campaign dicts with keys: id, name, status, objective,
            daily_budget (USD), lifetime_budget (USD), start_time, stop_time.
        """
        import httpx  # noqa: PLC0415

        token = await self._get_token(user_id)
        fields = (
            "id,name,status,objective,"
            "daily_budget,lifetime_budget,start_time,stop_time"
        )
        url = (
            f"{_GRAPH_BASE}/act_{ad_account_id}/campaigns"
            f"?fields={fields}&access_token={token}"
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                campaigns = data.get("data", [])

            result: list[dict[str, Any]] = []
            for c in campaigns:
                meta_status = c.get("status", "PAUSED")
                daily_raw = c.get("daily_budget")
                lifetime_raw = c.get("lifetime_budget")
                result.append({
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "status": _STATUS_FROM_META.get(
                        meta_status, meta_status.lower()
                    ),
                    "objective": c.get("objective"),
                    "daily_budget": (
                        int(daily_raw) / 100 if daily_raw else None
                    ),
                    "lifetime_budget": (
                        int(lifetime_raw) / 100 if lifetime_raw else None
                    ),
                    "start_time": c.get("start_time"),
                    "stop_time": c.get("stop_time"),
                })
            return result
        except Exception:
            logger.exception(
                "MetaAdsService.list_campaigns failed for user=%s account=%s",
                user_id,
                ad_account_id,
            )
            return []

    # -------------------------------------------------------------------------
    # Campaign creation
    # -------------------------------------------------------------------------

    async def create_campaign(
        self,
        user_id: str,
        ad_account_id: str,
        name: str,
        objective: str = "OUTCOME_TRAFFIC",
        daily_budget: int | None = None,
        lifetime_budget: int | None = None,
        status: str = "PAUSED",  # noqa: ARG002 — always PAUSED for safety
    ) -> dict[str, Any]:
        """Create a new Meta Ads campaign.

        Campaigns are ALWAYS created in PAUSED status regardless of the
        ``status`` parameter — activation requires a separate approval gate.

        Budget values are in **cents** (multiply USD by 100 before passing).
        Exactly one of ``daily_budget`` or ``lifetime_budget`` should be set.

        Args:
            user_id: The user's UUID.
            ad_account_id: Meta ad account ID (digits only).
            name: Campaign name.
            objective: Campaign objective (e.g. ``"OUTCOME_TRAFFIC"``).
            daily_budget: Daily budget in cents (USD × 100).
            lifetime_budget: Lifetime budget in cents (USD × 100).
            status: Ignored — always PAUSED for safety.

        Returns:
            Dict with keys: id, name, status, and budget info.
            On failure: {"error": "<message>"}.
        """
        import httpx  # noqa: PLC0415

        token = await self._get_token(user_id)
        url = f"{_GRAPH_BASE}/act_{ad_account_id}/campaigns"

        payload: dict[str, Any] = {
            "name": name,
            "objective": objective,
            "special_ad_categories": [],
            "status": "PAUSED",
            "access_token": token,
        }
        if daily_budget is not None:
            payload["daily_budget"] = daily_budget
        if lifetime_budget is not None:
            payload["lifetime_budget"] = lifetime_budget

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return {
                    "id": data.get("id"),
                    "name": name,
                    "status": "paused",
                    "objective": objective,
                    "daily_budget_cents": daily_budget,
                    "lifetime_budget_cents": lifetime_budget,
                }
        except Exception:
            logger.exception(
                "MetaAdsService.create_campaign failed for user=%s account=%s name=%s",
                user_id,
                ad_account_id,
                name,
            )
            return {"error": "Failed to create Meta campaign. Check logs for details."}

    # -------------------------------------------------------------------------
    # Status and budget updates
    # -------------------------------------------------------------------------

    async def update_campaign_status(
        self,
        user_id: str,
        campaign_id: str,
        status: str,
    ) -> dict[str, Any]:
        """Update a Meta campaign's serving status.

        Args:
            user_id: The user's UUID.
            campaign_id: Meta campaign ID.
            status: Internal status string — ``"active"`` or ``"paused"``.

        Returns:
            Dict with success flag, or {"error": ...}.
        """
        import httpx  # noqa: PLC0415

        token = await self._get_token(user_id)
        meta_status = _STATUS_TO_META.get(status, "PAUSED")
        url = f"{_GRAPH_BASE}/{campaign_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    json={"status": meta_status, "access_token": token},
                )
                resp.raise_for_status()
                data = resp.json()
                return {"success": data.get("success", True), "status": status}
        except Exception:
            logger.exception(
                "MetaAdsService.update_campaign_status failed for user=%s campaign=%s",
                user_id,
                campaign_id,
            )
            return {"error": "Failed to update Meta campaign status."}

    async def update_campaign_budget(
        self,
        user_id: str,
        campaign_id: str,
        daily_budget: int | None = None,
        lifetime_budget: int | None = None,
    ) -> dict[str, Any]:
        """Update a Meta campaign's budget.

        Budget values are in **cents** (USD × 100).

        Args:
            user_id: The user's UUID.
            campaign_id: Meta campaign ID.
            daily_budget: New daily budget in cents, or ``None`` to leave unchanged.
            lifetime_budget: New lifetime budget in cents, or ``None`` to leave
                unchanged.

        Returns:
            Dict with success flag, or {"error": ...}.
        """
        import httpx  # noqa: PLC0415

        token = await self._get_token(user_id)
        url = f"{_GRAPH_BASE}/{campaign_id}"

        payload: dict[str, Any] = {"access_token": token}
        if daily_budget is not None:
            payload["daily_budget"] = daily_budget
        if lifetime_budget is not None:
            payload["lifetime_budget"] = lifetime_budget

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return {
                    "success": data.get("success", True),
                    "daily_budget_cents": daily_budget,
                    "lifetime_budget_cents": lifetime_budget,
                }
        except Exception:
            logger.exception(
                "MetaAdsService.update_campaign_budget failed for user=%s campaign=%s",
                user_id,
                campaign_id,
            )
            return {"error": "Failed to update Meta campaign budget."}

    # -------------------------------------------------------------------------
    # Insights / performance reporting
    # -------------------------------------------------------------------------

    async def get_campaign_insights(
        self,
        user_id: str,
        ad_account_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """Retrieve daily campaign performance insights from Meta.

        Args:
            user_id: The user's UUID.
            ad_account_id: Meta ad account ID (digits only).
            start_date: ISO date string, e.g. ``"2026-01-01"``.
            end_date: ISO date string, e.g. ``"2026-01-31"``.

        Returns:
            List of daily insight dicts with keys: campaign_id,
            campaign_name, date, impressions, clicks, spend (USD),
            conversions, conversion_value.
        """
        import httpx  # noqa: PLC0415

        token = await self._get_token(user_id)
        fields = (
            "campaign_id,campaign_name,impressions,clicks,spend,"
            "actions,action_values"
        )
        time_range = f"{{'since':'{start_date}','until':'{end_date}'}}"
        url = (
            f"{_GRAPH_BASE}/act_{ad_account_id}/insights"
            f"?fields={fields}"
            f"&time_range={time_range}"
            "&level=campaign"
            "&time_increment=1"
            f"&access_token={token}"
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                raw_rows = data.get("data", [])

            rows: list[dict[str, Any]] = []
            for row in raw_rows:
                # Extract conversion count from actions array
                actions = row.get("actions", [])
                conversions = sum(
                    float(a.get("value", 0))
                    for a in actions
                    if a.get("action_type") in (
                        "offsite_conversion",
                        "onsite_conversion.lead_grouped",
                        "purchase",
                        "complete_registration",
                    )
                )

                # Extract conversion value
                action_values = row.get("action_values", [])
                conversion_value = sum(
                    float(av.get("value", 0)) for av in action_values
                )

                rows.append({
                    "campaign_id": row.get("campaign_id"),
                    "campaign_name": row.get("campaign_name"),
                    "date": row.get("date_start"),
                    "impressions": int(row.get("impressions", 0)),
                    "clicks": int(row.get("clicks", 0)),
                    "spend": float(row.get("spend", 0)),
                    "conversions": conversions,
                    "conversion_value": conversion_value,
                })
            return rows
        except Exception:
            logger.exception(
                "MetaAdsService.get_campaign_insights failed for user=%s account=%s",
                user_id,
                ad_account_id,
            )
            return []


__all__ = ["MetaAdsService"]
