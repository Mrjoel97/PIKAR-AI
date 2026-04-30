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
