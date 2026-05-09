# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for `create_document` widget envelope emission.

The Google Docs API client and chat_widgets persistence layer are
fully mocked — these tests just assert the tool returns a renderable
`document` widget envelope and that the widget gets persisted once.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.agents.tools import docs as docs_tool


class _StubToolContext:
    """Minimal stand-in for an ADK ToolContext."""

    def __init__(self, state: dict | None = None) -> None:
        self.state = state or {}


def _make_doc(doc_id: str = "doc-123", title: str = "My Doc") -> SimpleNamespace:
    return SimpleNamespace(
        id=doc_id,
        title=title,
        url=f"https://docs.google.com/document/d/{doc_id}/edit",
    )


def test_create_document_returns_document_widget_envelope() -> None:
    """Top-level `type == "document"` and a populated `data` dict are
    required for the SSE post-processor to hoist the widget into chat."""
    docs_service = MagicMock()
    docs_service.create_document.return_value = _make_doc()

    ctx = _StubToolContext({"user_id": "user-1", "session_id": "sess-1"})

    with (
        patch.object(docs_tool, "_get_docs_service", return_value=docs_service),
        patch.object(docs_tool, "_track_created_doc"),
        patch("app.services.chat_widget_persistence.persist_chat_widget"),
    ):
        result = docs_tool.create_document(ctx, title="My Doc", content="Hello")

    assert result["type"] == "document"
    assert result["title"] == "My Doc"
    assert isinstance(result["data"], dict)
    assert result["data"]["url"] == "https://docs.google.com/document/d/doc-123/edit"
    assert result["data"]["doc_id"] == "doc-123"
    assert result["data"]["kind"] == "google_doc"
    assert "widget_id" in result and result["widget_id"]

    # Legacy field preserved for backward compat callers.
    assert result["document"]["id"] == "doc-123"
    assert result["document"]["url"].endswith("/edit")
    assert result["status"] == "success"


def test_create_document_persists_widget_once() -> None:
    """`persist_chat_widget` must be called once with the widget envelope."""
    docs_service = MagicMock()
    docs_service.create_document.return_value = _make_doc(doc_id="doc-xyz", title="Spec")

    ctx = _StubToolContext({"user_id": "user-1", "session_id": "sess-1"})

    with (
        patch.object(docs_tool, "_get_docs_service", return_value=docs_service),
        patch.object(docs_tool, "_track_created_doc"),
        patch(
            "app.services.chat_widget_persistence.persist_chat_widget"
        ) as mock_persist,
    ):
        docs_tool.create_document(ctx, title="Spec")

    assert mock_persist.call_count == 1
    kwargs = mock_persist.call_args.kwargs
    assert kwargs["user_id"] == "user-1"
    assert kwargs["session_id"] == "sess-1"
    widget = kwargs["widget"]
    assert widget["type"] == "document"
    assert widget["data"]["doc_id"] == "doc-xyz"
    assert widget["data"]["kind"] == "google_doc"


def test_create_document_persistence_failure_does_not_break_tool() -> None:
    """If `persist_chat_widget` raises, the tool must still return success."""
    docs_service = MagicMock()
    docs_service.create_document.return_value = _make_doc()

    ctx = _StubToolContext({"user_id": "user-1", "session_id": "sess-1"})

    with (
        patch.object(docs_tool, "_get_docs_service", return_value=docs_service),
        patch.object(docs_tool, "_track_created_doc"),
        patch(
            "app.services.chat_widget_persistence.persist_chat_widget",
            side_effect=RuntimeError("supabase down"),
        ),
    ):
        result = docs_tool.create_document(ctx, title="My Doc")

    assert result["status"] == "success"
    assert result["type"] == "document"


def test_create_report_doc_returns_document_widget_envelope() -> None:
    """`create_report_doc` should also emit a `document` widget."""
    docs_service = MagicMock()
    docs_service.create_report_document.return_value = _make_doc(
        doc_id="rep-1", title="Q4 Report"
    )

    ctx = _StubToolContext({"user_id": "user-1", "session_id": "sess-1"})
    sections = [{"heading": "Summary", "content": "..."}]

    with (
        patch.object(docs_tool, "_get_docs_service", return_value=docs_service),
        patch.object(docs_tool, "_track_created_doc"),
        patch(
            "app.services.chat_widget_persistence.persist_chat_widget"
        ) as mock_persist,
    ):
        result = docs_tool.create_report_doc(
            ctx, title="Q4 Report", sections=sections
        )

    assert result["type"] == "document"
    assert result["data"]["kind"] == "google_doc"
    assert result["data"]["doc_id"] == "rep-1"
    assert mock_persist.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
