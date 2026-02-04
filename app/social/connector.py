# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Social Media OAuth Connector.

Handles OAuth 2.0 flows for connecting social media accounts.
"""

import os
import hashlib
import base64
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode

from supabase import Client
from app.services.supabase import get_service_client

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
        "scopes": ["pages_show_list", "pages_manage_posts", "pages_read_engagement"],
        "client_id_env": "FACEBOOK_APP_ID",
        "client_secret_env": "FACEBOOK_APP_SECRET",
    },
    "instagram": {
        "auth_url": "https://api.instagram.com/oauth/authorize",
        "token_url": "https://api.instagram.com/oauth/access_token",
        "scopes": ["instagram_basic", "instagram_content_publish"],
        "client_id_env": "INSTAGRAM_APP_ID",
        "client_secret_env": "INSTAGRAM_APP_SECRET",
    },
    "youtube": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"],
        "client_id_env": "YOUTUBE_CLIENT_ID",
        "client_secret_env": "YOUTUBE_CLIENT_SECRET",
    },
}


class SocialConnector:
    """Manages OAuth connections to social media platforms."""
    
    def __init__(self):
        self.client = self._get_supabase()
        self._pkce_verifiers: Dict[str, str] = {}  # state -> verifier

    def _get_supabase(self) -> Client:
        return get_service_client()

    def _generate_pkce(self) -> tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge."""
        verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()
        return verifier, challenge

    def get_authorization_url(
        self, 
        platform: str, 
        user_id: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
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
        
        return {
            "authorization_url": auth_url,
            "state": state,
            "platform": platform
        }

    async def handle_callback(
        self,
        platform: str,
        code: str,
        state: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
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
        except:
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
            "status": "active"
        }
        
        # Upsert (update if exists)
        self.client.table("connected_accounts").upsert(
            connection_data,
            on_conflict="user_id,platform"
        ).execute()
        
        return {
            "success": True,
            "platform": platform,
            "message": f"Successfully connected {platform} account"
        }

    def list_connections(self, user_id: str) -> List[Dict[str, Any]]:
        """List all connected accounts for a user."""
        result = self.client.table("connected_accounts").select(
            "id, platform, platform_username, status, connected_at"
        ).eq("user_id", user_id).execute()
        
        return result.data

    def revoke_connection(self, user_id: str, platform: str) -> Dict[str, Any]:
        """Revoke/disconnect a social account."""
        self.client.table("connected_accounts").update(
            {"status": "revoked"}
        ).eq("user_id", user_id).eq("platform", platform).execute()
        
        return {"success": True, "message": f"Disconnected {platform}"}

    def get_access_token(self, user_id: str, platform: str) -> Optional[str]:
        """Get valid access token for a platform, refreshing if needed."""
        result = self.client.table("connected_accounts").select("*").eq(
            "user_id", user_id
        ).eq("platform", platform).eq("status", "active").execute()
        
        if not result.data:
            return None
            
        account = result.data[0]
        
        # Check expiry
        expires_at = account.get("token_expires_at")
        if expires_at:
            exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if exp_dt < datetime.now(exp_dt.tzinfo):
                # Token expired - would need refresh logic here
                return None
        
        return account.get("access_token")


# Singleton
_connector: Optional[SocialConnector] = None

def get_social_connector() -> SocialConnector:
    global _connector
    if _connector is None:
        _connector = SocialConnector()
    return _connector
