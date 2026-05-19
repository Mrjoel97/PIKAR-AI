"""ADK tool: cross-agent semantic claim search."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def search_agent_claims(
    query: str,
    agent_id: str | None = None,
    claim_type: str | None = None,
    top_k: int = 10,
) -> dict[str, Any]:
    """Search all agents' knowledge-graph claims by semantic similarity.

    Args:
        query: Natural-language search string.
        agent_id: Optional — restrict to a specific agent.
        claim_type: Optional — restrict to a single claim_type.
        top_k: Max results returned. Default 10; capped at 100.

    Returns:
        Dict with results list and count int. See docs/intelligence/claim-types.md.
    """
    from app.services.intelligence import search_claims_semantic

    try:
        hits = await search_claims_semantic(
            query=query, agent_id=agent_id, claim_type=claim_type, top_k=top_k,
        )
    except Exception as e:
        logger.warning("search_agent_claims failed: %s", e)
        return {"results": [], "count": 0, "error": str(e)}

    results: list[dict[str, Any]] = []
    for claim, similarity in hits:
        results.append({
            "finding_text": claim.finding_text,
            "confidence": claim.confidence,
            "band": claim.band,
            "agent_id": claim.agent_id,
            "claim_type": claim.claim_type,
            "domain": claim.domain,
            "similarity": similarity,
            "sources": [s.model_dump(exclude_none=True) for s in claim.sources],
            "freshness_at": claim.freshness_at.isoformat(),
        })

    return {"results": results, "count": len(results)}


INTELLIGENCE_SEARCH_TOOLS = [search_agent_claims]
