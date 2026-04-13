# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Gemini-powered sentiment analysis tool.

Replaces the Phase 0 degraded stub with a real NLP implementation that
calls Gemini to return structured sentiment scores (positive, negative,
neutral, mixed) with confidence values.
"""

import asyncio
import json
import logging
import re

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client helper (same lazy-init pattern as debate.py)
# ---------------------------------------------------------------------------


def _get_genai_client():
    """Lazy-create a google.genai Client (auto-configures from env vars)."""
    import google.genai as genai

    return genai.Client()


# ---------------------------------------------------------------------------
# JSON parsing helper (handles markdown code fences)
# ---------------------------------------------------------------------------

_JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*([\s\S]+?)\s*```",
    re.IGNORECASE,
)


def _extract_json(text: str) -> str:
    """Strip markdown code fences from a string before JSON parsing."""
    match = _JSON_FENCE_RE.search(text)
    if match:
        return match.group(1)
    return text.strip()


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------


class SentimentAnalysisInput(BaseModel):
    """Input schema for the sentiment analysis tool."""

    query: str = Field(
        "",
        description="Text to analyse for sentiment. Can be a customer review, feedback, or any free-form text.",
    )


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

_SENTIMENT_PROMPT_TEMPLATE = """\
Analyse the sentiment of the following text and return a JSON object with \
this exact structure:

{{
  "sentiment": "<positive|negative|neutral|mixed>",
  "confidence": <float between 0.0 and 1.0>,
  "scores": {{
    "positive": <float>,
    "negative": <float>,
    "neutral": <float>,
    "mixed": <float>
  }},
  "summary": "<one sentence explanation>"
}}

Rules:
- All four score values must sum to approximately 1.0.
- confidence reflects how certain the dominant sentiment label is.
- If the text is empty or cannot be meaningfully analysed, return neutral \
  with equal scores and confidence 0.5.
- Return ONLY the JSON object, no other text.

Text to analyse:
{text}
"""


async def analyze_sentiment(query: str = "", **kwargs) -> dict:
    """Analyse the sentiment of a text using Gemini.

    Calls the Gemini Flash model to classify the input text into one of four
    sentiment categories (positive, negative, neutral, mixed) with per-class
    confidence scores.

    Args:
        query: The text to analyse.
        **kwargs: Ignored — kept for backward compatibility with degraded signature.

    Returns:
        dict with keys: success, sentiment, confidence, scores, summary, tool.
        On failure: success=False with an error key.
    """
    from app.agents.data.tools import track_event

    try:
        text = query.strip() if query else ""
        prompt = _SENTIMENT_PROMPT_TEMPLATE.format(text=text or "(no text provided)")

        client = _get_genai_client()
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw = response.text or ""
        parsed = json.loads(_extract_json(raw))

        # Normalise required keys with safe defaults
        sentiment = parsed.get("sentiment", "neutral")
        confidence = float(parsed.get("confidence", 0.5))
        scores = parsed.get(
            "scores",
            {"positive": 0.25, "negative": 0.25, "neutral": 0.25, "mixed": 0.25},
        )
        summary = parsed.get("summary", "")

        # Fire-and-forget observability (mirrors degraded version)
        try:
            await track_event(
                event_name="analyze_sentiment",
                category="research",
                properties=json.dumps(
                    {"query_length": len(text), "sentiment": sentiment},
                    default=str,
                ),
            )
        except Exception:
            pass  # observability is non-fatal

        return {
            "success": True,
            "sentiment": sentiment,
            "confidence": confidence,
            "scores": scores,
            "summary": summary,
            "tool": "analyze_sentiment",
        }

    except Exception as exc:
        logger.exception("analyze_sentiment failed: %s", exc)
        return {
            "success": False,
            "error": str(exc),
            "tool": "analyze_sentiment",
        }
