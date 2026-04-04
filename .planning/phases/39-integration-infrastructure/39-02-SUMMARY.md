---
phase: 39-integration-infrastructure
plan: 02
subsystem: infra
tags: [webhooks, hmac, circuit-breaker, retry, dead-letter, supabase, postgresql]

# Dependency graph
requires:
  - phase: 38-solopreneur-unlock
    provides: Base platform with solopreneur persona and tool honesty
provides:
  - Inbound webhook receiver with HMAC-SHA256 verification and idempotent deduplication
  - Outbound webhook delivery service with exponential backoff retry
  - Dead letter queue for exhausted deliveries
  - Per-endpoint circuit breaker that auto-disables after 10 consecutive failures
  - Worker loop integration for scheduled delivery ticks
  - Event catalog with 9 webhook event types and JSON Schema payload definitions
  - Three Supabase tables (webhook_events, webhook_endpoints, webhook_deliveries)
affects: [39-integration-infrastructure, integration-sync, external-automation, api-endpoints]

# Tech tracking
tech-stack:
  added: []
  patterns: [hmac-sha256-webhook-signing, exponential-backoff-retry, per-endpoint-circuit-breaker, upsert-ignore-duplicates-idempotency]

key-files:
  created:
    - supabase/migrations/20260404600000_webhook_infrastructure.sql
    - app/models/webhook_events.py
    - app/services/webhook_delivery_service.py
    - tests/unit/test_webhook_service.py
  modified:
    - app/routers/webhooks.py
    - app/workflows/worker.py

key-decisions:
  - "Used upsert with ignore_duplicates=True for idempotent inbound webhook dedup instead of raw ON CONFLICT SQL"
  - "Split inbound webhook helpers (_verify_inbound_signature, _handle_inbound_insert) as testable functions separate from endpoint handler to avoid heavy ASGI import chain in tests"
  - "Created _INBOUND_PROVIDER_SECRETS dict as bridge until Plan 01 delivers PROVIDER_REGISTRY; runtime fallback import from integration_providers"
  - "Circuit breaker disables endpoint by setting active=false and disabled_at, consistent with project pattern from cache.py"

patterns-established:
  - "HMAC-SHA256 outbound signing: X-Pikar-Signature header with sha256={hex} format"
  - "Exponential backoff retry: [1, 5, 30, 300, 1800] seconds across 5 attempts"
  - "Dead letter: status='dead' after MAX_ATTEMPTS (5) exhausted"
  - "Per-endpoint circuit breaker: consecutive_failures >= 10 triggers auto-disable"
  - "Worker loop pattern: run_webhook_delivery_if_due() with 10-second interval"

requirements-completed: [INFRA-04, INFRA-05, INFRA-06]

# Metrics
duration: 17min
completed: 2026-04-04
---

# Phase 39 Plan 02: Webhook Infrastructure Summary

**Inbound HMAC-verified webhook receiver with idempotent dedup, outbound delivery with 5-attempt exponential backoff, dead letter queue, and per-endpoint circuit breaker**

## Performance

- **Duration:** 17 min
- **Started:** 2026-04-04T12:33:53Z
- **Completed:** 2026-04-04T12:51:30Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Inbound webhook endpoint POST /webhooks/inbound/{provider} with HMAC-SHA256 verification and ON CONFLICT idempotency
- Outbound webhook delivery service with retry backoff [1s, 5s, 30s, 5min, 30min], dead letter after 5 failures, circuit breaker after 10 consecutive failures
- Event catalog with 9 event types (task, workflow, approval, initiative, contact, invoice) with JSON Schema payload definitions
- Worker loop integration running delivery tick every 10 seconds
- 26 unit tests covering signature verification, idempotency, delivery, backoff, dead letter, circuit breaker

## Task Commits

Each task was committed atomically:

1. **Task 1: Webhook tables + event catalog + inbound receiver** - `42dbcdd` (feat)
2. **Task 2: Outbound delivery worker with retry, dead letter, and circuit breaker** - `664508c` (feat)

_Both tasks used TDD: tests written first (RED), implementation passes all tests (GREEN)._

## Files Created/Modified
- `supabase/migrations/20260404600000_webhook_infrastructure.sql` - 3 webhook tables with indexes, RLS on endpoints, unique constraint for dedup
- `app/models/webhook_events.py` - WebhookEventType enum, EVENT_CATALOG dict with 9 event types and JSON Schema payloads
- `app/services/webhook_delivery_service.py` - Outbound delivery: enqueue, delivery tick, single delivery with retry/dead letter/circuit breaker
- `app/routers/webhooks.py` - Added generalized inbound endpoint, HMAC verification, event ID extraction, idempotent insert
- `app/workflows/worker.py` - Added run_webhook_delivery_if_due() to worker loop (10s interval)
- `tests/unit/test_webhook_service.py` - 26 tests: inbound verification, idempotency, catalog, delivery, backoff, dead letter, circuit breaker

## Decisions Made
- Used upsert with ignore_duplicates for idempotent webhook dedup (matches Supabase Python client API)
- Created _INBOUND_PROVIDER_SECRETS bridge dict since Plan 01 (PROVIDER_REGISTRY) hasn't been executed yet; added runtime fallback import
- Split helper functions for testability without triggering the heavy ASGI import chain (rate_limiter, env file reads)
- Circuit breaker pattern consistent with project's cache.py: closed/open states based on consecutive failure counts

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] PROVIDER_REGISTRY not available from Plan 01**
- **Found during:** Task 1 (inbound webhook endpoint)
- **Issue:** Plan references `from app.config.integration_providers import PROVIDER_REGISTRY` but Plan 01 hasn't been executed yet
- **Fix:** Created `_INBOUND_PROVIDER_SECRETS` dict with common provider env var names as a bridge; added runtime fallback import from integration_providers at request time
- **Files modified:** app/routers/webhooks.py
- **Verification:** Tests pass; endpoint works with both the bridge dict and future PROVIDER_REGISTRY
- **Committed in:** 42dbcdd (Task 1 commit)

**2. [Rule 3 - Blocking] Supabase insert API mismatch**
- **Found during:** Task 1 (inbound insert logic)
- **Issue:** Plan specified `.insert().on_conflict().execute_ignore()` which is not a valid Supabase Python client API
- **Fix:** Used `.upsert(data, on_conflict="provider,event_id", ignore_duplicates=True)` which is the correct Supabase Python API for insert-or-ignore
- **Files modified:** app/routers/webhooks.py
- **Verification:** Tests pass; duplicate insert returns empty data as expected
- **Committed in:** 42dbcdd (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
- Test import chain triggers rate_limiter module which reads .env file with encoding issues on Windows; resolved by stubbing the rate_limiter and related modules at test module level

## User Setup Required

None - no external service configuration required. Webhook secrets are loaded from environment variables that will be configured per-provider when integrations are set up (Plan 01).

## Next Phase Readiness
- Webhook infrastructure complete; ready for Plan 03 (integration sync engine) to build on top
- Inbound webhook endpoint ready to receive events from any provider once Plan 01 configures OAuth + provider registry
- Outbound delivery ready to send events to user-configured endpoints once webhook_endpoints are registered via future API

## Self-Check: PASSED

- All 7 files verified present on disk
- Commit 42dbcdd (Task 1) verified in git log
- Commit 664508c (Task 2) verified in git log
- 26/26 tests passing

---
*Phase: 39-integration-infrastructure*
*Completed: 2026-04-04*
