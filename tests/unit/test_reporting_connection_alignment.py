from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agents.tools.google_sheets import _persist_spreadsheet_connection, connect_spreadsheet
from app.agents.tools.report_scheduling import _resolve_connection_id, schedule_report


def test_persist_spreadsheet_connection_sets_state(monkeypatch):
    captured: dict[str, object] = {}

    def fake_upsert(self, **kwargs):
        captured.update(kwargs)
        return {"id": "conn-123", **kwargs}

    monkeypatch.setattr(
        "app.services.spreadsheet_connection_service.SpreadsheetConnectionService.upsert_connection",
        fake_upsert,
    )

    tool_context = SimpleNamespace(state={"user_id": "user-123"})
    result = _persist_spreadsheet_connection(
        tool_context,
        spreadsheet_id="sheet-123",
        spreadsheet_name="Revenue Tracker",
        spreadsheet_url="https://docs.google.com/spreadsheets/d/sheet-123",
        metadata={"source": "test"},
    )

    assert result["id"] == "conn-123"
    assert tool_context.state["connection_id"] == "conn-123"
    assert captured == {
        "user_id": "user-123",
        "spreadsheet_id": "sheet-123",
        "spreadsheet_name": "Revenue Tracker",
        "spreadsheet_url": "https://docs.google.com/spreadsheets/d/sheet-123",
        "metadata": {"source": "test"},
    }


def test_connect_spreadsheet_returns_connection_id(monkeypatch):
    spreadsheet = SimpleNamespace(
        id="sheet-456",
        name="Board Metrics",
        url="https://docs.google.com/spreadsheets/d/sheet-456",
        sheets=["Data", "Summary"],
    )

    class FakeSheetsService:
        def get_spreadsheet(self, spreadsheet_id: str):
            assert spreadsheet_id == "sheet-456"
            return spreadsheet

    monkeypatch.setattr("app.agents.tools.google_sheets._get_sheets_service", lambda _ctx: FakeSheetsService())
    monkeypatch.setattr(
        "app.agents.tools.google_sheets._persist_spreadsheet_connection",
        lambda *_args, **_kwargs: {"id": "conn-456"},
    )

    tool_context = SimpleNamespace(state={"user_id": "user-456"})
    result = connect_spreadsheet(tool_context, "sheet-456")

    assert result["status"] == "success"
    assert result["connection_id"] == "conn-456"
    assert tool_context.state["connected_spreadsheet_id"] == "sheet-456"
    assert tool_context.state["connected_spreadsheet_name"] == "Board Metrics"


def test_resolve_connection_id_recovers_from_database(monkeypatch):
    def fake_get_connection(self, **kwargs):
        assert kwargs == {"user_id": "user-789", "spreadsheet_id": "sheet-789"}
        return {"id": "conn-789", **kwargs}

    monkeypatch.setattr(
        "app.services.spreadsheet_connection_service.SpreadsheetConnectionService.get_connection",
        fake_get_connection,
    )

    tool_context = SimpleNamespace(state={"user_id": "user-789"})
    connection_id = _resolve_connection_id(tool_context, "sheet-789")

    assert connection_id == "conn-789"
    assert tool_context.state["connection_id"] == "conn-789"


@pytest.mark.asyncio
async def test_schedule_report_uses_resolved_connection_id(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_create_schedule(**kwargs):
        captured.update(kwargs)
        return {"status": "success", "schedule": {"id": "schedule-1"}}

    monkeypatch.setattr(
        "app.agents.tools.report_scheduling._resolve_connection_id",
        lambda *_args, **_kwargs: "conn-321",
    )
    monkeypatch.setattr(
        "app.services.report_scheduler.report_scheduler.create_schedule",
        fake_create_schedule,
    )

    tool_context = SimpleNamespace(
        state={
            "user_id": "user-321",
            "connected_spreadsheet_id": "sheet-321",
        }
    )
    result = await schedule_report(
        tool_context,
        frequency="weekly",
        report_format="pptx",
        recipients=["team@example.com"],
    )

    assert result["status"] == "success"
    assert captured["user_id"] == "user-321"
    assert captured["connection_id"] == "conn-321"
    assert str(captured["frequency"]).endswith("WEEKLY")
