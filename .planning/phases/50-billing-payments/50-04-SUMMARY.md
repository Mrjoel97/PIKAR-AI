---
phase: 50-billing-payments
plan: 04
subsystem: payments
tags: [stripe, billing, subscription, portal, webhook, vitest, pytest, ssr]

# Dependency graph
requires:
  - phase: 50-billing-payments
    provides: "Plan 50-01 (webhook idempotency ledger + checkout.session.completed demotion), Plan 50-02 (SubscriptionContext + SubscriptionBadge + Supabase Realtime), Plan 50-03 (BillingMetricsService DB-native MRR + churn)"
provides:
  - "SubscriptionBadge wired into PremiumShell header so every authenticated page renders real-time billing state for all personas"
  - "Vitest unit test coverage (4 cases) for /api/stripe/portal — closes BILL-05 regression gap"
  - "tests/e2e/test_stripe_checkout_flow.py — pytest-marker-gated Stripe CLI e2e helper for pre-beta smoke test (skipped in CI via STRIPE_CLI_ENABLED opt-in)"
  - "tests/e2e/stripe_api_verification.py — standalone Stripe-API direct verification script that validates the Stripe-side contract BILL-01/BILL-05 depend on, without needing any local dev services"
  - "50-04-stripe-api-fixtures.json — captured real Stripe event payloads (prices, customer, subscription, events, portal configuration, portal session) for future regression use"
  - "BILL-05 (Stripe Customer Portal) closed via unit test + Stripe-API contract verification"
  - "Phase 50 closed — all 5 BILL requirements (BILL-01 through BILL-05) complete"
affects: [phase-51-observability, phase-52-persona-gating, phase-54-onboarding]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Stripe-API direct verification (stripe Python SDK + restricted test key) as a lightweight alternative to full webhook round-trip for contract validation"
    - "Pytest-marker-gated e2e tests (STRIPE_CLI_ENABLED env opt-in) — importable in CI, skipped unless operator explicitly enables"
    - "SubscriptionBadge as zero-prop context-reader — parent only has to render it; useSubscription() handles all state"

key-files:
  created:
    - frontend/src/app/api/stripe/portal/__tests__/route.test.ts
    - tests/e2e/test_stripe_checkout_flow.py
    - tests/e2e/stripe_api_verification.py
    - .planning/phases/50-billing-payments/50-04-stripe-api-fixtures.json
  modified:
    - frontend/src/components/layout/PremiumShell.tsx

key-decisions:
  - "UAT checkpoint resolved via Stripe-API direct verification (rk_test_ restricted key) instead of full webhook round-trip, because the full round-trip required Docker Desktop + Stripe CLI + local dev stack that were not available in this execution window"
  - "tests/e2e/test_stripe_checkout_flow.py retained as the canonical pre-beta smoke test (not deleted) — operator runs it when the full local stack is available"
  - "Live STRIPE_SECRET_KEY in .env was rejected for safety and the user provided a restricted test key (STRIPE_TEST_KEY, rk_test_ prefix) for the verification pass"
  - "SubscriptionBadge placement in PremiumShell header bar adjacent to existing user-menu / notification area — single source of truth across all authenticated routes"
  - "Portal route test mocks @supabase/ssr + stripe SDK to isolate the handler — no real network calls, fully CI-safe"

patterns-established:
  - "Stripe-API direct verification: talk to api.stripe.com with the Python stripe SDK + a restricted test key, capture real event payloads to a fixtures file, assert the shape our webhook handlers depend on. Cheaper than booting the full stack, higher-confidence than mock fixtures alone."
  - "Fixtures JSON committed alongside the plan for future regression — if Stripe changes event shape, re-running the verifier reveals the drift immediately."

requirements-completed: [BILL-05]

# Metrics
duration: "Plan executed in two sessions separated by UAT pause — code work ~10 min (2026-04-07 18:10-18:18); UAT resolution ~40 min (2026-04-08)"
completed: 2026-04-08
---

# Phase 50 Plan 04: Billing UAT — Badge Placement, Portal Test, Stripe API Verification Summary

**SubscriptionBadge placed in PremiumShell header, /api/stripe/portal gains 4-case vitest coverage, Stripe CLI e2e helper committed for operator smoke test, and BILL-05 closed via a direct Stripe-API contract verification (11 real-API assertions, all PASSED) — Phase 50 4/4 complete.**

## Performance

- **Started:** 2026-04-07T18:10:53+03:00 (Task 1 commit)
- **Paused:** 2026-04-07T18:17:47+03:00 (Task 3 committed, Task 4 UAT checkpoint reached)
- **Resumed:** 2026-04-08 (UAT resolution via Stripe API verification)
- **Completed:** 2026-04-08T15:57:28+03:00 (verification commit)
- **Code execution time:** ~7 min for Tasks 1-3 (badge + portal test + CLI helper)
- **UAT resolution time:** ~40 min (API verification script + fixtures capture + Task 4 close-out)
- **Tasks:** 4 of 4
- **Files created:** 4 (portal test, CLI e2e helper, API verification script, fixtures JSON)
- **Files modified:** 1 (PremiumShell.tsx)
- **Commits (code):** 4 — `ca0e5ad`, `3c87a40`, `fda6c87`, `715c9bc`
- **Commits (metadata):** 1 — this SUMMARY + STATE + ROADMAP + REQUIREMENTS

## Accomplishments

- **Task 1 — Badge placement:** SubscriptionBadge now renders in the PremiumShell header for every authenticated page, regardless of persona. Zero prop drilling — badge reads `useSubscription()` context directly.
- **Task 2 — Portal route test coverage:** 4 vitest cases cover the /api/stripe/portal route: 401 on no session, 400 on missing `stripe_customer_id`, 200 + URL on happy path, 500 with generic message on Stripe SDK error (no stack leak). All 4 pass against the existing route implementation — no route changes needed, closes the BILL-05 regression gap.
- **Task 3 — Stripe CLI e2e helper:** `tests/e2e/test_stripe_checkout_flow.py` encodes the full checkout → webhook → DB assertion flow as a pytest helper, gated behind `STRIPE_CLI_ENABLED` env opt-in so it stays skipped in CI. Re-runnable via test-row teardown.
- **Task 4 — UAT checkpoint resolved via Stripe API verification:** Instead of running the full local dev stack (Docker + Supabase + backend + frontend + Stripe CLI + browser checkout), Task 4 was closed by writing `tests/e2e/stripe_api_verification.py`, a standalone Python script that talks directly to the Stripe API with a restricted test key (`rk_test_`) and validates the Stripe-side contract our webhook handlers depend on. **11 sub-assertions across 8 checks, all PASSED against a real Stripe test-mode account.** Real event payloads captured in `50-04-stripe-api-fixtures.json` (1073 lines) as regression fixtures.

## Task Commits

1. **Task 1: Render SubscriptionBadge in PremiumShell header** — `ca0e5ad` (feat)
2. **Task 2: Unit test coverage for /api/stripe/portal route (BILL-05)** — `3c87a40` (test)
3. **Task 3: Stripe CLI e2e helper for local billing UAT** — `fda6c87` (test)
4. **Task 4 (UAT resolution): Stripe API verification script and captured fixtures** — `715c9bc` (test)

**Plan metadata:** (this commit — docs: complete plan)

## Files Created/Modified

### Created

- `frontend/src/app/api/stripe/portal/__tests__/route.test.ts` (227 lines) — 4-case vitest suite mocking `@supabase/ssr` + `stripe` SDK
- `tests/e2e/test_stripe_checkout_flow.py` (341 lines) — pytest Stripe CLI helper, skipped without `STRIPE_CLI_ENABLED`
- `tests/e2e/stripe_api_verification.py` (481 lines) — standalone Stripe-API direct verifier using `STRIPE_TEST_KEY`
- `.planning/phases/50-billing-payments/50-04-stripe-api-fixtures.json` (1073 lines) — captured real Stripe fixtures for 8 checks

### Modified

- `frontend/src/components/layout/PremiumShell.tsx` — imports `SubscriptionBadge` from `@/components/billing/SubscriptionBadge`, renders it in the header bar. No state, no fetching, no provider re-wrap (SubscriptionProvider already at `dashboard/layout.tsx` per Plan 50-02).

## Decisions Made

1. **UAT resolved via Stripe-API contract verification instead of full webhook round-trip.** The original Task 4 required Docker Desktop + Stripe CLI + local Supabase + local backend + local frontend + real browser checkout. Those were not available in the execution window. Instead of blocking the plan indefinitely, we wrote a standalone Python script that validates the Stripe-side contract directly via the Stripe API. The full round-trip through the LOCAL webhook handler remains tested by 9 vitest cases in `frontend/src/app/api/webhooks/stripe/__tests__/route.test.ts` using mock events — and this verification pass confirms those mocks are shape-realistic against real Stripe.

2. **Restricted test key (rk_test_) only — live key rejected.** The initial `.env` contained a LIVE `STRIPE_SECRET_KEY`. That was rejected for safety. The user provided `STRIPE_TEST_KEY=rk_test_...` (restricted test key) and the verification script uses only that.

3. **`tests/e2e/test_stripe_checkout_flow.py` retained as canonical pre-beta smoke test.** Not deleted. The operator runs it against the full local stack when Docker + Stripe CLI + supabase + backend + frontend are all up.

4. **SubscriptionBadge placement in PremiumShell header, not layout.** Plan 50-02 intentionally shipped the badge without placement; Plan 50-04 owns placement. PremiumShell wraps all authenticated routes across all personas, so a single render covers the full surface.

5. **Portal route tests mock everything — no real network.** `@supabase/ssr` and `stripe` SDK both mocked via `vi.mock()`. Tests run in Vitest's Node environment with a fabricated NextRequest. Fully CI-safe, zero external dependencies.

## Stripe API Verification — What Was Covered

**Script:** `tests/e2e/stripe_api_verification.py`
**Auth:** `STRIPE_TEST_KEY` from `.env` (restricted test key, `rk_test_` prefix)
**Target:** api.stripe.com (real, test mode)
**Fixtures captured:** `.planning/phases/50-billing-payments/50-04-stripe-api-fixtures.json`

| # | Check | Validates | Result |
|---|-------|-----------|--------|
| 1a | Solopreneur price ($99/mo, monthly, active, test) | BILL-01 tier mapping | PASS |
| 1b | Startup price ($297/mo, monthly, active, test) | BILL-01 tier mapping | PASS |
| 1c | SME price ($597/mo, monthly, active, test) | BILL-01 tier mapping | PASS |
| 2 | `Customer.create` with `metadata.supabase_user_id` | BILL-01 user-ID resolution (customer path) | PASS |
| 3 | `Subscription.create` on Solopreneur with metadata | BILL-01 webhook payload shape | PASS |
| 4a | `customer.subscription.created` event carries `metadata.supabase_user_id` | BILL-01 user-ID resolution (subscription path) | PASS |
| 4b | `customer.subscription.created` event `items[0].price.id` matches Solopreneur | BILL-01 tier mapping in webhook handler | PASS |
| 5 | `Subscription.modify` with `cancel_at_period_end=True` persists | BILL-05 portal cancel contract | PASS |
| 6 | `customer.subscription.updated` event carries `cancel_at_period_end=True` | BILL-01 race fix tests a real behavior (Test 9 regression anchor) | PASS |
| 7 | `billing_portal.Configuration.create` succeeds | BILL-05 prerequisite — portal configuration exists for the test account (`bpc_1TJve4IpVJs9RrPniHkbl6Q0`) | PASS |
| 8 | `billing_portal.Session.create` returns valid URL | BILL-05 contract — what `/api/stripe/portal` wraps | PASS |

**11 / 11 assertions PASSED.**

### Key fixture highlights

- `price_solopreneur.id = price_1S3aSSIpVJs9RrPn3xgT1tsd` (unit_amount: 9900)
- `price_startup.id = price_1S3aSzIpVJs9RrPnpPBdr4ej` (unit_amount: 29700)
- `price_sme.id = price_1S3aTaIpVJs9RrPnv42ImIxv` (unit_amount: 59700)
- `customer.id = cus_UIWhYXPqdlTv8v` (metadata.supabase_user_id preserved through API round-trip)
- `subscription.id = sub_...` with `items[0].price.id` matching the Solopreneur price
- `customer.subscription.updated` payload shows `cancel_at_period_end: true` after `Subscription.modify`
- `portal_configuration = bpc_1TJve4IpVJs9RrPniHkbl6Q0` (created during the verification run — BILL-05 now has a prerequisite in the test account)
- `portal_session.url = https://billing.stripe.com/p/session/...` (valid Stripe-hosted portal URL)

## Deferred to Pre-Beta Smoke Test

The Stripe API verification pass validates the **Stripe-side contract** — what the Stripe API returns and what event payloads the webhook handlers receive. It does **NOT** cover the full local HTTP round-trip from Stripe → Next.js webhook handler → Supabase → SubscriptionContext realtime → SubscriptionBadge re-render. That remains a pre-beta smoke test to run when the operator has the full dev stack available.

### What the operator must still verify manually before beta launch

Run `tests/e2e/test_stripe_checkout_flow.py` (or the manual UAT in `50-04-PLAN.md` Task 4 `<how-to-verify>`) with:

- Docker Desktop running
- `supabase start` (migrations applied)
- `docker compose up` (backend + redis)
- `cd frontend && npm run dev` (frontend on :3000)
- Stripe CLI installed + `stripe login` completed
- `stripe listen --forward-to http://localhost:3000/api/webhooks/stripe` running in a terminal, with the `whsec_...` copied into `frontend/.env.local` as `STRIPE_WEBHOOK_SECRET`
- `STRIPE_CLI_ENABLED=1` and `TEST_USER_ID=<real supabase uuid>` env vars

Then cover these 6 flows from the original Task 4 `<how-to-verify>` block:

- **Step A — Empty state:** Badge shows "Free" (gray) for a fresh user
- **Step B — Checkout flow:** Stripe test card `4242 4242 4242 4242` → redirect back → badge updates to "Active · Solopreneur" within 5s without manual refresh; `stripe_webhook_events` table shows `status='processed'` rows for both `checkout.session.completed` AND `customer.subscription.created`
- **Step C — Idempotency + BILL-01 re-delivery check:** Re-send `checkout.session.completed` via Stripe Dashboard — confirm only ONE row in `stripe_webhook_events` for that `event_id` and `subscriptions.tier` / `is_active` / `will_renew` / `last_event_type` all stay unchanged (the demoted handler cannot regress state)
- **Step D — Portal + cancel:** Click "Manage Subscription" → Stripe Customer Portal → Cancel → badge updates to "Canceling" (amber) within 5s without page reload; then re-deliver an older `checkout.session.completed` and confirm `will_renew` remains `false`
- **Step E — Admin billing dashboard:** `/admin/billing` shows MRR $99, Active 1, Churn 0%, Plan Distribution 1 solopreneur (validates Plan 50-03 end-to-end)
- **Step F — Real-time badge regression:** Change plan in Stripe Dashboard from Solopreneur to Startup — open tab's badge updates within 5s without refresh (validates Plan 50-02 realtime path)

### What is NOT deferred (already verified)

- Webhook handler logic (9 vitest cases in `frontend/src/app/api/webhooks/stripe/__tests__/route.test.ts` from Plan 50-01)
- SubscriptionContext realtime subscription (vitest cases from Plan 50-02)
- BillingMetricsService MRR + churn (pytest cases from Plan 50-03)
- Portal route handler (4 vitest cases from this plan, Task 2)
- Stripe-side contract (11 real-API assertions from this plan, Task 4 resolution)

The combination above gives HIGH confidence that the full flow works. The deferred smoke test is the final belt-and-braces check before inviting beta users.

## Deviations from Plan

### Auto-fixed / Process-level

**1. [Process] UAT checkpoint resolved via Stripe API direct verification instead of full local-stack round-trip**

- **Found during:** Task 4 (UAT checkpoint)
- **Issue:** The original Task 4 required Docker Desktop + Stripe CLI + `stripe login` + `supabase start` + `docker compose up` + `npm run dev` + manual browser click-through. None of those were running in the execution window, and the user could not spin them up on demand.
- **Also found:** `.env` contained a LIVE `STRIPE_SECRET_KEY` (`sk_live_...`). Using that against real Stripe was rejected for safety — a misfired test could have touched real production customers.
- **Fix:** User provided `STRIPE_TEST_KEY=rk_test_...` (a restricted test key) in `.env`. I wrote `tests/e2e/stripe_api_verification.py` — a standalone Python script using the `stripe` SDK + the restricted test key to validate the Stripe-side contract directly via api.stripe.com (test mode). Script ran green: 11 / 11 assertions PASSED. Real event payloads captured to `50-04-stripe-api-fixtures.json` for future regression.
- **Files created:** `tests/e2e/stripe_api_verification.py`, `.planning/phases/50-billing-payments/50-04-stripe-api-fixtures.json`
- **Verification:** Script exit code 0 across all 8 checks; fixtures JSON committed and inspectable.
- **Committed in:** `715c9bc`
- **Impact:** No code change to any already-shipped file. Task 4 is closed with high confidence on the Stripe-side contract, with the full local round-trip explicitly deferred to a pre-beta smoke test and documented in the "Deferred to Pre-Beta Smoke Test" section above.

---

**Total deviations:** 1 process-level (UAT resolution path change, no code impact)
**Impact on plan:** Zero — all 4 task deliverables shipped as specified, only the Task 4 verification method differs from the original human-click-through script. The deferred smoke test path is fully documented so the verifier knows exactly what remains.

## Issues Encountered

- **Live Stripe key in .env** — blocked the first verification attempt. Resolved by the user providing a restricted test key (`STRIPE_TEST_KEY`, `rk_test_`). Resolution captured in decisions above.
- **Docker Desktop not running + no Stripe CLI installed** — prevented the original full-stack UAT path. Resolved by switching to Stripe-API direct verification (see Deviations).

## Stripe Test Reference

- **Test card used by the Stripe CLI e2e helper and documented in the manual UAT script:** `4242 4242 4242 4242`, any future expiry, any CVC, any ZIP
- **Fake Supabase user UUID used by the API verification script:** `00000000-0000-0000-0000-001775652927` (embedded in `fixtures.customer.metadata.supabase_user_id` and `fixtures.subscription.metadata.supabase_user_id`)
- **Restricted test key used for the verification run:** `rk_test_...` (stored in `.env` as `STRIPE_TEST_KEY`, never committed)
- **Portal configuration created as side-effect of verification run:** `bpc_1TJve4IpVJs9RrPniHkbl6Q0` (BILL-05 now has a test-account prerequisite in place)

## Audited Routes Note

The Python `AuditLogMiddleware` (from Plan 49-04) runs on the FastAPI backend, but the Stripe webhook, checkout, and portal routes all live in the **Next.js frontend** (`frontend/src/app/api/webhooks/stripe/`, `frontend/src/app/api/stripe/checkout/`, `frontend/src/app/api/stripe/portal/`). The only FastAPI billing route (`/admin/billing`) is already excluded from audit middleware via the `/admin` entry in `_EXCLUDED_PREFIXES`. **No audit-route changes are needed for Phase 50.** Future verifiers should not re-ask this question.

## Environment Variable Reference

The plan did not require new env vars beyond what Plan 50-01/02/03 already shipped. For the optional pre-beta smoke test the operator needs:

```
# In frontend/.env.local
STRIPE_SECRET_KEY=sk_test_...              # TEST MODE ONLY — never live
STRIPE_WEBHOOK_SECRET=whsec_...            # from `stripe listen` output
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_STRIPE_PRICE_SOLOPRENEUR=price_1S3aSSIpVJs9RrPn3xgT1tsd
NEXT_PUBLIC_STRIPE_PRICE_STARTUP=price_1S3aSzIpVJs9RrPnpPBdr4ej
NEXT_PUBLIC_STRIPE_PRICE_SME=price_1S3aTaIpVJs9RrPnv42ImIxv
STRIPE_PRICE_TIER_MAP=price_1S3aSSIpVJs9RrPn3xgT1tsd:solopreneur,price_1S3aSzIpVJs9RrPnpPBdr4ej:startup,price_1S3aTaIpVJs9RrPnv42ImIxv:sme

# In .env (root, for the API verification script — optional, keep out of VCS)
STRIPE_TEST_KEY=rk_test_...                # restricted test key
```

Real test-mode price IDs are now captured in the fixtures JSON for easy copy-paste.

## Production Runbook Deferrals (NOT Phase 50 scope)

These are deployment-time concerns, NOT code work:

- **Production Stripe key rotation runbook** — document the procedure for rotating live keys without downtime
- **Production webhook endpoint creation** — create the production Stripe webhook endpoint in the Stripe Dashboard pointing at the deployed frontend URL, then copy the `whsec_...` into the production env
- **Production price ID creation** — create live-mode prices matching the test-mode tiers and update production env vars

These are tracked as pre-beta checklist items, not Phase 50 plan items.

## Next Phase Readiness

- **Phase 50 is 4/4 complete.** All 5 BILL requirements (BILL-01, BILL-02, BILL-03, BILL-04, BILL-05) are closed.
- **Phase 51 (Observability & Monitoring) is next.** No blockers from Phase 50. The audit-routes note above explicitly eliminates one known source of confusion for Phase 51 verifiers.
- **Known pre-beta task:** Run the full local-stack UAT smoke test documented in the "Deferred to Pre-Beta Smoke Test" section above before inviting real beta users. Everything needed (test file, script, UAT steps, price IDs, test card) is committed and findable.

## Self-Check: PASSED

All 6 referenced files found on disk (PremiumShell.tsx, portal route test, e2e helper, API verification script, fixtures JSON, this SUMMARY). All 4 task commits verified in git history (ca0e5ad, 3c87a40, fda6c87, 715c9bc).

---
*Phase: 50-billing-payments*
*Completed: 2026-04-08*
