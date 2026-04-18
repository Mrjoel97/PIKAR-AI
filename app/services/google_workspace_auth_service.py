# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Canonical Google Workspace credential sync and resolution service."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from app.services.encryption import decrypt_secret, encrypt_secret
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

GOOGLE_WORKSPACE_PROVIDER = "google_workspace"
GOOGLE_WORKSPACE_DISCONNECT_KEY = "google_workspace_explicit_disconnect"
GOOGLE_WORKSPACE_FEATURES = [
    "Google Docs - Create and edit documents",
    "Google Sheets - Create spreadsheets and track data",
    "Google Forms - Create surveys and feedback forms",
    "Google Calendar - Schedule events and meetings",
    "Gmail - Send emails on your behalf",
]


def _normalize_scopes(scopes: str | list[str] | tuple[str, ...] | None) -> str:
    """Normalize scopes to a space-delimited string for persistence."""
    if scopes is None:
        return ""
    if isinstance(scopes, str):
        return scopes.strip()
    return " ".join(scope.strip() for scope in scopes if scope and scope.strip())


def _extract_identity_data(identity: Any) -> dict[str, Any]:
    """Return identity metadata regardless of object/dict representation."""
    data = getattr(identity, "identity_data", None)
    if isinstance(data, dict):
        return data
    if isinstance(identity, dict):
        nested = identity.get("identity_data")
        if isinstance(nested, dict):
            return nested
    return {}


class GoogleWorkspaceAuthService:
    """Owns Google Workspace credential persistence and resolution."""

    def __init__(self, *, client: Any | None = None):
        self._client = client or get_service_client()

    @property
    def client(self) -> Any:
        """Return the Supabase client used by the service."""
        return self._client

    def sync_credentials(
        self,
        *,
        user_id: str,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: str | None = None,
        scopes: str | list[str] | tuple[str, ...] | None = None,
        email: str | None = None,
        token_type: str = "bearer",
    ) -> dict[str, Any]:
        """Persist Google Workspace credentials through the canonical store."""
        if not access_token:
            raise ValueError("Google Workspace access token is required.")

        existing = self._get_raw_canonical_row(user_id)
        scopes_text = _normalize_scopes(scopes) or (existing or {}).get("scopes") or ""

        row = {
            "user_id": user_id,
            "provider": GOOGLE_WORKSPACE_PROVIDER,
            "access_token": encrypt_secret(access_token),
            "refresh_token": (
                encrypt_secret(refresh_token)
                if refresh_token
                else (existing or {}).get("refresh_token")
            ),
            "token_type": token_type,
            "scopes": scopes_text,
            "expires_at": expires_at or (existing or {}).get("expires_at"),
            "account_name": email or (existing or {}).get("account_name") or "",
        }

        response = (
            self.client.table("integration_credentials")
            .upsert(row, on_conflict="user_id,provider")
            .execute()
        )
        self._clear_disconnect_marker(user_id)
        return response.data[0] if response.data else row

    def get_canonical_credentials(self, user_id: str) -> dict[str, Any] | None:
        """Return decrypted Google Workspace credentials from canonical storage."""
        row = self._get_raw_canonical_row(user_id)
        if not row:
            return None

        return {
            "access_token": (
                decrypt_secret(row["access_token"]) if row.get("access_token") else None
            ),
            "refresh_token": (
                decrypt_secret(row["refresh_token"])
                if row.get("refresh_token")
                else None
            ),
            "expires_at": row.get("expires_at"),
            "scopes": row.get("scopes") or "",
            "account_name": row.get("account_name") or "",
            "token_type": row.get("token_type") or "bearer",
            "updated_at": row.get("updated_at"),
            "source": "integration_credentials",
            "is_canonical": True,
        }

    def resolve_credentials(
        self,
        user_id: str,
        *,
        provider_token: str | None = None,
        provider_refresh_token: str | None = None,
        allow_legacy_fallback: bool = True,
    ) -> dict[str, Any] | None:
        """Resolve Google credentials from live state, canonical storage, or legacy fallback."""
        if provider_token or provider_refresh_token:
            return {
                "access_token": provider_token,
                "refresh_token": provider_refresh_token,
                "expires_at": None,
                "scopes": "",
                "account_name": "",
                "token_type": "bearer",
                "source": "session",
                "is_canonical": False,
            }

        canonical = self.get_canonical_credentials(user_id)
        if canonical and (canonical.get("access_token") or canonical.get("refresh_token")):
            return canonical

        if self._is_explicitly_disconnected(user_id):
            return None

        if not allow_legacy_fallback:
            return None

        legacy_google_tokens = self._get_legacy_google_token_row(user_id)
        if legacy_google_tokens:
            return legacy_google_tokens

        return self._get_legacy_refresh_token_row(user_id)

    def get_connection_status(self, user_id: str) -> dict[str, Any]:
        """Return truthful Google Workspace connection state for the UI."""
        google_identity = None
        user_email: str | None = None

        try:
            user_response = self.client.auth.admin.get_user_by_id(user_id)
            user_obj = getattr(user_response, "user", None)
            if user_obj is not None:
                user_email = getattr(user_obj, "email", None)
                for identity in getattr(user_obj, "identities", None) or []:
                    provider = getattr(identity, "provider", None)
                    if provider is None and isinstance(identity, dict):
                        provider = identity.get("provider")
                    if provider == "google":
                        google_identity = identity
                        break
        except Exception as exc:
            logger.warning("Failed to inspect Google identity for %s: %s", user_id, exc)

        resolved = self.resolve_credentials(user_id, allow_legacy_fallback=True)
        has_reusable_credentials = bool(resolved and resolved.get("refresh_token"))
        has_partial_credentials = bool(resolved and resolved.get("access_token"))

        identity_email = None
        if google_identity is not None:
            identity_email = _extract_identity_data(google_identity).get("email")

        email = user_email or identity_email
        if not email and resolved:
            account_name = resolved.get("account_name")
            if account_name:
                email = account_name

        if has_reusable_credentials:
            return {
                "connected": True,
                "email": email,
                "provider": "google",
                "features": GOOGLE_WORKSPACE_FEATURES,
                "message": "Google Workspace is connected and ready to use.",
                "needs_reconnect": False,
                "connected_via_identity": google_identity is not None,
                "connection_source": resolved.get("source"),
            }

        if google_identity is not None or has_partial_credentials:
            return {
                "connected": False,
                "email": email,
                "provider": "google",
                "features": [],
                "message": (
                    "Reconnect Google Workspace to finish storing a reusable "
                    "server-side token for Gmail, Calendar, Docs, Sheets, and Forms."
                ),
                "needs_reconnect": True,
                "connected_via_identity": google_identity is not None,
                "connection_source": resolved.get("source") if resolved else None,
            }

        return {
            "connected": False,
            "email": None,
            "provider": None,
            "features": [],
            "message": "Sign in with Google to enable Google Workspace features.",
            "needs_reconnect": False,
            "connected_via_identity": False,
            "connection_source": None,
        }

    def disconnect(self, user_id: str) -> bool:
        """Remove reusable Google Workspace credentials and mark the disconnect."""
        had_connection = bool(
            self.resolve_credentials(user_id, allow_legacy_fallback=True)
        )
        deleted_any = False

        deleted_any = (
            self._delete_rows(
                "integration_credentials",
                user_id=user_id,
                provider=GOOGLE_WORKSPACE_PROVIDER,
            )
            or deleted_any
        )
        deleted_any = (
            self._delete_rows("user_google_tokens", user_id=user_id) or deleted_any
        )
        deleted_any = (
            self._delete_rows("user_oauth_tokens", user_id=user_id, provider="google")
            or deleted_any
        )
        deleted_any = (
            self._delete_rows(
                "integration_sync_state",
                user_id=user_id,
                provider=GOOGLE_WORKSPACE_PROVIDER,
            )
            or deleted_any
        )
        self._set_disconnect_marker(user_id)

        return had_connection or deleted_any

    def _get_legacy_google_token_row(self, user_id: str) -> dict[str, Any] | None:
        """Return a legacy token bundle from ``user_google_tokens`` when available."""
        try:
            response = (
                self.client.table("user_google_tokens")
                .select("provider_token, refresh_token")
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
        except Exception as exc:
            logger.debug("Legacy user_google_tokens lookup failed for %s: %s", user_id, exc)
            return None

        row = response.data or {}
        access_token = row.get("provider_token")
        refresh_token = row.get("refresh_token")
        if not access_token and not refresh_token:
            return None

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": None,
            "scopes": "",
            "account_name": "",
            "token_type": "bearer",
            "source": "user_google_tokens",
            "is_canonical": False,
        }

    def _get_legacy_refresh_token_row(self, user_id: str) -> dict[str, Any] | None:
        """Return legacy refresh-token-only credentials when available."""
        refresh_token = self._get_legacy_refresh_token(user_id)
        if not refresh_token:
            return None

        return {
            "access_token": None,
            "refresh_token": refresh_token,
            "expires_at": None,
            "scopes": "",
            "account_name": "",
            "token_type": "bearer",
            "source": "legacy_refresh_token",
            "is_canonical": False,
        }

    def _get_legacy_refresh_token(self, user_id: str) -> str | None:
        """Resolve a legacy Google refresh token through compatibility fallbacks."""
        try:
            rpc_response = self.client.rpc(
                "get_user_provider_refresh_token",
                {"p_user_id": user_id},
            ).execute()
            token = rpc_response.data
            if isinstance(token, str) and token:
                return token
            if isinstance(token, list) and token:
                first = token[0]
                if isinstance(first, str):
                    return first
                if isinstance(first, dict):
                    return first.get("provider_refresh_token")
        except Exception as exc:
            logger.debug(
                "RPC get_user_provider_refresh_token failed for %s: %s", user_id, exc
            )

        try:
            response = (
                self.client.table("user_oauth_tokens")
                .select("refresh_token")
                .eq("user_id", user_id)
                .eq("provider", "google")
                .limit(1)
                .execute()
            )
            if response.data:
                return response.data[0].get("refresh_token")
        except Exception as exc:
            logger.debug("Legacy user_oauth_tokens lookup failed for %s: %s", user_id, exc)

        return None

    def _get_raw_canonical_row(self, user_id: str) -> dict[str, Any] | None:
        """Return the raw canonical integration_credentials row for the user."""
        response = (
            self.client.table("integration_credentials")
            .select(
                "access_token, refresh_token, expires_at, scopes, account_name, "
                "token_type, updated_at"
            )
            .eq("user_id", user_id)
            .eq("provider", GOOGLE_WORKSPACE_PROVIDER)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def _delete_rows(self, table_name: str, **filters: Any) -> bool:
        """Delete rows from a table and report whether any row was removed."""
        try:
            query = self.client.table(table_name).delete()
            for key, value in filters.items():
                query = query.eq(key, value)
            response = query.execute()
        except Exception as exc:
            logger.debug(
                "Failed to delete %s rows for %s (%s): %s",
                table_name,
                filters.get("user_id"),
                filters,
                exc,
            )
            return False
        return bool(response.data)

    def _is_explicitly_disconnected(self, user_id: str) -> bool:
        """Return whether the user explicitly disconnected Google Workspace."""
        try:
            response = (
                self.client.table("user_configurations")
                .select("config_value")
                .eq("user_id", user_id)
                .eq("config_key", GOOGLE_WORKSPACE_DISCONNECT_KEY)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            logger.debug(
                "Google Workspace disconnect marker lookup failed for %s: %s",
                user_id,
                exc,
            )
            return False
        rows = response.data
        if not isinstance(rows, list) or not rows:
            return False
        first_row = rows[0]
        if not isinstance(first_row, dict):
            return False
        return bool(first_row.get("config_value"))

    def _set_disconnect_marker(self, user_id: str) -> None:
        """Remember that the user explicitly disconnected Google Workspace."""
        self.client.table("user_configurations").upsert(
            {
                "user_id": user_id,
                "config_key": GOOGLE_WORKSPACE_DISCONNECT_KEY,
                "config_value": datetime.now(tz=timezone.utc).isoformat(),
                "is_sensitive": False,
            },
            on_conflict="user_id,config_key",
        ).execute()

    def _clear_disconnect_marker(self, user_id: str) -> None:
        """Remove the explicit disconnect marker after a fresh reconnect."""
        try:
            (
                self.client.table("user_configurations")
                .delete()
                .eq("user_id", user_id)
                .eq("config_key", GOOGLE_WORKSPACE_DISCONNECT_KEY)
                .execute()
            )
        except Exception as exc:
            logger.debug(
                "Google Workspace disconnect marker clear failed for %s: %s",
                user_id,
                exc,
            )


def get_google_workspace_auth_service(
    *, client: Any | None = None
) -> GoogleWorkspaceAuthService:
    """Return a GoogleWorkspaceAuthService instance."""
    return GoogleWorkspaceAuthService(client=client)


__all__ = [
    "GOOGLE_WORKSPACE_DISCONNECT_KEY",
    "GOOGLE_WORKSPACE_FEATURES",
    "GOOGLE_WORKSPACE_PROVIDER",
    "GoogleWorkspaceAuthService",
    "get_google_workspace_auth_service",
]
