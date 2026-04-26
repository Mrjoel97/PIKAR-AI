# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Prompt Enhancer — expand vague user descriptions into Stitch-optimized specifications.

Calls Gemini Flash to add design specificity: color palette, typography,
section breakdown, visual style. Falls back gracefully if unavailable.
"""

import logging
from typing import Any

try:
    from google import genai
    from google.genai import types as genai_types
except (
    Exception
):  # pragma: no cover - import guard for environments without google-genai
    genai = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# Design vocabulary for common domain types — injects domain-specific context
# before calling Gemini so the model has a concrete starting point.
DESIGN_VOCABULARY: dict[str, dict[str, Any]] = {
    "bakery": {
        "colors": [
            "#F5E6D3 (warm cream)",
            "#8B4513 (saddle brown)",
            "#D2691E (chocolate)",
        ],
        "typography": "Playfair Display headings, Lato body",
        "mood": "artisan, warm, inviting",
        "sections": [
            "hero with bread/pastry photography",
            "featured products grid",
            "about/story section",
            "hours and location with Google Maps",
        ],
    },
    "saas": {
        "colors": ["#6366F1 (indigo)", "#FFFFFF (white)", "#F9FAFB (gray-50)"],
        "typography": "Inter headings and body",
        "mood": "professional, modern, trustworthy",
        "sections": [
            "hero with product screenshot",
            "feature highlights",
            "social proof / testimonials",
            "pricing table",
            "CTA",
        ],
    },
    "restaurant": {
        "colors": ["#1C1C1E (near black)", "#C9A96E (gold)", "#FFFFFF (white)"],
        "typography": "Cormorant Garamond headings, Raleway body",
        "mood": "elegant, upscale, appetizing",
        "sections": ["full-bleed hero", "menu preview", "reservations", "location"],
    },
    "fitness": {
        "colors": ["#FF6B35 (orange)", "#1A1A2E (dark navy)", "#FFFFFF"],
        "typography": "Montserrat bold headings, Open Sans body",
        "mood": "energetic, motivating, bold",
        "sections": [
            "hero with action photography",
            "class schedule",
            "trainers",
            "pricing",
        ],
    },
}

ENHANCEMENT_SYSTEM_PROMPT = """You are a UI design specialist who converts vague web page descriptions
into structured specifications for an AI design tool (Google Stitch).

Output a detailed specification in this exact format:
CONCEPT: [one-sentence summary]
VISUAL_STYLE: [adjectives: modern/minimal/bold/warm/elegant/playful]
COLOR_PALETTE: [3 hex codes with names, e.g. #F5E6D3 warm cream]
TYPOGRAPHY: [heading font + body font pairing]
SECTIONS: [comma-separated list of page sections in order]
IMAGERY: [photography/illustration style description]
TONE: [brand voice: professional/friendly/luxurious/energetic]
TARGET_AUDIENCE: [who this is for]

Be specific. Include actual hex codes, specific font names, concrete section names.
Do not use generic language like "nice colors" or "good fonts"."""


async def enhance_prompt(
    description: str,
    domain_hint: str | None = None,
) -> str:
    """Expand a vague user description into a Stitch-optimized specification.

    Args:
        description: Raw user input, e.g. "bakery website" or "fitness app landing page".
        domain_hint: Optional category matching DESIGN_VOCABULARY keys
                     (bakery, saas, restaurant, fitness). Auto-detected if None
                     by checking if any key appears in the description.

    Returns:
        Structured specification string with COLOR_PALETTE, TYPOGRAPHY, SECTIONS, etc.
        Falls back to the original description if Gemini is unavailable.
    """
    # Auto-detect domain hint from description keywords
    if domain_hint is None:
        desc_lower = description.lower()
        for domain in DESIGN_VOCABULARY:
            if domain in desc_lower:
                domain_hint = domain
                break

    vocab_context = ""
    if domain_hint and domain_hint.lower() in DESIGN_VOCABULARY:
        vocab = DESIGN_VOCABULARY[domain_hint.lower()]
        vocab_context = (
            f"\n\nDesign vocabulary for {domain_hint}: "
            f"colors={vocab['colors']}, typography='{vocab['typography']}', "
            f"mood='{vocab['mood']}', typical sections={vocab['sections']}"
        )

    if genai is None:
        logger.warning("enhance_prompt: google-genai unavailable — returning original")
        return description

    try:
        client = genai.Client()
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{description}{vocab_context}",
            config=genai_types.GenerateContentConfig(
                system_instruction=ENHANCEMENT_SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=500,
            ),
        )
        enhanced = response.text
        logger.info(
            "enhance_prompt: expanded '%s' -> %d chars (domain_hint=%s)",
            description[:50],
            len(enhanced),
            domain_hint,
        )
        return enhanced
    except Exception as e:
        logger.warning(
            "enhance_prompt fallback (Gemini unavailable): %s — returning original", e
        )
        return description
