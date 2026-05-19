"""Two-tier adaptive cache: graph for claims, Redis for raw external calls.

Public surface:
- should_query_graph   — consult kg_findings freshness
- should_call_external — consult Redis with age tracking

Both return CacheDecision(tier, verdict, freshness_hours). Reads degrade
silently — backend failure returns verdict='miss' forcing a fresh fetch.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.services.intelligence.schemas import CacheDecision

logger = logging.getLogger(__name__)


async def should_query_graph(
    *,
    entity_id: UUID,
    claim_type: str | None,
    agent_id: str | None,
    freshness_threshold_hours: float,
) -> CacheDecision:
    """Stub — implemented in Task 4."""
    raise NotImplementedError("Implemented in Plan 112-04 Task 4")


async def should_call_external(
    *,
    cache_key: str,
    ttl_seconds: int,
) -> CacheDecision:
    """Stub — implemented in Task 6."""
    raise NotImplementedError("Implemented in Plan 112-04 Task 6")
