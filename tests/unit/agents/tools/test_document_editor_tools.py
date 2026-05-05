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


# ---------------------------------------------------------------------------
# Helpers used by the edit-tool tests
# ---------------------------------------------------------------------------


def _patch_upload_render(monkeypatch, url: str = "https://example.com/v2.bin") -> None:
    """Patch ``_upload_render`` to return a stub URL without touching storage."""
    from app.agents.tools import document_editor

    async def fake_upload(**kwargs):
        return url

    monkeypatch.setattr(document_editor, "_upload_render", fake_upload)


# ---------------------------------------------------------------------------
# edit_report_doc
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edit_report_doc_replace_section(
    tool_context, mock_services, monkeypatch
):
    """Happy path: ``replace_section`` mutates source, calls update + append."""
    from app.agents.tools import document_editor
    from app.agents.tools.document_editor import edit_report_doc

    source_service, version_service, _ = mock_services
    source_service.get.return_value = {
        "user_id": tool_context.state["user_id"],
        "document_id": "doc-r1",
        "doc_class": "report",
        "binary_url": "https://example.com/old.pdf",
        "source": {
            "title": "Q1 Report",
            "sections": [
                {"heading": "Intro", "content": "Old intro."},
                {"heading": "Body", "content": "Old body."},
            ],
        },
    }
    version_service.append.return_value = {"id": "v2"}

    async def fake_render(source):
        return b"%PDF-new"

    monkeypatch.setattr(
        "app.services.document_service.render_pdf_from_source",
        fake_render,
    )
    _patch_upload_render(monkeypatch, url="https://example.com/v2.pdf")

    result = await edit_report_doc(
        tool_context=tool_context,
        document_id="doc-r1",
        operation="replace_section",
        target="Intro",
        new_content="New intro.",
    )

    assert result["status"] == "success"
    assert result["_workspace_command"] is True
    assert result["new_version_id"] == "v2"
    assert result["new_render_url"] == "https://example.com/v2.pdf"

    source_service.update_source.assert_awaited_once()
    update_kwargs = source_service.update_source.await_args.kwargs
    assert update_kwargs["document_id"] == "doc-r1"
    assert update_kwargs["new_binary_url"] == "https://example.com/v2.pdf"
    assert update_kwargs["new_source"]["sections"][0]["content"] == "New intro."

    version_service.append.assert_awaited_once()
    append_kwargs = version_service.append.await_args.kwargs
    assert append_kwargs["document_id"] == "doc-r1"
    assert append_kwargs["binary_url"] == "https://example.com/v2.pdf"
    assert append_kwargs["created_by"] == "agent"

    # Sanity: the document_editor module was imported (helps catch import-time errors).
    assert hasattr(document_editor, "edit_report_doc")


@pytest.mark.asyncio
async def test_edit_report_doc_target_not_found(tool_context, mock_services):
    """Anchor heading not in source.sections returns an error envelope."""
    from app.agents.tools.document_editor import edit_report_doc

    source_service, _, _ = mock_services
    source_service.get.return_value = {
        "user_id": tool_context.state["user_id"],
        "document_id": "doc-r2",
        "doc_class": "report",
        "binary_url": None,
        "source": {
            "title": "T",
            "sections": [{"heading": "Intro", "content": "x"}],
        },
    }

    result = await edit_report_doc(
        tool_context=tool_context,
        document_id="doc-r2",
        operation="replace_section",
        target="Missing",
        new_content="x",
    )

    assert result["status"] == "error"
    assert "missing" in result["message"].lower()


@pytest.mark.asyncio
async def test_edit_report_doc_rejects_other_users_doc(tool_context, mock_services):
    """Other-user record yields the standard ``not accessible`` error."""
    from app.agents.tools.document_editor import edit_report_doc

    source_service, _, _ = mock_services
    other_user_id = str(uuid4())
    assert other_user_id != tool_context.state["user_id"]
    source_service.get.return_value = {
        "user_id": other_user_id,
        "document_id": "doc-r3",
        "doc_class": "report",
        "binary_url": None,
        "source": {"title": "T", "sections": [{"heading": "Intro", "content": "x"}]},
    }

    result = await edit_report_doc(
        tool_context=tool_context,
        document_id="doc-r3",
        operation="replace_section",
        target="Intro",
        new_content="x",
    )

    assert result["status"] == "error"
    assert "not accessible" in result["message"].lower()


# ---------------------------------------------------------------------------
# edit_spreadsheet
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edit_spreadsheet_set_cell(tool_context, mock_services, monkeypatch):
    """``set_cell`` sets B2=42 and persists the mutated source."""
    from app.agents.tools.document_editor import edit_spreadsheet

    source_service, version_service, _ = mock_services
    source_service.get.return_value = {
        "user_id": tool_context.state["user_id"],
        "document_id": "doc-s1",
        "doc_class": "spreadsheet",
        "binary_url": None,
        "source": {
            "sheets": [
                {
                    "name": "Sheet1",
                    "rows": [
                        ["A1", "B1"],
                        ["A2", "B2"],
                    ],
                }
            ]
        },
    }
    version_service.append.return_value = {"id": "v2"}

    async def fake_render(source):
        return b"PK-xlsx"

    monkeypatch.setattr(
        "app.services.document_service.render_xlsx_from_source",
        fake_render,
    )
    _patch_upload_render(monkeypatch, url="https://example.com/v2.xlsx")

    result = await edit_spreadsheet(
        tool_context=tool_context,
        document_id="doc-s1",
        operation="set_cell",
        sheet_name="Sheet1",
        cell="B2",
        value=42,
    )

    assert result["status"] == "success"
    update_kwargs = source_service.update_source.await_args.kwargs
    new_source = update_kwargs["new_source"]
    assert new_source["sheets"][0]["rows"][1][1] == 42


# ---------------------------------------------------------------------------
# edit_presentation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edit_presentation_edit_text(tool_context, mock_services, monkeypatch):
    """``edit_text`` updates slide 0's title from 'Old' to 'Updated Title'."""
    from app.agents.tools.document_editor import edit_presentation

    source_service, version_service, _ = mock_services
    source_service.get.return_value = {
        "user_id": tool_context.state["user_id"],
        "document_id": "doc-p1",
        "doc_class": "presentation",
        "binary_url": None,
        "source": {
            "slides": [
                {"layout": "title", "title": "Old", "body": "x", "speaker_notes": None},
            ]
        },
    }
    version_service.append.return_value = {"id": "v2"}

    async def fake_render(source):
        return b"PK-pptx"

    monkeypatch.setattr(
        "app.services.document_service.render_pptx_from_source",
        fake_render,
    )
    _patch_upload_render(monkeypatch, url="https://example.com/v2.pptx")

    result = await edit_presentation(
        tool_context=tool_context,
        document_id="doc-p1",
        operation="edit_text",
        slide_index=0,
        field="title",
        new_value="Updated Title",
    )

    assert result["status"] == "success"
    new_source = source_service.update_source.await_args.kwargs["new_source"]
    assert new_source["slides"][0]["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_edit_presentation_insert_slide(tool_context, mock_services, monkeypatch):
    """``insert_slide`` adds a new slide at index 1, doubling slide count."""
    from app.agents.tools.document_editor import edit_presentation

    source_service, version_service, _ = mock_services
    source_service.get.return_value = {
        "user_id": tool_context.state["user_id"],
        "document_id": "doc-p2",
        "doc_class": "presentation",
        "binary_url": None,
        "source": {
            "slides": [
                {
                    "layout": "title",
                    "title": "Cover",
                    "body": "",
                    "speaker_notes": None,
                },
            ]
        },
    }
    version_service.append.return_value = {"id": "v2"}

    async def fake_render(source):
        return b"PK-pptx"

    monkeypatch.setattr(
        "app.services.document_service.render_pptx_from_source",
        fake_render,
    )
    _patch_upload_render(monkeypatch, url="https://example.com/v2.pptx")

    result = await edit_presentation(
        tool_context=tool_context,
        document_id="doc-p2",
        operation="insert_slide",
        slide_index=1,
        layout="title_and_body",
        title="New Slide",
        body="Bullet 1\nBullet 2",
    )

    assert result["status"] == "success"
    new_source = source_service.update_source.await_args.kwargs["new_source"]
    assert len(new_source["slides"]) == 2
    assert new_source["slides"][1]["title"] == "New Slide"


# ---------------------------------------------------------------------------
# edit_word_doc
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edit_word_doc_replace_paragraph(
    tool_context, mock_services, monkeypatch
):
    """``replace_paragraph`` swaps the body of the named section."""
    from app.agents.tools.document_editor import edit_word_doc

    source_service, version_service, _ = mock_services
    source_service.get.return_value = {
        "user_id": tool_context.state["user_id"],
        "document_id": "doc-w1",
        "doc_class": "word",
        "binary_url": None,
        "source": {
            "title": "Memo",
            "sections": [
                {"heading": "Intro", "content": "Old intro."},
            ],
        },
    }
    version_service.append.return_value = {"id": "v2"}

    async def fake_render(source):
        return b"PK-docx"

    monkeypatch.setattr(
        "app.services.document_service.render_docx_from_source",
        fake_render,
    )
    _patch_upload_render(monkeypatch, url="https://example.com/v2.docx")

    result = await edit_word_doc(
        tool_context=tool_context,
        document_id="doc-w1",
        operation="replace_paragraph",
        target="Intro",
        new_content="Brand new intro.",
    )

    assert result["status"] == "success"
    new_source = source_service.update_source.await_args.kwargs["new_source"]
    assert new_source["sections"][0]["content"] == "Brand new intro."


# ---------------------------------------------------------------------------
# edit_google_doc
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edit_google_doc_replace_section(
    tool_context, mock_services, monkeypatch
):
    """``edit_google_doc`` calls ``replace_section`` on the Google Docs service."""
    from app.agents.tools import document_editor
    from app.agents.tools.document_editor import edit_google_doc

    source_service, version_service, _ = mock_services
    source_service.get.return_value = {
        "user_id": tool_context.state["user_id"],
        "document_id": "doc-g1",
        "doc_class": "google_doc",
        "binary_url": None,
        "source": {"google_doc_id": "g-doc-id-123"},
    }
    version_service.append.return_value = {"id": "v3"}

    fake_google = MagicMock()
    fake_google.read_doc_content.return_value = "Old summary text."
    fake_google.replace_section.return_value = {"replies": []}

    monkeypatch.setattr(
        document_editor,
        "_get_google_docs_service",
        lambda ctx: fake_google,
    )

    result = await edit_google_doc(
        tool_context=tool_context,
        document_id="doc-g1",
        operation="replace_section",
        anchor="Summary",
        new_content="New summary text.",
    )

    assert result["status"] == "success"
    assert result["new_version_id"] == "v3"
    fake_google.replace_section.assert_called_once_with(
        "g-doc-id-123",
        "Summary",
        "New summary text.",
    )

    append_kwargs = version_service.append.await_args.kwargs
    assert append_kwargs["document_id"] == "doc-g1"
    snapshot = append_kwargs["source_snapshot"]
    assert snapshot["google_doc_id"] == "g-doc-id-123"
    assert snapshot["before_text"] == "Old summary text."
    assert snapshot["anchor"] == "Summary"


# ---------------------------------------------------------------------------
# list_document_versions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_document_versions(tool_context, mock_services):
    """Owned doc returns the version_service.list() rows verbatim."""
    from app.agents.tools.document_editor import list_document_versions

    source_service, version_service, _ = mock_services
    source_service.get.return_value = {
        "user_id": tool_context.state["user_id"],
        "document_id": "doc-l1",
        "doc_class": "report",
        "binary_url": None,
        "source": None,
    }
    version_service.list.return_value = [
        {"id": "v3", "diff_summary": "Latest"},
        {"id": "v2", "diff_summary": "Earlier"},
    ]

    result = await list_document_versions(
        tool_context=tool_context,
        document_id="doc-l1",
    )

    assert result["status"] == "success"
    assert result["versions"][0]["id"] == "v3"
    assert len(result["versions"]) == 2
    version_service.list.assert_awaited_once_with("doc-l1", limit=10)
