---
phase: 43-ad-platform-integration
plan: 02
subsystem: api
tags: [google-ads, meta-ads, approvals, notifications, supabase, fastapi, httpx]

# Dependency graph
requires:
  - phase: 43-ad-platform-integration plan 01
    provides: GoogleAdsService, MetaAdsService, AdBudgetCapService, ad_budget_caps migration

provides:
  - AdApprovalService — gates GATED_OPERATIONS with rich card payload + cap headroom
  - execute_approved_operation — dispatches to Google Ads / Meta Ads API after human approval
  - ad_approvals router — POST decide, GET card, GET pending list endpoints
  - AdPerformanceSyncService — 6-hour scheduled sync + budget pacing alerts
  - Integration router — GET/PUT /{provider}/budget-cap, POST sync-performance, POST internal sync
  - OAuth callback budget-cap check — prompts frontend when no cap is configured post-connection

affects:
  - 43-03-ad-management-agent (uses AdApprovalService.check_and_gate for all ad tool calls)
  - frontend ad campaign management UI (consumes /ad-approvals endpoints and budget-cap API)
  - Cloud Scheduler configuration (needs POST /internal/sync/ad-performance every 6 hours)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Approval gate pattern: check_and_gate returns approval_required dict; execute_approved_operation dispatches to platform API on APPROVED status
    - Scheduled sync with AdminService for credential queries (no user JWT in background workers)
    - Budget pacing alert fires WARNING notification when projected total > monthly cap
    - OAuth callback budget-cap check: signals needs_budget_cap to frontend via postMessage

key-files:
  created:
    - app/services/ad_approval_service.py
    - app/routers/ad_approvals.py
    - app/services/ad_performance_sync_service.py
  modified:
    - app/routers/integrations.py
    - app/fast_api_app.py

key-decisions:
  - "GATED_OPERATIONS frozenset defines which ad operations need approval — activate, resume, budget increases, bid changes"
  - "execute_approved_operation fetches APPROVED row from DB then dispatches to GoogleAdsService or MetaAdsService"
  - "AdPerformanceSyncService covers last 7 days on each sync to handle Google 3h reporting delay and Meta late conversions"
  - "Budget pacing check uses AdminService for campaign + spend queries — no user JWT available in background sync"
  - "OAuth callback checks is_cap_set after ad platform connection; signals needs_budget_cap postMessage to frontend"
  - "Internal sync endpoint authenticated via X-Workflow-Secret header matching WORKFLOW_SERVICE_SECRET env var"

patterns-established:
  - "Approval gate: check_and_gate() → blocked (cap exceeded) | execute=True (non-gated) | approval card (gated)"
  - "Background sync: AdminService for all DB queries, lazy service imports inside async methods"

requirements-completed: [ADS-03, ADS-04, ADS-05]

# Metrics
duration: 16min
completed: 2026-04-05
---

# Phase 43 Plan 02: Ad Approval Gate & Performance Sync Summary

**Human approval gate for ad budget operations with rich card payloads, 6-hour performance sync, and budget pacing alerts via notification system**

## Performance

- **Duration:** 16 min
- **Started:** 2026-04-05T01:47:39Z
- **Completed:** 2026-04-05T02:03:10Z
- **Tasks:** 2
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments

- AdApprovalService gates 6 budget/spend operations behind human approval — builds card payload with projected monthly impact, cap headroom, and platform context, then calls request_human_approval with action_type=AD_BUDGET_CHANGE
- execute_approved_operation fetches APPROVED row, dispatches to GoogleAdsService or MetaAdsService, and updates local ad_campaigns record
- AdPerformanceSyncService pulls last 7 days from Google Ads and Meta Ads for all connected users, writes to ad_spend_tracking, and fires WARNING notifications when daily spend pace would exceed monthly cap
- Integration router gains GET/PUT /{provider}/budget-cap (cap config), POST /{provider}/sync-performance (on-demand), and POST /internal/sync/ad-performance (Cloud Scheduler every 6h)
- OAuth callback now checks for budget cap after ad platform connection and signals frontend when none is set

## Task Commits

Each task was committed atomically:

1. **Task 1: Ad approval service and REST endpoints** - `2f8afd9` (feat)
2. **Task 2: Performance sync service, budget pacing alerts, and integration endpoints** - `bfdf124` (feat)

**Plan metadata:** (this commit, docs)

## Files Created/Modified

- `app/services/ad_approval_service.py` — GATED_OPERATIONS set, check_and_gate, request_budget_approval, execute_approved_operation with platform dispatch
- `app/routers/ad_approvals.py` — POST decide, GET card, GET pending list, ownership checks
- `app/services/ad_performance_sync_service.py` — sync_all_users, sync_user_platform, _sync_google_ads, _sync_meta_ads, _check_budget_pacing
- `app/routers/integrations.py` — budget-cap CRUD endpoints, sync-performance trigger, internal scheduler endpoint, OAuth callback cap check, _oauth_budget_cap_prompt_html helper
- `app/fast_api_app.py` — import and mount ad_approvals_router

## Decisions Made

- GATED_OPERATIONS frozenset defines the approval boundary: activate/resume (starts spending), budget increases, bid changes. Non-gated operations (pause, decrease budget) execute immediately.
- execute_approved_operation reads the APPROVED row from DB rather than taking the operation as a parameter — this ensures the decision came through the approval flow and prevents parameter tampering.
- Performance sync covers last 7 days on each run to handle Google Ads' ~3-hour reporting delay and Meta's late-arriving conversion data.
- Budget pacing uses AdminService for DB queries (no user JWT available in background workers called by Cloud Scheduler).
- OAuth callback budget cap check is fire-and-forget with a warning log on failure — the check is helpful but should never block OAuth completion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] GoogleAdsService, MetaAdsService, AdBudgetCapService already existed**
- **Found during:** Pre-execution dependency check
- **Issue:** Plan 01 services (GoogleAdsService, MetaAdsService, AdBudgetCapService) were required by Plan 02 but had already been built (Plan 01 executed prior to this session). Files existed with full implementations matching the plan spec.
- **Fix:** Confirmed all three services were complete and compatible; proceeded directly to Plan 02 tasks without rebuilding.
- **Files modified:** None — used existing services as-is.
- **Committed in:** N/A (no action needed)

---

**Total deviations:** 1 (blocking dependency — resolved by verifying Plan 01 already complete)
**Impact on plan:** No scope creep. Plan 02 tasks executed exactly as specified.

## Issues Encountered

None — all Plan 01 prerequisites were already in place. Both tasks executed cleanly against the existing service layer.

## User Setup Required

None — no new external service configuration required for Plan 02. Cloud Scheduler configuration for the 6-hour sync endpoint is covered in Phase 43 deployment setup.

## Next Phase Readiness

- AdApprovalService is ready for wiring into the MarketingAutomationAgent tools (Phase 43 Plan 03)
- AdPerformanceSyncService is ready to be registered as a Cloud Scheduler job targeting POST /internal/sync/ad-performance with X-Workflow-Secret header
- Frontend can consume /ad-approvals/pending to display approval cards and /ad-approvals/{id}/decide for user action
- Budget cap endpoints are live; frontend OAuth callback handler should check needs_budget_cap in postMessage and show cap configuration dialog

---
*Phase: 43-ad-platform-integration*
*Completed: 2026-04-05*

## Self-Check: PASSED

- FOUND: app/services/ad_approval_service.py
- FOUND: app/routers/ad_approvals.py
- FOUND: app/services/ad_performance_sync_service.py
- FOUND: app/routers/integrations.py (modified)
- FOUND: app/fast_api_app.py (modified)
- FOUND commit: 2f8afd9 (Task 1)
- FOUND commit: bfdf124 (Task 2)
- AD_BUDGET_CHANGE appears 3 times in ad_approval_service.py
- budget-cap appears 2 times in integrations.py
- sync_all_users appears 4 times in ad_performance_sync_service.py
- ad_approvals mounted in fast_api_app.py (2 occurrences)
