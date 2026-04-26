# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Social Media Analytics Agent Tools.

ADK-compatible tools for fetching engagement metrics, post performance,
and account-level analytics from connected social media platforms.
"""

from typing import Any


async def get_social_analytics(
    user_id: str,
    platform: str,
    metric_type: str = "account",
    resource_id: str | None = None,
    since_days: int = 30,
) -> dict[str, Any]:
    """Get analytics from a connected social media account.

    Fetches engagement metrics, follower stats, and performance data
    from any connected platform. Use 'account' for overview stats or
    'post' for specific post/video metrics.

    Args:
        user_id: The user's ID.
        platform: Platform to query (twitter, instagram, linkedin,
                  facebook, youtube).
        metric_type: 'account' for account-level stats (followers,
                     impressions, reach) or 'post' for per-post metrics
                     (likes, shares, comments).
        resource_id: The post/tweet/video ID. Required when metric_type
                     is 'post'.
        since_days: Lookback period in days for account metrics
                    (default: 30).

    Returns:
        Dictionary with platform-specific metrics.
    """
    from app.social.analytics import get_social_analytics_service

    service = get_social_analytics_service()

    try:
        return await service.get_platform_analytics(
            user_id=user_id,
            platform=platform,
            metric_type=metric_type,
            resource_id=resource_id,
            since_days=since_days,
        )
    except Exception as e:
        return {"error": f"Social analytics failed: {e!s}"}


async def get_all_platform_analytics(
    user_id: str,
    since_days: int = 30,
) -> dict[str, Any]:
    """Get account-level analytics from ALL connected social platforms at once.

    Queries every connected platform in parallel and returns a unified
    dashboard view. Use this for marketing overview dashboards.

    Args:
        user_id: The user's ID.
        since_days: Lookback period in days (default: 30).

    Returns:
        Dictionary with per-platform analytics and a summary.
    """
    from app.social.analytics import get_social_analytics_service
    from app.social.connector import get_social_connector

    connector = get_social_connector()
    connections = connector.list_connections(user_id)
    connected_platforms = [
        c["platform"] for c in connections if c.get("status") == "active"
    ]

    if not connected_platforms:
        return {
            "success": False,
            "error": "No social accounts connected. Use get_oauth_url to connect platforms.",
            "platforms": {},
        }

    service = get_social_analytics_service()

    try:
        results = {}
        for platform in connected_platforms:
            try:
                results[platform] = await service.get_platform_analytics(
                    user_id=user_id,
                    platform=platform,
                    metric_type="account",
                    since_days=since_days,
                )
            except Exception as e:
                results[platform] = {"error": str(e)}

        return {
            "success": True,
            "connected_platforms": connected_platforms,
            "analytics": results,
            "period": f"last_{since_days}_days",
        }
    except Exception as e:
        return {"error": f"Multi-platform analytics failed: {e!s}"}


SOCIAL_ANALYTICS_TOOLS = [
    get_social_analytics,
    get_all_platform_analytics,
]
