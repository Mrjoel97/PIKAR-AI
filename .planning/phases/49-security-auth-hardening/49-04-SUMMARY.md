---
phase: 49-security-auth-hardening
plan: 04
subsystem: auth
tags: [audit-log, fastapi, asgi-middleware, governance, rbac, supabase]

# Dependency graph
requires:
  - phase: enterprise-governance
    provides: GovernanceService.log_event() and governance_audit_log table (already write-fault-tolerant)
  - phase: 49-security-auth-hardening
    provides: AUTH-03 RBAC role assignment surface (audited via /teams prefix)
provides:
  - Centralised AuditLogMiddleware ASGI class wired into the real FastAPI app
  - 34-entry AUDITED_ROUTES inclusion list (initiatives, workflows, content, campaigns, reports, vault, integrations, briefing, pages, community, finance, sales, support, compliance, learning, api_credentials, byok, journeys, ad_approvals, email_sequences, files, onboarding, teams, governance, account, configuration, data_io, departments, kpis, monitoring_jobs, outbound_webhooks, self_improvement, workflow_triggers, app_builder)
  - Hard-exclusion list (/health, /a2a, /admin, /webhooks, /auth, /docs, /openapi.json, /redoc) so the audit log never includes health checks, agent SSE chat, admin actions (which already flow to the separate admin_audit_log), inbound webhooks, or auth flows
  - action_type naming convention `{resource_type}.{verb}` where verb ∈ {created, updated, deleted}
  - Fire-and-forget background insert via asyncio.create_task with strong-ref tracking (RUF006-safe)
  - Parametrised regression test that iterates EVERY AUDITED_ROUTES entry (34 subtests) — catches typos and silent drops in the inclusion list
  - Middleware-stack assertion test (and source-inspection backup) proving AuditLogMiddleware is registered AFTER OnboardingGuardMiddleware in the real app
affects:
  - 49-05 (AUTH-05): admin governance audit viewer reads from this exact governance_audit_log row shape and uses AUDITED_ROUTES values to populate the resource_type filter dropdown
  - All future user-facing routers: any new prefix added later must be appended to AUDITED_ROUTES to start producing audit rows
  - 50-billing: subscription mutation endpoints will be audited automatically once registered under one of the audited prefixes

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Centralised ASGI middleware over per-handler decorators (one place to maintain coverage; new handlers automatically inherit auditing)
    - Inclusion list (allow-list) NOT exclusion list — new routers stay un-audited until explicitly added (safe default)
    - Fire-and-forget asyncio.create_task with module-level strong-ref set so background task is not garbage-collected (RUF006)
    - NEVER-raises contract on observability middleware — try/except around the entire dispatch body, errors logged at ERROR level and swallowed
    - Parametrised regression test over the configuration map itself (one subtest per entry) to catch silent typos
    - Middleware-stack order assertion test imports the real app and introspects app.user_middleware

key-files:
  created:
    - app/middleware/audit_log.py
    - tests/unit/app/middleware/test_audit_log_middleware.py
    - tests/integration/middleware/test_audit_log_e2e.py
  modified:
    - app/fast_api_app.py

key-decisions:
  - "AUDITED_ROUTES is an explicit allow-list of 34 router prefixes — new routers stay un-audited until added. Safer than an exclusion list, which would silently start logging new endpoints."
  - "action_type follows {resource_type}.{verb} convention (e.g. initiative.created, workflow.deleted) so plan 49-05 admin viewer can derive filter values directly from AUDITED_ROUTES.values() without hardcoding."
  - "details JSONB shape is fixed: {method, path, status_code} — the admin viewer will surface these fields verbatim. Resource bodies are NEVER read because doing so would break SSE responses and large downloads."
  - "Audit insert is fire-and-forget via asyncio.create_task with strong-ref set tracking — request flow is never blocked on the audit write."
  - "Middleware NEVER raises — entire dispatch body is wrapped in try/except. Audit failures are logged at ERROR and swallowed so an audit-system outage cannot break the user-facing request flow."
  - "/admin/* is hard-excluded — admin actions are already audited via app/services/admin_audit.py to a separate admin_audit_log table (Phase 7 separation), and double-logging would create duplicate trails."
  - "Resource_id extraction is best-effort — first path segment after the matched prefix. Collection routes (POST /initiatives) get resource_id=None. Nested routes (PATCH /initiatives/abc-123/checklist/item-1) get resource_id=abc-123, the parent resource."
  - "Middleware registered AFTER OnboardingGuardMiddleware so it WRAPS the inner stack and observes the final response status code while inheriting the request_id from RequestLoggingMiddleware. Asserted by test_audit_log_middleware_registered_in_real_app + source-inspection backup."
  - "Anonymous requests (no/invalid Bearer token) DO NOT produce audit rows — there is no actor to record. Verified by test_anonymous_request_does_not_log."
  - "Only successful 2xx responses produce audit rows — 4xx and 5xx are skipped because the action did not succeed. Verified by test_failed_4xx and test_failed_5xx."

patterns-established:
  - "Centralised middleware over per-handler decorator: when coverage must scale with router count, ASGI middleware is preferred over per-endpoint instrumentation."
  - "Allow-list configuration with parametrised regression test: every entry in a configuration map gets one auto-generated subtest, so typos and silent drops fail loudly."
  - "Fire-and-forget background tasks must use module-level strong-ref tracking (RUF006) — store the task handle in a set with task.add_done_callback(set.discard)."
  - "Observability middleware NEVER raises: wrap the entire dispatch body in try/except, log errors at ERROR, and return the original response untouched."
  - "Middleware-stack order is part of the contract: assert it via a regression test that imports the real app and introspects user_middleware (with a source-inspection backup for environments where importing the app crashes)."

requirements-completed: [AUTH-04]

# Metrics
duration: 13min
completed: 2026-04-07
---

# Phase 49 Plan 04: AuditLogMiddleware Summary

**Centralised FastAPI ASGI middleware that auto-audits successful 2xx mutations on 34 user-facing router prefixes to governance_audit_log, replacing ~26 routers' worth of missing audit coverage with a single fire-and-forget background insert.**

## Performance

- **Duration:** 13 min (3 commits across 3:55–4:08 UTC+3)
- **Started:** 2026-04-07T00:55:22Z
- **Completed:** 2026-04-07T01:08:05Z
- **Tasks:** 3 (TDD red+green for middleware, registration + stack-order test, e2e integration smoke tests)
- **Files modified:** 4 (1 production module, 1 app entry, 2 test files)

## Accomplishments

- AuditLogMiddleware closes the AUTH-04 audit-coverage gap from ~4/30 routers (manual log_event calls in initiatives/teams/workflows/governance) to centralised coverage of 34 user-facing router prefixes — every new POST/PUT/PATCH/DELETE on an audited prefix produces a governance_audit_log row automatically with no per-handler instrumentation.
- 47 unit tests in tests/unit/app/middleware/test_audit_log_middleware.py: 13 case-based tests cover the full happy path, exclusion list, never-raises contract, anonymous requests, and failed responses; a parametrised regression test produces 34 subtests (one per AUDITED_ROUTES entry) that catch silent typos in the inclusion list.
- 3 e2e integration smoke tests in tests/integration/middleware/test_audit_log_e2e.py prove the exact governance_audit_log row shape that plan 49-05 (AUTH-05 admin viewer) will read back: user_id from JWT, action_type as `{resource_type}.{verb}`, resource_id extracted from URL, details {method, path, status_code}.
- Middleware-stack registration and ordering is asserted by both a runtime introspection test (test_audit_log_middleware_registered_in_real_app, skipped on Windows due to a pre-existing binary `.env` issue documented in deferred-items.md) and a source-inspection backup (test_audit_log_middleware_registered_via_source_inspection) so coverage holds even when the runtime import fails.

## Task Commits

Each task was committed atomically:

1. **Task 1: AuditLogMiddleware ASGI class + parametrised AUDITED_ROUTES coverage** - `3f38003` (feat)
   - 343 lines in app/middleware/audit_log.py
   - 550 lines of unit tests (13 case-based + 34 parametrised subtests)
2. **Task 2: Register AuditLogMiddleware in FastAPI app + middleware-stack assertion test** - `5f166fa` (feat)
   - Stack-order assertion test (runtime import + source-inspection backup)
   - Logged binary `.env` UnicodeDecodeError as a deferred Windows-only environment issue
3. **Task 3: End-to-end smoke tests against governance_audit_log row shape** - `138c38c` (test)
   - 3 e2e tests pinning the exact contract Plan 49-05 will read

**Plan metadata:** completion commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS update).

## Files Created/Modified

- `app/middleware/audit_log.py` — Centralised ASGI middleware: AuditLogMiddleware class, AUDITED_ROUTES inclusion list (34 prefixes), _EXCLUDED_PREFIXES tuple, _resolve_resource_type/_extract_resource_id/_resolve_actor helpers, fire-and-forget _fire_log_event background task, _BACKGROUND_TASKS strong-ref set
- `app/fast_api_app.py` — Imports AuditLogMiddleware and registers it via `app.add_middleware(AuditLogMiddleware)` AFTER OnboardingGuardMiddleware in the user_middleware stack
- `tests/unit/app/middleware/test_audit_log_middleware.py` — 13 case-based + 34 parametrised regression subtests + stack-order assertion test + source-inspection backup test
- `tests/integration/middleware/test_audit_log_e2e.py` — 3 e2e smoke tests proving the governance_audit_log row shape for POST/DELETE/PUT mutations

## Decisions Made

- **Allow-list over exclusion list (AUDITED_ROUTES inclusion):** Safer because new routers added in future phases stay un-audited until explicitly registered. An exclusion list would silently start auditing new endpoints with no schema review.
- **action_type = `{resource_type}.{verb}`:** Plan 49-05 admin viewer can derive filter dropdown values directly from `AUDITED_ROUTES.values()` and `["created","updated","deleted"]` without hardcoding.
- **Fixed details shape `{method, path, status_code}`:** Avoids reading response bodies (which would break SSE and large downloads) while still giving the admin viewer enough request metadata to render meaningful audit rows.
- **Fire-and-forget asyncio.create_task with strong-ref tracking:** Audit insert never blocks the response. RUF006-safe via module-level _BACKGROUND_TASKS set.
- **NEVER-raises contract enforced by try/except wrapping the entire dispatch body:** Defence-in-depth on top of GovernanceService.log_event's own internal try/except. Audit failures are logged at ERROR and swallowed.
- **/admin/* hard-excluded:** Admin actions already flow through app/services/admin_audit.py to a separate admin_audit_log table (Phase 7 separation). Double-logging would create duplicate audit trails.
- **Middleware registered AFTER OnboardingGuardMiddleware:** ASGI middleware is inside-out, so the LAST add_middleware call WRAPS the inner stack. Audit logging happens on the way out, after auth + onboarding guards have done their work and the route handler has produced a status code.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Source-inspection backup test for middleware-stack assertion**
- **Found during:** Task 2 (stack-order assertion test)
- **Issue:** The runtime introspection test (`test_audit_log_middleware_registered_in_real_app`) imports `app.fast_api_app.app`, which triggers `slowapi.Limiter()` → `starlette.config.Config(env_file=".env")`. On Windows, the project root `.env` contains UTF-8 box-drawing characters at byte ~2451 that cp1252 cannot decode, raising UnicodeDecodeError at test-collection time. This blocks running the assertion test locally.
- **Fix:** Added a second test, `test_audit_log_middleware_registered_via_source_inspection`, that statically reads `app/fast_api_app.py` and asserts the AuditLogMiddleware import + add_middleware lines are present in the correct order, even when the runtime import fails. The runtime test wraps its import in a try/except → pytest.skip so it runs in CI/Docker but skips cleanly on broken-env machines.
- **Files modified:** tests/unit/app/middleware/test_audit_log_middleware.py
- **Verification:** Both tests pass; on Windows the runtime test skips and the source-inspection backup passes (covered)
- **Committed in:** 5f166fa (Task 2 commit)

**2. [Out of scope - deferred] Binary `.env` file UnicodeDecodeError**
- **Found during:** Task 2 (running the new test against the real app)
- **Issue:** Pre-existing local `.env` contains UTF-8 box-drawing characters that crash starlette.config.Config() on Windows under cp1252. Affects ALL existing tests that import app.fast_api_app, not just the new ones.
- **Disposition:** Logged to `.planning/phases/49-security-auth-hardening/deferred-items.md` per SCOPE BOUNDARY rule. This is a per-developer environment issue (`.env` is gitignored) and unrelated to AUTH-04. Suggested follow-ups documented in deferred-items.md (patch local `.env`, file slowapi upstream issue, add UTF-8 wrapper around Config()).
- **Files modified:** .planning/phases/49-security-auth-hardening/deferred-items.md (entry added)
- **Committed in:** 5f166fa (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 blocking) + 1 deferred out-of-scope item
**Impact on plan:** No scope creep. The source-inspection backup test is a pure addition that hardens the assertion under broken-env conditions; the deferred `.env` issue is documented for future cleanup and does not block AUTH-04 from shipping.

## Issues Encountered

- **Test environment binary `.env` blocking real-app import on Windows:** Resolved via skip-guard + source-inspection backup test. See deviation #1 above.
- **Final test run on this machine:** All 51 tests pass (50 PASSED + 1 SKIPPED for the runtime introspection test that requires a clean import environment). The source-inspection backup covers the assertion in both Windows local dev and CI.

## User Setup Required

None — no external service configuration required. The middleware uses the existing GovernanceService and Supabase service-role client; no new env vars, no new tables, no new credentials.

## Next Phase Readiness

- **Plan 49-05 (AUTH-05) admin viewer is unblocked.** It can read from `governance_audit_log` filtered by `user_id`, `action_type`, `resource_type`, and `created_at` ranges, populating the action_type filter dropdown directly from `AUDITED_ROUTES.values()` × `["created","updated","deleted"]`.
- **Plan 49-01 (AUTH-01)** is the only AUTH-* requirement still pending in Phase 49. AUTH-04 ships independently.
- **Concern:** Production rollout should monitor governance_audit_log row growth — 34 prefixes × 100-user beta × ~10 mutations/user/day = ~34k rows/day at peak. Add an index on `(user_id, created_at DESC)` and `(action_type, created_at DESC)` before plan 49-05 ships its admin viewer query layer (likely already present from the enterprise governance migration; verify in plan 49-05 task 1).

---
*Phase: 49-security-auth-hardening*
*Completed: 2026-04-07*

## Self-Check: PASSED

- FOUND: app/middleware/audit_log.py (343 lines)
- FOUND: tests/unit/app/middleware/test_audit_log_middleware.py (664 lines)
- FOUND: tests/integration/middleware/test_audit_log_e2e.py (153 lines)
- FOUND: app/fast_api_app.py (AuditLogMiddleware import on line 324, registration on line 807)
- FOUND: commit 3f38003 (feat: add AuditLogMiddleware with parametrised AUDITED_ROUTES coverage)
- FOUND: commit 5f166fa (feat: register AuditLogMiddleware in FastAPI app + stack-order tests)
- FOUND: commit 138c38c (test: add e2e integration smoke tests for AuditLogMiddleware)
- VERIFIED: 51 tests collected, 50 passed, 1 skipped (runtime real-app introspection — source-inspection backup passed)
