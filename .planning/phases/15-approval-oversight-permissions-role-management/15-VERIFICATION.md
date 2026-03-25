---
phase: 15-approval-oversight-permissions-role-management
verified: 2026-03-25T18:30:00Z
status: gaps_found
score: 8/10 must-haves verified
gaps:
  - truth: "Admin can navigate to /admin/settings and see three tabs with role management fully functional for super_admin"
    status: failed
    reason: "GET /admin/check-access does not return admin_role field. The settings page fetches admin_role from this endpoint, but the endpoint only returns {access, email, admin_source}. adminRole always stays at the default 'junior_admin', so isSuperAdmin is always false — Role Management and Role Permissions tabs are perpetually read-only for every user including actual super admins."
    artifacts:
      - path: "app/routers/admin/auth.py"
        issue: "check_admin_access returns {access, email, admin_source} but not admin_role. require_admin now populates admin_role on the user dict, but auth.py never includes it in the response."
      - path: "frontend/src/app/(admin)/settings/page.tsx"
        issue: "Line 71: if (data.admin_role) { setAdminRole(data.admin_role) } — data.admin_role will always be undefined because the endpoint does not send it."
    missing:
      - "Add admin_role to the check_admin_access return dict in app/routers/admin/auth.py: return {\"access\": True, \"email\": admin_user[\"email\"], \"admin_source\": admin_user[\"admin_source\"], \"admin_role\": admin_user.get(\"admin_role\", \"junior_admin\")}"
  - truth: "REQUIREMENTS.md checkboxes updated to reflect Phase 15 completion"
    status: partial
    reason: "REQUIREMENTS.md still shows [ ] (unchecked) for ASST-02, SKIL-12, SKIL-13, SKIL-14, SKIL-15, SKIL-16, and the traceability table still marks them Pending. The implementations exist and pass tests, but the requirements document was not updated after Phase 15 completed."
    artifacts:
      - path: ".planning/REQUIREMENTS.md"
        issue: "Lines 19, 131-133, 137-138, 170, 230-234: all show unchecked/Pending status despite working implementations in governance.py and 59-tool AdminAgent."
    missing:
      - "Update REQUIREMENTS.md: check [x] for ASST-02, SKIL-12, SKIL-13, SKIL-14, SKIL-15, SKIL-16 and change traceability table status from Pending to Complete for each."
human_verification:
  - test: "Navigate to /admin/settings as super_admin, click 'Role Management' tab, verify Add Admin button is visible and functional (not read-only banner)"
    expected: "After fix: isSuperAdmin is true, table shows Add Admin button and editable role dropdowns"
    why_human: "Cannot verify UI state programmatically; requires live browser with authenticated super_admin session"
  - test: "In admin chat, type 'Give me a daily operational digest' and verify AdminAgent calls generate_daily_digest()"
    expected: "Response includes pending_approvals count, at_risk_users, anomalies, and upcoming_expirations sections"
    why_human: "Requires live ADK agent execution with backend running"
  - test: "In admin chat, ask 'What autonomy tier should I set for a new purge_all_logs action?' and verify AdminAgent calls recommend_autonomy_tier()"
    expected: "Response recommends 'blocked' tier with reasoning about mass-destructive keywords"
    why_human: "Requires live agent session"
---

# Phase 15: Approval Oversight, Permissions, and Role Management — Verification Report

**Phase Goal:** The admin can see and act on all pending approvals, reconfigure AdminAgent autonomy tiers, and manage a multi-tier admin hierarchy — super admin can create junior_admin, senior_admin, and admin accounts with scoped access permissions per section and action.
**Verified:** 2026-03-25T18:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Admin can query all pending approvals at GET /admin/approvals/all | VERIFIED | `app/routers/admin/approvals.py` line 94: endpoint exists with status/action_type/user_id/pagination filters, wired into admin_router at line 67 of `__init__.py` |
| 2 | Admin can approve or reject any pending approval via POST /admin/approvals/{id}/override with confirm-tier enforcement and admin_override audit source | VERIFIED | `approvals.py` line 155: Depends(require_admin_role("senior_admin")), log_admin_action(source="admin_override") at line 232. admin_override added to _VALID_SOURCES in admin_audit.py |
| 3 | require_admin returns admin_role field; require_admin_role(min_role) blocks insufficient roles with 403 | VERIFIED | `app/middleware/admin_auth.py` lines 43-48: ROLE_HIERARCHY dict; line 106: env path returns admin_role='super_admin'; line 113: DB path fetches role; line 129-167: require_admin_role(min_role) factory |
| 4 | Junior admin is blocked from write endpoints; senior admin blocked from role management | VERIFIED | approvals.py: write endpoints use Depends(require_admin_role("senior_admin")), role endpoints use Depends(require_admin_role("super_admin")). 6 unit tests in test_role_access.py verify each level |
| 5 | Super admin can create admin accounts, assign roles, and configure per-role permissions | VERIFIED | approvals.py: POST /roles (super_admin gate), PUT /roles/permissions (super_admin gate), migration creates admin_role_permissions with 40-row seed |
| 6 | All 8 governance tools exist in governance.py with autonomy enforcement | VERIFIED | `app/agents/admin/tools/governance.py`: 1003 lines, all 8 tools implemented with _check_autonomy() gate before every tool body |
| 7 | AdminAgent has 59 tools registered (satisfies ASST-02 30+ requirement) | VERIFIED | `__init__.py` __all__ has 59 entries (counted). agent.py imports all 8 governance tools and registers under "# Phase 15: governance and approvals" comment in both singleton and factory |
| 8 | Frontend approvals page at /admin/approvals renders filterable queue with override actions | VERIFIED | `frontend/src/app/(admin)/approvals/page.tsx`: 195 lines, fetches /admin/approvals/all with Bearer token, handleOverride POSTs to /admin/approvals/{id}/override, 60s polling, ApprovalQueueTable wired |
| 9 | Admin settings page at /admin/settings renders 3 tabs — Autonomy Tiers, Role Management, Role Permissions | VERIFIED (partial) | Page exists and tabs render. Autonomy Tiers tab fully functional. Role Management and Role Permissions tabs BROKEN for role gating — see gap below |
| 10 | REQUIREMENTS.md updated to reflect Phase 15 completion | FAILED | ASST-02, SKIL-12 through SKIL-16 still show `[ ]` unchecked and "Pending" in traceability table despite working implementations |

**Score:** 8/10 truths verified (9 partially, 1 fully failed)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `supabase/migrations/20260325100000_approval_roles_permissions.sql` | admin_role_permissions table, user_id on approval_requests, 40 permission seeds, 8 tool seeds | VERIFIED | File exists, creates table with CHECK constraints, adds user_id with JSONB backfill index, seeds 4 roles x 10 sections |
| `app/middleware/admin_auth.py` | ROLE_HIERARCHY + require_admin_role factory | VERIFIED | 168 lines, ROLE_HIERARCHY at line 43, require_admin_role factory at line 129, admin_role field on both auth paths |
| `app/routers/admin/approvals.py` | 7 admin endpoints | VERIFIED | 486 lines, all 7 endpoints present with correct role gating |
| `app/routers/admin/__init__.py` | approvals router wired | VERIFIED | Line 67: admin_router.include_router(approvals.router, tags=["admin-approvals"]) |
| `app/agents/admin/tools/governance.py` | 8 governance tools | VERIFIED | 1003 lines, all 8 tools with autonomy enforcement, no stubs |
| `app/agents/admin/tools/__init__.py` | 59 tools in __all__ | VERIFIED | 59 quoted entries, all 8 governance tools imported and exported |
| `app/agents/admin/agent.py` | governance tools registered in singleton + factory | VERIFIED | Both admin_agent singleton and create_admin_agent() factory include all 8 tools under Phase 15 comment; ADMIN_AGENT_INSTRUCTION includes governance skill sections |
| `frontend/src/app/(admin)/approvals/page.tsx` | Approval queue page | VERIFIED | 195 lines, substantive: fetch + polling + handleOverride + ApprovalQueueTable wired |
| `frontend/src/components/admin/approvals/ApprovalQueueTable.tsx` | Filterable table with override actions | VERIFIED | 339 lines, filter bar, table with 6 columns, inline confirm form, processingId double-click protection |
| `frontend/src/app/(admin)/settings/page.tsx` | 3-tab settings page | VERIFIED | 151 lines, 3 tabs, token + adminRole fetched from check-access and passed to tabs |
| `frontend/src/components/admin/settings/AutonomyTierTab.tsx` | Domain-grouped autonomy editor | VERIFIED | 331 lines, DOMAIN_MAP, collapsible sections, tier dropdowns, PUT /admin/config/permissions/{action_name} |
| `frontend/src/components/admin/settings/RoleManagementTab.tsx` | Admin CRUD (super_admin gate) | STUB/BROKEN | 416 lines, substantive code exists, but isSuperAdmin always false due to check-access gap |
| `frontend/src/components/admin/settings/RolePermissionsTab.tsx` | Role-section-action matrix (super_admin gate) | STUB/BROKEN | 300 lines, 120-cell matrix implemented, but all checkboxes disabled due to same gap |
| `tests/unit/admin/test_role_access.py` | 6 role access tests | VERIFIED | 210 lines, 6 test functions confirmed |
| `tests/unit/admin/test_approval_api.py` | 10 approval API tests | VERIFIED | 440 lines, 10 test functions confirmed |
| `tests/unit/admin/test_governance_tools.py` | 16 governance tool tests | VERIFIED | 520 lines, 16 test functions confirmed |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/routers/admin/approvals.py` | `app/middleware/admin_auth.py` | Depends(require_admin) and Depends(require_admin_role) | WIRED | require_admin at line 96, require_admin_role("senior_admin") at line 160, require_admin_role("super_admin") at lines 286, 341, 423 |
| `app/routers/admin/approvals.py` | `app/services/admin_audit.py` | log_admin_action(source='admin_override') | WIRED | Line 232: source="admin_override"; admin_override is registered in _VALID_SOURCES |
| `app/middleware/admin_auth.py` | supabase user_roles table | SELECT role FROM user_roles WHERE user_id | WIRED | _get_admin_role() at line 51, queries user_roles.select("role").eq("user_id", user_id) |
| `app/agents/admin/tools/governance.py` | `app/agents/admin/tools/_autonomy.py` | _check_autonomy() before each tool | WIRED | All 8 tools call gate = await _check_autonomy("tool_name") as first statement |
| `app/agents/admin/tools/governance.py` | `app/services/admin_audit.py` | log_admin_action for confirm-tier tools | WIRED | classify_and_escalate, override_approval, manage_admin_role all call log_admin_action |
| `app/agents/admin/agent.py` | `app/agents/admin/tools/governance.py` | tools list registration | WIRED | All 8 tools in import block (lines 37-46) and in both tools lists (lines 504-511 and 617-624) |
| `frontend/src/app/(admin)/approvals/page.tsx` | `/admin/approvals/all` | fetch with Bearer token | WIRED | Line 54: fetch(`${API_URL}/admin/approvals/all?${params}`, {headers: {Authorization: `Bearer ${session.access_token}`}}) |
| `frontend/src/components/admin/approvals/ApprovalQueueTable.tsx` | `/admin/approvals/{id}/override` | fetch POST on approve/reject | WIRED | Line 95 of page.tsx: fetch(`${API_URL}/admin/approvals/${id}/override`, {method: 'POST', ...}) |
| `frontend/src/components/admin/settings/RoleManagementTab.tsx` | `/admin/roles` | fetch GET/POST/DELETE | WIRED | Lines 83, 110, 140, 173: fetch calls to /admin/roles with correct methods |
| `frontend/src/components/admin/settings/RolePermissionsTab.tsx` | `/admin/roles/permissions` | fetch GET/PUT | WIRED | Lines 101, 147: fetch calls to /admin/roles/permissions |
| `frontend/src/app/(admin)/settings/page.tsx` | `/admin/check-access` | fetch GET for admin_role | NOT_WIRED | Page expects data.admin_role from /admin/check-access, but endpoint returns {access, email, admin_source} — admin_role field absent |
| `/admin/approvals` and `/admin/settings` | AdminSidebar nav | adminNav.ts href entries | WIRED | adminNav.ts lines 51 and 76: both routes pre-wired in sidebar navigation |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| APPR-01 | 15-01, 15-03 | Admin can view and manage all pending approvals across users | SATISFIED | GET /admin/approvals/all with filters + /admin/approvals page with table |
| APPR-02 | 15-01, 15-03 | Admin can approve/reject on behalf of users (confirm-tier action) | SATISFIED | POST /admin/approvals/{id}/override gated senior_admin, logged source=admin_override, inline confirm form in UI |
| ROLE-01 | 15-01, 15-03 | Super admin can create admin accounts and assign roles | SATISFIED (code) / BLOCKED (UI) | Backend POST /admin/roles exists and is super_admin gated. UI "Add Admin" button hidden due to check-access gap — adminRole never reaches 'super_admin' |
| ROLE-02 | 15-01, 15-03 | Super admin can define per-role access permissions | SATISFIED (code) / BLOCKED (UI) | Backend PUT /admin/roles/permissions exists. RolePermissionsTab checkboxes all disabled due to same check-access gap |
| ROLE-03 | 15-01 | Senior admin has access to all admin features except role management | SATISFIED | require_admin_role("admin") gates GET/GET roles endpoints; require_admin_role("super_admin") gates mutations |
| ROLE-04 | 15-01 | Junior admin has read-only access by default | SATISFIED | require_admin_role("senior_admin") on all write endpoints; level-1 role blocked from all mutations |
| ASST-02 | 15-02 | AdminAgent has 30+ tools across 7 domains | SATISFIED | 59 tools in __all__ (7 prior domains + governance = 8 domains). Requirement says 7 domains but 8 are actually covered. Implementation exceeds requirement. |
| SKIL-12 | 15-02 | recommend autonomy tiers for new tools based on risk profile | SATISFIED | recommend_autonomy_tier() in governance.py with keyword-based risk classification (auto/confirm/blocked) |
| SKIL-13 | 15-02 | Summarize audit logs into narrative compliance reports | SATISFIED | generate_compliance_report() queries admin_audit_log, builds narrative with by_source/by_action aggregation |
| SKIL-14 | 15-02 | Suggest per-role permissions when creating admin accounts | SATISFIED | suggest_role_permissions() returns section-action matrix from role description keywords |
| SKIL-15 | 15-02 | Daily operational digest covering pending approvals, at-risk users, anomalies, expirations | SATISFIED | generate_daily_digest() aggregates 4 sources with graceful degradation per section |
| SKIL-16 | 15-02 | Classify issue severity and route escalations to super admin | SATISFIED | classify_and_escalate() scores severity, auto-escalates HIGH/CRITICAL to super_admin via audit log |

**Note on REQUIREMENTS.md:** All 12 requirements have working implementations. However, ASST-02, SKIL-12 through SKIL-16 remain marked `[ ]` (unchecked) with "Pending" status in `.planning/REQUIREMENTS.md` — the document was not updated after Phase 15 completed. This is a documentation gap, not an implementation gap. ROLE-01 and ROLE-02 are additionally blocked at the UI layer by the check-access gap.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/routers/admin/auth.py` | 50-54 | check_admin_access returns dict without admin_role key | BLOCKER | Settings page cannot gate Role Management / Role Permissions tabs for super_admin — both tabs are permanently read-only for all users |
| `.planning/REQUIREMENTS.md` | 19, 131-138, 230-234 | [ ] unchecked boxes and "Pending" status for completed requirements | INFO | Documentation out of sync — not a code defect, but misleads future planners about what is complete |

No stubs, TODOs, empty implementations, or placeholder returns found in any Phase 15 code files.

---

## Human Verification Required

### 1. Role Management Tab — super_admin write access

**Test:** After applying the check-access fix, log in as a super_admin user, navigate to `/admin/settings`, click "Role Management", verify the "Add Admin" button is visible and functional (not the read-only amber banner).
**Expected:** Add Admin form renders, POST to /admin/roles succeeds, new row appears in table.
**Why human:** Requires live browser session with a real super_admin JWT.

### 2. Role Permissions Tab — checkbox editing

**Test:** On the same super_admin session, click "Role Permissions" tab, verify checkboxes are enabled and a PUT to /admin/roles/permissions fires on toggle.
**Expected:** Checkboxes are interactive, optimistic update visible, no permission banner.
**Why human:** Requires authenticated session and visual checkbox state inspection.

### 3. AdminAgent governance tool invocation

**Test:** In admin chat, type "Give me a daily operational digest" and "What autonomy tier should I set for a new purge_all_logs action?"
**Expected:** First response calls generate_daily_digest() and presents structured sections. Second calls recommend_autonomy_tier() and returns "blocked" tier.
**Why human:** Requires live ADK agent execution with backend running.

---

## Gaps Summary

Two gaps block full goal achievement:

**Gap 1 (BLOCKER): check-access endpoint missing admin_role field**

The settings page at `/admin/settings` fetches `admin_role` from `GET /admin/check-access` to gate the Role Management and Role Permissions tabs for super admins. However, `check_admin_access` in `app/routers/admin/auth.py` returns only `{access, email, admin_source}` — the `admin_role` field that `require_admin` now populates on the user dict is never included in the response. As a result, `adminRole` in the settings page defaults to `'junior_admin'` for every user, `isSuperAdmin` is always false, and both tabs show read-only banners. The Role Management and Role Permissions features are fully implemented in the backend but are inaccessible from the UI.

Fix is one line in `auth.py`: add `"admin_role": admin_user.get("admin_role", "junior_admin")` to the return dict.

**Gap 2 (INFO): REQUIREMENTS.md not updated**

ASST-02, SKIL-12, SKIL-13, SKIL-14, SKIL-15, and SKIL-16 all have working, tested implementations but remain marked `[ ]` unchecked in REQUIREMENTS.md with "Pending" in the traceability table. This does not affect runtime behavior but misrepresents Phase 15 completion state for future planners. Update the checkboxes and traceability table to `[x]` / "Complete".

---

_Verified: 2026-03-25T18:30:00Z_
_Verifier: Claude (gsd-verifier)_
