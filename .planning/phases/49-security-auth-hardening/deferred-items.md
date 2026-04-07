# Phase 49 — Deferred Items

Out-of-scope discoveries logged during plan execution. These are NOT fixed by phase 49 plans because they pre-exist the plan's scope. Address in a dedicated cleanup phase or as part of the file owner's next touch.

## Discovered during 49-02 (RootErrorBoundary wiring)

**Pre-existing frontend lint debt — 287 problems (147 errors, 140 warnings)**

`cd frontend && npm run lint -- --max-warnings=0` reports 287 problems across the codebase. None of them touch files modified by plan 49-02; all four files created/modified in this plan (`RootErrorBoundary.tsx`, root `layout.tsx`, `(personas)/layout.tsx`, the new test) lint clean individually with `--max-warnings=0`.

Concentrated areas (not exhaustive — sampled from lint output):
- `src/services/workflows.ts` — ~22 `@typescript-eslint/no-explicit-any` errors
- `src/services/initiatives.ts` — `no-explicit-any`
- `src/services/widgetDisplay.ts` — `no-explicit-any`, unused imports
- `src/services/api.ts` — unused vars
- `src/services/app-builder.ts` — unused imports
- Hooks, contexts, components, lib — assorted `no-unused-vars`, `no-explicit-any`, `react-hooks/exhaustive-deps`

**Why deferred:** SCOPE BOUNDARY rule — only fix issues directly caused by current task changes. These are pre-existing and would balloon plan 49-02 from a 2-task error-boundary plan into a multi-day codebase-wide type cleanup.

**Suggested follow-up:** Create a dedicated plan in a future hardening phase (e.g. 49-LATE or v7.5 cleanup) titled "Frontend lint debt zero-out" that runs `eslint --fix` for autofixable warnings, then migrates remaining `any` usages to `unknown` + type guards.

## Discovered during 49-04 (AuditLogMiddleware wiring)

**Pre-existing local `.env` file is not UTF-8 — breaks all unit tests that import `app.fast_api_app` on Windows**

The project root `.env` contains UTF-8 box-drawing characters (`─`, `┐`, `│`) at byte offset ~2451 — likely from a TUI table that was pasted into the file. `slowapi.Limiter()` (called at module-import time inside `app/middleware/rate_limiter.py:211`) eventually invokes `starlette.config.Config(env_file=...)` which uses Python's default (cp1252 on Windows) encoding to read `.env`. Result: any unit test that does `from app.fast_api_app import app` raises `UnicodeDecodeError: 'charmap' codec can't decode byte 0x90` and fails collection.

This affects existing tests too — verified `tests/unit/app/routers/test_initiatives.py` raises the same error in this dev environment.

**Impact on plan 49-04:** the new `test_audit_log_middleware_registered_in_real_app` regression test is wrapped in a `try/except → pytest.skip` guard so it doesn't fail collection on broken envs. In a clean environment (CI, Docker, or after the .env is fixed) the test runs and asserts the middleware is registered. Locally on Windows with the binary `.env`, it skips with a clear message.

**Why deferred:** SCOPE BOUNDARY rule — fixing `.env` encoding is unrelated to AUTH-04 audit middleware. It is also a per-developer environment issue (the file is `.gitignore`'d), not a code defect.

**Suggested follow-ups:**
1. Patch the local `.env` to remove the binary block (file owner action — not committable since `.env` is gitignored).
2. File a slowapi/starlette upstream fix to read env files as UTF-8 explicitly.
3. As a defence-in-depth measure, add `encoding="utf-8"` handling in a wrapper around `Config()` in `app/middleware/rate_limiter.py` so the same crash cannot happen on production Windows hosts.

## Discovered during 49-03 (teams_rbac sibling router + role label reconciliation)

**Pre-existing frontend test suite failures — 22 test files / 54 individual tests fail on a clean run**

`cd frontend && npm test -- --run` reports 22 failed test files (54 tests) and 37 passed (356 tests). None of the failures involve `team/RoleDropdown`, `team/TeamMemberList`, or `dashboard/team/page` — they are all in unrelated modules:

- `__tests__/components/ProtectedRoute.test.tsx` — supabase auth mock returns `undefined`
- `__tests__/contexts/SessionControlContext.test.tsx` — fetch mocking issues
- `__tests__/pages/*Page.test.tsx` — Next.js router mock failures (Login, Signup, Settings, ResetPassword, ForgotPassword)
- `src/components/chat/ChatInterface.test.tsx`, `src/components/chat/SessionList.test.tsx` — chat fixture drift
- `src/__tests__/services/initiatives.test.ts`, `src/__tests__/departments.page.test.tsx` — service shape drift
- `src/lib/chatMetadata.test.ts` — metadata extraction regression
- `__tests__/auth.test.ts` — supabase v2 OAuth signature drift

**Why deferred:** SCOPE BOUNDARY rule — none of these tests cover `team/*` files modified by plan 49-03. The frontend test corpus has visibly drifted from current source (multiple Next.js + supabase-js major-version bumps since these tests were written). My added changes pass ESLint with `--max-warnings=0` and TypeScript clean on the touched files.

**Pre-existing TypeScript error in dashboard/team/page.tsx (unrelated to my changes):**
- Line 463: `role === 'owner'` — `WorkspaceRole` type is `'admin' | 'editor' | 'viewer' | null`, no `'owner'` literal. The comparison was on line 456 in HEAD before my changes (verified via `git show HEAD:`); I only shifted it down 7 lines by adding an explanatory comment block.

**Suggested follow-up:** Schedule a "Frontend test corpus refresh" plan in v7.5 cleanup to: (1) re-baseline the supabase auth mocks, (2) update Next.js router mock harnesses, (3) add the missing `'owner'` literal to `WorkspaceRole` type or remove the dead branch in team/page.tsx.

**Pre-existing lint debt in `app/fast_api_app.py` (E402 + I001 import-block issues):**
- Baseline pre-change: 76 ruff errors in fast_api_app.py
- Post-change: 78 errors (1 new E402 from the `teams_rbac_router` import line — same pattern as every other import in the section, all already E402)
- The I001 sort error is pre-existing and unrelated to my insertion

**Why deferred:** Every router import in `fast_api_app.py` lines ~872-917 is already E402 because they come after `app = FastAPI(...)`. Refactoring would require restructuring app construction.

## Discovered during 49-05 (Admin governance audit log viewer)

**Pre-existing Node heap OOM on full-project `npm run lint` and `npm run build` (Windows)**

Running `cd frontend && npm run lint -- --max-warnings=0` crashes with `FATAL ERROR: Zone Allocation failed - process out of memory` after ~30s. Running `cd frontend && npm run build` (Next.js 16.1.4 Turbopack) crashes with `FATAL ERROR: CALL_AND_RETRY_LAST Allocation failed - JavaScript heap out of memory` even with `NODE_OPTIONS=--max-old-space-size=8192`. The failures are pre-existing and NOT caused by plan 49-05's two new frontend files.

**Scoped verification used instead** (passes cleanly):
- `npx eslint "src/app/(admin)/audit-log/governance/page.tsx" "src/components/admin/GovernanceAuditTable.tsx" --max-warnings=0` — exit 0, zero warnings
- `npx tsc --noEmit -p tsconfig.json` filtered for the two new files — zero type errors

**Why deferred:** SCOPE BOUNDARY rule — fixing Turbopack/Node heap exhaustion on Windows is a toolchain/environment issue wholly unrelated to AUTH-05. The Turbopack Windows memory regression is known upstream in Next.js 16.x.

**Suggested follow-ups:**
1. File/track an upstream Next.js issue for Turbopack memory footprint on Windows >= 16.1.4.
2. In CI (Linux containers) the full `npm run build` is expected to pass — this is a local-dev Windows-only blocker.
3. As a dev-UX workaround, add a `lint:changed` script that runs eslint on `git diff --name-only` files so contributors can verify their own touches without OOM.
