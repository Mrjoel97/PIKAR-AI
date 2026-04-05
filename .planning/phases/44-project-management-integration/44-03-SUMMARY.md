---
phase: 44-project-management-integration
plan: 03
subsystem: api
tags: [linear, asana, pm-sync, agent-tools, operations-agent, react, typescript]

# Dependency graph
requires:
  - phase: 44-01
    provides: LinearService, AsanaService, PMSyncService, pm_sync_service endpoints
  - phase: 44-02
    provides: Webhook handlers, sync state management, integration_sync_state
provides:
  - PM_TASK_TOOLS: 5 agent tools for Linear/Asana task management from OperationsAgent
  - PMSyncSection: frontend project picker and status mapping UI for Linear/Asana cards
  - Auto-detect provider logic for single-connected-PM-tool UX
affects:
  - operations-agent
  - configuration-page
  - any phase adding more PM tool features

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Auto-detect connected PM provider (single → use it; both → ask; none → error)
    - Redis skip-flag set before local insert in create_pm_task to prevent webhook echo
    - PM props pattern: same conditional-prop pattern as ad platform budget cap props in IntegrationProviderCard
    - Collapsible status mapping section using AnimatePresence + ChevronDown/ChevronRight (matches existing patterns)

key-files:
  created:
    - app/agents/tools/pm_task_tools.py
    - .planning/phases/44-project-management-integration/44-03-SUMMARY.md
  modified:
    - app/agents/operations/agent.py
    - frontend/src/app/dashboard/configuration/page.tsx

key-decisions:
  - "PM_TASK_TOOLS exported as a list (matches AD_PLATFORM_TOOLS pattern), added via *PM_TASK_TOOLS spread in OPERATIONS_AGENT_TOOLS"
  - "PMSyncSection accepts all PM props from IntegrationProviderCard rather than fetching independently — avoids duplicate API calls"
  - "Frontend fetches PM projects/config/mappings only for connected PM providers (checked against integrationStatuses on mount)"
  - "handleSavePMSync re-fetches status mappings after save since server seeds them from selected projects"

patterns-established:
  - "PM prop passthrough: PM_PROVIDER_KEYS.has(p.key) gates every PM prop — identical to AD_PLATFORM_KEYS pattern for budget caps"
  - "Provider auto-detect: _detect_provider helper used by all 5 tools; explicit provider= arg always overrides"

requirements-completed: [PM-01, PM-02, PM-03, PM-04, PM-05]

# Metrics
duration: 11min
completed: 2026-04-05
---

# Phase 44 Plan 03: Project Management Integration — Agent Tools & Frontend UI Summary

**PM_TASK_TOOLS wired into OperationsAgent with auto-provider detection, plus frontend project picker and collapsible status mapping dropdowns on Linear/Asana configuration cards**

## Performance

- **Duration:** 11 min
- **Started:** 2026-04-05T13:00:08Z
- **Completed:** 2026-04-05T13:11:27Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- 5 PM agent tools (get_pm_projects, list_pm_tasks, create_pm_task, update_pm_task, get_pm_sync_status) covering full CRUD with bidirectional sync and Redis loop prevention
- OperationsAgent updated with PM tool import, tool list entry, and PM-specific instruction block guiding auto-detect and project-first workflow
- Frontend configuration page shows project checkboxes (Save & Sync) and collapsible status mapping dropdowns (Save Mappings) on Linear/Asana provider cards when expanded

## Task Commits

1. **Task 1: PM task agent tools** - `8cfca1f` (feat)
2. **Task 2: Wire OperationsAgent + frontend project picker and status mapping UI** - `0c3e083` (feat)

**Plan metadata:** `[pending final commit]` (docs: complete plan)

## Files Created/Modified

- `app/agents/tools/pm_task_tools.py` - 5 agent-callable async tools with _detect_provider helper and PM_TASK_TOOLS export list (575 lines)
- `app/agents/operations/agent.py` - Added PM_TASK_TOOLS import, *PM_TASK_TOOLS in OPERATIONS_AGENT_TOOLS, PM instruction block
- `frontend/src/app/dashboard/configuration/page.tsx` - Added PMSyncSection component, PM state, PM handlers, PM_PROVIDER_KEYS, PM type interfaces, wired props into IntegrationProviderCard

## Decisions Made

- PMSyncSection renders inside IntegrationProviderCard's expandable area, receiving all data as props — avoids duplicate fetch calls and matches the existing BudgetCapSection prop pattern
- After saving PM sync config (which seeds status mappings on the backend), the frontend re-fetches mappings automatically so the status mapping section populates without a page refresh
- Frontend fetches PM data only for providers that are already connected (checked via integrationStatuses), avoiding 401 errors on unconnected providers

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Ruff E501 (line-length) flagged 3 lines in pm_task_tools.py during Task 1 verification — fixed inline before commit (string wrapping, removed spurious f-prefix)
- Pre-existing E501 errors in OPERATIONS_AGENT_INSTRUCTION string (long natural language text) are out of scope per deviation rules; they existed before this plan

## User Setup Required

None — no external service configuration required beyond what Plans 01 and 02 established.

## Next Phase Readiness

- Phase 44 complete: LinearService, AsanaService, PMSyncService, webhook handlers, agent tools, and frontend UI all in place
- Users can now say "create a ticket in Linear for the auth bug" and OperationsAgent will call get_pm_projects, create_pm_task simultaneously in Linear and synced_tasks, and return a link
- Frontend configuration page shows project picker and status mapping on Linear/Asana cards after OAuth connection
- Ready for Phase 45 or any phase that builds on PM task data (e.g., reporting, workflow automation with PM tasks)

---
*Phase: 44-project-management-integration*
*Completed: 2026-04-05*
