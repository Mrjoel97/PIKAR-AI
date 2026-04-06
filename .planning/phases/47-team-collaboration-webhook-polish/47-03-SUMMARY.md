---
phase: 47-team-collaboration-webhook-polish
plan: 03
subsystem: agent-tools, frontend
tags: [webhooks, operations-agent, react, nextjs, tailwind, tdd, team-analytics]

requires:
  - phase: 47-team-collaboration-webhook-polish-01
    provides: outbound webhook REST API, EVENT_CATALOG, VERIFICATION_SNIPPETS
  - phase: 47-team-collaboration-webhook-polish-02
    provides: TeamAnalyticsService, /teams/analytics, /teams/shared/*, /teams/activity

provides:
  - WEBHOOK_TOOLS list (5 functions) wired to OperationsAgent
  - WebhooksSection in configuration page (endpoint CRUD, event picker, delivery log, signing snippets)
  - Team analytics dashboard with KPI tiles, member breakdown, shared work tabs, activity feed

affects:
  - app/agents/operations/agent.py (WEBHOOK_TOOLS added to OPERATIONS_AGENT_TOOLS)
  - frontend/src/app/dashboard/configuration/page.tsx (WebhooksSection added)
  - frontend/src/app/dashboard/team/page.tsx (full dashboard overhaul)

tech-stack:
  added: []
  patterns:
    - "Lazy import pattern for agent tools — sanitize_tools handles FunctionTool wrapping"
    - "Explicit secret stripping in list_webhook_endpoints — defensive even with SELECT column filter"
    - "sys.modules stub for app.agents.specialized_agents prevents google.adk cascade in tests"
    - "Patch at source module (app.services.supabase) not tool module — lazy imports have no module-level attribute"
    - "TeamAnalytics component replaces TeamPageContent — same GatedPage + PremiumShell wrapper kept"
    - "loadedTabs Set tracks which SharedWork tabs have been fetched — prevents redundant API calls on re-tab"

key-files:
  created:
    - app/agents/tools/webhook_tools.py
  modified:
    - app/agents/operations/agent.py
    - frontend/src/app/dashboard/configuration/page.tsx
    - frontend/src/app/dashboard/team/page.tsx
    - tests/unit/test_outbound_webhooks.py

key-decisions:
  - "Patch at source module not tool module — lazy imports inside functions have no module-level attribute to patch"
  - "Stub app.agents.specialized_agents (not app.agents package) to prevent google.adk/supabase.Client import cascade"
  - "list_webhook_endpoints explicitly strips secret key from rows even though SELECT excludes it — defensive contract"
  - "VERIFICATION_SNIPPETS hardcoded in frontend as const object — static strings, no API call needed"
  - "SharedWork uses loadedTabs Set to lazy-load tabs on first switch, never refetch on subsequent switch"
  - "MemberBreakdown renders null when member_breakdown is null/empty (non-admin user) — no skeleton shown"

patterns-established:
  - "Agent tools for webhook management follow lazy-import + raw-function-export pattern (no FunctionTool wrapper)"
  - "Ownership check before any mutation in agent tools mirrors router-layer pattern"

requirements-completed: [HOOK-05, TEAM-01, TEAM-02, TEAM-03, TEAM-04]

duration: 19min
completed: 2026-04-06
---

# Phase 47 Plan 03: Webhook Agent Tools + Frontend Dashboard Summary

**WEBHOOK_TOOLS on OperationsAgent enabling chat-based webhook management, WebhooksSection with full endpoint CRUD and signing verification snippets, and team analytics dashboard with KPI tiles, member breakdown, shared work tabs, and resource-grouped activity feed**

## Performance

- **Duration:** 19 min
- **Started:** 2026-04-06T05:11:44Z
- **Completed:** 2026-04-06T05:30:44Z
- **Tasks:** 2
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- Created `app/agents/tools/webhook_tools.py` with 5 agent-callable async functions following the `communication_tools.py` pattern: `list_webhook_endpoints`, `create_webhook_endpoint`, `delete_webhook_endpoint`, `list_webhook_events`, `get_webhook_delivery_log`. All use lazy imports; secrets are never exposed in list results; ownership checked before delete/delivery operations
- Wired `WEBHOOK_TOOLS` into `OPERATIONS_AGENT_TOOLS` via `*WEBHOOK_TOOLS` spread (Phase 47 comment) and added webhook management instructions to the operations agent
- Added `WebhooksSection` to `configuration/page.tsx` after MonitoringJobsSection: endpoint list with active toggle/test-send/delete/view-logs, create form with multi-select event catalog, once-only secret display with copy button and "won't be shown again" warning, delivery log panel with color-coded status, expandable signing verification snippets in Node.js/Python/cURL tabs
- Rewrote `team/page.tsx` as full team analytics dashboard: `TeamKPITiles` (6-tile responsive grid from `/teams/analytics`), `MemberBreakdown` (collapsible admin-only per-member table), `SharedWork` (tabbed initiatives/workflows with lazy tab loading), `ActivityFeed` (resource-grouped clusters with relative timestamps), then existing TeamMemberList/InviteLinkGenerator/RoleInfoCard below
- 9 `TestWebhookTools` tests added to `test_outbound_webhooks.py` — all pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Webhook agent tools on OperationsAgent** — `4d74796` (feat)
2. **Task 2: WebhooksSection + team analytics dashboard UI** — `1f1910e` (feat)

## Files Created/Modified

- `app/agents/tools/webhook_tools.py` — WEBHOOK_TOOLS with 5 async functions (list, create, delete endpoints; list events; delivery log)
- `app/agents/operations/agent.py` — Added WEBHOOK_TOOLS import + spread + instructions
- `frontend/src/app/dashboard/configuration/page.tsx` — WebhooksSection component + 3 new TypeScript interfaces (WebhookEndpoint, WebhookEvent, WebhookDelivery)
- `frontend/src/app/dashboard/team/page.tsx` — Full rewrite: TeamAnalytics, TeamKPITiles, MemberBreakdown, SharedWork, ActivityFeed components
- `tests/unit/test_outbound_webhooks.py` — TestWebhookTools class (9 tests)

## Decisions Made

- Patch at source module (`app.services.supabase`) not tool module for mock targets — lazy imports inside functions leave no module-level attribute to patch
- Stub `app.agents.specialized_agents` in sys.modules before tests to prevent `google.adk` cascade triggered by `app/agents/__init__.py` imports
- `list_webhook_endpoints` explicitly strips `secret` key from rows even though the SELECT column list already excludes it — defensive contract that survives future SELECT changes
- `VERIFICATION_SNIPPETS` hardcoded in frontend as `const` — static strings matching Plan 01's `webhook_events.py` values, no API round-trip needed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Patched at source module instead of tool module**
- **Found during:** Task 1 TDD GREEN phase
- **Issue:** `patch("app.agents.tools.webhook_tools.get_service_client")` raised `AttributeError` — lazy imports inside function bodies have no module-level attribute
- **Fix:** Changed all `patch()` targets to `app.services.supabase.get_service_client` and `app.services.supabase_async.execute_async` (the actual module-level names)
- **Files modified:** `tests/unit/test_outbound_webhooks.py`
- **Verification:** 9 TestWebhookTools tests pass

**2. [Rule 3 - Blocking] Stubbed app.agents.specialized_agents to prevent google.adk import cascade**
- **Found during:** Task 1 TDD GREEN phase
- **Issue:** Importing `app.agents.tools.webhook_tools` triggers `app/agents/__init__.py` which imports `specialized_agents` which imports all agent modules which require `google.adk` (not installed in test environment)
- **Fix:** Added `sys.modules.setdefault("app.agents.specialized_agents", _mock_specialized)` stub at top of test file — pre-populates module before `__init__.py` tries to import it
- **Files modified:** `tests/unit/test_outbound_webhooks.py`
- **Verification:** Import resolves cleanly, all 9 tests pass

**3. [Rule 1 - Bug] Explicitly strip `secret` key in list_webhook_endpoints**
- **Found during:** Task 1 TDD GREEN phase  
- **Issue:** Mock returns full DB row including `secret` field; SELECT column filter only applies to real DB calls. Test assertion `assert "secret" not in ep` would fail with raw row passthrough
- **Fix:** Added dict comprehension to strip `secret` key from all rows before returning
- **Files modified:** `app/agents/tools/webhook_tools.py`
- **Verification:** `test_list_endpoints_returns_user_endpoints` passes

---

**Total deviations:** 3 auto-fixed (2x Rule 3 blocking, 1x Rule 1 bug)
**Impact on plan:** All fixes resolve test environment compatibility issues. No scope change.

## User Setup Required

None — all new features consume existing API endpoints (Plans 01 and 02). No migrations, env vars, or external service configuration needed.

## Next Phase Readiness

- Phase 47 is now complete: all 3 plans done (01: webhook API, 02: team analytics backend, 03: agent tools + frontend UI)
- All 5 HOOK/TEAM requirements marked complete: HOOK-01 through HOOK-05, TEAM-01 through TEAM-04

---
*Phase: 47-team-collaboration-webhook-polish*
*Completed: 2026-04-06*
