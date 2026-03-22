"""Tests for the adaptive research depth router."""

from __future__ import annotations

from unittest.mock import patch


def test_determine_depth_returns_valid_depth():
    """Router returns a valid ResearchDepth enum value."""
    from app.agents.research.tools.adaptive_router import ResearchDepth, determine_depth

    result = determine_depth(
        query="What are interest rates in South Africa?",
        domain="financial",
        agent_id="FIN",
    )

    assert isinstance(result, ResearchDepth)
    assert result in (
        ResearchDepth.CACHE_ONLY,
        ResearchDepth.QUICK,
        ResearchDepth.STANDARD,
        ResearchDepth.DEEP,
    )


def test_fresh_graph_data_returns_cache_only():
    """If graph has fresh data, router returns CACHE_ONLY."""
    from app.agents.research.tools.adaptive_router import ResearchDepth, determine_depth

    result = determine_depth(
        query="test query",
        domain="financial",
        agent_id="FIN",
        graph_freshness_hours=1.0,  # 1 hour old, threshold is 4h for financial
    )

    assert result == ResearchDepth.CACHE_ONLY


def test_stale_graph_data_triggers_research():
    """If graph data is stale, router recommends research."""
    from app.agents.research.tools.adaptive_router import ResearchDepth, determine_depth

    result = determine_depth(
        query="What are interest rates in South Africa?",
        domain="financial",
        agent_id="FIN",
        graph_freshness_hours=10.0,  # 10 hours old, threshold is 4h
    )

    assert result in (ResearchDepth.QUICK, ResearchDepth.STANDARD, ResearchDepth.DEEP)


def test_no_graph_data_triggers_research():
    """If no graph data exists, router recommends research."""
    from app.agents.research.tools.adaptive_router import ResearchDepth, determine_depth

    result = determine_depth(
        query="Something never researched before",
        domain="financial",
        agent_id="FIN",
        graph_freshness_hours=None,  # no data
    )

    assert result != ResearchDepth.CACHE_ONLY


def test_exhausted_budget_returns_cache_only():
    """If domain budget is exhausted, router falls back to CACHE_ONLY."""
    from app.agents.research.tools.adaptive_router import ResearchDepth, determine_depth

    with patch("app.agents.research.tools.adaptive_router._check_budget", return_value=False):
        result = determine_depth(
            query="test",
            domain="financial",
            agent_id="FIN",
            graph_freshness_hours=None,
        )

    assert result == ResearchDepth.CACHE_ONLY


def test_high_priority_domain_gets_deeper_research():
    """Financial domain (high priority) gets deeper research than HR."""
    from app.agents.research.tools.adaptive_router import determine_depth

    financial_depth = determine_depth(
        query="market analysis question",
        domain="financial",
        agent_id="FIN",
        graph_freshness_hours=None,
    )
    hr_depth = determine_depth(
        query="leave policy question",
        domain="hr",
        agent_id="HR",
        graph_freshness_hours=None,
    )

    # Financial should get at least as deep as HR
    assert financial_depth.value >= hr_depth.value


def test_depth_to_string():
    """ResearchDepth enum converts to string for storage."""
    from app.agents.research.tools.adaptive_router import ResearchDepth

    assert ResearchDepth.CACHE_ONLY.name.lower() == "cache_only"
    assert ResearchDepth.DEEP.name.lower() == "deep"
