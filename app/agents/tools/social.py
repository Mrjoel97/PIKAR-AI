# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Social Media Tools for Agents.

Tools for Marketing Agent to manage social accounts and publish content.
"""

import asyncio
from typing import Dict, Any, List


def list_connected_accounts(user_id: str) -> List[Dict[str, Any]]:
    """List all connected social media accounts for the user.
    
    Use this to see which platforms the user has connected.
    
    Args:
        user_id: The user's ID.
        
    Returns:
        List of connected accounts with platform and status.
    """
    from app.social.connector import get_social_connector
    connector = get_social_connector()
    return connector.list_connections(user_id)


def publish_to_social(
    user_id: str,
    platform: str,
    content: str
) -> Dict[str, Any]:
    """Publish content to a connected social media account.
    
    Use this when the user wants to post something to their social media.
    Supports: twitter, linkedin, facebook, instagram.
    
    Args:
        user_id: The user's ID.
        platform: Target platform (twitter, linkedin, facebook, instagram).
        content: The text content to post.
        
    Returns:
        Result with post_id if successful.
    """
    from app.social.publisher import get_social_publisher
    publisher = get_social_publisher()
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        publisher.post_text(user_id, platform, content)
    )


def get_oauth_url(
    platform: str,
    user_id: str,
    redirect_uri: str = "https://app.pikar.ai/auth/callback"
) -> Dict[str, Any]:
    """Get OAuth authorization URL to connect a social account.
    
    Use this when user wants to connect a new social media account.
    
    Args:
        platform: Platform to connect (twitter, linkedin, facebook, instagram).
        user_id: The user's ID.
        redirect_uri: OAuth callback URL.
        
    Returns:
        Dict with authorization_url to redirect user to.
    """
    from app.social.connector import get_social_connector
    connector = get_social_connector()
    return connector.get_authorization_url(platform, user_id, redirect_uri)


def disconnect_social_account(
    user_id: str,
    platform: str
) -> Dict[str, Any]:
    """Disconnect a social media account.
    
    Args:
        user_id: The user's ID.
        platform: Platform to disconnect.
        
    Returns:
        Confirmation of disconnection.
    """
    from app.social.connector import get_social_connector
    connector = get_social_connector()
    return connector.revoke_connection(user_id, platform)


SOCIAL_TOOLS = [
    list_connected_accounts,
    publish_to_social,
    get_oauth_url,
    disconnect_social_account,
]
