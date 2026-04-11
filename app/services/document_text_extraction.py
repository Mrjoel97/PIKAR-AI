# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Shared MIME-aware document text extraction for vault ingestion.

This module centralises text extraction so both the user-facing Knowledge
Vault (``app/routers/vault.py``) and the admin knowledge service
(``app/services/knowledge_service.py``) can share the same truthful parsing
behaviour instead of maintaining separate, weaker ad-hoc decoders.

Exports:
    extract_text_from_bytes — Extract text from file bytes by MIME type.
                              Returns ``None`` for storage-only (non-searchable)
                              formats; raises ``ExtractionError`` on parse failure.
    is_searchable_format    — Return True when a MIME type maps to a format that
                              can be embedded as searchable text.
    ExtractionError         — Raised when extraction is attempted but fails.

Searchable formats (at minimum for v7):
    - text/plain
    - text/markdown, text/x-markdown, text/md
    - application/pdf                           (via pypdf)
    - application/vnd.openxmlformats-officedocument.wordprocessingml.document
                                                (via python-docx)

All other MIME types (image/*, video/*, audio/*, application/octet-stream not
matching text, etc.) are treated as storage-only and return ``None``.
"""

from __future__ import annotations

import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy imports — keep module importable even if pypdf / docx are absent in
# some environments.  The names are module-level so tests can patch them.
# ---------------------------------------------------------------------------

try:
    import pypdf  # type: ignore[import]
except ImportError:  # pragma: no cover
    pypdf = None  # type: ignore[assignment]

try:
    import docx  # type: ignore[import]
except ImportError:  # pragma: no cover
    docx = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Public contract
# ---------------------------------------------------------------------------

#: MIME types that can be embedded as searchable text
_SEARCHABLE_MIMES: frozenset[str] = frozenset(
    [
        "text/plain",
        "text/markdown",
        "text/x-markdown",
        "text/md",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
)


class ExtractionError(Exception):
    """Raised when a supported format cannot be parsed (e.g. corrupt file)."""


def _normalise_mime(mime_type: str | None) -> str:
    """Strip charset / boundary suffixes and lowercase the MIME string."""
    if not mime_type:
        return ""
    return mime_type.lower().split(";")[0].strip()


def is_searchable_format(mime_type: str | None) -> bool:
    """Return ``True`` when *mime_type* maps to a searchable text format.

    Args:
        mime_type: Raw MIME type string (may include charset suffix).

    Returns:
        ``True`` if the format can be embedded, ``False`` otherwise.
    """
    normalised = _normalise_mime(mime_type)
    if not normalised:
        return False
    # Also accept any text/* sub-type
    if normalised.startswith("text/"):
        return True
    return normalised in _SEARCHABLE_MIMES


def extract_text_from_bytes(
    file_bytes: bytes,
    mime_type: str | None,
) -> Optional[str]:
    """Extract searchable text from raw file bytes.

    Args:
        file_bytes: Raw binary content downloaded from storage.
        mime_type: MIME type string for the file (may include charset suffix).

    Returns:
        Extracted text string (may be empty ``""`` if the file has no text),
        or ``None`` if *mime_type* is not a searchable format (storage-only).

    Raises:
        ExtractionError: When the file is a supported searchable format but
            parsing fails (e.g. corrupt PDF, truncated DOCX).
    """
    normalised = _normalise_mime(mime_type)

    # --- Storage-only formats: return None immediately ---
    if not is_searchable_format(normalised):
        return None

    # --- PDF ---
    if normalised == "application/pdf":
        return _extract_pdf(file_bytes)

    # --- DOCX ---
    if normalised == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return _extract_docx(file_bytes)

    # --- Plain text / markdown / other text/* ---
    return file_bytes.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Internal extraction helpers
# ---------------------------------------------------------------------------


def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes via pypdf.

    Raises:
        ExtractionError: On any pypdf parse failure.
    """
    if pypdf is None:  # pragma: no cover
        raise ExtractionError("PDF extraction unavailable: pypdf not installed")
    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        parts: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return "\n".join(parts)
    except Exception as exc:
        raise ExtractionError(f"PDF extraction failed: {exc}") from exc


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX bytes via python-docx.

    Raises:
        ExtractionError: On any python-docx parse failure.
    """
    if docx is None:  # pragma: no cover
        raise ExtractionError("DOCX extraction unavailable: python-docx not installed")
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text)
    except Exception as exc:
        raise ExtractionError(f"DOCX extraction failed: {exc}") from exc
