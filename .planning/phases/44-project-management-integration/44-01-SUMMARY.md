---
phase: 44-project-management-integration
plan: 01
subsystem: api
tags: [linear, asana, graphql, rest, httpx, supabase, redis, postgresql, rls, oauth2, bidirectional-sync]

# Dependency graph
requires:
  - phase: 39-integration-infrastructure
    provides: IntegrationManager.get_valid_token, OAuth credential storage, PROVIDER_REGISTRY
  - phase: 42-hubspot-crm-integration
    provides: Redis skip-flag loop prevention pattern, AdminService upsert pattern

provides:
  - synced_tasks table with RLS, indexes, moddatetime trigger
  - pm_status_mappings table with RLS and per-user customisation
  - LinearService: GraphQL client for teams, issues (CRUD), workflow states
  - AsanaService: REST client for workspaces, projects, tasks (CRUD), sections, move_task_to_section
  - PMSyncService: bidirectional sync orchestrator with status mapping, Redis skip-flag, last-write-wins
  - Integration router endpoints: /projects, /sync-config (GET/PUT), /status-mappings (GET/PUT)

affects:
  - 44-02 (webhook handlers will call PMSyncService.sync_from_external)
  - 44-03 (agent tools will use PMSyncService and LinearService/AsanaService directly)

# Tech tracking
tech-stack:
  added: [httpx (already present), Linear GraphQL API, Asana REST API v1.0]
  patterns:
    - httpx.AsyncClient with 30s timeout for all external API calls
    - IntegrationManager.get_valid_token for OAuth token resolution
    - Redis skip-flag pikar:pm:skip:{provider}:{external_id} TTL 30s for bidirectional echo prevention
    - AdminService for all synced_tasks/pm_status_mappings writes (service role bypasses RLS for sync)
    - Last-write-wins conflict resolution (logged, not blocked)
    - Lazy imports for provider-specific services inside PMSyncService to avoid circular imports

key-files:
  created:
    - supabase/migrations/20260405950000_pm_integration.sql
    - app/services/linear_service.py
    - app/services/asana_service.py
    - app/services/pm_sync_service.py
  modified:
    - app/routers/integrations.py

key-decisions:
  - "PM sync uses same Redis skip-flag pattern as HubSpot (pikar:pm:skip:{provider}:{external_id}, 30s TTL) for loop prevention"
  - "Linear state.type drives default mappings (triage/backlog/unstarted → pending, started → in_progress, completed → completed, cancelled → cancelled)"
  - "Asana sections serve as workflow statuses; section name keyword matching drives default mappings"
  - "PMSyncService lazy-imports LinearService/AsanaService to prevent circular dependencies"
  - "Status mapping upsert uses ignore_duplicates=True so seeding never overwrites user customisations"
  - "External project_id stored in synced_tasks as external_project_id TEXT for multi-project queries"

patterns-established:
  - "PM provider guard: _PM_PROVIDERS = frozenset({'linear', 'asana'}) mirrors _AD_PLATFORMS pattern in integrations router"
  - "GraphQL client pattern: _graphql() helper resolves token, POSTs, raises on errors field"
  - "Asana REST pattern: _get/_post/_put helpers share token resolution and base URL"

requirements-completed: [PM-01, PM-02, PM-03, PM-04]

# Metrics
duration: 12min
completed: 2026-04-05
---

# Phase 44 Plan 01: PM Integration Foundation Summary

**Linear GraphQL client, Asana REST client, and bidirectional sync orchestrator with Redis skip-flag loop prevention, per-user status mapping, and five integration router endpoints**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-05T12:26:05Z
- **Completed:** 2026-04-05T12:37:33Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Database schema: `synced_tasks` + `pm_status_mappings` tables with full RLS, indexes on (user_id), (user_id, provider), (user_id, provider, status), and moddatetime trigger
- `LinearService`: GraphQL client with `list_teams`, `list_issues` (paginated, incremental), `create_issue`, `update_issue`, `list_workflow_states` — all using `IntegrationManager.get_valid_token`
- `AsanaService`: REST client with workspace/project listing, task CRUD, section listing, and `move_task_to_section` for status-as-section changes
- `PMSyncService`: full bidirectional orchestrator — status mapping seeding/CRUD, `sync_from_external` (with Redis skip-flag), `sync_to_external` (with pre-call skip-flag), `initial_sync` (30-day bulk import), `save_sync_config` (persists + seeds + syncs)
- Integration router: `GET /{provider}/projects`, `GET/PUT /{provider}/sync-config`, `GET/PUT /{provider}/status-mappings` for both Linear and Asana

## Task Commits

Each task was committed atomically:

1. **Task 1: Database migration for synced_tasks and pm_status_mappings** - `ea0d4a8` (feat)
2. **Task 2: Linear service + Asana service + PM sync service + integration endpoints** - `6d1d848` (feat)

## Files Created/Modified

- `supabase/migrations/20260405950000_pm_integration.sql` — synced_tasks + pm_status_mappings schema, RLS, indexes, moddatetime trigger
- `app/services/linear_service.py` — LinearService GraphQL client (429 lines)
- `app/services/asana_service.py` — AsanaService REST client (426 lines)
- `app/services/pm_sync_service.py` — PMSyncService bidirectional orchestrator (731 lines)
- `app/routers/integrations.py` — Added _PM_PROVIDERS guard, SyncConfigRequest/StatusMappingItem schemas, 5 PM endpoints

## Decisions Made

- PM sync uses the same Redis skip-flag pattern as HubSpot (`pikar:pm:skip:{provider}:{external_id}`, 30s TTL) for bidirectional loop prevention
- Linear `state.type` drives default status mappings (triage/backlog/unstarted → pending, started → in_progress, completed → completed, cancelled → cancelled)
- Asana sections serve as workflow statuses; section name keyword matching drives default mappings
- `PMSyncService` lazy-imports `LinearService`/`AsanaService` inside methods to prevent circular dependencies
- Status mapping upsert uses `ignore_duplicates=True` so seeding never overwrites user customisations
- `AdminService` used for all synced_tasks/pm_status_mappings writes so background sync tasks work without a user JWT

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused `filter_clause` variable in LinearService.list_issues**
- **Found during:** Task 2 (LinearService implementation)
- **Issue:** `filter_clause` string was assigned but never used in the GraphQL query after refactoring; Ruff F841 violation
- **Fix:** Removed both the initial assignment (`filter_clause = ""`) and the conditional assignment inside `if updated_after:`
- **Files modified:** `app/services/linear_service.py`
- **Verification:** `ruff check` returned zero errors on new files
- **Committed in:** `6d1d848` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Minor cleanup only, no scope change.

## Issues Encountered

- Ruff E501 on line 177 of `linear_service.py` (GraphQL query signature too long) — fixed by splitting the variable declaration across two lines within the triple-quoted string
- Ruff E501 on `integrations.py` line 1005 (comment too long) — fixed by moving the comment to a dedicated line above the value
- Pre-existing E501 in `_oauth_budget_cap_prompt_html` HTML string literal (was present before Phase 44) — out of scope, left as-is

## User Setup Required

External services require manual configuration:

**Linear:**
- `LINEAR_CLIENT_ID` and `LINEAR_CLIENT_SECRET` from Linear Settings → API → OAuth Applications
- Create OAuth application with redirect URI: `/integrations/linear/callback`
- Create webhook pointing to `/webhooks/linear` with Issue events enabled

**Asana:**
- `ASANA_CLIENT_ID` and `ASANA_CLIENT_SECRET` from Asana Developer Console → My Apps
- Create OAuth app with redirect URI: `/integrations/asana/callback`

## Next Phase Readiness

- Database schema and service layer complete — Phase 44-02 (webhook handlers) can call `PMSyncService.sync_from_external` directly
- `PMSyncService.sync_to_external` ready for Phase 44-03 (agent tools) to call when agents update task status
- Status mapping endpoints allow frontend to build mapping UI before agent tools are wired up
- Linear and Asana must be in PROVIDER_REGISTRY (verify in `app/config/integration_providers.py`) before OAuth flows can be tested

## Self-Check: PASSED

All created files exist on disk. Both task commits (ea0d4a8, 6d1d848) confirmed in git log.

---
*Phase: 44-project-management-integration*
*Completed: 2026-04-05*
