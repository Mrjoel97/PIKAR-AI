# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for `_synthesize_markdown_report_widget`.

Exercises the qualification thresholds (LONGFORM_MIN_CHARS = 200,
STRUCTURED_MIN_CHARS = 140), the widget envelope shape, and the
best-effort persistence contract — including that a raising
`persist_chat_widget` does not break the synthesizer.
"""

from __future__ import annotations

from unittest.mock import patch

from app.sse_utils import (
    LONGFORM_MIN_CHARS,
    STRUCTURED_MIN_CHARS,
    _synthesize_markdown_report_widget,
)


def test_plain_prose_over_longform_threshold_returns_widget() -> None:
    """A 250-char plain-prose response must be promoted to a widget."""
    text = (
        "Pikar AI shipped its v12.0 release this week. "
        "The release covers tangible outputs across thirteen agents, "
        "long-running tasks of up to thirty minutes, generative research "
        "with citation grading, and cross-agent memory."
    )
    assert len(text) >= LONGFORM_MIN_CHARS

    with patch(
        "app.services.chat_widget_persistence.persist_chat_widget"
    ) as mock_persist:
        widget = _synthesize_markdown_report_widget(
            text,
            session_id="sess-1",
            user_id="user-1",
            agent_name="EXEC",
        )

    assert widget is not None
    assert widget["type"] == "markdown_report"
    assert isinstance(widget.get("data"), dict)
    assert widget["data"]["markdown"] == text
    assert widget["data"]["session_id"] == "sess-1"
    assert isinstance(widget.get("widget_id"), str) and widget["widget_id"]
    assert widget["workspace"]["sessionId"] == "sess-1"
    assert isinstance(widget["workspace"]["workspaceItemId"], str)
    mock_persist.assert_called_once()


def test_short_text_under_longform_threshold_returns_none() -> None:
    """A short plain-prose snippet under 200 chars must NOT be promoted."""
    text = "Quick note: the deployment finished without errors."
    assert len(text) < LONGFORM_MIN_CHARS

    with patch(
        "app.services.chat_widget_persistence.persist_chat_widget"
    ) as mock_persist:
        widget = _synthesize_markdown_report_widget(
            text,
            session_id="sess-1",
            user_id="user-1",
        )

    assert widget is None
    mock_persist.assert_not_called()


def test_structured_markdown_at_150_chars_returns_widget() -> None:
    """Structured markdown (heading + bullets) at ~150 chars must qualify
    via the STRUCTURED_MIN_CHARS path even though it's under LONGFORM."""
    text = (
        "# Q3 Pricing Review\n"
        "- Tier A holds at $49 with 88% retention this quarter\n"
        "- Tier B drops to $99 to clear churn cohort\n"
        "- Tier C unchanged at $199 for enterprise"
    )
    assert STRUCTURED_MIN_CHARS <= len(text) < LONGFORM_MIN_CHARS

    with patch(
        "app.services.chat_widget_persistence.persist_chat_widget"
    ) as mock_persist:
        widget = _synthesize_markdown_report_widget(
            text,
            session_id="sess-2",
            user_id="user-2",
            agent_name="financial",
        )

    assert widget is not None
    assert widget["type"] == "markdown_report"
    # Title should be derived from the leading `# Q3 Pricing Review` heading.
    assert widget["title"] == "Q3 Pricing Review"
    mock_persist.assert_called_once()


def test_persistence_failure_does_not_break_synthesizer() -> None:
    """If `persist_chat_widget` raises, the helper still returns the widget
    envelope — persistence is best-effort and must never break the stream."""
    text = (
        "Pikar AI shipped its v12.0 release this week. "
        "The release covers tangible outputs across thirteen agents, "
        "long-running tasks of up to thirty minutes, generative research "
        "with citation grading, and cross-agent memory."
    )
    assert len(text) >= LONGFORM_MIN_CHARS

    with patch(
        "app.services.chat_widget_persistence.persist_chat_widget",
        side_effect=RuntimeError("supabase down"),
    ):
        widget = _synthesize_markdown_report_widget(
            text,
            session_id="sess-3",
            user_id="user-3",
        )

    assert widget is not None
    assert widget["type"] == "markdown_report"
    assert widget["data"]["markdown"] == text
