"""Unit tests for briefing tools.

Tests get_daily_briefing with mocked Supabase to verify section grouping.
"""

from unittest.mock import MagicMock, patch


def _make_tool_context(state: dict | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.state = state or {}
    return ctx


def _make_triage_items() -> list[dict]:
    """Return a representative set of triage items for today."""
    return [
        {
            "id": "1",
            "subject": "URGENT: Server down",
            "sender": "ops@example.com",
            "priority": "urgent",
            "section": "urgent",
            "action_type": "needs_review",
            "status": "pending",
            "created_at": "2026-03-19T08:00:00Z",
        },
        {
            "id": "2",
            "subject": "Re: Proposal",
            "sender": "client@example.com",
            "priority": "normal",
            "section": "needs_reply",
            "action_type": "needs_reply",
            "status": "pending",
            "created_at": "2026-03-19T09:00:00Z",
        },
        {
            "id": "3",
            "subject": "Newsletter",
            "sender": "news@example.com",
            "priority": "low",
            "section": "fyi",
            "action_type": "fyi",
            "status": "pending",
            "created_at": "2026-03-19T09:30:00Z",
        },
        {
            "id": "4",
            "subject": "Auto-reply sent",
            "sender": "bot@example.com",
            "priority": "normal",
            "section": "auto_handled",
            "action_type": "auto_handle",
            "status": "auto_handled",
            "created_at": "2026-03-19T10:00:00Z",
        },
        {
            "id": "5",
            "subject": "Meeting invite",
            "sender": "calendar@example.com",
            "priority": "normal",
            "section": "fyi",
            "action_type": "fyi",
            "status": "pending",
            "created_at": "2026-03-19T10:30:00Z",
        },
    ]


def test_get_daily_briefing_sections_grouped_correctly():
    """get_daily_briefing groups items into the correct sections."""
    mock_response = MagicMock()
    mock_response.data = _make_triage_items()

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.execute.return_value = mock_response

    mock_db = MagicMock()
    mock_db.table.return_value = mock_table

    with patch(
        "app.agents.tools.briefing_tools._get_supabase", return_value=mock_db
    ):
        from app.agents.tools.briefing_tools import get_daily_briefing

        result = get_daily_briefing(_make_tool_context())

    assert result["status"] == "ok"
    counts = result["counts"]

    # 1 urgent item (priority=urgent)
    assert counts["urgent"] == 1, f"Expected 1 urgent, got {counts['urgent']}"

    # 1 needs_reply item
    assert counts["needs_reply"] == 1, f"Expected 1 needs_reply, got {counts['needs_reply']}"

    # 1 auto_handled item (action_type=auto_handle)
    assert counts["auto_handled"] == 1, f"Expected 1 auto_handled, got {counts['auto_handled']}"

    # 2 fyi items
    assert counts["fyi"] == 2, f"Expected 2 fyi, got {counts['fyi']}"

    # Total should equal number of items
    assert result["total"] == 5


def test_get_daily_briefing_returns_ok_with_empty_table():
    """get_daily_briefing returns status ok and zero counts when no items exist."""
    mock_response = MagicMock()
    mock_response.data = []

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.execute.return_value = mock_response

    mock_db = MagicMock()
    mock_db.table.return_value = mock_table

    with patch(
        "app.agents.tools.briefing_tools._get_supabase", return_value=mock_db
    ):
        from app.agents.tools.briefing_tools import get_daily_briefing

        result = get_daily_briefing(_make_tool_context())

    assert result["status"] == "ok"
    assert result["total"] == 0
    assert all(count == 0 for count in result["counts"].values())


def test_get_daily_briefing_error_handling():
    """get_daily_briefing returns error status when database raises."""
    mock_db = MagicMock()
    mock_db.table.side_effect = RuntimeError("DB unavailable")

    with patch(
        "app.agents.tools.briefing_tools._get_supabase", return_value=mock_db
    ):
        from app.agents.tools.briefing_tools import get_daily_briefing

        result = get_daily_briefing(_make_tool_context())

    assert result["status"] == "error"
    assert "DB unavailable" in result["message"]


def test_get_daily_briefing_fallback_section_for_unknown_action_type():
    """Items with unknown section/action_type fall into fyi."""
    mock_response = MagicMock()
    mock_response.data = [
        {
            "id": "99",
            "subject": "Something odd",
            "sender": "odd@example.com",
            "priority": "normal",
            "section": None,
            "action_type": "spam",  # not explicitly handled
            "status": "pending",
            "created_at": "2026-03-19T11:00:00Z",
        }
    ]

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.execute.return_value = mock_response

    mock_db = MagicMock()
    mock_db.table.return_value = mock_table

    with patch(
        "app.agents.tools.briefing_tools._get_supabase", return_value=mock_db
    ):
        from app.agents.tools.briefing_tools import get_daily_briefing

        result = get_daily_briefing(_make_tool_context())

    assert result["counts"]["fyi"] == 1


def test_briefing_tools_export():
    """BRIEFING_TOOLS list contains all five expected tool functions."""
    from app.agents.tools.briefing_tools import BRIEFING_TOOLS

    names = [fn.__name__ for fn in BRIEFING_TOOLS]
    assert "get_daily_briefing" in names
    assert "refresh_briefing" in names
    assert "approve_draft" in names
    assert "dismiss_item" in names
    assert "undo_auto_action" in names
    assert len(BRIEFING_TOOLS) == 5
