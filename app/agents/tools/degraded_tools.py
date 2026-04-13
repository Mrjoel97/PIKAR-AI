# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Degraded workflow tools — Phase 70 cleanup in progress.

All tools except analyze_sentiment and ocr_document have been promoted to
real implementations in app/agents/tools/registry.py (Phase 70-02).

analyze_sentiment and ocr_document are being moved to dedicated modules by
Phase 70-01 (running in parallel). Once Phase 70-01 ships, this file will be
fully empty.

See app/agents/tools/registry.py for the promoted versions.
"""

import json

from app.agents.content.tools import save_content
from app.agents.data.tools import track_event
from app.agents.tools.deep_research import quick_research


def _props(payload: dict) -> str:
    """Serialize payload dict to JSON string."""
    return json.dumps(payload, default=str)


async def _audit_event(event_name: str, category: str, payload: dict) -> None:
    """Track an audit event."""
    await track_event(
        event_name=event_name, category=category, properties=_props(payload)
    )


async def analyze_sentiment(query: str = "", **kwargs) -> dict:
    """Placeholder: analyze sentiment via research (Phase 70-01 moves to real implementation)."""
    research = await quick_research(
        topic=f"sentiment analysis: {query or 'workflow context'}"
    )
    await _audit_event(
        "analyze_sentiment", "research", {"query": query, "kwargs": kwargs}
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "research": research,
        "tool": "analyze_sentiment",
    }


async def ocr_document(
    name: str = "document", extracted_text: str = "", **kwargs
) -> dict:
    """Placeholder: OCR via save_content (Phase 70-01 moves to real implementation)."""
    artifact = await save_content(
        title=f"Document OCR: {name}",
        content=extracted_text or f"OCR extraction completed for '{name}'.",
    )
    await _audit_event("ocr_document", "content", {"name": name, "kwargs": kwargs})
    return {
        "success": True,
        "status": "degraded_completed",
        "artifact": artifact,
        "tool": "ocr_document",
    }
