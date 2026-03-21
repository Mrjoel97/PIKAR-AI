# Phase 9: User Management + Impersonation View - Research

**Researched:** 2026-03-21
**Domain:** Supabase Auth Admin API, server-side user table pagination, React context override for impersonation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**User Management Backend**
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

**User Management Frontend**
- Route: `/admin/users` — user table with search, filters, pagination
- Route: `/admin/users/[id]` — individual user detail page
- Uses `@tanstack/react-table` for headless server-side pagination
- Table columns: name, email, persona, signup date, last active, status
- Actions on user detail: suspend/unsuspend button, persona dropdown, impersonate button
- Suspend action shows a confirmation dialog (not agent confirm card — this is a direct UI action)

**Impersonation View Mode**
- Route: `/admin/impersonate/[userId]` — wraps existing persona layouts
- `ImpersonationContext` provider overrides `PersonaContext` with target user's persona and data
- Persistent non-dismissible banner at top: "Viewing as: user@example.com (startup persona) [Exit Impersonation]"
- Banner cannot be closed, scrolled away, or hidden — always visible
- View mode is read-only: all mutation endpoints (POST, PATCH, DELETE) are blocked in impersonation
- Backend: admin endpoints accept optional `X-Impersonate-User-Id` header
- When present + requester is admin: data is scoped to target user
- All impersonation actions logged to `admin_audit_log` with source: 'impersonation'
- Impersonation sessions auto-expire after 30 minutes (tracked via session start time in context)

**Admin Agent User Tools**
- New tools in `app/agents/admin/tools/users.py`:
  - `list_users` (auto) — search/filter users with pagination
  - `get_user_detail` (auto) — full user profile, persona, activity
  - `suspend_user` (confirm) — disable a user account
  - `unsuspend_user` (confirm) — re-enable a user account
  - `change_user_persona` (confirm) — switch a user's persona tier
  - `impersonate_user` (confirm) — open impersonation view for a user
- All tools use autonomy enforcement from Phase 7 infrastructure

**Backend Structure**
- `app/routers/admin/users.py` — user management API endpoints
- `app/agents/admin/tools/users.py` — agent user tools
- Update `app/routers/admin/__init__.py` to register users router
- Update `app/agents/admin/agent.py` to register user tools

**Frontend Structure**
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

### Deferred Ideas (OUT OF SCOPE)
- Interactive impersonation mode (USER-04) — Phase 13, requires super_admin role
- Bulk CSV export of user data — future requirement
- Bulk email to users — future requirement
- User deletion (blocked-level action) — requires careful data cleanup, deferred
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| USER-01 | Admin can search, filter, and paginate users in a table view | `auth.users` + `user_executive_agents` join, `@tanstack/react-table` server-side pagination, Supabase service-role client |
| USER-02 | Admin can suspend and unsuspend user accounts | `supabase.auth.admin.update_user_by_id` with `ban_duration` ("none" to unsuspend), GoTrue AdminUserAttributes TypedDict |
| USER-03 | Admin can view impersonation (see app as any user, read-only, non-dismissible banner) | `ImpersonationContext` overriding `PersonaContext`, `X-Impersonate-User-Id` header pattern, 30-min session timer |
| USER-05 | Admin can switch a user's persona | `PATCH` to `user_executive_agents.persona` column, persona CHECK constraint validated values, audit log |
</phase_requirements>

---

## Summary

Phase 9 builds on the Phase 7/8 admin foundation cleanly. Every pattern needed already exists in the codebase — this phase applies them to a new domain (users) rather than inventing new infrastructure. The primary new integration is the Supabase Auth Admin API (`auth.admin.update_user_by_id` with `ban_duration`) which is verified against the installed `supabase_auth` package (v2.27.2). The frontend requires adding `@tanstack/react-table` (not yet in package.json) using the `manualPagination: true` server-side pattern. Impersonation context is a straightforward React context override pattern — the `PersonaContext` already carries all necessary state (`persona`, `userId`, `agentName`) and `ImpersonationContext` replaces those values with the target user's data while adding `sessionStartTime` and `targetUserEmail`.

The only genuinely tricky area is the X-Impersonate-User-Id header flow: the backend router endpoints that serve user data must be designed to scope their queries to `target_user_id` rather than `admin_user_id` when this header is present. Because impersonation view is read-only, mutation endpoints do not need to handle this header at all — the frontend simply never fires them in impersonation mode.

The audit log schema (admin_audit_log, Phase 7) already supports `source: 'impersonation'` — this was confirmed in the existing `audit.py` router. The `impersonation_session_id` column is schema-ready but is not populated until Phase 13 (AUDT-04). Phase 9 only needs to set `source: 'impersonation'` in the audit rows.

**Primary recommendation:** Use `auth.admin.update_user_by_id` with `ban_duration="none"` to unsuspend (not a direct database update), follow the `_check_autonomy()` helper pattern from `monitoring.py` for all user tools, and implement `ImpersonationContext` as a provider that wraps the impersonation route's layout.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `supabase-auth` | 2.27.2 (installed) | Auth admin API: suspend/unsuspend via `update_user_by_id` | Already a project dependency via `supabase>=2.27.2,<3.0.0` |
| `@tanstack/react-table` | ^8.21.3 | Headless server-side paginated user table | Confirmed in project research SUMMARY.md; not yet installed — needs `npm install` |
| Supabase service client (`get_service_client`) | existing | Query `auth.users` + `user_executive_agents` across all users, bypassing RLS | All admin endpoints already use this pattern |
| `log_admin_action` | existing | Audit all user actions | Phase 7 service, already used in `chat.py` |
| `_check_autonomy()` | existing | Enforce autonomy tiers in user tools | Defined in `monitoring.py`, must be copied/imported for `users.py` tools |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `lucide-react` | ^0.563.0 (installed) | User status icons, action buttons | Already a dependency — no install needed |
| `sonner` | ^2.0.7 (installed) | Toast notifications for suspend/unsuspend actions | Already a dependency — use for success/error toasts |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@tanstack/react-table` | Plain `<table>` with manual state | TanStack Table prescribed by CONTEXT.md locked decisions; provides column sorting, filtering hooks for free |
| `ban_duration` API | Direct DB `UPDATE auth.users SET banned_until` | Auth Admin API is the correct path — direct DB writes to `auth.users` from app code are not supported in Supabase |

**Installation:**
```bash
cd frontend && npm install @tanstack/react-table@^8.21.3
```

---

## Architecture Patterns

### Recommended Project Structure

New files for this phase:
```
app/
├── routers/admin/
│   ├── users.py              # NEW: user management endpoints
│   └── __init__.py           # UPDATE: register users router
├── agents/admin/
│   ├── tools/
│   │   └── users.py          # NEW: agent user tools
│   └── agent.py              # UPDATE: register user tools

frontend/src/
├── app/(admin)/
│   ├── users/
│   │   ├── page.tsx          # NEW: user list table
│   │   └── [id]/
│   │       └── page.tsx      # NEW: user detail page
│   └── impersonate/
│       └── [userId]/
│           └── page.tsx      # NEW: impersonation view wrapper
├── contexts/
│   └── ImpersonationContext.tsx   # NEW: impersonation state
└── components/admin/
    └── ImpersonationBanner.tsx    # NEW: non-dismissible banner
```

### Pattern 1: Supabase Auth Admin — Suspend/Unsuspend

**What:** Call `client.auth.admin.update_user_by_id(uid, {"ban_duration": "876000h"})` to suspend indefinitely; `{"ban_duration": "none"}` to unsuspend.

**When to use:** Any time a user account must be disabled/re-enabled without deleting data.

**Key finding from installed SDK** (`supabase_auth/types.py` line 249-254):
```python
# Source: .venv/Lib/site-packages/supabase_auth/types.py
class AdminUserAttributes(UserAttributes, TypedDict):
    user_metadata: NotRequired[Any]
    app_metadata: NotRequired[Any]
    email_confirm: NotRequired[bool]
    phone_confirm: NotRequired[bool]
    ban_duration: NotRequired[Union[str, Literal["none"]]]
    role: NotRequired[str]
    ...
```

**Example:**
```python
# Source: .venv/Lib/site-packages/supabase_auth/_sync/gotrue_admin_api.py
# Suspend: large duration effectively permanent; can use "876000h" (100 years)
client.auth.admin.update_user_by_id(uid, {"ban_duration": "876000h"})

# Unsuspend: "none" lifts the ban
client.auth.admin.update_user_by_id(uid, {"ban_duration": "none"})
```

**Critical note:** `auth.admin` is a sync API. The existing `get_service_client()` returns a sync Supabase `Client`. Call `client.auth.admin.update_user_by_id(...)` directly — no `await`, no `execute_async`. Wrap in `asyncio.to_thread()` if called from an async endpoint to avoid blocking the event loop.

### Pattern 2: User List Query — Join auth.users + user_executive_agents

**What:** The service role client bypasses RLS on both `auth.users` and `user_executive_agents`. Query `user_executive_agents` first (it has persona, last_active approximation), join or cross-reference with `auth.users` for email, signup date, and `banned_until`.

**When to use:** `GET /admin/users` list and `GET /admin/users/{id}` detail.

**Example:**
```python
# Source: existing project pattern — service role client + Supabase query builder
client = get_service_client()

# Query user_executive_agents for app-level data
result = (
    client.table("user_executive_agents")
    .select("user_id, persona, agent_name, created_at, updated_at, onboarding_completed")
    .order("created_at", desc=True)
    .range(offset, offset + page_size - 1)
    .execute()
)

# For each user_id, fetch auth.users data via auth admin API
auth_user = client.auth.admin.get_user_by_id(user_id)
# auth_user.user.email, auth_user.user.created_at, auth_user.user.banned_until
```

**Note:** `auth.users` is not directly queryable via the PostgREST `.table()` API — use `client.auth.admin.get_user_by_id(uid)` or `client.auth.admin.list_users()`. The `list_users()` method returns a `List[User]` with `page` and `per_page` params.

**Alternative for search:** The PostgREST API cannot search `auth.users.email` directly. Use `client.auth.admin.list_users(page=N, per_page=50)` then filter in Python, OR expose a Supabase RPC function that queries `auth.users` with the service key.

**Recommendation:** For the `GET /admin/users` search endpoint, create a Supabase SQL function (or query `auth.users` via RPC) to enable server-side email search. The simpler path is `auth.admin.list_users()` with Python-side filtering for MVP.

### Pattern 3: Autonomy Enforcement for User Tools

**What:** Copy the `_check_autonomy()` helper pattern from `app/agents/admin/tools/monitoring.py` exactly.

**When to use:** Every function in `app/agents/admin/tools/users.py`.

**Example:**
```python
# Source: app/agents/admin/tools/monitoring.py (lines 28-76)
async def _check_autonomy(action_name: str) -> dict | None:
    """Returns gate dict if blocked/confirm, None to proceed."""
    try:
        client = get_service_client()
        res = (
            client.table("admin_agent_permissions")
            .select("autonomy_level")
            .eq("action_name", action_name)
            .limit(1)
            .execute()
        )
        if res.data:
            level = res.data[0].get("autonomy_level", "auto")
            if level == "blocked":
                return {"error": f"{action_name} is blocked ..."}
            if level == "confirm":
                token = str(uuid.uuid4())
                return {
                    "requires_confirmation": True,
                    "confirmation_token": token,
                    "action_details": {
                        "action": action_name,
                        "risk_level": "medium",  # adjust per tool
                        "description": "...",
                    },
                }
    except Exception as exc:
        logger.warning("Could not verify autonomy level ...: %s", exc)
    return None
```

New permission seeds needed in migration for `admin_agent_permissions`:
```sql
INSERT INTO admin_agent_permissions (action_category, action_name, autonomy_level, risk_level, description)
VALUES
    ('users', 'list_users',           'auto',    'low',    'List and search user accounts'),
    ('users', 'get_user_detail',      'auto',    'low',    'Get full user profile and activity stats'),
    ('users', 'suspend_user',         'confirm', 'medium', 'Temporarily suspend a user account'),
    ('users', 'unsuspend_user',       'confirm', 'medium', 'Re-enable a suspended user account'),
    ('users', 'change_user_persona',  'confirm', 'medium', 'Switch a user persona tier'),
    ('users', 'impersonate_user',     'confirm', 'low',    'Open read-only impersonation view for a user')
ON CONFLICT (action_category, action_name) DO NOTHING;
```

### Pattern 4: TanStack Table Server-Side Pagination

**What:** `useReactTable` with `manualPagination: true` + `rowCount`. The table does NOT paginate data itself — it only manages `pageIndex`/`pageSize` state and calculates `pageCount`. The component fetches from the server when pagination state changes.

**When to use:** `frontend/src/app/(admin)/users/page.tsx`.

**Example:**
```typescript
// Source: https://tanstack.com/table/v8/docs/guide/pagination
import {
  useReactTable,
  getCoreRowModel,
  type ColumnDef,
  type PaginationState,
} from '@tanstack/react-table';
import { useState } from 'react';

const [pagination, setPagination] = useState<PaginationState>({
  pageIndex: 0,
  pageSize: 25,
});

// Fetch from server when pagination changes
// useEffect runs on pagination state change

const table = useReactTable({
  data,               // current page rows from server
  columns,
  rowCount: total,    // total rows from server (v8.13+)
  state: { pagination },
  onPaginationChange: setPagination,
  manualPagination: true,   // CRITICAL: disables client-side pagination
  getCoreRowModel: getCoreRowModel(),
});
```

**Note:** `rowCount` was added in `@tanstack/react-table` v8.13.0. For earlier versions use `pageCount` directly. Since we install `^8.21.3`, `rowCount` is available.

**Note on column sorting/filtering:** The user table does NOT need `getSortedRowModel()` or `getFilteredRowModel()` because sorting and filtering happen server-side (query params). Only `getCoreRowModel()` is needed.

### Pattern 5: ImpersonationContext — Override PersonaContext

**What:** `ImpersonationContext` provides the same interface as `PersonaContext` but with the target user's data injected statically. The impersonation view renders existing persona layouts — they call `usePersona()` and get the impersonated user's data transparently.

**When to use:** `frontend/src/app/(admin)/impersonate/[userId]/page.tsx` layout.

**PersonaContext interface** (verified from `frontend/src/contexts/PersonaContext.tsx`):
```typescript
interface PersonaContextType {
  persona: Persona;           // target user's persona
  setPersona: (persona: Persona) => void;  // no-op in impersonation
  isLoading: boolean;         // false (data already fetched)
  userId: string | null;      // target user's ID
  userEmail: string | null;   // target user's email
  agentName: string | null;   // target user's agent name
}
```

**Example:**
```typescript
// Source: project pattern derived from PersonaContext.tsx
'use client';
import { createContext, useContext, useState } from 'react';

interface ImpersonationState {
  isActive: boolean;
  targetUserId: string;
  targetUserEmail: string;
  sessionStartTime: Date;
  // PersonaContext overrides:
  persona: Persona;
  agentName: string | null;
}

const ImpersonationContext = createContext<ImpersonationState | null>(null);

export function ImpersonationProvider({
  children,
  targetUser,  // pre-fetched target user data
}: {
  children: React.ReactNode;
  targetUser: { id: string; email: string; persona: Persona; agentName: string | null };
}) {
  const [sessionStartTime] = useState(() => new Date());

  return (
    <ImpersonationContext.Provider value={{
      isActive: true,
      targetUserId: targetUser.id,
      targetUserEmail: targetUser.email,
      sessionStartTime,
      persona: targetUser.persona,
      agentName: targetUser.agentName,
    }}>
      {children}
    </ImpersonationContext.Provider>
  );
}
```

**Key architectural constraint:** The impersonation view at `/admin/impersonate/[userId]/page.tsx` must be a **server component** that fetches the target user's data, then passes it to a client-side `ImpersonationProvider`. The existing persona layouts use `usePersona()` from `PersonaContext` — the impersonation page does NOT re-use `PersonaProvider` but instead renders the persona layout fragment directly with mocked context. Alternatively, create a thin `ImpersonationPersonaProvider` that satisfies the `PersonaContext.Provider` interface with the target user's data.

### Pattern 6: Admin Router Registration

**What:** Add `users` router to `app/routers/admin/__init__.py` following the existing 4-router pattern.

**Example:**
```python
# Source: app/routers/admin/__init__.py (existing pattern)
from app.routers.admin import audit, auth, chat, monitoring, users  # add users

# Phase 9: user management endpoints
admin_router.include_router(users.router)
```

**Admin agent tool registration** — add to `app/agents/admin/agent.py`:
```python
# Source: app/agents/admin/agent.py (existing pattern)
from app.agents.admin.tools.users import (
    list_users,
    get_user_detail,
    suspend_user,
    unsuspend_user,
    change_user_persona,
    impersonate_user,
)
# Add to tools list in admin_agent and create_admin_agent()
```

### Pattern 7: fetchWithAuth Pattern in Frontend

**What:** Existing admin pages use inline `supabase.auth.getSession()` + `fetch(url, { headers: { Authorization: \`Bearer ${token}\` } })` — there is no shared `fetchWithAuth` utility. This is the established project pattern.

**Example:**
```typescript
// Source: frontend/src/app/(admin)/monitoring/page.tsx (existing pattern)
const { data: { session } } = await supabase.auth.getSession();
if (!session) { /* handle unauthenticated */ return; }

const res = await fetch(`${API_URL}/admin/users`, {
  headers: { Authorization: `Bearer ${session.access_token}` },
});
```

**For impersonation:** When fetching data in impersonation mode, no special header is needed for read endpoints — the backend user endpoints designed to serve the impersonation view will receive the `X-Impersonate-User-Id` header injected by `ImpersonationContext`-aware fetch calls.

### Anti-Patterns to Avoid

- **Direct write to `auth.users`:** Do not attempt `client.table("auth.users")` — this table is not accessible via PostgREST. Use `client.auth.admin.update_user_by_id()` for all auth-layer mutations.
- **Awaiting `auth.admin` calls:** `client.auth.admin.update_user_by_id()` is synchronous. Do not `await` it. Use `asyncio.to_thread()` in async endpoints.
- **Calling `PersonaContext.Provider` inside impersonation:** The impersonation page wraps persona layouts; don't instantiate a real `PersonaProvider` (it would re-fetch the admin's own persona from Supabase). Use a static value provider instead.
- **Dismissible impersonation banner:** The banner must be `position: sticky; top: 0; z-index: 9999` or `position: fixed; top: 0` with no close button. Do not use `sonner` for this — it can be dismissed.
- **Audit log contamination:** All PATCH/action endpoints in `app/routers/admin/users.py` must log to `admin_audit_log` with `source='manual'` (direct UI actions). The agent tools log with `source='ai_agent'`. Impersonation page fetches log with `source='impersonation'`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| User suspension | Direct SQL `UPDATE auth.users SET banned_until` | `client.auth.admin.update_user_by_id(uid, {"ban_duration": "876000h"})` | auth.users is not writable via PostgREST; Admin API handles auth side effects (sign out active sessions) |
| Pagination state | Custom offset/page tracking with plain `useState` counters | `@tanstack/react-table` with `PaginationState` | Prescribed by locked decisions; provides column state management, accessible table markup, sorting hooks for free |
| Admin audit logging | Custom DB insert per endpoint | `log_admin_action()` from `app/services/admin_audit.py` | Already exists, handles error isolation (audit failures never propagate) |
| Autonomy enforcement | Custom permission check per tool | `_check_autonomy()` helper from `monitoring.py` | Already established pattern, must be consistent across all admin agent tools |
| Token for auth fetches | Custom auth header utility | Inline `supabase.auth.getSession()` + `fetch` | Established project pattern in all existing admin pages |

---

## Common Pitfalls

### Pitfall 1: `auth.admin` is Synchronous — Blocks Async Event Loop
**What goes wrong:** Calling `client.auth.admin.update_user_by_id(...)` directly in an `async def` FastAPI endpoint blocks the asyncio event loop for the duration of the HTTP call to GoTrue. Under load, this can cause all requests to queue behind the blocking call.
**Why it happens:** The `supabase_auth` `SyncGoTrueAdminAPI` uses `httpx.Client` (sync), not `httpx.AsyncClient`.
**How to avoid:** Wrap in `asyncio.to_thread()`:
```python
import asyncio
result = await asyncio.to_thread(
    client.auth.admin.update_user_by_id,
    uid,
    {"ban_duration": "876000h"},
)
```
**Warning signs:** Response times on user endpoints spike under concurrent admin usage.

### Pitfall 2: `list_users()` Returns All Users — No Server-Side Email Search
**What goes wrong:** `client.auth.admin.list_users(page=N, per_page=50)` returns paginated users but does not support a `search` or `email` filter parameter. Implementing `GET /admin/users?search=foo` with Python-side filtering means fetching all pages to find matching users.
**Why it happens:** GoTrue's `GET /admin/users` endpoint does not support query-based filtering.
**How to avoid:** For the MVP (small user count), Python-side filtering across a single `list_users()` call is acceptable. If user count grows, add a Supabase SQL RPC function that queries `auth.users` with `ILIKE` on email using the service key. Document the limitation and flag for future optimization.
**Warning signs:** `GET /admin/users?search=...` is slow when user count exceeds 500.

### Pitfall 3: ImpersonationContext Does Not Override PersonaContext
**What goes wrong:** Impersonation view renders existing persona layout components that call `usePersona()`. If `PersonaContext.Provider` is not replaced, `usePersona()` will still return the admin's own persona/userId, not the target user's.
**Why it happens:** React context lookup walks up the tree — if `PersonaProvider` is still mounted above the impersonation layout (e.g., in the root layout), `usePersona()` will find it first.
**How to avoid:** The impersonation route at `/admin/impersonate/[userId]/` must mount a `PersonaContext.Provider` (not `PersonaProvider`) directly with static target user values, positioned closer in the tree than the outer `PersonaProvider`. The outer `PersonaProvider` in the `(personas)` layout group is not present in the `(admin)` layout group — verify the Next.js route group structure to confirm isolation.
**Warning signs:** `usePersona().userId` returns the admin's user ID instead of the target user's ID during impersonation.

### Pitfall 4: Impersonation Session Timer Without Page Lifecycle
**What goes wrong:** Tracking 30-minute session expiry with `Date.now()` in context works as long as the React component stays mounted. If the admin navigates to a different admin route and comes back, a new `ImpersonationProvider` mounts and resets the timer.
**Why it happens:** Context state is in-memory and not persisted across route changes that unmount the provider.
**How to avoid:** Store `sessionStartTime` in `sessionStorage` under a key tied to `targetUserId`. On mount, check sessionStorage first; only set a new start time if none exists or if the timer has already expired.
**Warning signs:** Admin can refresh/navigate to extend their session beyond 30 minutes.

### Pitfall 5: Supabase `banned_until` vs `ban_duration` Confusion
**What goes wrong:** The database field is `banned_until` (a timestamp), but the API parameter is `ban_duration` (a Go duration string like "876000h"). Passing `banned_until` directly as an API parameter will not work.
**Why it happens:** The Admin API computes `banned_until = now() + ban_duration` server-side.
**How to avoid:** Always use `{"ban_duration": "876000h"}` for suspend (not `{"banned_until": "2099-01-01"}`). Use `{"ban_duration": "none"}` for unsuspend. Verified against installed SDK `AdminUserAttributes` TypedDict.

### Pitfall 6: Admin Agent Tools Missing from `admin_agent_permissions` Seed
**What goes wrong:** New user tools call `_check_autonomy("suspend_user")` but no row exists in `admin_agent_permissions` for `action_name="suspend_user"`. The helper's `except` branch defaults to "auto" — every confirm-tier action executes immediately without confirmation.
**Why it happens:** The migration seed only included `('users', 'suspend_user', 'confirm', ...)` in Phase 7's initial seed (from `20260321300000_admin_panel_foundation.sql`) but the other new tool names are not yet seeded.
**How to avoid:** Phase 9 migration must include `INSERT INTO admin_agent_permissions` for all 6 new user tool action names. The Phase 7 migration already seeds `('users', 'suspend_user', 'confirm', ...)` — do not duplicate that row; use `ON CONFLICT DO NOTHING`.

### Pitfall 7: User Detail Page Fetches Activity Stats Across Multiple Tables
**What goes wrong:** `GET /admin/users/{id}` should show "chat history count, workflows run, agent usage breakdown." These require querying `admin_chat_messages`, `workflow_executions`, `interaction_logs` — potentially expensive cross-table queries.
**Why it happens:** Activity stats are spread across application tables, not pre-aggregated.
**How to avoid:** Use `COUNT(*)` queries with `limit` bounds (e.g., count last 90 days of chat messages only). Document that these are approximate counts. Do NOT attempt real-time aggregation across the full history — this is an admin diagnostic view, not a billing-grade analytics report.

---

## Code Examples

### User List Backend Endpoint

```python
# Source: project pattern derived from app/routers/admin/monitoring.py
@router.get("/users")
@limiter.limit("60/minute")
async def list_users(
    request: Request,
    admin_user: dict = Depends(require_admin),
    search: str | None = None,
    persona: Literal["solopreneur", "startup", "sme", "enterprise"] | None = None,
    status: Literal["active", "suspended"] | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict:
    client = get_service_client()
    # Query user_executive_agents for paginated user list
    offset = (page - 1) * page_size
    query = (
        client.table("user_executive_agents")
        .select("user_id, persona, agent_name, onboarding_completed, created_at, updated_at", count="exact")
        .order("created_at", desc=True)
        .range(offset, offset + page_size - 1)
    )
    if persona:
        query = query.eq("persona", persona)
    result = await execute_async(query, op_name="admin.users.list")
    # Enrich with auth data per user via asyncio.to_thread for ban status
    ...
```

### Suspend User Backend

```python
# Source: supabase_auth types.py AdminUserAttributes (verified locally)
async def _suspend_user(uid: str) -> None:
    client = get_service_client()
    await asyncio.to_thread(
        client.auth.admin.update_user_by_id,
        uid,
        {"ban_duration": "876000h"},  # ~100 years = effectively permanent
    )

async def _unsuspend_user(uid: str) -> None:
    client = get_service_client()
    await asyncio.to_thread(
        client.auth.admin.update_user_by_id,
        uid,
        {"ban_duration": "none"},  # "none" lifts the ban
    )
```

### ImpersonationBanner Component

```typescript
// Source: project pattern — non-dismissible fixed position banner
'use client';
import { useRouter } from 'next/navigation';

interface ImpersonationBannerProps {
  targetEmail: string;
  persona: string;
  sessionStartTime: Date;
  onExit: () => void;
}

export function ImpersonationBanner({
  targetEmail, persona, sessionStartTime, onExit,
}: ImpersonationBannerProps) {
  // Banner is sticky top-0, z-50 (above all content)
  // No close/dismiss button — onExit redirects to /admin/users
  return (
    <div className="sticky top-0 z-50 flex items-center justify-between
                    bg-amber-600 text-white px-4 py-2 text-sm font-medium">
      <span>
        Viewing as: {targetEmail} ({persona} persona) — READ ONLY
      </span>
      <button type="button" onClick={onExit}
              className="ml-4 underline hover:no-underline">
        Exit Impersonation
      </button>
    </div>
  );
}
```

### TanStack Table Server-Side Pagination

```typescript
// Source: https://tanstack.com/table/v8/docs/guide/pagination
import {
  useReactTable,
  getCoreRowModel,
  type ColumnDef,
  type PaginationState,
} from '@tanstack/react-table';
import { useState, useEffect } from 'react';

const PAGE_SIZE = 25;

export default function UsersPage() {
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: PAGE_SIZE,
  });
  const [data, setData] = useState<UserRow[]>([]);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchUsers(pagination.pageIndex + 1, pagination.pageSize);
  }, [pagination]);

  const table = useReactTable({
    data,
    columns,
    rowCount: total,
    state: { pagination },
    onPaginationChange: setPagination,
    manualPagination: true,
    getCoreRowModel: getCoreRowModel(),
  });
  ...
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `supabase.auth.api.ban_user()` (JS) | `auth.admin.update_user_by_id(uid, {"ban_duration": "876000h"})` (Python) | supabase-py v2.x | Python SDK uses GoTrue Admin API, not deprecated `auth.api` methods |
| `pageCount` in TanStack Table | `rowCount` (table computes pageCount internally) | TanStack Table v8.13.0 | Use `rowCount: total` — simpler API, no manual pageCount calculation |

**Deprecated/outdated:**
- `supabase.auth.api.signOut()` — use `auth.admin.sign_out(jwt)` for force-signing out a user
- TanStack Table `pageCount` manual calculation — replaced by `rowCount` in v8.13+

---

## Open Questions

1. **"Last active" timestamp source**
   - What we know: `user_executive_agents.updated_at` reflects last config change, not last activity. `admin_chat_messages` has per-message timestamps. `interaction_logs` may have last API call.
   - What's unclear: Which table has the most reliable "user was active" signal.
   - Recommendation (Claude's discretion): Use `admin_chat_messages` MAX(created_at) per user_id as the "last active" proxy — it directly reflects user engagement. Fall back to `user_executive_agents.updated_at` if no messages.

2. **Email search implementation**
   - What we know: `auth.users` email is not queryable via PostgREST `.table()`. `client.auth.admin.list_users()` has no email filter parameter.
   - What's unclear: Whether project has an RPC function for email search already.
   - Recommendation: For MVP, use `list_users()` with Python-side `str.lower() in email.lower()` filtering. Add a SQL RPC function in the Phase 9 migration if search is needed at scale.

3. **`auth.users` data availability per user in `user_executive_agents` list**
   - What we know: The user list query returns `user_id` from `user_executive_agents`. To get email/banned_until, we need `client.auth.admin.get_user_by_id(uid)` per row — N+1 problem for large pages.
   - What's unclear: Whether a Supabase RPC can join auth.users efficiently.
   - Recommendation: For page sizes of 25, N+1 fetches via `asyncio.to_thread` + `asyncio.gather` are acceptable. Add a SQL function in migration to expose auth user data via a custom view if page load is slow.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (uv run pytest) |
| Config file | pyproject.toml (tool.pytest.ini_options) |
| Quick run command | `uv run pytest tests/unit/admin/ -x -q` |
| Full suite command | `uv run pytest tests/unit/admin/ tests/unit/app/ -x -q` |
| Frontend framework | vitest (node ./scripts/run-vitest.mjs) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| USER-01 | `GET /admin/users` returns paginated user list with correct shape | unit | `uv run pytest tests/unit/admin/test_users_api.py -x` | ❌ Wave 0 |
| USER-01 | `GET /admin/users` filters by persona and status | unit | `uv run pytest tests/unit/admin/test_users_api.py::test_list_users_filter -x` | ❌ Wave 0 |
| USER-02 | `PATCH /admin/users/{id}/suspend` calls `update_user_by_id` with `ban_duration="876000h"` | unit | `uv run pytest tests/unit/admin/test_users_api.py::test_suspend_user -x` | ❌ Wave 0 |
| USER-02 | `PATCH /admin/users/{id}/unsuspend` calls `update_user_by_id` with `ban_duration="none"` | unit | `uv run pytest tests/unit/admin/test_users_api.py::test_unsuspend_user -x` | ❌ Wave 0 |
| USER-02 | Suspend/unsuspend actions are logged to audit_log with source="manual" | unit | `uv run pytest tests/unit/admin/test_users_api.py::test_suspend_audit -x` | ❌ Wave 0 |
| USER-03 | `list_users` agent tool returns user list (auto tier) | unit | `uv run pytest tests/unit/admin/test_user_tools.py::test_list_users_tool -x` | ❌ Wave 0 |
| USER-03 | `suspend_user` agent tool returns confirmation request on confirm tier | unit | `uv run pytest tests/unit/admin/test_user_tools.py::test_suspend_user_confirm_tier -x` | ❌ Wave 0 |
| USER-05 | `PATCH /admin/users/{id}/persona` updates `user_executive_agents.persona` | unit | `uv run pytest tests/unit/admin/test_users_api.py::test_change_persona -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/admin/ -x -q`
- **Per wave merge:** `uv run pytest tests/unit/admin/ tests/unit/app/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/admin/test_users_api.py` — covers USER-01, USER-02, USER-05 (route-level unit tests following `test_monitoring_api.py` pattern)
- [ ] `tests/unit/admin/test_user_tools.py` — covers USER-03 agent tool tests following `test_autonomy.py` pattern

*(Shared fixtures in `tests/unit/admin/conftest.py` already exist — `mock_supabase_client`, `admin_user_dict`, `mock_verify_token`)*

---

## Sources

### Primary (HIGH confidence)
- `.venv/Lib/site-packages/supabase_auth/types.py` lines 249-254 — `AdminUserAttributes` TypedDict with `ban_duration: NotRequired[Union[str, Literal["none"]]]` — verified locally
- `.venv/Lib/site-packages/supabase_auth/_sync/gotrue_admin_api.py` lines 133-181 — `list_users(page, per_page)` and `update_user_by_id(uid, attributes)` signatures — verified locally
- `app/routers/admin/monitoring.py` — established router pattern (rate limiter, require_admin, execute_async)
- `app/agents/admin/tools/monitoring.py` — `_check_autonomy()` helper pattern for agent tools
- `app/services/admin_audit.py` — `log_admin_action()` service interface
- `frontend/src/contexts/PersonaContext.tsx` — `PersonaContextType` interface to replicate in `ImpersonationContext`
- `frontend/src/hooks/useAdminChat.ts` — `getToken()` + inline fetch pattern for authenticated admin calls
- `supabase/migrations/20260321300000_admin_panel_foundation.sql` — `admin_audit_log` schema, `admin_agent_permissions` seed format
- `supabase/migrations/0015_add_onboarding_columns.sql` — `user_executive_agents.persona` column with CHECK constraint
- `frontend/package.json` — confirmed `@tanstack/react-table` NOT yet installed (needs `npm install`)

### Secondary (MEDIUM confidence)
- [Supabase Python Auth Admin API](https://supabase.com/docs/reference/python/admin-api) — admin methods listing (page structure confirmed, ban_duration details in SDK source)
- [TanStack Table v8 Pagination Guide](https://tanstack.com/table/v8/docs/guide/pagination) — `manualPagination`, `rowCount`, `PaginationState` confirmed
- Web search: `ban_duration="none"` lifts ban — confirmed by multiple community sources and SDK source

### Tertiary (LOW confidence)
- Community sources on `banned_until` vs `ban_duration` parameter naming — corroborated by SDK source inspection

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against installed local SDK and existing project files
- Architecture: HIGH — derived directly from existing Phase 7/8 patterns in the codebase
- Pitfalls: HIGH — auth.admin sync/async issue verified from SDK source; banner dismissal is a UI design constraint

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (supabase-py version pinned; TanStack Table stable)
