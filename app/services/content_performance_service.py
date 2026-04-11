# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Content Performance Service.

Fetches engagement data for published content and generates
heuristic-based improvement suggestions. Closes the feedback loop
between content creation and content optimisation.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _get_calendar_service():
    """Lazy import to avoid circular dependency chains."""
    from app.services.content_calendar_service import ContentCalendarService

    return ContentCalendarService()


def _get_social_analytics(
    user_id: str,
    platform: str,
    metric_type: str = "account",
    resource_id: str | None = None,
) -> dict[str, Any]:
    """Lazy wrapper around social analytics for patchable test mocking."""
    from app.agents.tools.social_analytics import get_social_analytics

    return get_social_analytics(
        user_id=user_id,
        platform=platform,
        metric_type=metric_type,
        resource_id=resource_id,
    )


# Re-export the lazy helper at module level for convenient patching in tests.
get_social_analytics = _get_social_analytics


def ContentCalendarService():
    """Lazy factory for ContentCalendarService — patchable in tests."""
    from app.services.content_calendar_service import (
        ContentCalendarService as _ContentCalendarService,
    )

    return _ContentCalendarService()


# ---------------------------------------------------------------------------
# Priority ordering for suggestions
# ---------------------------------------------------------------------------
_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


class ContentPerformanceService:
    """Fetches engagement data for published content and generates improvement suggestions."""

    # ------------------------------------------------------------------
    # Published content retrieval
    # ------------------------------------------------------------------

    async def get_published_content(
        self,
        user_id: str,
        since_days: int = 30,
        platform: str | None = None,
    ) -> list[dict]:
        """Fetch published calendar items from ContentCalendarService.

        Args:
            user_id: The user whose content to fetch.
            since_days: Lookback period in days.
            platform: Optional platform filter.

        Returns:
            List of published calendar item dicts.
        """
        start_date = (date.today() - timedelta(days=since_days)).isoformat()

        service = ContentCalendarService()
        items = await service.list_calendar(
            status="published",
            user_id=user_id,
            start_date=start_date,
            platform=platform,
        )
        return items

    # ------------------------------------------------------------------
    # Per-item engagement fetching
    # ------------------------------------------------------------------

    def fetch_engagement_for_item(
        self,
        user_id: str,
        item: dict,
    ) -> dict:
        """Get engagement metrics for a single published item via social_analytics.

        Args:
            user_id: The user's ID.
            item: A calendar item dict (must have ``platform`` and optional
                ``metadata.post_id`` or ``metadata.resource_id``).

        Returns:
            Engagement data dict, or a ``metrics_available: False`` sentinel
            when no post ID is linked.
        """
        platform = item.get("platform")
        if not platform:
            return {"metrics_available": False, "reason": "No platform specified"}

        metadata = item.get("metadata") or {}
        resource_id = metadata.get("post_id") or metadata.get("resource_id")

        if not resource_id:
            return {"metrics_available": False, "reason": "No post ID linked"}

        return get_social_analytics(
            user_id=user_id,
            platform=platform,
            metric_type="post",
            resource_id=resource_id,
        )

    # ------------------------------------------------------------------
    # Suggestion generation (heuristic, no ML)
    # ------------------------------------------------------------------

    def generate_suggestions(
        self,
        items_with_metrics: list[dict],
    ) -> list[dict]:
        """Analyse metrics and generate actionable improvement suggestions.

        Args:
            items_with_metrics: List of dicts each containing ``metrics``
                (likes, shares, comments, impressions) and ``platform``.

        Returns:
            Up to 5 suggestion dicts sorted by priority, each with
            ``category``, ``insight``, ``action``, ``priority``.
        """
        suggestions: list[dict] = []

        # Collect valid metrics
        valid = [
            m
            for m in items_with_metrics
            if m.get("metrics") and m["metrics"].get("metrics_available") is not False
        ]
        if not valid:
            return suggestions

        # Aggregate
        total_likes = sum(m["metrics"].get("likes", 0) for m in valid)
        total_shares = sum(m["metrics"].get("shares", 0) for m in valid)
        total_comments = sum(m["metrics"].get("comments", 0) for m in valid)
        total_impressions = sum(m["metrics"].get("impressions", 0) for m in valid)

        # --- Rule: low overall engagement rate ---
        if total_impressions > 0:
            engagement_rate = (
                (total_likes + total_comments + total_shares) / total_impressions * 100
            )
            if engagement_rate < 2:
                suggestions.append(
                    {
                        "category": "engagement",
                        "insight": "Overall engagement is below average",
                        "action": (
                            "Try asking questions or using polls to boost interaction"
                        ),
                        "priority": "high",
                    }
                )

        # --- Rule: high likes but low shares ---
        if total_likes > 0 and total_shares > 0:
            like_share_ratio = total_likes / total_shares
            if like_share_ratio > 10:
                suggestions.append(
                    {
                        "category": "shareability",
                        "insight": "People like your content but don't share it",
                        "action": (
                            "Add stronger CTAs encouraging shares, "
                            "or create more debate-worthy angles"
                        ),
                        "priority": "medium",
                    }
                )

        # --- Rule: platform outperformance ---
        platform_engagement: dict[str, list[float]] = {}
        for m in valid:
            plat = m.get("platform", "unknown")
            imp = m["metrics"].get("impressions", 0)
            eng = (
                m["metrics"].get("likes", 0)
                + m["metrics"].get("comments", 0)
                + m["metrics"].get("shares", 0)
            )
            rate = (eng / imp * 100) if imp > 0 else 0
            platform_engagement.setdefault(plat, [])
            platform_engagement[plat].append(rate)

        if len(platform_engagement) > 1:
            avg_by_platform = {
                p: sum(rates) / len(rates) for p, rates in platform_engagement.items()
            }
            best = max(avg_by_platform, key=avg_by_platform.get)  # type: ignore[arg-type]
            worst = min(avg_by_platform, key=avg_by_platform.get)  # type: ignore[arg-type]
            if avg_by_platform[best] > 0 and avg_by_platform[worst] > 0:
                ratio = avg_by_platform[best] / avg_by_platform[worst]
                if ratio >= 2:
                    suggestions.append(
                        {
                            "category": "platform",
                            "insight": f"{best.title()} is your strongest channel",
                            "action": (
                                f"Double down on {best.title()} content and consider "
                                f"reducing effort on {worst.title()}"
                            ),
                            "priority": "low",
                        }
                    )

        # Sort by priority and cap at 5
        suggestions.sort(key=lambda s: _PRIORITY_ORDER.get(s["priority"], 99))
        return suggestions[:5]

    # ------------------------------------------------------------------
    # Aggregate metrics
    # ------------------------------------------------------------------

    def compute_aggregate_metrics(
        self,
        items_with_metrics: list[dict],
    ) -> dict:
        """Compute totals and averages across all published items.

        Args:
            items_with_metrics: List of dicts each with ``metrics`` and item info.

        Returns:
            Dict with total_posts, total_likes, total_shares, total_comments,
            total_impressions, avg_engagement_rate, best_performing, worst_performing.
        """
        valid = [
            m
            for m in items_with_metrics
            if m.get("metrics") and m["metrics"].get("metrics_available") is not False
        ]

        if not valid:
            return {
                "total_posts": 0,
                "total_likes": 0,
                "total_shares": 0,
                "total_comments": 0,
                "total_impressions": 0,
                "avg_engagement_rate": 0.0,
                "best_performing": None,
                "worst_performing": None,
            }

        total_likes = sum(m["metrics"].get("likes", 0) for m in valid)
        total_shares = sum(m["metrics"].get("shares", 0) for m in valid)
        total_comments = sum(m["metrics"].get("comments", 0) for m in valid)
        total_impressions = sum(m["metrics"].get("impressions", 0) for m in valid)

        avg_engagement_rate = 0.0
        if total_impressions > 0:
            avg_engagement_rate = round(
                (total_likes + total_comments + total_shares) / total_impressions * 100,
                2,
            )

        # Best/worst by individual engagement
        def _engagement_score(m: dict) -> int:
            met = m.get("metrics", {})
            return met.get("likes", 0) + met.get("comments", 0) + met.get("shares", 0)

        best = max(valid, key=_engagement_score)
        worst = min(valid, key=_engagement_score)

        return {
            "total_posts": len(valid),
            "total_likes": total_likes,
            "total_shares": total_shares,
            "total_comments": total_comments,
            "total_impressions": total_impressions,
            "avg_engagement_rate": avg_engagement_rate,
            "best_performing": {
                "title": best.get("title", ""),
                "platform": best.get("platform", ""),
                "engagement": _engagement_score(best),
            },
            "worst_performing": {
                "title": worst.get("title", ""),
                "platform": worst.get("platform", ""),
                "engagement": _engagement_score(worst),
            },
        }

    # ------------------------------------------------------------------
    # Full performance summary pipeline
    # ------------------------------------------------------------------

    async def get_performance_summary(
        self,
        user_id: str,
        since_days: int = 30,
        platform: str | None = None,
    ) -> dict:
        """Full pipeline: fetch published items, get engagement, generate suggestions.

        Args:
            user_id: The user whose content performance to summarise.
            since_days: Lookback period in days.
            platform: Optional platform filter.

        Returns:
            Dict with success, period_days, published_count, aggregate,
            suggestions, items, and a human-readable message.
        """
        items = await self.get_published_content(
            user_id=user_id,
            since_days=since_days,
            platform=platform,
        )

        if not items:
            return {
                "success": True,
                "published_count": 0,
                "message": (
                    f"No published content found in the last {since_days} days. "
                    "Create and publish content to start tracking performance."
                ),
            }

        # Fetch engagement for each item
        items_with_metrics: list[dict] = []
        for item in items:
            metrics = self.fetch_engagement_for_item(user_id=user_id, item=item)
            items_with_metrics.append(
                {
                    "title": item.get("title", ""),
                    "platform": item.get("platform", ""),
                    "scheduled_date": item.get("scheduled_date", ""),
                    "content_type": item.get("content_type", ""),
                    "metrics": metrics,
                }
            )

        aggregate = self.compute_aggregate_metrics(items_with_metrics)
        suggestions = self.generate_suggestions(items_with_metrics)

        return {
            "success": True,
            "period_days": since_days,
            "published_count": len(items),
            "aggregate": aggregate,
            "suggestions": suggestions,
            "items": items_with_metrics[:10],
            "message": (
                f"Performance summary for your last {len(items)} published "
                f"posts over the past {since_days} days."
            ),
        }
