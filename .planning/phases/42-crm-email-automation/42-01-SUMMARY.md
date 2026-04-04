---
phase: 42-crm-email-automation
plan: 01
subsystem: database, api, crm
tags: [hubspot, crm, email-sequences, webhooks, oauth, postgres, redis]

# Dependency graph
requires:
  - phase: 39-integration-infrastructure
    provides: OAuth credential storage, IntegrationManager, webhook infrastructure
  - phase: 41-financial-integrations
    provides: StripeSyncService pattern (asyncio.to_thread, AdminService writes, lazy SDK import)
provides:
  - Phase 42 database schema (hubspot_deals, email_sequences, email_sequence_steps, email_sequence_enrollments, email_tracking_events)
  - hubspot_contact_id column on existing contacts table
  - HubSpotService with bidirectional contact/deal sync
  - Dedicated /webhooks/hubspot endpoint with v3 signature verification
  - Redis skip-flag pattern for sync loop prevention
affects: [42-02 (email sequence service uses email tables), 42-03 (agent tools use HubSpotService), 43-ad-platform (CRM audience data)]

# Tech tracking
tech-stack:
  added: [hubspot-api-client, jinja2]
  patterns: [HubSpot v3 HMAC-SHA256 webhook verification, Redis skip-flag for bidirectional sync loop prevention, lazy HubSpot SDK import]

key-files:
  created:
    - supabase/migrations/20260404800000_crm_email_automation.sql
    - app/services/hubspot_service.py
  modified:
    - app/routers/webhooks.py
    - pyproject.toml

key-decisions:
  - "Redis skip-flag (30s TTL) for bidirectional sync loop prevention -- when Pikar pushes to HubSpot, a flag prevents the resulting webhook from re-importing"
  - "Last-write-wins conflict resolution for concurrent HubSpot/Pikar edits -- logged but not blocked per user decision"
  - "HubSpot client_secret used for v3 webhook signature (not a separate webhook secret) -- matches HubSpot's v3 signature spec"
  - "Single-user fallback in portal resolution -- returns first HubSpot credential when portal_id doesn't match account_name"

patterns-established:
  - "HubSpot webhook v3 verification: HMAC-SHA256(secret, METHOD+URL+body+timestamp) with 300s replay window"
  - "Redis skip-flag pattern: pikar:hubspot:skip:{object_id} with 30s TTL for bidirectional sync echo suppression"
  - "Batched webhook processing: HubSpot sends JSON array, iterate and route by subscriptionType prefix"

requirements-completed: [CRM-01, CRM-02, CRM-03, CRM-06]

# Metrics
duration: 14min
completed: 2026-04-04
---

# Phase 42 Plan 01: CRM & Email Automation Foundation Summary

**HubSpot bidirectional CRM sync with contact/deal import, push-to-HubSpot, dedicated webhook endpoint with v3 signature verification, and full Phase 42 database schema (5 new tables + contacts extension)**

## Performance

- **Duration:** 14 min
- **Started:** 2026-04-04T18:16:37Z
- **Completed:** 2026-04-04T18:31:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Complete Phase 42 database schema: hubspot_deals, email_sequences, email_sequence_steps, email_sequence_enrollments, email_tracking_events -- all with RLS policies, service_role bypass, indexes, and triggers
- HubSpotService with 9 methods: sync_contacts, sync_deals, push_contact_to_hubspot, push_deal_to_hubspot, get_deal_context, search_contacts, handle_contact_webhook, handle_deal_webhook
- Dedicated /webhooks/hubspot endpoint with v3 HMAC-SHA256 signature verification and batched event processing
- Bidirectional sync loop prevention via Redis skip flags (30s TTL)
- Conflict detection with last-write-wins strategy for concurrent edits

## Task Commits

Each task was committed atomically:

1. **Task 1: Database migration for all Phase 42 tables** - `214bd75` (feat)
2. **Task 2: HubSpot sync service and dedicated webhook endpoint** - `84ecb81` (feat)

## Files Created/Modified
- `supabase/migrations/20260404800000_crm_email_automation.sql` - All Phase 42 tables: hubspot_deals, email_sequences, email_sequence_steps, email_sequence_enrollments, email_tracking_events, plus contacts.hubspot_contact_id
- `app/services/hubspot_service.py` - HubSpotService class (1003 lines) with full CRM sync, push, search, webhook handling
- `app/routers/webhooks.py` - Added /webhooks/hubspot endpoint with v3 signature verification and portal-based user resolution
- `pyproject.toml` - Added hubspot-api-client and jinja2 dependencies

## Decisions Made
- Redis skip-flag (30s TTL) for bidirectional sync loop prevention -- matches the pattern from existing codebase Redis usage
- Last-write-wins conflict resolution for concurrent HubSpot/Pikar edits -- logged for visibility but applied per user decision from planning
- HubSpot client_secret used for v3 webhook verification -- HubSpot v3 spec uses the app's client secret, not a separate webhook secret
- Single-user fallback in _resolve_hubspot_user -- returns first HubSpot credential when portal_id lookup fails (solopreneur mode)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added service_role RLS policies on all tables**
- **Found during:** Task 1 (Database migration)
- **Issue:** Plan specified RLS for authenticated users but not service_role bypass needed for webhook/AdminService writes
- **Fix:** Added `service_role` policy on each table following Phase 41 pattern
- **Files modified:** supabase/migrations/20260404800000_crm_email_automation.sql
- **Verification:** All tables have service_role policy
- **Committed in:** 214bd75 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Essential for AdminService webhook writes. No scope creep.

## Issues Encountered
None

## User Setup Required

External services require manual configuration:
- **HUBSPOT_CLIENT_ID** and **HUBSPOT_CLIENT_SECRET** from HubSpot Developer Portal
- Create a HubSpot private app with scopes: crm.objects.contacts.read, crm.objects.contacts.write, crm.objects.deals.read, crm.objects.deals.write
- Register webhook subscriptions for contact.creation, contact.propertyChange, deal.creation, deal.propertyChange

## Next Phase Readiness
- Database schema ready for Plan 02 (email sequence service uses email_sequences, email_sequence_steps, email_sequence_enrollments, email_tracking_events tables)
- HubSpotService ready for Plan 03 (agent tool wiring on SalesAgent)
- get_deal_context method ready for CRM-aware agent responses (CRM-05 in Plan 03)

## Self-Check: PASSED

- All 4 files verified present on disk
- Both task commits (214bd75, 84ecb81) verified in git log

---
*Phase: 42-crm-email-automation*
*Completed: 2026-04-04*
