# Phase 83 — Deferred Items

## Out-of-scope discoveries during Plan 01 execution

### 1. Pre-existing failure: `ChatInterface.test.tsx` (4 tests) crash with `useSessionControl must be used within a SessionControlProvider`

**Discovered:** Plan 01 Task 1 — running the plan's combined verification command revealed all 4 existing ChatInterface tests fail at render time.

**Root cause:** `ChatInterface.tsx` was modified (commit `bd1ccd5d` and earlier) to add 11 module-scope hooks including `useSessionControl()`, but `ChatInterface.test.tsx` only mocks `useAgentChat`. The test was written before the new hooks were added and was never updated. Running `npx vitest run src/components/chat/ChatInterface.test.tsx` on `main` (no Plan 01 changes) reproduces the exact same 4 failures.

**Why deferred:**
- The plan explicitly forbids modifying `ChatInterface.test.tsx` in Plan 01 (it is Plan 02's scope).
- Vitest hoists `vi.mock` calls per-file; the harness's mocks installed in `chatHarness.test.tsx` do NOT propagate to `ChatInterface.test.tsx`. The harness cannot fix nor regress this test.
- This is exactly the gap the harness was built to close. Plan 02 will adopt the harness inside `ChatInterface.test.tsx`, which will make all 4 existing tests pass.

**Mitigation:** Plan 02's first task should refactor `ChatInterface.test.tsx` to import and use `renderChatInterface` from `./__test-utils__/chatHarness`. Once that lands, all 4 existing tests will pass automatically because the harness installs every required hook stub.

**Verification reproducibility:** `git stash && cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx` shows the same 4 failures pre-Plan 01.

**Status:** Deferred to Plan 02. Not blocking Plan 01 completion — the harness itself works (4/4 harness tests green) and is the prerequisite for Plan 02 to fix this issue.

**RESOLVED in Plan 02 (2026-04-30):** Plan 02 adopted `renderChatInterface` from the harness inside `ChatInterface.test.tsx`. All 4 existing tests now pass. One assertion ("disables input when streaming") was stale against current production behavior and was rewritten to match the actual UX (streaming swaps Send for Stop button). See `83-02-document-upload-bypass-fix-SUMMARY.md` Deviations Rule 1 (#1) for the full justification.

---

## Out-of-scope discoveries during Plan 02 execution

### 2. Pre-existing failures in 21 unrelated test files (50 tests) — investigate in a follow-up cleanup pass

**Discovered:** Plan 02 Task 3 — running `cd frontend && npm test` (full suite) reports 50 failed tests across 21 files outside the chat folder.

**Root cause:** The dominant failure mode is `TypeError: supabase.auth.getUser is not a function` from `src/components/auth/ProtectedRoute.tsx:18`, originating in tests that mock `@/lib/supabase/client` but do not provide a `getUser` method. The chatHarness from Plan 01 does provide `getUser`, which is why ChatInterface tests work.

**Affected files:**
- `__tests__/components/ProtectedRoute.test.tsx` (2 tests)
- `__tests__/pages/ForgotPassword.test.tsx` (4 tests)
- `__tests__/pages/LoginPage.test.tsx` (2 tests)
- `__tests__/pages/ResetPassword.test.tsx` (4 tests)
- `__tests__/pages/SettingsPage.test.tsx` (6 tests)
- `__tests__/pages/SignupPage.test.tsx` (1 test)
- `__tests__/contexts/SessionControlContext.test.tsx` (2 tests)
- `src/components/chat/SessionList.test.tsx` (failures unclear; not ChatInterface)
- `src/__tests__/services/initiatives.test.ts`
- `src/__tests__/departments.page.test.tsx`
- `src/lib/chatMetadata.test.ts`
- ~10 more files

**Verification of pre-existing status:** Checked out `HEAD~2` (the parent commit before any Plan 02 changes) and ran `npx vitest run __tests__/components/ProtectedRoute.test.tsx` — same 2 failures with the same `supabase.auth.getUser is not a function` error. Confirmed pre-existing.

**Why deferred:** Per the deviation rules' SCOPE BOUNDARY, only auto-fix issues directly caused by the current task's changes. None of these failures are in files modified by Plan 02 (only `ChatInterface.tsx` and `ChatInterface.test.tsx` were touched).

**Recommended fix:** A small dedicated PR that either (a) extends each affected test file with a `getUser` stub in its `vi.mock('@/lib/supabase/client')` factory, or (b) creates a lightweight shared test fixture (similar to `chatHarness`) for any test that touches Supabase-auth-protected code paths.

**Status:** Out of scope for Phase 83. Recommended for the next `RETROSPECTIVE.md` cycle or a small dedicated PR.
