# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""IntegrationManager — Credential lifecycle and sync state management.

This service handles the full OAuth credential lifecycle for external
integrations: encrypted storage, proactive token refresh with async
locking, and per-provider sync state tracking.

All tokens are encrypted at rest with Fernet via ``encrypt_secret`` /
``decrypt_secret`` from ``app.services.encryption``.

Token refresh uses an ``asyncio.Lock`` per ``(user_id, provider)`` pair
with a double-check pattern to prevent concurrent refresh races.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar

import httpx

from app.config.integration_providers import PROVIDER_REGISTRY
from app.services.base_service import BaseService
from app.services.encryption import decrypt_secret, encrypt_secret

logger = logging.getLogger(__name__)


def _is_expiring_soon(expires_at_str: str | None, minutes: int = 5) -> bool:
    """Check whether a token's expiration is within ``minutes`` from now.

    Args:
        expires_at_str: ISO-8601 timestamp string, or ``None`` for
            non-expiring tokens.
        minutes: Threshold in minutes (default 5).

    Returns:
        ``True`` if the token expires within the threshold, ``False``
        if it has no expiry or is still valid beyond the threshold.
    """
    if not expires_at_str:
        return False
    try:
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        remaining = (expires_at - now).total_seconds()
        return remaining < (minutes * 60)
    except (ValueError, TypeError):
        logger.warning("Invalid expires_at value: %s", expires_at_str)
        return False


class IntegrationManager(BaseService):
    """Manages integration credentials and sync state.

    Extends ``BaseService`` for Supabase query execution with proper
    RLS authentication.

    Class-level lock registry ensures only one coroutine refreshes a
    given ``(user_id, provider)`` token at a time.
    """

    _refresh_locks: ClassVar[dict[tuple[str, str], asyncio.Lock]] = {}
    _locks_guard = asyncio.Lock()

    @classmethod
    async def _get_refresh_lock(cls, user_id: str, provider: str) -> asyncio.Lock:
        """Get or create the refresh lock for a (user_id, provider) pair.

        Args:
            user_id: The user's UUID.
            provider: Provider key (e.g. ``"hubspot"``).

        Returns:
            An ``asyncio.Lock`` dedicated to this user+provider combination.
        """
        key = (user_id, provider)
        async with cls._locks_guard:
            if key not in cls._refresh_locks:
                cls._refresh_locks[key] = asyncio.Lock()
            return cls._refresh_locks[key]

    # ========================================================================
    # Credential CRUD
    # ========================================================================

    async def store_credentials(
        self,
        *,
        user_id: str,
        provider: str,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: str | None = None,
        scopes: str = "",
        account_name: str = "",
        token_type: str = "bearer",
    ) -> dict[str, Any]:
        """Encrypt and upsert integration credentials.

        Tokens are encrypted with Fernet before being persisted so that
        plaintext secrets never touch the database.

        Args:
            user_id: The user's UUID.
            provider: Provider key.
            access_token: Plaintext OAuth access token.
            refresh_token: Plaintext OAuth refresh token (optional).
            expires_at: ISO-8601 expiration timestamp (optional).
            scopes: Space-separated scope string.
            account_name: Display name from the provider.
            token_type: Token type (default ``"bearer"``).

        Returns:
            The upserted credential row as a dict.
        """
        encrypted_access = encrypt_secret(access_token)
        encrypted_refresh = encrypt_secret(refresh_token) if refresh_token else None

        row = {
            "user_id": user_id,
            "provider": provider,
            "access_token": encrypted_access,
            "refresh_token": encrypted_refresh,
            "token_type": token_type,
            "scopes": scopes,
            "expires_at": expires_at,
            "account_name": account_name,
        }

        result = await self.execute(
            self.client.table("integration_credentials")
            .upsert(row, on_conflict="user_id,provider"),
            op_name="integrations.store_credentials",
        )
        return result.data[0] if result.data else row

    async def get_credentials(
        self, user_id: str, provider: str
    ) -> dict[str, Any] | None:
        """Fetch raw credential row (tokens still encrypted).

        Args:
            user_id: The user's UUID.
            provider: Provider key.

        Returns:
            The credential row dict, or ``None`` if not found.
        """
        result = await self.execute(
            self.client.table("integration_credentials")
            .select("*")
            .eq("user_id", user_id)
            .eq("provider", provider),
            op_name="integrations.get_credentials",
        )
        return result.data[0] if result.data else None

    async def get_valid_token(
        self, user_id: str, provider: str
    ) -> str | None:
        """Get a valid (decrypted) access token, refreshing if necessary.

        If the token expires within 5 minutes, acquires an async lock for
        the ``(user_id, provider)`` pair and performs a double-check: after
        acquiring the lock, re-reads the credential to see if another
        coroutine already refreshed it.

        Args:
            user_id: The user's UUID.
            provider: Provider key.

        Returns:
            Decrypted access token string, or ``None`` if no credential
            exists.
        """
        cred = await self.get_credentials(user_id, provider)
        if not cred:
            return None

        if not _is_expiring_soon(cred.get("expires_at")):
            return decrypt_secret(cred["access_token"])

        # Token is expiring — acquire lock and double-check
        lock = await self._get_refresh_lock(user_id, provider)
        async with lock:
            # Re-read after acquiring lock (another coroutine may have refreshed)
            cred = await self.get_credentials(user_id, provider)
            if not cred:
                return None

            if not _is_expiring_soon(cred.get("expires_at")):
                # Another coroutine already refreshed — use the fresh token
                return decrypt_secret(cred["access_token"])

            # Still expiring — perform the refresh
            cred = await self._refresh_token(user_id, provider, cred)
            return decrypt_secret(cred["access_token"])

    async def _refresh_token(
        self, user_id: str, provider: str, cred: dict[str, Any]
    ) -> dict[str, Any]:
        """Exchange a refresh token for a new access token.

        Calls the provider's token URL with ``grant_type=refresh_token``,
        then stores the new tokens via ``store_credentials``.

        Args:
            user_id: The user's UUID.
            provider: Provider key.
            cred: Current credential row (with encrypted tokens).

        Returns:
            Updated credential row.

        Raises:
            httpx.HTTPStatusError: If the token exchange fails.
        """
        provider_config = PROVIDER_REGISTRY.get(provider)
        if not provider_config:
            raise ValueError(f"Unknown provider: {provider}")

        refresh_token = (
            decrypt_secret(cred["refresh_token"])
            if cred.get("refresh_token")
            else None
        )
        if not refresh_token:
            logger.warning(
                "No refresh token available for user=%s provider=%s",
                user_id,
                provider,
            )
            return cred

        client_id = os.environ.get(provider_config.client_id_env, "")
        client_secret = os.environ.get(provider_config.client_secret_env, "")

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.post(
                provider_config.token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            response.raise_for_status()
            token_data = response.json()

        new_access = token_data.get("access_token", "")
        new_refresh = token_data.get("refresh_token", refresh_token)
        expires_in = token_data.get("expires_in")

        expires_at = None
        if expires_in:
            expires_at = (
                datetime.now(tz=timezone.utc)
                + timedelta(seconds=int(expires_in))
            ).isoformat()

        return await self.store_credentials(
            user_id=user_id,
            provider=provider,
            access_token=new_access,
            refresh_token=new_refresh,
            expires_at=expires_at,
            scopes=cred.get("scopes", ""),
            account_name=cred.get("account_name", ""),
            token_type=cred.get("token_type", "bearer"),
        )

    async def delete_credentials(self, user_id: str, provider: str) -> bool:
        """Remove a user's credentials for a provider.

        Args:
            user_id: The user's UUID.
            provider: Provider key.

        Returns:
            ``True`` if a row was deleted, ``False`` otherwise.
        """
        result = await self.execute(
            self.client.table("integration_credentials")
            .delete()
            .eq("user_id", user_id)
            .eq("provider", provider),
            op_name="integrations.delete_credentials",
        )
        return bool(result.data)

    async def get_all_credentials(self, user_id: str) -> list[dict[str, Any]]:
        """List all connected providers for a user (metadata only).

        Tokens are NOT decrypted — only metadata fields are returned.

        Args:
            user_id: The user's UUID.

        Returns:
            List of dicts with ``provider``, ``account_name``,
            ``expires_at``, ``scopes``, ``token_type``.
        """
        result = await self.execute(
            self.client.table("integration_credentials")
            .select(
                "provider, account_name, expires_at, "
                "scopes, token_type, created_at"
            )
            .eq("user_id", user_id),
            op_name="integrations.get_all_credentials",
        )
        return result.data or []

    # ========================================================================
    # Sync State
    # ========================================================================

    async def get_sync_state(
        self, user_id: str, provider: str
    ) -> dict[str, Any] | None:
        """Fetch the sync state for a user + provider.

        Args:
            user_id: The user's UUID.
            provider: Provider key.

        Returns:
            Sync state row dict, or ``None`` if not found.
        """
        result = await self.execute(
            self.client.table("integration_sync_state")
            .select("*")
            .eq("user_id", user_id)
            .eq("provider", provider),
            op_name="integrations.get_sync_state",
        )
        return result.data[0] if result.data else None

    async def update_sync_state(
        self,
        *,
        user_id: str,
        provider: str,
        sync_cursor: dict[str, Any] | None = None,
        last_sync_at: str | None = None,
        error_count: int | None = None,
        last_error: str | None = None,
        backoff_until: str | None = None,
    ) -> dict[str, Any]:
        """Upsert sync state for a user + provider.

        Only non-None fields are updated, allowing callers to update
        individual fields without overwriting others.

        Args:
            user_id: The user's UUID.
            provider: Provider key.
            sync_cursor: Provider-specific pagination cursor.
            last_sync_at: ISO-8601 timestamp of last successful sync.
            error_count: Number of consecutive errors.
            last_error: Description of the most recent error.
            backoff_until: ISO-8601 timestamp before which no sync should retry.

        Returns:
            The upserted sync state row.
        """
        row: dict[str, Any] = {
            "user_id": user_id,
            "provider": provider,
        }
        if sync_cursor is not None:
            row["sync_cursor"] = sync_cursor
        if last_sync_at is not None:
            row["last_sync_at"] = last_sync_at
        if error_count is not None:
            row["error_count"] = error_count
        if last_error is not None:
            row["last_error"] = last_error
        if backoff_until is not None:
            row["backoff_until"] = backoff_until

        result = await self.execute(
            self.client.table("integration_sync_state")
            .upsert(row, on_conflict="user_id,provider"),
            op_name="integrations.update_sync_state",
        )
        return result.data[0] if result.data else row

    # ========================================================================
    # Aggregated Status
    # ========================================================================

    async def get_integration_status(
        self, user_id: str
    ) -> list[dict[str, Any]]:
        """Get per-provider connection status for a user.

        Merges credential and sync state data for all providers in the
        registry, returning a unified status list for the UI.

        Args:
            user_id: The user's UUID.

        Returns:
            List of status dicts, one per provider in the registry.
        """
        creds = await self.get_all_credentials(user_id)
        cred_map = {c["provider"]: c for c in creds}

        # Fetch all sync states for user
        sync_result = await self.execute(
            self.client.table("integration_sync_state")
            .select("*")
            .eq("user_id", user_id),
            op_name="integrations.get_all_sync_states",
        )
        sync_map = {s["provider"]: s for s in (sync_result.data or [])}

        statuses = []
        for key, config in PROVIDER_REGISTRY.items():
            cred = cred_map.get(key)
            sync = sync_map.get(key)

            connected = cred is not None
            has_error = sync and sync.get("error_count", 0) > 0

            if has_error:
                status = "error"
            elif connected:
                status = "connected"
            else:
                status = "disconnected"

            statuses.append({
                "provider": key,
                "name": config.name,
                "category": config.category,
                "connected": connected,
                "status": status,
                "account_name": cred.get("account_name", "") if cred else "",
                "last_sync_at": sync.get("last_sync_at") if sync else None,
                "error_count": sync.get("error_count", 0) if sync else 0,
                "last_error": sync.get("last_error") if sync else None,
            })

        return statuses
