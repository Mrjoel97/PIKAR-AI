"""Tests for the research query planner."""

from __future__ import annotations


def test_plan_queries_returns_correct_structure():
    """Query planner returns list of track dicts with query and track_type."""
    from app.agents.research.tools.query_planner import plan_queries

    result = plan_queries(
        query="What are the current interest rate trends in South Africa?",
        domain="financial",
        depth="deep",
    )

    assert result["success"] is True
    tracks = result["tracks"]
    assert isinstance(tracks, list)
    assert len(tracks) >= 3  # deep = 5, standard = 3, quick = 1
    for track in tracks:
        assert "query" in track
        assert "track_type" in track
        assert track["track_type"] in (
            "primary",
            "context",
            "contrarian",
            "impact",
            "risk",
            "historical",
        )


def test_plan_queries_deep_returns_5_tracks():
    """Deep research generates 5 tracks."""
    from app.agents.research.tools.query_planner import plan_queries

    result = plan_queries(
        query="South Africa interest rates",
        domain="financial",
        depth="deep",
    )
    assert len(result["tracks"]) == 5


def test_plan_queries_standard_returns_3_tracks():
    """Standard research generates 3 tracks."""
    from app.agents.research.tools.query_planner import plan_queries

    result = plan_queries(
        query="South Africa interest rates",
        domain="financial",
        depth="standard",
    )
    assert len(result["tracks"]) == 3


def test_plan_queries_quick_returns_1_track():
    """Quick research generates 1 track (primary only)."""
    from app.agents.research.tools.query_planner import plan_queries

    result = plan_queries(
        query="South Africa interest rates",
        domain="financial",
        depth="quick",
    )
    assert len(result["tracks"]) == 1
    assert result["tracks"][0]["track_type"] == "primary"


def test_plan_queries_adds_domain_context():
    """Queries include domain-specific keywords."""
    from app.agents.research.tools.query_planner import plan_queries

    result = plan_queries(
        query="interest rates",
        domain="compliance",
        depth="standard",
    )
    # At least one track should reference compliance/regulatory context
    all_queries = " ".join(t["query"].lower() for t in result["tracks"])
    assert any(
        kw in all_queries
        for kw in ("regulation", "compliance", "legal", "policy", "ruling")
    )


def test_plan_queries_handles_empty_query():
    """Empty query returns error."""
    from app.agents.research.tools.query_planner import plan_queries

    result = plan_queries(query="", domain="financial", depth="deep")
    assert result["success"] is False
