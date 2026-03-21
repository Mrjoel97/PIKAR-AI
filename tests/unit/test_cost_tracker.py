"""Tests for the research cost tracker tool."""

from unittest.mock import MagicMock, patch

from app.agents.research.tools.cost_tracker import (
    estimate_cost_usd,
    log_research_cost,
)


def _mock_client_with_log_id(log_id: str = "log-uuid-1") -> MagicMock:
    """Return a mock Supabase client that supports insert on kg_research_log."""
    client = MagicMock()
    insert_result = MagicMock()
    insert_result.data = [{"id": log_id}]
    client.table.return_value.insert.return_value.execute.return_value = insert_result
    return client


@patch("app.agents.research.tools.cost_tracker._get_supabase")
def test_log_research_cost_writes_to_table(mock_get_sb):
    """Verify insert is called on kg_research_log with correct data."""
    log_id = "log-uuid-abc"
    client = _mock_client_with_log_id(log_id)
    mock_get_sb.return_value = client

    result = log_research_cost(
        domain="financial",
        query="AI market trends",
        depth="standard",
        tracks_run=3,
        searches_used=3,
        scrapes_used=6,
        findings_count=12,
        graph_updates=4,
        triggered_by="agent_request",
        duration_ms=5200,
        requesting_agent="FinancialAgent",
        user_id="user-1",
    )

    assert result["success"] is True
    assert result["log_id"] == log_id
    assert result["cost_usd"] > 0

    # Verify insert was called on the correct table
    client.table.assert_called_with("kg_research_log")
    client.table.return_value.insert.assert_called_once()

    # Verify the inserted row contains expected fields
    inserted_row = client.table.return_value.insert.call_args[0][0]
    assert inserted_row["domain"] == "financial"
    assert inserted_row["query"] == "AI market trends"
    assert inserted_row["depth"] == "standard"
    assert inserted_row["tracks_run"] == 3
    assert inserted_row["requesting_agent"] == "FinancialAgent"
    assert inserted_row["user_id"] == "user-1"


def test_estimate_cost_calculates_correctly():
    """Verify cost estimate is positive and matches expected formula."""
    cost = estimate_cost_usd(searches=5, scrapes=3)

    expected = 5 * 0.01 + 3 * 0.015  # 0.05 + 0.045 = 0.095
    assert cost > 0
    assert cost == round(expected, 4)


@patch("app.agents.research.tools.cost_tracker._get_supabase")
def test_log_research_cost_handles_db_error(mock_get_sb):
    """DB exception returns success=False without raising."""
    mock_get_sb.side_effect = RuntimeError("Connection refused")

    result = log_research_cost(
        domain="marketing",
        query="Brand awareness campaigns",
        depth="quick",
        tracks_run=1,
        searches_used=1,
        scrapes_used=2,
        findings_count=3,
        graph_updates=1,
        triggered_by="user_initiated",
        duration_ms=1500,
    )

    assert result["success"] is False
    assert "Connection refused" in result["error"]
