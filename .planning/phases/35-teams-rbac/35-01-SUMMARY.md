---
phase: 35-teams-rbac
plan: "01"
subsystem: teams-rbac
tags: [database, rbac, middleware, feature-gating, workspaces]
dependency_graph:
  requires: []
  provides: [workspaces-schema, workspace-service, require-role-middleware, teams-feature-gate]
  affects: [feature-gating, supabase-migrations, fastapi-middleware]
tech_stack:
  added: []
  patterns: [dependency-factory, service-role-client, rls-helper-functions, execute-async]
key_files:
  created:
    - supabase/migrations/20260403200000_teams_rbac.sql
    - app/services/workspace_service.py
    - app/middleware/workspace_role.py
  modified:
    - app/config/feature_gating.py
    - frontend/src/config/featureGating.ts
decisions:
  - "Application-layer isolation: workspace_members defines who shares data; no workspace_id columns added to existing tables (initiatives, campaigns, etc.) in this migration"
  - "Admin cannot be assigned via invite token — owner is always admin; invite roles limited to editor/viewer"
  - "Solo users without a workspace pass require_role checks without restriction — team RBAC only applies once a workspace exists"
  - "require_role follows the same dependency-factory pattern as require_feature for API consistency"
metrics:
  duration: "5m 31s"
  completed_date: "2026-04-03"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 2
---

# Phase 35 Plan 01: Teams RBAC Foundation Summary

**One-liner:** PostgreSQL workspace schema with RLS, WorkspaceService (8 async methods), and require_role middleware using secrets-based invite tokens and admin-gated role management.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Database migration for workspaces, members, and invites | 2adf547 | supabase/migrations/20260403200000_teams_rbac.sql |
| 2 | Workspace service and require_role middleware | 045a059 | app/services/workspace_service.py, app/middleware/workspace_role.py, app/config/feature_gating.py, frontend/src/config/featureGating.ts |

## What Was Built

### Task 1: Database Migration

Created `supabase/migrations/20260403200000_teams_rbac.sql` with:

- **`workspaces` table** — `id`, `owner_id`, `name`, `slug` (unique), `created_at`, `updated_at`. Index on `owner_id`. RLS: owner can do everything; members can SELECT.
- **`workspace_members` table** — `id`, `workspace_id`, `user_id`, `role` CHECK(`admin`/`editor`/`viewer`), `joined_at`. UNIQUE(workspace_id, user_id). Indexes on both FK columns. RLS: members SELECT own workspace; admins INSERT/UPDATE/DELETE.
- **`workspace_invites` table** — `id`, `workspace_id`, `token` (unique), `role` CHECK(`editor`/`viewer`), `created_by`, `expires_at`, `accepted_by`, `accepted_at`, `is_active`. Indexes on token and workspace_id. RLS: admins CRUD; public SELECT by token for accept-invite flow.
- **Helper functions** — `is_workspace_member(ws_id)` and `get_workspace_role(ws_id)` as `SECURITY DEFINER` SQL functions used by RLS policies.
- **`updated_at` trigger** on workspaces.

### Task 2: Backend Service and Middleware

**`WorkspaceService`** (`app/services/workspace_service.py`) — 8 async methods:

| Method | Purpose |
|--------|---------|
| `get_or_create_workspace(user_id)` | Returns or creates a workspace; auto-assigns admin membership to owner |
| `get_workspace_for_user(user_id)` | Looks up workspace via workspace_members join |
| `get_member_role(user_id, workspace_id)` | Returns role string or None |
| `get_workspace_members(workspace_id)` | Returns members enriched with user_profiles data |
| `create_invite_link(workspace_id, created_by, role, expires_hours)` | Creates invite with `secrets.token_urlsafe(32)` token; validates admin actor |
| `accept_invite(token, user_id)` | Validates token (active, not expired, not used), inserts membership, marks invite accepted |
| `update_member_role(workspace_id, target, new_role, actor)` | Admin-only role change; blocks changing owner's role |
| `remove_member(workspace_id, target, actor)` | Admin-only removal; blocks removing owner |

Uses `get_service_client()` and `execute_async()` patterns matching existing services. Google-style docstrings with Args/Returns/Raises.

**`require_role` middleware** (`app/middleware/workspace_role.py`) — follows identical pattern to `require_feature()`:
- Factory function returning an async FastAPI dependency
- Solo users (no workspace) pass through without restriction
- Team members with insufficient role receive HTTP 403 with structured JSON: `error`, `message`, `current_role`, `required_roles`
- Exports `get_workspace_context` dependency for non-gating workspace injection

**Feature gating updates:**
- `app/config/feature_gating.py` — added `"teams"` with `min_tier: "startup"`
- `frontend/src/config/featureGating.ts` — added `"teams"` to `FeatureKey` union and `FEATURE_ACCESS` record with `minTier: 'startup'`, `route: '/dashboard/team'`

## Decisions Made

1. **Application-layer workspace isolation** — No `workspace_id` columns added to existing tables. The `workspace_members` table identifies co-members; backend services filter shared data by looking up users in the same workspace. This avoids a large data migration and keeps the workspace concept additive.

2. **Admin-only invites, limited to editor/viewer** — The workspace owner is always the admin. Invite tokens can only grant `editor` or `viewer` roles. This prevents privilege escalation via share links.

3. **Solo-user passthrough in require_role** — Users without a workspace (solo users on the solopreneur tier) are not blocked by require_role. Team RBAC only activates once the user has a workspace membership row, making the feature safely additive.

4. **Same dependency-factory pattern as require_feature** — `require_role` mirrors `require_feature` structurally so router and endpoint usage is identical, reducing learning curve and maintaining API consistency.

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- `WorkspaceService` importable: PASSED (confirmed via AST parse + direct import with uv run)
- 8 async methods confirmed: `get_or_create_workspace`, `get_workspace_for_user`, `get_member_role`, `get_workspace_members`, `create_invite_link`, `accept_invite`, `update_member_role`, `remove_member`
- `require_role` and `get_workspace_context` defined in workspace_role.py: PASSED (AST parse confirms function definitions)
- Python feature gating `"teams"` entry: PASSED (`from app.config.feature_gating import FEATURE_ACCESS; assert 'teams' in FEATURE_ACCESS` passed)
- TypeScript `FeatureKey` and `FEATURE_ACCESS` contain `"teams"`: PASSED (grep confirmed)
- Migration has 3 CREATE TABLE statements: PASSED (`grep -c "CREATE TABLE"` = 3)
- Ruff lint on new Python files: PASSED (all checks passed)
- Note: `require_role` transitive import of `get_current_user_id` triggers `.env` encoding issue in the local Windows dev environment — this is a pre-existing issue confirmed by the same error occurring with `require_feature` (existing middleware). Does not affect production or correctness.

## Self-Check: PASSED

- `supabase/migrations/20260403200000_teams_rbac.sql` — FOUND
- `app/services/workspace_service.py` — FOUND
- `app/middleware/workspace_role.py` — FOUND
- commit `2adf547` — FOUND
- commit `045a059` — FOUND
