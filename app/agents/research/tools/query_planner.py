"""Query planner for multi-track research decomposition.

Takes a research question and decomposes it into focused sub-queries,
each assigned a track type. This is the GSD-style decomposition that
enables parallel independent research tracks.

Track types (inspired by GSD research documents):
- primary: Direct answer to the query (GSD: FEATURES.md)
- context: Background/conditions around the topic (GSD: ARCHITECTURE.md)
- contrarian: Opposing views, alternative data (GSD: PITFALLS.md)
- impact: Practical implications for the user (GSD: SUMMARY.md)
- risk: Uncertainty factors, what could go wrong (GSD: PITFALLS.md)
- historical: Trend data, how this has changed (GSD: STACK.md)
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Track configurations by depth
TRACK_CONFIGS = {
    "quick": ["primary"],
    "standard": ["primary", "context", "impact"],
    "deep": ["primary", "context", "contrarian", "impact", "risk"],
}

# Domain-specific keywords to inject into queries for better results
DOMAIN_KEYWORDS = {
    "financial": ["market", "investment", "economic", "financial", "fiscal"],
    "marketing": ["brand", "campaign", "audience", "trend", "digital marketing"],
    "compliance": [
        "regulation",
        "compliance",
        "legal",
        "policy",
        "ruling",
        "enforcement",
    ],
    "sales": ["revenue", "pipeline", "conversion", "deal", "pricing"],
    "strategic": [
        "competitive",
        "strategy",
        "market position",
        "growth",
        "opportunity",
    ],
    "operations": [
        "process",
        "efficiency",
        "supply chain",
        "operational",
        "logistics",
    ],
    "hr": ["workforce", "talent", "employment", "HR policy", "labor"],
    "customer_support": [
        "customer satisfaction",
        "support",
        "service",
        "feedback",
        "NPS",
    ],
    "data": [
        "analytics",
        "data platform",
        "metrics",
        "dashboard",
        "data engineering",
    ],
    "content": [
        "content strategy",
        "publishing",
        "editorial",
        "media",
        "content marketing",
    ],
}

# Templates for generating track-specific queries
TRACK_TEMPLATES = {
    "primary": "{query} {year} latest",
    "context": "{query} background context {domain_kw} landscape overview",
    "contrarian": (
        "{query} criticism risks challenges opposing view alternative perspective"
    ),
    "impact": "{query} impact implications business practical effects {domain_kw}",
    "risk": "{query} risks uncertainty threats what could go wrong {domain_kw}",
    "historical": "{query} history trend over time evolution changes {year_range}",
}


def plan_queries(
    query: str,
    domain: str,
    depth: str = "standard",
) -> dict[str, Any]:
    """Decompose a research question into multi-track sub-queries.

    Args:
        query: The original research question.
        domain: Agent domain for context-aware query generation.
        depth: Research depth — 'quick' (1 track), 'standard' (3), or 'deep' (5).

    Returns:
        Dict with success flag and list of track dicts, each containing
        'query' and 'track_type'.
    """
    if not query or not query.strip():
        return {"success": False, "tracks": [], "error": "Query cannot be empty"}

    track_types = TRACK_CONFIGS.get(depth, TRACK_CONFIGS["standard"])
    domain_keywords = DOMAIN_KEYWORDS.get(domain, [])
    domain_kw = domain_keywords[0] if domain_keywords else domain

    year = datetime.datetime.now(tz=datetime.timezone.utc).year
    year_range = f"{year - 2}-{year}"

    tracks = []
    for track_type in track_types:
        template = TRACK_TEMPLATES.get(track_type, "{query}")
        track_query = template.format(
            query=query.strip(),
            domain_kw=domain_kw,
            year=year,
            year_range=year_range,
        )
        tracks.append(
            {
                "query": track_query,
                "track_type": track_type,
            }
        )

    return {
        "success": True,
        "tracks": tracks,
        "original_query": query,
        "domain": domain,
        "depth": depth,
    }


# ADK tool export
QUERY_PLANNER_TOOLS = [plan_queries]
