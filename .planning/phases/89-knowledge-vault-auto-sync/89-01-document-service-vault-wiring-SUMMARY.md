---
phase: 89-knowledge-vault-auto-sync
plan: 01
subsystem: rag
tags: [knowledge-vault, document-service, pdf, pptx, ingest, hotfix-07, rag, pypdf]

# Dependency graph
requires:
  - phase: 86-document-generation-skills-exposure
    provides: Executive Agent + Content Director instructions that route generate_pdf_report and generate_pitch_deck — caller side of the auto-ingest pipeline
provides:
  - DocumentService._upload_document now performs best-effort Knowledge Vault ingest after media_assets upsert
  - PDF body text auto-extracted via existing pypdf pipeline (RAG-searchable content)
  - PPTX synthetic descriptor (transcription deferred per CONTEXT decision)
  - Standardized vault metadata schema across the third generated-asset path (asset_id, asset_type, bucket_id, file_path, template, file_type, session_id)
  - 5 new pytest tests in TestVaultAutoIngest asserting the full ingest contract
affects: [89-02-standardize-tagging-shipped-paths, 89-03-search-retrieval-regression]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Module-scope import for ingest_document_content (single stable patch target for tests)
    - Best-effort vault ingest mirrors director_service.py:551-568 idiom — outer try/except Exception logs WARNING, widget returned regardless
    - Inner try/except ExtractionError lets supported-format parse failures fall back to synthetic descriptor instead of bubbling up

key-files:
  created: []
  modified:
    - app/services/document_service.py
    - tests/unit/services/test_document_service.py

key-decisions:
  - "Module-scope imports for ingest_document_content / extract_text_from_bytes / ExtractionError — gives a single stable patch target (`app.services.document_service.*`) and matches the existing app/routers/vault.py import shape; verified safe (no circular import: app/rag/knowledge_vault.py does NOT import from document_service)"
  - "PDF path uses real extracted text via existing pypdf pipeline; PPTX path uses synthetic descriptor `f'Generated pitch deck: {title}. Asset ID: {doc_id}.'` (transcription explicitly out of scope per CONTEXT)"
  - "document_type = 'pitch_deck' if template_name == 'pitch_deck' else 'pdf' — matches CONTEXT enum; the only callers of _upload_document are generate_pdf (5 VALID_TEMPLATES) and generate_pptx ('pitch_deck')"
  - "Outer try/except Exception wraps both extraction AND ingest so any unexpected error stays non-blocking; the inner try/except ExtractionError adds graceful fallback for supported-format parse failures (corrupt PDF) without losing the WARNING log"
  - "Empty extracted text ('') falls back to synthetic descriptor — sending '' to ingest_document_content would early-return success=False; descriptor preserves the asset_id/title link so search can still find it"

patterns-established:
  - "Best-effort vault ingest contract for generated documents: media_assets upsert FIRST, then try-extract-then-ingest in an outer try/except Exception, WARNING-level log on failure"
  - "Standardized ingest metadata schema for generated assets: {asset_id, asset_type, bucket_id, file_path, template, file_type, session_id} — 89-02 will align video/image paths to the same shape"
  - "Synthetic descriptor convention for non-text generated artifacts: `f'Generated {kind}: {title}. Asset ID: {doc_id}.'`"

requirements-completed: [HOTFIX-07]

# Metrics
duration: 6min
completed: 2026-05-01
---

# Phase 89 Plan 01: Document Service Vault Wiring Summary

**DocumentService now auto-ingests generated PDFs (real pypdf-extracted text) and pitch decks (synthetic descriptor) into the Knowledge Vault on every generate_pdf / generate_pptx call, closing the third auto-ingest path with module-scope imports and best-effort failure handling.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-05-01T20:46:59Z
- **Completed:** 2026-05-01T20:53:51Z
- **Tasks:** 2 (TDD: RED test commit, then GREEN wiring commit)
- **Files modified:** 2

## Accomplishments

- Closed the third auto-ingest path (HOTFIX-07): `generate_pdf_report` and `generate_pitch_deck` outputs are now searchable via `search_business_knowledge`
- Real document body extraction for PDFs via existing `app/services/document_text_extraction.py` pipeline (pypdf) — no new dependencies
- Standardized vault metadata schema applied at this site; 89-02 will retrofit director_service / media.py to match
- 5 new pytest tests asserting the ingest contract (kwargs, metadata schema, fallback paths, best-effort failure handling)
- All 19 DocumentService tests GREEN (14 existing + 5 new); ruff clean on both modified files

## Task Commits

Each task was committed atomically following the plan's TDD intent:

1. **Task 1: Add Wave-0 failing tests for vault ingest contract** — `cefcd73f` (test) — `tests/unit/services/test_document_service.py` +246 lines, new `TestVaultAutoIngest` class
2. **Task 2: Wire vault ingest into DocumentService._upload_document** — `d0d30646` (feat) — `app/services/document_service.py` +57/-1 lines

_Note: The two commits combined turn the 5 new tests RED → GREEN; the test commit was authored to fail against the pre-Task-2 codebase per TDD discipline._

## Files Created/Modified

- `app/services/document_service.py` — Module-scope imports added at lines 27-31; new ingest block at lines 448-496 inside `_upload_document`, placed AFTER the `media_assets` upsert try/except and BEFORE the widget return; `_upload_document` docstring updated to note the ingest step.
- `tests/unit/services/test_document_service.py` — Added `import logging` (line 8); appended `TestVaultAutoIngest` class with 5 async tests at the end of the file.

## Decisions Made

See frontmatter `key-decisions` for the full list. Highlights:

- **Module-scope import strategy:** chose `from app.rag.knowledge_vault import ingest_document_content` at module top (line 27) rather than the lazy/local-import pattern used by `director_service.py`. Rationale: gives tests a single stable `patch("app.services.document_service.ingest_document_content", new_callable=AsyncMock)` target; matches `app/routers/vault.py` precedent; verified no circular-import risk because `knowledge_vault.py` does not depend on `document_service.py`.
- **PDF body vs synthetic descriptor:** PDFs go through `extract_text_from_bytes` (pypdf) since that's already wired in `app/routers/vault.py /process`. PPTX uses a synthetic descriptor because `_SEARCHABLE_MIMES` does not include the OOXML presentation MIME and adding python-pptx text extraction is explicitly out of scope per CONTEXT.
- **Empty / failed extraction → synthetic descriptor:** the wiring guards against three failure modes (extracted text is None, empty string, or `ExtractionError`) and falls back to a synthetic descriptor in all three cases. This keeps `ingest_document_content` from receiving empty content (which it would early-return `success=False` on) while preserving the asset_id/title link in the vault.

## Deviations from Plan

None — plan executed exactly as written.

The implementation matched the plan's 5-step pseudo-code in `<task name="Task 2">.<action>` line-for-line:
1. `document_type = "pitch_deck" if template_name == "pitch_deck" else "pdf"` — done
2. PDF extraction with `ExtractionError` inner-handler and fallback — done
3. Standardized `ingest_metadata` dict with all 7 plan-specified keys — done
4. Outer `try/except Exception` wraps extraction + ingest — done
5. Widget return unchanged — verified via `TestUploadAndTrack` regression

## Issues Encountered

**Parallel-executor git index contention.** Wave-0 ran 89-02 in parallel; both executors competed for the git index lock and occasionally restaged each other's files. Resolved with a retry loop (up to 30 attempts, 3-4s backoff) around `git add` and `git commit`, plus an explicit `git restore --staged` of the parallel executor's files when they leaked into my staging area before commit. Both Task 1 and Task 2 commits ultimately landed clean (single file each, verified via `git show --stat`).

## User Setup Required

None — purely a backend service wiring change; no env vars, dashboard config, or migrations.

## Next Phase Readiness

- **89-02 (parallel wave-0):** modifies `director_service.py` and `media.py` to align video/image vault metadata to the new standardized schema established here. Disjoint files, no merge conflict expected.
- **89-03 (wave-1):** depends on 89-01 + 89-02 completion. Will add search retrieval regression tests asserting that `search_business_knowledge(document_type=["pdf", "pitch_deck"])` returns artifacts ingested by this plan.
- **Manual UAT** (`.planning/phases/89-knowledge-vault-auto-sync/89-MANUAL-UAT.md`): deferred to post-89-03 phase-level UAT — ask the agent "create a financial report PDF about Q1" → confirm a row appears in `agent_knowledge` with `document_type="pdf"` and the same `doc_id` as the media_assets row.

## Self-Check: PASSED

- [x] `app/services/document_service.py` — present (FOUND, modified at lines 27-31, 396-397, 448-496)
- [x] `tests/unit/services/test_document_service.py` — present (FOUND, `TestVaultAutoIngest` class with 5 tests)
- [x] Commit `cefcd73f` — exists in `git log`
- [x] Commit `d0d30646` — exists in `git log`
- [x] All 19 DocumentService tests GREEN (`uv run pytest tests/unit/services/test_document_service.py` → 19 passed in 18.98s)
- [x] Ruff clean on both modified files

---

*Phase: 89-knowledge-vault-auto-sync*
*Plan: 01-document-service-vault-wiring*
*Completed: 2026-05-01*
