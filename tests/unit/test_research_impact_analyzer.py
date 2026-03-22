"""Tests for the research impact analyzer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_analyze_research_impact_returns_structure():
    """Analyzer returns per-domain impact comparison."""
    from app.services.research_impact_analyzer import analyze_research_impact

    mock_client = MagicMock()

    # Mock interaction_logs with research tracking
    mock_client.table.return_value.select.return_value.gte.return_value.execute.return_value.data = [
        {
            "agent_id": "FIN",
            "research_used": True,
            "research_depth": "standard",
            "user_feedback": "positive",
            "task_completed": True,
            "was_escalated": False,
            "had_followup": False,
        },
        {
            "agent_id": "FIN",
            "research_used": True,
            "research_depth": "deep",
            "user_feedback": "positive",
            "task_completed": True,
            "was_escalated": False,
            "had_followup": False,
        },
        {
            "agent_id": "FIN",
            "research_used": False,
            "research_depth": "none",
            "user_feedback": "negative",
            "task_completed": False,
            "was_escalated": True,
            "had_followup": True,
        },
        {
            "agent_id": "FIN",
            "research_used": False,
            "research_depth": "none",
            "user_feedback": "neutral",
            "task_completed": True,
            "was_escalated": False,
            "had_followup": False,
        },
        {
            "agent_id": "HR",
            "research_used": True,
            "research_depth": "quick",
            "user_feedback": "neutral",
            "task_completed": True,
            "was_escalated": False,
            "had_followup": False,
        },
        {
            "agent_id": "HR",
            "research_used": False,
            "research_depth": "none",
            "user_feedback": "neutral",
            "task_completed": True,
            "was_escalated": False,
            "had_followup": False,
        },
    ]

    with patch(
        "app.services.research_impact_analyzer._get_supabase", return_value=mock_client
    ):
        result = analyze_research_impact(days=30)

    assert result["success"] is True
    assert "domains" in result
    assert "FIN" in result["domains"]
    assert "with_research" in result["domains"]["FIN"]
    assert "without_research" in result["domains"]["FIN"]


def test_generate_skill_recommendations_high_delta():
    """High delta (research helps a lot) generates pre_research skill."""
    from app.services.research_impact_analyzer import generate_skill_recommendations

    domain_impacts = {
        "FIN": {
            "with_research": {"score": 0.87, "count": 20},
            "without_research": {"score": 0.52, "count": 30},
            "delta": 0.35,
        },
    }

    recommendations = generate_skill_recommendations(domain_impacts)

    assert len(recommendations) >= 1
    assert any(r["type"] == "pre_research" for r in recommendations)
    assert any(
        "FIN" in r.get("agent_id", "") or "financial" in r.get("domain", "")
        for r in recommendations
    )


def test_generate_skill_recommendations_low_delta():
    """Low delta (research doesn't help) generates skip_research skill."""
    from app.services.research_impact_analyzer import generate_skill_recommendations

    domain_impacts = {
        "HR": {
            "with_research": {"score": 0.60, "count": 10},
            "without_research": {"score": 0.58, "count": 15},
            "delta": 0.02,
        },
    }

    recommendations = generate_skill_recommendations(domain_impacts)

    assert len(recommendations) >= 1
    assert any(r["type"] == "skip_research" for r in recommendations)


def test_generate_skill_recommendations_insufficient_data():
    """Not enough data (< min_count) generates no recommendations."""
    from app.services.research_impact_analyzer import generate_skill_recommendations

    domain_impacts = {
        "FIN": {
            "with_research": {"score": 0.90, "count": 2},  # too few
            "without_research": {"score": 0.50, "count": 3},
            "delta": 0.40,
        },
    }

    recommendations = generate_skill_recommendations(domain_impacts, min_count=5)

    assert len(recommendations) == 0


def test_compute_effectiveness_score():
    """Effectiveness score matches self-improvement formula."""
    from app.services.research_impact_analyzer import compute_effectiveness_score

    interactions = [
        {
            "user_feedback": "positive",
            "task_completed": True,
            "was_escalated": False,
            "had_followup": False,
        },
        {
            "user_feedback": "positive",
            "task_completed": True,
            "was_escalated": False,
            "had_followup": False,
        },
        {
            "user_feedback": "negative",
            "task_completed": False,
            "was_escalated": True,
            "had_followup": True,
        },
    ]

    score = compute_effectiveness_score(interactions)

    assert 0.0 <= score <= 1.0
    # 2/3 positive, 2/3 completed, 1/3 escalated, 1/3 retry
    # = 0.35*0.667 + 0.30*0.667 + 0.20*(1-0.333) + 0.15*(1-0.333)
    # ≈ 0.234 + 0.200 + 0.133 + 0.100 = 0.667
    assert 0.6 <= score <= 0.7
