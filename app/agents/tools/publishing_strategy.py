"""Publishing Strategy Tools — Intelligent content distribution planning.

Provides tools to create comprehensive publishing strategies that go beyond
simple "post to social media." Each strategy includes platform-specific captions,
optimal posting times, hashtag strategies, multi-day distribution calendars,
and cross-platform adaptation notes.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _get_supabase_client():
    """Get Supabase client from centralized service."""
    try:
        from app.services.supabase import get_service_client

        return get_service_client()
    except (ImportError, ConnectionError):
        return None


def _get_request_user_id() -> str | None:
    """Get the current user ID from the request context."""
    try:
        from app.services.request_context import get_current_user_id

        return get_current_user_id()
    except (ImportError, AttributeError):
        return None


# Platform-specific best practices for the agent to reference
PLATFORM_GUIDELINES = {
    "instagram": {
        "optimal_times": "Mon-Fri 9am, 12pm, 3pm; Sat 11am (local time of audience)",
        "hashtag_count": "5-15 relevant hashtags, mix of broad and niche",
        "caption_style": "Hook in first line, line breaks for readability, CTA at end",
        "format_notes": "Reels > Carousels > Static for reach. 9:16 vertical for Reels.",
        "max_caption_length": 2200,
    },
    "tiktok": {
        "optimal_times": "Tue-Thu 10am, 2pm, 7pm; Sun 1pm (local time)",
        "hashtag_count": "3-5 trending + niche hashtags",
        "caption_style": "Short, punchy, casual. Hook viewers in first 3 seconds.",
        "format_notes": "9:16 vertical. 15-60s sweet spot. Use trending audio.",
        "max_caption_length": 300,
    },
    "youtube": {
        "optimal_times": "Thu-Sat 2pm-4pm (audience timezone)",
        "hashtag_count": "3-5 in description, NOT in title",
        "caption_style": "SEO-optimized title (60 chars max), description with timestamps",
        "format_notes": "16:9 horizontal. Custom thumbnail critical. Chapters boost retention.",
        "max_caption_length": 5000,
    },
    "linkedin": {
        "optimal_times": "Tue-Thu 8am-10am, 12pm (business hours)",
        "hashtag_count": "3-5 professional hashtags",
        "caption_style": "Professional but human. Lead with insight or hot take. Tag people.",
        "format_notes": "Text posts outperform images. Carousels (PDF) for thought leadership.",
        "max_caption_length": 3000,
    },
    "twitter": {
        "optimal_times": "Mon-Fri 8am-10am, 6pm-9pm",
        "hashtag_count": "1-2 max, organic integration",
        "caption_style": "Concise, witty, thread-worthy. Quote tweets for engagement.",
        "format_notes": "280 chars. Thread for long content. Images boost engagement 150%.",
        "max_caption_length": 280,
    },
    "facebook": {
        "optimal_times": "Wed-Fri 1pm-4pm",
        "hashtag_count": "1-3 max",
        "caption_style": "Conversational, question-driven. Shorter posts perform better.",
        "format_notes": "Video gets 6x engagement. Native video > links. Groups for community.",
        "max_caption_length": 63206,
    },
}


async def create_publishing_strategy(
    content_description: str,
    content_type: str = "",
    target_platforms: list[str] | None = None,
    campaign_goal: str = "",
    content_id: str = "",
    pipeline_id: str = "",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Create a comprehensive publishing strategy for content distribution.

    Generates platform-specific captions, optimal posting schedules, hashtag
    strategies, and a multi-day distribution calendar. References the brand
    profile for voice consistency and platform rules.

    Args:
        content_description: What the content is about and what it looks like.
        content_type: Type of content (video ad, blog post, carousel, etc.).
        target_platforms: List of platforms to publish on (e.g., ["instagram", "tiktok", "linkedin"]).
        campaign_goal: What the publishing should achieve (awareness, leads, engagement, etc.).
        content_id: Optional ID of the content asset being published.
        pipeline_id: Optional content pipeline ID for tracking.
        user_id: Optional user ID override.

    Returns:
        Comprehensive publishing strategy with per-platform plans.
    """
    user_id = user_id or _get_request_user_id()
    strategy_id = str(uuid.uuid4())
    platforms = target_platforms or ["instagram", "tiktok", "linkedin"]

    # Load brand profile for platform rules
    brand_platform_rules = {}
    if user_id:
        try:
            supabase = _get_supabase_client()
            if supabase:
                result = (
                    supabase.table("brand_profiles")
                    .select("platform_rules, voice_tone, audience_description")
                    .eq("user_id", user_id)
                    .eq("is_default", True)
                    .limit(1)
                    .execute()
                )
                if result.data:
                    profile = result.data[0]
                    brand_platform_rules = profile.get("platform_rules", {}) or {}
        except Exception:
            pass

    # Build per-platform strategy templates
    platform_strategies = []
    for platform in platforms:
        platform_lower = platform.lower().strip()
        guidelines = PLATFORM_GUIDELINES.get(platform_lower, {})
        brand_rules = brand_platform_rules.get(platform_lower, {})

        strategy = {
            "platform": platform_lower,
            "caption": "",  # Agent fills this with platform-specific copy
            "hashtags": [],  # Agent fills with relevant hashtags
            "optimal_posting_time": guidelines.get("optimal_times", "Research needed"),
            "format_notes": guidelines.get("format_notes", ""),
            "caption_guidelines": guidelines.get("caption_style", ""),
            "max_caption_length": guidelines.get("max_caption_length", 2200),
            "recommended_hashtag_count": guidelines.get("hashtag_count", "3-5"),
            "brand_rules": brand_rules,
            "content_adaptations": "",  # Agent fills with platform-specific tweaks
            "cta": "",  # Agent fills with platform-specific CTA
        }
        platform_strategies.append(strategy)

    # Build distribution calendar template
    distribution_calendar = [
        {
            "day": "Day 1 (Launch)",
            "platform": "",
            "time": "",
            "content_variant": "Primary content — full version",
            "notes": "",
        },
        {
            "day": "Day 2",
            "platform": "",
            "time": "",
            "content_variant": "Behind-the-scenes or making-of",
            "notes": "",
        },
        {
            "day": "Day 3",
            "platform": "",
            "time": "",
            "content_variant": "Teaser or highlight clip",
            "notes": "",
        },
        {
            "day": "Day 5",
            "platform": "",
            "time": "",
            "content_variant": "User engagement prompt or poll",
            "notes": "",
        },
        {
            "day": "Day 7",
            "platform": "",
            "time": "",
            "content_variant": "Repurposed format (carousel, thread, etc.)",
            "notes": "",
        },
    ]

    strategy_doc = {
        "id": strategy_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "content_description": content_description,
        "content_type": content_type,
        "campaign_goal": campaign_goal,
        "content_id": content_id or None,
        "pipeline_id": pipeline_id or None,
        # Per-platform strategies (agent fills in captions, hashtags, adaptations)
        "platform_strategies": platform_strategies,
        # Multi-day distribution calendar (agent fills in specifics)
        "distribution_calendar": distribution_calendar,
        # Cross-platform notes
        "cross_platform_notes": "",
        "a_b_test_suggestions": [],
        "engagement_hooks": [],
        "repurpose_ideas": [],
    }

    # Save to Knowledge Vault
    if user_id:
        supabase = _get_supabase_client()
        if supabase:
            try:
                supabase.table("knowledge_vault").insert(
                    {
                        "id": strategy_id,
                        "user_id": user_id,
                        "title": f"Publishing Strategy: {content_description[:60]}",
                        "content": json.dumps(strategy_doc, default=str),
                        "document_type": "publishing_strategy",
                        "metadata": {
                            "pipeline_stage": "publish_strategy",
                            "pipeline_id": pipeline_id or None,
                            "platforms": platforms,
                            "content_type": content_type,
                        },
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).execute()
            except Exception as exc:
                logger.warning("Failed to save publishing strategy: %s", exc)

    return {
        "success": True,
        "strategy_id": strategy_id,
        "strategy": strategy_doc,
        "message": (
            f"Publishing strategy template created for {len(platforms)} platform(s). "
            "For each platform, fill in:\n"
            "- **caption**: Platform-native copy (respect max length and style)\n"
            "- **hashtags**: Relevant hashtags (follow count guidelines)\n"
            "- **content_adaptations**: Platform-specific tweaks (aspect ratio, length, etc.)\n"
            "- **cta**: Platform-appropriate call to action\n\n"
            "Then fill in the distribution_calendar with specific platforms, times, and content variants.\n"
            "Add a_b_test_suggestions, engagement_hooks, and repurpose_ideas for maximum reach."
        ),
    }


async def get_publishing_strategy(
    strategy_id: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Retrieve a saved publishing strategy by ID.

    Args:
        strategy_id: The UUID of the publishing strategy.
        user_id: Optional user ID override.

    Returns:
        The full publishing strategy data.
    """
    user_id = user_id or _get_request_user_id()
    if not user_id:
        return {"success": False, "error": "No user context available."}

    supabase = _get_supabase_client()
    if not supabase:
        return {"success": False, "error": "Database not configured."}

    try:
        result = (
            supabase.table("knowledge_vault")
            .select("*")
            .eq("id", strategy_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if result.data:
            content = result.data.get("content", "{}")
            strategy = json.loads(content) if isinstance(content, str) else content
            return {
                "success": True,
                "strategy": strategy,
                "strategy_id": strategy_id,
            }

        return {"success": False, "error": f"Strategy {strategy_id} not found."}

    except Exception as e:
        logger.error("Failed to retrieve publishing strategy: %s", e)
        return {"success": False, "error": str(e)}


# Exported tools list
PUBLISHING_STRATEGY_TOOLS = [
    create_publishing_strategy,
    get_publishing_strategy,
]
