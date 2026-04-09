# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Workflow discovery service for natural-language intent matching.

Enables non-technical users to discover workflows by describing what
they want in plain language (e.g. "launch a product") and to browse
a curated gallery of pre-built content templates.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class WorkflowMatch(BaseModel):
    """A workflow template that matches a user's natural-language query."""

    name: str
    description: str
    category: str
    match_score: float  # 0.0 – 1.0


class ContentTemplate(BaseModel):
    """A pre-built content template for the template gallery."""

    name: str
    description: str
    category: str
    icon: str
    example_prompt: str


# ---------------------------------------------------------------------------
# Stopwords stripped from user queries before scoring
# ---------------------------------------------------------------------------

_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "my",
        "me",
        "i",
        "want",
        "to",
        "need",
        "help",
        "with",
        "please",
        "can",
        "you",
        "do",
        "how",
        "for",
    }
)

# ---------------------------------------------------------------------------
# Pre-built content templates (curated gallery)
# ---------------------------------------------------------------------------

CONTENT_TEMPLATES: list[ContentTemplate] = [
    ContentTemplate(
        name="Product Launch Brief",
        description="Plan and coordinate a full product launch with messaging, timeline, and channels",
        category="strategy",
        icon="rocket",
        example_prompt="Create a product launch brief for my new fitness app",
    ),
    ContentTemplate(
        name="Blog Post",
        description="Write an SEO-optimized blog post with headline, outline, and body copy",
        category="content",
        icon="file-text",
        example_prompt="Write a blog post about sustainable packaging trends",
    ),
    ContentTemplate(
        name="Newsletter",
        description="Draft a customer newsletter with sections, CTAs, and personalization",
        category="content",
        icon="mail",
        example_prompt="Create a monthly newsletter for our SaaS product updates",
    ),
    ContentTemplate(
        name="Social Media Campaign",
        description="Plan a multi-platform social media campaign with posts and scheduling",
        category="marketing",
        icon="share-2",
        example_prompt="Plan a social media campaign for our summer sale",
    ),
    ContentTemplate(
        name="Video Ad Script",
        description="Write a short-form video ad script with hook, story, and CTA",
        category="content",
        icon="video",
        example_prompt="Write a 30-second video ad script for our protein bars",
    ),
    ContentTemplate(
        name="Testimonial Collection",
        description="Design a testimonial request workflow to gather customer stories",
        category="sales",
        icon="message-circle",
        example_prompt="Help me collect customer testimonials for our website",
    ),
    ContentTemplate(
        name="Email Sequence",
        description="Build a multi-step email drip sequence for nurturing or onboarding",
        category="marketing",
        icon="send",
        example_prompt="Create a 5-email welcome sequence for new subscribers",
    ),
    ContentTemplate(
        name="Competitive Analysis",
        description="Analyze competitor positioning, pricing, and market trends",
        category="strategy",
        icon="search",
        example_prompt="Run a competitive analysis on the top 3 project management tools",
    ),
    ContentTemplate(
        name="Landing Page Copy",
        description="Write conversion-focused landing page copy with headline, benefits, and CTA",
        category="marketing",
        icon="layout",
        example_prompt="Write landing page copy for our AI writing assistant",
    ),
    ContentTemplate(
        name="Sales Pitch Deck",
        description="Create a persuasive pitch deck outline with key slides and talking points",
        category="sales",
        icon="presentation",
        example_prompt="Build a pitch deck for our Series A fundraise",
    ),
    ContentTemplate(
        name="Monthly Report",
        description="Generate a monthly operations report with KPIs, highlights, and next steps",
        category="operations",
        icon="bar-chart",
        example_prompt="Generate a monthly operations report for March",
    ),
    ContentTemplate(
        name="Customer Survey",
        description="Design a customer satisfaction survey with scoring and open-ended questions",
        category="data",
        icon="clipboard",
        example_prompt="Create a customer satisfaction survey for our mobile app",
    ),
]


# ---------------------------------------------------------------------------
# Lazy engine accessor (easily patchable in tests)
# ---------------------------------------------------------------------------


def _get_engine():
    """Return the workflow engine singleton (lazy import to avoid circular deps)."""
    from app.workflows.engine import get_workflow_engine

    return get_workflow_engine()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _tokenize_query(query: str) -> list[str]:
    """Tokenize and strip stopwords from a natural-language query."""
    tokens = query.lower().split()
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def _score_template(
    keywords: list[str],
    name: str,
    description: str,
    category: str,
) -> float:
    """Score a template against query keywords (0.0 – 1.0)."""
    if not keywords:
        return 0.0

    haystack = f"{name} {description} {category}".lower()
    matched = 0

    for kw in keywords:
        # Exact word match
        if kw in haystack.split():
            matched += 1
        # Substring / partial match bonus
        elif kw in haystack:
            matched += 0.7

    base_score = matched / len(keywords)

    # Substring containment bonus: if any keyword appears as substring
    # of the template name specifically, add a boost
    name_lower = name.lower()
    for kw in keywords:
        if kw in name_lower:
            base_score = min(1.0, base_score + 0.3)
            break

    return round(min(1.0, base_score), 3)


async def search_workflows_by_intent(
    query: str,
    limit: int = 5,
) -> list[WorkflowMatch]:
    """Search workflow templates by natural-language intent.

    Tokenizes the query, strips stopwords, and scores each workflow
    template by keyword overlap.  Falls back to content templates if
    no workflow-engine templates match.

    Args:
        query: Natural-language description of desired workflow.
        limit: Maximum number of results to return.

    Returns:
        Scored list of matching workflows, sorted by relevance.
    """
    keywords = _tokenize_query(query)
    if not keywords:
        return []

    engine = _get_engine()
    templates = await engine.list_templates()

    scored: list[WorkflowMatch] = []
    for tpl in templates:
        score = _score_template(
            keywords,
            tpl.get("name", ""),
            tpl.get("description", ""),
            tpl.get("category", ""),
        )
        if score > 0.1:
            scored.append(
                WorkflowMatch(
                    name=tpl.get("name", ""),
                    description=tpl.get("description", ""),
                    category=tpl.get("category", ""),
                    match_score=score,
                )
            )

    # Fallback: also score content templates if no engine matches
    if not scored:
        for ct in CONTENT_TEMPLATES:
            score = _score_template(keywords, ct.name, ct.description, ct.category)
            if score > 0.1:
                scored.append(
                    WorkflowMatch(
                        name=ct.name,
                        description=ct.description,
                        category=ct.category,
                        match_score=score,
                    )
                )

    scored.sort(key=lambda m: m.match_score, reverse=True)
    return scored[:limit]


async def get_content_templates(
    category: str | None = None,
) -> list[ContentTemplate]:
    """Return pre-built content templates, optionally filtered by category.

    Args:
        category: If provided, only return templates in this category.

    Returns:
        Alphabetically sorted list of content templates.
    """
    templates = CONTENT_TEMPLATES
    if category:
        templates = [t for t in templates if t.category == category.lower()]
    return sorted(templates, key=lambda t: t.name)
