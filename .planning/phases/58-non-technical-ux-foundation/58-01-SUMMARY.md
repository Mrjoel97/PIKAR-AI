---
phase: 58-non-technical-ux-foundation
plan: 01
subsystem: ui, api
tags: [fastapi, react, pydantic, suggestions, persona, chat]

# Dependency graph
requires: []
provides:
  - "GET /suggestions endpoint returning persona-aware, time-of-day chips"
  - "SuggestionService with weighted pool selection (persona 3x, time 2x, activity reserved)"
  - "SuggestionChips React component with backend fetch and 30s cache"
  - "fetchSuggestions frontend API client"
affects: [58-non-technical-ux-foundation, chat-interface]

# Tech tracking
tech-stack:
  added: []
  patterns: [weighted-pool-selection, reserved-slot-guarantees, in-memory-cache-30s]

key-files:
  created:
    - app/services/suggestion_service.py
    - app/routers/suggestions.py
    - frontend/src/services/suggestions.ts
    - frontend/src/components/chat/SuggestionChips.tsx
    - tests/unit/app/services/test_suggestion_service.py
  modified:
    - app/fast_api_app.py
    - frontend/src/components/chat/ChatInterface.tsx

key-decisions:
  - "Reserved slot for activity followups to guarantee at least one appears when activity data exists"
  - "Used get_current_user_id (existing pattern) instead of verify_token directly to satisfy ruff B008"
  - "Chips show only on fresh sessions (messages.length === 0) to avoid stale suggestions mid-conversation"

patterns-established:
  - "Weighted pool selection: persona (3x), time-of-day (2x), activity followup (reserved slot)"
  - "Frontend suggestion cache: 30s TTL keyed by persona, avoids refetch per render"

requirements-completed: [NTUX-01]

# Metrics
duration: 9min
completed: 2026-04-09
---

# Phase 58 Plan 01: Suggestion Chips Summary

**Backend-driven persona-aware suggestion chip system replacing hardcoded displaySuggestions with weighted pool selection across persona, time-of-day, and activity dimensions**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-09T23:00:39Z
- **Completed:** 2026-04-09T23:10:08Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Backend SuggestionService with 4 persona pools (12 suggestions each), 3 time-of-day buckets (7 each), and 6 activity follow-up categories
- GET /suggestions endpoint with auth, persona/hour/recent_activity query params
- SuggestionChips React component with graceful fallback to generic suggestions on fetch failure
- Removed hardcoded displaySuggestions useMemo and userJourneys fetch from ChatInterface
- All 5 backend tests pass; TypeScript compiles cleanly

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests** - `52199e9` (test)
2. **Task 1 (GREEN): Backend service + router** - `aa645ad` (feat)
3. **Task 2: Frontend SuggestionChips + ChatInterface refactor** - `660c8a4` (feat)

## Files Created/Modified
- `app/services/suggestion_service.py` - SuggestionService with weighted pool selection and persona/time/activity pools
- `app/routers/suggestions.py` - GET /suggestions endpoint with auth
- `app/fast_api_app.py` - Router registration for suggestions
- `frontend/src/services/suggestions.ts` - fetchSuggestions API client with 30s cache
- `frontend/src/components/chat/SuggestionChips.tsx` - Reusable chip strip component
- `frontend/src/components/chat/ChatInterface.tsx` - Replaced hardcoded suggestions with SuggestionChips
- `tests/unit/app/services/test_suggestion_service.py` - 5 tests covering all service behaviors

## Decisions Made
- Reserved a slot for activity followup suggestions to guarantee at least one appears when activity data exists (pure weighted shuffle was drowning them out)
- Used `get_current_user_id` from onboarding module rather than `Depends(verify_token)` directly to match project convention and satisfy ruff B008
- Chips display only on fresh sessions (messages.length === 0) -- mid-conversation contextual suggestions deferred to future iteration

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Activity followups drowned out by weighted shuffle**
- **Found during:** Task 1 (GREEN phase, test_activity_followup_includes_related_suggestion)
- **Issue:** Activity followups at weight 1 were consistently shuffled behind persona (3x) and time (2x) entries, never making it into the top 6
- **Fix:** Implemented reserved-slot approach: extract one random activity followup first, then fill remaining slots from the weighted main pool
- **Files modified:** app/services/suggestion_service.py
- **Verification:** All 5 tests pass including activity followup test
- **Committed in:** aa645ad (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Essential fix for activity followup visibility. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Suggestion chip backend and frontend are fully wired
- Future iterations can add: mid-session contextual suggestions, user journey integration, usage-based personalization
- Ready for 58-02 (intent clarification) and 58-03 (TL;DR mode) plans

## Self-Check: PASSED

All 6 created files exist. All 3 task commits verified in git log.

---
*Phase: 58-non-technical-ux-foundation*
*Completed: 2026-04-09*
