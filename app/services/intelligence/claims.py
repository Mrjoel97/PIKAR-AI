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
    result = (
        client.table("kg_entities")
        .upsert(
            row,
            on_conflict="canonical_name,entity_type",
        )
        .execute()
    )
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
    """Insert a single claim into kg_findings.

    Append-only — never updates existing rows. Each call creates a new row;
    historical claims are retained for audit. Use expires_at to set a
    retention horizon.

    Args:
        entity_id: kg_entities row to attach to (or None if edge_id supplied).
        edge_id: kg_edges row to attach to (or None if entity_id supplied).
        domain: Agent domain tag (e.g., 'data', 'research').
        finding_text: Human-readable claim text.
        confidence: [0.0, 1.0] — typically from a preset like data_confidence.
        sources: List of dicts matching ClaimSource shape (kind, ref, score?).
        agent_id: e.g., 'data', 'research', 'financial'.
        claim_type: Domain-specific type tag (e.g., 'cohort_retention').
        embed: If True, generate embedding via Vertex AI before insert.
        expires_at: Optional retention timestamp.
        contradicts: List of UUIDs of contradicting claims.

    Returns:
        UUID of the newly inserted kg_findings row.

    Raises:
        Exception on Supabase failure or DB constraint violation.
    """
    client = _get_supabase_client()

    embedding: list[float] | None = None
    if embed and finding_text and len(finding_text) >= 20:
        embedding = await _embed_text(finding_text)

    row: dict = {
        "domain": domain,
        "finding_text": finding_text,
        "confidence": confidence,
        "sources": list(sources),
        "contradicts": [str(c) for c in contradicts],
        "agent_id": agent_id,
        "claim_type": claim_type,
    }
    if entity_id is not None:
        row["entity_id"] = str(entity_id)
    if edge_id is not None:
        row["edge_id"] = str(edge_id)
    if embedding is not None:
        row["embedding"] = embedding
    if expires_at is not None:
        row["expires_at"] = expires_at.isoformat()

    result = client.table("kg_findings").insert(row).execute()
    if not result.data:
        raise RuntimeError(f"Insert returned no rows for claim_type={claim_type}")
    return UUID(result.data[0]["id"])


async def _embed_text(text: str) -> list[float] | None:
    """Generate a Vertex AI embedding for the given text.

    Returns None and logs a warning on failure (caller treats as no-embedding).
    The underlying generate_embedding is sync; run it in a thread to avoid
    blocking the event loop.
    """
    import asyncio

    try:
        from app.rag.embedding_service import generate_embedding

        return await asyncio.get_event_loop().run_in_executor(
            None, generate_embedding, text
        )
    except Exception as e:
        logger.warning("Embedding generation failed: %s", e)
        return None


async def write_claims(claims: Sequence[ClaimPayload]) -> list[UUID]:
    """Bulk-insert claims in a single statement.

    Returns IDs in input order. Embeddings are opt-in per-payload (the
    embed flag on ClaimPayload). For mixed embed/no-embed batches, embeddings
    are generated sequentially before the bulk insert.

    Args:
        claims: Sequence of ClaimPayload. Empty input returns []
                without hitting the DB.

    Returns:
        list[UUID] of the inserted row IDs, same order as input.

    Raises:
        Exception on Supabase failure or any single-row constraint violation.
        Partial inserts are NOT possible — the bulk INSERT is atomic.
    """
    if not claims:
        return []

    client = _get_supabase_client()
    rows: list[dict] = []
    for c in claims:
        embedding: list[float] | None = None
        if c.embed and c.finding_text and len(c.finding_text) >= 20:
            embedding = await _embed_text(c.finding_text)

        row: dict = {
            "domain": c.domain,
            "finding_text": c.finding_text,
            "confidence": c.confidence,
            "sources": [s.model_dump(exclude_none=True) for s in c.sources],
            "contradicts": [str(x) for x in c.contradicts],
            "agent_id": c.agent_id,
            "claim_type": c.claim_type,
        }
        if c.entity_id is not None:
            row["entity_id"] = str(c.entity_id)
        if c.edge_id is not None:
            row["edge_id"] = str(c.edge_id)
        if embedding is not None:
            row["embedding"] = embedding
        if c.expires_at is not None:
            row["expires_at"] = c.expires_at.isoformat()
        rows.append(row)

    result = client.table("kg_findings").insert(rows).execute()
    if not result.data or len(result.data) != len(claims):
        raise RuntimeError(
            f"Bulk insert returned {len(result.data) if result.data else 0} rows, "
            f"expected {len(claims)}"
        )
    return [UUID(r["id"]) for r in result.data]


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
    """Structured filter query over kg_findings. All filters AND'd.

    Returns Claim Pydantic models, freshest first.
    Empty result returns []; DB failure logs and returns [].

    Args:
        entity_id: Restrict to claims about this entity.
        agent_id: Restrict to claims emitted by this agent.
        claim_type: Restrict to a single claim type.
        domain: Restrict to a single domain.
        min_confidence: Floor confidence (inclusive).
        fresh_since: Only claims with freshness_at >= this timestamp.
        limit: Max rows returned. Default 50.

    Returns:
        list[Claim] sorted by freshness_at DESC.
    """
    from app.services.intelligence.schemas import ClaimSource

    try:
        client = _get_supabase_client()
        q = client.table("kg_findings").select("*")
        if entity_id is not None:
            q = q.eq("entity_id", str(entity_id))
        if agent_id is not None:
            q = q.eq("agent_id", agent_id)
        if claim_type is not None:
            q = q.eq("claim_type", claim_type)
        if domain is not None:
            q = q.eq("domain", domain)
        if min_confidence > 0:
            q = q.gte("confidence", min_confidence)
        if fresh_since is not None:
            q = q.gte("freshness_at", fresh_since.isoformat())
        q = q.order("freshness_at", desc=True).limit(limit)
        result = q.execute()

        claims: list[Claim] = []
        for r in result.data or []:
            sources_raw = r.get("sources") or []
            sources = [
                ClaimSource(**s)
                if isinstance(s, dict)
                else ClaimSource(kind="other", ref=str(s))
                for s in sources_raw
            ]
            claims.append(
                Claim(
                    id=UUID(r["id"]),
                    entity_id=UUID(r["entity_id"]) if r.get("entity_id") else None,
                    edge_id=UUID(r["edge_id"]) if r.get("edge_id") else None,
                    agent_id=r["agent_id"],
                    claim_type=r["claim_type"],
                    domain=r["domain"],
                    finding_text=r["finding_text"],
                    confidence=float(r["confidence"]),
                    sources=sources,
                    contradicts=[UUID(c) for c in (r.get("contradicts") or [])],
                    freshness_at=datetime.fromisoformat(
                        r["freshness_at"].replace("Z", "+00:00")
                    )
                    if isinstance(r["freshness_at"], str)
                    else r["freshness_at"],
                    expires_at=datetime.fromisoformat(
                        r["expires_at"].replace("Z", "+00:00")
                    )
                    if r.get("expires_at") and isinstance(r["expires_at"], str)
                    else r.get("expires_at"),
                    created_at=datetime.fromisoformat(
                        r["created_at"].replace("Z", "+00:00")
                    )
                    if isinstance(r["created_at"], str)
                    else r["created_at"],
                )
            )
        return claims
    except Exception as e:
        logger.warning("find_claims failed: %s", e)
        return []


async def _semantic_query_rows(
    *,
    embedding: list[float],
    agent_id: str | None,
    claim_type: str | None,
    top_k: int,
) -> list[dict]:
    """Execute a pgvector cosine-distance query and return raw row dicts.

    Uses psycopg directly for the parametrised ``<=>`` operator which the
    Supabase PostgREST client cannot express. The ``similarity`` key in each
    returned dict is the cosine *distance* (0 = identical, 2 = opposite) —
    lower values indicate higher semantic similarity.

    Args:
        embedding: Query embedding vector (must match column dimension, 768).
        agent_id: Optional agent filter. None means all agents.
        claim_type: Optional claim_type filter. None means all types.
        top_k: Maximum rows returned.

    Returns:
        List of row dicts with all kg_findings columns plus ``similarity``
        (cosine distance float). Returns [] on any DB error.
    """
    import asyncio
    import os

    try:
        import psycopg
    except ImportError:
        logger.warning(
            "_semantic_query_rows: psycopg not installed; returning empty results"
        )
        return []

    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        logger.warning(
            "_semantic_query_rows: SUPABASE_DB_URL not set; returning empty results"
        )
        return []

    # Use %s-style parameters (psycopg default) to avoid double-counting of
    # positional placeholders ($N syntax counts each occurrence separately).
    # embedding appears twice: once in SELECT, once in ORDER BY — pass it twice.
    filters: list[str] = []
    params: list = [embedding, embedding]  # for SELECT + ORDER BY
    if agent_id is not None:
        filters.append("agent_id = %s")
        params.append(agent_id)
    if claim_type is not None:
        filters.append("claim_type = %s")
        params.append(claim_type)
    params.append(top_k)  # for LIMIT

    where_sql = ""
    if filters:
        where_sql = "WHERE " + " AND ".join(filters)

    sql = f"""
        SELECT
            id, entity_id, edge_id, agent_id, claim_type, domain,
            finding_text, confidence, sources, contradicts,
            freshness_at, expires_at, created_at,
            (embedding <=> %s::vector) AS similarity
        FROM kg_findings
        {where_sql}
        ORDER BY embedding <=> %s::vector ASC
        LIMIT %s
    """

    def _run() -> list[dict]:
        """Sync psycopg call, run via executor to stay async-safe."""
        with psycopg.connect(db_url) as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    try:
        loop = asyncio.get_event_loop()
        rows: list[dict] = await loop.run_in_executor(None, _run)
        return rows
    except Exception as e:
        logger.warning("_semantic_query_rows DB query failed: %s", e)
        return []


async def search_claims_semantic(
    *,
    query: str,
    agent_id: str | None = None,
    claim_type: str | None = None,
    top_k: int = 10,
) -> list[tuple[Claim, float]]:
    """Search kg_findings by semantic similarity using pgvector cosine distance.

    Embeds *query* via Vertex AI, then executes an ``ORDER BY embedding <=> $1``
    query against kg_findings. Results are returned sorted ascending by cosine
    distance (most similar first).

    Degrades silently: returns [] when the embedding service is unavailable or
    the DB query fails — callers treat an empty result as a cache miss, not an
    error.

    Args:
        query: Natural-language search string.
        agent_id: Optional — restrict to a specific agent.
        claim_type: Optional — restrict to a single claim_type.
        top_k: Max results returned. Default 10; capped at 100.

    Returns:
        List of ``(Claim, similarity_float)`` tuples sorted by ascending cosine
        distance (0 = identical, 2 = opposite).
    """
    from app.services.intelligence.schemas import Claim, ClaimSource

    top_k = min(top_k, 100)

    embedding = await _embed_text(query)
    if embedding is None:
        logger.warning(
            "search_claims_semantic: embedding failed for query %r — returning []",
            query[:80],
        )
        return []

    rows = await _semantic_query_rows(
        embedding=embedding,
        agent_id=agent_id,
        claim_type=claim_type,
        top_k=top_k,
    )

    results: list[tuple[Claim, float]] = []
    for r in rows:
        try:
            sources_raw = r.get("sources") or []
            sources = [
                ClaimSource(**s)
                if isinstance(s, dict)
                else ClaimSource(kind="other", ref=str(s))
                for s in sources_raw
            ]

            def _parse_dt(val):
                if val is None:
                    return None
                if isinstance(val, str):
                    return datetime.fromisoformat(val.replace("Z", "+00:00"))
                return val

            claim = Claim(
                id=UUID(r["id"]) if isinstance(r["id"], str) else r["id"],
                entity_id=(
                    UUID(r["entity_id"])
                    if r.get("entity_id") and isinstance(r["entity_id"], str)
                    else r.get("entity_id")
                ),
                edge_id=(
                    UUID(r["edge_id"])
                    if r.get("edge_id") and isinstance(r["edge_id"], str)
                    else r.get("edge_id")
                ),
                agent_id=r["agent_id"],
                claim_type=r["claim_type"],
                domain=r["domain"],
                finding_text=r["finding_text"],
                confidence=float(r["confidence"]),
                sources=sources,
                contradicts=[
                    UUID(c) if isinstance(c, str) else c
                    for c in (r.get("contradicts") or [])
                ],
                freshness_at=_parse_dt(r["freshness_at"]),
                expires_at=_parse_dt(r.get("expires_at")),
                created_at=_parse_dt(r["created_at"]),
            )
            similarity = float(r["similarity"])
            results.append((claim, similarity))
        except Exception as e:
            logger.warning("search_claims_semantic: failed to parse row: %s", e)
            continue

    return results


async def claim_freshness_hours(
    *,
    entity_id: UUID,
    claim_type: str | None = None,
    agent_id: str | None = None,
) -> float | None:
    """Age in hours of the most recent matching claim, or None if no match.

    Used by cache.should_query_graph to decide whether to skip a fetch.

    Args:
        entity_id: The entity to query.
        claim_type: Optional claim type filter.
        agent_id: Optional agent filter.

    Returns:
        Float hours since the most recent matching claim's freshness_at, or
        None if no matching claim exists. Returns None (not raises) on DB error.
    """
    from datetime import timezone

    try:
        client = _get_supabase_client()
        q = (
            client.table("kg_findings")
            .select("freshness_at")
            .eq("entity_id", str(entity_id))
        )
        if claim_type is not None:
            q = q.eq("claim_type", claim_type)
        if agent_id is not None:
            q = q.eq("agent_id", agent_id)
        q = q.order("freshness_at", desc=True).limit(1)
        result = q.execute()
        if not result.data:
            return None

        freshness_at_raw = result.data[0]["freshness_at"]
        if isinstance(freshness_at_raw, str):
            freshness_at = datetime.fromisoformat(
                freshness_at_raw.replace("Z", "+00:00")
            )
        else:
            freshness_at = freshness_at_raw
        now = datetime.now(timezone.utc)
        delta = now - freshness_at
        return delta.total_seconds() / 3600.0
    except Exception as e:
        logger.warning("claim_freshness_hours failed: %s", e)
        return None
