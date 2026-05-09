# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for app.social.analytics SocialAnalyticsService (Plan 108-04 backfill).

Per-platform success-path + no-token + 4xx-error coverage for:

- Twitter: tweet metrics, account metrics
- Instagram: media insights, account insights
- LinkedIn: post analytics, follower stats
- Facebook: page insights, post metrics
- YouTube: video analytics, channel stats

Plus the unified ``get_platform_analytics`` dispatcher (account, post,
unknown metric_type, missing resource_id, unsupported platform).

Pattern: ``respx`` for upstream HTTP, ``MagicMock`` connector with
``AsyncMock`` ``get_access_token``.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx


def _make_service(token: str | None = "AT") -> Any:
    from app.social.analytics import SocialAnalyticsService

    service = SocialAnalyticsService.__new__(SocialAnalyticsService)
    connector = MagicMock()
    connector.get_access_token = AsyncMock(return_value=token)
    service.connector = connector
    return service


# ---------------------------------------------------------------------------
# Twitter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_twitter_tweet_metrics_success():
    service = _make_service()
    respx.get("https://api.twitter.com/2/tweets").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "T1",
                        "text": "hello world",
                        "created_at": "2026-01-01",
                        "public_metrics": {"like_count": 5},
                    }
                ]
            },
        )
    )
    result = await service.get_twitter_tweet_metrics("u1", ["T1"])
    assert result["success"] is True
    assert result["tweets"][0]["tweet_id"] == "T1"
    assert result["tweets"][0]["metrics"]["like_count"] == 5


@pytest.mark.asyncio
async def test_twitter_tweet_metrics_no_token():
    service = _make_service(token=None)
    result = await service.get_twitter_tweet_metrics("u1", ["T1"])
    assert "error" in result
    assert "twitter" in result["error"].lower()


@pytest.mark.asyncio
@respx.mock
async def test_twitter_tweet_metrics_4xx():
    service = _make_service()
    respx.get("https://api.twitter.com/2/tweets").mock(
        return_value=httpx.Response(429, text="rate limit")
    )
    result = await service.get_twitter_tweet_metrics("u1", ["T1"])
    assert "error" in result
    assert "429" in result["error"]


@pytest.mark.asyncio
@respx.mock
async def test_twitter_account_metrics_success():
    service = _make_service()
    respx.get("https://api.twitter.com/2/users/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "username": "alice",
                    "name": "Alice",
                    "public_metrics": {
                        "followers_count": 100,
                        "following_count": 50,
                        "tweet_count": 200,
                        "listed_count": 5,
                    },
                }
            },
        )
    )
    result = await service.get_twitter_account_metrics("u1")
    assert result["success"] is True
    assert result["account"]["followers"] == 100


@pytest.mark.asyncio
async def test_twitter_account_metrics_no_token():
    service = _make_service(token=None)
    result = await service.get_twitter_account_metrics("u1")
    assert "error" in result


@pytest.mark.asyncio
@respx.mock
async def test_twitter_account_metrics_4xx():
    service = _make_service()
    respx.get("https://api.twitter.com/2/users/me").mock(
        return_value=httpx.Response(401, text="unauth")
    )
    result = await service.get_twitter_account_metrics("u1")
    assert "error" in result and "401" in result["error"]


# ---------------------------------------------------------------------------
# Instagram
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_instagram_media_insights_success():
    service = _make_service()
    respx.get("https://graph.facebook.com/v18.0/IG-1/insights").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {"name": "engagement", "values": [{"value": 42}]},
                    {"name": "reach", "values": [{"value": 1000}]},
                ]
            },
        )
    )
    result = await service.get_instagram_media_insights("u1", "IG-1")
    assert result["success"] is True
    assert result["insights"]["engagement"] == 42
    assert result["insights"]["reach"] == 1000


@pytest.mark.asyncio
async def test_instagram_media_insights_no_token():
    service = _make_service(token=None)
    result = await service.get_instagram_media_insights("u1", "IG-1")
    assert "error" in result


@pytest.mark.asyncio
@respx.mock
async def test_instagram_media_insights_4xx():
    service = _make_service()
    respx.get("https://graph.facebook.com/v18.0/IG-1/insights").mock(
        return_value=httpx.Response(404, text="not found")
    )
    result = await service.get_instagram_media_insights("u1", "IG-1")
    assert "error" in result and "404" in result["error"]


@pytest.mark.asyncio
@respx.mock
async def test_instagram_account_insights_success():
    service = _make_service()
    respx.get("https://graph.facebook.com/v18.0/me/insights").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {"name": "impressions", "values": [{"value": 10}, {"value": 30}]},
                    {"name": "reach", "values": [{"value": 5}]},
                ]
            },
        )
    )
    result = await service.get_instagram_account_insights("u1")
    assert result["success"] is True
    assert result["insights"]["impressions"] == 30  # last value wins
    assert result["insights"]["reach"] == 5


@pytest.mark.asyncio
async def test_instagram_account_insights_no_token():
    service = _make_service(token=None)
    result = await service.get_instagram_account_insights("u1")
    assert "error" in result


@pytest.mark.asyncio
@respx.mock
async def test_instagram_account_insights_4xx():
    service = _make_service()
    respx.get("https://graph.facebook.com/v18.0/me/insights").mock(
        return_value=httpx.Response(403)
    )
    result = await service.get_instagram_account_insights("u1")
    assert "error" in result and "403" in result["error"]


# ---------------------------------------------------------------------------
# LinkedIn
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_linkedin_post_analytics_success():
    service = _make_service()
    urn = "urn:li:share:abc"
    respx.get(f"https://api.linkedin.com/v2/socialActions/{urn}").mock(
        return_value=httpx.Response(
            200,
            json={
                "likesSummary": {"totalLikes": 7},
                "commentsSummary": {"totalFirstLevelComments": 2},
                "sharesSummary": {"totalShares": 1},
            },
        )
    )
    result = await service.get_linkedin_post_analytics("u1", [urn])
    assert result["success"] is True
    assert result["posts"][0]["likes"] == 7
    assert result["posts"][0]["comments"] == 2
    assert result["posts"][0]["shares"] == 1


@pytest.mark.asyncio
async def test_linkedin_post_analytics_no_token():
    service = _make_service(token=None)
    result = await service.get_linkedin_post_analytics("u1", ["urn:li:share:x"])
    assert "error" in result


@pytest.mark.asyncio
@respx.mock
async def test_linkedin_follower_stats_success():
    service = _make_service()
    respx.get("https://api.linkedin.com/v2/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "localizedFirstName": "Ada",
                "localizedLastName": "Lovelace",
                "id": "ada-99",
            },
        )
    )
    result = await service.get_linkedin_follower_stats("u1")
    assert result["success"] is True
    assert result["profile"]["first_name"] == "Ada"


@pytest.mark.asyncio
async def test_linkedin_follower_stats_no_token():
    service = _make_service(token=None)
    result = await service.get_linkedin_follower_stats("u1")
    assert "error" in result


@pytest.mark.asyncio
@respx.mock
async def test_linkedin_follower_stats_4xx():
    service = _make_service()
    respx.get("https://api.linkedin.com/v2/me").mock(
        return_value=httpx.Response(401)
    )
    result = await service.get_linkedin_follower_stats("u1")
    assert "error" in result


# ---------------------------------------------------------------------------
# Facebook
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_facebook_page_insights_success():
    service = _make_service()
    respx.get("https://graph.facebook.com/v18.0/me/insights").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {"name": "page_fans", "values": [{"value": 1234}]},
                ]
            },
        )
    )
    result = await service.get_facebook_page_insights("u1")
    assert result["success"] is True
    assert result["insights"]["page_fans"] == 1234


@pytest.mark.asyncio
async def test_facebook_page_insights_no_token():
    service = _make_service(token=None)
    result = await service.get_facebook_page_insights("u1")
    assert "error" in result


@pytest.mark.asyncio
@respx.mock
async def test_facebook_page_insights_4xx():
    service = _make_service()
    respx.get("https://graph.facebook.com/v18.0/me/insights").mock(
        return_value=httpx.Response(400)
    )
    result = await service.get_facebook_page_insights("u1")
    assert "error" in result


@pytest.mark.asyncio
@respx.mock
async def test_facebook_post_metrics_success():
    service = _make_service()
    respx.get("https://graph.facebook.com/v18.0/POST-1").mock(
        return_value=httpx.Response(
            200,
            json={
                "likes": {"summary": {"total_count": 10}},
                "comments": {"summary": {"total_count": 3}},
                "shares": {"count": 2},
            },
        )
    )
    result = await service.get_facebook_post_metrics("u1", "POST-1")
    assert result["success"] is True
    assert result["metrics"]["likes"] == 10
    assert result["metrics"]["shares"] == 2


@pytest.mark.asyncio
async def test_facebook_post_metrics_no_token():
    service = _make_service(token=None)
    result = await service.get_facebook_post_metrics("u1", "POST-1")
    assert "error" in result


@pytest.mark.asyncio
@respx.mock
async def test_facebook_post_metrics_4xx():
    service = _make_service()
    respx.get("https://graph.facebook.com/v18.0/POST-1").mock(
        return_value=httpx.Response(404)
    )
    result = await service.get_facebook_post_metrics("u1", "POST-1")
    assert "error" in result


# ---------------------------------------------------------------------------
# YouTube
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_youtube_video_analytics_success():
    service = _make_service()
    respx.get("https://www.googleapis.com/youtube/v3/videos").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "snippet": {"title": "My Video"},
                        "statistics": {
                            "viewCount": "1000",
                            "likeCount": "50",
                            "commentCount": "10",
                            "favoriteCount": "0",
                        },
                    }
                ]
            },
        )
    )
    result = await service.get_youtube_video_analytics("u1", "VID-1")
    assert result["success"] is True
    assert result["metrics"]["views"] == 1000
    assert result["metrics"]["likes"] == 50


@pytest.mark.asyncio
async def test_youtube_video_analytics_no_token():
    service = _make_service(token=None)
    result = await service.get_youtube_video_analytics("u1", "V")
    assert "error" in result


@pytest.mark.asyncio
@respx.mock
async def test_youtube_video_analytics_no_items():
    service = _make_service()
    respx.get("https://www.googleapis.com/youtube/v3/videos").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    result = await service.get_youtube_video_analytics("u1", "V-X")
    assert "error" in result
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
@respx.mock
async def test_youtube_video_analytics_4xx():
    service = _make_service()
    respx.get("https://www.googleapis.com/youtube/v3/videos").mock(
        return_value=httpx.Response(403)
    )
    result = await service.get_youtube_video_analytics("u1", "V-X")
    assert "error" in result


@pytest.mark.asyncio
@respx.mock
async def test_youtube_channel_stats_success():
    service = _make_service()
    respx.get("https://www.googleapis.com/youtube/v3/channels").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "snippet": {"title": "MyChannel"},
                        "statistics": {
                            "subscriberCount": "999",
                            "viewCount": "5000",
                            "videoCount": "30",
                        },
                    }
                ]
            },
        )
    )
    result = await service.get_youtube_channel_stats("u1")
    assert result["success"] is True
    assert result["channel"]["subscribers"] == 999
    assert result["channel"]["total_views"] == 5000


@pytest.mark.asyncio
async def test_youtube_channel_stats_no_token():
    service = _make_service(token=None)
    result = await service.get_youtube_channel_stats("u1")
    assert "error" in result


@pytest.mark.asyncio
@respx.mock
async def test_youtube_channel_stats_no_items():
    service = _make_service()
    respx.get("https://www.googleapis.com/youtube/v3/channels").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    result = await service.get_youtube_channel_stats("u1")
    assert "error" in result


@pytest.mark.asyncio
@respx.mock
async def test_youtube_channel_stats_4xx():
    service = _make_service()
    respx.get("https://www.googleapis.com/youtube/v3/channels").mock(
        return_value=httpx.Response(500)
    )
    result = await service.get_youtube_channel_stats("u1")
    assert "error" in result


# ---------------------------------------------------------------------------
# Unified dispatcher
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_platform_analytics_account_dispatch_twitter():
    service = _make_service()
    fake_result = {"success": True, "platform": "twitter"}

    async def fake_account(_uid):
        return fake_result

    service.get_twitter_account_metrics = fake_account
    result = await service.get_platform_analytics("u1", "twitter", "account")
    assert result == fake_result


@pytest.mark.asyncio
async def test_get_platform_analytics_post_requires_resource_id():
    service = _make_service()
    result = await service.get_platform_analytics("u1", "twitter", "post")
    assert "error" in result
    assert "resource_id" in result["error"]


@pytest.mark.asyncio
async def test_get_platform_analytics_unknown_metric_type():
    service = _make_service()
    result = await service.get_platform_analytics("u1", "twitter", "garbage")
    assert "error" in result


@pytest.mark.asyncio
async def test_get_platform_analytics_unsupported_platform():
    service = _make_service()
    result = await service.get_platform_analytics("u1", "myspace", "account")
    assert "error" in result
    assert "myspace" in result["error"]


@pytest.mark.asyncio
async def test_get_platform_analytics_post_dispatch_youtube():
    service = _make_service()

    async def fake_video(uid, vid):
        return {"success": True, "video_id": vid}

    service.get_youtube_video_analytics = fake_video
    result = await service.get_platform_analytics(
        "u1", "youtube", "post", resource_id="V-1"
    )
    assert result["success"] is True
    assert result["video_id"] == "V-1"


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


def test_get_social_analytics_service_returns_singleton():
    from app.social import analytics

    # Clear any previously-cached instance and avoid invoking the real
    # connector singleton (would require Supabase env vars).
    analytics._analytics_service = None
    with patch.object(
        analytics, "SocialAnalyticsService", lambda: MagicMock()
    ):
        a = analytics.get_social_analytics_service()
        b = analytics.get_social_analytics_service()
    assert a is b
    analytics._analytics_service = None
