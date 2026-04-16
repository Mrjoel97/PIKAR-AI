# Phase 56: GDPR & RAG Hardening - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 56 closes the last v7 production-readiness gaps around privacy self-service and user-owned Knowledge Vault reliability:

1. **Personal data export** — authenticated users need one truthful self-service path to export the personal/business data the app stores for them in a standard downloadable archive.
2. **Deletion and anonymization hardening** — account deletion must fully cascade across current user-linked tables and preserve historical audit value by anonymizing audit references instead of leaving raw identity behind.
3. **Knowledge Vault auth and ingestion correctness** — the active Next.js proxy and backend ingestion flow must preserve the authenticated trust boundary and process the document types the UI promises are searchable.
4. **Governed RAG quality and performance** — retrieval quality, latency, and concurrent ingestion/search behavior need a measurable pass/fail contract rather than informal confidence.

**Out of scope for Phase 56**:
- New compliance programs beyond the scoped GDPR-style self-service export/deletion requirements
- Re-architecting the full RAG stack, swapping embedding vendors, or introducing a new vector store
- Broad admin knowledge-base work that is separate from the authenticated end-user Knowledge Vault
- Multi-region retention/legal-hold policy design
- New media understanding pipelines for every file type unless required to make current user-facing promises truthful

</domain>

<decisions>
## Implementation Decisions

### Execution Order

- **Plan and execute Phase 56 inside GSD.** No detached privacy/RAG checklist outside `.planning`.
- **Start with export (`56-01`).** It gives the cleanest inventory of what personal data the product currently owns and closes the most obvious missing self-service requirement first.
- **Then harden deletion (`56-02`).** The deletion path should be updated after the export inventory so the privacy surface is symmetrical: what we can export, we can also delete or anonymize correctly.
- **Then fix user-vault auth + ingestion (`56-03`).** This closes the active correctness bugs before performance benchmarking would otherwise measure an untruthful path.
- **Finish with the RAG evaluation contract (`56-04`).** Relevance/latency/concurrency measurements should be attached to the corrected ingestion and auth behavior, not the current partial state.

### Privacy Boundary

- **Account privacy actions belong to the authenticated account surface.** Export and deletion should stay backend-owned and user-triggered from Settings / Account rather than being split across unrelated admin or data-I/O entrypoints.
- **Secrets must not leak into exports.** OAuth tokens, API keys, encrypted credential blobs, and service-only metadata should be excluded or explicitly redacted; the export should describe integrations truthfully without dumping sensitive secrets.
- **Deletion must preserve audit usefulness without preserving identity.** Governance/history records should retain the action trail while removing or anonymizing directly identifying references where required.

### Knowledge Vault Boundary

- **Bearer-authenticated identity remains the source of truth.** Frontend proxy routes may pass `user_id` for convenience, but backend access control must continue to derive authority from the authenticated token path.
- **User-vault ingestion should reuse shared extraction logic, not decode raw bytes ad hoc.** The repo already has MIME-aware extraction patterns for admin knowledge; Phase 56 should reuse or centralize them instead of keeping a separate weaker path.
- **The UI must be truthful about searchable formats.** If some uploaded formats remain storage-only during this phase, the UI should say so instead of implying they were embedded successfully.

### RAG Contract Boundary

- **Relevance needs a named dataset.** “Looks good” is not enough for `>80% relevance`; Phase 56 needs a small fixed query/document set and machine-checkable scoring rules.
- **Latency should be measured against the real user-vault search path.** Any `<2s` claim should use the actual search service path and representative fixture load.
- **Concurrency coverage must target corruption/deadlock seams.** The focus is overlapping ingestion + search behavior, not synthetic benchmarking for its own sake.

### Claude's Discretion

The executor may decide without re-asking:
- Whether the export bundle is JSON-only, CSV-only, or a mixed archive, as long as it is downloadable, complete, and secrets are excluded/redacted
- Whether document extraction is centralized in a new helper module or refactored out of existing services, as long as both admin and user-vault ingestion can share the same truthful parsing behavior
- The exact eval dataset size and scoring shape for RAG, as long as the final contract is deterministic and threshold-based

</decisions>

<specifics>
## Specific Ideas

- `app/services/data_export_service.py` already solves signed storage uploads for single-table CSV export; Phase 56 should reuse that pattern rather than invent a second download mechanism.
- `supabase/migrations/20260316000000_data_deletion.sql` pre-dates newer user-linked tables and `governance_audit_log`, so the existing `delete_user_account()` function is probably no longer exhaustive enough for v7 sign-off.
- `frontend/src/app/api/vault/search/route.ts` and `frontend/src/app/api/vault/process/route.ts` currently authenticate the browser session but do not forward the bearer token when calling the backend vault endpoints.
- `app/routers/vault.py` currently decodes uploaded file bytes as `utf-8` or `latin-1`, which does not match the PDF/DOCX-heavy promise shown in `VaultInterface`.
- `app/services/knowledge_service.py` already contains `_extract_pdf_text`, `_extract_docx_text`, and `_extract_text_by_mime`, which strongly suggests a shared extraction helper is the lowest-risk path.

</specifics>

<code_context>
## Existing Code Insights

### Privacy / Account

- `app/routers/account.py` already owns:
  - `DELETE /account/delete`
  - Facebook deletion callback handling
  - deletion status lookup by confirmation code
- `frontend/src/app/settings/page.tsx` already exposes a delete-account UI entrypoint and is the natural place for a new export action.
- `app/services/data_export_service.py` and `app/routers/data_io.py` already provide signed CSV export infrastructure, but only for one table at a time.

### Deletion / Audit

- `supabase/migrations/20260316000000_data_deletion.sql` created `data_deletion_requests` and the `delete_user_account(p_user_id UUID)` stored procedure.
- That migration already deletes many user-scoped rows and preserves `data_deletion_requests` with `ON DELETE SET NULL`, but it predates later `auth.users(id)` references and the governance audit subsystem.
- `supabase/migrations/20260403300000_enterprise_governance.sql` introduced `governance_audit_log(user_id UUID NOT NULL, ...)`, which is not obviously anonymized by the existing deletion function.
- `app/routers/admin/governance_audit.py` reads `governance_audit_log` and enriches rows with actor emails via the auth admin API, so deletion/anonymization must keep the viewer truthful and non-breaking.

### Knowledge Vault / RAG

- `app/routers/vault.py` already supports list, download, semantic search, process-for-RAG, and delete flows for user-owned vault documents.
- `frontend/src/components/vault/VaultInterface.tsx` is the active user-facing surface rendered by `frontend/src/app/dashboard/vault/page.tsx`.
- `frontend/src/app/api/vault/search/route.ts` and `frontend/src/app/api/vault/process/route.ts` authenticate the Supabase session but currently call the backend without an `Authorization: Bearer ...` header.
- `app/rag/knowledge_vault.py`, `app/rag/search_service.py`, and `app/rag/ingestion_service.py` already implement the core ingestion/search path that Phase 56 should harden rather than replace.
- Existing automated coverage is present but shallow:
  - `tests/unit/test_rag_services.py`
  - `tests/integration/test_rag_services.py`
  - `tests/integration/test_knowledge_vault.py`

</code_context>

<deferred>
## Deferred Ideas

- Legal-hold workflows, retention-policy editing, or admin DSAR operations dashboards
- Hybrid retrieval/reranking experiments beyond what is needed to satisfy the current relevance threshold
- Rich OCR/vision transcription for every media format if a truthful “storage-only” fallback is sufficient for v7

</deferred>

---

*Phase: 56-gdpr-rag-hardening*
*Context gathered: 2026-04-11*
