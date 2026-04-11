"""Unit tests for ContentPerformanceService."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.content_performance_service import ContentPerformanceService


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

def _published_items():
    """Return sample published calendar items."""
    return [
        {
            "id": "item-1",
            "title": "Product Launch Post",
            "platform": "instagram",
            "status": "published",
            "scheduled_date": "2026-04-01",
            "content_type": "social",
            "metadata": {"post_id": "ig-post-123"},
        },
        {
            "id": "item-2",
            "title": "Thought Leadership Article",
            "platform": "linkedin",
            "status": "published",
            "scheduled_date": "2026-04-03",
            "content_type": "blog",
            "metadata": {"post_id": "li-post-456"},
        },
        {
            "id": "item-3",
            "title": "Quick Update",
            "platform": "twitter",
            "status": "published",
            "scheduled_date": "2026-04-05",
            "content_type": "social",
            "metadata": {},  # no post_id
        },
    ]


def _engagement_high_likes_low_shares():
    """Engagement metrics where likes are high but shares are low."""
    return {
        "likes": 500,
        "shares": 10,
        "comments": 80,
        "impressions": 10000,
    }


def _engagement_low_overall():
    """Engagement metrics with low overall engagement."""
    return {
        "likes": 5,
        "shares": 1,
        "comments": 2,
        "impressions": 5000,
    }


# ---------------------------------------------------------------------------
# Test 1: get_published_content returns only published items for the user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.services.content_performance_service.ContentCalendarService")
async def test_get_published_content_returns_only_published(mock_calendar_cls):
    """get_published_content returns only calendar items with status='published' for the user."""
    mock_service = AsyncMock()
    mock_calendar_cls.return_value = mock_service
    mock_service.list_calendar.return_value = _published_items()

    svc = ContentPerformanceService()
    result = await svc.get_published_content(user_id="user-1", since_days=30)

    mock_service.list_calendar.assert_called_once()
    call_kwargs = mock_service.list_calendar.call_args[1]
    assert call_kwargs["status"] == "published"
    assert call_kwargs["user_id"] == "user-1"
    assert len(result) == 3


# ---------------------------------------------------------------------------
# Test 2: fetch_engagement_for_item calls get_social_analytics with metric_type="post"
# ---------------------------------------------------------------------------

@patch("app.services.content_performance_service.get_social_analytics")
def test_fetch_engagement_calls_social_analytics_with_post_type(mock_analytics):
    """fetch_engagement_for_item calls get_social_analytics with metric_type='post' for each item."""
    mock_analytics.return_value = _engagement_high_likes_low_shares()

    svc = ContentPerformanceService()
    item = _published_items()[0]  # has post_id in metadata
    result = svc.fetch_engagement_for_item(user_id="user-1", item=item)

    mock_analytics.assert_called_once_with(
        user_id="user-1",
        platform="instagram",
        metric_type="post",
        resource_id="ig-post-123",
    )
    assert result["likes"] == 500


# ---------------------------------------------------------------------------
# Test 2b: fetch_engagement_for_item without resource_id returns unavailable
# ---------------------------------------------------------------------------

@patch("app.services.content_performance_service.get_social_analytics")
def test_fetch_engagement_without_resource_id(mock_analytics):
    """fetch_engagement_for_item without post_id returns metrics_available=False."""
    svc = ContentPerformanceService()
    item = _published_items()[2]  # no post_id in metadata
    result = svc.fetch_engagement_for_item(user_id="user-1", item=item)

    mock_analytics.assert_not_called()
    assert result["metrics_available"] is False


# ---------------------------------------------------------------------------
# Test 3: generate_suggestions with high likes but low shares
# ---------------------------------------------------------------------------

def test_generate_suggestions_high_likes_low_shares():
    """High likes but low shares suggests CTA for sharing."""
    svc = ContentPerformanceService()
    items_with_metrics = [
        {
            "title": "Popular Post",
            "platform": "instagram",
            "metrics": _engagement_high_likes_low_shares(),
        },
    ]
    suggestions = svc.generate_suggestions(items_with_metrics)

    assert len(suggestions) >= 1
    categories = [s["category"] for s in suggestions]
    assert "shareability" in categories
    share_suggestion = next(s for s in suggestions if s["category"] == "shareability")
    assert "call-to-action" in share_suggestion["action"].lower() or "cta" in share_suggestion["action"].lower()


# ---------------------------------------------------------------------------
# Test 4: generate_suggestions with low engagement overall
# ---------------------------------------------------------------------------

def test_generate_suggestions_low_engagement():
    """Low overall engagement suggests timing changes and format adjustments."""
    svc = ContentPerformanceService()
    items_with_metrics = [
        {
            "title": "Low Performer 1",
            "platform": "twitter",
            "metrics": _engagement_low_overall(),
        },
        {
            "title": "Low Performer 2",
            "platform": "twitter",
            "metrics": _engagement_low_overall(),
        },
    ]
    suggestions = svc.generate_suggestions(items_with_metrics)

    assert len(suggestions) >= 1
    categories = [s["category"] for s in suggestions]
    assert "engagement" in categories
    eng_suggestion = next(s for s in suggestions if s["category"] == "engagement")
    assert eng_suggestion["priority"] == "high"


# ---------------------------------------------------------------------------
# Test 5: get_performance_summary returns structured summary
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.services.content_performance_service.get_social_analytics")
@patch("app.services.content_performance_service.ContentCalendarService")
async def test_get_performance_summary_structured(mock_calendar_cls, mock_analytics):
    """get_performance_summary returns summary with content_items, aggregate_metrics, suggestions."""
    mock_service = AsyncMock()
    mock_calendar_cls.return_value = mock_service
    mock_service.list_calendar.return_value = _published_items()[:2]  # 2 items with post_ids
    mock_analytics.return_value = _engagement_high_likes_low_shares()

    svc = ContentPerformanceService()
    result = await svc.get_performance_summary(user_id="user-1", since_days=30)

    assert result["success"] is True
    assert result["published_count"] == 2
    assert "aggregate" in result
    assert "suggestions" in result
    assert "items" in result
    assert result["aggregate"]["total_posts"] == 2
    assert result["aggregate"]["total_likes"] == 1000  # 500 * 2


# ---------------------------------------------------------------------------
# Test 6: get_performance_summary with no published content
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.services.content_performance_service.ContentCalendarService")
async def test_get_performance_summary_empty(mock_calendar_cls):
    """No published content returns helpful empty-state message."""
    mock_service = AsyncMock()
    mock_calendar_cls.return_value = mock_service
    mock_service.list_calendar.return_value = []

    svc = ContentPerformanceService()
    result = await svc.get_performance_summary(user_id="user-1", since_days=30)

    assert result["success"] is True
    assert result["published_count"] == 0
    assert "No published content" in result["message"]
