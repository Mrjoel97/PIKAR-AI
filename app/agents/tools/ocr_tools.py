# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Gemini Vision OCR tool.

Replaces the Phase 0 degraded stub with a real implementation that passes
image/document bytes through Gemini's multimodal vision API and returns
the extracted text.
"""

import asyncio
import json
import logging

import httpx
from pydantic import BaseModel, Field

from app.agents.shared import get_model

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MIME type detection
# ---------------------------------------------------------------------------

_EXT_MIME_MAP: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".pdf": "application/pdf",
}


def _detect_mime_type(filename: str) -> str:
    """Detect MIME type from file extension.

    Args:
        filename: The filename (with or without path).

    Returns:
        MIME type string. Defaults to ``image/png`` for unknown extensions.
    """
    lower = filename.lower()
    for ext, mime in _EXT_MIME_MAP.items():
        if lower.endswith(ext):
            return mime
    return "image/png"  # safe default


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------


class OcrDocumentInput(BaseModel):
    """Input schema for the OCR document tool."""

    name: str = Field(
        "document",
        description="Filename of the document (used to detect MIME type).",
    )
    file_content: str | None = Field(
        None,
        description="Base64-encoded file bytes. Mutually exclusive with file_url.",
    )
    file_url: str | None = Field(
        None,
        description="URL to fetch the document from (e.g. Supabase Storage URL).",
    )


# ---------------------------------------------------------------------------
# Internal Gemini call (isolated for testability)
# ---------------------------------------------------------------------------

_OCR_PROMPT = (
    "Extract all text from this document image. "
    "Return the raw extracted text, preserving layout where possible. "
    "Do not add any commentary — output only the extracted text."
)


async def _run_ocr_on_bytes(raw_bytes: bytes, mime_type: str) -> str:
    """Call Gemini Vision on the provided bytes and return extracted text.

    This function is isolated so tests can patch it directly without needing
    to mock the full google.genai.types hierarchy.

    Args:
        raw_bytes: The raw image/document bytes.
        mime_type: The MIME type of the content.

    Returns:
        Extracted text string (may be empty if Gemini returns nothing).
    """
    from google.genai import types

    media_part = types.Part.from_bytes(data=raw_bytes, mime_type=mime_type)
    prompt_part = types.Part.from_text(text=_OCR_PROMPT)
    content = types.Content(role="user", parts=[prompt_part, media_part])
    config = types.GenerateContentConfig(temperature=0.0)

    model = get_model()
    response = await asyncio.to_thread(
        lambda: model.api_client.models.generate_content(
            model=model.model,
            contents=[content],
            config=config,
        )
    )
    return (response.text or "").strip()


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------


async def ocr_document(
    name: str = "document",
    file_content: bytes | None = None,
    file_url: str | None = None,
    extracted_text: str = "",
    **kwargs,
) -> dict:
    """Extract text from an image or document using Gemini Vision.

    Accepts raw bytes (``file_content``), a URL to fetch (``file_url``), or
    an already-extracted text string (``extracted_text``, backward-compat
    passthrough). If only ``extracted_text`` is provided it is returned
    directly without any model call.

    Args:
        name: Filename used to infer the MIME type.
        file_content: Raw bytes of the image/document.
        file_url: URL to download the document from.
        extracted_text: Pre-extracted text (backward compat — returned as-is).
        **kwargs: Ignored — kept for backward compatibility.

    Returns:
        dict with keys: success, extracted_text, tool.
        On failure: success=False with an error key.
    """
    from app.agents.data.tools import track_event

    try:
        # Backward-compat passthrough: if caller already has extracted text, return it.
        if extracted_text:
            return {
                "success": True,
                "extracted_text": extracted_text,
                "tool": "ocr_document",
            }

        # Resolve bytes from whichever source was provided.
        raw_bytes: bytes | None = None

        if file_content is not None:
            raw_bytes = file_content

        elif file_url:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(file_url)
                response.raise_for_status()
                raw_bytes = response.content

        if not raw_bytes:
            return {
                "success": False,
                "error": "No document content provided. Supply file_content, file_url, or extracted_text.",
                "tool": "ocr_document",
            }

        mime_type = _detect_mime_type(name)
        text_result = await _run_ocr_on_bytes(raw_bytes=raw_bytes, mime_type=mime_type)

        # Fire-and-forget observability
        try:
            await track_event(
                event_name="ocr_document",
                category="content",
                properties=json.dumps(
                    {"name": name, "mime_type": mime_type, "chars": len(text_result)},
                    default=str,
                ),
            )
        except Exception:
            pass  # observability is non-fatal

        return {
            "success": True,
            "extracted_text": text_result,
            "tool": "ocr_document",
        }

    except Exception as exc:
        logger.exception("ocr_document failed for '%s': %s", name, exc)
        return {
            "success": False,
            "error": str(exc),
            "tool": "ocr_document",
        }
