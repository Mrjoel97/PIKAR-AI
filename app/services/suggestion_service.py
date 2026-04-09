# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Suggestion chip service for persona-aware, time-sensitive chat prompts.

Generates contextual suggestion chips based on:
- User persona (solopreneur, startup, sme, enterprise)
- Time of day (morning, afternoon, evening buckets)
- Recent activity (workflow follow-ups)

Used by the ``GET /suggestions`` endpoint to replace hardcoded client-side
suggestions with backend-driven, personalized chips.
"""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SuggestionItem(BaseModel):
    """A single suggestion chip returned to the frontend."""

    text: str
    category: str  # quick_start | persona_specific | time_aware | activity_followup


# ---------------------------------------------------------------------------
# Persona-specific suggestion pools
# ---------------------------------------------------------------------------

PERSONA_SUGGESTIONS: dict[str, list[str]] = {
    "solopreneur": [
        "Review yesterday's revenue",
        "Check my business revenue",
        "Create a content calendar for this week",
        "Start a brain dump session",
        "Show available workflows",
        "Brainstorm a new product idea",
        "Generate a marketing campaign",
        "Analyze my social media performance",
        "Draft a sales outreach email",
        "Review my task pipeline",
        "Find growth opportunities",
        "Optimize my pricing strategy",
    ],
    "startup": [
        "Check product-market fit signals",
        "Review experiment velocity this sprint",
        "Analyze growth metrics dashboard",
        "Prepare fundraising pitch materials",
        "Review burn rate and runway",
        "Identify top churn risk customers",
        "Draft investor update email",
        "Brainstorm feature prioritization",
        "Analyze competitor landscape",
        "Review hiring pipeline status",
        "Plan next sprint objectives",
        "Check activation funnel metrics",
    ],
    "sme": [
        "Review department performance reports",
        "Check compliance status across teams",
        "Generate monthly business report",
        "Optimize cross-department workflows",
        "Review employee satisfaction trends",
        "Audit process efficiency metrics",
        "Plan resource allocation for Q2",
        "Check vendor contract renewals",
        "Review customer satisfaction scores",
        "Analyze operational bottlenecks",
        "Draft team communication update",
        "Review project milestone progress",
    ],
    "enterprise": [
        "Check portfolio health dashboard",
        "Review governance compliance status",
        "Analyze enterprise risk indicators",
        "Coordinate cross-functional initiatives",
        "Review executive briefing summary",
        "Audit security posture metrics",
        "Plan strategic quarterly objectives",
        "Check regulatory change impacts",
        "Review M&A pipeline status",
        "Analyze workforce planning data",
        "Draft board presentation materials",
        "Review global operations dashboard",
    ],
}

# ---------------------------------------------------------------------------
# Time-of-day buckets
# ---------------------------------------------------------------------------

TIME_BUCKET_SUGGESTIONS: dict[str, list[str]] = {
    "morning": [
        "Review yesterday's metrics",
        "Plan today's priorities",
        "Check overnight notifications",
        "Review pending approvals",
        "Start the day with a brain dump",
        "Check your calendar for today",
        "Review urgent action items",
    ],
    "afternoon": [
        "Summarize progress so far today",
        "Draft a follow-up on pending items",
        "Review team updates",
        "Analyze today's performance data",
        "Create a workflow for a recurring task",
        "Check on running experiments",
        "Prepare materials for tomorrow",
    ],
    "evening": [
        "Plan tomorrow's top priorities",
        "Review today's accomplishments",
        "Draft end-of-day status update",
        "Brainstorm ideas for next week",
        "Review weekly goals progress",
        "Prepare for tomorrow's meetings",
        "Reflect on key learnings today",
    ],
}

# ---------------------------------------------------------------------------
# Activity follow-up mappings
# ---------------------------------------------------------------------------

ACTIVITY_FOLLOWUP_MAP: dict[str, list[str]] = {
    "workflow:content_creation": [
        "Review your latest content draft",
        "Schedule content for publishing",
        "Analyze content performance metrics",
    ],
    "workflow:marketing_campaign": [
        "Check campaign performance results",
        "Adjust campaign targeting parameters",
        "Review campaign budget allocation",
    ],
    "workflow:financial_review": [
        "Review updated financial projections",
        "Check expense anomalies flagged",
        "Compare actuals vs budget",
    ],
    "workflow:strategic_planning": [
        "Review strategic initiative progress",
        "Update milestone timelines",
        "Check strategic goal alignment",
    ],
    "workflow:compliance_check": [
        "Review compliance findings report",
        "Address flagged compliance items",
        "Schedule follow-up compliance audit",
    ],
    "workflow:sales_pipeline": [
        "Review pipeline conversion rates",
        "Follow up on stalled deals",
        "Prepare proposal for top prospect",
    ],
}


def _get_time_bucket(hour: int) -> str:
    """Map an hour (0-23) to a time-of-day bucket."""
    if 6 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    # evening (17-22) and night (22-6) both use evening bucket
    return "evening"


async def get_suggestions(
    persona: str,
    hour: int,
    recent_activity: list[str] | None = None,
    limit: int = 6,
) -> list[SuggestionItem]:
    """Generate personalized suggestion chips.

    Collects candidates from persona pool (weight 3), time-of-day pool (weight 2),
    and activity follow-ups (weight 1). Shuffles, deduplicates, and returns
    ``limit`` items (minimum 4).

    Args:
        persona: User persona key (solopreneur, startup, sme, enterprise).
        hour: Current hour in 0-23 range.
        recent_activity: Optional list of activity type strings.
        limit: Maximum number of suggestions to return (default 6).

    Returns:
        List of 4-6 SuggestionItem objects.
    """
    weighted_pool: list[tuple[str, str]] = []  # (text, category)

    # --- Persona suggestions (weight 3) ---
    persona_pool = PERSONA_SUGGESTIONS.get(persona, PERSONA_SUGGESTIONS["solopreneur"])
    for text in persona_pool:
        weighted_pool.extend([(text, "persona_specific")] * 3)

    # --- Time-of-day suggestions (weight 2) ---
    bucket = _get_time_bucket(hour)
    for text in TIME_BUCKET_SUGGESTIONS.get(bucket, []):
        weighted_pool.extend([(text, "time_aware")] * 2)

    # --- Build result: reserve slots for activity followups, then fill rest ---
    seen: set[str] = set()
    result: list[SuggestionItem] = []

    # If activity followups exist, guarantee at least one slot for them
    activity_items: list[SuggestionItem] = []
    if recent_activity:
        for activity_key in recent_activity:
            for text in ACTIVITY_FOLLOWUP_MAP.get(activity_key, []):
                if text not in seen:
                    seen.add(text)
                    activity_items.append(
                        SuggestionItem(text=text, category="activity_followup"),
                    )
        if activity_items:
            random.shuffle(activity_items)
            result.append(activity_items[0])

    # Shuffle and deduplicate the main weighted pool
    random.shuffle(weighted_pool)
    main_unique: list[SuggestionItem] = []
    for text, category in weighted_pool:
        if text not in seen:
            seen.add(text)
            main_unique.append(SuggestionItem(text=text, category=category))

    # Fill remaining slots up to limit
    remaining_slots = max(limit, 4) - len(result)
    result.extend(main_unique[:remaining_slots])

    # Shuffle final result so activity followup isn't always first
    random.shuffle(result)

    # Ensure minimum of 4
    if len(result) < 4:
        fallbacks = [
            SuggestionItem(text="Review my business", category="quick_start"),
            SuggestionItem(text="Create a strategic plan", category="quick_start"),
            SuggestionItem(text="Start a brain dump session", category="quick_start"),
            SuggestionItem(text="Show available workflows", category="quick_start"),
        ]
        for fb in fallbacks:
            if fb.text not in seen and len(result) < 4:
                seen.add(fb.text)
                result.append(fb)

    return result
