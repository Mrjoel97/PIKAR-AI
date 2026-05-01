---
phase: 89-knowledge-vault-auto-sync
plan: 03
subsystem: rag
tags: [knowledge-vault, search, regression-tests, hotfix-07, manual-uat, phase-completion]

# Dependency graph
requires:
  - phase: 89-knowledge-vault-auto-sync
    provides: 89-01 DocumentService auto-ingest + 89-02 standardized document_type tagging on shipped media paths
provides:
  - "End-to-end retrieval regression suite asserting all 5 document_type values surface via search_business_knowledge in a single ranked list"
  - "User-perspective E2E proxy: DocumentService PDF write -> search retrieval round-trip"
  - "Manual upload (/vault/process) regression coverage proving 89-01/02 did not break document_type='uploaded_document'"
  - "Cross-plan backward-compat protection: real generate_image + generate_video calls preserve nested metadata.asset_type alongside the new top-level document_type"
  - "89-MANUAL-UAT.md: 5-SC scaffold for real-Gemini round-trip verification in a deployed environment"
affects:
  - "Phase 89 ROADMAP success criteria 4 and 5 — now automated"
  - "gsd-verifier: phase-level goal-backward verification can now run against all 5 ROADMAP SCs"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mock _make_search_client builds a Supabase client whose .rpc('match_embeddings').execute() returns AsyncMock-wrapped MagicMock(data=rows) — the canonical pattern for unit-testing semantic_search downstream of search_business_knowledge"
    - "Round-trip proxy: capture DocumentService.generate_pdf's ingest kwargs, then feed those kwargs into the search mock's match_embeddings response so the same row is observed at both ends of the integration boundary"
    - "starlette.requests.Request constructed from a minimal ASGI scope ({type:http, method, path, headers:[]}) for direct router-function invocation without a TestClient"
    - "_schedule_immediately stub for fire-and-forget ingest tasks: replaces _schedule_best_effort_task with a side_effect that wraps the coroutine in a try/except runner and pushes it onto a sink list; assertions run after asyncio.gather(*sink, return_exceptions=True)"

key-files:
  created:
    - tests/unit/test_phase89_vault_retrieval.py
    - .planning/phases/89-knowledge-vault-auto-sync/89-MANUAL-UAT.md
  modified: []

key-decisions:
  - "Imported search_business_knowledge from app.agent (verified canonical location at app/agent.py:131); deliberately did NOT import from app.orchestration.knowledge_tools — that module has only 'add' tools, no search function"
  - "Test 4 uses real production-call inspection over fixture-shape inspection: invokes app.agents.tools.media.generate_image AND generate_video directly with patched ingest_document_content, asserts both top-level document_type AND nested metadata.asset_type. A future PR that strips metadata.asset_type from either site fails this test even if 89-02's per-plan tests are deleted or weakened — this is the genuine cross-plan backward-compat protection that the original Test 4 design lacked"
  - "Test 3 calls process_document_for_rag directly with starlette.requests.Request — slowapi rate limiter does not need bypassing because the Request scope contains no client info to throttle on; cleaner than mounting a TestClient just to invoke one function"
  - "Round-trip proxy in Test 2: captured kwargs dict reused as the search row, NOT a hand-rolled fixture — guarantees the assertion runs against the actual contract DocumentService writes (same content string, same metadata.template, same metadata.asset_id) rather than against a curated stand-in"
  - "Used set_current_user_id contextvar setter directly (with try/finally cleanup) rather than monkeypatching get_current_user_id — closer to production semantics and exercises the actual contextvar plumbing search_business_knowledge depends on"
  - "Manual UAT scaffold deliberately separates SQL verification from agent-response verification per SC: SC1-3 audit the agent_knowledge row directly, SC4 audits both the chat answer AND a count(*) sanity SQL, SC5 audits the row plus the /dashboard/vault list view — minimizes false-positive UAT passes"

patterns-established:
  - "Phase-completion regression test pattern: one focused test file (tests/unit/test_phase89_vault_retrieval.py) covering all phase ROADMAP SCs end-to-end, separate from per-plan tests — 89-03 establishes this; future hotfix phases should adopt"
  - "Round-trip proxy for write-then-search contracts: capture the writer's kwargs into a dict, feed the same dict into the searcher's mock — proves the contract holds at both boundaries without spinning up a real database"

requirements-completed: [HOTFIX-07]

# Metrics
duration: 5min
completed: 2026-05-01
---

# Phase 89 Plan 03: Search Retrieval Regression Summary

**Phase 89 (Knowledge Vault Auto Sync) is now phase-complete: regression tests assert that all 5 document_type values (pdf, pitch_deck, video, image, uploaded_document) round-trip through `search_business_knowledge`, the manual upload branch is unchanged, and the legacy nested `metadata.asset_type` is preserved at all three media.py production call sites — closing HOTFIX-07 with full automated and manual UAT coverage.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-01T21:02:28Z
- **Completed:** 2026-05-01T21:07:17Z
- **Tasks:** 1 (single TDD-green test plan; no production code changes)
- **Files created:** 2 (one test module, one UAT scaffold)
- **Files modified:** 0 (regression-only plan per design)

## Accomplishments

- 4 new GREEN tests in `tests/unit/test_phase89_vault_retrieval.py`
- 1 new manual UAT scaffold at `.planning/phases/89-knowledge-vault-auto-sync/89-MANUAL-UAT.md` covering all 5 ROADMAP SCs
- Combined Phase 89 regression run (4 + 19 + 25 + 3 = 51 tests) all GREEN in 11.08s
- Ruff clean on the new test file
- Zero production-code changes — purely additive regression coverage
- HOTFIX-07 ready for Complete status; Phase 89 ready for `gsd-verifier`

## Task Commits

1. **Task 1: Write end-to-end retrieval regression tests + manual UAT scaffold** — `9d1f9126` (test) — 2 new files, 461 insertions

## Files Created/Modified

- `tests/unit/test_phase89_vault_retrieval.py` (new, 372 lines) — 4 async tests with module-scope `_make_search_client`, `_make_document_supabase`, `_make_media_supabase`, and `_schedule_immediately` helpers
- `.planning/phases/89-knowledge-vault-auto-sync/89-MANUAL-UAT.md` (new) — 6 sections (Setup + SC1-5) with explicit pass/fail checkboxes and SQL verification queries per SC

## Test Catalog (Test → Assertion → SC Mapping)

| # | Test name | Key assertions | ROADMAP SC |
|---|-----------|----------------|------------|
| 1 | `test_search_returns_mixed_document_types` | All 5 `source_type` values present; similarity-descending order; `client.rpc` called once with `match_embeddings` and `filter_user_id='user-1'` | SC4 (search retrieves agent-generated assets) |
| 2 | `test_pdf_ingest_is_retrievable_via_search` | DocumentService.generate_pdf captures `document_type='pdf'` + `metadata.template='financial_report'`; same captured kwargs surface via `search_business_knowledge` round-trip | SC3 (PDF lands in vault) + SC4 (round-trip retrieval) |
| 3 | `test_manual_upload_branch_unchanged_after_phase89` | `process_document_for_rag` invoked directly via starlette Request; `ingest_document_content` called with `document_type='uploaded_document'`, `title='report.pdf'`, `metadata.file_path='user-1/report.pdf'`; response.success=True with embedding_count=2 | SC5 (manual upload regression) |
| 4 | `test_media_py_paths_preserve_legacy_asset_type` | Real `generate_image` call → captured kwargs have `document_type='image'` AND `metadata.asset_type='image'`; real `generate_video` call → captured kwargs have `document_type='video'` AND `metadata.asset_type='video'` | SC1 (video) + SC2 (image) backward-compat protection |

## ROADMAP Success Criteria Coverage Map

| SC | Description | Automated coverage | Manual UAT coverage |
|----|-------------|-------------------|---------------------|
| SC1 | Director-rendered video lands in vault with metadata | 89-02 `test_director_video_ingest_uses_document_type_video` + 89-03 Test 1 (mixed list includes video) + 89-03 Test 4 (real generate_video call preserves asset_type) | 89-MANUAL-UAT § 2 |
| SC2 | Generated image lands in vault | 89-02 `test_image_gen_ingest_uses_document_type_image` + 89-03 Test 1 (mixed list includes image) + 89-03 Test 4 (real generate_image call preserves asset_type) | 89-MANUAL-UAT § 3 |
| SC3 | PDF / pitch deck lands in vault with extracted body text | 89-01 `TestVaultAutoIngest.test_upload_document_ingests_pdf_to_vault` + 89-01 `test_upload_document_ingests_pptx_to_vault` + 89-03 Test 1 (mixed list) + 89-03 Test 2 (round-trip proxy) | 89-MANUAL-UAT § 4 |
| SC4 | `search_business_knowledge` retrieves agent-generated assets | 89-03 Test 1 (mixed list of 5 types) + 89-03 Test 2 (PDF round-trip) | 89-MANUAL-UAT § 5 |
| SC5 | Existing manual `Add to Vault` upload path remains functional | 89-03 Test 3 (`/vault/process` regression) | 89-MANUAL-UAT § 6 |

## Mock Pattern Documentation

**`match_embeddings` RPC mock:** built by `_make_search_client(rows)` — returns a `MagicMock` whose `.rpc(name, params).execute()` is an `AsyncMock` configured with `return_value=MagicMock(data=rows)`. This matches what `app.rag.search_service.format_search_results` consumes (rows must have `content`, `similarity`, `metadata`, `source_type`, `source_id`).

**Embedding generation mock:** `patch("app.rag.search_service.generate_embedding", return_value=[0.1] * 768)` — patched at the import site, not at the embedding_service module, because `semantic_search` imports `generate_embedding` directly. 768 dims chosen to match Gemini's text-embedding-004 dimensionality.

**`get_supabase_client` mock:** `patch("app.rag.knowledge_vault.get_supabase_client", AsyncMock(return_value=client))` — async mock because the production function is async; patched at the consuming module rather than `app.services.supabase` to avoid affecting other tests in the same session.

**Request-context user_id:** `set_current_user_id("user-1")` inside try/finally for cleanup. Production `search_business_knowledge` calls `get_current_user_id()` which reads the contextvar — this exercises the real contextvar plumbing rather than monkeypatching the resolver.

**`_schedule_best_effort_task` stub:** `_schedule_immediately(task_sink)` returns a closure that creates an `asyncio.Task` from each scheduled coroutine and appends it to a sink list; tests `await asyncio.gather(*sink, return_exceptions=True)` after the action so the inner `ingest_document_content` mock's `await_args.kwargs` is populated before assertions. Mirrors `tests/unit/test_phase89_media_tagging.py:_schedule_immediately`.

## Verification

**Automated:**
```
PS> uv run pytest tests/unit/test_phase89_vault_retrieval.py tests/unit/services/test_document_service.py tests/unit/test_director_service.py tests/unit/test_phase89_media_tagging.py -x
============================= 51 passed in 11.08s =============================
```

**Lint:**
```
PS> uv run ruff check tests/unit/test_phase89_vault_retrieval.py
All checks passed!
```

## Test 4 — Real Production-Call Confirmation

Per the plan's WARNING 3 reframing: Test 4 invokes the actual production code paths, not fixture data. The test:

1. Patches `app.agents.tools.media._get_supabase_client`, `app.services.vertex_image_service.generate_image`, `app.agents.tools.media._register_media_contract`, and `app.agents.tools.media._schedule_best_effort_task` to isolate the ingest call.
2. Calls `await media.generate_image(prompt="hero shot", user_id="user-1")` — the canonical public entry point on the production module.
3. After `asyncio.gather` flushes the scheduled tasks, asserts BOTH `kwargs["document_type"] == "image"` AND `kwargs["metadata"]["asset_type"] == "image"` against the real `ingest_document_content` mock.
4. Repeats Invocation B for `media.generate_video` (Veo path), asserting both `document_type='video'` AND `metadata.asset_type='video'`.

A future PR that drops the nested `metadata["asset_type"]` from either site would fail this test even if all of `tests/unit/test_phase89_media_tagging.py` were deleted — that is the cross-plan protection the original Test 4 lacked.

## Decisions Made

See frontmatter `key-decisions` for the full list. Highlights:

- **Test 4 reframed (Option (b)):** real production-call inspection over fixture-shape inspection. Two invocations (`generate_image` + `generate_video`) provide cross-site backward-compat protection that survives deletion or weakening of 89-02's per-plan tests.
- **Round-trip proxy (Test 2):** the same kwargs dict captured from `DocumentService.ingest_document_content` is reused to seed the search mock — guarantees the writer/searcher contract is exercised against identical data, not curated fixtures.
- **Direct router-function invocation (Test 3):** `process_document_for_rag` called directly with a synthetic `starlette.requests.Request` rather than via `TestClient`. The slowapi limiter is benign on a synthetic Request scope (no client info to throttle on).
- **Manual UAT 6 sections × 5 SCs:** SQL queries per SC plus chat-response audits for SC4 and `/dashboard/vault` list-view audit for SC5 — designed to minimize false-positive UAT passes.

## Deviations from Plan

None — plan executed exactly as written.

The implementation matched the plan's `<action>` step-by-step:
1. Read `app/services/request_context.py` ✓ (used `set_current_user_id` directly)
2. Read `tests/integration/test_knowledge_vault.py` ✓ (cribbed `_make_mock_supabase`-style helper)
3. Read `tests/unit/test_phase89_media_tagging.py` ✓ (reused `_schedule_immediately` pattern verbatim)
4. Created `tests/unit/test_phase89_vault_retrieval.py` with 4 async tests and module-level helpers
5. Test 4 invokes real `media.generate_image` and `media.generate_video` (not fixture data) — matches plan's Option (b) reframing
6. Created `89-MANUAL-UAT.md` with 6 sections (Setup + 5 SCs)
7. Pytest GREEN, Ruff clean

## Issues Encountered

None. The test file was authored once and passed on first run (4/4); the combined regression suite passed without conflicts (51/51).

## User Setup Required

None for the automated tests. The manual UAT in `89-MANUAL-UAT.md` requires:
- Real `GOOGLE_API_KEY` for Gemini routing + embeddings
- Real Supabase credentials (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`)
- A signed-in test user account
- Optional: Redis available (or accept circuit-breaker fallback)

## Next Phase Readiness

- Phase 89 (Knowledge Vault Auto Sync) is **complete pending gsd-verifier sign-off**.
- HOTFIX-07 should be marked `[x] Complete` in REQUIREMENTS.md (see post-execution `requirements mark-complete HOTFIX-07` step).
- ROADMAP.md Phase 89 row should show 3/3 plans complete, status In Progress → Ready for verification.
- The next workflow step is `gsd-verifier`'s goal-backward verification against the 5 ROADMAP success criteria. The 5×coverage table above gives the verifier the explicit SC→test mapping it needs.
- The manual UAT (`89-MANUAL-UAT.md`) can be executed in parallel with the verifier run; UAT failures unblock follow-up phases (e.g., audio transcription, deduplication policy — both deferred per CONTEXT).

## Self-Check: PASSED

- `tests/unit/test_phase89_vault_retrieval.py` — present (FOUND, 372 lines, 4 tests)
- `.planning/phases/89-knowledge-vault-auto-sync/89-MANUAL-UAT.md` — present (FOUND, 6 sections covering 5 SCs + setup)
- Commit `9d1f9126` — exists in git log (`git log --oneline | grep 9d1f9126`)
- All 4 new tests GREEN (`uv run pytest tests/unit/test_phase89_vault_retrieval.py -x` → 4 passed)
- Combined Phase 89 regression suite GREEN (51/51 across 89-01, 89-02, 89-03 outputs)
- Ruff clean on `tests/unit/test_phase89_vault_retrieval.py`

---

*Phase: 89-knowledge-vault-auto-sync*
*Plan: 03-search-retrieval-regression*
*Completed: 2026-05-01*
