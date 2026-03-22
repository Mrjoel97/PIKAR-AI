---
phase: 11-external-integrations
plan: "03"
subsystem: ui
tags: [react, nextjs, tailwind, typescript, integrations, admin]

# Dependency graph
requires:
  - phase: 11-01
    provides: GET/PUT/DELETE /admin/integrations and POST /admin/integrations/{provider}/test API endpoints

provides:
  - /admin/integrations page with 2-column provider card grid
  - ProviderCard component with status badge, masked key, health dot, Configure + Test Connection buttons
  - ConfigureModal component with encrypted-at-rest API key entry, base URL (PostHog), and provider-specific config fields

affects:
  - 11-04 (any future integration UI iteration)
  - Phase 13 (audit trail for config changes visible in admin)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Provider list always shows all 4 cards — API missing entries replaced with defaultEntry placeholders
    - API key input is password-type and never pre-filled — security boundary enforced at component level
    - PROVIDER_FIELDS constant map drives dynamic field rendering per provider
    - Test-result banner auto-dismisses via setTimeout(5000) — no manual dismiss required
    - handleSave only includes api_key in payload when user enters non-empty value

key-files:
  created:
    - frontend/src/components/admin/integrations/ProviderCard.tsx
    - frontend/src/components/admin/integrations/ConfigureModal.tsx
    - frontend/src/app/(admin)/integrations/page.tsx

key-decisions:
  - "11-03: PROVIDER_FIELDS constant map in ConfigureModal drives dynamic extra-field rendering — adding a new provider requires only one map entry"
  - "11-03: API key never pre-filled in ConfigureModal (password type, empty on open) — only last-4 shown in ProviderCard after save"
  - "11-03: defaultEntry() fills missing providers with is_active=false placeholders — UI always shows all 4 cards regardless of API response"
  - "11-03: handleSave omits api_key from PUT payload if field is empty — allows updating config-only fields without rotating an existing key"

patterns-established:
  - "Merge-with-defaults pattern: ALL_PROVIDERS constant + Map lookup + defaultEntry fallback ensures full provider grid even on empty API response"
  - "Modal security pattern: password-type API key input, empty on open, only conditionally included in PUT payload"

requirements-completed: [INTG-01, INTG-02, INTG-03, INTG-04, INTG-05]

# Metrics
duration: 4min
completed: 2026-03-22
---

# Phase 11 Plan 03: External Integrations UI Summary

**Admin integrations page with ProviderCard grid and ConfigureModal — API key entry, provider-specific config fields, and Test Connection pass/fail banner**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-22T15:54:53Z
- **Completed:** 2026-03-22T15:58:41Z
- **Tasks:** 3 of 3
- **Files modified:** 3

## Accomplishments

- ProviderCard component renders provider name, description, green/gray connection badge, masked key (`****...last4`), health status dot, and Configure + Test Connection buttons
- ConfigureModal with password-type API key (never pre-filled), PostHog-only base URL field, and PROVIDER_FIELDS-driven extra config inputs pre-filled from existing config
- IntegrationsPage merges API response with ALL_PROVIDERS constant so all 4 cards always render, handles save + test + auto-dismiss result banner

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ProviderCard and ConfigureModal components** - `0b285bf` (feat)
2. **Task 2: Create /admin/integrations page wiring cards and modal to API** - `58e3e63` (feat)
3. **Task 3: Verify integrations page renders correctly** - checkpoint approved by user (human-verify)

## Files Created/Modified

- `frontend/src/components/admin/integrations/ProviderCard.tsx` — Provider card with status badge, health dot, masked key display, Configure/Test Connection buttons
- `frontend/src/components/admin/integrations/ConfigureModal.tsx` — Modal with password API key input, PostHog base URL, PROVIDER_FIELDS-driven extra fields, Save/Cancel
- `frontend/src/app/(admin)/integrations/page.tsx` — Page component: fetch all integrations, merge with ALL_PROVIDERS defaults, handleSave (PUT), handleTestConnection (POST + 5s auto-dismiss banner)

## Decisions Made

- PROVIDER_FIELDS constant map in ConfigureModal drives dynamic extra-field rendering — adding a new provider requires only one map entry update
- API key never pre-filled (password type, empty on open) — only last-4 shown in ProviderCard after save — enforces security boundary in the component layer
- defaultEntry() fills missing providers with `is_active: false` placeholders — UI always shows all 4 provider cards regardless of what the API returns
- handleSave omits `api_key` from PUT payload if field is empty — allows updating config-only fields without rotating an existing key

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required for the frontend components themselves.

## Next Phase Readiness

- /admin/integrations page is accessible via the existing sidebar nav (`{ label: 'Integrations', href: '/admin/integrations', icon: Plug }`)
- All 4 provider cards render; configure modal and test connection are wired to Plan 01 API endpoints
- Human verification completed (Task 3 checkpoint approved) — plan is fully complete

---
*Phase: 11-external-integrations*
*Completed: 2026-03-22*
