# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Round-trip tests for the render_*_from_source pure helpers.

These tests actually invoke weasyprint, openpyxl, python-pptx, and python-docx
to verify the produced bytes carry the right magic numbers. PDF rendering may
fail on systems without weasyprint's required system libraries (cairo,
pango, gdk-pixbuf); in that case the PDF test is skipped.
"""

from __future__ import annotations

import pytest

# weasyprint requires system C libraries that are absent on some Windows boxes.
# If the import fails at collection time we skip the PDF round-trip test rather
# than fail the whole module — the other 3 builders (openpyxl/pptx/docx) work
# pure-Python.
try:  # pragma: no cover - environment guard
    import weasyprint  # noqa: F401

    _WEASYPRINT_AVAILABLE = True
    _WEASYPRINT_SKIP_REASON = ""
except Exception as exc:  # pragma: no cover - environment guard
    _WEASYPRINT_AVAILABLE = False
    _WEASYPRINT_SKIP_REASON = f"weasyprint unavailable: {exc}"

from app.services.document_service import (
    render_docx_from_source,
    render_pdf_from_source,
    render_pptx_from_source,
    render_xlsx_from_source,
)


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _WEASYPRINT_AVAILABLE,
    reason=_WEASYPRINT_SKIP_REASON or "weasyprint unavailable",
)
async def test_render_pdf_from_source_returns_bytes() -> None:
    """PDF output starts with the %PDF magic bytes."""
    source = {
        "title": "Quarterly Report",
        "sections": [
            {"heading": "Overview", "content": "First paragraph.\n\nSecond paragraph."},
            {"heading": "Outlook", "content": "Looking up."},
        ],
    }
    result = await render_pdf_from_source(source)
    assert isinstance(result, bytes)
    assert result.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_render_xlsx_from_source_returns_bytes() -> None:
    """XLSX output starts with the PK ZIP magic bytes."""
    source = {
        "sheets": [
            {"name": "Sheet1", "rows": [["A", "B"], [1, 2]]},
        ],
    }
    result = await render_xlsx_from_source(source)
    assert isinstance(result, bytes)
    assert result.startswith(b"PK")


@pytest.mark.asyncio
async def test_render_pptx_from_source_returns_bytes() -> None:
    """PPTX output starts with the PK ZIP magic bytes."""
    source = {
        "title": "Pitch",
        "slides": [
            {
                "layout": "title_and_content",
                "title": "Hello",
                "body": "Hello",
                "speaker_notes": None,
            },
        ],
    }
    result = await render_pptx_from_source(source)
    assert isinstance(result, bytes)
    assert result.startswith(b"PK")


@pytest.mark.asyncio
async def test_render_docx_from_source_returns_bytes() -> None:
    """DOCX output starts with the PK ZIP magic bytes."""
    source = {
        "title": "Memo",
        "sections": [
            {"heading": "Background", "content": "Para one.\n\nPara two."},
        ],
    }
    result = await render_docx_from_source(source)
    assert isinstance(result, bytes)
    assert result.startswith(b"PK")


@pytest.mark.asyncio
async def test_render_pdf_rejects_missing_sections() -> None:
    """render_pdf_from_source raises ValueError when 'sections' key is absent."""
    with pytest.raises(ValueError, match="sections"):
        await render_pdf_from_source({"title": "No sections here"})
