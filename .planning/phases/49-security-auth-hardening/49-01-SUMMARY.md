---
phase: 49-security-auth-hardening
plan: 01
subsystem: auth
tags: [nextjs, nextjs-16, proxy, middleware, supabase-ssr, jwt, edge-runtime, vitest]

requires:
  - phase: 48-notification-event-type-wiring
    provides: v6.0 baseline (no auth enforcement at route layer)

provides:
  - Server-side Next.js 16 root proxy.ts gating protected routes before any HTML/RSC is streamed
  - Supabase SSR client factory (updateSession) that refreshes tokens and returns validated JWT claims
  - Vitest coverage for matcher logic and redirect behaviour (14 test cases)
  - PROTECTED_PREFIXES contract other plans in this phase can rely on as the canonical protected-route list

affects: [49-02-error-boundary, 49-03-workspace-rbac, 49-05-audit-viewer, 50-billing, 52-persona-gating, 53-multi-user-teams, 54-onboarding]

tech-stack:
  added: []
  patterns:
    - "Next.js 16 proxy.ts convention (renamed from middleware.ts) at project root sibling to package.json"
    - "Supabase getClaims() for JWKS-validated JWT checks in server contexts (never getSession() which trusts spoofable cookies)"
    - "Single-response-object reuse across the proxy flow so refreshed Set-Cookie headers survive transparent token rotation"
    - "Partial Vitest mock with importOriginal fallthrough + per-test overrides when the same module must be real in one suite and mocked in another"

key-files:
  created:
    - frontend/proxy.ts
    - frontend/src/lib/supabase/proxy.ts
    - frontend/__tests__/proxy.test.ts
  modified: []

key-decisions:
  - "File name MUST be proxy.ts (not middleware.ts) — Next.js 16 renamed the convention; the file lives at frontend/proxy.ts sibling to package.json"
  - "Use Supabase auth.getClaims() for JWT signature verification via JWKS on every call — getSession() trusts the raw cookie and can be spoofed in server-side contexts"
  - "Proxy runs updateSession() on EVERY matched request (not just protected ones) so downstream RSCs always see fresh tokens; redirect enforcement is scoped to PROTECTED_PREFIXES only"
  - "Keep frontend/src/components/auth/ProtectedRoute.tsx as a defense-in-depth client-side fallback — the proxy is the FIRST gate, ProtectedRoute is a second gate for any branch the proxy may not cover"
  - "Keep frontend/src/app/(admin)/layout.tsx's existing server-side getSession() check as a second gate behind the proxy — the proxy redirects unauthenticated /admin traffic before the admin layout runs /admin/check-access"
  - "Matcher excludes /api/*, /_next/static/*, /_next/image/*, favicon.ico, robots.txt, and static asset extensions so the Supabase round-trip never runs on asset fetches"
  - "updateSession() reads NEXT_PUBLIC_SUPABASE_URL/ANON_KEY at call-time (not module load) so the proxy always uses runtime env vars, never a build-time placeholder"

patterns-established:
  - "proxy.ts at project root: import updateSession from @/lib/supabase/proxy, call on every request, gate protected prefixes only"
  - "Supabase SSR proxy client: build cookie adapter from NextRequest/NextResponse (not next/headers which is unavailable in proxy runtime), mirror refreshed cookies to both request and response"
  - "Vitest partial mock for self-referencing modules: vi.mock(alias, async (importOriginal) => ({ ...await importOriginal(), override: controlled(fn) })) lets one test suite use the real implementation while another overrides per test"

requirements-completed: [AUTH-01]

duration: 14 min
completed: 2026-04-07
---

# Phase 49 Plan 01: Server-Side Proxy Route Protection Summary

**Next.js 16 root proxy.ts that gates protected routes via Supabase getClaims() JWT verification, redirecting unauthenticated traffic to /auth/login before any HTML or RSC payload is streamed.**

## Performance

- **Duration:** 14 min (initial session ~12 min interrupted mid-Task 2 GREEN + ~2 min continuation to finalise verify, mock-isolation fix, SUMMARY, and metadata commit)
- **Started:** 2026-04-07T04:42:00Z (approx — Task 1 RED commit at 04:43)
- **Completed:** 2026-04-07T04:57:00Z
- **Tasks:** 2 (both TDD: RED → GREEN)
- **Files created:** 3
- **Test cases:** 14 passing (5 updateSession + 9 proxy matcher/redirect)

## Accomplishments

- **Server-side route enforcement** — unauthenticated requests to `/dashboard`, `/settings`, `/admin`, and all persona routes now redirect to `/auth/login?next=<original-path>` at the proxy layer, BEFORE any protected page shell reaches the browser. Closes the largest production-readiness security gap: today's client-side `ProtectedRoute.tsx` renders page content first and then redirects, meaning unauthenticated visitors briefly saw protected page shells.
- **JWKS-verified JWT trust** — every gated request runs `supabase.auth.getClaims()` which validates the signature against the published JWKS, never trusting a raw cookie. Defends against spoofed `sb-*-auth-token` cookies in server-side contexts.
- **Transparent token refresh** — when the access token is expired, Supabase's SSR client silently refreshes via the `setAll()` cookie adapter callback. Refreshed cookies are mirrored to BOTH the inbound request (for downstream RSCs) and the outbound response (for the browser), with a single response object reused across the flow so `Set-Cookie` headers survive.
- **Narrow matcher** — excludes `/api/*`, `/_next/static/*`, `/_next/image/*`, `favicon.ico`, `robots.txt`, and common static asset extensions so the Supabase round-trip never runs on asset fetches.
- **14 passing Vitest cases** covering: Task 1 updateSession behaviour (no-cookie / valid-cookie / refresh / createServerClient invocation / env var wiring) and Task 2 proxy matcher + redirect (landing / auth / dashboard / settings / admin / personas / authenticated pass-through / api exclusion / _next exclusion).

## Task Commits

1. **Task 1 RED: Add failing test for Supabase SSR proxy client** — `d01b678` (test)
2. **Task 1 GREEN: Implement Supabase SSR proxy client with token refresh** — `fd9a868` (feat)
3. **Task 2 RED: Add failing tests for root proxy matcher and redirect** — `4b9251d` (test)
4. **Task 2 GREEN: Implement root proxy.ts matcher and redirect logic** — `50691d1` (feat) — also carries the Rule 1 auto-fix for the test-isolation bug introduced in commit 4b9251d

**Plan metadata:** pending final commit after SUMMARY creation

## Files Created/Modified

- **`frontend/proxy.ts`** (100 lines) — Next.js 16 root proxy entry point. Declares the `PROTECTED_PREFIXES` list, exports `proxy(request)` which runs `updateSession()` on every matched request and issues `NextResponse.redirect('/auth/login?next=<path>')` when `isProtected(pathname) && !claims`, exports `config.matcher` to exclude API and asset routes.
- **`frontend/src/lib/supabase/proxy.ts`** (92 lines) — Supabase SSR client factory. Exports `updateSession(request)` returning `{ response, claims }`. Reads env vars at call-time (not module load). Uses `getClaims()` for JWKS validation. Mirrors refreshed cookies to both request and response so token rotation is transparent to the browser.
- **`frontend/__tests__/proxy.test.ts`** (276 lines) — Vitest coverage. Two suites: `updateSession` (mocks `@supabase/ssr` to drive the JWT validation paths) and `root proxy() matcher and redirect behaviour` (partial-mocks `@/lib/supabase/proxy` with an `importOriginal` fallthrough so the first suite can run the real implementation while the second suite overrides per test).

## PROTECTED_PREFIXES Shipped

The canonical protected-route list (other plans in this phase can rely on this as the source of truth):

```
/dashboard
/settings
/admin
/onboarding
/approval
/departments
/org-chart
/solopreneur
/startup
/sme
/enterprise
```

A request is protected if its pathname equals any prefix exactly (`/dashboard`) OR starts with `<prefix>/` (`/dashboard/team`). Anything not in this list is public.

## Decisions Made

All key decisions are captured in the frontmatter `key-decisions` field. Summary:

1. **File name is `proxy.ts` not `middleware.ts`** — Next.js 16 renamed the convention. Verified during planning research.
2. **`getClaims()` not `getSession()`** — JWKS-signature validation on every call, never trusts spoofable cookies.
3. **Session refresh runs on every matched request** — so downstream RSCs always see fresh tokens; redirect is gated to PROTECTED_PREFIXES only.
4. **ProtectedRoute.tsx and admin layout getSession() are INTENTIONALLY retained** — defense in depth. The proxy is the FIRST gate, not the only gate.
5. **Matcher excludes /api/* and static assets** — `/api/*` has its own backend auth via `verify_token`; assets never need the Supabase round-trip.
6. **updateSession reads env at call-time** — Next.js build can run with placeholder env vars; the request handler must always pick up runtime values.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Vitest mock collision between Task 1 and Task 2 suites in proxy.test.ts**

- **Found during:** Task 2 GREEN verify (the continuation session ran the Task 2 `verify` command and observed the Task 1 suite failing even though `fd9a868` had shipped the correct `updateSession` implementation).
- **Issue:** Vitest hoists all `vi.mock()` calls to the top of the test file. When commit `4b9251d` (Task 2 RED) added `vi.mock('@/lib/supabase/proxy', () => ({ updateSession: (req) => updateSessionMock(req) }))`, the alias `@/lib/supabase/proxy` resolved (per `vitest.config.mts`) to `./src/lib/supabase/proxy` — the EXACT SAME module the Task 1 suite was importing by relative path `../src/lib/supabase/proxy`. Result: the Task 1 suite received the mock's `updateSession` instead of the real one, which returned `undefined` after `vi.clearAllMocks()` in `beforeEach`, causing `Cannot destructure property 'response' of '(intermediate value)' as it is undefined` on all 5 Task 1 tests.
- **Fix:** Changed the Task 2 mock factory from `vi.mock('@/lib/supabase/proxy', () => ({ ... }))` to an `async (importOriginal)` factory that spreads every real export and only overrides `updateSession` with a conditional dispatcher: when `updateSessionMock.getMockImplementation()` is set (Task 2 per-test override), it delegates to the mock; otherwise it falls through to the real `updateSession` (Task 1 suite).
- **Files modified:** `frontend/__tests__/proxy.test.ts` (partial-mock factory rewrite, ~15 lines changed)
- **Verification:** All 14 tests pass (`npm test -- proxy.test.ts --run`), both suites exercise their intended code paths.
- **Committed in:** `50691d1` (carried alongside the Task 2 GREEN source file since the fix is what makes the Task 2 verify command green)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The auto-fix was essential to complete Task 2 `verify` — without it the plan's automated verification (`cd frontend && npm test -- proxy.test.ts --run`) could never have gone green. No scope creep; the fix is confined to test infrastructure and does not change any runtime behaviour.

## Issues Encountered

**Session interruption mid-Task 2 GREEN.** The initial executor session was interrupted after writing `frontend/proxy.ts` to disk (untracked) but before running verify or committing. The continuation session (this one) picked up with the file already on disk, ran verify, discovered the test-isolation bug, auto-fixed it under Rule 1, and committed Task 2 GREEN as `50691d1`. No work was lost and no duplicate commits were created.

**Frontend-wide lint debt out of scope.** The plan's Task 2 verify includes `npm run lint -- --max-warnings=0`, which reports 287 pre-existing problems (147 errors, 140 warnings) in completely unrelated files (`src/services/workflows.ts`, `src/services/initiatives.ts`, etc.). Per SCOPE BOUNDARY in the deviation rules, these are NOT fixed by 49-01. The 49-01 scope files (`proxy.ts`, `src/lib/supabase/proxy.ts`, `__tests__/proxy.test.ts`) lint clean individually with `--max-warnings=0`. The same pre-existing debt is already documented in `deferred-items.md` under the 49-02 entry — no new entry needed.

## User Setup Required

None — no external service configuration required. The proxy uses the existing `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` env vars that have been in the project since v1.x.

## Next Phase Readiness

- **Phase 49 progress:** 4 of 5 plans complete (49-01 ✅, 49-02 ✅, 49-03 ✅, 49-04 ✅, 49-05 pending).
- **Ready for 49-05:** AUTH-05 admin audit log viewer. 49-05 consumes the `governance_audit_log` table that 49-04 populated via `AuditLogMiddleware`.
- **Downstream plans can rely on `PROTECTED_PREFIXES`:** Plan 52 (persona gating) and Plan 53 (multi-user teams) both need to know which routes are gated by the proxy. The `PROTECTED_PREFIXES` constant in `frontend/proxy.ts` is the single source of truth — those plans should import it rather than re-declare.
- **Manual browser verification (deferred to human-verify):** The plan's `<verification>` block lists 7 manual cURL/browser checks (visiting `/dashboard`, `/settings`, `/admin`, `/solopreneur/dashboard`, `/`, `/auth/login`, and view-source on the `/dashboard` redirect to confirm no protected HTML leaks). These are covered by the 14 automated Vitest cases at the unit level but should be re-run manually against a running `npm run dev` before v7.0 beta ship.

## Self-Check: PASSED

**Files verified on disk:**
- `frontend/proxy.ts` FOUND
- `frontend/src/lib/supabase/proxy.ts` FOUND
- `frontend/__tests__/proxy.test.ts` FOUND
- `.planning/phases/49-security-auth-hardening/49-01-SUMMARY.md` FOUND

**Commits verified in git log:**
- `d01b678` (Task 1 RED) FOUND
- `fd9a868` (Task 1 GREEN) FOUND
- `4b9251d` (Task 2 RED) FOUND
- `50691d1` (Task 2 GREEN + mock-isolation auto-fix) FOUND

**Automated verification:** `cd frontend && npm test -- proxy.test.ts --run` → 14/14 tests passing, 1 test file passed, duration 1.58s.

---
*Phase: 49-security-auth-hardening*
*Plan: 01*
*Completed: 2026-04-07*
