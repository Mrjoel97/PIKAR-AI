# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Document editor agent tools.

Six tools (split across this module): read_document_content +
5 edit tools (one per doc class) + list_document_versions. Each edit
tool mutates the canonical source, re-renders the binary, writes a
version row, and returns a _workspace_command marker so the SSE
pipeline can notify the viewer.

This file ships only read_document_content for now; edit tools land in
follow-up tasks of the plan.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.agents.tools.base import agent_tool
from app.services.document_extraction_service import DocumentExtractionService
from app.services.document_source_service import DocumentSourceService
from app.services.document_version_service import DocumentVersionService

logger = logging.getLogger(__name__)

# Token cap for read_document_content output (~10K tokens, ~7500 words)
TEXT_TOKEN_CAP_WORDS = 7500


# --- Service factories (patchable in tests) ---


async def _get_source_service() -> DocumentSourceService:
    """Return a DocumentSourceService for cross-user reads (service role).

    Ownership is enforced in code via :func:`_load_owned_record`, not RLS.
    The default ``user_token=None`` constructor yields a service-role client
    via the shared async client; the agent runtime acts on the user's behalf
    so this is the intended access pattern for tools in this module.
    """
    return DocumentSourceService()


async def _get_version_service() -> DocumentVersionService:
    """Return a DocumentVersionService for cross-user reads (service role).

    Same rationale as :func:`_get_source_service` -- ownership is verified in
    code, not via RLS.
    """
    return DocumentVersionService()


def _get_extraction_service() -> DocumentExtractionService:
    """Return a DocumentExtractionService instance (stateless)."""
    return DocumentExtractionService()


async def _fetch_binary(url: str) -> bytes:
    """Fetch binary bytes from a URL via httpx.

    Uses an async context manager so the underlying connection pool is
    released even when the HTTP call raises.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


def _truncate_text(
    text: str, cap_words: int = TEXT_TOKEN_CAP_WORDS
) -> tuple[str, bool]:
    """Truncate ``text`` to ``cap_words`` whitespace-split words.

    Returns:
        ``(text, was_truncated)``. When truncated, the returned text has a
        ``\\n\\n[...truncated...]`` marker appended so the model can tell
        the content was cut off.
    """
    words = text.split()
    if len(words) <= cap_words:
        return text, False
    return " ".join(words[:cap_words]) + "\n\n[...truncated...]", True


async def _load_owned_record(
    tool_context: Any,
    document_id: str,
    source_service: DocumentSourceService,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Fetch a ``document_sources`` row and verify ownership.

    Returns ``(record, None)`` on success or ``(None, error_response)`` if
    the row is missing or not owned by the caller. Every tool in this
    module MUST use this helper instead of ``source_service.get`` directly:
    agents run under a service-role client so RLS doesn't gate access, and
    we enforce ownership in code by matching ``tool_context.state.user_id``
    against ``document_sources.user_id``.
    """
    record = await source_service.get(document_id)
    if record is None:
        return None, {
            "status": "error",
            "message": f"Document {document_id} not found",
        }
    user_id = (
        tool_context.state.get("user_id") if hasattr(tool_context, "state") else None
    )
    if not user_id or record.get("user_id") != user_id:
        return None, {
            "status": "error",
            "message": "Document not accessible",
        }
    return record, None


# --- Tool: read_document_content ---


@agent_tool
async def read_document_content(
    tool_context: Any,
    document_id: str,
    page_range: list[int] | None = None,
) -> dict[str, Any]:
    """Read text + structure from a document into the agent's context.

    Use when the user asks about a doc's contents, references something
    inside it, or before calling any ``edit_*`` tool that needs the current
    state to make a sensible change. Triggers lazy text extraction on the
    first call for a user upload.

    Args:
        tool_context: ADK tool context carrying ``state.user_id``.
        document_id: UUID of the document.
        page_range: 1-indexed pages to read (``None`` = whole doc, capped).
            Currently unused beyond pass-through; future versions will slice
            ``extracted_text`` by page.

    Returns:
        Dict with keys:
            * ``status`` -- ``"success"`` or ``"error"``.
            * ``text`` -- extracted text (capped at ~10K tokens; truncation
              marker appended when cut).
            * ``structure`` -- ``{type, section_count?, sheet_names?,
              slide_count?}``.
            * ``truncated`` -- ``True`` when content exceeded the token cap.
    """
    try:
        source_service = await _get_source_service()
        record, err = await _load_owned_record(
            tool_context,
            document_id,
            source_service,
        )
        if err is not None:
            return err
        assert record is not None  # _load_owned_record contract: err None => record set

        text = record.get("extracted_text")
        if not text:
            # Lazy extract from binary
            binary_url = record.get("binary_url")
            if not binary_url:
                return {
                    "status": "error",
                    "message": "Document has no binary URL to extract from",
                }
            binary = await _fetch_binary(binary_url)
            extraction_service = _get_extraction_service()
            text = await extraction_service.extract_text(
                binary=binary,
                doc_class=record["doc_class"],
            )
            await source_service.set_extracted_text(document_id, text)

        truncated_text, truncated = _truncate_text(text)

        structure: dict[str, Any] = {"type": record["doc_class"]}
        source = record.get("source")
        if source:
            if "sections" in source:
                structure["section_count"] = len(source["sections"])
            if "sheets" in source:
                structure["sheet_names"] = [s["name"] for s in source["sheets"]]
            if "slides" in source:
                structure["slide_count"] = len(source["slides"])

        return {
            "status": "success",
            "text": truncated_text,
            "structure": structure,
            "truncated": truncated,
        }
    except Exception as exc:
        logger.exception("read_document_content failed")
        return {"status": "error", "message": str(exc)}


# More tools follow in subsequent commits.

DOCUMENT_EDITOR_TOOLS: list = [read_document_content]


__all__ = ["DOCUMENT_EDITOR_TOOLS", "read_document_content"]
