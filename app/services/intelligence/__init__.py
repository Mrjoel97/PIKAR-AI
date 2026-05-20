"""Shared intelligence infrastructure used by agents.

Public surface:
- score_confidence / to_band — generic weighted scorer and band classifier
- presets — named confidence formulas per agent domain
- write_claim / write_claims / find_claims — kg_findings writers and reader
- search_claims_semantic — pgvector cosine-distance semantic search
- detect_contradictions — embedding-similarity contradiction flagger
- claim_freshness_hours — graph-tier freshness check
- get_or_create_entity — entity resolution with idempotent upsert
- should_query_graph / should_call_external — two-tier adaptive cache
- Claim / ClaimPayload / ClaimSource / ConfidenceBand / CacheDecision — schemas
"""

from app.services.intelligence import presets
from app.services.intelligence.cache import should_call_external, should_query_graph
from app.services.intelligence.claims import (
    claim_freshness_hours,
    detect_contradictions,
    find_claims,
    get_or_create_entity,
    search_claims_semantic,
    write_claim,
    write_claims,
)
from app.services.intelligence.confidence import score_confidence, to_band
from app.services.intelligence.schemas import (
    CacheDecision,
    Claim,
    ClaimPayload,
    ClaimSource,
    ConfidenceBand,
)

__all__ = [
    "CacheDecision",
    "Claim",
    "ClaimPayload",
    "ClaimSource",
    "ConfidenceBand",
    "claim_freshness_hours",
    "detect_contradictions",
    "find_claims",
    "get_or_create_entity",
    "presets",
    "score_confidence",
    "search_claims_semantic",
    "should_call_external",
    "should_query_graph",
    "to_band",
    "write_claim",
    "write_claims",
]
