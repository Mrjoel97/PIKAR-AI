"""Tests for the research synthesizer."""

from __future__ import annotations


def test_synthesize_findings_returns_structure():
    """Synthesizer returns findings, confidence, contradictions, entities."""
    from app.agents.research.tools.synthesizer import synthesize_tracks

    track_results = [
        {
            "success": True,
            "track_type": "primary",
            "sources": [
                {
                    "title": "SARB cuts rate",
                    "url": "https://a.com",
                    "content": "SARB cut repo rate to 7.75%",
                    "score": 0.92,
                },
            ],
            "scraped_content": [
                {
                    "success": True,
                    "url": "https://a.com",
                    "markdown": "SARB cut repo rate by 25bps to 7.75% on March 20, 2026.",
                    "metadata": {"title": "SARB"},
                },
            ],
        },
        {
            "success": True,
            "track_type": "context",
            "sources": [
                {
                    "title": "SA Inflation",
                    "url": "https://b.com",
                    "content": "Inflation eased to 4.2% y/y",
                    "score": 0.88,
                },
            ],
            "scraped_content": [
                {
                    "success": True,
                    "url": "https://b.com",
                    "markdown": "South Africa inflation fell to 4.2%.",
                    "metadata": {"title": "Inflation"},
                },
            ],
        },
    ]

    result = synthesize_tracks(
        track_results=track_results,
        original_query="South Africa interest rates",
        domain="financial",
    )

    assert result["success"] is True
    assert isinstance(result["findings"], list)
    assert len(result["findings"]) >= 1
    assert isinstance(result["confidence"], float)
    assert 0.0 <= result["confidence"] <= 1.0
    assert isinstance(result["all_sources"], list)


def test_synthesize_handles_failed_tracks():
    """Synthesizer works even if some tracks failed."""
    from app.agents.research.tools.synthesizer import synthesize_tracks

    track_results = [
        {
            "success": True,
            "track_type": "primary",
            "sources": [
                {
                    "title": "A",
                    "url": "https://a.com",
                    "content": "Data A",
                    "score": 0.9,
                }
            ],
            "scraped_content": [],
        },
        {
            "success": False,
            "track_type": "context",
            "error": "Rate limit",
            "sources": [],
            "scraped_content": [],
        },
    ]

    result = synthesize_tracks(
        track_results=track_results,
        original_query="test",
        domain="financial",
    )

    assert result["success"] is True
    assert result["tracks_succeeded"] == 1
    assert result["tracks_failed"] == 1


def test_synthesize_all_tracks_failed():
    """Synthesizer returns failure when all tracks fail."""
    from app.agents.research.tools.synthesizer import synthesize_tracks

    track_results = [
        {
            "success": False,
            "track_type": "primary",
            "error": "Fail",
            "sources": [],
            "scraped_content": [],
        },
        {
            "success": False,
            "track_type": "context",
            "error": "Fail",
            "sources": [],
            "scraped_content": [],
        },
    ]

    result = synthesize_tracks(
        track_results=track_results,
        original_query="test",
        domain="financial",
    )

    assert result["success"] is False


def test_confidence_formula_multi_track():
    """Confidence scoring uses the multi-track formula from spec."""
    from app.agents.research.tools.synthesizer import calculate_confidence

    confidence = calculate_confidence(
        track_agreement=0.8,
        source_quality=0.85,
        freshness=0.9,
        contradictions_found=1,
    )

    expected = (
        (0.8 * 0.35)
        + (0.85 * 0.30)
        + (0.9 * 0.20)
        + ((1.0 - min(1.0, 1 * 0.05)) * 0.15)
    )
    assert abs(confidence - expected) < 0.01


def test_confidence_quick_research_neutral_agreement():
    """Quick research (single track) uses 0.5 neutral agreement."""
    from app.agents.research.tools.synthesizer import calculate_confidence

    confidence = calculate_confidence(
        track_agreement=0.5,  # neutral for single track
        source_quality=0.8,
        freshness=1.0,
        contradictions_found=0,
    )

    assert 0.0 <= confidence <= 1.0


def test_extract_findings_from_scraped():
    """Findings are extracted from scraped content."""
    from app.agents.research.tools.synthesizer import extract_findings

    scraped = [
        {
            "success": True,
            "url": "https://a.com",
            "markdown": "The South African Reserve Bank cut the repo rate by 25 basis points to 7.75% on 20 March 2026, citing easing inflation pressures.",
            "metadata": {"title": "SARB"},
        },
        {
            "success": True,
            "url": "https://b.com",
            "markdown": "The rand weakened sharply against the US dollar following global risk-off sentiment and rising uncertainty in emerging markets.",
            "metadata": {"title": "Rand"},
        },
    ]
    sources = [
        {
            "url": "https://a.com",
            "title": "SARB",
            "score": 0.9,
            "content": "SARB cut the repo rate to 7.75% in March 2026",
        },
        {
            "url": "https://b.com",
            "title": "Rand",
            "score": 0.8,
            "content": "The rand weakened against the dollar sharply",
        },
    ]

    findings = extract_findings(scraped_content=scraped, sources=sources)

    assert isinstance(findings, list)
    assert len(findings) >= 1
    for f in findings:
        assert "text" in f
        assert "source_url" in f
        assert "confidence" in f
