# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for document_text_extraction shared helper.

Covers:
- extract_text_from_bytes for plain text, markdown, PDF, DOCX
- Unsupported / non-extractable format behavior (returns storage-only signal)
- Extraction failure handling (e.g. corrupt PDF bytes)
"""

from __future__ import annotations

import io
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers for building minimal fixture bytes
# ---------------------------------------------------------------------------


def _make_pdf_bytes(text: str = "Hello PDF world") -> bytes:
    """Return minimal valid PDF bytes containing *text* via pypdf mock."""
    return b"%PDF-1.4 fake-pdf-bytes-for-testing"


def _make_docx_bytes(text: str = "Hello DOCX world") -> bytes:
    """Return placeholder bytes; actual parsing is mocked."""
    return b"PK\x03\x04fake-docx-bytes-for-testing"


# ---------------------------------------------------------------------------
# Tests: extract_text_from_bytes
# ---------------------------------------------------------------------------


class TestExtractTextFromBytes:
    """Tests for the public extract_text_from_bytes entry-point."""

    def test_plain_text_utf8(self):
        from app.services.document_text_extraction import extract_text_from_bytes

        content = "Hello, plain text world!"
        result = extract_text_from_bytes(content.encode("utf-8"), "text/plain")
        assert "Hello, plain text world!" in result
        assert result.strip() != ""

    def test_markdown_text(self):
        from app.services.document_text_extraction import extract_text_from_bytes

        md = "# Title\n\nSome **bold** paragraph."
        result = extract_text_from_bytes(md.encode("utf-8"), "text/markdown")
        assert "Title" in result
        assert "paragraph" in result

    def test_markdown_x_mime(self):
        from app.services.document_text_extraction import extract_text_from_bytes

        md = "# Heading\nContent here"
        result = extract_text_from_bytes(md.encode("utf-8"), "text/x-markdown")
        assert "Heading" in result

    def test_pdf_extraction(self):
        """PDF bytes should be routed through pypdf extraction."""
        from app.services.document_text_extraction import extract_text_from_bytes

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Extracted PDF content"
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]

        with patch("app.services.document_text_extraction.pypdf") as mock_pypdf:
            mock_pypdf.PdfReader.return_value = mock_reader
            result = extract_text_from_bytes(b"fake-pdf", "application/pdf")

        assert "Extracted PDF content" in result
        mock_pypdf.PdfReader.assert_called_once()

    def test_docx_extraction(self):
        """DOCX bytes should be routed through python-docx extraction."""
        from app.services.document_text_extraction import extract_text_from_bytes

        mock_para = MagicMock()
        mock_para.text = "DOCX paragraph content"
        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para]

        with patch("app.services.document_text_extraction.docx") as mock_docx:
            mock_docx.Document.return_value = mock_doc
            result = extract_text_from_bytes(b"fake-docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        assert "DOCX paragraph content" in result
        mock_docx.Document.assert_called_once()

    def test_unsupported_mime_returns_storage_only(self):
        """Unsupported MIME types should return None (storage-only)."""
        from app.services.document_text_extraction import extract_text_from_bytes

        result = extract_text_from_bytes(b"\x00\x01\x02binary", "image/png")
        assert result is None

    def test_unsupported_video_returns_storage_only(self):
        from app.services.document_text_extraction import extract_text_from_bytes

        result = extract_text_from_bytes(b"fake-video-bytes", "video/mp4")
        assert result is None

    def test_corrupt_pdf_raises_extraction_error(self):
        """Corrupt PDF bytes should raise ExtractionError."""
        from app.services.document_text_extraction import (
            ExtractionError,
            extract_text_from_bytes,
        )

        with patch("app.services.document_text_extraction.pypdf") as mock_pypdf:
            mock_pypdf.PdfReader.side_effect = Exception("malformed PDF")
            with pytest.raises(ExtractionError, match="PDF"):
                extract_text_from_bytes(b"bad-pdf-bytes", "application/pdf")

    def test_corrupt_docx_raises_extraction_error(self):
        """Corrupt DOCX bytes should raise ExtractionError."""
        from app.services.document_text_extraction import (
            ExtractionError,
            extract_text_from_bytes,
        )

        with patch("app.services.document_text_extraction.docx") as mock_docx:
            mock_docx.Document.side_effect = Exception("bad zip")
            with pytest.raises(ExtractionError, match="DOCX"):
                extract_text_from_bytes(b"bad-docx-bytes", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    def test_text_mime_with_utf8_errors_uses_replace(self):
        """Text MIME with non-UTF-8 bytes should decode with replace rather than raise."""
        from app.services.document_text_extraction import extract_text_from_bytes

        # latin-1 byte in a text/plain blob
        result = extract_text_from_bytes(b"caf\xe9", "text/plain")
        assert result is not None
        assert "caf" in result

    def test_pdf_with_empty_pages_returns_empty_string(self):
        """PDF with no extractable text should return empty string, not None."""
        from app.services.document_text_extraction import extract_text_from_bytes

        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]

        with patch("app.services.document_text_extraction.pypdf") as mock_pypdf:
            mock_pypdf.PdfReader.return_value = mock_reader
            result = extract_text_from_bytes(b"pdf-no-text", "application/pdf")

        # Returns empty string (not None): PDF was searchable format but yielded no text
        assert result == ""

    def test_mime_with_charset_suffix_stripped(self):
        """MIME types like 'text/plain; charset=utf-8' should be handled correctly."""
        from app.services.document_text_extraction import extract_text_from_bytes

        result = extract_text_from_bytes(b"Hello charset", "text/plain; charset=utf-8")
        assert result is not None
        assert "Hello charset" in result


class TestIsSearchableFormat:
    """Tests for the is_searchable_format helper."""

    def test_pdf_is_searchable(self):
        from app.services.document_text_extraction import is_searchable_format

        assert is_searchable_format("application/pdf") is True

    def test_docx_is_searchable(self):
        from app.services.document_text_extraction import is_searchable_format

        assert is_searchable_format(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ) is True

    def test_plain_text_is_searchable(self):
        from app.services.document_text_extraction import is_searchable_format

        assert is_searchable_format("text/plain") is True

    def test_markdown_is_searchable(self):
        from app.services.document_text_extraction import is_searchable_format

        assert is_searchable_format("text/markdown") is True

    def test_image_not_searchable(self):
        from app.services.document_text_extraction import is_searchable_format

        assert is_searchable_format("image/png") is False

    def test_video_not_searchable(self):
        from app.services.document_text_extraction import is_searchable_format

        assert is_searchable_format("video/mp4") is False

    def test_empty_mime_not_searchable(self):
        from app.services.document_text_extraction import is_searchable_format

        assert is_searchable_format("") is False

    def test_none_mime_not_searchable(self):
        from app.services.document_text_extraction import is_searchable_format

        assert is_searchable_format(None) is False  # type: ignore[arg-type]
