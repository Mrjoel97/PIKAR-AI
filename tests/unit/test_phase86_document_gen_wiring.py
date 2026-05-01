# tests/unit/test_phase86_document_gen_wiring.py
"""Phase 86 wiring tests -- DOCUMENT_GEN_TOOLS exposed on Executive + Content Director."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.agent import _EXECUTIVE_TOOLS
from app.agents.content.agent import CONTENT_DIRECTOR_INSTRUCTION
from app.agents.tools.document_gen import (
    DOCUMENT_GEN_TOOLS,
    generate_pdf_report,
    generate_pitch_deck,
)
from app.services.document_service import VALID_TEMPLATES

EXECUTIVE_PROMPT_PATH = Path("app/prompts/executive_instruction.txt")


def _tool_names(tools) -> set[str]:
    return {getattr(t, "__name__", getattr(t, "name", "")) for t in tools}


def test_executive_tools_includes_document_gen() -> None:  # SC1
    names = _tool_names(_EXECUTIVE_TOOLS)
    assert "generate_pdf_report" in names
    assert "generate_pitch_deck" in names


def test_executive_instruction_names_doc_tools() -> None:  # SC2 (names)
    text = EXECUTIVE_PROMPT_PATH.read_text(encoding="utf-8")
    assert "generate_pdf_report" in text
    assert "generate_pitch_deck" in text


def test_executive_instruction_lists_pdf_templates() -> None:  # SC2 (templates)
    text = EXECUTIVE_PROMPT_PATH.read_text(encoding="utf-8")
    for tpl in VALID_TEMPLATES:
        assert tpl in text, f"Template '{tpl}' not named in executive_instruction.txt"


def test_content_director_instruction_mentions_doc_gen() -> None:  # SC3
    text = CONTENT_DIRECTOR_INSTRUCTION
    assert "generate_pdf_report" in text
    assert "generate_pitch_deck" in text
    # Capability mention (SC3 literal: "PDF and PowerPoint generation capability")
    assert "PDF" in text
    assert "PowerPoint" in text or "pptx" in text.lower()


def test_document_gen_tools_export_is_two_callables() -> None:
    assert len(DOCUMENT_GEN_TOOLS) == 2
    assert all(callable(t) for t in DOCUMENT_GEN_TOOLS)
    assert generate_pdf_report in DOCUMENT_GEN_TOOLS
    assert generate_pitch_deck in DOCUMENT_GEN_TOOLS


# SC4/SC5 mechanical proxy -- uses existing DocumentService test pattern
@pytest.mark.asyncio
async def test_generate_pdf_report_returns_widget(monkeypatch) -> None:  # SC4 proxy
    """When the agent invokes generate_pdf_report, a widget is returned."""
    from unittest.mock import AsyncMock, MagicMock, patch

    fake_widget = {"type": "document", "data": {"fileType": "pdf", "sizeBytes": 4096}}
    mock_service = MagicMock()
    mock_service.generate_pdf = AsyncMock(return_value=fake_widget)

    monkeypatch.setattr(
        "app.services.request_context.get_current_user_id",
        lambda: "user-1",
    )
    monkeypatch.setattr(
        "app.services.request_context.get_current_session_id",
        lambda: "sess-1",
    )

    with patch("app.services.document_service.DocumentService", return_value=mock_service):
        result = await generate_pdf_report(
            template="financial_report",
            data={"revenue": 100.0, "expenses": 50.0, "period": "Q1"},
            title="Q1 Financials",
        )

    assert result["status"] == "success"
    assert result["widget"]["data"]["fileType"] == "pdf"


@pytest.mark.asyncio
async def test_generate_pitch_deck_returns_widget(monkeypatch) -> None:  # SC5 proxy
    """When the agent invokes generate_pitch_deck, a widget is returned."""
    from unittest.mock import AsyncMock, MagicMock, patch

    fake_widget = {"type": "document", "data": {"fileType": "pptx", "sizeBytes": 8192}}
    mock_service = MagicMock()
    mock_service.generate_pptx = AsyncMock(return_value=fake_widget)
    mock_service.render_chart = MagicMock(return_value=b"\x89PNG_fake")

    monkeypatch.setattr(
        "app.services.request_context.get_current_user_id",
        lambda: "user-1",
    )
    monkeypatch.setattr(
        "app.services.request_context.get_current_session_id",
        lambda: "sess-1",
    )

    with patch("app.services.document_service.DocumentService", return_value=mock_service):
        result = await generate_pitch_deck(
            content=[
                {"title": "Cover", "content": ["Pikar AI"]},
                {"title": "Problem", "content": ["X is hard"]},
            ],
            title="Investor Deck",
        )

    assert result["status"] == "success"
    assert result["widget"]["data"]["fileType"] == "pptx"
