# Shared Intelligence Infrastructure — Design

**Date:** 2026-05-18
**Status:** Draft for review
**Phases:** 112 (modules + Research migration), 113 (Data Agent adoption)
**Owner:** TBD

## Summary

Lift three pieces from the Research Agent into shared modules every specialized agent can use:

1. **Confidence scoring** — generic weighted scorer + per-agent presets + band classifier
2. **Knowledge-graph claims** — broaden `kg_findings` to accept any agent's claims, expose unified write/read API
3. **Two-tier adaptive cache** — graph for semantic claims, Redis for raw external calls

Pilot with the Data Agent after Research is migrated. Other 8 specialized agents adopt in later phases.

## Motivation

Today only the Research Agent has a quantitative trust signal (`calculate_confidence` in `app/agents/research/tools/synthesizer.py:120-151`). Every other agent emits confident-sounding text with no calibration. The Research Agent also has a cache-first discipline (`adaptive_router.py:54-121`) — every other agent re-fetches every time.

The Research Agent's pipeline is well-factored: each step passes plain dicts and is reusable. Three pieces are universally valuable; the rest (multi-track decomposition, Tavily/Firecrawl) is research-specific and stays put.

## Decisions

These were settled during brainstorming. Each is non-trivial.

| # | Decision | Alternative considered | Why |
|---|---|---|---|
| 1 | Lift confidence + graph + adaptive cache, **equal weight** | Single primary driver | All three reinforce each other; unbalancing means partial value. |
| 2 | **Generic scorer + named presets** for confidence | Generic-only / presets-only / band-only | Best balance: primitive for advanced callers, presets for fast adoption. |
| 3 | **Broaden `kg_findings`** (add `agent_id`, `claim_type`) | New table / unified `claims` table / federated view | Schema is already 90% domain-agnostic; one query surface; no migration of existing data. |
| 4 | **Pilot with Data Agent only**, then expand | Big-bang / infra-only / 3-agent pilot | Tightest provable scope; validates abstraction with one new consumer. |
| 5 | **Two-tier cache substrate** (graph for claims, Redis for raw) | Graph-as-cache / Redis-as-cache | Asymmetric TTLs match reality — claims live for hours/days, raw calls for minutes. |
| 6 | **Two phases** (112: infra + research migration; 113: data adoption) | Single phase / three phases | Each phase shippable in isolation; Phase 112's success criterion is binary. |
| 7 | **Library-first**, no new ADK tools in Phase 112 | Tool-first / hybrid | Confidence/cache decisions are mechanical; tool calls waste LLM turns. |
| 8 | **Aggressive cleanup** — delete old `calculate_confidence` after migration | Alias old name to new | CLAUDE.md rules out back-compat shims; Research is internal. |
| 9 | **Surface errors on writes, return defaults on reads** | Swallow all (current research pattern) | Reads degrade silently; writes fail loudly. Lost claims corrupt cross-agent model. |
| 10 | **`record_claim` ADK tool deferred** | Ship with Phase 112 | Add only when LLM-driven claim emission becomes a real need. |
| 11 | **Executive `search_claims_semantic` ADK tool justified for Phase 113** | Library-only across all phases | Reasoning-driven retrieval *does* benefit from LLM deciding when to search. |

## Architecture

### Package layout

```
app/services/intelligence/
├── __init__.py          # public re-exports
├── confidence.py        # generic scorer + band classifier
├── claims.py            # kg_findings write/read API
├── cache.py             # two-tier adaptive cache
├── schemas.py           # Pydantic models
└── presets/
    ├── __init__.py
    ├── research.py      # lifted from synthesizer.py
    └── data.py          # new: sample/missing/sigma/recency
```

Rationale: existing `app/services/graph_service.py` is read-only; mixing in writes/compute would push it past comprehensible size. Leave it as the read API. New package contains writes, compute, and cache. Consolidation is a separate later cleanup.

### Public surface

```python
from app.services.intelligence import (
    # confidence
    score_confidence,           # generic weighted scorer
    to_band,                    # float -> Literal["low", "medium", "high"]
    presets,                    # presets.research_confidence, presets.data_confidence
    # claims
    write_claim,                # async, single insert into kg_findings
    write_claims,               # async, bulk insert
    find_claims,                # async, structured filter
    claim_freshness_hours,      # async, age of latest matching claim
    get_or_create_entity,       # async, upsert on (canonical_name, entity_type)
    # cache
    should_query_graph,         # CacheDecision for claims tier
    should_call_external,       # CacheDecision for Redis tier
    # schemas
    Claim,                      # Pydantic output shape; .band is computed property
    ClaimPayload,               # Pydantic input shape for write_claim / write_claims
    ClaimSource,
    ConfidenceBand,
    CacheDecision,
)
```

Phase 113 adds: `search_claims_semantic`, `detect_contradictions`.

## Module specifications

### `confidence.py`

```python
def score_confidence(
    inputs: Mapping[str, float],
    weights: Mapping[str, float],
) -> float:
    """Generic weighted confidence scorer.

    Validates key match and weights sum <= 1.0. Returns clamped [0.0, 1.0].
    Raises ValueError on key mismatch or weights overshoot.
    """

def to_band(
    score: float,
    *,
    low_threshold: float = 0.50,
    high_threshold: float = 0.75,
) -> ConfidenceBand:
    """Classify score into Literal["low", "medium", "high"].

    Thresholds default to Research Agent's existing 0.50 / 0.75 convention.
    Configurable so callers can tune per use case.
    """
```

### `presets/research.py`

```python
RESEARCH_WEIGHTS = {
    "track_agreement": 0.35,
    "source_quality": 0.30,
    "freshness": 0.20,
    "contradiction_adjusted": 0.15,
}

def research_confidence(
    track_agreement: float,
    source_quality: float,
    freshness: float,
    contradictions_found: int,
) -> float:
    """Bit-identical replacement for synthesizer.py:120-151 calculate_confidence."""
    contradiction_penalty = min(1.0, contradictions_found * 0.05)
    return score_confidence(
        inputs={
            "track_agreement": track_agreement,
            "source_quality": source_quality,
            "freshness": freshness,
            "contradiction_adjusted": 1.0 - contradiction_penalty,
        },
        weights=RESEARCH_WEIGHTS,
    )
```

### `presets/data.py`

```python
DATA_WEIGHTS = {
    "sample_adequacy": 0.35,
    "completeness": 0.25,
    "statistical_strength": 0.25,
    "recency": 0.15,
}

def data_confidence(
    sample_size: int,
    missing_pct: float,
    sigma_distance: float,
    data_age_hours: float,
    *,
    sample_threshold: int = 100,
    recency_horizon_hours: float = 720,  # 30 days
) -> float:
    """Internal-data confidence for analytics aggregations.

    Reflects statistical rigor from Data Agent instructions
    (agent.py:166-176): sample_size >= 30 for trends, >= 100 for anomalies;
    missing >20% flagged; outliers >3 sigma.

    statistical_strength inverts sigma — high sigma means *anomalous*,
    not *certain*. Anomaly may have high signal but low confidence in
    trend stability.
    """
    sample_adequacy = min(1.0, sample_size / sample_threshold)
    completeness = max(0.0, 1.0 - missing_pct)
    statistical_strength = max(0.0, 1.0 - min(1.0, sigma_distance / 3.0))
    recency = max(0.0, 1.0 - min(1.0, data_age_hours / recency_horizon_hours))

    return score_confidence(
        inputs={
            "sample_adequacy": sample_adequacy,
            "completeness": completeness,
            "statistical_strength": statistical_strength,
            "recency": recency,
        },
        weights=DATA_WEIGHTS,
    )
```

Initial weights are educated guesses. Phase 114+ may calibrate against labeled data.

### `claims.py`

```python
async def write_claim(
    *,
    entity_id: UUID | None,
    edge_id: UUID | None = None,
    domain: str,
    finding_text: str,                # kept as finding_text to match DB column
    confidence: float,
    sources: Sequence[ClaimSource],
    agent_id: str,
    claim_type: str,
    embed: bool = False,              # explicit opt-in, no magic
    expires_at: datetime | None = None,
    contradicts: Sequence[UUID] = (),
) -> UUID:
    """Single insert into kg_findings. Raises on failure.

    embed=True triggers Vertex AI embedding generation before insert
    (cost-aware; caller decides). Embedding failure inserts row with
    NULL embedding and logs warning.
    """

async def write_claims(claims: Sequence[ClaimPayload]) -> list[UUID]:
    """Bulk insert. One INSERT statement. Raises on partial failure."""

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
    """Structured filter query. All filters AND'd."""

async def claim_freshness_hours(
    *,
    entity_id: UUID,
    claim_type: str | None = None,
    agent_id: str | None = None,
) -> float | None:
    """Age of the most recent matching claim. None on no match.

    Used internally by cache.should_query_graph.
    """

async def get_or_create_entity(
    *,
    canonical_name: str,
    entity_type: str,
    domains: Sequence[str] = (),
    properties: dict | None = None,
) -> UUID:
    """Upsert on (canonical_name, entity_type). Idempotent.

    Without this every adopter would reinvent entity resolution
    with inconsistent canonical naming. Load-bearing for graph hygiene.
    """
```

### `cache.py`

```python
@dataclass(frozen=True)
class CacheDecision:
    tier: Literal["graph", "redis"]
    verdict: Literal["fresh", "stale", "miss"]
    freshness_hours: float | None  # None on miss

async def should_query_graph(
    *,
    entity_id: UUID,
    claim_type: str | None,
    agent_id: str | None,
    freshness_threshold_hours: float,
) -> CacheDecision:
    """Graph-tier decision. Calls claim_freshness_hours and applies threshold."""

async def should_call_external(
    *,
    cache_key: str,
    ttl_seconds: int,
) -> CacheDecision:
    """Redis-tier decision. Wraps app/services/cache.py.

    Requires extension to cache_service: get_with_age() returning
    (value, age_seconds) instead of just value.
    """
```

Reads return `verdict="miss"` on backend failure (conservative default forces fresh fetch). Errors logged via existing telemetry.

### `schemas.py`

```python
ConfidenceBand = Literal["low", "medium", "high"]

class ClaimSource(BaseModel):
    kind: Literal["url", "supabase_row", "stripe_row", "shopify_row",
                  "regulation", "user", "other"]
    ref: str                  # URL, row ID, citation
    score: float | None = None

class Claim(BaseModel):
    """A row from kg_findings as returned by find_claims / search_claims_semantic."""
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

    @computed_field
    @property
    def band(self) -> ConfidenceBand:
        return to_band(self.confidence)

class ClaimPayload(BaseModel):
    """Input to write_claim / write_claims. Mirrors write_claim's kwargs.

    Distinct from Claim because input lacks DB-assigned fields
    (id, created_at, freshness_at) and has embed flag controlling
    embedding generation.
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
```

`band` as computed property keeps thresholds tunable in code without DB migration. `ClaimPayload` is the input shape; `Claim` is the output shape — kept separate because input lacks DB-assigned fields and carries the `embed` policy flag that has no place on a stored row.

## Schema migration

**File:** `supabase/migrations/20260518000000_broaden_kg_findings_for_shared_claims.sql`

```sql
BEGIN;

-- 1. Add columns with defaults so existing rows classify as research.
ALTER TABLE kg_findings
    ADD COLUMN IF NOT EXISTS agent_id   TEXT NOT NULL DEFAULT 'research',
    ADD COLUMN IF NOT EXISTS claim_type TEXT NOT NULL DEFAULT 'research_finding';

-- 2. Drop defaults so future inserts must specify.
ALTER TABLE kg_findings
    ALTER COLUMN agent_id   DROP DEFAULT,
    ALTER COLUMN claim_type DROP DEFAULT;

-- 3. Indices for new query patterns.
CREATE INDEX IF NOT EXISTS idx_kg_findings_entity_claim_agent_fresh
    ON kg_findings (entity_id, claim_type, agent_id, freshness_at DESC);

CREATE INDEX IF NOT EXISTS idx_kg_findings_agent_freshness
    ON kg_findings (agent_id, freshness_at DESC);

CREATE INDEX IF NOT EXISTS idx_kg_findings_claim_type_confidence
    ON kg_findings (claim_type, confidence DESC)
    WHERE confidence >= 0.5;

COMMIT;
```

**Rollback** (sibling file or DOWN section): drop the three indices, drop the two columns. Fully reversible — no data destroyed, no existing-column constraints altered.

**Production deploy note:** index creation should use `CREATE INDEX CONCURRENTLY` outside the transaction block. Phase 112 Plan 112-01 implementation must address this — `CONCURRENTLY` cannot run inside `BEGIN`/`COMMIT`.

**Not changed:** `kg_entities`, `kg_edges`, `kg_domain_budgets`, `kg_research_log`, `user_memory_facts`, `agent_memory`.

## Data flow

### Happy path — Data Agent `cohort_analysis(cohort="2026-Q1")`, cold cache

1. `get_or_create_entity(canonical_name="cohort_2026_q1", entity_type="metric")` → entity_id
2. `should_query_graph(entity_id, claim_type="cohort_retention", agent_id="data", freshness_threshold_hours=24)` → `verdict="miss"`
3. `should_call_external(cache_key="stripe:cohort:2026-Q1", ttl_seconds=300)` → `verdict="miss"`
4. Call Stripe; `cache_service.set(...)` for raw response
5. Compute retention curve
6. `presets.data_confidence(sample_size=487, missing_pct=0.02, sigma_distance=0.4, data_age_hours=2)` → 0.83
7. `write_claim(entity_id, agent_id="data", claim_type="cohort_retention", finding_text="...", confidence=0.83, sources=[ClaimSource(kind="stripe_row", ref="...")], embed=False)`
8. Return `{value: 0.624, confidence: 0.83, band: "high", sources: [...]}` to user

### Warm path — same query within 24h

Steps 1, 2 only: graph hit returns existing Claim. Zero Stripe calls.

### Mixed path — graph stale, Redis fresh

Steps 1, 2 (stale), 3 (fresh) → skip Stripe, recompute claim from cached raw data, write new claim.

### Error paths

| Operation | Behavior |
|---|---|
| `get_or_create_entity` fails | Raise. Caller propagates. |
| `should_query_graph` / `should_call_external` fail | Return `verdict="miss"`. Log. Conservative default forces fresh fetch. |
| `find_claims` fails | Return `[]`. Log. Caller proceeds without cached context. |
| `write_claim` fails | Raise. Caller decides retry vs propagate. No silent claim loss. |
| Embedding generation fails when `embed=True` | Insert row with `embedding=NULL`. Log warning. |
| `score_confidence` invalid input | Raise `ValueError`. Programming error, surface immediately. |

**Operating philosophy:** reads degrade silently; writes fail loudly. Missed cache hit costs a recomputation (recoverable); lost claim corrupts cross-agent model (not recoverable).

## Phase 112 — Modules + Research migration

**Promise:** Shared intelligence infrastructure exists. Research Agent uses it. Research behavior unchanged.

### Plans

| Plan | Subject |
|---|---|
| 112-01 | Schema migration + rollback validation |
| 112-02 | `confidence.py` + `presets/research.py` + property-based regression test |
| 112-03 | `claims.py` + entity resolution + `Claim` / `ClaimSource` schemas |
| 112-04 | `cache.py` + `get_with_age()` extension to `app/services/cache.py` |
| 112-05 | Research Agent refactor; delete old `calculate_confidence`, `_upsert_entity`, `_insert_finding` |

### Acceptance criteria

**Schema:**
- Migration applies cleanly to fresh DB and copy-of-prod
- Rollback returns DB to pre-migration state (verified via `pg_dump --schema-only` diff)
- `kg_findings` row count unchanged; existing rows have `agent_id='research'`, `claim_type='research_finding'`
- All three indices present (verified via `\d kg_findings`)

**Module surface:**
- Public surface import test passes — every documented name importable from `app.services.intelligence`
- `Claim.band` is computed property derived from `confidence`, not stored
- `write_claim` defaults `embed=False`
- `CacheDecision` has no `suggested_action` field
- No new ADK tools registered (diff tool registry against pre-112 baseline returns empty)

**Research no-regression (load-bearing):**
- `research_confidence(...) == old calculate_confidence(...)` over 10,000 Hypothesis-generated inputs
- `app/agents/research/` test suite green
- Captured end-to-end research transcript replay produces byte-identical SSE events (modulo timestamps and UUIDs)
- `/admin/research/overview` dashboard renders correctly
- `grep -r "calculate_confidence" app/agents/research` returns zero hits post-merge

**Error path:**
- Tests cover Supabase-down, Redis-down, embedding-failure, and invalid-input scenarios per the error-path table

**Documentation:**
- Public API documented in module-level docstrings
- `docs/intelligence/adopting-shared-infra.md` written for Phase 113 adopters

### Out of scope (deferred)

Data Agent adoption · `search_claims_semantic` · pgvector index · `detect_contradictions` · persona-formatting generalization · `record_claim` ADK tool · weights calibration · consolidating `graph_service.py` / `intelligence_scheduler.py` / `intelligence_worker.py` · changes to `user_memory_facts` / `agent_memory`.

### Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Research regression slips through | Low | High | Hypothesis fuzz + SSE replay both gate merge |
| Index build locks `kg_findings` in prod | Medium | Medium | Use `CREATE INDEX CONCURRENTLY` outside transaction in prod deploy |
| `claims.py` async pattern conflicts with existing | Medium | Low | Mirror `graph_service.py:20-79` pattern; don't invent new style |
| Branch pollution from parallel GSD automation | Medium | Medium | Develop on clean branch off main; cherry-pick to fresh branch before pushing |
| Self-improvement engine depends on refactored symbols | Medium | High | Plan 112-05 audits `app/services/self_improvement_engine.py` and `skill_experiment_evaluator.py`. Read `docs/self-improvement-policy.md` before merge. If engine binds to old names, keep a thin shim. |
| Removing `_upsert_entity` breaks `intelligence_scheduler.py` / `intelligence_worker.py` | Medium | Medium | Plan 112-05 audits imports; update to use `get_or_create_entity` |

### Effort estimate

~3-4 weeks. Plans 112-01 (1-2d), 112-02 (2-3d), 112-03 (4-5d), 112-04 (2-3d), 112-05 (4-5d), plus 3-5d slack/integration.

## Phase 113 — Data Agent adoption

**Promise:** Data Agent uses shared infrastructure. Cross-agent semantic claim search works. Abstraction validated by non-research consumer.

### Plans

| Plan | Subject |
|---|---|
| 113-01 | `presets/data.py` + Data Agent statistical wiring |
| 113-02 | Two-tier cache integration around Data Agent external calls |
| 113-03 | Data Agent claim emission rules + claim-type vocabulary |
| 113-04 | `search_claims_semantic` + pgvector index migration + Executive ADK tool |
| 113-05 | `detect_contradictions` + auto-populate on `write_claim` |

### Claim emission rules (Plan 113-03)

| Output type | Becomes a Claim? | Storage |
|---|---|---|
| Raw aggregation ("last month MRR = $48,234") | No | Redis only (5-min TTL) |
| Cohort retention curve | Yes — one claim per (cohort, month) | `kg_findings`, claim_type=`cohort_retention_mN` |
| Weekly report executive summary | Yes — one claim per insight | `kg_findings`, claim_type=`weekly_insight` |
| Anomaly detection | Yes | `kg_findings`, claim_type=`kpi_anomaly` |
| Trend assertion | Yes | `kg_findings`, claim_type=`revenue_trend` |
| One-off SQL query answer | No (transient) | Response payload only |
| Cohort sample sizes / row counts | No | Embedded in claim's `sources` JSONB |

Principle: a claim has epistemic content (assertion about the world worth recalling). Raw numbers without assertion content stay in Redis.

### Acceptance criteria

**Data Agent behavior:**
- Existing test suite green
- New responses carry `confidence` and `band` fields
- Confidence reflects real signals, not hardcoded constants

**Cache effectiveness:**
- Stripe API call rate reduced by >=40% on synthetic load test vs pre-113 baseline
- Graph-tier hit rate for `cohort_analysis` >=60% on repeated calls within 24h
- No cache-poisoning regressions

**Cross-agent semantic search:**
- `search_claims_semantic(query="Q1 customer retention", top_k=10)` returns both Research findings and Data claims
- pgvector index used (verified via `EXPLAIN ANALYZE`)
- p50 latency <=200ms with 100k claims

**Contradiction detection:**
- Synthetic test: conflicting Data vs Research claims auto-populate `contradicts` field
- False-positive rate <=10% on 50-pair hand-curated test set
- Adds <=150ms to `write_claim` p95

**Cross-cutting:**
- Executive Agent gains `search_claims_semantic` ADK tool (the one justified tool wrapper)
- `/admin/research/overview` extended to show all-agent claim counts
- `docs/intelligence/presets.md` documents the data preset

### Risk register (delta)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Data claim emission too aggressive | Medium | Medium | Strict claim-type vocabulary; sample real outputs in dev |
| pgvector index degrades at scale | Low | Medium | `ivfflat` with `lists=100` for <=500k rows; migrate to `hnsw` if >1M |
| Contradiction detector noisy | Medium | Medium | Threshold tuning gate; ship at `0.85`; tune from telemetry |
| Executive `search_claims_semantic` floods context | Medium | Medium | `top_k` capped at 10; tool description encourages narrow filters |

### Effort estimate

~2-3 weeks. Plans 113-01 / 113-02 mechanical (abstractions exist). 113-03 design-heavy (vocabulary). 113-04 / 113-05 isolated.

## Testing strategy

**Unit (each module):** boundary cases, validation rejection, frozen dataclass immutability.

**Property-based (Hypothesis):**
- `research_confidence == old calculate_confidence` over 10k random inputs — **load-bearing for Phase 112**
- `to_band` monotonicity
- `score_confidence` output range invariant

**Integration (local Supabase):**
- `write_claim` → `find_claims` round-trip preserves JSONB
- `write_claims` produces single INSERT statement
- `get_or_create_entity` idempotent under concurrency
- Migration applies + rolls back cleanly on copy-of-prod

**Regression (Phase 112):**
- Research test suite green
- Captured SSE transcript replay byte-identical

**Load (Phase 113):**
- 1000-request `cohort_analysis` burst — Stripe call count >=40% lower
- 100k-claim semantic search benchmark

**Cross-cutting:**
- Public surface import test
- "No new ADK tools" diff test (Phase 112)

## Observability

| Metric | Tags | Phase |
|---|---|---|
| `intelligence.claims.written` | `agent_id`, `claim_type`, `band` | 112 |
| `intelligence.claims.write_failure` | `agent_id`, `claim_type`, `error_class` | 112 |
| `intelligence.cache.decision` | `tier`, `verdict` | 112 |
| `intelligence.confidence.computed` | `preset_name`, `band` | 112 |
| `intelligence.search.semantic` | `agent_filter`, `top_k`, `latency_bucket` | 113 |
| `intelligence.contradictions.detected` | `new_claim_agent`, `conflicting_claim_agent` | 113 |

Feeds existing `/admin/research/overview` dashboard. Phase 113 extends dashboard to show all-agent claim counts.

## Out of scope (this entire effort)

- Other 8 specialized agents (Marketing, Sales, Financial, Compliance, HR, Operations, Customer Support, Strategic, Content) — separate phases per agent, prioritized by user value
- Persona-aware formatting generalization (low value vs effort)
- Multi-track decomposition / Tavily / Firecrawl generalization (research-specific, do not lift)
- Monitoring jobs generalization (overlaps with existing `ReportScheduler`)
- Per-agent budget tracking analogous to research's `kg_domain_budgets` (only Research has metered external calls)
- Replacing `app/agents/tools/deep_research.py` (separate concept, leave alone)
- Consolidating existing `graph_service.py` / `intelligence_scheduler.py` / `intelligence_worker.py` into new package (cleanup phase, no behavior change)
- Changes to `user_memory_facts` / `agent_memory` (different concept, untouched)
- Weights calibration tooling (Phase 114+ once we have labeled data)

## References

- Research Agent confidence formula: `app/agents/research/tools/synthesizer.py:120-151`
- Research adaptive router: `app/agents/research/tools/adaptive_router.py:54-121`
- Knowledge-graph schema: `supabase/migrations/20260321500000_knowledge_graph.sql`
- Data Agent statistical rigor: `app/agents/data/agent.py:166-176`
- Existing cache service: `app/services/cache.py`
- Existing graph reader: `app/services/graph_service.py`
- Self-improvement policy (load-bearing for Plan 112-05 audit): `docs/self-improvement-policy.md`
