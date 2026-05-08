# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for SSE-side markdown_report widget synthesis.

The backend `_synthesize_markdown_report_widget` helper is the primary
writer for longform `markdown_report` widgets — these tests pin down the
qualifying thresholds (mirrors the frontend `buildMarkdownWorkspaceWidget`
heuristics in `frontend/src/services/workspaceArtifacts.ts`) and verify
that persistence is best-effort (one call, swallowed exceptions).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.sse_utils import _synthesize_markdown_report_widget


def _plain_prose(length: int) -> str:
    """Return *length* characters of plain prose (no markdown signals)."""
    base = (
        "The quarterly review highlights steady revenue growth, reinforced "
        "retention metrics, and a healthier net dollar retention curve. "
        "Operations remain on track and customer support response times "
        "continue to trend favorably across all priority tiers. "
    )
    out = (base * ((length // len(base)) + 2))[:length]
    assert "#" not in out and "- " not in out and "```" not in out
    return out


class TestSynthesisThresholds:
    """Threshold checks: plain longform, structured shorter, sub-threshold."""

    def test_plain_prose_250_chars_returns_markdown_report_widget(self):
        text = _plain_prose(250)
        with patch(
            "app.services.chat_widget_persistence.persist_chat_widget"
        ):
            widget = _synthesize_markdown_report_widget(
                text,
                session_id="sess-1",
                user_id="user-1",
                agent_name="ExecutiveAgent",
            )

        assert widget is not None
        assert widget["type"] == "markdown_report"
        assert widget["data"]["markdown"] == text.strip()
        assert widget["title"]
        assert widget["widget_id"]
        assert widget["workspace"]["sessionId"] == "sess-1"
        assert widget["workspace"]["workspaceItemId"]

    def test_short_plain_prose_returns_none(self):
        # 150 plain-prose chars: below LONGFORM_MIN_CHARS (200), no structured
        # signals, fewer than 12 lines — must NOT promote.
        text = _plain_prose(150)
        with patch(
            "app.services.chat_widget_persistence.persist_chat_widget"
        ) as mock_persist:
            widget = _synthesize_markdown_report_widget(
                text,
                session_id="sess-1",
                user_id="user-1",
                agent_name="ExecutiveAgent",
            )

        assert widget is None
        mock_persist.assert_not_called()

    def test_structured_markdown_150_chars_returns_widget(self):
        # ~150 chars but with heading + bullet list signals — STRUCTURED_MIN_CHARS
        # is 140, so this should promote even when shorter than LONGFORM_MIN_CHARS.
        text = (
            "# Q1 Roadmap\n\n"
            "- Launch new pricing page in March\n"
            "- Refresh onboarding flow with checklist\n"
            "- Run partner webinar series\n"
            "Wraps end of quarter."
        )
        assert 140 <= len(text) < 200
        with patch(
            "app.services.chat_widget_persistence.persist_chat_widget"
        ):
            widget = _synthesize_markdown_report_widget(
                text,
                session_id="sess-2",
                user_id="user-1",
                agent_name="MarketingAgent",
            )

        assert widget is not None
        assert widget["type"] == "markdown_report"
        # Title should derive from the first heading text.
        assert widget["title"].startswith("Q1 Roadmap") or "Roadmap" in widget["title"]


class TestSynthesisPersistence:
    """Persistence is best-effort: one call, swallowed exceptions."""

    def test_persist_called_once_when_widget_synthesized(self):
        text = _plain_prose(300)
        with patch(
            "app.services.chat_widget_persistence.persist_chat_widget"
        ) as mock_persist:
            widget = _synthesize_markdown_report_widget(
                text,
                session_id="sess-3",
                user_id="user-7",
                agent_name="DataAgent",
            )

        assert widget is not None
        assert mock_persist.call_count == 1
        kwargs = mock_persist.call_args.kwargs
        assert kwargs["user_id"] == "user-7"
        assert kwargs["session_id"] == "sess-3"
        assert kwargs["widget"]["type"] == "markdown_report"

    def test_persistence_failure_does_not_break_synthesizer(self):
        text = _plain_prose(300)
        with patch(
            "app.services.chat_widget_persistence.persist_chat_widget",
            side_effect=RuntimeError("supabase down"),
        ):
            widget = _synthesize_markdown_report_widget(
                text,
                session_id="sess-4",
                user_id="user-1",
                agent_name="ExecutiveAgent",
            )

        # Synthesizer must still return the widget — the SSE generator
        # depends on it to emit the event regardless of persistence health.
        assert widget is not None
        assert widget["type"] == "markdown_report"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
