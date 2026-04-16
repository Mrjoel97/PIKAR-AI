---
phase: 55
slug: integration-quality-load-testing
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-11
---

# Phase 55 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + vitest + TypeScript + Locust/report scripts |
| **Config file** | `pyproject.toml`, `frontend/vitest.config.mts`, `frontend/tsconfig.json` |
| **Quick run command** | `uv run pytest tests/unit/test_integration_manager.py tests/unit/app/test_google_workspace_auth_service.py tests/integration/test_sse_endpoint.py -x && cd frontend && npm run test -- __tests__/hooks/useBackgroundStream.test.ts && npx tsc -p . --noEmit` |
| **Full suite command** | `uv run pytest tests/unit/test_integration_manager.py tests/unit/app/test_google_workspace_auth_service.py tests/integration/test_sse_endpoint.py tests/unit/test_sse_connection_limits.py tests/unit/test_thread_pool_and_supabase_pool.py -x && cd frontend && npm run test -- __tests__/hooks/useBackgroundStream.test.ts && npx tsc -p . --noEmit` |
| **Estimated runtime** | ~80 seconds before any live Locust run |

---

## Sampling Rate

- **After every task commit:** Run the narrowest owning pytest/vitest command for that task.
- **After every plan wave:** Run the quick run command plus any new load-harness self-check script.
- **Before `$gsd-verify-work`:** Full suite must be green and the staging load-test command must be documented and runnable on demand.
- **Max feedback latency:** 80 seconds for code-only checks.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 55-01-01 | 01 | 1 | INTG-01 | unit | `uv run pytest tests/unit/test_integration_manager.py -k delete_credentials -x` | ✅ | ✅ green |
| 55-01-02 | 01 | 1 | INTG-01 | unit | `uv run pytest tests/unit/app/test_google_workspace_auth_service.py -x` | ✅ | ✅ green |
| 55-02-01 | 02 | 2 | INTG-02 | integration | `uv run pytest tests/integration/test_sse_endpoint.py -x` | ✅ | ✅ green |
| 55-02-02 | 02 | 2 | INTG-03 | component | `cd frontend && npm run test -- __tests__/hooks/useBackgroundStream.test.ts` | ✅ | ✅ green |
| 55-03-01 | 03 | 3 | LOAD-04 | script | `uv run python tests/load_test/report_assertions.py --help` | ✅ | ✅ green |
| 55-03-02 | 03 | 3 | LOAD-01, LOAD-02, LOAD-03 | documentation/script | `uv run python tests/load_test/report_assertions.py --input tests/load_test/.results/sample.csv --max-p95-ms 3000` | ✅ | ✅ green |
| 55-03-03 | 03 | 3 | LOAD-04 | typecheck | `cd frontend && npx tsc -p . --noEmit` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/load_test/report_assertions.py` — machine-readable pass/fail threshold evaluator for load-test artifacts
- [x] Any new backend/frontend isolation tests referenced by 55-02 are created before the final verification loop

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Provider connect → disconnect → reconnect cycle against live OAuth provider | INTG-01 | Requires real provider credentials and callback flow | Use a staging or local UI session to connect a provider, disconnect it, reconnect it, and confirm status clears stale errors between each step |
| 100-user staging load run produces acceptable p95 and no pool exhaustion | LOAD-01, LOAD-02, LOAD-03, LOAD-04 | Requires live staging environment and credentials | Run the documented Locust command against staging, then inspect the generated report and threshold output |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all new references
- [x] No watch-mode flags
- [x] Feedback latency < 80s for code-only loops
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (manual runtime UAT still pending for live provider reconnect and the 100-user staging run)
