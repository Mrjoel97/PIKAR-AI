"""Shared Pydantic models and type aliases for the intelligence package."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, computed_field

ConfidenceBand = Literal["low", "medium", "high"]


class ClaimSource(BaseModel):
    """A source backing a claim. Domain-agnostic."""

    kind: Literal[
        "url",
        "supabase_row",
        "stripe_row",
        "shopify_row",
        "regulation",
        "user",
        "other",
    ]
    ref: str  # URL, row ID, citation, etc.
    score: float | None = None  # optional source-specific quality score


class Claim(BaseModel):
    """A row from kg_findings as returned by find_claims / search_claims_semantic.

    band is a computed property derived from confidence — keeps band thresholds
    tunable in code without DB migration.
    """

    id: UUID
    entity_id: UUID | None
    edge_id: UUID | None
    agent_id: str
    claim_type: str
    domain: str
    finding_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[ClaimSource]
    contradicts: list[UUID]
    freshness_at: datetime
    expires_at: datetime | None
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def band(self) -> ConfidenceBand:
        """Confidence band derived from the confidence score."""
        from app.services.intelligence.confidence import (
            to_band,  # deferred to avoid circular import
        )

        return to_band(self.confidence)


class ClaimPayload(BaseModel):
    """Input to write_claim / write_claims. Mirrors write_claim's kwargs.

    Distinct from Claim because input lacks DB-assigned fields
    (id, created_at, freshness_at) and carries the embed policy flag.
    """

    entity_id: UUID | None
    edge_id: UUID | None = None
    domain: str
    finding_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[ClaimSource]
    agent_id: str
    claim_type: str
    embed: bool = False
    expires_at: datetime | None = None
    contradicts: list[UUID] = Field(default_factory=list)


@dataclass(frozen=True)
class CacheDecision:
    """Decision returned by should_query_graph / should_call_external.

    Frozen so callers can rely on the value being unchanged after return.
    """

    tier: Literal["graph", "redis"]
    verdict: Literal["fresh", "stale", "miss"]
    freshness_hours: float | None  # None on miss
