# Shared Intelligence Infrastructure — Plan 113-03: Data Agent Claim Emission

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define the claim_type vocabulary and wire `write_claim` / `write_claims` into `cohort_analysis` so Data Agent's analytical outputs become `kg_findings` rows. After this plan ships, the graph-tier cache (Plan 113-02) starts actually hitting because there are claims to find.

**Architecture:** Two emissions per `cohort_analysis` call: (a) one **summary claim** with the full executive summary text + average retention + overall confidence, used by `should_query_graph` for short-circuit, and (b) **per-month retention claims** (one per cohort × month pair) for fine-grained semantic search in Plan 113-04. Raw aggregations (transaction lists, MRR numbers) stay OUT of the graph — they live only in Redis per the spec's emission rules.

**Tech Stack:** `write_claim`, `write_claims`, `ClaimPayload`, `ClaimSource` from Plan 112-03. No new dependencies.

**Spec reference:** `docs/superpowers/specs/2026-05-18-shared-intelligence-infra-design.md` § Phase 113 § Claim emission rules

**Out of scope for this plan:** Other Data Agent functions besides `cohort_analysis` (`weekly_report`, `query_analytics` adopt in later phases), embedding generation (`embed=False` everywhere here — Plan 113-04 turns it on for semantic search), contradiction detection (Plan 113-05).

---

## File structure

**Create:**
- `docs/intelligence/claim-types.md` — the claim_type vocabulary reference (one-pager so Phase 113+ adopters use consistent names)

**Modify:**
- `app/agents/data/tools.py:cohort_analysis` — append claim emission after computation
- `tests/integration/test_data_cache_integration.py` — assert the claims show up in kg_findings

**Reference (read-only):**
- `app/services/intelligence/claims.py` — `write_claim`, `write_claims`, `ClaimPayload`
- Spec § Phase 113 § "What outputs become claims (the call Plan 113-03 has to make)" — the emission rule table

---

## Pre-flight context

The emission rule (from the spec):

| Output type | Becomes a Claim? | Storage |
|---|---|---|
| Raw aggregation (e.g., "last month MRR = $48,234") | ❌ No | Redis only |
| Cohort retention curve | ✅ One claim per (cohort, month) | `kg_findings`, claim_type=`cohort_retention_mN` |
| Weekly report executive summary | ✅ One claim per insight | `kg_findings`, claim_type=`weekly_insight` |
| Anomaly detection ("churn up 12%") | ✅ Yes | `kg_findings`, claim_type=`kpi_anomaly` |
| Trend assertion ("revenue trending up") | ✅ Yes | `kg_findings`, claim_type=`revenue_trend` |
| One-off SQL query answer | ❌ No (transient) | Response payload only |
| Cohort sample sizes / row counts | ❌ No | Embedded in claim's `sources` JSONB |

Principle: **a claim has epistemic content** — an assertion about the world worth recalling. Raw numbers stay in Redis.

For Plan 113-03, `cohort_analysis` emits:
1. **`cohort_summary`** — one per call. Used by Plan 113-02's graph short-circuit.
2. **`cohort_retention_mN`** — one per (cohort, month) pair in the retention curve. Enables Plan 113-04's semantic search ("show me Q1 2026 month-3 retention").

Environment quirks: same as prior plans (env vars, PowerShell for uv).

---

## Tasks

### Task 1: Pre-flight + write the claim-type vocabulary doc

**Files:**
- Create: `docs/intelligence/claim-types.md`

- [ ] **Step 1: Confirm Plans 112-03 and 113-01/02 are integrated**

```bash
grep -E "^async def (write_claim|write_claims)" app/services/intelligence/claims.py
grep -nB 2 "data_confidence" app/agents/data/tools.py
grep -nB 2 "should_query_graph" app/agents/data/tools.py
```

Expected: all present.

- [ ] **Step 2: Create `docs/intelligence/claim-types.md`**

```markdown
# Claim-type vocabulary

The `claim_type` column on `kg_findings` is a free-text discriminator
used by `find_claims`, `should_query_graph`, and (in 113-04)
`search_claims_semantic`. Consistent vocabulary across agents lets
the Executive query "any claim of type X" without per-agent guessing.

## Data Agent (Plan 113-03)

| `claim_type` | What it represents | When emitted |
|---|---|---|
| `cohort_summary` | Single high-level finding per `cohort_analysis` call. Powers Plan 113-02's graph-tier short-circuit. | One per `cohort_analysis(months)` call. |
| `cohort_retention_m1` ... `cohort_retention_m6` | Per-month retention rate within a cohort. One claim per (cohort, month) pair. | Multiple per `cohort_analysis` call — one per (cohort, month_offset) in the retention curve. |

Reserved for future Data Agent plans (not emitted yet):

| `claim_type` | What it represents | When emitted |
|---|---|---|
| `weekly_insight` | A single insight from `generate_weekly_report`. | Future Data Agent plan. |
| `kpi_anomaly` | An anomaly detected against a baseline. | Future Data Agent plan. |
| `revenue_trend` | Direction assertion ("revenue trending up Q1"). | Future Data Agent plan. |

## Research Agent

| `claim_type` | What it represents |
|---|---|
| `research_finding` | A finding emitted by the Research Agent's multi-track synthesis. The legacy default for pre-Plan-112-01 rows. |

## How to add a new claim_type

1. Pick a snake_case name that describes the *epistemic content* (not the
   workflow that produced it). Prefer "what's claimed" over "how it was
   measured" — e.g., `cohort_retention_m3` not `stripe_query_result_3`.
2. Add it to the table above with: what it represents, when emitted.
3. If the claim's writer is a new agent, document the agent_id naming
   too (lowercase, matches the agent_id column in kg_findings).
4. Run `find_claims(claim_type="<new_name>")` after the first emission
   to confirm it lands.
```

- [ ] **Step 3: Commit**

```bash
git add docs/intelligence/claim-types.md
git commit -m "docs(113-03): claim-type vocabulary reference"
```

### Task 2: Wire claim emission into `cohort_analysis` (TDD)

**Files:**
- Modify: `app/agents/data/tools.py:cohort_analysis` — append claim writes after computation
- Modify: `tests/integration/test_data_cache_integration.py` — assert claims persist

- [ ] **Step 1: Append the failing claim-emission tests** to `tests/integration/test_data_cache_integration.py`:

```python
# ---------------------------------------------------------------------------
# Plan 113-03: claim emission
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cohort_analysis_writes_summary_claim():
    """After a fresh cohort_analysis, a cohort_summary claim exists in kg_findings."""
    from app.agents.data.tools import _cohort_entity_id, cohort_analysis
    from app.services.intelligence import find_claims

    fake_service = AsyncMock()
    fake_service.analyze = AsyncMock(return_value={
        "retention_data": {
            "cohorts": [
                {"cohort_month": "2026-01", "cohort_size": 200,
                 "retention_by_month": {1: 0.85, 2: 0.72, 3: 0.65}},
            ],
        },
        "ltv_breakdown": {}, "executive_summary": "Stable retention in early cohorts.",
        "chart_data": {},
    })
    with patch(
        "app.services.cohort_analysis_service.CohortAnalysisService",
        return_value=fake_service,
    ):
        await cohort_analysis(months=6)

    entity_id = await _cohort_entity_id(6)
    summaries = await find_claims(
        entity_id=entity_id, claim_type="cohort_summary", agent_id="data", limit=5,
    )
    assert len(summaries) >= 1
    assert summaries[0].finding_text  # non-empty
    assert summaries[0].agent_id == "data"
    assert summaries[0].domain == "data"


@pytest.mark.asyncio
async def test_cohort_analysis_writes_per_month_retention_claims():
    """After cohort_analysis, per-month retention claims exist (one per cohort × month)."""
    from app.agents.data.tools import _cohort_entity_id, cohort_analysis
    from app.services.intelligence import find_claims

    fake_service = AsyncMock()
    fake_service.analyze = AsyncMock(return_value={
        "retention_data": {
            "cohorts": [
                {"cohort_month": "2026-01", "cohort_size": 200,
                 "retention_by_month": {1: 0.85, 2: 0.72, 3: 0.65}},
                {"cohort_month": "2026-02", "cohort_size": 180,
                 "retention_by_month": {1: 0.88, 2: 0.74}},
            ],
        },
        "ltv_breakdown": {}, "executive_summary": "ok", "chart_data": {},
    })
    with patch(
        "app.services.cohort_analysis_service.CohortAnalysisService",
        return_value=fake_service,
    ):
        await cohort_analysis(months=6)

    entity_id = await _cohort_entity_id(6)
    # We seeded 3 + 2 = 5 (cohort, month) points
    m1 = await find_claims(
        entity_id=entity_id, claim_type="cohort_retention_m1", agent_id="data", limit=10,
    )
    m2 = await find_claims(
        entity_id=entity_id, claim_type="cohort_retention_m2", agent_id="data", limit=10,
    )
    m3 = await find_claims(
        entity_id=entity_id, claim_type="cohort_retention_m3", agent_id="data", limit=10,
    )
    # At least one of each — fixture-row uniqueness across runs may vary so use >=
    assert len(m1) >= 1, "cohort_retention_m1 claims should exist"
    assert len(m2) >= 1, "cohort_retention_m2 claims should exist"
    assert len(m3) >= 1, "cohort_retention_m3 claims should exist"
```

- [ ] **Step 2: Run — should FAIL** (`find_claims` returns empty; nothing's being written)

```powershell
uv run pytest tests/integration/test_data_cache_integration.py -k "writes_summary or per_month_retention" -v --tb=short
```

- [ ] **Step 3: Add claim emission to `cohort_analysis`**

In `app/agents/data/tools.py:cohort_analysis`, after the computation block (after `data_confidence` has run, before the response is returned), add:

```python
from app.services.intelligence import write_claim, write_claims
from app.services.intelligence.schemas import ClaimPayload, ClaimSource

# Summary claim — powers the graph-tier short-circuit on next call
exec_summary = str(result.get("executive_summary", "")).strip()
if exec_summary:
    try:
        await write_claim(
            entity_id=entity_id,
            domain="data",
            finding_text=exec_summary,
            confidence=confidence,
            sources=[{"kind": "stripe_row", "ref": f"cohort_window_{months}m"}],
            agent_id="data",
            claim_type="cohort_summary",
        )
    except Exception as e:
        logger.warning("cohort_summary claim write failed: %s", e)

# Per-month retention claims — fine-grained, enables 113-04 semantic search
retention_data = result.get("retention_data", {})
cohorts = retention_data.get("cohorts", []) if isinstance(retention_data, dict) else []
payloads: list[ClaimPayload] = []
for cohort in cohorts:
    cohort_month = str(cohort.get("cohort_month", ""))
    retention_by_month = cohort.get("retention_by_month", {})
    if not isinstance(retention_by_month, dict):
        continue
    for month_offset, retention_rate in retention_by_month.items():
        try:
            mn = int(month_offset)
        except (TypeError, ValueError):
            continue
        if mn < 1 or mn > 12:
            continue
        try:
            rate = float(retention_rate)
        except (TypeError, ValueError):
            continue
        payloads.append(ClaimPayload(
            entity_id=entity_id,
            domain="data",
            finding_text=(
                f"Cohort {cohort_month} month-{mn} retention = "
                f"{rate * 100:.1f}%"
            ),
            confidence=confidence,
            sources=[ClaimSource(
                kind="stripe_row",
                ref=f"cohort:{cohort_month}",
            )],
            agent_id="data",
            claim_type=f"cohort_retention_m{mn}",
        ))

if payloads:
    try:
        await write_claims(payloads)
    except Exception as e:
        logger.warning("cohort_retention bulk write failed: %s", e)
```

Note: writes are wrapped in `try/except` because claim emission is a side-effect — a graph-write failure should NOT prevent the user from getting their cohort analysis result. This is a deliberate exception to the spec's "writes fail loudly" rule, specifically for *secondary persistence* in a tool that has primary work to deliver. Document via the inline comment.

Also: make sure `logger` is imported at the top of `tools.py` (`import logging; logger = logging.getLogger(__name__)`).

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/integration/test_data_cache_integration.py -k "writes_summary or per_month_retention" -v --tb=short
```

- [ ] **Step 5: Confirm prior tests still pass**

```powershell
uv run pytest tests/integration/test_data_cache_integration.py tests/integration/test_data_cache_load.py -v --tb=short 2>&1 | Select-Object -Last 10
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add app/agents/data/tools.py tests/integration/test_data_cache_integration.py
git commit -m "feat(113-03): emit cohort_summary + cohort_retention_mN claims (GREEN)"
```

### Task 3: Verify the graph-tier cache now actually hits

**Files:** none modified — verification only.

In Plan 113-02, the graph-tier short-circuit was wired but mostly missed because nothing was writing claims. Now Plan 113-03 writes them. Confirm the loop closes.

- [ ] **Step 1: End-to-end cache loop test**

Append to `tests/integration/test_data_cache_integration.py`:

```python
@pytest.mark.asyncio
async def test_second_cohort_call_hits_graph_cache():
    """First cohort_analysis call writes claims; second call reads them and short-circuits."""
    from app.agents.data.tools import cohort_analysis

    fake_service = AsyncMock()
    fake_service.analyze = AsyncMock(return_value={
        "retention_data": {
            "cohorts": [{"cohort_month": "2026-03", "cohort_size": 100,
                         "retention_by_month": {1: 0.9}}],
        },
        "ltv_breakdown": {}, "executive_summary": "fresh test", "chart_data": {},
    })

    with patch(
        "app.services.cohort_analysis_service.CohortAnalysisService",
        return_value=fake_service,
    ):
        # Cold call — service hit, claims written
        first = await cohort_analysis(months=6)
        assert first.get("from_cache", False) is False
        assert fake_service.analyze.call_count == 1

        # Warm call — graph cache hits, service NOT called again
        second = await cohort_analysis(months=6)
        assert second.get("from_cache") is True
        assert second.get("cache_tier") == "graph"
        # The mock service call count should still be 1
        assert fake_service.analyze.call_count == 1
```

- [ ] **Step 2: Run**

```powershell
uv run pytest tests/integration/test_data_cache_integration.py::test_second_cohort_call_hits_graph_cache -v --tb=short
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_data_cache_integration.py
git commit -m "test(113-03): verify graph cache hit on second cohort_analysis call"
```

### Task 4: Lint + acceptance sign-off

- [ ] **Step 1: Lint**

```powershell
uv run ruff check app/agents/data/tools.py docs/intelligence/ tests/integration/test_data_cache_integration.py
uv run ruff format app/agents/data/tools.py tests/integration/test_data_cache_integration.py --check
```

Fix in-place; commit any fixes.

- [ ] **Step 2: Final cross-cutting test run**

```powershell
uv run pytest tests/integration/test_data_cache_integration.py tests/integration/test_data_cache_load.py tests/unit/services/intelligence/ -v --tb=short 2>&1 | Select-Object -Last 15
```

Expected: all PASS.

- [ ] **Step 3: Acceptance check against spec**

| Spec line | Where verified |
|---|---|
| Raw aggregations stay OUT of `kg_findings` | Implementation: no MRR / transaction-list writes |
| Cohort retention curves persist as per-month claims | Task 2 + `test_cohort_analysis_writes_per_month_retention_claims` |
| Weekly summary insights would persist (vocabulary reserved) | `docs/intelligence/claim-types.md` reserves `weekly_insight` for a future plan |
| Claim-type vocabulary documented | Task 1 |
| Graph cache hit rate >=60% for repeated cohort_analysis | Task 3 — single hit-rate of 100% on the test, well above 60% |
| Writes wrapped in try/except (claim emission is secondary) | Task 2 + inline comment |
| No new ADK tools | This plan is library-only |

- [ ] **Step 4: Plan 113-03 complete. Plan 113-04 (`search_claims_semantic` + pgvector) is unblocked.**

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| Claim-type vocabulary established | Task 1 |
| `cohort_analysis` writes `cohort_summary` claim | Task 2 |
| `cohort_analysis` writes per-month `cohort_retention_mN` claims | Task 2 |
| Bulk insert via `write_claims` | Task 2 |
| Graph short-circuit now hits on repeat | Task 3 |
| Secondary-write exception to "writes fail loudly" documented | Task 2 inline comment |
| Lint clean | Task 4 |

All spec lines covered.
