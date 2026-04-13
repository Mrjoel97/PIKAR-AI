# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the Gemini Vision OCR tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ocr_document_with_file_content():
    """ocr_document with file_content bytes returns extracted text."""
    from app.agents.tools.ocr_tools import ocr_document

    fake_bytes = b"\x89PNG\r\nfake image bytes"

    with patch(
        "app.agents.tools.ocr_tools._run_ocr_on_bytes",
        new=AsyncMock(return_value="Invoice total: $1,234.56"),
    ):
        result = await ocr_document(name="receipt.png", file_content=fake_bytes)

    assert result["success"] is True
    assert "extracted_text" in result
    assert "Invoice total" in result["extracted_text"]
    assert result["tool"] == "ocr_document"


@pytest.mark.asyncio
async def test_ocr_document_extracted_text_passthrough():
    """If extracted_text is provided directly (backward compat), return it as-is."""
    from app.agents.tools.ocr_tools import ocr_document

    result = await ocr_document(
        name="old_scan.pdf",
        extracted_text="Previously extracted content from the PDF.",
    )

    assert result["success"] is True
    assert result["extracted_text"] == "Previously extracted content from the PDF."
    assert result["tool"] == "ocr_document"


@pytest.mark.asyncio
async def test_ocr_document_with_file_url():
    """ocr_document with file_url fetches bytes and runs OCR."""
    from app.agents.tools.ocr_tools import ocr_document

    fake_bytes = b"\xff\xd8\xffJPEG fake bytes"
    fake_response = MagicMock()
    fake_response.content = fake_bytes
    fake_response.raise_for_status = MagicMock()

    with patch(
        "app.agents.tools.ocr_tools._run_ocr_on_bytes",
        new=AsyncMock(return_value="Name: John Doe"),
    ), patch("app.agents.tools.ocr_tools.httpx.AsyncClient") as mock_http_class:
        mock_http_ctx = AsyncMock()
        mock_http_ctx.__aenter__ = AsyncMock(return_value=mock_http_ctx)
        mock_http_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_http_ctx.get = AsyncMock(return_value=fake_response)
        mock_http_class.return_value = mock_http_ctx

        result = await ocr_document(
            name="photo.jpg",
            file_url="https://example.com/storage/photo.jpg",
        )

    assert result["success"] is True
    assert "Name: John Doe" in result["extracted_text"]


@pytest.mark.asyncio
async def test_ocr_document_no_input_returns_error():
    """Missing file_content and file_url and no extracted_text returns success=False."""
    from app.agents.tools.ocr_tools import ocr_document

    result = await ocr_document(name="empty.png")

    assert result["success"] is False
    assert "error" in result
    assert result["tool"] == "ocr_document"


@pytest.mark.asyncio
async def test_ocr_document_ocr_failure():
    """OCR failure returns success=False with error message (no crash)."""
    from app.agents.tools.ocr_tools import ocr_document

    fake_bytes = b"\x89PNG fake"

    with patch(
        "app.agents.tools.ocr_tools._run_ocr_on_bytes",
        new=AsyncMock(side_effect=RuntimeError("Simulated Gemini Vision failure")),
    ):
        result = await ocr_document(name="broken.png", file_content=fake_bytes)

    assert result["success"] is False
    assert "error" in result
    assert result["tool"] == "ocr_document"


@pytest.mark.asyncio
async def test_ocr_document_jpeg_mime_type():
    """JPEG file extension maps to image/jpeg mime type (no error raised)."""
    from app.agents.tools.ocr_tools import ocr_document

    fake_bytes = b"\xff\xd8\xffJPEG bytes"

    with patch(
        "app.agents.tools.ocr_tools._run_ocr_on_bytes",
        new=AsyncMock(return_value="Extracted from JPEG"),
    ):
        result = await ocr_document(name="photo.jpeg", file_content=fake_bytes)

    assert result["success"] is True


@pytest.mark.asyncio
async def test_ocr_document_pdf_mime_type():
    """PDF file extension maps to application/pdf mime type."""
    from app.agents.tools.ocr_tools import ocr_document

    fake_bytes = b"%PDF-1.4 fake pdf"

    with patch(
        "app.agents.tools.ocr_tools._run_ocr_on_bytes",
        new=AsyncMock(return_value="Page 1 content: Hello World"),
    ):
        result = await ocr_document(name="contract.pdf", file_content=fake_bytes)

    assert result["success"] is True
    assert "Hello World" in result["extracted_text"]


@pytest.mark.asyncio
async def test_ocr_document_unknown_extension_defaults_gracefully():
    """Unknown file extension still works (defaults to image/png)."""
    from app.agents.tools.ocr_tools import ocr_document

    fake_bytes = b"some binary data"

    with patch(
        "app.agents.tools.ocr_tools._run_ocr_on_bytes",
        new=AsyncMock(return_value="Unknown format text"),
    ):
        result = await ocr_document(name="scan.xyz", file_content=fake_bytes)

    assert result["success"] is True


@pytest.mark.asyncio
async def test_ocr_document_detect_mime_types():
    """Mime type detection covers all supported extensions."""
    from app.agents.tools.ocr_tools import _detect_mime_type

    assert _detect_mime_type("image.png") == "image/png"
    assert _detect_mime_type("photo.jpg") == "image/jpeg"
    assert _detect_mime_type("photo.jpeg") == "image/jpeg"
    assert _detect_mime_type("doc.pdf") == "application/pdf"
    assert _detect_mime_type("scan.tiff") == "image/tiff"
    assert _detect_mime_type("unknown.xyz") == "image/png"  # default
