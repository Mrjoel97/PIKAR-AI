# Phase 9: User Management + Impersonation View - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning
**Source:** PRD Express Path (docs/superpowers/specs/2026-03-21-admin-panel-design.md)

<domain>
## Phase Boundary

This phase adds user management (search, filter, paginate, suspend/unsuspend, persona switch) and read-only impersonation view mode. After this phase, the admin can find any user, take basic account actions, and view the app exactly as that user sees it — all logged to the audit trail with impersonation source tagging.

**Requirements:** USER-01, USER-02, USER-03, USER-05 (4 total)
**NOT in scope:** USER-04 (interactive impersonation — Phase 13)

</domain>

<decisions>
## Implementation Decisions

### User Management Backend
- New API endpoints under admin router:
  - `GET /admin/users` — search/filter/paginate users (query params: search, persona, status, page, page_size)
  - `GET /admin/users/{id}` — full user profile with activity stats
  - `PATCH /admin/users/{id}/suspend` — suspend user account
  - `PATCH /admin/users/{id}/unsuspend` — unsuspend user account
  - `PATCH /admin/users/{id}/persona` — change user's persona tier
- All endpoints gated by `require_admin` middleware
- Uses service role Supabase client (bypasses RLS) to query across all users
- User data comes from `auth.users` + `user_executive_agents` tables
- Suspend/unsuspend uses Supabase Auth Admin API (`supabase.auth.admin.update_user_by_id`) to set `banned_until` field
- Persona switch updates the `persona` field in `user_executive_agents` table
- All actions logged to `admin_audit_log` with source: 'manual' or 'ai_agent'

### User Management Frontend
- Route: `/admin/users` — user table with search, filters, pagination
- Route: `/admin/users/[id]` — individual user detail page
- Uses `@tanstack/react-table` for headless server-side pagination
- Table columns: name, email, persona, signup date, last active, status
- Actions on user detail: suspend/unsuspend button, persona dropdown, impersonate button
- Suspend action shows a confirmation dialog (not agent confirm card — this is a direct UI action)

### Impersonation View Mode
- Route: `/admin/impersonate/[userId]` — wraps existing persona layouts
- `ImpersonationContext` provider overrides `PersonaContext` with target user's persona and data
- Persistent non-dismissible banner at top: "Viewing as: user@example.com (startup persona) [Exit Impersonation]"
- Banner cannot be closed, scrolled away, or hidden — always visible
- View mode is read-only: all mutation endpoints (POST, PATCH, DELETE) are blocked in impersonation
- Backend: admin endpoints accept optional `X-Impersonate-User-Id` header
- When present + requester is admin: data is scoped to target user
- All impersonation actions logged to `admin_audit_log` with source: 'impersonation'
- Impersonation sessions auto-expire after 30 minutes (tracked via session start time in context)

### Admin Agent User Tools
- New tools in `app/agents/admin/tools/users.py`:
  - `list_users` (auto) — search/filter users with pagination
  - `get_user_detail` (auto) — full user profile, persona, activity
  - `suspend_user` (confirm) — disable a user account
  - `unsuspend_user` (confirm) — re-enable a user account
  - `change_user_persona` (confirm) — switch a user's persona tier
  - `impersonate_user` (confirm) — open impersonation view for a user
- All tools use autonomy enforcement from Phase 7 infrastructure

### Backend Structure
- `app/routers/admin/users.py` — user management API endpoints
- `app/agents/admin/tools/users.py` — agent user tools
- Update `app/routers/admin/__init__.py` to register users router
- Update `app/agents/admin/agent.py` to register user tools

### Frontend Structure
- `frontend/src/app/(admin)/users/page.tsx` — user list table
- `frontend/src/app/(admin)/users/[id]/page.tsx` — user detail page
- `frontend/src/app/(admin)/impersonate/[userId]/page.tsx` — impersonation view
- `frontend/src/contexts/ImpersonationContext.tsx` — impersonation state provider
- `frontend/src/components/admin/ImpersonationBanner.tsx` — non-dismissible banner

### Claude's Discretion
- Exact user table column widths and responsive breakpoints
- User detail page layout (card sections, activity stats visualization)
- How to determine "last active" timestamp (last chat message? last login?)
- Impersonation banner styling (color, position, z-index)
- Search debounce timing
- Whether to use URL query params or React state for filter persistence
- Error handling for suspended user login attempts (which Supabase error code maps to "account suspended")

</decisions>

<specifics>
## Specific Ideas

- User table should show a colored status badge: green for active, red for suspended
- Persona column should show the persona icon from the existing persona system
- Impersonation banner should be red/amber to clearly distinguish from normal operation
- "Exit Impersonation" button should redirect back to `/admin/users`
- User detail page should show: profile info, persona, signup date, last active, chat history count, workflows run, agent usage breakdown

</specifics>

<deferred>
## Deferred Ideas

- Interactive impersonation mode (USER-04) — Phase 13, requires super_admin role
- Bulk CSV export of user data — future requirement
- Bulk email to users — future requirement
- User deletion (blocked-level action) — requires careful data cleanup, deferred

</deferred>

---

*Phase: 09-user-management*
*Context gathered: 2026-03-21 via PRD Express Path*
