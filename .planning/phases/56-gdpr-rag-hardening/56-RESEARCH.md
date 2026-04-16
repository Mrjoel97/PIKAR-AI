# Phase 56: GDPR & RAG Hardening - Research

**Researched:** 2026-04-11
**Status:** Complete

## Research Question

What is the lowest-risk way to close the remaining v7 privacy and Knowledge Vault gaps using the code and trust boundaries that already exist in the repo?

## Findings

### 1. Self-service account deletion already exists, but the database deletion contract is likely stale relative to the current schema

- `app/routers/account.py` already gives the product:
  - self-service account deletion
  - Meta/Facebook deletion callback support
  - deletion status tracking through `data_deletion_requests`
- `supabase/migrations/20260316000000_data_deletion.sql` created the underlying `delete_user_account()` stored procedure.
- That procedure was written before later schema additions such as `governance_audit_log` and other newer user-linked tables.
- So Phase 56 does not need a brand-new deletion feature; it needs a **fresh inventory + hardening pass** so the current schema really satisfies GDPR-02 and GDPR-03.

### 2. The current deletion path does not yet prove audit-log anonymization

- The roadmap requirement explicitly says deletion should anonymize audit log references.
- `governance_audit_log` now stores a required `user_id` and is actively surfaced in admin views.
- The current deletion migration does not obviously anonymize those rows before deleting `auth.users`.
- This creates two concrete risks:
  - referential failure or broken viewer behavior if user-linked history remains raw
  - privacy non-compliance if identity is preserved where the product claims anonymization

### 3. Export groundwork exists, but only as single-table CSV export

- `app/services/data_export_service.py` already handles:
  - RLS-scoped table reads
  - CSV generation
  - Supabase Storage upload
  - signed URL generation
- `app/routers/data_io.py` already exposes table export.
- What is missing for GDPR-01 is not the storage/download mechanism; it is a **full-account export bundle** that gathers user data across multiple domains and excludes/redacts secrets.

### 4. The user-facing Knowledge Vault already exists, but the active Next.js proxy routes are not preserving the backend auth boundary

- `frontend/src/app/dashboard/vault/page.tsx` renders `VaultInterface`, so this is not dormant code.
- `frontend/src/app/api/vault/search/route.ts` and `frontend/src/app/api/vault/process/route.ts` authenticate the browser session, but when they call the backend vault routes they only send `Content-Type`.
- Unlike hardened proxy routes such as `frontend/src/app/api/briefing/route.ts` and the teams invite routes, they do **not** forward `Authorization: Bearer ${session.access_token}`.
- Because `app/routers/vault.py` depends on authenticated user identity, this is a real Phase 56 trust-boundary bug rather than a hypothetical enhancement.

### 5. User-vault document ingestion is currently less capable than the UI promise

- `VaultInterface` advertises/supports PDF, TXT, DOCX, Markdown, images, and videos.
- `app/routers/vault.py` currently downloads the file and tries:
  - `utf-8`
  - fallback `latin-1`
- That means uploaded PDFs and DOCX files are not being processed through a truthful text-extraction path today.
- The repo already has working MIME-aware extraction helpers in `app/services/knowledge_service.py` for admin knowledge ingestion.
- The lowest-risk Phase 56 move is to **centralize and reuse extraction logic** instead of leaving user-vault ingestion on a separate decode-only implementation.

### 6. The RAG subsystem has core plumbing, but not a governed success contract

- Existing pieces already present:
  - embeddings generation in `app/rag/embedding_service.py`
  - chunking/ingestion in `app/rag/ingestion_service.py`
  - search in `app/rag/search_service.py`
  - orchestration in `app/rag/knowledge_vault.py`
  - vector RPC/index support in Supabase migrations
  - `/health/embeddings` in `app/fast_api_app.py`
- Existing tests cover basic mechanics, but not the v7 outcome contract:
  - no named relevance dataset
  - no machine-checkable `>80% relevance` threshold
  - no explicit `<2s` search guardrail
  - no focused concurrency test for overlapping ingestion + search

### 7. The cleanest Phase 56 split follows the actual risk seams

The lowest-risk plan shape is:

1. **56-01 Personal data export**
   - backend-owned full export bundle
   - secrets/tokens excluded or redacted
   - settings entrypoint for download
2. **56-02 Deletion cascade hardening**
   - refresh `delete_user_account()` against the current schema
   - anonymize audit/history references
   - prove no orphans in the scoped tables
3. **56-03 Knowledge Vault auth + ingestion correctness**
   - bearer forwarding in the Next.js proxy routes
   - shared file-type-aware extraction
   - truthful UI/status for searchable formats
4. **56-04 RAG relevance + latency + concurrency contract**
   - fixed eval dataset
   - pass/fail runner
   - latency and concurrency guardrails

## Recommended Plan Shape

- Keep Phase 56 at **4 plans**.
- Treat **56-01 export** as the first execution target so the privacy surface becomes symmetrical before deletion hardening.
- Treat **56-04** as the final plan because it should benchmark the corrected user-vault path from 56-03, not the current partially untrusted path.

## Key Risks To Control

- Export must not leak encrypted credential blobs, OAuth refresh tokens, API keys, or other backend-only secrets.
- Deletion hardening must update the real SQL truth source, not add a superficial app-layer workaround while the database still allows orphaned references.
- Vault proxy fixes must keep the backend token path authoritative rather than shifting privileged behavior into the browser runtime.
- RAG evaluation should remain deterministic and machine-checkable; vague qualitative scoring would keep the phase open-ended.

---

*Phase: 56-gdpr-rag-hardening*
*Research completed: 2026-04-11*
