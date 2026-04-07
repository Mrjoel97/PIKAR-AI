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
