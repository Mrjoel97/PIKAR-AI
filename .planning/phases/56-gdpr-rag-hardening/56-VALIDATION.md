---
phase: 56
slug: gdpr-rag-hardening
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-11
---

# Phase 56 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + vitest + TypeScript + fixture-driven RAG eval script |
| **Config file** | `pyproject.toml`, `frontend/vitest.config.mts`, `frontend/tsconfig.json` |
| **Quick run command** | `uv run pytest tests/unit/services/test_personal_data_export_service.py tests/unit/app/routers/test_account_router.py tests/unit/services/test_document_text_extraction.py tests/unit/app/routers/test_vault_router.py -x && cd frontend && npm run test -- src/__tests__/services/vault-proxy.test.ts && npx tsc -p . --noEmit` |
| **Full suite command** | `uv run pytest tests/unit/services/test_personal_data_export_service.py tests/unit/app/routers/test_account_router.py tests/unit/services/test_document_text_extraction.py tests/unit/app/routers/test_vault_router.py tests/integration/test_account_deletion_cascade.py tests/integration/test_knowledge_vault.py tests/integration/test_rag_services.py -x && uv run python tests/rag/run_knowledge_vault_eval.py --dataset tests/eval_datasets/knowledge_vault_eval.json --min-relevance 0.8 --max-latency-ms 2000 && cd frontend && npm run test -- src/__tests__/services/vault-proxy.test.ts && npx tsc -p . --noEmit` |
| **Estimated runtime** | ~120 seconds for code-only checks; longer when local Supabase-backed integration coverage is included |

---

## Sampling Rate

- **After every task commit:** Run the narrowest owning pytest/vitest command for that task.
- **After every plan wave:** Run the quick run command plus any newly introduced script self-check.
- **Before `$gsd-verify-work`:** Full suite must be green and the RAG eval runner must produce a passing threshold report.
- **Max feedback latency:** 120 seconds for code-only loops.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 56-01-01 | 01 | 1 | GDPR-01 | unit | `uv run pytest tests/unit/services/test_personal_data_export_service.py -x` | ⬜ planned | ⬜ pending |
| 56-01-02 | 01 | 1 | GDPR-01 | router/typecheck | `uv run pytest tests/unit/app/routers/test_account_router.py -k export -x && cd frontend && npx tsc -p . --noEmit` | ⬜ planned | ⬜ pending |
| 56-02-01 | 02 | 2 | GDPR-02 | integration | `uv run pytest tests/integration/test_account_deletion_cascade.py -x` | ⬜ planned | ⬜ pending |
| 56-02-02 | 02 | 2 | GDPR-03 | unit/typecheck | `uv run pytest tests/unit/app/routers/test_account_router.py -k deletion -x && cd frontend && npx tsc -p . --noEmit` | ⬜ planned | ⬜ pending |
| 56-03-01 | 03 | 3 | RAG-01 | unit | `uv run pytest tests/unit/services/test_document_text_extraction.py tests/unit/app/routers/test_vault_router.py -x` | ⬜ planned | ⬜ pending |
| 56-03-02 | 03 | 3 | RAG-01 | component | `cd frontend && npm run test -- src/__tests__/services/vault-proxy.test.ts` | ⬜ planned | ⬜ pending |
| 56-04-01 | 04 | 4 | RAG-01, RAG-02 | script | `uv run python tests/rag/run_knowledge_vault_eval.py --dataset tests/eval_datasets/knowledge_vault_eval.json --min-relevance 0.8 --max-latency-ms 2000` | ⬜ planned | ⬜ pending |
| 56-04-02 | 04 | 4 | RAG-03 | integration | `uv run pytest tests/integration/test_knowledge_vault.py tests/integration/test_rag_services.py -k "concurrent or latency or search" -x` | ✅ partial | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/services/test_personal_data_export_service.py` exists before 56-01 closes.
- [ ] `tests/unit/services/test_document_text_extraction.py` and `tests/unit/app/routers/test_vault_router.py` exist before 56-03 closes.
- [ ] `tests/eval_datasets/knowledge_vault_eval.json` and `tests/rag/run_knowledge_vault_eval.py` exist before 56-04 closes.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| User triggers a full privacy export from Settings and downloads the generated archive | GDPR-01 | Requires real authenticated UI flow and signed download URL | Use a seeded user in local/staging, click the export action in Settings, download the archive, and verify that core domains are present while tokens/secrets are absent or redacted |
| User deletes an account and admin/governance views show anonymized history instead of broken actor references | GDPR-02, GDPR-03 | Requires real DB mutation plus admin viewer confirmation | Delete a non-production test account, then inspect `data_deletion_requests`, affected user-scoped tables, and the governance audit viewer for anonymized-but-still-readable history |
| Upload a PDF or DOCX in Knowledge Vault and confirm it becomes searchable through the user UI | RAG-01 | Requires real file upload + processing path | Upload a document through `VaultInterface`, trigger processing, then search for known phrases and confirm the returned result references the uploaded document |

---

## Validation Sign-Off

- [x] All planned tasks have an owning automated verification path
- [x] Sampling continuity is preserved across all 4 plans
- [x] Wave 0 artifacts are explicitly called out for the new tests/scripts
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved for execution planning; automated checks remain pending until the plan files are implemented
