# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for document_editor agent tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


@pytest.fixture
def tool_context():
    """Mock ADK tool context with state dict carrying user_id."""
    ctx = MagicMock()
    ctx.state = {"user_id": str(uuid4()), "agent_id": "test-agent"}
    return ctx


@pytest.fixture
def mock_services(monkeypatch):
    """Patch the service factories used inside ``document_editor``.

    Returns ``(source_service, version_service, extraction_service)`` --
    all ``AsyncMock``; tests configure return values per-case.
    """
    source_service = AsyncMock()
    version_service = AsyncMock()
    extraction_service = AsyncMock()

    from app.agents.tools import document_editor

    monkeypatch.setattr(
        document_editor,
        "_get_source_service",
        AsyncMock(return_value=source_service),
    )
    monkeypatch.setattr(
        document_editor,
        "_get_version_service",
        AsyncMock(return_value=version_service),
    )
    monkeypatch.setattr(
        document_editor,
        "_get_extraction_service",
        lambda: extraction_service,
    )
    return source_service, version_service, extraction_service


@pytest.mark.asyncio
async def test_read_document_content_returns_cached_text(tool_context, mock_services):
    """Cached extracted_text is returned untouched and not flagged truncated."""
    from app.agents.tools.document_editor import read_document_content

    source_service, _, _ = mock_services
    source_service.get.return_value = {
        "user_id": tool_context.state["user_id"],
        "document_id": "doc-1",
        "doc_class": "report",
        "extracted_text": "Cached text contents.",
        "binary_url": "https://example.com/x.pdf",
        "source": {"sections": [{"heading": "H", "content": "c"}]},
    }

    result = await read_document_content(tool_context=tool_context, document_id="doc-1")

    assert result["status"] == "success"
    assert result["text"] == "Cached text contents."
    assert result["truncated"] is False
    assert result["structure"] == {"type": "report", "section_count": 1}


@pytest.mark.asyncio
async def test_read_document_content_triggers_lazy_extraction(
    tool_context,
    mock_services,
    monkeypatch,
):
    """Empty extracted_text triggers _fetch_binary + extract_text + cache write."""
    from app.agents.tools import document_editor
    from app.agents.tools.document_editor import read_document_content

    source_service, _, extraction_service = mock_services
    source_service.get.return_value = {
        "user_id": tool_context.state["user_id"],
        "document_id": "doc-2",
        "doc_class": "report",
        "extracted_text": None,
        "binary_url": "https://example.com/x.pdf",
        "source": None,
    }
    fake_binary = b"%PDF-fake-bytes"

    fetch_mock = AsyncMock(return_value=fake_binary)
    monkeypatch.setattr(document_editor, "_fetch_binary", fetch_mock)
    extraction_service.extract_text.return_value = "Freshly extracted."

    result = await read_document_content(tool_context=tool_context, document_id="doc-2")

    assert result["status"] == "success"
    assert result["text"] == "Freshly extracted."
    assert result["truncated"] is False
    fetch_mock.assert_awaited_once_with("https://example.com/x.pdf")
    extraction_service.extract_text.assert_awaited_once_with(
        binary=fake_binary,
        doc_class="report",
    )
    source_service.set_extracted_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_read_document_content_truncates_long_text(tool_context, mock_services):
    """Text exceeding the cap is truncated with the marker appended."""
    from app.agents.tools.document_editor import read_document_content

    source_service, _, _ = mock_services
    long_text = "word " * 50_000  # ~50K tokens
    source_service.get.return_value = {
        "user_id": tool_context.state["user_id"],
        "document_id": "doc-3",
        "doc_class": "report",
        "extracted_text": long_text,
        "binary_url": "https://example.com/x.pdf",
        "source": None,
    }

    result = await read_document_content(tool_context=tool_context, document_id="doc-3")

    assert result["status"] == "success"
    assert result["truncated"] is True
    # 7500-word cap + marker; allow generous slack for the marker.
    assert len(result["text"].split()) <= 11_000
    assert "[...truncated...]" in result["text"]


@pytest.mark.asyncio
async def test_read_document_content_rejects_other_users_doc(
    tool_context,
    mock_services,
):
    """A document owned by a different user is rejected with an error envelope."""
    from app.agents.tools.document_editor import read_document_content

    source_service, _, _ = mock_services
    other_user_id = str(uuid4())
    assert other_user_id != tool_context.state["user_id"]
    source_service.get.return_value = {
        "user_id": other_user_id,
        "document_id": "doc-4",
        "doc_class": "report",
        "extracted_text": "Secrets.",
        "binary_url": "https://example.com/x.pdf",
        "source": None,
    }

    result = await read_document_content(tool_context=tool_context, document_id="doc-4")

    assert result["status"] == "error"
    assert "not accessible" in result["message"].lower()
