---
phase: 56-gdpr-rag-hardening
plan: "04"
subsystem: testing
tags: [rag, knowledge-vault, eval, pytest, cosine-similarity, concurrency, embedding]

# Dependency graph
requires:
  - phase: 56-03
    provides: bearer-authenticated vault proxy and MIME-aware ingestion path that this eval now benchmarks

provides:
  - Named relevance dataset with 5 documents and 10 queries (tests/eval_datasets/knowledge_vault_eval.json)
  - Threshold-based eval runner measuring cosine similarity and per-query latency (tests/rag/run_knowledge_vault_eval.py)
  - Concurrent ingestion + search regression coverage: 8 scenarios in test_knowledge_vault.py, 3 in test_rag_services.py
  - Machine-checkable RAG contract: governed thresholds of 0.8 relevance and 2000ms latency

affects:
  - Any future RAG or Knowledge Vault work that needs to verify retrieval quality
  - CI/CD pipelines that want to gate on RAG contract (run run_knowledge_vault_eval.py)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fail-loud eval pattern: zero-vector fallback when embedding credentials absent causes eval to fail loudly rather than silently passing — CI credential gaps surface immediately"
    - "sys.modules supabase stub pattern: inject supabase._async and supabase.lib.client_options stubs before app module import so mock-based integration tests run without live Supabase SDK"
    - "Cosine similarity eval: query embedding vs document embedding similarity used to measure relevance rather than requiring a live vector DB"

key-files:
  created:
    - tests/eval_datasets/knowledge_vault_eval.json
    - tests/rag/run_knowledge_vault_eval.py
    - tests/rag/test_eval_runner_contract.py
  modified:
    - tests/integration/test_knowledge_vault.py
    - tests/integration/test_rag_services.py
    - app/rag/knowledge_vault.py
    - app/rag/search_service.py

key-decisions:
  - "Eval uses cosine similarity between query and document embeddings without a live Supabase vector store — the contract measures embedding quality directly, which is the true relevance signal"
  - "Zero-vector embedding fallback causes eval to fail loudly (0.0 relevance on all queries) when credentials are absent — intentional so CI reveals missing credentials rather than hiding them behind a silent pass"
  - "Concurrent regression tests use sys.modules supabase stubs injected before app module import — avoids live Supabase SDK dependency while testing real knowledge_vault.py code paths"
  - "Pre-existing TestSearchKnowledge tests called search_knowledge synchronously against a search_knowledge_sync wrapper that no longer exists — fixed to await the real async function (Rule 1 bug fix)"
  - "Rerun commands documented in knowledge_vault.py and search_service.py module docstrings so future v7 follow-up is self-describing"

patterns-established:
  - "Named eval dataset pattern: fixed JSON with documents/queries/thresholds fields; query.relevant_doc_ids links queries to ground-truth documents"
  - "Threshold runner pattern: exits non-zero on threshold breach, JSON on stdout, human summary on stderr — machine-readable and CI-friendly"
  - "Supabase stub pattern for integration tests: _stub() helper injects supabase._async.client, supabase.lib.client_options, and app.services.supabase_client stubs at module level before any app import"

requirements-completed: [RAG-01, RAG-02, RAG-03]

# Metrics
duration: 14min
completed: 2026-04-11
---

# Phase 56 Plan 04: RAG Evaluation Contract Summary

**Named relevance dataset (5 docs, 10 queries), cosine-similarity threshold runner (0.8 relevance / 2000ms latency), and 11 concurrent ingestion+search regression scenarios closing RAG-01, RAG-02, and RAG-03**

## Performance

- **Duration:** 14 min
- **Started:** 2026-04-11T14:07:27Z
- **Completed:** 2026-04-11T14:21:36Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Created `tests/eval_datasets/knowledge_vault_eval.json` with 5 representative business documents, 10 queries with ground-truth relevant-doc links, and governed thresholds (0.8 relevance, 2000ms latency)
- Implemented `tests/rag/run_knowledge_vault_eval.py`: computes cosine similarity between query and document embeddings over the real embedding path, measures per-query latency, exits non-zero on threshold breach — machine-readable JSON on stdout, human summary on stderr
- Added 27 new tests across `test_knowledge_vault.py` (4 concurrent ingestion scenarios, 4 search-path regressions) and `test_rag_services.py` (3 concurrent RAG scenarios); 13 contract tests in `test_eval_runner_contract.py`
- All 27 mock-based tests pass in any environment (no Supabase credentials required); 2 live tests correctly skip without credentials

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Add failing tests for eval runner contract** - `10dc595a` (test)
2. **Task 1 GREEN: Implement Knowledge Vault eval runner** - `d00b3549` (feat)
3. **Task 2: Add concurrent ingestion + search regression coverage** - `f28e4e05` (feat)
4. **Task 3: Document governed contract rerun commands** - `e3b95f72` (chore)

## Files Created/Modified

- `tests/eval_datasets/knowledge_vault_eval.json` - 5 documents, 10 queries, governed thresholds
- `tests/rag/run_knowledge_vault_eval.py` - Threshold-based eval runner: cosine similarity + latency measurement
- `tests/rag/test_eval_runner_contract.py` - 13 tests: dataset structure validation + runner CLI contract
- `tests/integration/test_knowledge_vault.py` - Extended with TestConcurrentVaultOperations (4 tests) and TestSearchPathRegression (4 tests); supabase stubs added
- `tests/integration/test_rag_services.py` - Extended with TestKnowledgeVaultConcurrentRAG (3 tests); supabase stubs added; pre-existing TestSearchKnowledge fixed to use async API
- `app/rag/knowledge_vault.py` - Module docstring updated with governed contract rerun commands
- `app/rag/search_service.py` - Module docstring updated with latency contract note

## Decisions Made

- Cosine similarity between generated embeddings is used to measure relevance without requiring a live vector DB. The embedding quality is the true relevance signal, and this keeps the eval credential-gated rather than silently passing with empty results.
- Eval fails loudly (all relevance = 0.0) when no Google API credentials are configured. This is intentional: CI environments without credentials will surface the gap rather than falsely reporting a passing RAG contract.
- `sys.modules` supabase stub injection is the correct pattern for the test environment, matching how other integration tests in this repo stub the rate limiter and supabase service. The stub is injected before any app module is imported.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pre-existing TestSearchKnowledge tests calling search_knowledge without await**
- **Found during:** Task 2 (adding concurrent tests to test_rag_services.py)
- **Issue:** The existing `TestSearchKnowledge.test_searches_with_default_parameters/custom_top_k/handles_search_errors` tests called `search_knowledge("query")` synchronously and patched a `search_knowledge_sync` wrapper that no longer exists. `search_knowledge` is `async` — calling it without `await` returns a coroutine, and `"results" in coroutine` raises `TypeError`.
- **Fix:** Converted all three tests to `@pytest.mark.asyncio async def`, added `await`, and updated patches to mock the real async `semantic_search` path via `AsyncMock` on `get_supabase_client` and `generate_embedding`.
- **Files modified:** `tests/integration/test_rag_services.py`
- **Verification:** `pytest tests/integration/test_rag_services.py -k "search" -x` passes
- **Committed in:** `f28e4e05` (Task 2 commit)

**2. [Rule 3 - Blocking] Added sys.modules supabase stubs to integration test files**
- **Found during:** Task 2 (running tests for the first time)
- **Issue:** `app.rag.knowledge_vault` imports `app.services.supabase_client` which imports `from supabase._async.client import AsyncClient` — but the test environment has an incomplete/stub supabase package with no `_async` subpackage, causing `ModuleNotFoundError`.
- **Fix:** Added `_stub()` helper at module level in both `test_knowledge_vault.py` and `test_rag_services.py` to inject minimal supabase and supabase_client stubs into `sys.modules` before any app import — matching the established pattern in `test_vault_router.py` and `test_account_router.py`.
- **Files modified:** `tests/integration/test_knowledge_vault.py`, `tests/integration/test_rag_services.py`
- **Verification:** All mock-based tests import and run cleanly
- **Committed in:** `f28e4e05` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 1 bug, 1 Rule 3 blocking)
**Impact on plan:** Both fixes were necessary to make the test suite run. No scope creep.

## Issues Encountered

- The test environment has a stub supabase package that exports nothing from `supabase._async` — this is a known CI pattern in this repo where heavy SDK imports are avoided. The `sys.modules` injection is the established solution used by vault router and account router tests.

## User Setup Required

None — no external service configuration required. The eval runner works without credentials (fails loudly as designed). The concurrent regression tests run with mocks only.

## Next Phase Readiness

- Phase 56 is now complete across all four plans: personal data export (56-01), deletion cascade hardening (56-02), vault auth and ingestion correctness (56-03), and the governed RAG evaluation contract (56-04)
- The eval runner `tests/rag/run_knowledge_vault_eval.py` can be added to CI once `GOOGLE_API_KEY` or Vertex AI credentials are available in the pipeline
- The concurrent regression suite runs in any environment and provides ongoing protection against ingestion/search race conditions

---
*Phase: 56-gdpr-rag-hardening*
*Completed: 2026-04-11*
