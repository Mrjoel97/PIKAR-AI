# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Social Media Tools for Agents.

Tools for Marketing Agent to manage social accounts and publish content
including text, images, videos, and carousels.
"""

import asyncio
from typing import Any


def list_connected_accounts(user_id: str) -> list[dict[str, Any]]:
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
    content: str,
    media_url: str | None = None,
    media_urls: list[str] | None = None,
    media_type: str = "text",
    utm_params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Publish content to a connected social media account.

    Use this when the user wants to post to their social media.
    Supports text, images, videos, carousels, and reels.

    Platforms: twitter, linkedin, facebook, instagram, tiktok, youtube.

    Args:
        user_id: The user's ID.
        platform: Target platform (twitter, linkedin, facebook, instagram,
                  tiktok, youtube).
        content: The text/caption content to post.
        media_url: Single media URL (image or video). Convenience param;
                   if both media_url and media_urls are given, media_url
                   is prepended to media_urls.
        media_urls: List of media URLs for multi-image carousels or
                    batch posting.
        media_type: Type of media: 'text', 'image', 'video', 'carousel'.
                    Default is 'text' (no media). Set to 'image' or
                    'video' when attaching media. Use 'carousel' for
                    multi-image posts (Instagram, Facebook, LinkedIn).
        utm_params: Optional UTM tracking parameters to append to URLs
                    in the content. Dict with keys: utm_source, utm_medium,
                    utm_campaign, utm_term, utm_content.

    Returns:
        Result with post_id if successful.
    """
    import re

    from app.social.publisher import get_social_publisher

    publisher = get_social_publisher()

    # Append UTM params to any URLs in the content
    if utm_params:
        query_string = "&".join(f"{k}={v}" for k, v in utm_params.items())

        def _append_utm(match):
            url = match.group(0)
            separator = "&" if "?" in url else "?"
            return f"{url}{separator}{query_string}"

        content = re.sub(r'https?://[^\s<>"]+', _append_utm, content)

    # Merge media_url and media_urls into a single list
    resolved_urls: list[str] | None = None
    if media_url or media_urls:
        resolved_urls = []
        if media_url:
            resolved_urls.append(media_url)
        if media_urls:
            resolved_urls.extend(media_urls)

    # Auto-detect media_type from urls if caller left it as 'text'
    if resolved_urls and media_type == "text":
        first = resolved_urls[0].lower()
        if any(first.endswith(ext) for ext in (".mp4", ".mov", ".webm", ".avi")):
            media_type = "video"
        elif len(resolved_urls) > 1:
            media_type = "carousel"
        else:
            media_type = "image"

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        publisher.post_with_media(
            user_id=user_id,
            platform=platform,
            content=content,
            media_urls=resolved_urls,
            media_type=media_type,
        )
    )


def get_oauth_url(
    platform: str,
    user_id: str,
    redirect_uri: str = "https://app.pikar.ai/auth/callback",
) -> dict[str, Any]:
    """Get OAuth authorization URL to connect a social account.

    Use this when user wants to connect a new social media account.

    Args:
        platform: Platform to connect (twitter, linkedin, facebook,
                  instagram, tiktok, youtube).
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
    platform: str,
) -> dict[str, Any]:
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
