"""Knowledge-graph claims: writes and reads against kg_findings.

Public surface:
- write_claim       — insert one Claim
- write_claims      — bulk insert of ClaimPayload
- find_claims       — structured filter query
- claim_freshness_hours — age of latest matching claim (for cache.py)
- get_or_create_entity  — upsert on kg_entities

All operations use the service-role Supabase client. Writes raise on
failure; reads return [] / None on failure with structured logging.

Embeddings are opt-in via embed=True. Generation defers to
app/rag/embedding_service.py (Vertex AI).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from app.services.intelligence.schemas import Claim, ClaimPayload

logger = logging.getLogger(__name__)


def _get_supabase_client():
    """Build a service-role Supabase client directly from env vars.

    Uses create_client directly rather than the app singleton so this module
    works correctly when the integration conftest has mocked
    app.services.supabase_client.
    """
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)


async def get_or_create_entity(
    *,
    canonical_name: str,
    entity_type: str,
    domains: Sequence[str] = (),
    properties: dict | None = None,
) -> UUID:
    """Upsert a knowledge-graph entity by (canonical_name, entity_type).

    Idempotent: repeated calls with the same canonical_name + entity_type
    return the same UUID. domains and properties update on each call.

    Args:
        canonical_name: Human-readable entity name (e.g., "Acme Corp",
                       "Q1 2026 Cohort").
        entity_type: Must be one of the kg_entities CHECK constraint values:
                    'company', 'person', 'regulation', 'market', 'technology',
                    'topic', 'metric', 'country', 'institution', 'product',
                    'event'.
        domains: List of domain tags (e.g., ['financial', 'data']).
        properties: Arbitrary JSONB metadata.

    Returns:
        UUID of the existing or newly created entity row.

    Raises:
        Exception (from Supabase client) if the upsert fails.
    """
    client = _get_supabase_client()
    row = {
        "canonical_name": canonical_name,
        "entity_type": entity_type,
        "domains": list(domains),
        "properties": properties or {},
    }
    result = client.table("kg_entities").upsert(
        row,
        on_conflict="canonical_name,entity_type",
    ).execute()
    if not result.data:
        raise RuntimeError(
            f"Upsert returned no rows for entity ({canonical_name}, {entity_type})"
        )
    return UUID(result.data[0]["id"])


async def write_claim(
    *,
    entity_id: UUID | None,
    edge_id: UUID | None = None,
    domain: str,
    finding_text: str,
    confidence: float,
    sources: Sequence[dict],
    agent_id: str,
    claim_type: str,
    embed: bool = False,
    expires_at: datetime | None = None,
    contradicts: Sequence[UUID] = (),
) -> UUID:
    """Stub — implemented in Task 5."""
    raise NotImplementedError("Implemented in Plan 112-03 Task 5")


async def write_claims(claims: Sequence[ClaimPayload]) -> list[UUID]:
    """Stub — implemented in Task 6."""
    raise NotImplementedError("Implemented in Plan 112-03 Task 6")


async def find_claims(
    *,
    entity_id: UUID | None = None,
    agent_id: str | None = None,
    claim_type: str | None = None,
    domain: str | None = None,
    min_confidence: float = 0.0,
    fresh_since: datetime | None = None,
    limit: int = 50,
) -> list[Claim]:
    """Stub — implemented in Task 7."""
    raise NotImplementedError("Implemented in Plan 112-03 Task 7")


async def claim_freshness_hours(
    *,
    entity_id: UUID,
    claim_type: str | None = None,
    agent_id: str | None = None,
) -> float | None:
    """Stub — implemented in Task 7."""
    raise NotImplementedError("Implemented in Plan 112-03 Task 7")
