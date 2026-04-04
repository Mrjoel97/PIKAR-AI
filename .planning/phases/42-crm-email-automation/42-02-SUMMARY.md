---
phase: 42-crm-email-automation
plan: 02
subsystem: api, email, automation
tags: [email-sequences, drip-campaigns, jinja2, resend, redis, tracking-pixel, bounce-protection, warm-up]

# Dependency graph
requires:
  - phase: 42-crm-email-automation
    provides: Database schema (email_sequences, email_sequence_steps, email_sequence_enrollments, email_tracking_events), Resend webhook handler
  - phase: 39-integration-infrastructure
    provides: OAuth credential storage, webhook infrastructure
provides:
  - EmailSequenceService with CRUD, enrollment, template rendering, delivery tick, send limits, bounce protection, tracking helpers, performance stats
  - Email sequences REST router with 11 endpoints (CRUD, enrollment, tracking, unsubscribe)
  - Worker integration for 60-second email delivery tick
  - Resend webhook extension for sequence bounce/open/click events
affects: [42-03 (agent tools use EmailSequenceService), 43-ad-platform (email engagement data)]

# Tech tracking
tech-stack:
  added: []
  patterns: [Jinja2 template rendering with Undefined for graceful missing vars, Redis INCR for atomic daily send counters, warm-up schedule for deliverability, RFC 8058 one-click unsubscribe, tracking pixel injection and link wrapping]

key-files:
  created:
    - app/services/email_sequence_service.py
    - app/routers/email_sequences.py
  modified:
    - app/workflows/worker.py
    - app/routers/webhooks.py
    - app/fast_api_app.py

key-decisions:
  - "AdminService (service role) for all EmailSequenceService DB ops since delivery tick runs without user context"
  - "Jinja2 Undefined (not StrictUndefined) so missing template variables render as empty string"
  - "Tracking ID format: {enrollment_id}_{step_number} parsed via rsplit('_', 1)"
  - "Warm-up schedule enforced via Redis INCR with 90000s TTL (25h) on daily counters"
  - "Bounce rate check runs once per user per tick to avoid redundant queries"

patterns-established:
  - "Email tracking pixel: 43-byte transparent PNG served from /tracking/open/{id} with no-cache headers"
  - "Click tracking: /tracking/click/{id}?url=DEST with http/https validation to prevent open redirect"
  - "RFC 8058 unsubscribe: both GET and POST handlers on /unsubscribe/{enrollment_id}"
  - "Worker tick pattern: last_X_tick + X_interval_seconds + lazy import of tick function"
  - "Sequence email identification via X-Pikar-Enrollment-Id and X-Pikar-Step custom headers"

requirements-completed: [EMAIL-01, EMAIL-02, EMAIL-03, EMAIL-04, EMAIL-05]

# Metrics
duration: 11min
completed: 2026-04-04
---

# Phase 42 Plan 02: Email Sequence Engine Summary

**Multi-step drip campaign engine with Jinja2 templates, timezone-aware scheduling, open/click tracking, Redis-based warm-up send limits, and auto-pause bounce protection**

## Performance

- **Duration:** 11 min
- **Started:** 2026-04-04T18:39:12Z
- **Completed:** 2026-04-04T18:50:50Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Complete EmailSequenceService (750+ lines): CRUD, enrollment with timezone-aware scheduling, Jinja2 template rendering, delivery tick processing 50 enrollments/batch, Redis daily send limits with 4-week warm-up (50/100/250/500), bounce rate auto-pause at >5% with 20-send minimum, open/click/unsubscribe tracking
- Email sequences router with 11 route functions: 5 CRUD, 2 enrollment, 1 performance, 3 public tracking (open pixel, click redirect, unsubscribe with RFC 8058 one-click support)
- Worker integration: 60-second email delivery tick added to WorkflowWorker start() loop via run_email_sequence_tick_if_due
- Resend webhook handler extended to route email.bounced/opened/clicked events to EmailSequenceService for server-side tracking alongside pixel-based tracking

## Task Commits

Each task was committed atomically:

1. **Task 1: Email sequence service with delivery engine and safeguards** - `17eb7db` (feat)
2. **Task 2: Email sequence router, tracking endpoints, and worker integration** - `d42a32e` (feat)

## Files Created/Modified
- `app/services/email_sequence_service.py` - Complete email sequence engine: CRUD, enrollment, template rendering, delivery tick, send limits, bounce protection, tracking helpers, performance stats
- `app/routers/email_sequences.py` - REST API with 11 endpoints for sequences, enrollment, tracking, and unsubscribe
- `app/workflows/worker.py` - Added email delivery tick (60s interval) to worker loop
- `app/routers/webhooks.py` - Extended Resend webhook for sequence bounce/open/click events via _handle_resend_sequence_event
- `app/fast_api_app.py` - Registered email_sequences_router

## Decisions Made
- AdminService (service role) for all EmailSequenceService DB operations since the delivery tick runs in the worker without user JWT context
- Jinja2 Undefined (not StrictUndefined) for template rendering so missing variables render as empty strings rather than causing errors in automated sends
- Tracking ID uses format {enrollment_id}_{step_number} parsed via rsplit('_', 1) for unambiguous splitting
- Warm-up daily send limits enforced atomically via Redis INCR with 90000s TTL (25 hours, covers timezone edge cases)
- Bounce rate checked once per user per delivery tick to avoid redundant queries across multiple enrollments for the same user
- Sequence emails identified in Resend webhooks via X-Pikar-Enrollment-Id and X-Pikar-Step custom headers

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

External services require manual configuration:
- **PIKAR_BASE_URL** environment variable (defaults to https://app.pikar.ai) for tracking URL construction
- **Resend API key** must be configured (RESEND_API_KEY via MCP config) for email delivery
- **Redis** must be available for daily send limit counters (gracefully degrades without it)

## Next Phase Readiness
- EmailSequenceService and router ready for Plan 03 agent tool wiring
- run_email_delivery_tick integrated into worker loop for autonomous email delivery
- Tracking endpoints live and ready for open/click/unsubscribe event recording
- Performance stats endpoint ready for dashboard integration

## Self-Check: PASSED

- All 5 files verified present on disk
- Both task commits (17eb7db, d42a32e) verified in git log

---
*Phase: 42-crm-email-automation*
*Completed: 2026-04-04*
