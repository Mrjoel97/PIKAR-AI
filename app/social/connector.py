# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Social Media OAuth Connector.

Handles OAuth 2.0 flows for connecting social media accounts.
"""

import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from app.services.supabase import get_service_client
from supabase import Client

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
    """Manages OAuth connections to social media platforms."""

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
        self._pkce_verifiers[state] = verifier

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
        import httpx

        if platform not in PLATFORM_CONFIGS:
            return {"error": f"Unsupported platform: {platform}"}

        config = PLATFORM_CONFIGS[platform]

        # Extract user_id from state
        try:
            user_id = state.split(":")[0]
        except (IndexError, AttributeError):
            return {"error": "Invalid state parameter"}

        # Get PKCE verifier
        verifier = self._pkce_verifiers.pop(state, None)
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

        # Calculate expiry
        expires_in = tokens.get("expires_in", 3600)
        expires_at = datetime.now() + timedelta(seconds=expires_in)

        # Store connection
        connection_data = {
            "user_id": user_id,
            "platform": platform,
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
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

    def get_access_token(self, user_id: str, platform: str) -> str | None:
        """Get valid access token for a platform, refreshing if needed."""
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

        account = result.data[0]

        # Check expiry
        expires_at = account.get("token_expires_at")
        if expires_at:
            exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if exp_dt < datetime.now(exp_dt.tzinfo):
                # Token expired — attempt refresh
                refreshed = self._refresh_token(user_id, platform, account)
                if refreshed:
                    return refreshed
                return None

        return account.get("access_token")

    def _refresh_token(
        self, user_id: str, platform: str, account: dict[str, Any]
    ) -> str | None:
        """Refresh an expired OAuth token using the stored refresh_token.

        Args:
            user_id: Pikar-AI user ID.
            platform: Social platform name.
            account: The connected_accounts row dict.

        Returns:
            New access token if refresh succeeds, None otherwise.
        """
        import httpx

        refresh_token = account.get("refresh_token")
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
            with httpx.Client(timeout=30.0) as http:
                resp = http.post(
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
                new_expires = datetime.now() + timedelta(seconds=expires_in)

                # Update stored tokens
                update_data: dict[str, Any] = {
                    "access_token": new_access,
                    "token_expires_at": new_expires.isoformat(),
                }
                # Some platforms issue a new refresh token on each refresh
                if tokens.get("refresh_token"):
                    update_data["refresh_token"] = tokens["refresh_token"]

                self.client.table("connected_accounts").update(update_data).eq(
                    "user_id", user_id
                ).eq("platform", platform).execute()

                return new_access
        except Exception:
            return None


# Singleton
_connector: SocialConnector | None = None


def get_social_connector() -> SocialConnector:
    global _connector
    if _connector is None:
        _connector = SocialConnector()
    return _connector
