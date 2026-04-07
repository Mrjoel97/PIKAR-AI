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
