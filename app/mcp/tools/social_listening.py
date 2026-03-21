"""Social Listening Tool - Brand/keyword monitoring across platforms.

Monitors brand mentions, keywords, and competitor activity across
web sources, social platforms, and forums using a polling approach:
- Tavily web search for blog/news mentions
- Twitter API v2 recent search for tweet mentions
- Reddit API for subreddit/forum discussions

Provides sentiment analysis summaries and share-of-voice comparison.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.mcp.config import get_mcp_config
from app.mcp.security.audit_logger import log_mcp_call
from app.mcp.security.external_call_guard import protect_text_payload

logger = logging.getLogger(__name__)


class SocialListeningTool:
    """Monitors brand mentions and keywords across web and social platforms."""

    def __init__(self):
        self.config = get_mcp_config()

    async def search_web_mentions(
        self,
        query: str,
        max_results: int = 10,
    ) -> dict[str, Any]:
        """Search for brand/keyword mentions across the web using Tavily.

        Args:
            query: Brand name or keywords to search for.
            max_results: Number of results.

        Returns:
            Dict with web mentions (articles, blogs, news).
        """
        if not self.config.is_tavily_configured():
            return {
                "success": False,
                "error": "Tavily API not configured.",
                "mentions": [],
            }

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.config.tavily_base_url}/search",
                    headers={
                        "Authorization": f"Bearer {self.config.tavily_api_key}",
                    },
                    json={
                        "query": query,
                        "max_results": max_results,
                        "search_depth": "advanced",
                        "include_answer": True,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                duration_ms = int((time.time() - start_time) * 1000)

                mentions = [
                    {
                        "source": "web",
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", "")[:500],
                        "score": r.get("score", 0),
                        "published_date": r.get("published_date"),
                    }
                    for r in data.get("results", [])
                ]

                return {
                    "success": True,
                    "query": query,
                    "source": "web",
                    "total_mentions": len(mentions),
                    "mentions": mentions,
                    "summary": data.get("answer", ""),
                    "duration_ms": duration_ms,
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Web mention search failed: {e!s}",
                "mentions": [],
            }

    async def search_twitter_mentions(
        self,
        query: str,
        max_results: int = 20,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Search recent tweets mentioning a brand or keyword.

        Uses Twitter API v2 recent search (last 7 days).

        Args:
            query: Search query (brand name, keyword, hashtag).
            max_results: Number of tweets (10-100).
            user_id: Pikar-AI user ID for OAuth token.

        Returns:
            Dict with tweet mentions and engagement metrics.
        """
        token = None
        if user_id:
            from app.social.connector import get_social_connector

            connector = get_social_connector()
            token = connector.get_access_token(user_id, "twitter")

        if not token:
            return {
                "success": False,
                "error": "Twitter not connected. Connect via OAuth to search mentions.",
                "mentions": [],
            }

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    "https://api.twitter.com/2/tweets/search/recent",
                    headers={"Authorization": f"Bearer {token}"},
                    params={
                        "query": f"{query} -is:retweet",
                        "max_results": min(max(max_results, 10), 100),
                        "tweet.fields": "created_at,public_metrics,author_id,lang",
                    },
                )
                duration_ms = int((time.time() - start_time) * 1000)

                if resp.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Twitter API error ({resp.status_code}): {resp.text}",
                        "mentions": [],
                    }

                data = resp.json()
                tweets = data.get("data", [])

                mentions = [
                    {
                        "source": "twitter",
                        "tweet_id": t["id"],
                        "text": t.get("text", ""),
                        "created_at": t.get("created_at"),
                        "author_id": t.get("author_id"),
                        "metrics": t.get("public_metrics", {}),
                        "lang": t.get("lang"),
                    }
                    for t in tweets
                ]

                total_engagement = sum(
                    m.get("metrics", {}).get("like_count", 0)
                    + m.get("metrics", {}).get("retweet_count", 0)
                    + m.get("metrics", {}).get("reply_count", 0)
                    for m in mentions
                )

                return {
                    "success": True,
                    "query": query,
                    "source": "twitter",
                    "total_mentions": len(mentions),
                    "total_engagement": total_engagement,
                    "mentions": mentions,
                    "meta": data.get("meta", {}),
                    "duration_ms": duration_ms,
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Twitter search failed: {e!s}",
                "mentions": [],
            }

    async def search_reddit_mentions(
        self,
        query: str,
        subreddits: list[str] | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Search Reddit for brand/keyword mentions.

        Uses Reddit's public search API (no auth required for public posts).

        Args:
            query: Search query.
            subreddits: Optional list of subreddits to search within.
            limit: Number of results (max 100).

        Returns:
            Dict with Reddit post/comment mentions.
        """
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if subreddits:
                    search_url = (
                        f"https://www.reddit.com/r/{'+'.join(subreddits)}/search.json"
                    )
                else:
                    search_url = "https://www.reddit.com/search.json"

                resp = await client.get(
                    search_url,
                    params={
                        "q": query,
                        "limit": min(limit, 100),
                        "sort": "relevance",
                        "t": "month",
                    },
                    headers={"User-Agent": "PikarAI/1.0 (Social Listening Bot)"},
                )
                duration_ms = int((time.time() - start_time) * 1000)

                if resp.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Reddit API error ({resp.status_code})",
                        "mentions": [],
                    }

                data = resp.json()
                posts = data.get("data", {}).get("children", [])

                mentions = [
                    {
                        "source": "reddit",
                        "post_id": p["data"].get("id"),
                        "title": p["data"].get("title", ""),
                        "subreddit": p["data"].get("subreddit"),
                        "url": f"https://reddit.com{p['data'].get('permalink', '')}",
                        "score": p["data"].get("score", 0),
                        "num_comments": p["data"].get("num_comments", 0),
                        "created_utc": p["data"].get("created_utc"),
                        "selftext": p["data"].get("selftext", "")[:300],
                    }
                    for p in posts
                    if p.get("kind") == "t3"
                ]

                return {
                    "success": True,
                    "query": query,
                    "source": "reddit",
                    "subreddits": subreddits,
                    "total_mentions": len(mentions),
                    "mentions": mentions,
                    "duration_ms": duration_ms,
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Reddit search failed: {e!s}",
                "mentions": [],
            }

    async def monitor_brand(
        self,
        brand_name: str,
        keywords: list[str] | None = None,
        platforms: list[str] | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Run a comprehensive brand monitoring scan across all available platforms.

        Combines web search, Twitter, and Reddit to find all recent
        mentions of a brand or keywords.

        Args:
            brand_name: The primary brand name to monitor.
            keywords: Additional keywords/phrases to track.
            platforms: Which platforms to search (default: all available).
                       Options: "web", "twitter", "reddit".
            user_id: Pikar-AI user ID (needed for Twitter).

        Returns:
            Unified mention report with cross-platform analysis.
        """
        if platforms is None:
            platforms = ["web", "twitter", "reddit"]

        all_queries = [brand_name]
        if keywords:
            all_queries.extend(keywords)

        combined_query = " OR ".join(f'"{q}"' for q in all_queries)
        start_time = time.time()

        results: dict[str, Any] = {
            "brand": brand_name,
            "keywords": keywords or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "platforms_searched": [],
            "total_mentions": 0,
            "mentions_by_platform": {},
            "all_mentions": [],
        }

        # Web mentions
        if "web" in platforms:
            web_result = await self.search_web_mentions(combined_query)
            results["platforms_searched"].append("web")
            if web_result.get("success"):
                results["mentions_by_platform"]["web"] = web_result.get(
                    "total_mentions", 0
                )
                results["all_mentions"].extend(web_result.get("mentions", []))
                results["web_summary"] = web_result.get("summary", "")

        # Twitter mentions
        if "twitter" in platforms and user_id:
            twitter_result = await self.search_twitter_mentions(
                combined_query,
                user_id=user_id,
            )
            results["platforms_searched"].append("twitter")
            if twitter_result.get("success"):
                results["mentions_by_platform"]["twitter"] = twitter_result.get(
                    "total_mentions", 0
                )
                results["all_mentions"].extend(twitter_result.get("mentions", []))
                results["twitter_engagement"] = twitter_result.get(
                    "total_engagement", 0
                )

        # Reddit mentions
        if "reddit" in platforms:
            reddit_result = await self.search_reddit_mentions(brand_name)
            results["platforms_searched"].append("reddit")
            if reddit_result.get("success"):
                results["mentions_by_platform"]["reddit"] = reddit_result.get(
                    "total_mentions", 0
                )
                results["all_mentions"].extend(reddit_result.get("mentions", []))

        results["total_mentions"] = sum(results["mentions_by_platform"].values())
        results["duration_ms"] = int((time.time() - start_time) * 1000)
        results["success"] = True

        return results

    async def compare_share_of_voice(
        self,
        brands: list[str],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Compare share of voice across multiple brands/competitors.

        Searches for each brand across web and social platforms, then
        calculates relative mention volume.

        Args:
            brands: List of brand names to compare.
            user_id: Pikar-AI user ID.

        Returns:
            Dict with per-brand mention counts and share-of-voice percentages.
        """
        if len(brands) < 2:
            return {"error": "Provide at least 2 brands to compare."}

        start_time = time.time()
        brand_results = {}

        for brand in brands[:10]:
            result = await self.monitor_brand(
                brand_name=brand,
                platforms=["web", "reddit"],
                user_id=user_id,
            )
            brand_results[brand] = {
                "total_mentions": result.get("total_mentions", 0),
                "by_platform": result.get("mentions_by_platform", {}),
            }

        total_all = sum(br["total_mentions"] for br in brand_results.values())
        for brand, data in brand_results.items():
            data["share_of_voice_pct"] = (
                round(data["total_mentions"] / total_all * 100, 1)
                if total_all > 0
                else 0
            )

        duration_ms = int((time.time() - start_time) * 1000)

        return {
            "success": True,
            "brands_compared": brands,
            "results": brand_results,
            "total_mentions_all": total_all,
            "leader": max(
                brand_results, key=lambda b: brand_results[b]["total_mentions"]
            )
            if brand_results
            else None,
            "duration_ms": duration_ms,
        }


# Singleton
_listening_tool: SocialListeningTool | None = None


def _get_listening_tool() -> SocialListeningTool:
    """Get the singleton social listening tool instance."""
    global _listening_tool
    if _listening_tool is None:
        _listening_tool = SocialListeningTool()
    return _listening_tool


async def monitor_brand_mentions(
    brand_name: str,
    keywords: list[str] | None = None,
    platforms: list[str] | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Monitor brand mentions across web, social media, and forums."""
    guard = protect_text_payload(brand_name, field_name="brand_name")
    tool = _get_listening_tool()
    result = await tool.monitor_brand(
        brand_name=guard.outbound_value,
        keywords=keywords,
        platforms=platforms,
        user_id=user_id,
    )

    log_mcp_call(
        tool_name="social_listening",
        query_sanitized=guard.audit_value,
        success=result.get("success", False),
        response_status="success" if result.get("success") else "error",
        user_id=user_id,
        error_message=result.get("error"),
        duration_ms=result.get("duration_ms"),
        metadata={
            **guard.metadata,
            "total_mentions": result.get("total_mentions", 0),
            "platforms": result.get("platforms_searched", []),
        },
    )
    return result


async def compare_brand_share_of_voice(
    brands: list[str],
    user_id: str | None = None,
) -> dict[str, Any]:
    """Compare share of voice (mention volume) between brands."""
    tool = _get_listening_tool()
    result = await tool.compare_share_of_voice(brands=brands, user_id=user_id)

    log_mcp_call(
        tool_name="share_of_voice",
        query_sanitized=f"sov_comparison:{','.join(brands[:5])}",
        success=result.get("success", False),
        response_status="success" if result.get("success") else "error",
        user_id=user_id,
        duration_ms=result.get("duration_ms"),
    )
    return result
