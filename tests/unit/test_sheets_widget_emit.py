# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for `create_custom_spreadsheet` widget envelope emission.

The Google Sheets API client, knowledge-vault tracking, and chat_widgets
persistence layer are all mocked — these tests just assert the tool
returns a `document` widget envelope (kind=google_sheet) and that the
widget gets persisted once.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.agents.tools import google_sheets as sheets_tool


class _StubToolContext:
    """Minimal stand-in for an ADK ToolContext."""

    def __init__(self, state: dict | None = None) -> None:
        self.state = state or {}


def _make_sheet(
    sheet_id: str = "sheet-123",
    name: str = "Tracker",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=sheet_id,
        name=name,
        url=f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit",
        sheets=[{"title": "Data", "id": 0}],
    )


def test_create_custom_spreadsheet_returns_document_widget_envelope() -> None:
    """Top-level `type == "document"` with `kind == "google_sheet"`."""
    sheets_service = MagicMock()
    sheets_service.create_spreadsheet.return_value = _make_sheet()

    ctx = _StubToolContext({"user_id": "user-1", "session_id": "sess-1"})

    with (
        patch.object(sheets_tool, "_get_sheets_service", return_value=sheets_service),
        patch.object(sheets_tool, "_track_created_spreadsheet"),
        patch.object(
            sheets_tool, "_persist_spreadsheet_connection", return_value=None
        ),
        patch("app.services.chat_widget_persistence.persist_chat_widget"),
    ):
        result = sheets_tool.create_custom_spreadsheet(
            ctx,
            title="Tracker",
            purpose="track sales",
            columns=["Date", "Product", "Revenue"],
        )

    assert result["type"] == "document"
    assert result["title"] == "Tracker"
    assert isinstance(result["data"], dict)
    assert (
        result["data"]["url"]
        == "https://docs.google.com/spreadsheets/d/sheet-123/edit"
    )
    assert result["data"]["doc_id"] == "sheet-123"
    assert result["data"]["kind"] == "google_sheet"
    assert "widget_id" in result and result["widget_id"]

    # Legacy field preserved for backward compat callers.
    assert result["spreadsheet"]["id"] == "sheet-123"
    assert result["spreadsheet"]["columns"] == ["Date", "Product", "Revenue"]
    assert result["status"] == "success"


def test_create_custom_spreadsheet_persists_widget_once() -> None:
    """`persist_chat_widget` must be called exactly once."""
    sheets_service = MagicMock()
    sheets_service.create_spreadsheet.return_value = _make_sheet(
        sheet_id="sheet-xyz", name="KPI Board"
    )

    ctx = _StubToolContext({"user_id": "user-1", "session_id": "sess-1"})

    with (
        patch.object(sheets_tool, "_get_sheets_service", return_value=sheets_service),
        patch.object(sheets_tool, "_track_created_spreadsheet"),
        patch.object(
            sheets_tool, "_persist_spreadsheet_connection", return_value=None
        ),
        patch(
            "app.services.chat_widget_persistence.persist_chat_widget"
        ) as mock_persist,
    ):
        sheets_tool.create_custom_spreadsheet(
            ctx,
            title="KPI Board",
            purpose="weekly KPIs",
            columns=["Week", "MRR"],
        )

    assert mock_persist.call_count == 1
    kwargs = mock_persist.call_args.kwargs
    assert kwargs["user_id"] == "user-1"
    assert kwargs["session_id"] == "sess-1"
    widget = kwargs["widget"]
    assert widget["type"] == "document"
    assert widget["data"]["doc_id"] == "sheet-xyz"
    assert widget["data"]["kind"] == "google_sheet"


def test_create_custom_spreadsheet_persistence_failure_does_not_break_tool() -> None:
    """If `persist_chat_widget` raises, the tool must still return success."""
    sheets_service = MagicMock()
    sheets_service.create_spreadsheet.return_value = _make_sheet()

    ctx = _StubToolContext({"user_id": "user-1", "session_id": "sess-1"})

    with (
        patch.object(sheets_tool, "_get_sheets_service", return_value=sheets_service),
        patch.object(sheets_tool, "_track_created_spreadsheet"),
        patch.object(
            sheets_tool, "_persist_spreadsheet_connection", return_value=None
        ),
        patch(
            "app.services.chat_widget_persistence.persist_chat_widget",
            side_effect=RuntimeError("supabase down"),
        ),
    ):
        result = sheets_tool.create_custom_spreadsheet(
            ctx,
            title="Tracker",
            purpose="track sales",
            columns=["Date", "Revenue"],
        )

    assert result["status"] == "success"
    assert result["type"] == "document"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
