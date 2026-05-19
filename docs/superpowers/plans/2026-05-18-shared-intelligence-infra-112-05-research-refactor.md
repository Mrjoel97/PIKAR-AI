# Shared Intelligence Infrastructure — Plan 112-05: Research Agent Refactor

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate Research Agent off its private confidence formula and graph writer onto the shared intelligence modules (Plans 112-02 / 112-03). Behavior must remain bit-identical — same SSE events, same finding ordering, same confidence values. Aggressive cleanup: delete `calculate_confidence` and inline `write_to_graph`'s entity-upsert + finding-insert code; keep the function's external contract intact for existing callers.

**Architecture:** Two source files change — `synthesizer.py` swaps its `calculate_confidence` call for `research_confidence`, and `graph_writer.py`'s `write_to_graph` reimplements its internals using `get_or_create_entity` + `write_claims`. Two downstream callers (`app/services/intelligence_scheduler.py`, `app/services/monitoring_job_service.py`) get updated if the signature shape changes from sync to async — the audit in Task 1 decides which path. Self-improvement engine audited for symbol-name dependencies per the spec risk register.

**Tech Stack:** Python 3.10+, existing Research Agent test suite, the shared intelligence package built in 112-02/03/04.

**Spec reference:** `docs/superpowers/specs/2026-05-18-shared-intelligence-infra-design.md` § Phase 112 acceptance criteria § Research no-regression

**Out of scope for this plan:** Replacing the existing `app/agents/tools/deep_research.py` (different concept — that's an Executive tool, not a Research Agent piece), Data Agent adoption (Phase 113), and `app/agents/research/tools/adaptive_router.py` (research-specific budget logic stays where it is for now).

**Load-bearing constraint:** the Phase 112 promise is "Research behavior is unchanged." The Hypothesis property test in Plan 112-02 already guarantees the confidence formula is bit-identical. This plan's regression bar is: the existing `tests/integration/test_research_*.py` and unit tests in `tests/unit/agents/research/` all pass post-refactor with zero changes.

---

## File structure

**Modify (the substantive refactor):**
- `app/agents/research/tools/synthesizer.py` — delete `calculate_confidence` (lines 120-151); update call site (line 96) to use `research_confidence`
- `app/agents/research/tools/graph_writer.py` — reimplement `write_to_graph` internals using shared module; keep external signature
- `app/services/intelligence_scheduler.py` — update if `write_to_graph` becomes async
- `app/services/monitoring_job_service.py` — update if `write_to_graph` becomes async
- `app/agents/research/instructions.py` — textual reference to `write_to_graph(...)` in agent prompts; only update if the tool call shape changes (it shouldn't)

**Create (optional, only if E2E smoke needs fixtures):**
- `tests/integration/test_research_no_regression.py` — minimal end-to-end smoke if existing tests don't cover the full pipeline post-refactor

**Audit only (read-only):**
- `app/services/self_improvement_engine.py` — risk register flagged this; check for symbol-name dependencies on `calculate_confidence` / `_upsert_entity` / `_insert_finding`
- `app/services/skill_experiment_evaluator.py` — same audit
- `docs/self-improvement-policy.md` — read before merge per the recent CLAUDE.md addition

---

## Pre-flight context

Symbols changing:
| Symbol | Before | After |
|---|---|---|
| `app.agents.research.tools.synthesizer.calculate_confidence` | exists | DELETED (callers update) |
| `app.agents.research.tools.synthesizer.synthesize_tracks` (line 96 call) | calls `calculate_confidence` | calls `research_confidence` |
| `app.agents.research.tools.graph_writer.write_to_graph` | sync, inlined upsert+insert | sync or async (Task 1 decides), delegates to shared module |
| `app.agents.research.tools.graph_writer._build_markdown_report` | exists | unchanged (vault-specific, not migrated) |
| `app.agents.research.tools.graph_writer.write_to_vault` | exists | unchanged (RAG, not graph) |
| `app.agents.research.tools.graph_writer.GRAPH_WRITER_TOOLS` | exports `[write_to_graph]` | unchanged |

Known callers of `calculate_confidence` (from earlier audit):
- `app/agents/research/tools/synthesizer.py:96` — internal, swap to `research_confidence`
- `app/agents/tools/deep_research.py:983` — that's a private `_calculate_confidence` (different function, leave alone)

Known callers of `write_to_graph`:
- `app/services/intelligence_scheduler.py:241` (import), `:270` (call) — verify async context
- `app/services/monitoring_job_service.py:108-110` (lazy wrapper), `:656` (call) — verify async context

Self-improvement audit risk (from design risk register):
- `app/services/self_improvement_engine.py` and `app/services/skill_experiment_evaluator.py` may depend on these symbols by name. The recent `docs/self-improvement-policy.md` and CLAUDE.md addition state this engine is load-bearing.

Environment quirks: same as 112-01/02/03/04 — `uv` via PowerShell, Supabase local via docker exec for migrations.

---

## Tasks

### Task 1: Audit — callers, async/sync contexts, and self-improvement dependencies

**Files:** none modified — investigation only.

- [ ] **Step 1: Confirm shared infra is present**

```bash
ls app/services/intelligence/{__init__.py,confidence.py,claims.py,cache.py,schemas.py}
grep -E "^async def (write_claim|write_claims|find_claims|get_or_create_entity)" app/services/intelligence/claims.py
grep -E "^def (research_confidence)" app/services/intelligence/presets/research.py
```

Expected: all files exist; `claims.py` has 5 async functions defined (not stubs); `research_confidence` exists. If any stub remains, STOP — Plans 112-02/03 aren't complete.

- [ ] **Step 2: Check write_to_graph callers' async context**

```bash
grep -B 3 "write_to_graph(synthesis" app/services/intelligence_scheduler.py
grep -B 3 "write_to_graph(synthesis" app/services/monitoring_job_service.py
```

For each call site, determine whether the enclosing function is `async def` or `def`. Record this in the report:
- intelligence_scheduler.py:270 enclosing function: `async def` / `def` — _____
- monitoring_job_service.py:656 enclosing function: `async def` / `def` — _____

This determines the strategy for Task 4. Two paths:
- **If both callers are async:** make `write_to_graph` async; update call sites to `await`.
- **If either is sync:** keep `write_to_graph` sync; internally use `asyncio.run()` (or `anyio.from_thread.run`) to call the async shared module. (This is heavier but preserves the contract.)

- [ ] **Step 3: Audit self-improvement engine for symbol dependencies**

```bash
grep -rn "calculate_confidence\|_upsert_entity\|_insert_finding\|write_to_graph" app/services/self_improvement_engine.py app/services/skill_experiment_evaluator.py
```

Record what you find. Expected: nothing — the spec design said these engines don't bind to research's internals — but verify. If they DO depend on any of these symbols, the refactor must preserve those symbols (likely as thin shims). Read `docs/self-improvement-policy.md` to understand the autonomy boundary before deciding.

- [ ] **Step 4: Read existing research tests to know the regression bar**

```bash
ls tests/unit/agents/research tests/integration/test_research* 2>/dev/null
```

Note which test files exist. The acceptance bar for Task 3 and Task 5 is: every one of these tests passes post-refactor without test modifications.

- [ ] **Step 5: Capture the audit findings as a comment block in the plan**

This task produces no commits — only a written record. Open `docs/superpowers/plans/2026-05-18-shared-intelligence-infra-112-05-research-refactor.md` and add a comment at the bottom titled `## Task 1 Audit Findings` with:
- Async/sync context of each `write_to_graph` caller
- Self-improvement engine symbol dependencies (if any)
- List of existing research test files
- Chosen strategy (sync-preserved vs async-conversion)

Commit this annotation:
```bash
git add docs/superpowers/plans/2026-05-18-shared-intelligence-infra-112-05-research-refactor.md
git commit -m "docs(112-05): record Task 1 audit findings"
```

---

### Task 2: Refactor `synthesizer.py` to use `research_confidence`

**Files:**
- Modify: `app/agents/research/tools/synthesizer.py`

- [ ] **Step 1: Update the call site** (around line 96)

Find this block:

```python
confidence = calculate_confidence(
    track_agreement=track_agreement,
    source_quality=source_quality,
    freshness=freshness,
    contradictions_found=len(contradictions),
)
```

Replace with:

```python
from app.services.intelligence.presets import research_confidence

confidence = research_confidence(
    track_agreement=track_agreement,
    source_quality=source_quality,
    freshness=freshness,
    contradictions_found=len(contradictions),
)
```

The `from ...` import should be at the top of the file with the other imports, not inline. Move it.

- [ ] **Step 2: Delete the old `calculate_confidence` function** (lines 120-151)

Remove the entire function definition. If `calculate_confidence` is exported from the file's `__all__` (check), remove it there too.

- [ ] **Step 3: Verify no other references to `calculate_confidence` in the file**

```bash
grep -n "calculate_confidence" app/agents/research/tools/synthesizer.py
```

Expected: zero hits (the import and call site now use `research_confidence`).

- [ ] **Step 4: Run any synthesizer-specific tests if they exist**

```bash
ls tests/unit/agents/research/tools/test_synthesizer*.py tests/integration/test_*synthesiz*.py 2>/dev/null
```

If found, run them:
```powershell
uv run pytest tests/unit/agents/research/tools/test_synthesizer*.py -v --tb=short
```

Expected: PASS. If they were testing the old `calculate_confidence` directly (rare), update the tests to import from `app.services.intelligence.presets.research_confidence`. **Do not change the test assertions** — the values should be identical.

- [ ] **Step 5: Commit**

```bash
git add app/agents/research/tools/synthesizer.py
git commit -m "refactor(112-05): synthesizer uses research_confidence preset; delete legacy"
```

---

### Task 3: Run full research test suite — confirm zero regressions

**Files:** modify only if a test exposed a real refactor bug (rare).

- [ ] **Step 1: Run all research-related tests** (from PowerShell):

```powershell
$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_SERVICE_ROLE_KEY = (supabase status -o env | Select-String '^SERVICE_ROLE_KEY=').ToString().Split('=',2)[1].Trim('"')
$env:SUPABASE_DB_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
uv run pytest tests/unit/agents/research/ tests/integration/test_research*.py -v --tb=short 2>&1 | Select-Object -Last 50
```

Expected: same pass-rate as before the refactor. If anything that previously passed now fails:
1. Read the failure carefully
2. If it's a test importing `calculate_confidence` directly: update the import path to `from app.services.intelligence.presets import research_confidence`
3. If it's a behavioral diff in confidence values: STOP — this means the preset isn't bit-identical. Re-check Plan 112-02 Task 4's implementation against the legacy formula.

- [ ] **Step 2: If any test imports needed updating, commit them**

```bash
git add tests/
git commit -m "refactor(112-05): update test imports to use research_confidence"
```

(Skip if no test updates.)

- [ ] **Step 3: Confirm the Hypothesis property test from Plan 112-02 still passes**

```powershell
uv run pytest tests/unit/services/intelligence/test_presets_research.py -v
```

Expected: PASS. If this fails — the refactor accidentally drifted the formula. Stop, investigate. (Very unlikely since we only moved the call site, not the formula.)

---

### Task 4: Refactor `write_to_graph` in `graph_writer.py`

**Files:**
- Modify: `app/agents/research/tools/graph_writer.py`
- Modify: `app/services/intelligence_scheduler.py` (if Task 1 audit shows async caller)
- Modify: `app/services/monitoring_job_service.py` (if Task 1 audit shows async caller)

This is the biggest refactor in the plan. Two implementation paths depending on Task 1 audit:

**Path A — both callers are async (preferred if true):**

Change `write_to_graph` to `async def`, update both call sites to `await write_to_graph(...)`. Cleaner long-term.

**Path B — at least one caller is sync:**

Keep `write_to_graph` sync. Inside, use `asyncio.run()` to call the shared async functions, OR use `anyio.from_thread.run_sync` if `asyncio.run` would re-enter an event loop. Less clean but preserves contract.

Pick the path based on Task 1's findings.

- [ ] **Step 1: Replace `write_to_graph` body**

In `app/agents/research/tools/graph_writer.py`, replace the function body (lines 32-136) with the implementation matching your chosen path.

**Path A (async)** template:

```python
async def write_to_graph(
    synthesis: dict[str, Any],
    domain: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Persist synthesized findings to the knowledge graph tables.

    Refactored in Plan 112-05 to use the shared intelligence package:
    - get_or_create_entity for the topic upsert
    - write_claims for bulk finding insert

    Args:
        synthesis: Output from synthesize_tracks().
        domain: Agent domain.
        user_id: Optional user ID for audit trail (currently unused;
                 the shared module doesn't track user yet).

    Returns:
        Dict with success flag, counts, and entity_id (or None on failure).
    """
    from app.services.intelligence import (
        get_or_create_entity,
        write_claims,
    )
    from app.services.intelligence.schemas import ClaimPayload, ClaimSource

    original_query = synthesis.get("original_query", "research topic")
    confidence = synthesis.get("confidence", 0.5)
    findings = synthesis.get("findings", [])
    sources = synthesis.get("all_sources", [])

    try:
        entity_id = await get_or_create_entity(
            canonical_name=original_query,
            entity_type="topic",
            domains=[domain],
            properties={
                "confidence": confidence,
                "source_count": len(sources),
                "tracks_succeeded": synthesis.get("tracks_succeeded", 0),
            },
        )

        payloads: list[ClaimPayload] = []
        for finding in findings:
            payloads.append(ClaimPayload(
                entity_id=entity_id,
                domain=domain,
                finding_text=finding.get("text", ""),
                confidence=finding.get("confidence", 0.5),
                sources=[ClaimSource(
                    kind="url",
                    ref=finding.get("source_url", "") or "unknown",
                )],
                agent_id="research",
                claim_type="research_finding",
            ))

        claim_ids = await write_claims(payloads) if payloads else []

        logger.info(
            "Graph write complete: entity=%s, findings=%d, domain=%s",
            entity_id, len(claim_ids), domain,
        )
        return {
            "success": True,
            "entities_written": 1,
            "findings_written": len(claim_ids),
            "entity_id": str(entity_id),
        }
    except Exception as e:
        logger.error("Graph write failed: %s", e)
        return {
            "success": False,
            "entities_written": 0,
            "findings_written": 0,
            "entity_id": None,
            "error": str(e),
        }
```

**Path B (sync-preserved)** — wrap in `asyncio.run()` or use a thread-safe runner. Implementer must be careful about event-loop reentry. Example:

```python
def write_to_graph(synthesis, domain, user_id=None):
    """Same external contract; internally bridges to async shared module."""
    import asyncio
    async def _inner():
        # ... same body as Path A's try/except ...
        pass
    try:
        return asyncio.run(_inner())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            # Fallback: get the running loop and create a task
            loop = asyncio.get_running_loop()
            return asyncio.run_coroutine_threadsafe(_inner(), loop).result()
        raise
```

Path B is fragile under nested event loops; prefer Path A if at all possible. If Path A's call sites can't be reasonably converted to async, document why in the commit message.

- [ ] **Step 2: If Path A, update the two caller files**

```bash
grep -n "write_to_graph" app/services/intelligence_scheduler.py app/services/monitoring_job_service.py
```

For each call site:
- Change `result = write_to_graph(...)` → `result = await write_to_graph(...)`
- Verify the enclosing function is `async def` — if it's `def`, change to `async def` and trace callers further up (this can cascade; document the chain in the commit message)

- [ ] **Step 3: Verify no other internal calls to `_get_supabase()` remain unused**

The legacy `_get_supabase()` private helper in `graph_writer.py` (lines 25-29) is no longer needed if the shared module is doing all DB access. Delete it if unused:

```bash
grep -n "_get_supabase" app/agents/research/tools/graph_writer.py
```

If only the definition remains (no callers), delete the definition.

- [ ] **Step 4: Run research tests + monitoring/scheduler tests**

```powershell
uv run pytest tests/unit/agents/research/ tests/integration/test_research*.py tests/unit/services/test_intelligence_scheduler*.py tests/unit/services/test_monitoring_job*.py -v --tb=short 2>&1 | Select-Object -Last 50
```

Expected: same pass-rate as before. If anything fails, diagnose carefully — the most likely culprit is a sync/async mismatch from Path A or an event-loop issue from Path B.

- [ ] **Step 5: Commit**

```bash
git add app/agents/research/tools/graph_writer.py \
        app/services/intelligence_scheduler.py \
        app/services/monitoring_job_service.py
git commit -m "refactor(112-05): write_to_graph uses shared intelligence module"
```

(Adjust `git add` list based on what actually changed.)

---

### Task 5: End-to-end smoke — an actual research call returns correctly

**Files:** none modified.

Whether or not the project has a captured-SSE-replay test, run an actual end-to-end research query against the local dev server to confirm the refactor didn't break anything obvious.

- [ ] **Step 1: Start the local backend** (from PowerShell):

```powershell
# Confirm Supabase + Redis are running first
docker ps --format "{{.Names}}" | Select-String -Pattern "supabase|redis"

# Then start backend in a separate terminal
# (from PowerShell, in a new window or background)
# make local-backend
```

Or run the FastAPI app directly:
```powershell
uv run uvicorn app.fast_api_app:app --host 127.0.0.1 --port 8000 --reload
```

Wait for "Application startup complete."

- [ ] **Step 2: Hit the SSE endpoint with a research query**

From a separate PowerShell, send a research request via the A2A endpoint. The exact curl shape depends on the project's A2A protocol; check existing test fixtures or the OpenAPI spec at `http://127.0.0.1:8000/docs`. An approximate template:

```powershell
# Replace <a2a_path> with the actual A2A path from app/routers/a2a.py
$body = @{
    message = "Research the impact of AI agents on small business operations"
    domain = "marketing"
} | ConvertTo-Json
curl.exe -N -H "Content-Type: application/json" -d $body http://127.0.0.1:8000/<a2a_path> | Select-Object -First 30
```

Expected: SSE event stream containing widget events, reasoning trace, and a synthesized finding. Verify in the output:
1. Confidence value present and looks reasonable (between 0 and 1)
2. No errors emitted
3. Stream completes cleanly

If the project has a captured-fixture SSE replay test, run it instead:
```powershell
uv run pytest tests/integration/test_research_e2e*.py -v
```

- [ ] **Step 3: Verify a kg_findings row was written**

```powershell
docker exec supabase_db_Pikar-Ai psql -U postgres -d postgres -c "SELECT id, agent_id, claim_type, confidence, freshness_at FROM kg_findings WHERE agent_id = 'research' ORDER BY freshness_at DESC LIMIT 3;"
```

Expected: a recent row with `agent_id='research'`, `claim_type='research_finding'`, freshness_at near "now".

If you don't see a new row, the graph write side of the refactor has a bug. Investigate by checking the backend logs for `Graph write failed` warnings.

- [ ] **Step 4: Stop the backend.** No commit in this task — verification only.

---

### Task 6: Cleanup and lint pass

**Files:** modify only if lint flags issues or dead code is found.

- [ ] **Step 1: Check for dead imports in synthesizer.py and graph_writer.py**

```bash
uv run ruff check app/agents/research/tools/synthesizer.py app/agents/research/tools/graph_writer.py
```

Common issues:
- Unused `import json` in graph_writer.py if you removed the `json.dumps` calls
- Unused `_get_supabase` helper (delete if no callers)

- [ ] **Step 2: Format**

```powershell
uv run ruff format app/agents/research/tools/synthesizer.py app/agents/research/tools/graph_writer.py app/services/intelligence_scheduler.py app/services/monitoring_job_service.py
```

- [ ] **Step 3: Type check**

```powershell
uv run ty check app/agents/research/ app/services/intelligence_scheduler.py app/services/monitoring_job_service.py
```

Fix any new type errors (likely related to async/sync conversions or import changes).

- [ ] **Step 4: Full test suite re-run**

```powershell
uv run pytest tests/unit/agents/research/ tests/integration/test_research*.py tests/unit/services/intelligence/ tests/integration/test_intelligence_claims.py tests/integration/test_intelligence_cache.py tests/integration/test_kg_findings_broaden_migration.py -v --tb=short 2>&1 | Select-Object -Last 30
```

Expected: all tests PASS or skip cleanly. If any new failures, diagnose before committing.

- [ ] **Step 5: Commit lint/cleanup if needed**

```bash
git add app/agents/research/ app/services/intelligence_scheduler.py app/services/monitoring_job_service.py
git commit -m "style(112-05): lint and cleanup post-refactor"
```

(Skip if no fixes.)

---

### Task 7: Phase 112 acceptance sign-off

**Files:** none modified — final verification across all 5 sub-plans.

- [ ] **Step 1: Confirm no orphan symbol names remain**

```bash
grep -rn "calculate_confidence" app/agents/research app/services
# Should NOT find the legacy synthesizer function — only references to
# research_confidence imported from intelligence.presets.

grep -rn "_upsert_entity\|_insert_finding" app/agents/research app/services
# Should find nothing (legacy private helpers from graph_writer.py
# are gone or unused).
```

Expected outputs:
- `calculate_confidence` only appears as `research_confidence` callers, or as `_calculate_confidence` (the deep_research one, unrelated)
- `_upsert_entity` / `_insert_finding` appear nowhere

- [ ] **Step 2: Cross-check Phase 112 acceptance from the spec**

| Phase 112 acceptance line | Status |
|---|---|
| Schema migration applies cleanly | ✓ Plan 112-01 |
| Public surface importable from app.services.intelligence | ✓ Plans 112-02 / 03 / 04 |
| `Claim.band` computed property | ✓ Plan 112-03 |
| `write_claim` defaults `embed=False` | ✓ Plan 112-03 |
| `CacheDecision` has no `suggested_action` | ✓ Plan 112-04 |
| No new ADK tools registered | ✓ All plans verified by `git diff` checks |
| `research_confidence == legacy calculate_confidence` over 10k inputs | ✓ Plan 112-02 Hypothesis test |
| Research test suite green | ✓ Tasks 3, 5 of this plan |
| Captured-transcript SSE replay byte-identical | ⚠ Best-effort smoke in Task 5; if no captured fixture exists, document this gap |
| `/admin/research/overview` dashboard renders | Manual visual check; not gated here |
| Old `calculate_confidence` removed | ✓ Task 2 of this plan |
| Self-improvement engine audit | ✓ Task 1 of this plan |

- [ ] **Step 3: Confirm git log shape across all 5 sub-plans**

```bash
git log --oneline spec-b-clean..HEAD
```

Expected: a sequence of commits with prefixes `test(112-XX)`, `feat(112-XX)`, `refactor(112-05)`, `docs(112-XX)`, `style(112-XX)` covering all 5 sub-plans. The TDD cycle should be visible (tests before implementation for each substantive change).

- [ ] **Step 4: Phase 112 implementation complete. Phase 113 (Data Agent adoption) is unblocked.**

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| `calculate_confidence` deleted from synthesizer.py | Task 2 |
| Synthesizer call site uses `research_confidence` | Task 2 |
| `write_to_graph` reimplemented with shared module | Task 4 |
| Existing `write_to_graph` external contract preserved | Task 4 (Path A or B) |
| Downstream callers updated (if needed) | Task 4 Step 2 |
| Research test suite green post-refactor | Task 3, Task 5, Task 6 Step 4 |
| Self-improvement engine audit | Task 1 |
| `docs/self-improvement-policy.md` consulted before merge | Task 1 Step 3 |
| Aggressive cleanup (no alias) | Tasks 2, 4 — old function names deleted |
| End-to-end smoke | Task 5 |

All spec lines covered. No placeholders. No unmapped requirements.

---

## Task 1 Audit Findings

_To be filled in by the implementer running Task 1. This section is a deliberate placeholder; Task 1 Step 5 commits the filled-in version._

- intelligence_scheduler.py:270 enclosing function: ____
- monitoring_job_service.py:656 enclosing function: ____
- self-improvement engine symbol dependencies: ____
- existing research test files: ____
- Chosen strategy (sync-preserved / async-conversion): ____
