"""Social Media Analytics Service.

Fetches engagement metrics, audience demographics, and account-level
analytics from connected social platforms via their native APIs.

Platforms supported:
- Twitter/X (API v2) — tweet metrics, account stats
- Instagram (Graph API) — media insights, account insights
- LinkedIn (Marketing API) — share statistics, follower stats
- Facebook (Graph API) — page insights, post metrics
- YouTube (Data API v3) — video analytics, channel stats
- TikTok (Content Posting API) — video insights
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from app.social.connector import get_social_connector

logger = logging.getLogger(__name__)


class SocialAnalyticsService:
    """Fetches analytics from connected social media platforms."""

    def __init__(self):
        self.connector = get_social_connector()

    def _get_token(self, user_id: str, platform: str) -> Optional[str]:
        """Get a valid access token, returning None if unavailable."""
        return self.connector.get_access_token(user_id, platform)

    # ------------------------------------------------------------------
    # Twitter / X
    # ------------------------------------------------------------------

    async def get_twitter_tweet_metrics(
        self,
        user_id: str,
        tweet_ids: List[str],
    ) -> Dict[str, Any]:
        """Fetch public metrics for specific tweets.

        Args:
            user_id: Pikar-AI user ID.
            tweet_ids: List of tweet IDs to fetch metrics for.

        Returns:
            Dict with per-tweet metrics (likes, retweets, replies, impressions).
        """
        token = self._get_token(user_id, "twitter")
        if not token:
            return {"error": "Twitter not connected. Use get_oauth_url to connect."}

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                ids_param = ",".join(tweet_ids[:100])
                resp = await http.get(
                    "https://api.twitter.com/2/tweets",
                    headers={"Authorization": f"Bearer {token}"},
                    params={
                        "ids": ids_param,
                        "tweet.fields": "public_metrics,created_at,organic_metrics",
                    },
                )
                if resp.status_code != 200:
                    return {"error": f"Twitter API error ({resp.status_code}): {resp.text}"}

                data = resp.json().get("data", [])
                return {
                    "success": True,
                    "platform": "twitter",
                    "tweets": [
                        {
                            "tweet_id": t["id"],
                            "text": t.get("text", "")[:100],
                            "created_at": t.get("created_at"),
                            "metrics": t.get("public_metrics", {}),
                        }
                        for t in data
                    ],
                }
        except Exception as e:
            return {"error": f"Twitter analytics failed: {e!s}"}

    async def get_twitter_account_metrics(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """Fetch account-level metrics for the connected Twitter account."""
        token = self._get_token(user_id, "twitter")
        if not token:
            return {"error": "Twitter not connected."}

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                resp = await http.get(
                    "https://api.twitter.com/2/users/me",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"user.fields": "public_metrics,description,created_at"},
                )
                if resp.status_code != 200:
                    return {"error": f"Twitter API error ({resp.status_code}): {resp.text}"}

                user_data = resp.json().get("data", {})
                return {
                    "success": True,
                    "platform": "twitter",
                    "account": {
                        "username": user_data.get("username"),
                        "name": user_data.get("name"),
                        "followers": user_data.get("public_metrics", {}).get("followers_count", 0),
                        "following": user_data.get("public_metrics", {}).get("following_count", 0),
                        "tweet_count": user_data.get("public_metrics", {}).get("tweet_count", 0),
                        "listed_count": user_data.get("public_metrics", {}).get("listed_count", 0),
                    },
                }
        except Exception as e:
            return {"error": f"Twitter account metrics failed: {e!s}"}

    # ------------------------------------------------------------------
    # Instagram
    # ------------------------------------------------------------------

    async def get_instagram_media_insights(
        self,
        user_id: str,
        media_id: str,
    ) -> Dict[str, Any]:
        """Fetch insights for a specific Instagram post/reel."""
        token = self._get_token(user_id, "instagram")
        if not token:
            return {"error": "Instagram not connected."}

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                resp = await http.get(
                    f"https://graph.facebook.com/v18.0/{media_id}/insights",
                    params={
                        "metric": "engagement,impressions,reach,saved",
                        "access_token": token,
                    },
                )
                if resp.status_code != 200:
                    return {"error": f"Instagram API error ({resp.status_code}): {resp.text}"}

                insights = resp.json().get("data", [])
                return {
                    "success": True,
                    "platform": "instagram",
                    "media_id": media_id,
                    "insights": {
                        item["name"]: item["values"][0]["value"]
                        for item in insights
                        if item.get("values")
                    },
                }
        except Exception as e:
            return {"error": f"Instagram insights failed: {e!s}"}

    async def get_instagram_account_insights(
        self,
        user_id: str,
        period: str = "day",
        since_days: int = 30,
    ) -> Dict[str, Any]:
        """Fetch account-level insights for Instagram (followers, reach, impressions)."""
        token = self._get_token(user_id, "instagram")
        if not token:
            return {"error": "Instagram not connected."}

        since_ts = int((datetime.now() - timedelta(days=since_days)).timestamp())
        until_ts = int(datetime.now().timestamp())

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                resp = await http.get(
                    "https://graph.facebook.com/v18.0/me/insights",
                    params={
                        "metric": "impressions,reach,follower_count,profile_views",
                        "period": period,
                        "since": since_ts,
                        "until": until_ts,
                        "access_token": token,
                    },
                )
                if resp.status_code != 200:
                    return {"error": f"Instagram API error ({resp.status_code}): {resp.text}"}

                data = resp.json().get("data", [])
                return {
                    "success": True,
                    "platform": "instagram",
                    "period": f"last_{since_days}_days",
                    "insights": {
                        item["name"]: item.get("values", [{}])[-1].get("value", 0)
                        for item in data
                    },
                }
        except Exception as e:
            return {"error": f"Instagram account insights failed: {e!s}"}

    # ------------------------------------------------------------------
    # LinkedIn
    # ------------------------------------------------------------------

    async def get_linkedin_post_analytics(
        self,
        user_id: str,
        share_urns: List[str],
    ) -> Dict[str, Any]:
        """Fetch analytics for LinkedIn posts (shares).

        Args:
            user_id: Pikar-AI user ID.
            share_urns: List of LinkedIn share URNs.
        """
        token = self._get_token(user_id, "linkedin")
        if not token:
            return {"error": "LinkedIn not connected."}

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                results = []
                for urn in share_urns[:20]:
                    resp = await http.get(
                        "https://api.linkedin.com/v2/socialActions/{urn}".format(urn=urn),
                        headers={
                            "Authorization": f"Bearer {token}",
                            "X-Restli-Protocol-Version": "2.0.0",
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        results.append({
                            "urn": urn,
                            "likes": data.get("likesSummary", {}).get("totalLikes", 0),
                            "comments": data.get("commentsSummary", {}).get("totalFirstLevelComments", 0),
                            "shares": data.get("sharesSummary", {}).get("totalShares", 0) if "sharesSummary" in data else 0,
                        })

                return {
                    "success": True,
                    "platform": "linkedin",
                    "posts": results,
                }
        except Exception as e:
            return {"error": f"LinkedIn analytics failed: {e!s}"}

    async def get_linkedin_follower_stats(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """Fetch LinkedIn profile/page follower statistics."""
        token = self._get_token(user_id, "linkedin")
        if not token:
            return {"error": "LinkedIn not connected."}

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                resp = await http.get(
                    "https://api.linkedin.com/v2/me",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-Restli-Protocol-Version": "2.0.0",
                    },
                )
                if resp.status_code != 200:
                    return {"error": f"LinkedIn API error ({resp.status_code}): {resp.text}"}

                profile = resp.json()
                return {
                    "success": True,
                    "platform": "linkedin",
                    "profile": {
                        "first_name": profile.get("localizedFirstName"),
                        "last_name": profile.get("localizedLastName"),
                        "id": profile.get("id"),
                    },
                }
        except Exception as e:
            return {"error": f"LinkedIn follower stats failed: {e!s}"}

    # ------------------------------------------------------------------
    # Facebook
    # ------------------------------------------------------------------

    async def get_facebook_page_insights(
        self,
        user_id: str,
        since_days: int = 30,
    ) -> Dict[str, Any]:
        """Fetch Facebook page-level insights."""
        token = self._get_token(user_id, "facebook")
        if not token:
            return {"error": "Facebook not connected."}

        since_ts = int((datetime.now() - timedelta(days=since_days)).timestamp())
        until_ts = int(datetime.now().timestamp())

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                resp = await http.get(
                    "https://graph.facebook.com/v18.0/me/insights",
                    params={
                        "metric": "page_impressions,page_engaged_users,page_fans,page_views_total",
                        "since": since_ts,
                        "until": until_ts,
                        "access_token": token,
                    },
                )
                if resp.status_code != 200:
                    return {"error": f"Facebook API error ({resp.status_code}): {resp.text}"}

                data = resp.json().get("data", [])
                return {
                    "success": True,
                    "platform": "facebook",
                    "period": f"last_{since_days}_days",
                    "insights": {
                        item["name"]: item.get("values", [{}])[-1].get("value", 0)
                        for item in data
                    },
                }
        except Exception as e:
            return {"error": f"Facebook page insights failed: {e!s}"}

    async def get_facebook_post_metrics(
        self,
        user_id: str,
        post_id: str,
    ) -> Dict[str, Any]:
        """Fetch metrics for a specific Facebook post."""
        token = self._get_token(user_id, "facebook")
        if not token:
            return {"error": "Facebook not connected."}

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                resp = await http.get(
                    f"https://graph.facebook.com/v18.0/{post_id}",
                    params={
                        "fields": "message,created_time,shares,likes.summary(true),comments.summary(true),insights.metric(post_impressions,post_engaged_users,post_clicks)",
                        "access_token": token,
                    },
                )
                if resp.status_code != 200:
                    return {"error": f"Facebook API error ({resp.status_code}): {resp.text}"}

                data = resp.json()
                return {
                    "success": True,
                    "platform": "facebook",
                    "post_id": post_id,
                    "metrics": {
                        "likes": data.get("likes", {}).get("summary", {}).get("total_count", 0),
                        "comments": data.get("comments", {}).get("summary", {}).get("total_count", 0),
                        "shares": data.get("shares", {}).get("count", 0),
                    },
                }
        except Exception as e:
            return {"error": f"Facebook post metrics failed: {e!s}"}

    # ------------------------------------------------------------------
    # YouTube
    # ------------------------------------------------------------------

    async def get_youtube_video_analytics(
        self,
        user_id: str,
        video_id: str,
    ) -> Dict[str, Any]:
        """Fetch analytics for a specific YouTube video."""
        token = self._get_token(user_id, "youtube")
        if not token:
            return {"error": "YouTube not connected."}

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                resp = await http.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    headers={"Authorization": f"Bearer {token}"},
                    params={
                        "part": "statistics,snippet",
                        "id": video_id,
                    },
                )
                if resp.status_code != 200:
                    return {"error": f"YouTube API error ({resp.status_code}): {resp.text}"}

                items = resp.json().get("items", [])
                if not items:
                    return {"error": f"Video {video_id} not found."}

                video = items[0]
                stats = video.get("statistics", {})
                return {
                    "success": True,
                    "platform": "youtube",
                    "video_id": video_id,
                    "title": video.get("snippet", {}).get("title"),
                    "metrics": {
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comments": int(stats.get("commentCount", 0)),
                        "favorites": int(stats.get("favoriteCount", 0)),
                    },
                }
        except Exception as e:
            return {"error": f"YouTube analytics failed: {e!s}"}

    async def get_youtube_channel_stats(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """Fetch channel-level statistics for the connected YouTube account."""
        token = self._get_token(user_id, "youtube")
        if not token:
            return {"error": "YouTube not connected."}

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                resp = await http.get(
                    "https://www.googleapis.com/youtube/v3/channels",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"part": "statistics,snippet", "mine": "true"},
                )
                if resp.status_code != 200:
                    return {"error": f"YouTube API error ({resp.status_code}): {resp.text}"}

                items = resp.json().get("items", [])
                if not items:
                    return {"error": "No YouTube channel found."}

                ch = items[0]
                stats = ch.get("statistics", {})
                return {
                    "success": True,
                    "platform": "youtube",
                    "channel": {
                        "title": ch.get("snippet", {}).get("title"),
                        "subscribers": int(stats.get("subscriberCount", 0)),
                        "total_views": int(stats.get("viewCount", 0)),
                        "video_count": int(stats.get("videoCount", 0)),
                    },
                }
        except Exception as e:
            return {"error": f"YouTube channel stats failed: {e!s}"}

    # ------------------------------------------------------------------
    # Unified interface
    # ------------------------------------------------------------------

    async def get_platform_analytics(
        self,
        user_id: str,
        platform: str,
        metric_type: str = "account",
        resource_id: Optional[str] = None,
        since_days: int = 30,
    ) -> Dict[str, Any]:
        """Unified analytics interface across all platforms.

        Args:
            user_id: Pikar-AI user ID.
            platform: Platform name (twitter, instagram, linkedin, facebook, youtube).
            metric_type: "account" for account-level or "post" for post-level metrics.
            resource_id: Post/media/video ID (required for post-level metrics).
            since_days: Lookback period for account metrics.

        Returns:
            Platform-specific analytics dict.
        """
        if metric_type == "account":
            dispatch = {
                "twitter": lambda: self.get_twitter_account_metrics(user_id),
                "instagram": lambda: self.get_instagram_account_insights(user_id, since_days=since_days),
                "linkedin": lambda: self.get_linkedin_follower_stats(user_id),
                "facebook": lambda: self.get_facebook_page_insights(user_id, since_days=since_days),
                "youtube": lambda: self.get_youtube_channel_stats(user_id),
            }
        elif metric_type == "post":
            if not resource_id:
                return {"error": "resource_id is required for post-level metrics."}
            dispatch = {
                "twitter": lambda: self.get_twitter_tweet_metrics(user_id, [resource_id]),
                "instagram": lambda: self.get_instagram_media_insights(user_id, resource_id),
                "linkedin": lambda: self.get_linkedin_post_analytics(user_id, [resource_id]),
                "facebook": lambda: self.get_facebook_post_metrics(user_id, resource_id),
                "youtube": lambda: self.get_youtube_video_analytics(user_id, resource_id),
            }
        else:
            return {"error": f"Unknown metric_type: {metric_type}. Use 'account' or 'post'."}

        handler = dispatch.get(platform)
        if not handler:
            return {"error": f"Analytics not supported for platform: {platform}"}

        return await handler()


# Singleton
_analytics_service: Optional[SocialAnalyticsService] = None


def get_social_analytics_service() -> SocialAnalyticsService:
    """Return singleton SocialAnalyticsService instance."""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = SocialAnalyticsService()
    return _analytics_service
