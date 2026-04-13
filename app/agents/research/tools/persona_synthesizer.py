# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Persona-aware synthesis formatter for the Research Intelligence Agent.

Transforms the structured output of ``synthesize_tracks`` into a presentation
format matched to the user's persona:

- solopreneur: concise bullets + concrete action items
- startup: moderate detail with source attribution + prioritised recommendations
- sme: structured report with source URLs, data quality assessment
- enterprise: formal executive briefing with full methodology + citation appendix

The function also falls back to "startup" for unknown or missing personas.

Phase 69 addition.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Personas that map to a recognised format
_PERSONA_FORMATS: frozenset[str] = frozenset(
    {"solopreneur", "startup", "sme", "enterprise"}
)

# Categorical confidence bands
_CONFIDENCE_BANDS: tuple[tuple[float, str], ...] = (
    (0.75, "high"),
    (0.50, "medium"),
    (0.0, "low"),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def format_synthesis_for_persona(
    synthesis: dict[str, Any],
    persona: str | None = "startup",
) -> dict[str, Any]:
    """Format research synthesis output according to the user's persona.

    Accepts the dict returned by ``synthesize_tracks`` and produces a
    persona-tailored representation suitable for direct agent response.

    Args:
        synthesis: Output of ``synthesize_tracks`` — must contain at minimum
            the keys ``findings``, ``confidence``, ``all_sources``,
            ``contradictions``, ``tracks_succeeded``, ``scrape_count``.
        persona: Target persona string.  One of solopreneur, startup, sme,
            enterprise.  ``None`` or an unrecognised string defaults to
            startup (the balanced middle ground).

    Returns:
        A formatted dict with persona-specific keys.  Always includes
        ``format`` (the persona name that was applied).

    """
    # Resolve persona — fall back to "startup" for None / unknown
    if persona is None or persona not in _PERSONA_FORMATS:
        persona = "startup"

    findings: list[dict[str, Any]] = synthesis.get("findings") or []
    sources: list[dict[str, Any]] = synthesis.get("all_sources") or []
    confidence_score: float = float(synthesis.get("confidence", 0.0))
    contradictions: list[Any] = synthesis.get("contradictions") or []
    tracks_used: int = int(synthesis.get("tracks_succeeded", 0))
    scrape_count: int = int(synthesis.get("scrape_count", 0))

    # Dispatch to per-persona formatter
    if persona == "solopreneur":
        return _format_solopreneur(findings, sources, confidence_score)
    if persona == "startup":
        return _format_startup(findings, sources, confidence_score)
    if persona == "sme":
        return _format_sme(
            findings, sources, confidence_score, tracks_used, contradictions
        )
    # enterprise
    return _format_enterprise(
        findings, sources, confidence_score, tracks_used, scrape_count, contradictions
    )


# ---------------------------------------------------------------------------
# Per-persona formatters
# ---------------------------------------------------------------------------


def _format_solopreneur(
    findings: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    confidence_score: float,
) -> dict[str, Any]:
    """Concise, action-oriented output for solo founders."""
    if not findings:
        return {
            "format": "solopreneur",
            "no_findings": True,
            "summary": "No findings were returned for this query.",
            "key_findings": [],
            "action_items": [],
            "confidence": "low",
            "source_count": 0,
            "follow_up_queries": [
                "Try a more specific search term.",
                "Check if the topic is too niche or recent.",
                "Consider broadening the query scope.",
            ],
        }

    # Cap at 5 bullet findings, favour highest confidence
    top_findings = sorted(
        findings, key=lambda f: f.get("confidence", 0), reverse=True
    )[:5]

    return {
        "format": "solopreneur",
        "summary": _build_summary(findings, max_sentences=2),
        "key_findings": [f["text"][:200] for f in top_findings],
        "action_items": _extract_action_items(findings),
        "confidence": _confidence_label(confidence_score),
        "source_count": len(sources),
    }


def _format_startup(
    findings: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    confidence_score: float,
) -> dict[str, Any]:
    """Moderate detail with recommendation focus for small teams."""
    if not findings:
        return {
            "format": "startup",
            "no_findings": True,
            "summary": "No research findings were available for this query.",
            "key_findings": [],
            "recommendations": [],
            "confidence": {"score": 0.0, "explanation": "No data available."},
            "sources_consulted": 0,
            "follow_up_queries": [
                "Rephrase the query with more specific terms.",
                "Try researching individual sub-topics separately.",
            ],
        }

    top_findings = sorted(
        findings, key=lambda f: f.get("confidence", 0), reverse=True
    )[:7]

    key_findings = [
        {
            "finding": f["text"][:300],
            "source": _domain_from_url(f.get("source_url", "")),
        }
        for f in top_findings
    ]

    recommendations = _build_recommendations(findings, detail_level="startup")

    return {
        "format": "startup",
        "summary": _build_summary(findings, max_sentences=4),
        "key_findings": key_findings,
        "recommendations": recommendations,
        "confidence": {
            "score": round(confidence_score, 2),
            "explanation": _confidence_explanation(confidence_score),
        },
        "sources_consulted": len(sources),
    }


def _format_sme(
    findings: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    confidence_score: float,
    tracks_used: int,
    contradictions: list[Any],
) -> dict[str, Any]:
    """Structured report for small-medium enterprises."""
    if not findings:
        return {
            "format": "sme",
            "no_findings": True,
            "summary": "No research findings were available for this query.",
            "findings": [],
            "recommendations": [],
            "data_quality": {
                "confidence": 0.0,
                "tracks_used": tracks_used,
                "contradictions": 0,
            },
            "sources": [],
            "follow_up_queries": [
                "Expand the query scope or increase research depth.",
                "Verify that the topic is publicly covered in industry sources.",
            ],
        }

    sme_findings = [
        {
            "finding": f["text"][:400],
            "source_url": f.get("source_url", ""),
            "source_title": f.get("source_title", ""),
        }
        for f in findings
    ]

    recommendations = _build_recommendations(findings, detail_level="sme")

    source_list = [
        {"title": s.get("title", ""), "url": s.get("url", "")}
        for s in sources
    ]

    return {
        "format": "sme",
        "summary": _build_summary(findings, max_sentences=5),
        "findings": sme_findings,
        "recommendations": recommendations,
        "data_quality": {
            "confidence": round(confidence_score, 2),
            "tracks_used": tracks_used,
            "contradictions": len(contradictions),
        },
        "sources": source_list,
    }


def _format_enterprise(
    findings: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    confidence_score: float,
    tracks_used: int,
    scrape_count: int,
    contradictions: list[Any],
) -> dict[str, Any]:
    """Formal executive briefing for large organisations."""
    if not findings:
        return {
            "format": "enterprise",
            "no_findings": True,
            "executive_summary": (
                "The research query did not return sufficient findings "
                "for a formal briefing. This may indicate the topic is "
                "not yet covered by indexed public sources, "
                "or the query requires narrowing."
            ),
            "methodology": {
                "tracks_used": tracks_used,
                "sources_consulted": 0,
                "scrapes_performed": scrape_count,
                "approach": "Multi-track parallel research with cross-track synthesis.",
            },
            "detailed_findings": [],
            "risk_assessment": {
                "overall_confidence": 0.0,
                "contradictions": [],
                "data_gaps": ["No findings returned. Broaden query scope."],
            },
            "recommendations": [],
            "appendix_sources": [],
            "follow_up_queries": [
                "Increase research depth to 'deep' (5 tracks, 5 searches).",
                "Add domain-specific pinned URLs for authoritative sources.",
                "Rephrase the query using industry-standard terminology.",
            ],
        }

    citations = _build_citations(sources)
    detailed_findings = [
        {
            "id": idx + 1,
            "finding": f["text"][:600],
            "citation": citations.get(f.get("source_url", ""), ""),
            "confidence": round(float(f.get("confidence", 0.5)), 2),
        }
        for idx, f in enumerate(findings)
    ]

    appendix_sources = [
        {
            "id": idx + 1,
            "title": s.get("title", ""),
            "url": s.get("url", ""),
            "accessed": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
        }
        for idx, s in enumerate(sources)
    ]

    data_gaps: list[str] = []
    if confidence_score < 0.5:
        data_gaps.append("Low confidence — limited cross-track validation.")
    if not sources:
        data_gaps.append("No sources retrieved — query may need refinement.")

    return {
        "format": "enterprise",
        "executive_summary": _build_executive_summary(findings, confidence_score),
        "methodology": {
            "tracks_used": tracks_used,
            "sources_consulted": len(sources),
            "scrapes_performed": scrape_count,
            "approach": (
                "Multi-track parallel research with cross-track "
                "synthesis and confidence scoring."
            ),
        },
        "detailed_findings": detailed_findings,
        "risk_assessment": {
            "overall_confidence": round(confidence_score, 2),
            "contradictions": [str(c) for c in contradictions],
            "data_gaps": data_gaps,
        },
        "recommendations": _build_recommendations(findings, detail_level="enterprise"),
        "appendix_sources": appendix_sources,
    }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _build_summary(findings: list[dict[str, Any]], max_sentences: int) -> str:
    """Build a plain-language summary from the top findings.

    Joins the first ``max_sentences`` finding texts into a coherent summary
    string.  Truncates each finding snippet to avoid very long lines.

    Args:
        findings: List of finding dicts with a ``text`` key.
        max_sentences: Maximum number of finding snippets to include.

    Returns:
        A summary string.

    """
    if not findings:
        return "No findings were available for this query."

    top = sorted(
        findings, key=lambda f: f.get("confidence", 0), reverse=True
    )[:max_sentences]
    sentences = []
    for f in top:
        text = f.get("text", "").strip()
        # Trim at sentence boundary if possible
        if "." in text[:300]:
            idx = text.index(".", 0, 300)
            text = text[: idx + 1]
        else:
            text = text[:200]
        sentences.append(text)

    return " ".join(sentences)


def _build_executive_summary(
    findings: list[dict[str, Any]], confidence_score: float
) -> str:
    """Build a formal executive-briefing paragraph from top findings.

    Args:
        findings: List of finding dicts.
        confidence_score: Overall confidence from synthesis.

    Returns:
        A multi-sentence executive summary string.

    """
    if not findings:
        return "No findings were available to construct an executive summary."

    top = sorted(findings, key=lambda f: f.get("confidence", 0), reverse=True)[:3]
    snippets = []
    for f in top:
        text = f.get("text", "")[:300]
        parts = text.split(".")
        snippet = ". ".join(p.strip() for p in parts[:2] if p.strip())
        if snippet and not snippet.endswith("."):
            snippet += "."
        snippets.append(snippet)
    core = " ".join(s for s in snippets if s)
    label = _confidence_label(confidence_score)
    return (
        f"{core} "
        f"The overall research confidence is {label} ({confidence_score:.0%}), "
        f"based on cross-track validation across {len(findings)} findings from "
        f"{len(set(f.get('source_url') for f in findings))} unique sources."
    )


def _extract_action_items(findings: list[dict[str, Any]]) -> list[str]:
    """Derive concrete action items from research findings.

    Uses simple heuristics: findings that contain forward-looking language
    (consider, recommend, should, opportunity, risk, increase, decrease) are
    surfaced as action items.  Falls back to generic advice when none match.

    Args:
        findings: List of finding dicts.

    Returns:
        List of up to 3 action item strings.

    """
    action_keywords = {
        "consider", "recommend", "should", "opportunity", "risk",
        "increase", "decrease", "monitor", "watch", "avoid", "invest",
        "adopt", "review", "explore", "assess", "evaluate",
    }

    action_items: list[str] = []
    for f in findings:
        text = f.get("text", "").lower()
        if any(kw in text for kw in action_keywords):
            snippet = f["text"][:150].rstrip(".,;")
            action_items.append(f"Review: {snippet}")
        if len(action_items) >= 3:
            break

    if not action_items:
        action_items = [
            "Review the full source list for additional context.",
            "Consider validating findings with a primary source.",
            "Monitor this topic for updates over the next 30 days.",
        ]

    return action_items[:3]


def _build_recommendations(
    findings: list[dict[str, Any]],
    detail_level: str,
) -> list[dict[str, Any]]:
    """Build prioritised recommendations from research findings.

    Args:
        findings: List of finding dicts.
        detail_level: One of "startup", "sme", "enterprise" — controls dict shape.

    Returns:
        List of recommendation dicts.

    """
    recs: list[dict[str, Any]] = []

    action_keywords: dict[str, set[str]] = {
        "high": {
            "risk", "critical", "urgent", "immediately", "must",
            "increase", "decrease",
        },
        "medium": {
            "consider", "opportunity", "recommend", "should",
            "monitor", "explore",
        },
        "low": {"may", "could", "might", "possible", "watch"},
    }

    for i, f in enumerate(findings[:6]):
        text = f.get("text", "").lower()
        priority = "medium"
        for tier, keywords in action_keywords.items():
            if any(kw in text for kw in keywords):
                priority = tier
                break

        action = f["text"][:200].rstrip(".,;")
        source_domain = _domain_from_url(f.get("source_url", "unknown"))
        rationale = f"Based on source: {source_domain}"

        if detail_level == "startup":
            recs.append(
                {"action": action, "priority": priority, "rationale": rationale}
            )
        elif detail_level == "sme":
            recs.append({
                "action": action,
                "priority": priority,
                "rationale": rationale,
                "estimated_impact": "To be assessed by management.",
            })
        else:  # enterprise
            recs.append({
                "action": action,
                "priority": priority,
                "rationale": rationale,
                "risk": "Verify with internal stakeholders before acting.",
            })

        if len(recs) >= 3:
            break

    return recs


def _build_citations(sources: list[dict[str, Any]]) -> dict[str, str]:
    """Build a URL → numbered citation string mapping.

    Args:
        sources: List of source dicts with ``url`` and ``title`` keys.

    Returns:
        Dict mapping source URL to citation string like "[1] https://...".

    """
    citations: dict[str, str] = {}
    for idx, source in enumerate(sources, start=1):
        url = source.get("url", "")
        if url:
            citations[url] = f"[{idx}] {url}"
    return citations


def _confidence_label(score: float) -> str:
    """Map a 0-1 confidence score to a categorical label.

    Args:
        score: Confidence score between 0 and 1.

    Returns:
        One of "high", "medium", "low".

    """
    for threshold, label in _CONFIDENCE_BANDS:
        if score >= threshold:
            return label
    return "low"


def _confidence_explanation(score: float) -> str:
    """Return a brief textual explanation of a confidence score.

    Args:
        score: Confidence score between 0 and 1.

    Returns:
        Short explanatory string.

    """
    label = _confidence_label(score)
    pct = f"{score:.0%}"
    if label == "high":
        return f"{pct} — strong cross-track agreement with quality sources."
    if label == "medium":
        return f"{pct} — moderate corroboration; consider verifying key claims."
    return f"{pct} — limited corroboration; treat findings as directional only."


def _domain_from_url(url: str) -> str:
    """Extract the domain name from a URL for inline attribution.

    Args:
        url: A source URL string.

    Returns:
        Domain string (e.g. "techcrunch.com") or the original URL if parsing
        fails.

    """
    if not url:
        return "unknown"
    try:
        # Simple extraction without importing urllib for minimal dependencies
        url = url.split("//")[-1]
        return url.split("/")[0]
    except Exception:
        return url


# ---------------------------------------------------------------------------
# ADK tool export
# ---------------------------------------------------------------------------

PERSONA_SYNTHESIZER_TOOLS = [format_synthesis_for_persona]
