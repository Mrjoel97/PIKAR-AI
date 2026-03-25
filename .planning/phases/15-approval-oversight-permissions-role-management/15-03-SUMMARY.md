---
phase: 15-approval-oversight-permissions-role-management
plan: "03"
subsystem: admin-ui
tags: [admin, approvals, rbac, role-management, autonomy-tiers, react, nextjs, typescript]
dependency_graph:
  requires:
    - 15-01 (approval_requests table, /admin/approvals/* endpoints, /admin/roles/* endpoints)
    - 15-02 (governance tools, AdminAgent 59-tool registration)
    - 07-04 (ConfirmationCard double-click protection pattern, admin dark theme)
    - 14-01 (billing page pattern: useCallback fetch, 60s polling, loading skeleton)
  provides:
    - /admin/approvals page with filterable cross-user approval queue and override actions
    - ApprovalQueueTable component with inline confirm form and double-click protection
    - /admin/settings page with 3-tab navigation (Autonomy Tiers, Role Management, Role Permissions)
    - AutonomyTierTab: 58+ tools grouped by domain with collapsible sections and tier dropdowns
    - RoleManagementTab: admin CRUD with super_admin gate and read-only fallback
    - RolePermissionsTab: 10-section x 4-role x 3-action checkbox matrix with super_admin gate
  affects:
    - AdminSidebar navigation (both /admin/approvals and /admin/settings were pre-wired in adminNav.ts)
tech_stack:
  added: []
  patterns:
    - "processingId state for per-row double-click protection (extends ConfirmationCard clicked pattern to table rows)"
    - "Controlled filter state in parent page, presentational table component — clean separation"
    - "Token passed as prop to tab components — avoids repeated supabase.auth.getSession() calls in each tab"
    - "DOMAIN_MAP prefix/substring matching for autonomy tier grouping — deterministic, no API call"
    - "PermMatrix (role::section -> Set<Action>) reduces O(n) lookup to O(1) for checkbox rendering"
    - "Optimistic update + fetchPermissions() revert on error — consistent with AutonomyTable.tsx Phase 12 pattern"
key_files:
  created:
    - frontend/src/app/(admin)/approvals/page.tsx
    - frontend/src/components/admin/approvals/ApprovalQueueTable.tsx
    - frontend/src/app/(admin)/settings/page.tsx
    - frontend/src/components/admin/settings/AutonomyTierTab.tsx
    - frontend/src/components/admin/settings/RoleManagementTab.tsx
    - frontend/src/components/admin/settings/RolePermissionsTab.tsx
  modified: []
decisions:
  - "processingId state (string | null) tracks which row is being submitted — prevents double-submission without a full isLoading lock that would block the entire table"
  - "Token fetched once in settings/page.tsx from supabase.auth.getSession() and passed as prop — avoids 3 parallel getSession() calls in tab components"
  - "adminRole fetched from /admin/check-access in settings/page.tsx — single source of truth for both RoleManagementTab and RolePermissionsTab gate checks"
  - "AutonomyTierTab expands all domains on first load — best UX for initial discovery; user can collapse to reduce scroll"
  - "PermMatrix keyed as role::section -> Set<Action> — O(1) checkbox lookup vs O(n) array search across 120 cells (10 sections x 4 roles x 3 actions)"
  - "Filter state (statusFilter, actionTypeFilter) lives in ApprovalsPage, not ApprovalQueueTable — parent re-fetches on filter change so server-side filtering applies correctly"
metrics:
  duration: "~20 min"
  completed_date: "2026-03-25"
  tasks_completed: 2
  files_created: 6
  files_modified: 0
---

# Phase 15 Plan 03: Admin Approvals Page and Settings Page Summary

**One-liner:** Admin approval oversight page with cross-user queue and override actions, plus 3-tab settings page covering autonomy tier editing (58+ tools), admin role CRUD, and role-section-action permission matrix.

## What Was Built

### Task 1: Admin Approvals Page

**`frontend/src/app/(admin)/approvals/page.tsx`**
- `useCallback` fetch pattern from billing/page.tsx with 60-second polling via `setInterval`
- State: `approvals`, `isLoading`, `fetchError`, `statusFilter` (default PENDING), `actionTypeFilter`
- `handleOverride` posts to `POST /admin/approvals/{id}/override` then refetches
- Loading skeleton (initial load), error banner with retry, Refresh button

**`frontend/src/components/admin/approvals/ApprovalQueueTable.tsx`**
- Filter bar: Status dropdown (ALL/PENDING/APPROVED/REJECTED/EXPIRED) + action type text input
- Table columns: Action Type, User (truncated UUID + tooltip), Created (relative time), Expires (red if <24h), Status badge, Actions
- Inline confirm form per row: opens on Approve/Reject click, optional reason textarea, Confirm/Cancel buttons
- `processingId` state prevents double-submission (per-row, not full-table lock)
- Status badges: PENDING=amber, APPROVED=emerald, REJECTED=rose, EXPIRED=gray

### Task 2: Admin Settings Page

**`frontend/src/app/(admin)/settings/page.tsx`**
- Fetches session token + admin_role from `/admin/check-access` on mount
- Passes `token` and `adminRole` as props to all three tab components
- Tab bar: `bg-gray-800 rounded-lg p-1`, active tab `bg-indigo-600 text-white`
- Loading skeleton while session initialises

**`frontend/src/components/admin/settings/AutonomyTierTab.tsx`**
- Fetches `GET /admin/config/permissions` (existing endpoint)
- `DOMAIN_MAP` maps action name prefixes to 9 domain labels: System, Monitoring, Analytics, Integrations, Config, Knowledge, Users, Billing, Governance
- Collapsible domain sections (all expanded by default) with action count badges
- Tier dropdown per action (auto/confirm/blocked), optimistic update + revert on error
- PUT `/admin/config/permissions/{action_name}` — same endpoint as existing AutonomyTable

**`frontend/src/components/admin/settings/RoleManagementTab.tsx`**
- Fetches `GET /admin/roles`, displays 4-column table (User ID, Role, Created, Actions)
- Role badges: junior_admin=blue, senior_admin=amber, admin=indigo, super_admin=rose
- Add Admin inline form (UUID input + role dropdown), POST `/admin/roles`
- Role reassignment via select dropdown per row (POST `/admin/roles` upsert)
- Delete via `Trash2` icon + `window.confirm`, DELETE `/admin/roles/{user_id}`
- Non-super_admin: read-only view with amber banner

**`frontend/src/components/admin/settings/RolePermissionsTab.tsx`**
- Fetches `GET /admin/roles/permissions`, builds `PermMatrix` (role::section -> Set<Action>)
- 10 sections (rows) x 4 roles (column groups) x 3 actions (checkboxes per cell) = 120 cells
- Optimistic checkbox toggle + PUT `/admin/roles/permissions` + revert on error
- Non-super_admin: read-only view with amber banner (all checkboxes disabled)

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Admin approvals page + queue table | `7bfd9cf` | approvals/page.tsx, ApprovalQueueTable.tsx |
| 2 | Admin settings page + 3 tab components | `1add7f6` | settings/page.tsx, AutonomyTierTab.tsx, RoleManagementTab.tsx, RolePermissionsTab.tsx |

## Deviations from Plan

None — plan executed exactly as written. All TypeScript compiles cleanly (zero errors).

## Self-Check: PASSED

| Item | Status |
|------|--------|
| `frontend/src/app/(admin)/approvals/page.tsx` | FOUND |
| `frontend/src/components/admin/approvals/ApprovalQueueTable.tsx` | FOUND |
| `frontend/src/app/(admin)/settings/page.tsx` | FOUND |
| `frontend/src/components/admin/settings/AutonomyTierTab.tsx` | FOUND |
| `frontend/src/components/admin/settings/RoleManagementTab.tsx` | FOUND |
| `frontend/src/components/admin/settings/RolePermissionsTab.tsx` | FOUND |
| Commit `7bfd9cf` (Task 1) | FOUND |
| Commit `1add7f6` (Task 2) | FOUND |
| TypeScript `npx tsc --noEmit` | CLEAN (no output = no errors) |

## Awaiting

Task 3 (checkpoint:human-verify): Visual verification of /admin/approvals and /admin/settings pages.
