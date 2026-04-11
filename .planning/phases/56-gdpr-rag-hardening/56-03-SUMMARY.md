---
phase: 56-gdpr-rag-hardening
plan: "03"
subsystem: api
tags: [rag, vault, auth, fastapi, nextjs, pypdf, python-docx, vitest, pytest]

# Dependency graph
requires:
  - phase: 56-02
    provides: deletion cascade hardening and audit anonymization before vault correctness work

provides:
  - Shared MIME-aware document text extraction service (app/services/document_text_extraction.py)
  - Bearer-authenticated vault search and process proxy routes (Next.js)
  - Vault router updated to use shared extraction with storage-only format awareness
  - Truthful VaultInterface: searchable vs storage-only distinction in UI and upload flow

affects:
  - 56-04-rag-evaluation-contract (can now benchmark the corrected ingestion path)
  - app/routers/vault.py (process endpoint now uses shared extraction)
  - frontend/src/components/vault (UI truthfulness)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared MIME-aware extraction: extract_text_from_bytes returns None for storage-only, raises ExtractionError on parse failure"
    - "Bearer-forwarding proxy: Next.js route extracts Authorization header from incoming request and forwards to backend"
    - "Truthful UI contract: isSearchableFileType helper mirrors backend MIME set; DocumentStatusBadge renders correct per-file status"

key-files:
  created:
    - app/services/document_text_extraction.py
    - tests/unit/services/test_document_text_extraction.py
    - tests/unit/app/routers/test_vault_router.py
    - frontend/src/__tests__/services/vault-proxy.test.ts
  modified:
    - app/routers/vault.py
    - frontend/src/app/api/vault/search/route.ts
    - frontend/src/app/api/vault/process/route.ts
    - frontend/src/components/vault/VaultInterface.tsx

key-decisions:
  - "extract_text_from_bytes returns None for storage-only formats (image/*, video/*) rather than raising — None is the signal to the caller that embedding is not applicable"
  - "ExtractionError raised on parse failure of a supported format (corrupt PDF/DOCX) so callers can distinguish 'not searchable' from 'broken file'"
  - "Vault proxy forwards Authorization header from the incoming Next.js request rather than fetching a fresh session token — keeps backend as the sole trust boundary"
  - "body user_id removed from both backend proxy calls — backend derives identity from bearer token only"
  - "isSearchableFileType in VaultInterface mirrors the backend MIME set so the upload flow and UI stay in sync without a round-trip"
  - "RAG processing only triggered for searchable file types on upload — storage-only files skip the /api/vault/process call entirely"

patterns-established:
  - "Shared extraction helper pattern: services wanting MIME-aware text extraction import from document_text_extraction rather than duplicating pypdf/docx calls"
  - "Storage-only signal: None return from extract_text_from_bytes = not embeddable; caller decides how to surface this in UX"
  - "DocumentStatusBadge component: single source of truth for per-document searchability status in vault UI"

requirements-completed: [RAG-01]

# Metrics
duration: 11min
completed: 2026-04-11
---

# Phase 56 Plan 03: Vault Auth + Ingestion Truthfulness Summary

**MIME-aware shared extraction (PDF/DOCX/TXT/MD via pypdf and python-docx), bearer-authenticated vault proxy routes, and truthful VaultInterface that distinguishes searchable from storage-only uploads**

## Performance

- **Duration:** 11 min
- **Started:** 2026-04-11T13:52:17Z
- **Completed:** 2026-04-11T14:03:10Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Created `app/services/document_text_extraction.py` as a shared MIME-aware extraction helper — `extract_text_from_bytes` dispatches to pypdf for PDF, python-docx for DOCX, and UTF-8 decode for text/* formats; returns `None` for storage-only types (images, video); raises `ExtractionError` on parse failure
- Fixed both active vault proxy routes (`search/route.ts`, `process/route.ts`) to forward `Authorization: Bearer ...` from the incoming request to the backend instead of relying on body `user_id`; backend remains the authoritative trust boundary
- Updated `VaultInterface.tsx` with `isSearchableFileType` helper, `DocumentStatusBadge` component, truthful upload zone copy, and upload flow that only triggers RAG processing for searchable formats
- 32 tests total: 25 backend (pytest) + 7 frontend (vitest), all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Shared MIME-aware extraction + vault router update** - `3764acb3` (feat)
2. **Task 2: Fix vault proxy auth forwarding** - `25c14aa0` (feat)
3. **Task 3: Align VaultInterface with searchable-format contract** - `b7c4b020` (feat)

## Files Created/Modified

- `app/services/document_text_extraction.py` - New shared extraction helper: `extract_text_from_bytes`, `is_searchable_format`, `ExtractionError`
- `app/routers/vault.py` - Process endpoint updated to use shared extraction; MIME type looked up from vault_documents; storage-only and extraction-error responses added
- `frontend/src/app/api/vault/search/route.ts` - Forwards `Authorization` header; removed body `user_id`
- `frontend/src/app/api/vault/process/route.ts` - Forwards `Authorization` header; removed body `user_id`
- `frontend/src/components/vault/VaultInterface.tsx` - `isSearchableFileType` helper, `DocumentStatusBadge` component, truthful upload copy, conditional RAG processing trigger
- `tests/unit/services/test_document_text_extraction.py` - 17 tests covering all extraction paths
- `tests/unit/app/routers/test_vault_router.py` - 5 tests covering vault process endpoint behavior
- `frontend/src/__tests__/services/vault-proxy.test.ts` - 7 vitest tests covering auth forwarding, unauthenticated rejection, and body user_id non-escalation

## Decisions Made

- `extract_text_from_bytes` returns `None` for storage-only formats rather than raising — `None` is a clean signal meaning "not embeddable" rather than "error"; callers decide how to surface this
- `ExtractionError` class distinguishes broken-file failures from storage-only format signals so the vault router can return a meaningful message either way
- Vault proxy forwards the `Authorization` header from the incoming Next.js request rather than fetching a fresh access token from `getSession` — this is simpler and keeps the token chain unbroken without requiring an extra Supabase call
- `body user_id` removed from both proxy calls to the backend; the backend's `_resolve_user_id` is the correct place to validate identity, and sending it from the proxy creates an unnecessary parallel trust path
- `isSearchableFileType` in VaultInterface is kept in sync with the backend MIME set manually (small, stable list) rather than via an API call — avoids latency and keeps the upload flow offline-capable

## Deviations from Plan

None — plan executed exactly as written. The vault router mock required a module-stubbing pattern (sys.modules injection before import) matching the existing test style in the codebase; this was a test-infrastructure detail, not a deviation from the plan's scope.

## Issues Encountered

- Initial vault router test used a simple MagicMock for the supabase client, but `_assert_storage_access` and the new MIME-type lookup both call `supabase.table()`, causing 403s in tests. Resolved by adopting the same sys.modules stub pattern used in `test_account_router.py`, which correctly bypasses the rate limiter and dependency injection chain.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `56-04` RAG evaluation contract can now benchmark the corrected ingestion path (bearer auth preserved, MIME-aware extraction, storage-only formats excluded from embedding)
- The shared `document_text_extraction` helper is available for reuse by any future admin knowledge ingestion path that currently uses `knowledge_service._extract_text_by_mime` directly

---
*Phase: 56-gdpr-rag-hardening*
*Completed: 2026-04-11*
