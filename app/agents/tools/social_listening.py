"""Social Listening Agent Tools.

ADK-compatible tools for monitoring brand mentions, tracking keyword
sentiment, and comparing share of voice across web, social media,
and forum platforms.
"""

import asyncio
from typing import Any, Dict, List, Optional


def monitor_brand(
    brand_name: str,
    keywords: Optional[List[str]] = None,
    platforms: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Monitor brand mentions across web, social media, and forums.

    Scans multiple platforms for recent mentions of a brand and
    related keywords. Returns a unified report with mention counts,
    sources, and engagement data. Use this for brand monitoring,
    reputation tracking, and competitive intelligence.

    Args:
        brand_name: The primary brand name to monitor.
        keywords: Additional keywords or phrases to track alongside
                  the brand name (e.g. product names, slogans).
        platforms: Which platforms to search. Options: "web" (blogs,
                   news, articles), "twitter" (recent tweets),
                   "reddit" (forum discussions). Default: all.
        user_id: The user's ID (required for Twitter access).

    Returns:
        Dictionary with:
        - total_mentions: Combined count across all platforms
        - mentions_by_platform: Per-platform breakdown
        - all_mentions: List of individual mentions with source, content, URL
        - web_summary: AI summary of web mentions
        - twitter_engagement: Total engagement on Twitter mentions
    """
    from app.mcp.tools.social_listening import monitor_brand_mentions

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    monitor_brand_mentions(
                        brand_name=brand_name,
                        keywords=keywords,
                        platforms=platforms,
                        user_id=user_id,
                    ),
                )
                return future.result(timeout=120)
        else:
            return loop.run_until_complete(
                monitor_brand_mentions(
                    brand_name=brand_name,
                    keywords=keywords,
                    platforms=platforms,
                    user_id=user_id,
                )
            )
    except Exception as e:
        return {"success": False, "error": str(e)}


def compare_share_of_voice(
    brands: List[str],
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Compare share of voice between your brand and competitors.

    Measures relative mention volume for each brand across web and
    social platforms, calculating share-of-voice percentages. Use this
    for competitive positioning analysis.

    Args:
        brands: List of brand names to compare (minimum 2, max 10).
        user_id: The user's ID (optional, enables Twitter data).

    Returns:
        Dictionary with:
        - results: Per-brand mention counts and share-of-voice percentage
        - leader: The brand with the highest mention volume
        - total_mentions_all: Combined mentions across all brands
    """
    from app.mcp.tools.social_listening import compare_brand_share_of_voice

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    compare_brand_share_of_voice(brands=brands, user_id=user_id),
                )
                return future.result(timeout=180)
        else:
            return loop.run_until_complete(
                compare_brand_share_of_voice(brands=brands, user_id=user_id)
            )
    except Exception as e:
        return {"success": False, "error": str(e)}


SOCIAL_LISTENING_TOOLS = [
    monitor_brand,
    compare_share_of_voice,
]
