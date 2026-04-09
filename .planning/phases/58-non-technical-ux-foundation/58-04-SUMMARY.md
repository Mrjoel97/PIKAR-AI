---
phase: 58-non-technical-ux-foundation
plan: 04
subsystem: ui, api
tags: [workflow-discovery, natural-language, template-gallery, fastapi, react, pydantic]

# Dependency graph
requires:
  - phase: 58-01
    provides: suggestions router and frontend API client
provides:
  - WorkflowDiscoveryService with NL keyword/fuzzy matching
  - GET /suggestions/workflows endpoint for NL workflow search
  - GET /suggestions/templates endpoint for browsable gallery data
  - WorkflowLauncher component with confidence indicators and one-click launch
  - TemplateGallery component with category filtering and icon grid
  - ChatInterface NL intent detection with parallel workflow search
affects: [workflow-engine, chat-interface, content-creation]

# Tech tracking
tech-stack:
  added: []
  patterns: [lazy-engine-accessor, NL-keyword-scoring, client-side-intent-detection, auto-dismiss-timer]

key-files:
  created:
    - app/services/workflow_discovery_service.py
    - frontend/src/components/chat/WorkflowLauncher.tsx
    - frontend/src/components/chat/TemplateGallery.tsx
    - tests/unit/app/services/test_workflow_discovery_service.py
  modified:
    - app/routers/suggestions.py
    - frontend/src/services/suggestions.ts
    - frontend/src/components/chat/ChatInterface.tsx

key-decisions:
  - "Lazy _get_engine() wrapper instead of module-level import to avoid circular deps with workflow engine"
  - "Client-side intent detection (prefix matching) for workflow NL search to avoid extra backend round-trip"
  - "15-second auto-dismiss timer for WorkflowLauncher to prevent stale suggestions"

patterns-established:
  - "Lazy engine accessor: _get_engine() pattern for testable service-to-engine coupling"
  - "NL keyword scoring: tokenize, strip stopwords, score by keyword overlap + substring bonus"
  - "Icon string mapping: ICON_MAP dict mapping string names to lucide-react components"

requirements-completed: [NTUX-04, NTUX-05]

# Metrics
duration: 8min
completed: 2026-04-09
---

# Phase 58 Plan 04: Workflow Discovery & Template Gallery Summary

**NL workflow search with keyword scoring against engine templates, plus a 12-template visual gallery with category filtering and one-click launch**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-09T23:17:29Z
- **Completed:** 2026-04-09T23:25:09Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- WorkflowDiscoveryService with tokenization, stopword removal, and keyword/substring scoring
- 12 curated content templates (Product Launch, Blog, Newsletter, Video Ad, Email Sequence, etc.)
- Two new authenticated API endpoints on /suggestions router (workflows search + templates gallery)
- WorkflowLauncher component with confidence dots, category badges, and Start Workflow buttons
- TemplateGallery with category filter chips, icon-mapped card grid, and skeleton loading
- ChatInterface integration: NL intent detection triggers parallel search; Browse Templates button

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests** - `aff29737` (test)
2. **Task 1 (GREEN): Service + endpoints + tests pass** - `e28fff1f` (feat)
3. **Task 2: Frontend components + ChatInterface integration** - `d28bbd60` (feat)

## Files Created/Modified
- `app/services/workflow_discovery_service.py` - NL search service with keyword scoring and 12 content templates
- `app/routers/suggestions.py` - Extended with /workflows and /templates endpoints
- `tests/unit/app/services/test_workflow_discovery_service.py` - 6 unit tests for NL search and template retrieval
- `frontend/src/services/suggestions.ts` - Added searchWorkflows and fetchContentTemplates API clients
- `frontend/src/components/chat/WorkflowLauncher.tsx` - Inline workflow match panel with one-click launch
- `frontend/src/components/chat/TemplateGallery.tsx` - Browsable template grid with category filters
- `frontend/src/components/chat/ChatInterface.tsx` - NL intent detection, WorkflowLauncher/TemplateGallery rendering

## Decisions Made
- Used lazy `_get_engine()` wrapper to avoid circular import between service and workflow engine while keeping tests patchable
- Client-side intent detection via prefix matching ("I want to", "Help me", etc.) to trigger parallel workflow search without extra backend latency
- 15-second auto-dismiss timer for WorkflowLauncher to prevent stale suggestions cluttering the input area
- Icon string-to-component mapping (`ICON_MAP`) in TemplateGallery for dynamic icon rendering from backend data

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed mock patch target for workflow engine**
- **Found during:** Task 1 (TDD GREEN phase)
- **Issue:** Plan called for local import of `get_workflow_engine` inside `search_workflows_by_intent`, making it unpatchable at test time
- **Fix:** Created `_get_engine()` module-level accessor that wraps the lazy import, making it easily patchable
- **Files modified:** `app/services/workflow_discovery_service.py`, `tests/unit/app/services/test_workflow_discovery_service.py`
- **Verification:** All 6 tests pass
- **Committed in:** e28fff1f

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary for testability. No scope creep.

## Issues Encountered
None beyond the mock patching issue resolved above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Wave 2 Plan 04 complete; all NL discovery and template gallery features operational
- Templates and workflow search ready for consumption by other Wave 2 plans
- ChatInterface now supports both contextual workflow suggestions and browsable template gallery

---
*Phase: 58-non-technical-ux-foundation*
*Completed: 2026-04-09*
