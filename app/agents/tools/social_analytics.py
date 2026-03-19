"""Social Media Analytics Agent Tools.

ADK-compatible tools for fetching engagement metrics, post performance,
and account-level analytics from connected social media platforms.
"""

import asyncio
from typing import Any, Dict, List, Optional


def get_social_analytics(
    user_id: str,
    platform: str,
    metric_type: str = "account",
    resource_id: Optional[str] = None,
    since_days: int = 30,
) -> Dict[str, Any]:
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
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    service.get_platform_analytics(
                        user_id=user_id,
                        platform=platform,
                        metric_type=metric_type,
                        resource_id=resource_id,
                        since_days=since_days,
                    ),
                )
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(
                service.get_platform_analytics(
                    user_id=user_id,
                    platform=platform,
                    metric_type=metric_type,
                    resource_id=resource_id,
                    since_days=since_days,
                )
            )
    except Exception as e:
        return {"error": f"Social analytics failed: {e!s}"}


def get_all_platform_analytics(
    user_id: str,
    since_days: int = 30,
) -> Dict[str, Any]:
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
    connected_platforms = [c["platform"] for c in connections if c.get("status") == "active"]

    if not connected_platforms:
        return {
            "success": False,
            "error": "No social accounts connected. Use get_oauth_url to connect platforms.",
            "platforms": {},
        }

    service = get_social_analytics_service()

    async def _fetch_all():
        import asyncio as aio
        tasks = {
            platform: service.get_platform_analytics(
                user_id=user_id,
                platform=platform,
                metric_type="account",
                since_days=since_days,
            )
            for platform in connected_platforms
        }
        results = {}
        for platform, coro in tasks.items():
            try:
                results[platform] = await coro
            except Exception as e:
                results[platform] = {"error": str(e)}
        return results

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _fetch_all())
                platform_results = future.result(timeout=120)
        else:
            platform_results = loop.run_until_complete(_fetch_all())

        return {
            "success": True,
            "connected_platforms": connected_platforms,
            "analytics": platform_results,
            "period": f"last_{since_days}_days",
        }
    except Exception as e:
        return {"error": f"Multi-platform analytics failed: {e!s}"}


SOCIAL_ANALYTICS_TOOLS = [
    get_social_analytics,
    get_all_platform_analytics,
]
