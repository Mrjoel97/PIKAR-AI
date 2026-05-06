# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Summarize older conversation events that fell out of the agent's
context window so the agent retains the gist of earlier turns.

Called by ``SupabaseSessionService.get_session`` when an event count
crosses ``SESSION_MAX_EVENTS``. The output is prepended to the loaded
events as a synthetic user-authored event with a clear marker prefix —
the model treats it as background context rather than a real user turn.

Failures fall back to no summary; the agent simply doesn't see the
dropped turns. This module never blocks the session-load critical path
beyond ``SUMMARIZER_TIMEOUT_S`` (default 8s).
"""

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

SUMMARIZER_MODEL = os.getenv("CONVERSATION_SUMMARIZER_MODEL", "gemini-2.5-flash")
SUMMARIZER_TIMEOUT_S = float(os.getenv("CONVERSATION_SUMMARIZER_TIMEOUT_S", "8.0"))
SUMMARIZER_MAX_OUTPUT_TOKENS = int(
    os.getenv("CONVERSATION_SUMMARIZER_MAX_OUTPUT_TOKENS", "800")
)
# Cap input to keep the summarization call cheap and fast even when many
# events fall out of the window. Older-than-this events are dropped from
# the summary input entirely.
SUMMARIZER_MAX_INPUT_EVENTS = int(
    os.getenv("CONVERSATION_SUMMARIZER_MAX_INPUT_EVENTS", "200")
)

_SYSTEM_PROMPT = (
    "You are a conversation summarizer for an AI executive assistant.\n"
    "Below is a list of older conversation turns that fell outside the\n"
    "model's active context window. Summarize them so the assistant\n"
    "retains the user's intent, decisions made, key facts shared, and\n"
    "any open threads.\n\n"
    "Constraints:\n"
    "- 250 words MAX. Bullet points where appropriate.\n"
    "- Lead with the user's primary goal in this session.\n"
    "- Preserve concrete facts (names, numbers, dates, file references).\n"
    "- Note unresolved questions or pending tasks at the end.\n"
    "- Do NOT invent information not present in the turns.\n"
    "- Output ONLY the summary; no preamble, no apology, no meta-comment.\n"
)


def _flatten_event_text(event: dict[str, Any]) -> str:
    """Best-effort extraction of human-readable text from an ADK event payload."""
    author = event.get("author") or event.get("source") or "agent"
    content = event.get("content") or {}
    parts = content.get("parts") if isinstance(content, dict) else None
    text_parts: list[str] = []
    if isinstance(parts, list):
        for p in parts:
            if not isinstance(p, dict):
                continue
            text = p.get("text")
            if isinstance(text, str) and text.strip():
                text_parts.append(text.strip())
    elif isinstance(content, str):
        text_parts.append(content)
    if not text_parts:
        return ""
    text = "\n".join(text_parts)
    # Cap per-event text to keep one verbose tool output from dominating
    # the summarization prompt.
    if len(text) > 1500:
        text = text[:750] + " ... " + text[-500:]
    return f"[{author}] {text}"


def _format_events_for_prompt(events: list[dict[str, Any]]) -> str:
    """Stitch event payloads into a chronological transcript for the model."""
    lines: list[str] = []
    for ev in events[-SUMMARIZER_MAX_INPUT_EVENTS:]:
        rendered = _flatten_event_text(ev)
        if rendered:
            lines.append(rendered)
    return "\n\n".join(lines)


async def summarize_dropped_events(
    events: list[dict[str, Any]],
    *,
    session_id: str,
) -> str | None:
    """Summarize older events that fell outside the agent's loaded window.

    Returns the summary text on success, or ``None`` on any failure
    (timeout, model error, no usable text in events). Never raises.
    """
    if not events:
        return None

    transcript = _format_events_for_prompt(events)
    if not transcript.strip():
        logger.info(
            "Session %s: dropped events had no extractable text; skipping summary",
            session_id,
        )
        return None

    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        logger.warning(
            "google.genai not available; cannot summarize session %s", session_id
        )
        return None

    try:
        client = genai.Client()
        prompt = f"{_SYSTEM_PROMPT}\n\nTRANSCRIPT:\n{transcript}\n\nSUMMARY:"
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=SUMMARIZER_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=SUMMARIZER_MAX_OUTPUT_TOKENS,
                ),
            ),
            timeout=SUMMARIZER_TIMEOUT_S,
        )
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            logger.info("Session %s: summarizer returned empty text", session_id)
            return None
        return text
    except asyncio.TimeoutError:
        logger.warning(
            "Session %s: summarizer exceeded %.1fs timeout; skipping",
            session_id,
            SUMMARIZER_TIMEOUT_S,
        )
        return None
    except Exception as exc:
        logger.warning(
            "Session %s: summarizer call failed (%s); skipping",
            session_id,
            exc,
        )
        return None
