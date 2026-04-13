# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for persona_synthesizer tool.

Tests verify that format_synthesis_for_persona produces correctly structured,
persona-tailored output from a standard synthesize_tracks result dict.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Fixture: a representative synthesize_tracks output dict
# ---------------------------------------------------------------------------

@pytest.fixture()
def synthesis() -> dict:
    """Standard synthesis output matching synthesize_tracks return shape."""
    return {
        "success": True,
        "findings": [
            {
                "text": "Acme Corp raised its prices by 15% in Q1 2026, citing supply chain pressures.",
                "source_url": "https://techcrunch.com/acme-pricing",
                "source_title": "Acme Corp Q1 Pricing Update",
                "confidence": 0.9,
            },
            {
                "text": "Industry analysts expect further price increases across the SaaS sector through Q3 2026.",
                "source_url": "https://forester.com/saas-pricing-report",
                "source_title": "Forrester SaaS Pricing Report 2026",
                "confidence": 0.85,
            },
            {
                "text": "Competitors such as Beta Ltd and Gamma Inc have not followed Acme Corp's price increases.",
                "source_url": "https://businessinsider.com/saas-competitors",
                "source_title": "Business Insider: SaaS Competitor Analysis",
                "confidence": 0.8,
            },
            {
                "text": "Customers surveyed report moderate satisfaction despite the price increase.",
                "source_url": "https://g2.com/acme-reviews",
                "source_title": "G2 Acme Reviews 2026",
                "confidence": 0.75,
            },
            {
                "text": "Acme Corp's revenue grew 22% year-over-year despite churn concerns.",
                "source_url": "https://seekingalpha.com/acme-earnings",
                "source_title": "Acme Earnings Call Summary",
                "confidence": 0.88,
            },
            {
                "text": "Some analysts warn that aggressive pricing may open opportunities for emerging competitors.",
                "source_url": "https://gartner.com/saas-watch",
                "source_title": "Gartner SaaS Watch 2026",
                "confidence": 0.7,
            },
        ],
        "confidence": 0.83,
        "all_sources": [
            {"url": "https://techcrunch.com/acme-pricing", "title": "Acme Corp Q1 Pricing Update", "score": 0.9},
            {"url": "https://forester.com/saas-pricing-report", "title": "Forrester SaaS Pricing Report 2026", "score": 0.85},
            {"url": "https://businessinsider.com/saas-competitors", "title": "Business Insider: SaaS Competitor Analysis", "score": 0.8},
            {"url": "https://g2.com/acme-reviews", "title": "G2 Acme Reviews 2026", "score": 0.75},
            {"url": "https://seekingalpha.com/acme-earnings", "title": "Acme Earnings Call Summary", "score": 0.88},
            {"url": "https://gartner.com/saas-watch", "title": "Gartner SaaS Watch 2026", "score": 0.7},
        ],
        "contradictions": [],
        "tracks_succeeded": 3,
        "tracks_failed": 0,
        "search_count": 9,
        "scrape_count": 6,
        "original_query": "Acme Corp pricing strategy analysis",
        "domain": "sales",
        "track_agreement": 0.75,
        "source_quality": 0.83,
    }


@pytest.fixture()
def empty_synthesis() -> dict:
    """Synthesis with no findings (e.g., all tracks failed or no content)."""
    return {
        "success": True,
        "findings": [],
        "confidence": 0.0,
        "all_sources": [],
        "contradictions": [],
        "tracks_succeeded": 1,
        "tracks_failed": 2,
        "search_count": 3,
        "scrape_count": 0,
        "original_query": "obscure niche topic",
        "domain": "research",
        "track_agreement": 0.0,
        "source_quality": 0.0,
    }


# ---------------------------------------------------------------------------
# Test 1: Solopreneur format structure
# ---------------------------------------------------------------------------

def test_solopreneur_format_has_required_keys(synthesis):
    """Solopreneur format includes summary, key_findings, action_items, confidence, source_count."""
    from app.agents.research.tools.persona_synthesizer import format_synthesis_for_persona

    result = format_synthesis_for_persona(synthesis, persona="solopreneur")

    assert result["format"] == "solopreneur"
    assert "summary" in result, "solopreneur must have 'summary'"
    assert "key_findings" in result, "solopreneur must have 'key_findings'"
    assert "action_items" in result, "solopreneur must have 'action_items'"
    assert "confidence" in result, "solopreneur must have 'confidence'"
    assert "source_count" in result, "solopreneur must have 'source_count'"

    # Key findings capped at 5
    assert len(result["key_findings"]) <= 5

    # Confidence is categorical
    assert result["confidence"] in {"high", "medium", "low"}

    # source_count is just a number
    assert isinstance(result["source_count"], int)


# ---------------------------------------------------------------------------
# Test 2: Solopreneur does NOT include full citations / methodology
# ---------------------------------------------------------------------------

def test_solopreneur_format_excludes_verbose_sections(synthesis):
    """Solopreneur output must NOT contain full citation appendix or methodology."""
    from app.agents.research.tools.persona_synthesizer import format_synthesis_for_persona

    result = format_synthesis_for_persona(synthesis, persona="solopreneur")

    assert "appendix_sources" not in result, "solopreneur should not have appendix_sources"
    assert "methodology" not in result, "solopreneur should not have methodology"
    assert "detailed_findings" not in result, "solopreneur should not have detailed_findings"


# ---------------------------------------------------------------------------
# Test 3: Startup format structure
# ---------------------------------------------------------------------------

def test_startup_format_has_required_keys(synthesis):
    """Startup format includes summary, key_findings with attribution, recommendations, confidence, sources_consulted."""
    from app.agents.research.tools.persona_synthesizer import format_synthesis_for_persona

    result = format_synthesis_for_persona(synthesis, persona="startup")

    assert result["format"] == "startup"
    assert "summary" in result
    assert "key_findings" in result
    assert "recommendations" in result
    assert "confidence" in result
    assert "sources_consulted" in result

    # key_findings items have source attribution
    if result["key_findings"]:
        first_finding = result["key_findings"][0]
        assert "finding" in first_finding
        assert "source" in first_finding

    # confidence is a dict with score and explanation
    assert isinstance(result["confidence"], dict)
    assert "score" in result["confidence"]
    assert "explanation" in result["confidence"]

    # recommendations have priority
    if result["recommendations"]:
        first_rec = result["recommendations"][0]
        assert "action" in first_rec
        assert "priority" in first_rec
        assert "rationale" in first_rec


# ---------------------------------------------------------------------------
# Test 4: Enterprise format structure
# ---------------------------------------------------------------------------

def test_enterprise_format_has_required_keys(synthesis):
    """Enterprise format includes executive_summary, methodology, detailed_findings, risk_assessment, appendix_sources."""
    from app.agents.research.tools.persona_synthesizer import format_synthesis_for_persona

    result = format_synthesis_for_persona(synthesis, persona="enterprise")

    assert result["format"] == "enterprise"
    assert "executive_summary" in result
    assert "methodology" in result
    assert "detailed_findings" in result
    assert "risk_assessment" in result
    assert "appendix_sources" in result

    # Methodology has track and source counts
    methodology = result["methodology"]
    assert "tracks_used" in methodology
    assert "sources_consulted" in methodology

    # Detailed findings have numbered citations
    if result["detailed_findings"]:
        first = result["detailed_findings"][0]
        assert "id" in first
        assert "finding" in first
        assert "citation" in first

    # Appendix sources have id, title, url
    if result["appendix_sources"]:
        first_source = result["appendix_sources"][0]
        assert "id" in first_source
        assert "title" in first_source
        assert "url" in first_source

    # Risk assessment has overall_confidence
    risk = result["risk_assessment"]
    assert "overall_confidence" in risk


# ---------------------------------------------------------------------------
# Test 5: SME format structure
# ---------------------------------------------------------------------------

def test_sme_format_has_required_keys(synthesis):
    """SME format includes summary, findings with source links, recommendations, data_quality."""
    from app.agents.research.tools.persona_synthesizer import format_synthesis_for_persona

    result = format_synthesis_for_persona(synthesis, persona="sme")

    assert result["format"] == "sme"
    assert "summary" in result
    assert "findings" in result
    assert "recommendations" in result
    assert "data_quality" in result

    # findings have source_url
    if result["findings"]:
        first = result["findings"][0]
        assert "finding" in first
        assert "source_url" in first

    # data_quality has confidence and tracks_used
    dq = result["data_quality"]
    assert "confidence" in dq
    assert "tracks_used" in dq


# ---------------------------------------------------------------------------
# Test 6: None persona defaults to startup format
# ---------------------------------------------------------------------------

def test_none_persona_defaults_to_startup(synthesis):
    """When persona=None, the function defaults to startup format."""
    from app.agents.research.tools.persona_synthesizer import format_synthesis_for_persona

    result = format_synthesis_for_persona(synthesis, persona=None)

    assert result["format"] == "startup"


# ---------------------------------------------------------------------------
# Test 7: Empty findings handled gracefully for all personas
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("persona", ["solopreneur", "startup", "sme", "enterprise"])
def test_empty_findings_graceful_handling(empty_synthesis, persona):
    """All personas return a graceful no-findings response when synthesis has no findings."""
    from app.agents.research.tools.persona_synthesizer import format_synthesis_for_persona

    result = format_synthesis_for_persona(empty_synthesis, persona=persona)

    # Must not raise — must return a dict
    assert isinstance(result, dict)
    assert result["format"] == persona

    # Must include a message or indicator that no findings were available
    has_no_findings_indicator = (
        result.get("no_findings") is True
        or "no findings" in str(result).lower()
        or "no results" in str(result).lower()
        or "couldn't find" in str(result).lower()
        or "not find" in str(result).lower()
        or "no data" in str(result).lower()
        or "suggested_queries" in result
        or "follow_up_queries" in result
    )
    assert has_no_findings_indicator, f"Expected a no-findings indicator for persona '{persona}', got: {result}"


# ---------------------------------------------------------------------------
# Test 8: Unknown persona falls back to startup format
# ---------------------------------------------------------------------------

def test_unknown_persona_falls_back_to_startup(synthesis):
    """An unrecognized persona string falls back to startup format."""
    from app.agents.research.tools.persona_synthesizer import format_synthesis_for_persona

    result = format_synthesis_for_persona(synthesis, persona="admin")

    # admin is not a research consumer — should fall back to startup
    assert result["format"] == "startup"


# ---------------------------------------------------------------------------
# Test 9: PERSONA_SYNTHESIZER_TOOLS exports format_synthesis_for_persona
# ---------------------------------------------------------------------------

def test_persona_synthesizer_tools_exported():
    """PERSONA_SYNTHESIZER_TOOLS must be a list containing format_synthesis_for_persona."""
    from app.agents.research.tools.persona_synthesizer import (
        PERSONA_SYNTHESIZER_TOOLS,
        format_synthesis_for_persona,
    )

    assert isinstance(PERSONA_SYNTHESIZER_TOOLS, list)
    assert format_synthesis_for_persona in PERSONA_SYNTHESIZER_TOOLS
