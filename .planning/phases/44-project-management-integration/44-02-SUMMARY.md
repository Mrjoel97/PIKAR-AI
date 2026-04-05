---
phase: 44-project-management-integration
plan: 02
subsystem: api
tags: [webhooks, linear, asana, hmac, redis, pm-sync]

requires:
  - phase: 44-project-management-integration
    provides: PMSyncService, LinearService, AsanaService with bidirectional sync

provides:
  - Linear webhook handler at /webhooks/linear with HMAC-SHA256 verification
  - Asana webhook handler at /webhooks/asana with X-Hook-Secret handshake
  - PMSyncService.register_webhooks — Asana per-project subscription, Linear config check
  - PMSyncService.unregister_webhooks — Asana webhook GID cleanup via DELETE
  - PMSyncService.handle_webhook_event — centralised event processor for both providers
  - AsanaService.get_task — single task fetch by GID (required for webhook processing)

affects:
  - 44-project-management-integration
  - any phase adding new PM integrations

tech-stack:
  added: []
  patterns:
    - "X-Hook-Secret handshake pattern for Asana webhook registration with Redis persistence"
    - "Linear-Signature HMAC-SHA256 hex verification (not base64 — differs from Shopify)"
    - "Webhook GID storage in sync_cursor JSONB for lifecycle management"
    - "Pseudo-GID from query param ?gid= allows multiple Asana webhook secrets in Redis"

key-files:
  created: []
  modified:
    - app/routers/webhooks.py
    - app/services/pm_sync_service.py
    - app/services/asana_service.py

key-decisions:
  - "Linear webhooks are app-level (not per-project API) — register_webhooks only checks LINEAR_WEBHOOK_SECRET is set"
  - "Asana hook secret keyed by ?gid= query param on webhook URL, stored in Redis with 90-day TTL"
  - "Asana user resolution scans integration_sync_state for webhook_gids match; falls back to first Asana credential"
  - "Linear user resolution matches organizationId to account_name in integration_credentials; falls back to first Linear credential"
  - "PIKAR_BASE_URL env var used to construct Asana webhook target URL (with NEXT_PUBLIC_API_URL fallback)"
  - "handle_webhook_event passes Asana events through get_task fetch before sync — webhook payload only has GID"

patterns-established:
  - "PM webhook handlers follow Shopify/HubSpot pattern: raw body read first, HMAC verify, then JSON parse"
  - "Asana handshake response must include X-Hook-Secret header echoed back — use Response() not dict"
  - "Webhook GIDs persisted in sync_cursor.webhook_gids list for cleanup on unregister"

requirements-completed: [PM-03, PM-04]

duration: 6min
completed: 2026-04-05
---

# Phase 44 Plan 02: PM Webhook Integration Summary

**Linear + Asana real-time webhook handlers with HMAC verification, X-Hook-Secret handshake, per-project Asana subscription registration, and centralised event processing via PMSyncService**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-05T12:46:29Z
- **Completed:** 2026-04-05T12:52:23Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Linear webhook handler at `/webhooks/linear` verifies `Linear-Signature` HMAC-SHA256 and processes Issue create/update/remove events; remove maps to `cancelled` status
- Asana webhook handler at `/webhooks/asana` completes X-Hook-Secret handshake (persisting secret in Redis), verifies subsequent `X-Hook-Signature`, and delegates task events to PMSyncService
- PMSyncService extended with full webhook lifecycle: `register_webhooks` (Asana POSTs per project, Linear config check), `unregister_webhooks` (Asana GID DELETE), `handle_webhook_event` (centralised processor), and `save_sync_config` now auto-registers webhooks after initial sync

## Task Commits

Each task was committed atomically:

1. **Task 1: Linear and Asana webhook handlers** — `2ec7ff9` (feat)
2. **Task 2: Webhook subscription registration on sync config save** — `ca562e0` (feat)

## Files Created/Modified

- `app/routers/webhooks.py` — Added `/webhooks/linear` and `/webhooks/asana` endpoint handlers plus helpers (`_resolve_linear_user`, `_resolve_asana_user`, `_store_asana_hook_secret`, `_get_asana_hook_secret`)
- `app/services/pm_sync_service.py` — Extended with `register_webhooks`, `unregister_webhooks`, `handle_webhook_event`; updated `save_sync_config` to call `register_webhooks`
- `app/services/asana_service.py` — Added `get_task` method (Rule 2 auto-fix)

## Decisions Made

- Linear webhooks are app-level, not per-project — the API doesn't support programmatic registration of webhooks to external URLs without a Linear app configuration. `register_webhooks` for Linear only checks that `LINEAR_WEBHOOK_SECRET` is set and logs a reminder.
- Asana hook secret is stored in Redis keyed by `?gid=` query param appended to the webhook target URL, allowing multiple projects with independent secrets. Falls back to `ASANA_WEBHOOK_SECRET` env var when Redis is unavailable.
- `handle_webhook_event` for Asana fetches the full task via `AsanaService.get_task` because Asana webhook events only deliver the task GID, not the full payload.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added `AsanaService.get_task` for single-task fetch**
- **Found during:** Task 2 (handle_webhook_event implementation)
- **Issue:** `PMSyncService.handle_webhook_event` for Asana must call `asana_svc.get_task(user_id, task_gid)` to retrieve full task data — the webhook only delivers GIDs. The method did not exist in Plan 01's AsanaService.
- **Fix:** Added `get_task(user_id, task_gid)` to `AsanaService` with full `opt_fields` matching `list_tasks`, exception-safe returning `None` on failure.
- **Files modified:** `app/services/asana_service.py`
- **Verification:** Ruff lint clean; method integrated into `handle_webhook_event` call chain.
- **Committed in:** `ca562e0` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing critical functionality)
**Impact on plan:** Essential for correctness — without `get_task`, webhook events for Asana tasks could never be synced. No scope creep.

## Issues Encountered

None beyond the Rule 2 auto-fix above.

## User Setup Required

Two environment variables are required for webhook verification:

- `LINEAR_WEBHOOK_SECRET` — The signing secret from the Linear app webhook settings. Set this in Cloud Run and locally. Without it, signature verification is skipped (warning logged).
- `ASANA_WEBHOOK_SECRET` — Fallback Asana hook secret used when Redis is unavailable. The primary secret is stored in Redis during handshake.
- `PIKAR_BASE_URL` — The public base URL of the backend (e.g., `https://api.pikar.ai`). Required for Asana webhook registration target URL construction.

Linear webhook must be configured in the Linear app dashboard:
1. Go to Linear Settings > API > Webhooks
2. Add a webhook pointing to `https://<your-domain>/webhooks/linear`
3. Copy the signing secret to `LINEAR_WEBHOOK_SECRET`

## Next Phase Readiness

- Real-time bidirectional PM sync is fully operational: Plan 01 (API services + initial sync) + Plan 02 (webhooks) together deliver complete Linear and Asana integration
- Plan 03 can build the PM sync UI (project selector, status mapping editor, sync status dashboard) on top of this foundation
- `PMSyncService.unregister_webhooks` is ready for use if a "disconnect" flow is added to the settings UI

---
*Phase: 44-project-management-integration*
*Completed: 2026-04-05*
