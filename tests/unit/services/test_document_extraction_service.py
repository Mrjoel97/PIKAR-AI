# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for DocumentExtractionService -- binary -> text and binary -> source.

Round-trip strategy: the existing ``render_*_from_source`` helpers in
``document_service`` produce real binary; that binary is fed back through
``DocumentExtractionService`` and the output is asserted to contain the
expected content. PDF round-trip relies on weasyprint, which needs system
C libraries (cairo/pango/gdk-pixbuf) that are absent on some Windows boxes;
those two tests are skipped in that case (matching the existing
``test_document_service_render_from_source`` pattern).
"""

from __future__ import annotations

import pytest

from app.services.document_extraction_service import (
    DocumentExtractionService,
    UnsupportedFormatError,
)
from app.services.document_service import (
    render_docx_from_source,
    render_pdf_from_source,
    render_pptx_from_source,
    render_xlsx_from_source,
)

# weasyprint requires system C libraries that are absent on some Windows boxes.
# Mirror the skip guard used by test_document_service_render_from_source so the
# PDF round-trips skip cleanly when the system deps are missing.
try:  # pragma: no cover - environment guard
    import weasyprint  # noqa: F401

    _WEASYPRINT_AVAILABLE = True
    _WEASYPRINT_SKIP_REASON = ""
except Exception as exc:  # pragma: no cover - environment guard
    _WEASYPRINT_AVAILABLE = False
    _WEASYPRINT_SKIP_REASON = f"weasyprint unavailable: {exc}"

requires_weasyprint = pytest.mark.skipif(
    not _WEASYPRINT_AVAILABLE,
    reason=_WEASYPRINT_SKIP_REASON or "weasyprint system deps unavailable",
)


@pytest.fixture
def service() -> DocumentExtractionService:
    """Return a fresh DocumentExtractionService for each test."""
    return DocumentExtractionService()


@requires_weasyprint
@pytest.mark.asyncio
async def test_extract_text_from_pdf(service: DocumentExtractionService) -> None:
    """Round-trip a PDF and confirm the section content is recovered as text."""
    pdf = await render_pdf_from_source(
        {
            "title": "Sample",
            "sections": [
                {
                    "heading": "Intro",
                    "content": "Hello world from extraction test.",
                },
            ],
        }
    )

    text = await service.extract_text(binary=pdf, doc_class="report")

    assert "Hello world from extraction test." in text


@pytest.mark.asyncio
async def test_extract_text_from_xlsx(service: DocumentExtractionService) -> None:
    """Round-trip an XLSX and confirm cell values are recovered as text."""
    xlsx = await render_xlsx_from_source(
        {"sheets": [{"name": "Data", "rows": [["Name", "Age"], ["Alice", 30]]}]}
    )

    text = await service.extract_text(binary=xlsx, doc_class="spreadsheet")

    assert "Alice" in text
    assert "30" in text


@pytest.mark.asyncio
async def test_extract_text_from_pptx(service: DocumentExtractionService) -> None:
    """Round-trip a PPTX and confirm title + body text are recovered."""
    pptx = await render_pptx_from_source(
        {
            "title": "Deck",
            "slides": [
                {
                    "layout": "title",
                    "title": "Findings",
                    "body": "Conclusion: ship it.",
                    "speaker_notes": None,
                },
            ],
        }
    )

    text = await service.extract_text(binary=pptx, doc_class="presentation")

    assert "Findings" in text
    assert "ship it" in text


@pytest.mark.asyncio
async def test_extract_text_from_docx(service: DocumentExtractionService) -> None:
    """Round-trip a DOCX and confirm body paragraph text is recovered."""
    docx = await render_docx_from_source(
        {
            "title": "Doc",
            "sections": [
                {"heading": "S", "content": "Some unique paragraph text."},
            ],
        }
    )

    text = await service.extract_text(binary=docx, doc_class="word")

    assert "Some unique paragraph text." in text


@pytest.mark.asyncio
async def test_extract_text_raises_on_unsupported_class(
    service: DocumentExtractionService,
) -> None:
    """Unsupported doc_class fires UnsupportedFormatError before any decoding."""
    with pytest.raises(UnsupportedFormatError):
        await service.extract_text(binary=b"...", doc_class="image")


@requires_weasyprint
@pytest.mark.asyncio
async def test_fork_to_source_pdf_produces_report_source(
    service: DocumentExtractionService,
) -> None:
    """fork_to_source on a PDF produces a report-shaped source dict."""
    pdf = await render_pdf_from_source(
        {
            "title": "Report",
            "sections": [
                {"heading": "S1", "content": "Para A.\n\nPara B."},
            ],
        }
    )

    source = await service.fork_to_source(binary=pdf, doc_class="report")

    assert "sections" in source
    assert isinstance(source["sections"], list)
    assert len(source["sections"]) >= 1


@pytest.mark.asyncio
async def test_fork_to_source_xlsx_produces_sheet_source(
    service: DocumentExtractionService,
) -> None:
    """fork_to_source on an XLSX produces a spreadsheet-shaped source dict."""
    xlsx = await render_xlsx_from_source(
        {"sheets": [{"name": "S", "rows": [["a", "b"], [1, 2]]}]}
    )

    source = await service.fork_to_source(binary=xlsx, doc_class="spreadsheet")

    assert "sheets" in source
    assert source["sheets"][0]["rows"][0] == ["a", "b"]
