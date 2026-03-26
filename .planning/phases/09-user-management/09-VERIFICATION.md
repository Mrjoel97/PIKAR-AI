---
phase: 09-user-management
verified: 2026-03-21T20:30:00Z
status: gaps_found
score: 9/11 must-haves verified
gaps:
  - truth: "GET /admin/users/{id} returns full user profile with activity stats"
    status: partial
    reason: "Backend returns activity.action_count but frontend UserDetail type declares activity.chat_count and activity.workflow_count. Frontend renders undefined for both stat fields."
    artifacts:
      - path: "app/routers/admin/users.py"
        issue: "get_user_detail returns {\"activity\": {\"action_count\": N}} — no chat_count or workflow_count keys"
      - path: "frontend/src/app/(admin)/users/[id]/page.tsx"
        issue: "UserDetail interface declares activity.chat_count and activity.workflow_count; both will be undefined at runtime"
    missing:
      - "Either rename backend key to split into chat_count/workflow_count (requires actual data sources), OR align frontend UserDetail interface to use action_count and update the rendered labels"

  - truth: "change_user_persona tool returns confirmation request (confirm tier) before executing"
    status: failed
    reason: "_VALID_PERSONAS in app/agents/admin/tools/users.py contains a completely wrong set of values (executive, manager, analyst, sales, marketing, operations, finance, hr, compliance, support) instead of the project persona tiers (solopreneur, startup, sme, enterprise). The persona validation check fires BEFORE the autonomy check, so all real persona values are rejected with an error dict and the tool never reaches _check_autonomy()."
    artifacts:
      - path: "app/agents/admin/tools/users.py"
        issue: "_VALID_PERSONAS frozenset contains role-names (executive, manager, analyst, …) not persona tiers (solopreneur, startup, sme, enterprise)"
    missing:
      - "Replace _VALID_PERSONAS in app/agents/admin/tools/users.py with: frozenset({'solopreneur', 'startup', 'sme', 'enterprise'})"
      - "Update test_user_tools.py: test_change_persona_confirm_tier passes 'executive' which will now fail validation — change to a real persona value like 'startup'"
human_verification:
  - test: "Navigate to /admin/users and verify the user table loads and filters work"
    expected: "Table renders with email, persona badge, signup date, and status columns. Search input debounces. Persona and status dropdowns filter results."
    why_human: "Requires live backend with real Supabase Auth data; cannot verify server-side pagination rendering programmatically"
  - test: "Click a user row, navigate to detail page, check activity stats display"
    expected: "Profile card shows correct data. Activity stats card shows numeric values (not blank/NaN)"
    why_human: "The activity field mismatch (gap 1) will cause blank stats — human must confirm what is rendered and whether it is acceptable or broken"
  - test: "Navigate to /admin/impersonate/{userId} and verify the impersonation banner"
    expected: "Amber banner sticky at top with email, persona, MM:SS countdown. Exit button redirects to /admin/users. Banner turns red when under 5 minutes remain."
    why_human: "Timer behavior, visual appearance, and sticky positioning require browser verification"
  - test: "Verify audit log entries after suspend/unsuspend/persona-change actions"
    expected: "Admin actions from the UI have source=manual in admin_audit_log. Actions from admin chat panel (AdminAgent tools) have source=ai_agent."
    why_human: "Requires running system and database inspection to verify audit trail separation"
---

# Phase 9: User Management Verification Report

**Phase Goal:** The admin can find any user, take basic account actions, and view the app exactly as that user sees it — without any of those actions appearing as user-originated in the audit log
**Verified:** 2026-03-21T20:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /admin/users returns paginated user list with email, persona, status, signup date | VERIFIED | `app/routers/admin/users.py` lines 50–162: full implementation with asyncio.gather enrichment, persona/status/search filters, range-based pagination |
| 2 | GET /admin/users supports search, persona filter, status filter query params | VERIFIED | Router has `search`, `persona`, `status` Query params; filters applied Python-side after auth enrichment |
| 3 | GET /admin/users/{id} returns full user profile with activity stats | PARTIAL | Returns profile correctly; `activity` key contains `action_count` only — frontend expects `chat_count` and `workflow_count` (see Gap 1) |
| 4 | PATCH /admin/users/{id}/suspend calls Supabase Auth Admin API with ban_duration=876000h | VERIFIED | Line 287–291: `asyncio.to_thread(client.auth.admin.update_user_by_id, user_id, {"ban_duration": "876000h"})` |
| 5 | PATCH /admin/users/{id}/unsuspend calls Supabase Auth Admin API with ban_duration=none | VERIFIED | Line 334–338: same pattern with `{"ban_duration": "none"}` |
| 6 | PATCH /admin/users/{id}/persona updates user_executive_agents.persona column | VERIFIED | Lines 390–396: validates against `_VALID_PERSONAS`, updates via execute_async |
| 7 | All user management endpoints are audit-logged with source=manual | VERIFIED | Lines 296–303, 343–350, 403–410: all three mutating endpoints call `log_admin_action(..., "manual")` |
| 8 | All 6 agent tools are registered in AdminAgent tools list | VERIFIED | `app/agents/admin/agent.py` lines 17–24, 94–99, 131–143: all 6 imported and registered in both singleton and factory |
| 9 | change_user_persona tool uses correct persona values | FAILED | `_VALID_PERSONAS` in `app/agents/admin/tools/users.py` lines 28–41 contains role-names (`executive`, `manager`, `analyst`, …) not persona tiers (`solopreneur`, `startup`, `sme`, `enterprise`) — see Gap 2 |
| 10 | Non-dismissible banner visible during impersonation with exit button and countdown | VERIFIED | `ImpersonationBanner.tsx`: sticky top-0 z-[9999], no dismiss button, countdown timer, exit button calls `exitImpersonation()`, amber→red at 5min |
| 11 | Impersonation session auto-expires after 30 minutes with audit separation | VERIFIED | `ImpersonationContext.tsx` lines 37, 89–104: 30-min sessionStorage-persisted timer, auto-redirect on expiry. Agent tools use `source="ai_agent"`, REST endpoints use `source="manual"` |

**Score:** 9/11 truths verified (2 gaps)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `supabase/migrations/20260321600000_user_management_permissions.sql` | 6 admin_agent_permissions seed rows | VERIFIED | 6 rows: list_users(auto), get_user_detail(auto), suspend_user(confirm), unsuspend_user(confirm), change_user_persona(confirm), impersonate_user(confirm) with ON CONFLICT DO NOTHING |
| `app/routers/admin/users.py` | 5 user management API endpoints | VERIFIED | 413 lines: list_users, get_user_detail, suspend_user, unsuspend_user, change_persona — all with require_admin and rate limiting |
| `app/routers/admin/__init__.py` | users.router registered | VERIFIED | Line 13: `from app.routers.admin import audit, auth, chat, monitoring, users`; line 30: `admin_router.include_router(users.router)` with Phase 9 comment |
| `tests/unit/admin/test_users_api.py` | Unit tests for all 5 endpoints (min 100 lines) | VERIFIED | 684 lines, 15 tests covering list, persona filter, status filter, search, detail shape, suspend, unsuspend, persona change, invalid persona, auth enforcement |
| `app/agents/admin/tools/users.py` | 6 AdminAgent user tools, min 150 lines | VERIFIED (with gap) | 487 lines, 6 tools present — but `_VALID_PERSONAS` contains wrong values (see Gap 2) |
| `tests/unit/admin/test_user_tools.py` | Unit tests for agent tools (min 80 lines) | VERIFIED | 276 lines, 9 tests covering auto, confirm, blocked tiers and auto-mode execution |
| `frontend/src/app/(admin)/users/page.tsx` | User list table with search, filters, pagination (min 100 lines) | VERIFIED | 361 lines: TanStack Table v8 with manualPagination, 300ms debounced search, persona + status dropdowns, server-side pagination, row-click navigation |
| `frontend/src/app/(admin)/users/[id]/page.tsx` | User detail page with actions (min 80 lines) | VERIFIED (with gap) | 408 lines: profile card, activity stats card (but field mismatch — see Gap 1), suspend/unsuspend, persona dropdown, impersonate button |
| `frontend/src/contexts/ImpersonationContext.tsx` | ImpersonationContext with timer, min 50 lines | VERIFIED | 143 lines: ImpersonationProvider, PersonaContext override, 30-min sessionStorage-persisted timer, exitImpersonation |
| `frontend/src/components/admin/ImpersonationBanner.tsx` | Non-dismissible sticky banner, min 30 lines | VERIFIED | 71 lines: sticky top-0 z-[9999], amber/red conditional background, MM:SS countdown, Exit button, no dismiss button |
| `frontend/src/app/(admin)/impersonate/[userId]/page.tsx` | Impersonation view page, min 60 lines | VERIFIED | 178 lines: fetches target user, loading skeleton, error+redirect, ImpersonationProvider wrapping, ImpersonationBanner rendered |
| `frontend/src/contexts/PersonaContext.tsx` | Raw PersonaContext exported | VERIFIED | Line 116: `export { PersonaContext }` — ImpersonationContext imports and overrides it correctly |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/routers/admin/users.py` | `app/routers/admin/__init__.py` | `admin_router.include_router(users.router)` | WIRED | Line 13 import, line 30 include_router confirmed |
| `app/routers/admin/users.py` | `app/middleware/admin_auth.py` | `Depends(require_admin)` | WIRED | All 5 endpoint signatures include `Depends(require_admin)` |
| `app/routers/admin/users.py` | `app/services/admin_audit.py` | `log_admin_action()` calls | WIRED | 3 calls at lines 296, 343, 403 with `source="manual"` |
| `app/agents/admin/tools/users.py` | `app/agents/admin/agent.py` | `from app.agents.admin.tools.users import ...` | WIRED | Lines 17–24: all 6 tools imported; lines 94–99, 131–143: registered in singleton and factory |
| `app/agents/admin/tools/users.py` | `app/services/admin_audit.py` | `log_admin_action(source='ai_agent')` | WIRED | Lines 314–321, 365–372, 429–436, 475–482: all 4 mutating tools log with `source="ai_agent"` |
| `app/agents/admin/tools/users.py` | `admin_agent_permissions` table | `_check_autonomy()` queries | WIRED | `_check_autonomy()` present at lines 49–97; all 6 tools call it before executing |
| `frontend/src/app/(admin)/users/page.tsx` | `/admin/users API` | `fetch` with Bearer token | WIRED | Line 116: `fetch(\`${API_URL}/admin/users?${params.toString()}\`, { headers: { Authorization: \`Bearer ${session.access_token}\` } })` |
| `frontend/src/app/(admin)/users/[id]/page.tsx` | `/admin/users/{id} API` | `fetch` with Bearer token | WIRED | Line 75: `fetch(\`${API_URL}/admin/users/${userId}\`, ...)` |
| `frontend/src/app/(admin)/users/[id]/page.tsx` | `/admin/users/{id}/suspend API` | `fetch PATCH` | WIRED | Lines 124: `fetch(\`${API_URL}/admin/users/${userId}/${action}\`, { method: 'PATCH', ... })` |
| `frontend/src/app/(admin)/impersonate/[userId]/page.tsx` | `ImpersonationContext.tsx` | `ImpersonationProvider` wrapping | WIRED | Lines 129–136: `<ImpersonationProvider targetUser={...}>` wraps all content |
| `frontend/src/app/(admin)/impersonate/[userId]/page.tsx` | `/admin/users/{id} API` | `fetch` target user data | WIRED | Line 63: `fetch(\`${API_URL}/admin/users/${userId}\`, ...)` |
| `frontend/src/contexts/ImpersonationContext.tsx` | `frontend/src/contexts/PersonaContext.tsx` | `PersonaContext.Provider` override | WIRED | Line 13: `import { PersonaContext } from '@/contexts/PersonaContext'`; lines 131–135: `<PersonaContext.Provider value={personaOverride}>` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| USER-01 | 09-01, 09-02, 09-03 | Admin can search, filter, and paginate users in a table view | SATISFIED | REST API with search/persona/status/page params; TanStack Table v8 frontend with server-side pagination and debounced search |
| USER-02 | 09-01, 09-02, 09-03 | Admin can suspend and unsuspend user accounts | SATISFIED | PATCH /suspend and /unsuspend with ban_duration=876000h/none; frontend with window.confirm dialog; agent tools with confirm-tier gate |
| USER-03 | 09-02, 09-04 | Admin can view impersonation (see app as any user, read-only, non-dismissible banner) | SATISFIED | ImpersonationProvider + ImpersonationBanner with sticky banner, PersonaContext override, 30-min timer; read-only view at /admin/impersonate/[userId] |
| USER-05 | 09-01, 09-02, 09-03 | Admin can switch a user's persona | PARTIALLY SATISFIED | REST endpoint works correctly. Agent tool `change_user_persona` is broken due to wrong `_VALID_PERSONAS` set — all valid persona values are rejected (see Gap 2) |

**All 4 required IDs (USER-01, USER-02, USER-03, USER-05) are accounted for across plans.**
**USER-04 is correctly excluded — it is Phase 13 scope.**

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/agents/admin/tools/users.py` | 28–41 | Wrong `_VALID_PERSONAS` set (role-names instead of persona tiers) | Blocker | `change_user_persona` tool rejects all valid persona values and accepts none — USER-05 partially broken for agent path |
| `app/routers/admin/users.py` | 254–256 | `activity` returns `action_count` only; docstring at lines 184–185 promises `chat_count` and `workflow_count` | Warning | Frontend detail page renders blank activity stats (undefined.chat_count, undefined.workflow_count) — displayed as blank numbers in the UI |
| `app/agents/admin/tools/users.py` | 267 | `activity.note` stub: `"Activity counts require analytics integration (Phase 10)."` | Info | Agent tool cannot provide numeric activity stats; returns a note string. Does not affect phase goal but is a stub in get_user_detail. |

---

## Human Verification Required

### 1. User Table Rendering and Filtering

**Test:** Start the backend and frontend. Navigate to http://localhost:3000/admin/users.
**Expected:** User table renders with columns (email, persona badge, signup date, status badge). Search input filters by email with ~300ms delay. Persona dropdown and status dropdown filter results. Clicking a row navigates to /admin/users/[id].
**Why human:** Requires live Supabase Auth data with real users; table rendering and filter interaction cannot be verified statically.

### 2. Activity Stats Display on Detail Page

**Test:** Navigate to /admin/users/[id] for any user.
**Expected:** Activity card shows two numeric values labeled "Chat messages" and "Workflows run".
**Why human:** The backend returns `action_count` while the frontend reads `chat_count` and `workflow_count` — both will render as blank (undefined cast to number displays as NaN or 0). Human must confirm whether values are blank or if there is a default of 0 being applied.

### 3. Impersonation Banner Behaviour

**Test:** From a user detail page, click "Impersonate". Verify the impersonation view at /admin/impersonate/[userId].
**Expected:** Amber sticky banner visible at top with "Viewing as: user@email.com (persona) — READ ONLY". MM:SS countdown ticking. No dismiss button. Exit Impersonation button redirects to /admin/users.
**Why human:** Timer behavior, visual appearance, sticky positioning, and redirect require browser verification.

### 4. Audit Log Source Separation

**Test:** Suspend a user via the UI (detail page). Then ask the AdminAgent in the admin chat "suspend user [id]" and approve the confirmation. Check admin_audit_log.
**Expected:** UI-originated action has `source='manual'`. Agent-originated action has `source='ai_agent'`. Neither appears as user-originated.
**Why human:** Requires running system and direct database inspection.

---

## Gaps Summary

Two gaps block complete goal achievement:

**Gap 1 — Activity field mismatch (Warning severity):** `GET /admin/users/{id}` returns `{"activity": {"action_count": N}}` but the frontend `UserDetail` interface declares `activity.chat_count` and `activity.workflow_count`. The detail page renders `user.activity.chat_count` and `user.activity.workflow_count`, both of which will be `undefined` at runtime. The activity stats card will display blank or NaN values. This is a schema contract break between Plan 01 (backend) and Plan 03 (frontend). Fix: either split `action_count` into `chat_count` + `workflow_count` in the backend (requires real data sources beyond audit log counting), or align the frontend type to use `action_count` and update the labels.

**Gap 2 — Wrong `_VALID_PERSONAS` in agent tools (Blocker severity):** `app/agents/admin/tools/users.py` defines `_VALID_PERSONAS` as a set of role-names from a different domain (`executive`, `manager`, `analyst`, `sales`, `marketing`, `operations`, `finance`, `hr`, `compliance`, `support`) that has no overlap with the project's actual persona tiers (`solopreneur`, `startup`, `sme`, `enterprise`). The `change_user_persona` tool validates the `new_persona` argument against this set before calling `_check_autonomy()`. This means every call with a real persona value (`solopreneur`, `startup`, `sme`, `enterprise`) returns `{"error": "Invalid persona '...'. Valid personas: ..."}` immediately, never reaching the confirmation gate or the DB update. The REST endpoint (`app/routers/admin/users.py`) has the correct set. Fix: replace `_VALID_PERSONAS` in `tools/users.py` with `frozenset({'solopreneur', 'startup', 'sme', 'enterprise'})` and update `test_user_tools.py` line 196 to pass `'startup'` instead of `'executive'`.

These two gaps share a common root cause: both were introduced silently without a corresponding test that would have caught the mismatch. The `_VALID_PERSONAS` bug is particularly notable because the test suite for `test_user_tools.py` used `"executive"` as the test persona value — which accidentally passes validation against the wrong set, masking the bug.

---

_Verified: 2026-03-21T20:30:00Z_
_Verifier: Claude (gsd-verifier)_
