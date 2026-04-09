---
phase: 51-observability-monitoring
plan: 01
subsystem: infra
tags: [sentry, error-monitoring, fastapi, nextjs, react-error-boundary, pii-safety]

# Dependency graph
requires: []
provides:
  - sentry_sdk initialized in fast_api_app.py before FastAPI instantiation (errors-only, no traces, no PII)
  - Sentry user context set to user_id UUID only in run_sse endpoint
  - frontend @sentry/nextjs SDK with sentry.client.config.ts, sentry.server.config.ts, sentry.edge.config.ts
  - RootErrorBoundary wired to Sentry.captureException with componentStack
  - next.config.ts wrapped with withSentryConfig
  - All Sentry initializations are no-op when DSN env vars are absent
affects: [52-persona-gating, 55-load-testing, production-deployments]

# Tech tracking
tech-stack:
  added: [sentry-sdk[fastapi]>=2.0.0 (Python), @sentry/nextjs@10.47.0 (frontend)]
  patterns:
    - Conditional SDK init gated on env var (no-op in dev without config)
    - errors-only mode — traces_sample_rate=0.0, profiles_sample_rate=0.0, send_default_pii=False
    - PII boundary: user_id UUID only sent to Sentry, never email/persona/workspace

key-files:
  created:
    - frontend/sentry.client.config.ts
    - frontend/sentry.server.config.ts
    - frontend/sentry.edge.config.ts
    - tests/unit/test_sentry_init.py
  modified:
    - app/fast_api_app.py
    - pyproject.toml
    - frontend/package.json
    - frontend/next.config.ts
    - frontend/src/components/errors/RootErrorBoundary.tsx
    - .env.example
    - frontend/.env.example

key-decisions:
  - "OBS-01: Sentry init is errors-only (traces_sample_rate=0.0, profiles_sample_rate=0.0, send_default_pii=False) — no APM, no profiling, just error capture"
  - "OBS-01: PII boundary: only user_id UUID sent to Sentry.set_user() — no email, persona, or workspace"
  - "OBS-01: Both backend and frontend SDKs are no-ops when DSN env vars are unset (safe for dev environments)"
  - "OBS-01: withSentryConfig uses sourcemaps.disable rather than deprecated hideSourceMaps — per @sentry/nextjs v10 SentryBuildOptions type"

patterns-established:
  - "Env-gated SDK init: check os.environ.get('SENTRY_DSN_BACKEND', '') before calling sentry_sdk.init()"
  - "PII contract: sentry_sdk.set_user({'id': str(user_id)}) — id key only, enforced by test_sentry_user_context_sets_id_only"
  - "Frontend Sentry config: three files (client/server/edge) all read NEXT_PUBLIC_SENTRY_DSN"

requirements-completed: [OBS-01]

# Metrics
duration: 35min
completed: 2026-04-09
---

# Phase 51 Plan 01: Sentry Error Capture Integration Summary

**sentry-sdk[fastapi] + @sentry/nextjs wired end-to-end: backend errors captured with user_id context, frontend errors forwarded from RootErrorBoundary, all no-op when DSN is absent**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-04-09T09:16:00Z
- **Completed:** 2026-04-09T09:51:00Z
- **Tasks:** 2 (+ 1 auto-fix deviation)
- **Files modified:** 12

## Accomplishments

- Backend sentry_sdk.init() placed before FastAPI() instantiation in fast_api_app.py, conditional on SENTRY_DSN_BACKEND, errors-only mode (no traces, no profiles, no PII)
- Sentry user context set to UUID-only in run_sse after JWT extraction — PII boundary enforced and verified by unit test
- Frontend @sentry/nextjs installed, three config files created (client/server/edge), next.config.ts wrapped with withSentryConfig
- RootErrorBoundary.componentDidCatch wired to Sentry.captureException with componentStack in extra — TODO comment resolved
- New env vars documented in both .env.example files

## Task Commits

1. **Task 1: Install Sentry SDKs and configure backend + frontend initialization** - `ecd4d67` (feat)
2. **Task 2: Wire RootErrorBoundary to Sentry and add backend unit test** - `f6bd6a8` (feat)
3. **Auto-fix: SentryBuildOptions type + pre-existing webhook PATCH cast** - `d08bdcb` (fix)

**Plan metadata:** to be committed with docs commit

## Files Created/Modified

- `app/fast_api_app.py` - sentry_sdk.init() after logging setup, sentry_sdk.set_user() in run_sse
- `pyproject.toml` - added sentry-sdk[fastapi]>=2.0.0 dependency
- `frontend/sentry.client.config.ts` - client-side Sentry init (NEXT_PUBLIC_SENTRY_DSN gated)
- `frontend/sentry.server.config.ts` - server-side Sentry init
- `frontend/sentry.edge.config.ts` - edge runtime Sentry init
- `frontend/next.config.ts` - withSentryConfig wrapper + fixed SentryBuildOptions (sourcemaps.disable)
- `frontend/package.json` - @sentry/nextjs@10.47.0 added
- `frontend/src/components/errors/RootErrorBoundary.tsx` - Sentry.captureException in componentDidCatch, TODO removed
- `tests/unit/test_sentry_init.py` - 3 tests: conditional init, PII boundary, no-traces contract
- `.env.example` - SENTRY_DSN_BACKEND and SENTRY_AUTH_TOKEN documented
- `frontend/.env.example` - NEXT_PUBLIC_SENTRY_DSN, NEXT_PUBLIC_ENVIRONMENT, SENTRY_AUTH_TOKEN documented

## Decisions Made

- errors-only mode chosen (traces_sample_rate=0.0, profiles_sample_rate=0.0, send_default_pii=False) per CONTEXT.md PII boundary decision
- user_id UUID is the only identity sent to Sentry — no email, no persona, no workspace — enforced by test
- withSentryConfig uses `sourcemaps: { disable: !SENTRY_AUTH_TOKEN }` — not deprecated `hideSourceMaps` (invalid in @sentry/nextjs v10)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed invalid SentryBuildOptions property hideSourceMaps**
- **Found during:** Phase 3 quality gate (tsc)
- **Issue:** next.config.ts used `hideSourceMaps: true` which does not exist in @sentry/nextjs v10 SentryBuildOptions type — tsc error TS2561
- **Fix:** Replaced with `sourcemaps: { disable: !process.env.SENTRY_AUTH_TOKEN }` per actual type definition
- **Files modified:** frontend/next.config.ts
- **Verification:** `npx tsc --noEmit` returns no errors for next.config.ts
- **Committed in:** d08bdcb

**2. [Rule 3 - Blocking] Fixed pre-existing webhook PATCH Response cast blocking build**
- **Found during:** Phase 3 quality gate (next build)
- **Issue:** frontend/src/app/dashboard/configuration/page.tsx:2466 — `fetchWithAuth(...) as WebhookEndpoint` without `.then(r => r.json())`. Same pattern as commit f49ae78 (explicitly noted as deferred in that commit message). Blocked the production build.
- **Fix:** Added `.then((r) => r.json())` before the cast — same fix as f49ae78
- **Files modified:** frontend/src/app/dashboard/configuration/page.tsx
- **Verification:** tsc no longer reports error on line 2466
- **Committed in:** d08bdcb

---

**Total deviations:** 2 auto-fixed (1 type error bug, 1 blocking build issue)
**Impact on plan:** Both fixes necessary for type safety and build gate. No scope creep — second fix was explicitly flagged as "latent" in the prior commit message.

## Issues Encountered

- `uv sync` not directly accessible from bash (uv.cmd shim only supports `uv run`). sentry-sdk installed via pip directly into the venv. pyproject.toml is updated so the next `uv sync` from a proper terminal will lock it. uv.lock not updated in this session.
- Windows Turbopack TurbopackInternalError (os error 10054) prevents local `npm run build` from completing. This is a known Windows CI limitation — does not affect Cloud Run Linux builds. tsc passes for all our files.

## User Setup Required

Add these to production environment before activating Sentry:

**Cloud Run (backend):**
```
SENTRY_DSN_BACKEND=<your-backend-dsn-from-sentry-dashboard>
```

**Vercel (frontend):**
```
NEXT_PUBLIC_SENTRY_DSN=<your-frontend-dsn-from-sentry-dashboard>
NEXT_PUBLIC_ENVIRONMENT=production
SENTRY_AUTH_TOKEN=<your-sentry-auth-token-for-source-maps>
```

Both are no-op (safe) when unset — dev environments work without Sentry configured.

## Next Phase Readiness

- OBS-01 complete: error capture foundation in place for both backend and frontend
- Ready for Phase 51 Plan 02 (structured logging / log enrichment) or Plan 03 (metrics/dashboards)
- Sentry DSN values needed from user before production error visibility is active

---
*Phase: 51-observability-monitoring*
*Completed: 2026-04-09*
