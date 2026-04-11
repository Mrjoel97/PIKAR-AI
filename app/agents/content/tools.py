# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tools for the Content Creation Agent."""

import logging

from app.agents.tools.brand_profile import get_brand_profile
from app.services.content_service import ContentService
from app.services.request_context import get_current_user_id

logger = logging.getLogger(__name__)

# ==========================================
# One-Shot Fast Path Tool
# ==========================================

# Supported content types for the one-shot fast path
SIMPLE_CONTENT_TYPES = frozenset(
    {"social_post", "blog_intro", "email", "caption", "headline", "tagline"}
)

# Platform-specific length guidance
PLATFORM_LENGTH_HINTS: dict[str, str] = {
    "twitter": "Max 280 characters. Punchy, concise, hook-first.",
    "linkedin": "1-3 short paragraphs. Professional yet personable.",
    "instagram": "Caption up to 2200 chars. Lead with hook, end with CTA. Use line breaks.",
    "facebook": "1-2 paragraphs. Conversational, encourage engagement.",
    "threads": "Max 500 characters. Conversational and snappy.",
}

# Content-type specific guidance
CONTENT_TYPE_GUIDANCE: dict[str, str] = {
    "social_post": (
        "Write an engaging social media post. "
        "Lead with a hook, be concise, end with a CTA or question."
    ),
    "blog_intro": (
        "Write a compelling blog introduction (2-3 paragraphs). "
        "Hook the reader, state the problem, preview the value."
    ),
    "email": (
        "Write an email with a subject line and body. "
        "Be personal, clear, and action-oriented."
    ),
    "caption": (
        "Write a short, punchy caption. "
        "Visual-first context, keep it brief and engaging."
    ),
    "headline": (
        "Write a compelling headline. Clear, benefit-driven, curiosity-inducing."
    ),
    "tagline": (
        "Write a memorable tagline. Short, brand-aligned, emotionally resonant."
    ),
}

# Length guidance mapping
LENGTH_GUIDANCE: dict[str, str] = {
    "short": "Keep it brief -- 1-2 sentences or under 100 words.",
    "medium": "Moderate length -- 2-4 sentences or 100-250 words.",
    "long": "Detailed -- 4-8 sentences or 250-500 words.",
}


async def simple_create_content(
    topic: str,
    content_type: str,
    platform: str | None = None,
    tone: str | None = None,
    length: str = "medium",
    additional_context: str = "",
) -> dict:
    """Create a simple, one-shot content draft without the full creative pipeline.

    Use this for quick content requests: social posts, blog intros, emails,
    captions, headlines, and taglines. The tool loads brand context, structures
    the prompt, and saves the result. The LLM generates the actual text using
    the returned prompt_context.

    Args:
        topic: What the content is about (e.g., "Product launch for our new app").
        content_type: One of: social_post, blog_intro, email, caption, headline, tagline.
        platform: Target platform (twitter, linkedin, instagram, facebook, threads).
            Adds platform-specific constraints. Optional.
        tone: Desired tone (e.g., "casual", "professional", "edgy"). Falls back
            to brand profile voice_tone if not provided. Optional.
        length: How long the content should be: short, medium, or long. Default medium.
        additional_context: Any extra context or requirements for the content.

    Returns:
        Dictionary with success status, brand_context, prompt_context for the LLM,
        and saved content_id.
    """
    # --- 1. Load brand profile (optional, not a blocker) ---
    brand_context: dict = {}
    try:
        brand_data = await get_brand_profile()
        if brand_data.get("success") and brand_data.get("brand_name"):
            brand_context = {
                "brand_name": brand_data.get("brand_name", ""),
                "voice_tone": brand_data.get("voice_tone", ""),
            }
    except Exception:
        logger.debug(
            "Brand profile unavailable for simple_create_content; proceeding without."
        )

    # --- 2. Resolve tone ---
    effective_tone = tone or brand_context.get("voice_tone", "")

    # --- 3. Build structured prompt context ---
    prompt_context: dict = {
        "topic": topic,
        "content_type": content_type,
        "type_guidance": CONTENT_TYPE_GUIDANCE.get(content_type, ""),
        "length_guidance": LENGTH_GUIDANCE.get(length, LENGTH_GUIDANCE["medium"]),
        "tone": effective_tone,
    }

    if platform:
        prompt_context["platform"] = platform
        prompt_context["platform_guidance"] = PLATFORM_LENGTH_HINTS.get(platform, "")

    if additional_context:
        prompt_context["additional_context"] = additional_context

    if brand_context.get("brand_name"):
        prompt_context["brand_name"] = brand_context["brand_name"]

    # --- 4. Save draft to Knowledge Vault ---
    content_id = None
    saved = False
    try:
        user_id = get_current_user_id()
        service = ContentService()
        save_title = f"[{content_type}] {topic[:80]}"
        save_body = (
            f"Content type: {content_type}\n"
            f"Topic: {topic}\n"
            f"Platform: {platform or 'general'}\n"
            f"Tone: {effective_tone or 'default'}\n"
            f"Length: {length}\n"
        )
        save_result = await service.save_content(
            title=save_title,
            content=save_body,
            agent_id="content-agent",
            user_id=user_id,
        )
        if save_result.get("success"):
            ids = save_result.get("ids", [])
            content_id = ids[0] if ids else None
            saved = True
    except Exception:
        logger.warning("Failed to save simple draft to Knowledge Vault; continuing.")

    # --- 5. Return structured result ---
    return {
        "success": True,
        "content_type": content_type,
        "platform": platform,
        "topic": topic,
        "brand_context": brand_context,
        "prompt_context": prompt_context,
        "saved": saved,
        "content_id": content_id,
    }


def search_knowledge(query: str) -> dict:
    """Search business knowledge base for relevant information.

    Args:
        query: The search query to find relevant business knowledge.

    Returns:
        Dictionary containing search results.
    """
    try:
        from app.rag.knowledge_vault import search_knowledge as kb_search

        return kb_search(query, top_k=3)
    except Exception:
        return {"results": []}


async def save_content(title: str, content: str) -> dict:
    """Save generated content to the Knowledge Vault via ContentService.

    Args:
        title: Title of the content.
        content: The text content to save.

    Returns:
        Dictionary confirming save status.
    """
    from app.services.content_service import ContentService

    try:
        from app.services.request_context import get_current_user_id

        service = ContentService()
        result = await service.save_content(
            title, content, agent_id="content-agent", user_id=get_current_user_id()
        )
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_content(content_id: str) -> dict:
    """Retrieve saved content by its ID.

    Args:
        content_id: The unique ID of the content.

    Returns:
        Dictionary containing the content record.
    """
    from app.services.content_service import ContentService

    try:
        from app.services.request_context import get_current_user_id

        service = ContentService()
        result = await service.get_content(content_id, user_id=get_current_user_id())
        return {"success": True, "content": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_content(
    content_id: str, title: str = None, content: str = None
) -> dict:
    """Update existing content.

    Args:
        content_id: The unique ID of the content.
        title: New title (optional).
        content: New content text (optional).

    Returns:
        Dictionary with updated content.
    """
    from app.services.content_service import ContentService

    try:
        from app.services.request_context import get_current_user_id

        service = ContentService()
        result = await service.update_content(
            content_id, title=title, content=content, user_id=get_current_user_id()
        )
        return {"success": True, "content": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_content(content_type: str = None) -> dict:
    """List saved content items.

    Args:
        content_type: Optional filter by type (e.g., 'blog', 'social').

    Returns:
        Dictionary with list of content items.
    """
    from app.services.content_service import ContentService

    try:
        from app.services.request_context import get_current_user_id

        service = ContentService()
        items = await service.list_content(
            content_type=content_type, user_id=get_current_user_id()
        )
        return {"success": True, "items": items, "count": len(items)}
    except Exception as e:
        return {"success": False, "error": str(e), "items": []}


# ==========================================
# Scheduling Suggestion Tool
# ==========================================

# Content type mapping from agent content types to calendar content types
_CONTENT_TYPE_MAP: dict[str, str] = {
    "social_post": "social",
    "blog_intro": "blog",
    "email": "email",
    "caption": "social",
    "headline": "ad",
    "tagline": "ad",
    "video": "video",
}

# Day-name to weekday index (Monday=0 ... Sunday=6)
_DAY_INDEX: dict[str, int] = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

# Platform-specific first recommended time (parsed from PLATFORM_GUIDELINES)
_PLATFORM_FIRST_TIME: dict[str, tuple[tuple[int, ...], str]] = {
    # (weekday indices, first time string)
    "instagram": ((0, 1, 2, 3, 4), "09:00"),  # Mon-Fri 9am
    "tiktok": ((1, 2, 3), "10:00"),  # Tue-Thu 10am
    "youtube": ((3, 4, 5), "14:00"),  # Thu-Sat 2pm
    "linkedin": ((1, 2, 3), "09:00"),  # Tue-Thu 8am-10am -> 9am
    "twitter": ((0, 1, 2, 3, 4), "09:00"),  # Mon-Fri 8am-10am -> 9am
    "facebook": ((2, 3, 4), "13:00"),  # Wed-Fri 1pm
}

# Reasoning templates per platform
_PLATFORM_REASONING: dict[str, str] = {
    "instagram": "Instagram posts perform best Mon-Fri at 9am, 12pm, and 3pm in your audience's timezone",
    "tiktok": "TikTok engagement peaks Tue-Thu at 10am, 2pm, and 7pm",
    "youtube": "YouTube videos perform best Thu-Sat between 2-4pm in your audience's timezone",
    "linkedin": "LinkedIn posts perform best Tue-Thu between 8-10am during business hours",
    "twitter": "Twitter/X engagement peaks Mon-Fri at 8-10am and 6-9pm",
    "facebook": "Facebook posts perform best Wed-Fri between 1-4pm",
}


def _today():
    """Return today's date. Extracted for testability."""
    from datetime import date

    return date.today()


def _map_content_type(content_type: str) -> str:
    """Map agent content type to calendar content type.

    Args:
        content_type: The content type from the agent (e.g., 'social_post', 'blog_intro').

    Returns:
        Calendar-compatible content type string.
    """
    return _CONTENT_TYPE_MAP.get(content_type, "other")


def _next_weekday_on_or_after(start, target_weekdays: tuple[int, ...]):
    """Find the next date on or after *start* whose weekday is in *target_weekdays*.

    Args:
        start: The starting date.
        target_weekdays: Tuple of acceptable weekday indices (0=Mon, 6=Sun).

    Returns:
        The next matching date.
    """
    from datetime import timedelta

    for offset in range(7):
        candidate = start + timedelta(days=offset)
        if candidate.weekday() in target_weekdays:
            return candidate
    # Fallback: should never happen with 7-day scan
    return start  # pragma: no cover


def _compute_optimal_timing(
    platform: str | None,
) -> tuple[str, str, str]:
    """Compute optimal posting date, time, and reasoning for a platform.

    Uses PLATFORM_GUIDELINES data to pick the next suitable date/time.

    Args:
        platform: Target platform name (e.g., 'instagram', 'linkedin') or None.

    Returns:
        Tuple of (date_str YYYY-MM-DD, time_str HH:MM, reasoning).
    """
    today = _today()
    # Start searching from tomorrow to avoid same-day scheduling
    from datetime import timedelta

    search_start = today + timedelta(days=1)

    platform_key = (platform or "").lower().strip()

    if platform_key and platform_key in _PLATFORM_FIRST_TIME:
        weekdays, time_str = _PLATFORM_FIRST_TIME[platform_key]
        optimal_date = _next_weekday_on_or_after(search_start, weekdays)
        reasoning = _PLATFORM_REASONING.get(
            platform_key,
            f"Timing based on {platform_key} best practices",
        )
    else:
        # Default: next weekday at 10:00
        weekdays = (0, 1, 2, 3, 4)
        time_str = "10:00"
        optimal_date = _next_weekday_on_or_after(search_start, weekdays)
        reasoning = (
            "General best practice: posting on a weekday at 10am for default reach"
        )

    return optimal_date.strftime("%Y-%m-%d"), time_str, reasoning


async def suggest_and_schedule_content(
    title: str,
    content_type: str,
    platform: str | None = None,
    description: str = "",
    schedule: bool = False,
    preferred_date: str | None = None,
    preferred_time: str | None = None,
) -> dict:
    """Suggest an optimal posting time and optionally schedule content.

    When schedule=False (default), returns a suggestion with optimal date/time
    and reasoning. When schedule=True, creates a calendar entry via
    ContentCalendarService.

    Args:
        title: Content title.
        content_type: Type of content (social_post, blog_intro, email, video, etc.).
        platform: Target platform (instagram, linkedin, etc.) or None.
        description: Brief description of the content.
        schedule: If True, actually schedule it; if False, just suggest.
        preferred_date: User override for date (YYYY-MM-DD).
        preferred_time: User override for time (HH:MM).

    Returns:
        Dictionary with suggestion or scheduling confirmation.
    """
    try:
        # Compute optimal timing
        optimal_date, optimal_time, reasoning = _compute_optimal_timing(platform)

        # Apply user overrides
        date_str = preferred_date or optimal_date
        time_str = preferred_time or optimal_time

        # Map content type for calendar
        mapped_type = _map_content_type(content_type)

        platform_label = platform or "your channel"

        if not schedule:
            # Suggestion mode: return recommendation without scheduling
            return {
                "success": True,
                "mode": "suggestion",
                "optimal_date": date_str,
                "optimal_time": time_str,
                "reasoning": reasoning,
                "platform": platform,
                "content_type": mapped_type,
                "message": (
                    f"I suggest posting on {date_str} at {time_str}. "
                    f"{reasoning}. Say 'schedule it' to confirm."
                ),
            }

        # Scheduling mode: create calendar entry
        from app.services.content_calendar_service import ContentCalendarService
        from app.services.request_context import get_current_user_id

        service = ContentCalendarService()
        calendar_item = await service.schedule_content(
            title=title,
            content_type=mapped_type,
            scheduled_date=date_str,
            platform=platform,
            scheduled_time=time_str,
            description=description,
            user_id=get_current_user_id(),
        )

        return {
            "success": True,
            "mode": "scheduled",
            "calendar_item": calendar_item,
            "message": (
                f"Scheduled '{title}' for {date_str} at {time_str} on {platform_label}."
            ),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ==========================================
# Brand Voice Auto-Learning Tool
# ==========================================


async def learn_brand_voice() -> dict:
    """Analyze the user's content history to learn their brand voice patterns.

    Requires at least 5 prior pieces of content. Extracts tone, vocabulary,
    sentence patterns, and formality signals from the content history, then
    persists the learned voice profile to the user's brand profile so all
    future content (fast path and pipeline) reflects their natural writing
    style without manual configuration.

    Returns:
        When ready:
            ``{"success": True, "voice_profile": {...}, "persist_result": {...},
            "content_count": int}``
        When insufficient:
            ``{"success": False, "reason": "Need at least 5 content pieces (have N)",
            "content_count": int}``
        On error:
            ``{"success": False, "error": str}``
    """
    from app.services.brand_voice_service import BrandVoiceService

    try:
        user_id = get_current_user_id()
        service = BrandVoiceService()
        result = await service.analyze_and_learn(user_id)

        if result.get("success"):
            logger.info(
                "learn_brand_voice succeeded for user=%s content_count=%s",
                user_id,
                result.get("content_count"),
            )
        else:
            logger.info(
                "learn_brand_voice not ready for user=%s: %s",
                user_id,
                result.get("reason"),
            )

        return result
    except Exception as exc:
        logger.exception("learn_brand_voice failed")
        return {"success": False, "error": str(exc)}


# ==========================================
# Content Performance Feedback Loop Tool
# ==========================================


async def get_content_performance(
    since_days: int = 30,
    platform: str | None = None,
) -> dict:
    """Get performance summary for published content with improvement suggestions.

    Fetches engagement data (likes, shares, comments, impressions) for content
    published in the specified period and generates actionable improvement suggestions.

    Args:
        since_days: Lookback period in days (default: 30).
        platform: Optional filter by platform (twitter, instagram, linkedin, etc.).

    Returns:
        Dictionary with performance summary, aggregate metrics, and suggestions.
    """
    from app.services.content_performance_service import ContentPerformanceService

    try:
        user_id = get_current_user_id()
        service = ContentPerformanceService()
        result = await service.get_performance_summary(
            user_id=user_id, since_days=since_days, platform=platform
        )
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}
