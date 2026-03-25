---
phase: 15-approval-oversight-permissions-role-management
plan: 01
subsystem: auth
tags: [rbac, fastapi, supabase, admin, approvals, role-management, postgres]

# Dependency graph
requires:
  - phase: 07-foundation
    provides: require_admin middleware, admin_audit_log table, admin_agent_permissions table, user_roles table
  - phase: 14-billing-dashboard
    provides: admin router pattern, admin_audit source field pattern

provides:
  - ROLE_HIERARCHY dict and require_admin_role(min_role) dependency factory in admin_auth.py
  - admin_role field on require_admin return dict (super_admin for env path, DB role for db_role path)
  - admin_role_permissions table with default seeds for all 4 admin roles across 10 sections
  - user_id column on approval_requests with JSONB backfill and index
  - GET /admin/approvals/all with status/action_type/user_id/pagination filters
  - POST /admin/approvals/{id}/override with senior_admin gate and admin_override audit source
  - GET/POST/DELETE /admin/roles (super_admin gate for mutations)
  - GET/PUT /admin/roles/permissions (admin+ gate for read, super_admin for write)
  - 8 Phase 15 admin_agent_permissions seeds

affects:
  - 15-02 and later Phase 15 plans (consume require_admin_role for tool endpoints)
  - Any plan adding new admin endpoints (should use require_admin_role pattern)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - require_admin_role(min_role) factory builds on require_admin, enables clean role gating per endpoint
    - ROLE_HIERARCHY dict enables numeric level comparison for hierarchical roles
    - TDD RED-GREEN flow: test files committed before implementation, then implementation commits

key-files:
  created:
    - supabase/migrations/20260325100000_approval_roles_permissions.sql
    - app/routers/admin/approvals.py
    - tests/unit/admin/test_role_access.py
    - tests/unit/admin/test_approval_api.py
  modified:
    - app/middleware/admin_auth.py
    - app/routers/admin/__init__.py
    - app/services/admin_audit.py

key-decisions:
  - "require_admin_role(min_role) is a factory returning an inner async dependency that calls require_admin internally — avoids double DB lookup by chaining the same credential flow"
  - "Env allowlist (bootstrap) admins always get admin_role='super_admin' — bootstrap admins are implicitly super; no DB row required"
  - "_get_admin_role falls back to 'junior_admin' if user_roles row missing — DB admin with no role row gets least-privilege, not locked out"
  - "admin_override added to _VALID_SOURCES in admin_audit.py — required for audit integrity per plan spec, not a free-text field"
  - "override_approval uses Request (not Request|None) — FastAPI cannot model Optional[Request] as a response field; always injected in HTTP context"

patterns-established:
  - "Role gating pattern: Depends(require_admin_role('senior_admin')) on endpoint definition — consistent across all Phase 15 endpoints"
  - "Admin override audit: source='admin_override' distinguishes automated vs. human override in audit log queries"

requirements-completed: [APPR-01, APPR-02, ROLE-01, ROLE-02, ROLE-03, ROLE-04]

# Metrics
duration: 14min
completed: 2026-03-25
---

# Phase 15 Plan 01: Approval Oversight and RBAC Foundation Summary

**Role-aware admin middleware with ROLE_HIERARCHY enforcement, admin approval queue with senior_admin-gated overrides, and full admin role CRUD — 16 tests passing**

## Performance

- **Duration:** 14 min
- **Started:** 2026-03-25T15:57:23Z
- **Completed:** 2026-03-25T16:11:26Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Enhanced `require_admin` to return `admin_role` field (env admins always `super_admin`, DB admins from `user_roles` row)
- Added `require_admin_role(min_role)` factory with `ROLE_HIERARCHY` numeric comparison — blocks insufficient roles with HTTP 403
- Created `admin_role_permissions` table with 40 default seed rows (4 roles × 10 sections) and `user_id` column on `approval_requests` with JSONB backfill
- 7 new admin endpoints: approval queue listing, approval override, role CRUD, and role permissions management

## Task Commits

Each task was committed atomically with TDD RED before GREEN:

1. **Task 1 RED: role access tests** — `4ff51f9` (test)
2. **Task 1 GREEN: migration + enhanced middleware** — `8c6b6b4` (feat)
3. **Task 2 RED: approval API tests** — `71409ff` (test)
4. **Task 2 GREEN: approvals router + admin_audit fix** — `712f706` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `supabase/migrations/20260325100000_approval_roles_permissions.sql` — Creates admin_role_permissions, adds user_id to approval_requests, seeds 4 roles × 10 sections + 8 Phase 15 tool permissions
- `app/middleware/admin_auth.py` — ROLE_HIERARCHY dict, _get_admin_role helper, admin_role field in require_admin return, require_admin_role(min_role) factory
- `app/routers/admin/approvals.py` — 7 endpoints: GET/POST /approvals, GET/POST/DELETE /roles, GET/PUT /roles/permissions
- `app/routers/admin/__init__.py` — Wires approvals router into admin_router
- `app/services/admin_audit.py` — Adds admin_override to _VALID_SOURCES
- `tests/unit/admin/test_role_access.py` — 6 role hierarchy unit tests
- `tests/unit/admin/test_approval_api.py` — 10 approval API unit tests

## Decisions Made

- `require_admin_role(min_role)` is a factory that returns an inner dependency calling `require_admin` internally — avoids a separate DB round-trip while maintaining the HTTPBearer → verify_token → role-check chain
- Env allowlist admins always receive `admin_role='super_admin'` — bootstrap admins need no `user_roles` row
- `_get_admin_role` falls back to `'junior_admin'` when no `user_roles` row exists for a DB-approved admin — least-privilege default, never a lockout
- `admin_override` added to `_VALID_SOURCES` — distinguishes human override from AI agent or automated monitoring actions in audit queries

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Request|None parameter type rejected by FastAPI**
- **Found during:** Task 2 (override_approval endpoint)
- **Issue:** FastAPI cannot generate a response model for `Request | None` union type; raises `FastAPIError` at startup
- **Fix:** Changed signature to `request: Request` (always injected in HTTP context) and removed `client_ip: str = "unknown"` fallback param
- **Files modified:** app/routers/admin/approvals.py, tests/unit/admin/test_approval_api.py
- **Verification:** All 10 approval API tests pass after fix
- **Committed in:** `712f706` (Task 2 commit)

**2. [Rule 2 - Missing Critical] Added admin_override to _VALID_SOURCES in admin_audit.py**
- **Found during:** Task 2 (override_approval audit logging)
- **Issue:** Plan specifies `source="admin_override"` for override audit entries, but `_VALID_SOURCES` only contained `manual/ai_agent/impersonation/monitoring_loop` — would silently convert to `"manual"`, obscuring override events in audit queries
- **Fix:** Added `"admin_override"` to `_VALID_SOURCES` frozenset
- **Files modified:** app/services/admin_audit.py
- **Verification:** Audit source preserved correctly in test assertion
- **Committed in:** `712f706` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both fixes required for correctness and audit integrity. No scope creep.

## Issues Encountered

None — both deviations were caught and resolved within the same task execution cycle.

## Next Phase Readiness

- RBAC foundation complete: `require_admin_role` is available for all Phase 15 plan 02+ endpoints
- `admin_role_permissions` table seeded and queryable for governance tools
- `admin_override` audit source registered, ready for AI-driven governance agent tools
- All 16 tests pass; `app/routers/admin/approvals.py` is wired and importable

---
*Phase: 15-approval-oversight-permissions-role-management*
*Completed: 2026-03-25*
