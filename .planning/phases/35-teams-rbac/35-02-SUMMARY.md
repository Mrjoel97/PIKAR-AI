---
phase: 35-teams-rbac
plan: "02"
subsystem: teams-rbac
tags: [api, rbac, react-context, workspace, data-scoping, dashboard]
dependency_graph:
  requires: [workspaces-schema, workspace-service, require-role-middleware, teams-feature-gate]
  provides: [teams-api-router, workspace-context, workspace-data-filter]
  affects: [dashboard-summary, content-api, initiatives-api, frontend-dashboard-layout]
tech_stack:
  added: []
  patterns: [workspace-scoped-queries, react-context-provider, fastapi-router-with-feature-gate, graceful-degradation]
key_files:
  created:
    - app/routers/teams.py
    - frontend/src/contexts/WorkspaceContext.tsx
    - app/services/workspace_data_filter.py
  modified:
    - app/fast_api_app.py
    - frontend/src/app/dashboard/layout.tsx
    - app/services/dashboard_summary_service.py
    - app/routers/content.py
    - app/routers/initiatives.py
decisions:
  - "workspace-scoped reads use .in_() with a single-element list for solo users — no branching required in callers, zero behavioral change for non-team users"
  - "WorkspaceContext defaults all permissions to true when role is null (no workspace) — solo users are never blocked by RBAC checks"
  - "Write/mutate endpoints remain user-specific; only list/read queries are workspace-scoped — data ownership is not changed, only visibility"
  - "normalize_operational_state imported at module level in initiatives.py rather than inline to satisfy ruff I001 import ordering rule"
metrics:
  duration: "~18m"
  completed_date: "2026-04-03"
  tasks_completed: 3
  tasks_total: 3
  files_created: 3
  files_modified: 5
---

# Phase 35 Plan 02: Teams API, WorkspaceContext, and Data Scoping Summary

**One-liner:** FastAPI teams router (6 endpoints, feature+role gated), React WorkspaceContext with permission booleans, and workspace-scoped read queries across dashboard/content/initiatives so invited members see shared data.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Backend teams API router | 865f594 | app/routers/teams.py, app/fast_api_app.py |
| 2 | Frontend WorkspaceContext and dashboard layout wiring | b46cd73 | frontend/src/contexts/WorkspaceContext.tsx, frontend/src/app/dashboard/layout.tsx |
| 3 | Workspace-scoped data access for shared content visibility | 97f5836 | app/services/workspace_data_filter.py, app/services/dashboard_summary_service.py, app/routers/content.py, app/routers/initiatives.py |

## What Was Built

### Task 1: Backend Teams API Router

Created `app/routers/teams.py` with prefix `/teams`, tags `["Teams"]`, and router-level `Depends(require_feature("teams"))` gate (startup+ tier required):

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /teams/workspace` | any member | Get or create workspace; returns role + member_count |
| `GET /teams/members` | any member | List all workspace members |
| `POST /teams/invites` | admin only | Create invite link with configurable role + expiry |
| `POST /teams/invites/accept` | any authenticated | Accept invite token; no workspace required |
| `PATCH /teams/members/{id}/role` | admin only | Change member role |
| `DELETE /teams/members/{id}` | admin only | Remove member |

All Pydantic request/response models defined with field-level validation (`pattern` for role strings, `ge`/`le` bounds for expiry hours). Error handling wraps all service calls with 400/403/404/500 responses. Rate-limited via `@limiter.limit(get_user_persona_limit)`.

Registered in `app/fast_api_app.py` alongside all other routers.

### Task 2: Frontend WorkspaceContext

Created `frontend/src/contexts/WorkspaceContext.tsx` following the exact same pattern as `SubscriptionContext.tsx`:

- `'use client'` directive, `createContext`, Provider + hook exports
- On mount: queries `workspace_members` joined with `workspaces` via Supabase client; falls back gracefully if table absent or query fails
- Derives permission booleans:
  - `canEdit` — admin or editor (or null role = solo user)
  - `canManageTeam` — admin only (or null role = solo user)
  - `canView` — always true
  - `isTeamWorkspace` — memberCount > 1
- `ready` flag set after initial fetch (even on no-workspace result)
- `refresh()` function for manual re-fetch after team changes
- Auth state listener resets context on sign-out

Updated `frontend/src/app/dashboard/layout.tsx` to wrap children in `<WorkspaceProvider>` inside `<SubscriptionProvider>` so all dashboard pages have workspace context without extra imports.

### Task 3: Workspace-Scoped Data Access

**`app/services/workspace_data_filter.py`** — single async function `get_workspace_user_ids(user_id)`:
- Calls `WorkspaceService.get_workspace_for_user()` → `get_workspace_members()`
- Returns list of all co-member user_ids; always includes the requesting user_id
- Gracefully degrades to `[user_id]` on any error (tables not migrated, service failure)
- Design: always returns a non-empty list so callers use `.in_()` unconditionally

**`app/services/dashboard_summary_service.py`** — modified `get_home_summary()` to:
1. Resolve `scoped_user_ids` once at the top (one async call, reused)
2. Pass to 6 internal methods: `_active_workflows`, `_recent_completed_workflows`, `_initiatives`, `_open_tasks`, `_content_queue`, `_reports`
3. Each scoped method: uses `.in_("user_id", scoped_user_ids)` when len > 1, else `.eq("user_id", user_id)` (solo fast path)
4. Methods kept user-specific: `_pending_approvals` (personal), `_brain_dumps` (private), `_compliance_audits`/`_compliance_risks`/`_workflow_execution_audit` (unchanged)

**`app/routers/content.py`** — 3 list endpoints scoped:
- `list_bundles` → workspace-scoped `.in_()` on content_bundles
- `list_deliverables` → workspace-scoped `.in_()` on content_bundle_deliverables
- `list_campaigns` → workspace-scoped `.in_()` on campaigns

**`app/routers/initiatives.py`** — `list_initiatives` endpoint:
- When `len(scoped_user_ids) > 1`: direct Supabase query with `.in_()`, applies same status/phase/priority/limit filters, normalizes via `normalize_operational_state`
- When solo: delegates to `InitiativeService.list_initiatives()` unchanged

## Decisions Made

1. **Uniform `.in_()` pattern with single-element list** — `get_workspace_user_ids` always returns a list, so callers do `if len(scoped_user_ids) > 1` to decide between `.in_()` and `.eq()`. This avoids changing existing code paths for solo users and keeps the fast-path explicit.

2. **Solo users default to all-permissions-true in WorkspaceContext** — When `role` is null (no workspace membership row exists), `canEdit`, `canManageTeam`, and `canView` all return true. RBAC only restricts once a workspace exists, making teams an additive feature.

3. **Read-only scoping; write operations remain user-specific** — Data ownership (the `user_id` column on created records) is not changed. Only list/read queries expand their scope. This preserves data integrity and prevents accidental cross-user data modification.

4. **Top-level import for `normalize_operational_state`** — Initially placed as an inline import inside the workspace branch of `list_initiatives`. Ruff `I001` flagged the unsorted local import. Moved to module-level with the other service imports, which is also the cleaner pattern.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed import of `normalize_operational_state` in initiatives.py**
- **Found during:** Task 3 ruff check
- **Issue:** Plan suggested `from app.services.initiative_service import _normalize_operational_state` but that symbol is a private alias inside initiative_service, not importable from outside. Ruff also flagged the inline local import as unsorted.
- **Fix:** Used the actual source `from app.services.initiative_operational_state import normalize_operational_state` at module level.
- **Files modified:** app/routers/initiatives.py
- **Commit:** 97f5836

### Deferred Items (Pre-existing, Out of Scope)

`app/routers/content.py` and `app/routers/initiatives.py` have pre-existing `B904` ruff violations (raise-without-from in except blocks) across many endpoints. These are not related to this plan's changes and are logged to deferred-items.md.

## Verification Results

- Teams router: 6 routes confirmed (grep on `@router.(get|post|patch|delete)`)
- teams_router registered in fast_api_app.py: PASSED
- WorkspaceProvider and useWorkspace exported: PASSED
- Dashboard layout has WorkspaceProvider: PASSED
- `get_workspace_user_ids` defined in workspace_data_filter.py: PASSED
- Dashboard summary service uses scoped_user_ids: PASSED
- Content router uses get_workspace_user_ids: PASSED
- Initiatives router uses get_workspace_user_ids: PASSED
- Python syntax (py_compile): PASSED on all 4 modified Python files
- Ruff lint on new files (workspace_data_filter.py, teams.py, dashboard_summary_service.py): All checks passed

## Self-Check: PASSED

- `app/routers/teams.py` — FOUND
- `frontend/src/contexts/WorkspaceContext.tsx` — FOUND
- `app/services/workspace_data_filter.py` — FOUND
- commit `865f594` — FOUND
- commit `b46cd73` — FOUND
- commit `97f5836` — FOUND
