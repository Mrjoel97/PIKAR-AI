# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Social Media OAuth Connector.

Handles OAuth 2.0 flows for connecting social media accounts.
"""

import asyncio
import base64
import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar
from urllib.parse import urlencode

import httpx
from cryptography.fernet import InvalidToken

from app.services.encryption import decrypt_secret, encrypt_secret
from app.services.supabase import get_service_client
from supabase import Client

logger = logging.getLogger(__name__)

PKCE_STATE_TABLE = "oauth_pkce_states"
PKCE_TTL_MINUTES = int(os.environ.get("SOCIAL_OAUTH_PKCE_TTL_MINUTES", "10"))

# Platform configurations
PLATFORM_CONFIGS = {
    "linkedin": {
        "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
        "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
        "scopes": ["openid", "profile", "w_member_social"],
        "client_id_env": "LINKEDIN_CLIENT_ID",
        "client_secret_env": "LINKEDIN_CLIENT_SECRET",
    },
    "twitter": {
        "auth_url": "https://twitter.com/i/oauth2/authorize",
        "token_url": "https://api.twitter.com/2/oauth2/token",
        "scopes": ["tweet.read", "tweet.write", "users.read", "offline.access"],
        "client_id_env": "TWITTER_CLIENT_ID",
        "client_secret_env": "TWITTER_CLIENT_SECRET",
    },
    "facebook": {
        "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
        "scopes": [
            "pages_show_list",
            "pages_manage_posts",
            "pages_read_engagement",
            "read_insights",
        ],
        "client_id_env": "FACEBOOK_APP_ID",
        "client_secret_env": "FACEBOOK_APP_SECRET",
    },
    "instagram": {
        "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
        "scopes": [
            "instagram_basic",
            "instagram_content_publish",
            "instagram_manage_insights",
            "pages_show_list",
        ],
        "client_id_env": "FACEBOOK_APP_ID",
        "client_secret_env": "FACEBOOK_APP_SECRET",
    },
    "youtube": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube",
        ],
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
    },
    "tiktok": {
        "auth_url": "https://www.tiktok.com/v2/auth/authorize/",
        "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
        "scopes": ["user.info.basic", "video.publish", "video.upload"],
        "client_id_env": "TIKTOK_CLIENT_KEY",
        "client_secret_env": "TIKTOK_CLIENT_SECRET",
    },
    "google_search_console": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": [
            "https://www.googleapis.com/auth/webmasters.readonly",
            "https://www.googleapis.com/auth/analytics.readonly",
        ],
        "client_id_env": "GOOGLE_SEO_CLIENT_ID",
        "client_secret_env": "GOOGLE_SEO_CLIENT_SECRET",
    },
    "google_analytics": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["https://www.googleapis.com/auth/analytics.readonly"],
        "client_id_env": "GOOGLE_SEO_CLIENT_ID",
        "client_secret_env": "GOOGLE_SEO_CLIENT_SECRET",
    },
}


class SocialConnector:
    """Manages OAuth connections to social media platforms.

    Class-level lock registry ensures only one coroutine refreshes a
    given ``(user_id, platform)`` token at a time. Mirrors the pattern
    in :class:`app.services.integration_manager.IntegrationManager`.
    """

    # Per-(user_id, platform) lock registry used by the async refresh path.
    # ``_locks_guard`` is initialized lazily inside ``_get_refresh_lock`` so
    # that the lock binds to the active asyncio event loop, not whichever
    # loop happened to be running at class-definition time.
    _refresh_locks: ClassVar[dict[tuple[str, str], asyncio.Lock]] = {}
    _locks_guard: ClassVar[asyncio.Lock | None] = None

    @classmethod
    async def _get_refresh_lock(cls, user_id: str, platform: str) -> asyncio.Lock:
        """Get or create the refresh lock for a ``(user_id, platform)`` pair.

        Args:
            user_id: The user's UUID.
            platform: Social platform name.

        Returns:
            An :class:`asyncio.Lock` dedicated to this user + platform.
        """
        if cls._locks_guard is None:
            cls._locks_guard = asyncio.Lock()
        key = (user_id, platform)
        async with cls._locks_guard:
            if key not in cls._refresh_locks:
                cls._refresh_locks[key] = asyncio.Lock()
            return cls._refresh_locks[key]

    def __init__(self):
        self.client = self._get_supabase()
        self._pkce_verifiers: dict[str, str] = {}  # state -> verifier

    def _get_supabase(self) -> Client:
        return get_service_client()

    def _generate_pkce(self) -> tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge."""
        verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        return verifier, challenge

    def _encrypt_token(self, token: str | None) -> str | None:
        if not token:
            return None
        return encrypt_secret(token)

    def _decrypt_token(self, token: str | None) -> str | None:
        if not token:
            return None
        try:
            return decrypt_secret(token)
        except InvalidToken:
            if token.startswith("gAAAAA"):
                logger.exception("Encrypted social OAuth token could not be decrypted")
                return None
            logger.warning(
                "Using legacy plaintext social OAuth token. "
                "Reconnect this account to rotate it into encrypted storage."
            )
            return token
        except RuntimeError:
            logger.exception("Social token decryption is not configured")
            return None
        except Exception:
            logger.exception("Social OAuth token decryption failed")
            return None

    async def _fetch_linkedin_identity(
        self,
        http: httpx.AsyncClient,
        access_token: str,
    ) -> tuple[str | None, str | None]:
        """Fetch ``(sub, display_name)`` from LinkedIn ``/v2/userinfo``.

        Returns ``(sub, name)`` on success; ``(None, None)`` on any
        failure. Never raises. Display name prefers ``name``; falls back
        to ``given_name``; finally ``None``.

        This is the LinkedIn-specific helper called by the publisher
        lazy-backfill path (when ``connected_accounts.platform_user_id``
        is null at publish time) AND by ``_fetch_platform_profile`` for
        the LinkedIn dispatch arm. Phase 101 AUTH-04 will refactor the
        per-platform dispatch into a registry; the signature here is
        designed so that change is a one-line wiring update.

        Args:
            http: An open ``httpx.AsyncClient`` -- callers reuse the
                same client opened higher up the stack so we don't pay
                another connection setup.
            access_token: Plaintext bearer token issued for the
                ``openid profile`` scopes.

        Returns:
            ``(sub, display_name)`` -- either or both may be ``None``.
        """
        try:
            resp = await http.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
        except httpx.HTTPError:
            logger.exception("LinkedIn /v2/userinfo fetch raised")
            return None, None

        if resp.status_code != 200:
            logger.warning(
                "LinkedIn /v2/userinfo failed: status=%s body=%s",
                resp.status_code,
                (resp.text or "")[:200],
            )
            return None, None

        try:
            j = resp.json()
        except (ValueError, TypeError):
            logger.warning("LinkedIn /v2/userinfo returned non-JSON body")
            return None, None

        sub = j.get("sub")
        name = j.get("name") or j.get("given_name")
        return sub, name

    async def _fetch_platform_profile(
        self,
        platform: str,
        access_token: str,
        http: httpx.AsyncClient,
    ) -> tuple[str | None, str | None]:
        """Fetch (platform_user_id, platform_username) from the provider.

        Best-effort: any failure (network error, non-200 status, malformed
        JSON, missing fields) returns ``(None, None)`` and logs a WARNING.
        The OAuth flow MUST NOT abort because profile capture failed -- the
        user still gets a connected account row, just without the display
        identifiers.

        Out-of-scope platforms (threads, pinterest, google_search_console,
        google_analytics) short-circuit to ``(None, None)`` without an
        error -- those will be added in Phase 108.

        TikTok captures ``open_id`` only (``platform_username = None``)
        because the ``user.info.profile`` scope required for the username
        is not in ``PLATFORM_CONFIGS["tiktok"]["scopes"]`` -- that scope
        addition is Phase 108 hygiene.

        Args:
            platform: Social platform name (must be in PLATFORM_CONFIGS).
            access_token: Plaintext bearer token from the just-completed
                token exchange. Caller is responsible for encryption
                downstream.
            http: The same ``httpx.AsyncClient`` opened by
                ``handle_callback`` -- reused so we don't pay another
                connection setup.

        Returns:
            ``(platform_user_id, platform_username)`` -- either or both
            may be ``None`` on partial / total failure.
        """
        if platform == "linkedin":
            # Delegate to the LinkedIn-specific helper so the OIDC
            # display-name fallback (``name`` -> ``given_name``) and the
            # WARNING log shape stay consistent with the publisher's
            # lazy-backfill path.
            return await self._fetch_linkedin_identity(http, access_token)

        headers = {"Authorization": f"Bearer {access_token}"}
        resp = None
        try:
            if platform == "twitter":
                resp = await http.get(
                    "https://api.twitter.com/2/users/me",
                    headers=headers,
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {}) or {}
                    return data.get("id"), data.get("username")
            elif platform == "facebook":
                resp = await http.get(
                    "https://graph.facebook.com/v18.0/me",
                    headers=headers,
                    params={"fields": "id,name"},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    j = resp.json()
                    return j.get("id"), j.get("name")
            elif platform == "instagram":
                # IG Business connects via FB Page. Walk /me/accounts and
                # pick the first page with an instagram_business_account.
                resp = await http.get(
                    "https://graph.facebook.com/v18.0/me/accounts",
                    headers=headers,
                    params={"fields": "instagram_business_account{id,username}"},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    pages = resp.json().get("data", []) or []
                    for page in pages:
                        iba = page.get("instagram_business_account") or {}
                        if iba.get("id"):
                            return iba.get("id"), iba.get("username")
            elif platform == "tiktok":
                resp = await http.get(
                    "https://open.tiktokapis.com/v2/user/info/",
                    headers=headers,
                    params={"fields": "open_id"},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    user = (resp.json().get("data") or {}).get("user") or {}
                    # username requires user.info.profile scope (Phase 108)
                    return user.get("open_id"), None
            elif platform == "youtube":
                resp = await http.get(
                    "https://www.googleapis.com/youtube/v3/channels",
                    headers=headers,
                    params={"part": "snippet,id", "mine": "true"},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    items = resp.json().get("items") or []
                    if items:
                        snippet = items[0].get("snippet") or {}
                        return items[0].get("id"), snippet.get("title")
            else:
                # google_search_console, google_analytics, threads,
                # pinterest: capture deferred to Phase 108 hygiene.
                return None, None

            # We executed a branch but did not return -- either non-200
            # status or an empty payload. Log so operators can diagnose
            # missing display identifiers in the UI.
            status = getattr(resp, "status_code", "no-response")
            logger.warning(
                "Profile capture failed for platform=%s: status=%s",
                platform,
                status,
            )

        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            logger.warning(
                "Profile capture failed for platform=%s: %s",
                platform,
                exc,
            )

        return None, None

    def _store_pkce_verifier(
        self, state: str, user_id: str, platform: str, verifier: str
    ) -> None:
        """Persist a PKCE verifier so callbacks survive worker restarts."""
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=PKCE_TTL_MINUTES)

        try:
            encrypted_verifier = encrypt_secret(verifier)
            self.client.table(PKCE_STATE_TABLE).upsert(
                {
                    "state": state,
                    "user_id": user_id,
                    "platform": platform,
                    "code_verifier": encrypted_verifier,
                    "expires_at": expires_at.isoformat(),
                },
                on_conflict="state",
            ).execute()
        except Exception as exc:
            logger.warning(
                "Persisting OAuth PKCE verifier failed; falling back to local memory: %s",
                exc,
            )
            self._pkce_verifiers[state] = verifier

    def _pop_pkce_verifier(self, state: str, platform: str) -> str | None:
        """Return and remove a persisted PKCE verifier for a callback state."""
        try:
            result = (
                self.client.table(PKCE_STATE_TABLE)
                .select("state, platform, code_verifier, expires_at")
                .eq("state", state)
                .limit(1)
                .execute()
            )
            rows = result.data or []

            if rows:
                row = rows[0]
                self.client.table(PKCE_STATE_TABLE).delete().eq(
                    "state", state
                ).execute()

                if row.get("platform") != platform:
                    return None

                expires_at = row.get("expires_at")
                if expires_at:
                    exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    if exp_dt < datetime.now(exp_dt.tzinfo):
                        return None

                return decrypt_secret(row["code_verifier"])
        except Exception as exc:
            logger.warning(
                "Loading persisted OAuth PKCE verifier failed; checking local memory: %s",
                exc,
            )

        return self._pkce_verifiers.pop(state, None)

    def get_authorization_url(
        self, platform: str, user_id: str, redirect_uri: str
    ) -> dict[str, Any]:
        """Generate OAuth authorization URL for a platform.

        Args:
            platform: Social platform name (linkedin, twitter, etc.)
            user_id: Pikar-AI user ID
            redirect_uri: OAuth callback URL

        Returns:
            Dict with authorization_url and state
        """
        if platform not in PLATFORM_CONFIGS:
            return {"error": f"Unsupported platform: {platform}"}

        config = PLATFORM_CONFIGS[platform]
        client_id = os.environ.get(config["client_id_env"])

        if not client_id:
            return {"error": f"Missing {config['client_id_env']} in environment"}

        # Generate state (includes user_id for callback)
        state = f"{user_id}:{secrets.token_urlsafe(16)}"

        # Generate PKCE
        verifier, challenge = self._generate_pkce()
        self._store_pkce_verifier(state, user_id, platform, verifier)

        # Build authorization URL
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(config["scopes"]),
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }

        auth_url = f"{config['auth_url']}?{urlencode(params)}"

        return {"authorization_url": auth_url, "state": state, "platform": platform}

    async def handle_callback(
        self, platform: str, code: str, state: str, redirect_uri: str
    ) -> dict[str, Any]:
        """Exchange authorization code for tokens and store connection.

        Args:
            platform: Social platform name
            code: Authorization code from callback
            state: State parameter (contains user_id)
            redirect_uri: Same redirect_uri used in authorization

        Returns:
            Dict with connection status
        """
        if platform not in PLATFORM_CONFIGS:
            return {"error": f"Unsupported platform: {platform}"}

        config = PLATFORM_CONFIGS[platform]

        # Extract user_id from state
        try:
            user_id = state.split(":")[0]
        except (IndexError, AttributeError):
            return {"error": "Invalid state parameter"}

        # Get PKCE verifier
        verifier = self._pop_pkce_verifier(state, platform)
        if not verifier:
            return {"error": "PKCE verifier not found. Session may have expired."}

        # Exchange code for tokens
        client_id = os.environ.get(config["client_id_env"])
        client_secret = os.environ.get(config["client_secret_env"])

        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
            "code_verifier": verifier,
        }

        async with httpx.AsyncClient() as http:
            resp = await http.post(config["token_url"], data=token_data)

            if resp.status_code != 200:
                return {"error": f"Token exchange failed: {resp.text}"}

            tokens = resp.json()

            access_token = tokens.get("access_token")
            if not access_token:
                return {"error": "Token exchange did not return an access token"}

            # Fetch provider profile to populate platform_user_id /
            # platform_username (AUTH-04). Best-effort: failures do not
            # abort the OAuth flow. Reuse the same AsyncClient so we don't
            # pay another connection setup.
            platform_user_id, platform_username = await self._fetch_platform_profile(
                platform,
                access_token,
                http,
            )

        try:
            encrypted_access_token = self._encrypt_token(access_token)
            encrypted_refresh_token = self._encrypt_token(tokens.get("refresh_token"))
        except RuntimeError:
            logger.exception("Social token encryption is not configured")
            return {"error": "Social token encryption is not configured"}

        # Calculate expiry
        expires_in = tokens.get("expires_in", 3600)
        expires_at = datetime.now() + timedelta(seconds=expires_in)

        # Store connection
        connection_data = {
            "user_id": user_id,
            "platform": platform,
            "access_token": encrypted_access_token,
            "refresh_token": encrypted_refresh_token,
            "platform_user_id": platform_user_id,
            "platform_username": platform_username,
            "token_expires_at": expires_at.isoformat(),
            "scopes": config["scopes"],
            "status": "active",
        }

        # Upsert (update if exists)
        self.client.table("connected_accounts").upsert(
            connection_data, on_conflict="user_id,platform"
        ).execute()

        return {
            "success": True,
            "platform": platform,
            "message": f"Successfully connected {platform} account",
        }

    def list_connections(self, user_id: str) -> list[dict[str, Any]]:
        """List all connected accounts for a user."""
        result = (
            self.client.table("connected_accounts")
            .select("id, platform, platform_username, status, connected_at")
            .eq("user_id", user_id)
            .execute()
        )

        return result.data

    def revoke_connection(self, user_id: str, platform: str) -> dict[str, Any]:
        """Revoke/disconnect a social account."""
        self.client.table("connected_accounts").update({"status": "revoked"}).eq(
            "user_id", user_id
        ).eq("platform", platform).execute()

        return {"success": True, "message": f"Disconnected {platform}"}

    def _fetch_active_account(
        self, user_id: str, platform: str
    ) -> dict[str, Any] | None:
        """Fetch the active connected_accounts row for a user + platform.

        Synchronous helper -- callers from async contexts must wrap this in
        ``asyncio.to_thread`` to avoid blocking the event loop on the
        underlying HTTP-based Supabase REST call.

        Args:
            user_id: Pikar-AI user ID.
            platform: Social platform name.

        Returns:
            The first matching row dict, or ``None`` if no active row.
        """
        result = (
            self.client.table("connected_accounts")
            .select("*")
            .eq("user_id", user_id)
            .eq("platform", platform)
            .eq("status", "active")
            .execute()
        )
        if not result.data:
            return None
        return result.data[0]

    def _update_account_tokens(
        self, user_id: str, platform: str, update_data: dict[str, Any]
    ) -> None:
        """Update token fields on the active connected_accounts row.

        Synchronous helper -- callers from async contexts must wrap this in
        ``asyncio.to_thread``.
        """
        self.client.table("connected_accounts").update(update_data).eq(
            "user_id", user_id
        ).eq("platform", platform).execute()

    @staticmethod
    def _is_token_expired(expires_at: str | None) -> bool:
        """Return True if the ISO-8601 expiry is in the past or unparseable.

        Returns False when ``expires_at`` is ``None`` (no expiry recorded
        means we trust the access token until proven otherwise -- matches
        the prior synchronous behavior).
        """
        if not expires_at:
            return False
        try:
            exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return False
        return exp_dt < datetime.now(exp_dt.tzinfo)

    async def get_access_token(self, user_id: str, platform: str) -> str | None:
        """Get a valid access token, refreshing under a per-key lock if needed.

        Mirrors :meth:`IntegrationManager.get_valid_token`: an
        :class:`asyncio.Lock` keyed by ``(user_id, platform)`` ensures only
        one coroutine fires the refresh HTTP call when many concurrent
        callers race against an expired row. The double-check inside the
        lock means losers re-read the freshly-refreshed row instead of
        firing redundant refreshes.

        Args:
            user_id: Pikar-AI user ID.
            platform: Social platform name.

        Returns:
            Plaintext access token, or ``None`` if no active connection
            exists or the refresh failed.
        """
        account = await asyncio.to_thread(self._fetch_active_account, user_id, platform)
        if not account:
            return None

        if not self._is_token_expired(account.get("token_expires_at")):
            return self._decrypt_token(account.get("access_token"))

        lock = await self._get_refresh_lock(user_id, platform)
        async with lock:
            # Double-check: another coroutine may have refreshed while we
            # were queued at the lock.
            account = await asyncio.to_thread(
                self._fetch_active_account, user_id, platform
            )
            if not account:
                return None
            if not self._is_token_expired(account.get("token_expires_at")):
                return self._decrypt_token(account.get("access_token"))
            return await self._refresh_token(user_id, platform, account)

    async def _refresh_token(
        self, user_id: str, platform: str, account: dict[str, Any]
    ) -> str | None:
        """Refresh an expired OAuth token using the stored refresh_token.

        Uses :class:`httpx.AsyncClient` so the call yields control to the
        event loop while the provider's token endpoint is responding.
        Callers must hold the per-(user_id, platform) lock returned by
        :meth:`_get_refresh_lock` to avoid concurrent-refresh races.

        Args:
            user_id: Pikar-AI user ID.
            platform: Social platform name.
            account: The connected_accounts row dict.

        Returns:
            New plaintext access token if refresh succeeds, ``None``
            otherwise.
        """
        refresh_token = self._decrypt_token(account.get("refresh_token"))
        if not refresh_token:
            return None

        if platform not in PLATFORM_CONFIGS:
            return None

        config = PLATFORM_CONFIGS[platform]
        client_id = os.environ.get(config["client_id_env"])
        client_secret = os.environ.get(config["client_secret_env"])

        if not client_id or not client_secret:
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                resp = await http.post(
                    config["token_url"],
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": client_id,
                        "client_secret": client_secret,
                    },
                )
                if resp.status_code != 200:
                    return None

                tokens = resp.json()
                new_access = tokens.get("access_token")
                if not new_access:
                    return None

                # Calculate new expiry
                expires_in = tokens.get("expires_in", 3600)
                new_expires = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

                # Update stored tokens
                update_data: dict[str, Any] = {
                    "access_token": self._encrypt_token(new_access),
                    "token_expires_at": new_expires.isoformat(),
                }
                # Some platforms issue a new refresh token on each refresh
                if tokens.get("refresh_token"):
                    update_data["refresh_token"] = self._encrypt_token(
                        tokens["refresh_token"]
                    )

                await asyncio.to_thread(
                    self._update_account_tokens, user_id, platform, update_data
                )

                return new_access
        except Exception:
            logger.exception(
                "OAuth refresh failed for user=%s platform=%s", user_id, platform
            )
            return None


# Singleton
_connector: SocialConnector | None = None


def get_social_connector() -> SocialConnector:
    global _connector
    if _connector is None:
        _connector = SocialConnector()
    return _connector
