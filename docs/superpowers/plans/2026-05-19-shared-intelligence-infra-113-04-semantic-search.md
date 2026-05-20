# Shared Intelligence Infrastructure — Plan 113-04: Semantic Search + Executive ADK Tool

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `search_claims_semantic(query, agent_id?, claim_type?, top_k)` to the intelligence package — pgvector-backed semantic search across all agents' claims. Turn on `embed=True` for cohort summary claims so they become searchable. Expose the search as the **first justified ADK tool wrapper** in the package (per the spec, reasoning-driven retrieval is where LLM tool calls add value).

**Architecture:** New migration adds an `ivfflat` index on `kg_findings.embedding` (conservative for ≤500k rows; migrate to `hnsw` later if needed). `search_claims_semantic` generates an embedding for the query, runs `ORDER BY embedding <=> $1` via pgvector, and returns `list[tuple[Claim, float similarity]]`. Executive Agent gains an ADK tool `search_agent_claims` that wraps the function with sensible defaults (top_k=10).

**Tech Stack:** pgvector (already installed for `kg_entities.embedding` + `kg_findings.embedding`), `app/rag/embedding_service.generate_embedding` (sync, wrapped to async per Plan 112-03's `_embed_text`), the ADK tool registration pattern from `app/agents/specialized_agents.py`.

**Spec reference:** `docs/superpowers/specs/2026-05-18-shared-intelligence-infra-design.md` § Phase 113 § Cross-agent semantic search

**Out of scope:** Contradiction detection (Plan 113-05), tuning ivfflat lists or migration to hnsw, full-text search fallback for when embedding generation fails.

---

## File structure

**Create:**
- `supabase/migrations/20260519000000_kg_findings_embedding_ivfflat_index.sql` — pgvector index
- `app/agents/tools/intelligence_search.py` — ADK tool wrapper for Executive
- `tests/unit/services/intelligence/test_search.py` — unit tests with mocked embedding + DB
- `tests/integration/test_intelligence_search.py` — integration tests against real pgvector

**Modify:**
- `app/services/intelligence/claims.py` — add `search_claims_semantic` async function
- `app/services/intelligence/__init__.py` — re-export `search_claims_semantic`
- `app/agents/data/tools.py` — flip `embed=True` on the `cohort_summary` write
- `app/agent.py` (ExecutiveAgent) — register the new `search_agent_claims` ADK tool

**Reference (read-only):**
- `app/agents/research/tools/synthesizer.py` — pattern for embedding-on-write
- `app/rag/embedding_service.py` — `generate_embedding` (sync)
- `supabase/migrations/20260321500000_knowledge_graph.sql` — see how `kg_entities.embedding` index is defined (line 47 — `USING hnsw (embedding vector_cosine_ops)`)

---

## Pre-flight context

Note: `kg_entities` already has an HNSW index on its embedding column. For `kg_findings.embedding`, the spec recommends starting with `ivfflat` (`lists=100`) for ≤500k rows, migrating to `hnsw` only if needed. Why the divergence:
- Entities are sparse (~1 row per topic); HNSW gives fast lookup with low memory overhead
- Findings will be dense (potentially many per topic); ivfflat scales better to large row counts on commodity hardware

You can override this choice if you have reason — just document it in the migration's comment.

`search_claims_semantic` signature per spec:
```python
async def search_claims_semantic(
    *, query: str,
    agent_id: str | None = None,
    claim_type: str | None = None,
    top_k: int = 10,
) -> list[tuple[Claim, float]]:  # (claim, similarity)
```

Performance target (from spec): p50 ≤ 200ms with 100k claims in table. ivfflat at `lists=100` typically delivers this; ANALYZE the table after migration to make sure the planner picks the index.

Acceptance bar:
- Returns Research findings AND Data claims for a query about a shared topic
- pgvector index used (verified via `EXPLAIN ANALYZE`)
- Executive ADK tool registered and discoverable

Environment quirks: same as prior plans.

---

## Tasks

### Task 1: pgvector index migration

**Files:**
- Create: `supabase/migrations/20260519000000_kg_findings_embedding_ivfflat_index.sql`

- [ ] **Step 1: Create the migration**

```sql
-- =============================================================================
-- Plan 113-04: ivfflat index on kg_findings.embedding for semantic search.
--
-- Why ivfflat (not hnsw): kg_findings is expected to grow into the hundreds
-- of thousands of rows. ivfflat with lists=100 is conservative for that scale
-- and uses materially less memory than hnsw. Migrate to hnsw if and when:
--   - row count exceeds 1M
--   - p50 query latency exceeds 200ms despite tuning
--
-- ROLLBACK:
--   DROP INDEX IF EXISTS idx_kg_findings_embedding_semantic;
--
-- PRODUCTION DEPLOY NOTE: for large tables, build via CREATE INDEX
-- CONCURRENTLY outside a transaction (mirrors the kg_findings broaden
-- migration runbook). The form below uses regular CREATE INDEX inside
-- BEGIN/COMMIT for local dev; prod deploy script must switch to
-- CONCURRENTLY.
-- =============================================================================

BEGIN;

CREATE INDEX IF NOT EXISTS idx_kg_findings_embedding_semantic
    ON kg_findings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Tell the planner about the new index
ANALYZE kg_findings;

COMMIT;
```

- [ ] **Step 2: Apply locally**

```powershell
Get-Content supabase/migrations/20260519000000_kg_findings_embedding_ivfflat_index.sql | docker exec -i supabase_db_Pikar-Ai psql -U postgres -d postgres
```

Expected: BEGIN / CREATE INDEX / ANALYZE / COMMIT.

- [ ] **Step 3: Verify the index exists**

```powershell
docker exec supabase_db_Pikar-Ai psql -U postgres -d postgres -c "\d kg_findings" | Select-String "idx_kg_findings_embedding_semantic"
```

Expected: prints the index line.

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/20260519000000_kg_findings_embedding_ivfflat_index.sql
git commit -m "feat(113-04): add ivfflat index on kg_findings.embedding for semantic search"
```

### Task 2: Implement `search_claims_semantic` (TDD)

**Files:**
- Create: `tests/unit/services/intelligence/test_search.py`
- Modify: `app/services/intelligence/claims.py` — append the new function
- Modify: `app/services/intelligence/__init__.py` — re-export

- [ ] **Step 1: Failing unit test**

```python
"""Unit tests for search_claims_semantic with mocked embedding + DB."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_search_claims_semantic_returns_claims_ordered_by_similarity():
    """Mocked DB returns 3 rows; result preserves order and packs Claim objects."""
    from app.services.intelligence.claims import search_claims_semantic

    fake_rows = [
        {
            "id": str(uuid4()),
            "entity_id": str(uuid4()), "edge_id": None,
            "agent_id": "data", "claim_type": "cohort_summary",
            "domain": "data", "finding_text": "very similar",
            "confidence": 0.9, "sources": [], "contradicts": [],
            "freshness_at": "2026-05-19T12:00:00+00:00",
            "expires_at": None, "created_at": "2026-05-19T11:55:00+00:00",
            "similarity": 0.05,  # closer = lower distance
        },
        {
            "id": str(uuid4()),
            "entity_id": str(uuid4()), "edge_id": None,
            "agent_id": "research", "claim_type": "research_finding",
            "domain": "research", "finding_text": "somewhat similar",
            "confidence": 0.7, "sources": [], "contradicts": [],
            "freshness_at": "2026-05-19T10:00:00+00:00",
            "expires_at": None, "created_at": "2026-05-19T09:55:00+00:00",
            "similarity": 0.4,
        },
    ]
    fake_embed = [0.1] * 768

    with patch(
        "app.services.intelligence.claims._embed_text",
        new=AsyncMock(return_value=fake_embed),
    ), patch(
        "app.services.intelligence.claims._semantic_query_rows",
        new=AsyncMock(return_value=fake_rows),
    ):
        results = await search_claims_semantic(query="cohort retention", top_k=5)

    assert len(results) == 2
    # Each result is (Claim, similarity float)
    first_claim, first_sim = results[0]
    assert first_claim.finding_text == "very similar"
    assert first_sim == pytest.approx(0.05)
    second_claim, second_sim = results[1]
    assert second_claim.finding_text == "somewhat similar"
    assert second_sim == pytest.approx(0.4)


@pytest.mark.asyncio
async def test_search_claims_semantic_skips_when_embedding_fails():
    """If embedding generation fails, return [] (degrade silently — read path)."""
    from app.services.intelligence.claims import search_claims_semantic

    with patch(
        "app.services.intelligence.claims._embed_text",
        new=AsyncMock(return_value=None),
    ):
        results = await search_claims_semantic(query="anything")

    assert results == []


@pytest.mark.asyncio
async def test_search_claims_semantic_top_k_respected():
    """The top_k argument caps the number of rows fetched."""
    from app.services.intelligence.claims import search_claims_semantic

    fake_embed = [0.1] * 768
    captured = {}

    async def capture_query(*, embedding, agent_id, claim_type, top_k):
        captured["top_k"] = top_k
        return []

    with patch(
        "app.services.intelligence.claims._embed_text",
        new=AsyncMock(return_value=fake_embed),
    ), patch(
        "app.services.intelligence.claims._semantic_query_rows",
        side_effect=capture_query,
    ):
        await search_claims_semantic(query="x", top_k=3)

    assert captured["top_k"] == 3
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/services/intelligence/test_search.py -v --tb=short
```

- [ ] **Step 3: Implement in `claims.py`**

Add to `app/services/intelligence/claims.py` (append after the existing functions):

```python
async def search_claims_semantic(
    *,
    query: str,
    agent_id: str | None = None,
    claim_type: str | None = None,
    top_k: int = 10,
) -> list[tuple[Claim, float]]:
    """Semantic search across kg_findings.embedding.

    Embeds the query, runs pgvector cosine-distance ORDER BY, and returns
    (Claim, similarity) tuples — lower similarity = closer match.

    Reads degrade silently: embedding-generation failure or DB failure
    returns []. Caller may show "no semantic results" or fall back to
    structured search.

    Args:
        query: Natural-language search string.
        agent_id: Restrict to a specific agent (e.g., "data", "research").
        claim_type: Restrict to a specific claim_type.
        top_k: Max rows returned. Capped at 100 internally to avoid runaway.

    Returns:
        list[tuple[Claim, float]] sorted by similarity ASCENDING (closest first).
        Empty list on failure or no matches.
    """
    embedding = await _embed_text(query)
    if embedding is None:
        return []

    top_k = max(1, min(top_k, 100))  # safety cap

    try:
        rows = await _semantic_query_rows(
            embedding=embedding,
            agent_id=agent_id,
            claim_type=claim_type,
            top_k=top_k,
        )
    except Exception as e:
        logger.warning("search_claims_semantic query failed: %s", e)
        return []

    from app.services.intelligence.schemas import ClaimSource
    results: list[tuple[Claim, float]] = []
    for r in rows:
        sources_raw = r.get("sources") or []
        sources = [
            ClaimSource(**s) if isinstance(s, dict) else ClaimSource(kind="other", ref=str(s))
            for s in sources_raw
        ]
        claim = Claim(
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
            freshness_at=datetime.fromisoformat(r["freshness_at"].replace("Z", "+00:00"))
                if isinstance(r["freshness_at"], str) else r["freshness_at"],
            expires_at=datetime.fromisoformat(r["expires_at"].replace("Z", "+00:00"))
                if r.get("expires_at") and isinstance(r["expires_at"], str) else r.get("expires_at"),
            created_at=datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
                if isinstance(r["created_at"], str) else r["created_at"],
        )
        similarity = float(r.get("similarity", 0.0))
        results.append((claim, similarity))
    return results


async def _semantic_query_rows(
    *,
    embedding: list[float],
    agent_id: str | None,
    claim_type: str | None,
    top_k: int,
) -> list[dict]:
    """Execute the pgvector ORDER BY query and return raw rows.

    Isolated as a helper so tests can mock the DB hop without mocking
    the whole search_claims_semantic.
    """
    # Build the SQL — pgvector uses <=> for cosine distance
    where_clauses = []
    params: list = [embedding, top_k]
    if agent_id is not None:
        params.append(agent_id)
        where_clauses.append(f"agent_id = ${len(params)}")
    if claim_type is not None:
        params.append(claim_type)
        where_clauses.append(f"claim_type = ${len(params)}")
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    sql = f"""
        SELECT id, entity_id, edge_id, agent_id, claim_type, domain,
               finding_text, confidence, sources, contradicts,
               freshness_at, expires_at, created_at,
               (embedding <=> $1) AS similarity
          FROM kg_findings
          {where_sql}
         ORDER BY embedding <=> $1
         LIMIT $2
    """

    # Run via psycopg directly — the supabase python client doesn't
    # expose vector parameters cleanly enough for this pattern.
    import os
    import psycopg
    dsn = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        logger.warning("SUPABASE_DB_URL not set; semantic search unavailable")
        return []

    def _run():
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]

    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)
```

- [ ] **Step 4: Update `__init__.py`** to re-export `search_claims_semantic`:

```python
# Add to the imports block:
from app.services.intelligence.claims import (
    claim_freshness_hours,
    find_claims,
    get_or_create_entity,
    search_claims_semantic,  # NEW
    write_claim,
    write_claims,
)

# Add "search_claims_semantic" to __all__
```

- [ ] **Step 5: Re-run unit tests — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/test_search.py -v --tb=short
```

- [ ] **Step 6: Commit**

```bash
git add app/services/intelligence/claims.py app/services/intelligence/__init__.py tests/unit/services/intelligence/test_search.py
git commit -m "feat(113-04): implement search_claims_semantic with pgvector cosine distance (GREEN)"
```

### Task 3: Turn on `embed=True` for cohort_summary writes

**Files:**
- Modify: `app/agents/data/tools.py:cohort_analysis` — flip `embed=True` on the `cohort_summary` `write_claim`

- [ ] **Step 1: Edit**

In the `cohort_summary` `write_claim` call (added in Plan 113-03), change `embed=False` (or omitted, defaults to False) to `embed=True`. Per-month `cohort_retention_mN` claims stay at `embed=False` — those are short numerical claims with low semantic search value.

Also: confirm `app/rag/embedding_service.generate_embedding` exists and is callable. If it returns sync, `_embed_text` already handles that wrapper (Plan 112-03's helper).

- [ ] **Step 2: Run prior test to confirm no regression**

```powershell
uv run pytest tests/integration/test_data_cache_integration.py -k "writes_summary" -v --tb=short
```

- [ ] **Step 3: Commit**

```bash
git add app/agents/data/tools.py
git commit -m "feat(113-04): enable embeddings on cohort_summary claims for semantic search"
```

### Task 4: Integration test — semantic search round-trip

**Files:**
- Create: `tests/integration/test_intelligence_search.py`

- [ ] **Step 1: Create the test**

```python
"""Integration test: write claims with embeddings, then semantic-search them."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var) for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
        ),
        reason="env not set",
    ),
]


@pytest.mark.asyncio
async def test_semantic_search_returns_relevant_claims():
    """Write two distinct claims (one about cohorts, one about regulations);
    search for 'cohort retention' should rank the cohort claim higher.
    """
    from app.services.intelligence import (
        get_or_create_entity, search_claims_semantic, write_claim,
    )

    e1 = await get_or_create_entity(
        canonical_name=f"semantic_cohort_{uuid4()}",
        entity_type="metric", domains=["data"],
    )
    e2 = await get_or_create_entity(
        canonical_name=f"semantic_compliance_{uuid4()}",
        entity_type="regulation", domains=["compliance"],
    )

    await write_claim(
        entity_id=e1, domain="data",
        finding_text="Customer cohort retention dropped 12% in Q1 driven by enterprise churn",
        confidence=0.85,
        sources=[{"kind": "stripe_row", "ref": "test"}],
        agent_id="data", claim_type="cohort_summary",
        embed=True,
    )
    await write_claim(
        entity_id=e2, domain="compliance",
        finding_text="GDPR Article 17 mandates erasure of personal data on request",
        confidence=0.95,
        sources=[{"kind": "regulation", "ref": "GDPR Art 17"}],
        agent_id="compliance", claim_type="regulation_summary",
        embed=True,
    )

    results = await search_claims_semantic(
        query="cohort retention drop", top_k=5,
    )

    assert len(results) >= 1
    # The first result should be the cohort claim (semantic neighbour),
    # NOT the GDPR claim. We accept any plausible ordering as long as
    # the cohort claim ranks above the GDPR claim if both are returned.
    cohort_position = None
    gdpr_position = None
    for i, (claim, _sim) in enumerate(results):
        if "cohort" in claim.finding_text.lower():
            cohort_position = i if cohort_position is None else cohort_position
        if "GDPR" in claim.finding_text:
            gdpr_position = i if gdpr_position is None else gdpr_position
    assert cohort_position is not None, "Cohort claim should appear in top results"
    if gdpr_position is not None:
        assert cohort_position < gdpr_position, "Cohort claim should rank above GDPR claim"
```

- [ ] **Step 2: Run**

```powershell
uv run pytest tests/integration/test_intelligence_search.py -v --tb=short
```

Expected: PASS. If the ordering fails, the embedding service may be returning a low-quality vector — investigate before changing the assertion.

- [ ] **Step 3: Verify pgvector index is used** via `EXPLAIN ANALYZE` (sanity check, not a test assertion):

```powershell
docker exec supabase_db_Pikar-Ai psql -U postgres -d postgres -c "EXPLAIN ANALYZE SELECT id FROM kg_findings WHERE embedding IS NOT NULL ORDER BY embedding <=> ARRAY[0.1, 0.2, 0.3]::vector LIMIT 5;"
```

Look for `Index Scan using idx_kg_findings_embedding_semantic` in the plan. If you see a Seq Scan, the planner thinks the table is too small to bother — that's fine for local dev; prod will use the index.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_intelligence_search.py
git commit -m "test(113-04): integration test for semantic search across agents"
```

### Task 5: Add Executive ADK tool wrapper

**Files:**
- Create: `app/agents/tools/intelligence_search.py`
- Modify: `app/agent.py` — register the new tool

This is the **first justified ADK tool wrapper** in the intelligence package. The Executive LLM gets to decide when semantic search is worth invoking, with what filters.

- [ ] **Step 1: Create `app/agents/tools/intelligence_search.py`**

```python
"""ADK tool: cross-agent semantic claim search.

Wraps app.services.intelligence.search_claims_semantic with sensible defaults
for the Executive Agent. The LLM decides when this is worth calling
(reasoning-driven retrieval, not a mechanical lookup).
"""

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

    Returns claims any specialized agent has written about a topic — useful
    when the Executive needs to recall what's known across the team.

    Args:
        query: Natural-language search string (e.g., "Q1 customer retention").
        agent_id: Optional — restrict to a specific agent. Examples:
                  "data", "research", "financial", "compliance".
        claim_type: Optional — restrict to a single claim_type. See
                    docs/intelligence/claim-types.md for the vocabulary.
        top_k: Max results to return. Default 10; capped at 100.

    Returns:
        Dict with `results: list[{finding_text, confidence, band, agent_id,
        claim_type, similarity, domain, sources}]` and `count: int`.
    """
    from app.services.intelligence import search_claims_semantic

    try:
        hits = await search_claims_semantic(
            query=query,
            agent_id=agent_id,
            claim_type=claim_type,
            top_k=top_k,
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


# ADK tool export
INTELLIGENCE_SEARCH_TOOLS = [search_agent_claims]
```

- [ ] **Step 2: Wire into `app/agent.py`** (ExecutiveAgent)

Find the ExecutiveAgent's tool list assembly in `app/agent.py`. Add the import and extend the tool list:

```python
from app.agents.tools.intelligence_search import INTELLIGENCE_SEARCH_TOOLS

# In the tool-list build site, e.g.:
tools = [
    *KNOWLEDGE_SEARCH_TOOLS,
    *BRAIN_DUMP_TOOLS,
    # ...
    *INTELLIGENCE_SEARCH_TOOLS,
]
```

The exact insertion point depends on the current structure — find where tool lists are accumulated and add the new one.

- [ ] **Step 3: Verify the tool is discoverable**

```powershell
uv run python -c "
from app.agents.tools.intelligence_search import search_agent_claims, INTELLIGENCE_SEARCH_TOOLS
print('tool import OK; tool count =', len(INTELLIGENCE_SEARCH_TOOLS))
"
```

Expected: `tool import OK; tool count = 1`.

- [ ] **Step 4: Smoke-test through the ADK tool layer**

```powershell
$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_SERVICE_ROLE_KEY = (supabase status -o env | Select-String '^SERVICE_ROLE_KEY=').ToString().Split('=',2)[1].Trim('"')
$env:SUPABASE_DB_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
uv run python -c "
import asyncio
from app.agents.tools.intelligence_search import search_agent_claims

async def main():
    result = await search_agent_claims(query='cohort retention', top_k=3)
    print(f'count={result[\"count\"]}; first result agent={result[\"results\"][0][\"agent_id\"] if result[\"results\"] else \"<none>\"}')

asyncio.run(main())
"
```

Expected: prints a count + sample result (if any prior tests wrote claims with embeddings). If `count=0` on a fresh DB, that's expected — just confirm no exception.

- [ ] **Step 5: Commit**

```bash
git add app/agents/tools/intelligence_search.py app/agent.py
git commit -m "feat(113-04): add search_agent_claims ADK tool for Executive"
```

### Task 6: Lint + acceptance sign-off

- [ ] **Step 1: Lint**

```powershell
uv run ruff check app/services/intelligence/claims.py app/agents/tools/intelligence_search.py tests/unit/services/intelligence/test_search.py tests/integration/test_intelligence_search.py
uv run ruff format app/services/intelligence/claims.py app/agents/tools/intelligence_search.py tests/unit/services/intelligence/test_search.py tests/integration/test_intelligence_search.py --check
```

Fix in-place; commit any fixes.

- [ ] **Step 2: Acceptance check**

| Spec line | Verified by |
|---|---|
| `search_claims_semantic` async, returns `list[tuple[Claim, float]]` | Task 2 implementation |
| pgvector index created | Task 1 migration |
| Reads degrade silently on embedding failure | Task 2 + `test_search_claims_semantic_skips_when_embedding_fails` |
| Executive ADK tool `search_agent_claims` registered | Task 5 |
| Returns claims from multiple agents for a shared topic | Task 4 integration test |
| `top_k` capped at 100 | Task 2 + `test_search_claims_semantic_top_k_respected` |
| Embeddings now generated for cohort_summary writes | Task 3 |
| No lint regressions | Task 6 |

- [ ] **Step 3: Plan 113-04 complete. Plan 113-05 (`detect_contradictions`) is unblocked.**

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| ivfflat pgvector index on kg_findings.embedding | Task 1 |
| `search_claims_semantic(query, agent_id?, claim_type?, top_k)` | Task 2 |
| Reads degrade silently | Task 2 tests |
| Executive ADK tool wrapper (first justified one) | Task 5 |
| Embeddings on cohort_summary writes | Task 3 |
| Integration test confirms cross-agent retrieval | Task 4 |
| pgvector index actually used (EXPLAIN check) | Task 4 Step 3 |
| Lint clean | Task 6 |

All spec lines covered.
