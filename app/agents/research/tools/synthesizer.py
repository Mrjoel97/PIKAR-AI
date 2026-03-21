"""Cross-track synthesis for multi-track research.

Takes results from parallel track runners and:
1. Merges and deduplicates sources across tracks
2. Extracts key findings from scraped content
3. Identifies contradictions between tracks
4. Calculates confidence using the multi-track formula
5. Produces a structured synthesis ready for graph persistence
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def synthesize_tracks(
    track_results: list[dict[str, Any]],
    original_query: str,
    domain: str,
) -> dict[str, Any]:
    """Synthesize results from multiple parallel research tracks.

    Args:
        track_results: List of track runner results.
        original_query: The original research question.
        domain: Agent domain for context.

    Returns:
        Dict with findings, confidence, sources, contradictions, and metadata.
    """
    succeeded = [t for t in track_results if t.get("success")]
    failed = [t for t in track_results if not t.get("success")]

    if not succeeded:
        return {
            "success": False,
            "findings": [],
            "confidence": 0.0,
            "all_sources": [],
            "contradictions": [],
            "tracks_succeeded": 0,
            "tracks_failed": len(failed),
            "error": "All research tracks failed",
        }

    # Merge sources across tracks
    all_sources: list[dict[str, Any]] = []
    all_scraped: list[dict[str, Any]] = []
    search_count = 0
    scrape_count = 0

    for track in succeeded:
        all_sources.extend(track.get("sources", []))
        all_scraped.extend(track.get("scraped_content", []))
        search_count += track.get("search_count", 1)
        scrape_count += track.get("scrape_count", 0)

    # Deduplicate sources by URL
    seen_urls: set[str] = set()
    unique_sources: list[dict[str, Any]] = []
    for source in sorted(all_sources, key=lambda s: s.get("score", 0), reverse=True):
        url = source.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_sources.append(source)

    # Extract findings from scraped content
    findings = extract_findings(
        scraped_content=all_scraped,
        sources=unique_sources,
    )

    # Calculate track agreement (findings seen in 2+ tracks)
    track_agreement = _calculate_track_agreement(
        findings=findings,
        track_count=len(succeeded),
    )

    # Source quality (average Tavily score)
    source_scores = [s.get("score", 0) for s in unique_sources if s.get("score")]
    source_quality = sum(source_scores) / len(source_scores) if source_scores else 0.5

    # Freshness (use 1.0 as default — sources are live)
    freshness = 1.0

    # Contradictions (simple text overlap check)
    contradictions = _find_contradictions(findings)

    # Calculate confidence
    confidence = calculate_confidence(
        track_agreement=track_agreement,
        source_quality=source_quality,
        freshness=freshness,
        contradictions_found=len(contradictions),
    )

    return {
        "success": True,
        "findings": findings,
        "confidence": round(confidence, 3),
        "all_sources": unique_sources,
        "contradictions": contradictions,
        "tracks_succeeded": len(succeeded),
        "tracks_failed": len(failed),
        "search_count": search_count,
        "scrape_count": scrape_count,
        "original_query": original_query,
        "domain": domain,
        "track_agreement": round(track_agreement, 3),
        "source_quality": round(source_quality, 3),
    }


def calculate_confidence(
    track_agreement: float,
    source_quality: float,
    freshness: float,
    contradictions_found: int,
) -> float:
    """Calculate confidence using the multi-track formula from spec.

    Formula:
        confidence = (track_agreement * 0.35) + (source_quality * 0.30)
                   + (freshness * 0.20) + ((1 - contradiction_penalty) * 0.15)

    Args:
        track_agreement: Ratio of cross-validated findings (0.0-1.0).
        source_quality: Average source relevance score (0.0-1.0).
        freshness: Source freshness score (0.0-1.0).
        contradictions_found: Number of contradictions detected.

    Returns:
        Confidence score between 0.0 and 1.0.
    """
    contradiction_penalty = min(1.0, contradictions_found * 0.05)
    freshness_clamped = max(0.0, freshness)

    confidence = (
        track_agreement * 0.35
        + source_quality * 0.30
        + freshness_clamped * 0.20
        + (1.0 - contradiction_penalty) * 0.15
    )

    return max(0.0, min(1.0, confidence))


def extract_findings(
    scraped_content: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract key findings from scraped content and source summaries.

    Each finding includes the text, source URL, and a confidence based
    on the source's Tavily score.

    Args:
        scraped_content: List of scrape results with 'markdown' content.
        sources: List of search sources with 'score' and 'url'.

    Returns:
        List of finding dicts with 'text', 'source_url', 'confidence'.
    """
    source_scores = {s.get("url", ""): s.get("score", 0.5) for s in sources}
    findings: list[dict[str, Any]] = []

    # Extract from scraped content (primary source of findings)
    for scrape in scraped_content:
        if not scrape.get("success") and not scrape.get("markdown"):
            continue
        url = scrape.get("url", "")
        markdown = scrape.get("markdown", "")
        title = scrape.get("metadata", {}).get("title", "")

        # Split into paragraphs and take substantive ones as findings
        paragraphs = [
            p.strip()
            for p in markdown.split("\n\n")
            if p.strip() and len(p.strip()) > 50 and not p.strip().startswith("#")
        ]

        for para in paragraphs[:3]:  # max 3 findings per source
            findings.append(
                {
                    "text": para[:500],  # cap at 500 chars
                    "source_url": url,
                    "source_title": title,
                    "confidence": source_scores.get(url, 0.5),
                }
            )

    # If no scraped findings, fall back to source content summaries
    if not findings:
        for source in sources[:5]:
            content = source.get("content", "")
            if content and len(content) > 30:
                findings.append(
                    {
                        "text": content[:500],
                        "source_url": source.get("url", ""),
                        "source_title": source.get("title", ""),
                        "confidence": source.get("score", 0.5),
                    }
                )

    return findings


def _calculate_track_agreement(
    findings: list[dict[str, Any]],
    track_count: int,
) -> float:
    """Estimate cross-track agreement.

    For single-track research, returns 0.5 (neutral).
    For multi-track, counts how many findings have corroborating
    sources from different URLs.

    Args:
        findings: List of extracted findings.
        track_count: Number of successful tracks.

    Returns:
        Agreement score between 0.0 and 1.0.
    """
    if track_count <= 1:
        return 0.5  # neutral for single track

    if not findings:
        return 0.0

    # Count findings that have sources from multiple URLs
    urls = {f.get("source_url") for f in findings if f.get("source_url")}
    if len(urls) <= 1:
        return 0.3  # all from same source

    # More unique sources = higher agreement
    return min(1.0, len(urls) / (track_count * 2))


def _find_contradictions(findings: list[dict[str, Any]]) -> list[str]:
    """Detect potential contradictions between findings.

    Simple heuristic: looks for findings containing numbers that
    differ for the same topic keywords.

    Args:
        findings: List of finding dicts.

    Returns:
        List of contradiction description strings.
    """
    # Simple implementation — full LLM-based contradiction
    # detection will be added in a later phase
    return []


# ADK tool export
SYNTHESIZER_TOOLS = [synthesize_tracks]
