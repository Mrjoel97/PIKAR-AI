# Phase 15: Approval Oversight + Permissions + Role Management — Research

**Date:** 2026-03-25
**Confidence:** HIGH
**Phase requirements:** APPR-01, APPR-02, ROLE-01, ROLE-02, ROLE-03, ROLE-04, ASST-02, SKIL-12, SKIL-13, SKIL-14, SKIL-15, SKIL-16

---

## Existing Infrastructure

### approval_requests table (migration 0012)
- Schema: id (UUID), token (TEXT UNIQUE), action_type (TEXT), payload (JSONB), status (PENDING/APPROVED/REJECTED/EXPIRED), created_at, expires_at, responded_at, responder_ip
- RLS: public read (token-gated), service_role writes
- Indexes: token, status
- **No user_id column** — requester_user_id is embedded in payload JSONB

### user_roles table (migration 20260321300000)
- Schema: id (UUID), user_id (UUID FK auth.users), role (CHECK: user/junior_admin/senior_admin/admin/super_admin), created_at, updated_at
- UNIQUE on user_id (one role per user)
- `is_admin()` SECURITY DEFINER function: returns TRUE for any admin-level role

### admin_agent_permissions table (migration 20260321300000)
- Stores autonomy tiers per action_name
- Queried by `_check_autonomy()` in `app/agents/admin/tools/_autonomy.py`
- Currently has 56 tool permission seeds across phases 7-14

### admin_auth middleware (app/middleware/admin_auth.py)
- `require_admin` dependency — OR logic: env allowlist OR db role
- Returns user dict with `admin_source` field
- **Does NOT return the role level** — only boolean admin/not-admin
- Needs enhancement to return actual role for role-based access control

### Existing approvals router (app/routers/approvals.py)
- User-facing: create_approval_request, get_approval_request, decide_approval
- Token-based (SHA-256 hashed), status tracking, expiry
- No admin cross-user view — admin needs a query-all endpoint

### Admin pages already in sidebar
- `/admin/approvals` — NOT YET CREATED (no page.tsx in admin dir)
- `/admin/settings` — NOT YET CREATED (settings exists at app-level, not admin)

### AdminAgent current state
- 56 tools across 7 domains (monitoring, analytics, users, config, integrations, knowledge, billing)
- Phase 15 adds governance tools to reach 30+ requirement (ASST-02 already satisfied with 56)

---

## Architecture Decisions

### 1. Role-Based Access Control (RBAC)

**Admin role hierarchy:**
| Role | Read Admin | Write Actions | Manage Roles | Override Approvals |
|------|-----------|---------------|-------------|-------------------|
| junior_admin | ✓ all sections | ✗ blocked | ✗ | ✗ |
| senior_admin | ✓ all sections | ✓ all except roles | ✗ | ✓ |
| admin | ✓ all sections | ✓ all | ✓ (below own level) | ✓ |
| super_admin | ✓ all sections | ✓ all | ✓ all | ✓ |

**Implementation approach:**
- New `admin_role_permissions` table: role → section → allowed_actions (read/write/manage)
- Enhance `require_admin` middleware to return the role and check section-level access
- New `require_admin_role(min_role)` dependency for fine-grained endpoint protection
- Role hierarchy as integer: junior_admin=1, senior_admin=2, admin=3, super_admin=4

### 2. Approval Oversight

**Admin approval queue approach:**
- New admin endpoint `GET /admin/approvals/all` — queries all approval_requests (not just user's own)
- Filter params: status, action_type, user_id, date range
- Admin override endpoint `POST /admin/approvals/{id}/override` — approve/reject any approval
- Override is confirm-tier AdminAgent action, tagged `source: admin_override` in audit log

### 3. Permissions UI

**Settings page approach:**
- `/admin/settings` page with tabs: Autonomy Tiers | Role Management | Role Permissions
- Autonomy Tiers tab: table of all 56+ tool actions with auto/confirm/blocked dropdowns
- Role Management tab: list of admin accounts with role assignment (super_admin only)
- Role Permissions tab: matrix of role × section × action (super_admin only)

### 4. AdminAgent Governance Skills (SKIL-12 through SKIL-16)

| Skill | Tool Name | Tier | Approach |
|-------|-----------|------|----------|
| SKIL-12 | recommend_autonomy_tier | auto | Analyzes tool's risk profile (writes vs reads, external calls, data access) and recommends auto/confirm/blocked |
| SKIL-13 | generate_compliance_report | auto | Queries admin_audit_log with date range, groups by source/action, generates narrative summary |
| SKIL-14 | suggest_role_permissions | auto | Given a role description, recommends section access based on existing role templates |
| SKIL-15 | generate_daily_digest | auto | Aggregates: pending approvals count, at-risk users (declining usage), anomalous metrics (reuses SKIL-05), upcoming subscription expirations |
| SKIL-16 | classify_and_escalate | confirm | Scores issue severity (low/medium/high/critical), routes high+ to super_admin via notification in audit log |

---

## Migration Plan

**Timestamp:** 20260325100000 (after billing permissions at 20260325000000)

New tables:
1. `admin_role_permissions` — role (text), section (text), allowed_actions (text[]), PRIMARY KEY (role, section)

Alterations:
1. Add `user_id` column to `approval_requests` for direct querying (backfill from payload->>'requester_user_id')

Seeds:
1. Default role_permissions for all 4 admin roles
2. Permission seeds for 5 new governance tools

---

## Wave Structure Recommendation

**Wave 1 (backend — parallel safe):**
- Plan 15-01: Migration + role service + approval admin endpoints + middleware enhancement
- Plan 15-02: 5 governance AdminAgent tools (SKIL-12 through SKIL-16) + agent registration + tests

**Wave 2 (frontend — depends on Wave 1):**
- Plan 15-03: Approvals page + Settings page (tabs: autonomy, roles, role permissions) + visual checkpoint

---

## Pitfalls

1. **Circular RLS on user_roles** — `is_admin()` is SECURITY DEFINER to avoid this. Any new queries on user_roles from RLS policies must also use SECURITY DEFINER functions.
2. **Breaking existing admin access** — `require_admin` enhancement must remain backward-compatible (OR logic stays, role return is additive).
3. **56 tools in autonomy table** — permissions UI must paginate or group by domain, not render a flat list.
4. **approval_requests has no user_id column** — need migration to add it for efficient admin cross-user queries.
5. **ASST-02 (30+ tools)** — already satisfied at 56 tools. Phase 15 adds 5 more (61 total). Just need to verify count at the end.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (existing) |
| Quick run command | `uv run pytest tests/unit/admin/test_governance_tools.py -x` |
| Full suite command | `uv run pytest tests/unit/admin/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command |
|--------|----------|-----------|-------------------|
| APPR-01 | GET /admin/approvals/all returns cross-user pending approvals | unit | `uv run pytest tests/unit/admin/test_approval_api.py::test_list_all_approvals -x` |
| APPR-02 | POST /admin/approvals/{id}/override with confirm-tier + audit log | unit | `uv run pytest tests/unit/admin/test_approval_api.py::test_override_approval -x` |
| ROLE-01 | create_admin_account inserts user_roles row with specified role | unit | `uv run pytest tests/unit/admin/test_governance_tools.py::test_create_admin_account -x` |
| ROLE-02 | junior_admin blocked from write endpoints | unit | `uv run pytest tests/unit/admin/test_role_access.py::test_junior_admin_write_blocked -x` |
| ROLE-03 | senior_admin has full access except role management | unit | `uv run pytest tests/unit/admin/test_role_access.py::test_senior_admin_no_role_management -x` |
| ROLE-04 | super_admin can configure per-role permissions | unit | `uv run pytest tests/unit/admin/test_governance_tools.py::test_update_role_permissions -x` |
| SKIL-12 | recommend_autonomy_tier returns tier recommendation with reasoning | unit | `uv run pytest tests/unit/admin/test_governance_tools.py::test_recommend_autonomy_tier -x` |
| SKIL-13 | generate_compliance_report returns narrative summary from audit logs | unit | `uv run pytest tests/unit/admin/test_governance_tools.py::test_generate_compliance_report -x` |
| SKIL-14 | suggest_role_permissions returns section-action matrix | unit | `uv run pytest tests/unit/admin/test_governance_tools.py::test_suggest_role_permissions -x` |
| SKIL-15 | generate_daily_digest returns aggregated operational summary | unit | `uv run pytest tests/unit/admin/test_governance_tools.py::test_generate_daily_digest -x` |
| SKIL-16 | classify_and_escalate returns severity + routes critical to super_admin | unit | `uv run pytest tests/unit/admin/test_governance_tools.py::test_classify_and_escalate -x` |

### Wave 0 Gaps
- [ ] `tests/unit/admin/test_governance_tools.py` — all 5 governance tools + role CRUD
- [ ] `tests/unit/admin/test_approval_api.py` — admin approval endpoints
- [ ] `tests/unit/admin/test_role_access.py` — role-based access control enforcement

---

## Sources

### Primary (HIGH confidence)
- `supabase/migrations/0012_approval_requests.sql` — approval_requests schema
- `supabase/migrations/20260321300000_admin_panel_foundation.sql` — user_roles + admin_agent_permissions + is_admin()
- `app/middleware/admin_auth.py` — require_admin dependency (OR logic, no role return)
- `app/agents/admin/tools/_autonomy.py` — check_autonomy() implementation
- `app/routers/approvals.py` — existing user-facing approval endpoints
- `app/agents/admin/tools/__init__.py` — 56 tools in __all__
- `app/agents/admin/agent.py` — AdminAgent instruction pattern

### Secondary (MEDIUM confidence)
- Role hierarchy enforcement patterns from prior phases (user management in Phase 9, impersonation in Phase 13)
