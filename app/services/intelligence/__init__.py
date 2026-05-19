"""Shared intelligence infrastructure used by agents.

Public surface:
- score_confidence / to_band — generic weighted scorer and band classifier
- presets — named confidence formulas per agent domain
- write_claim / write_claims / find_claims — kg_findings writers and reader
- claim_freshness_hours — graph-tier freshness check (for cache.py in 112-04)
- get_or_create_entity — entity resolution with idempotent upsert
- Claim / ClaimPayload / ClaimSource / ConfidenceBand — schemas

Plan 112-04 will add adaptive cache (should_query_graph, should_call_external).
See the design at docs/superpowers/specs/2026-05-18-shared-intelligence-infra-design.md.
"""

from app.services.intelligence import presets
from app.services.intelligence.claims import (
    claim_freshness_hours,
    find_claims,
    get_or_create_entity,
    write_claim,
    write_claims,
)
from app.services.intelligence.confidence import score_confidence, to_band
from app.services.intelligence.schemas import (
    Claim,
    ClaimPayload,
    ClaimSource,
    ConfidenceBand,
)

__all__ = [
    "Claim",
    "ClaimPayload",
    "ClaimSource",
    "ConfidenceBand",
    "claim_freshness_hours",
    "find_claims",
    "get_or_create_entity",
    "presets",
    "score_confidence",
    "to_band",
    "write_claim",
    "write_claims",
]
