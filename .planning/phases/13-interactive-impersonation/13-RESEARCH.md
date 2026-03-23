# Phase 13: Interactive Impersonation - Research

**Researched:** 2026-03-23
**Domain:** Admin impersonation sessions, endpoint allow-lists, audit tagging, user intelligence skills
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| USER-04 | Super admin can use interactive impersonation (allow-listed endpoints, notification suppression, 30-min expiry) | Phase 9 foundation (ImpersonationContext, ImpersonationBanner, sessionStorage timer) is already complete. Phase 13 upgrades it from read-only view to interactive mode by: (1) issuing a signed impersonation session token, (2) enforcing the allow-list in middleware, (3) suppressing notifications. |
| AUDT-04 | Impersonation actions tagged with impersonation_session_id in audit log | Schema is already ready: `admin_audit_log.impersonation_session_id uuid` column added in Phase 7 migration (20260321300000). log_admin_action() needs a new optional `impersonation_session_id` parameter wired in. |
| SKIL-03 | AdminAgent can identify at-risk users by correlating declining usage with billing status and last login | Available data: `sessions` table (updated_at per user), `session_events` (message counts), `admin_analytics_daily` (platform-level DAU/MAU), `auth.admin.get_user_by_id` (last_sign_in_at). Billing is via Stripe (Phase 14 owns the billing table; SKIL-03 uses Stripe integration proxy already in place from Phase 11). |
| SKIL-04 | AdminAgent provides structured support playbooks during interactive impersonation sessions | Prompt-injected capability in AdminAgent instruction. Tool: get_user_support_context (auto-tier) — fetches user's recent errors, usage trend, last session data. Playbook logic lives in the ADMIN_AGENT_INSTRUCTION, not in code. |

</phase_requirements>

---

## Summary

Phase 13 upgrades the existing read-only impersonation view (Phase 9) into an interactive mode that lets super admins perform support actions on behalf of a user. The technical work has three distinct tracks:

**Track 1 — Backend session tokens and allow-list enforcement.** The current impersonation flow is purely frontend: the admin navigates to `/admin/impersonate/{userId}` and the ImpersonationContext sets a sessionStorage timer. For interactive mode, the backend must issue a signed impersonation session record (a UUID row in a new `admin_impersonation_sessions` table), and all user-facing API calls during the session must pass this session ID in a header (`X-Impersonation-Session`). A new FastAPI dependency (`require_impersonation_or_user`) validates the header, checks the allow-list, enforces the 30-minute expiry, and populates `impersonation_session_id` in the audit log automatically.

**Track 2 — Notification suppression.** The platform sends notifications via email triage service and scheduled endpoints. During an active impersonation session, any notification pathway that would fire for the target user must check whether an active impersonation session exists and suppress it. The suppression flag lives in the `admin_impersonation_sessions` table (`is_active` boolean + `expires_at` timestamptz) — notification services query this before sending.

**Track 3 — User intelligence skills (SKIL-03 and SKIL-04).** These are prompt-injected capabilities: SKIL-03 adds a new `get_at_risk_users` tool that queries `sessions`, `session_events`, and auth data to build a watch list. SKIL-04 adds a `get_user_support_context` tool that pulls recent errors and usage for a specific user during an impersonation session and populates the ADMIN_AGENT_INSTRUCTION playbook.

**Primary recommendation:** Implement the impersonation session table and allow-list middleware as the core infrastructure (Plan 1), upgrade the AdminAgent tool and audit logging (Plan 2), then upgrade the frontend banner from amber to red and wire the session token into API calls (Plan 3).

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | New middleware dependency for impersonation session validation | Already used throughout admin routers |
| Supabase Python (supabase) | existing | New `admin_impersonation_sessions` table, session token queries | Established pattern (service role client) |
| pytest + AsyncMock | existing | Tests for new middleware, tools, and session service | Established project test pattern |
| Next.js / React 19 | existing | Frontend session token passing in fetch headers | Already used in ImpersonationBanner and impersonate page |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uuid (stdlib) | stdlib | Generating impersonation session IDs | Session table row creation |
| datetime + timezone | stdlib | Expiry calculation (`expires_at = now() + 30 minutes`) | Session validation, auto-expiry check |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New DB table for sessions | Redis key expiry | DB table is more auditable and survives Redis downtime; aligns with existing pattern (circuit breaker on Redis) |
| Middleware allow-list enforcement | Frontend-only allow-list | Frontend enforcement is trivially bypassable; must be backend-enforced |

---

## Architecture Patterns

### Recommended Project Structure

No new top-level directories. Additions within existing structure:

```
app/
├── middleware/
│   └── impersonation_auth.py       # NEW: validate X-Impersonation-Session header
├── services/
│   └── impersonation_service.py    # NEW: create/validate/expire impersonation sessions
├── routers/admin/
│   └── users.py                    # MODIFY: add POST /admin/impersonate/{userId}/start
│                                   #         and DELETE /admin/impersonate/{id}/end
├── agents/admin/tools/
│   └── users.py                    # MODIFY: upgrade impersonate_user to interactive mode
│   └── users_intelligence.py       # NEW: get_at_risk_users, get_user_support_context
├── agents/admin/
│   └── agent.py                    # MODIFY: add Phase 13 tools + SKIL-03/SKIL-04 instructions
└── services/
    └── admin_audit.py              # MODIFY: add impersonation_session_id parameter

supabase/migrations/
└── 2026032[N]000000_interactive_impersonation.sql  # NEW: admin_impersonation_sessions table

frontend/src/
├── contexts/
│   └── ImpersonationContext.tsx    # MODIFY: add sessionToken state, pass to API calls
├── components/admin/
│   └── ImpersonationBanner.tsx     # MODIFY: turn red on activation (not just on 5-min warning)
└── app/(admin)/impersonate/[userId]/
    └── page.tsx                    # MODIFY: call /admin/impersonate/{userId}/start, store token
```

### Pattern 1: Impersonation Session Lifecycle

**What:** A super admin activates interactive impersonation by calling `POST /admin/impersonate/{userId}/start`. The backend inserts a row into `admin_impersonation_sessions` and returns the session UUID. All subsequent user-context API calls during the session carry `X-Impersonation-Session: {session_id}`.

**When to use:** Any time a super admin clicks "Activate Interactive Impersonation" on the impersonation view.

**Example (session creation — backend):**

```python
# app/services/impersonation_service.py
import uuid
from datetime import datetime, timedelta, timezone
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

SESSION_DURATION_MINUTES = 30

async def create_impersonation_session(
    admin_user_id: str,
    target_user_id: str,
) -> dict:
    """Create an impersonation session row. Returns the session dict."""
    client = get_service_client()
    session_id = str(uuid.uuid4())
    expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=SESSION_DURATION_MINUTES)
    ).isoformat()

    row = {
        "id": session_id,
        "admin_user_id": admin_user_id,
        "target_user_id": target_user_id,
        "expires_at": expires_at,
        "is_active": True,
    }
    await execute_async(
        client.table("admin_impersonation_sessions").insert(row),
        op_name="impersonation.create_session",
    )
    return row


async def validate_impersonation_session(session_id: str) -> dict | None:
    """Validate session: returns row if active and not expired, None otherwise."""
    client = get_service_client()
    now = datetime.now(timezone.utc).isoformat()
    result = await execute_async(
        client.table("admin_impersonation_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("is_active", True)
        .gt("expires_at", now)
        .limit(1),
        op_name="impersonation.validate_session",
    )
    rows = result.data or []
    return rows[0] if rows else None


async def deactivate_impersonation_session(session_id: str) -> None:
    """Mark session as inactive (manual exit or expiry)."""
    client = get_service_client()
    await execute_async(
        client.table("admin_impersonation_sessions")
        .update({"is_active": False})
        .eq("id", session_id),
        op_name="impersonation.deactivate_session",
    )
```

### Pattern 2: Endpoint Allow-List Middleware

**What:** A FastAPI dependency that validates `X-Impersonation-Session` header. Blocks access to any path not in the explicit allow-list.

**When to use:** Applied to user-context endpoints that should be accessible during impersonation.

```python
# app/middleware/impersonation_auth.py
from fastapi import Header, HTTPException, Request
from app.services.impersonation_service import validate_impersonation_session

# Explicit allow-list: only these path prefixes are allowed during impersonation
IMPERSONATION_ALLOWED_PATHS = frozenset({
    "/api/agents/chat",        # Main chat interface
    "/api/workflows",          # View workflow history
    "/api/approvals",          # View pending approvals
    "/api/briefing",           # View briefing content
    "/api/reports",            # Read reports
    "/admin/users",            # User detail (read)
})

async def validate_impersonation(
    request: Request,
    x_impersonation_session: str | None = Header(default=None),
) -> dict | None:
    """Returns the impersonation session if header is present and valid, else None.
    Raises 403 if the session is invalid/expired.
    Raises 403 if the path is not on the allow-list."""
    if x_impersonation_session is None:
        return None  # Not an impersonation request — pass through

    session = await validate_impersonation_session(x_impersonation_session)
    if session is None:
        raise HTTPException(
            status_code=403,
            detail="Impersonation session is invalid or has expired. Re-activate to continue.",
        )

    # Enforce allow-list
    path = request.url.path
    if not any(path.startswith(allowed) for allowed in IMPERSONATION_ALLOWED_PATHS):
        raise HTTPException(
            status_code=403,
            detail=(
                f"This action is not permitted during impersonation. "
                f"Path '{path}' is not on the impersonation allow-list."
            ),
        )

    return session
```

### Pattern 3: Audit Tagging with Impersonation Session ID

**What:** `log_admin_action` already has an `impersonation_session_id` column ready in the schema (Phase 7, `admin_audit_log.impersonation_session_id uuid`). The function signature needs the parameter wired in.

**When to use:** Any action performed during an impersonation session.

```python
# app/services/admin_audit.py  (modification — add parameter)
async def log_admin_action(
    admin_user_id: str | None,
    action: str,
    target_type: str | None,
    target_id: str | None,
    details: dict | None,
    source: str,
    impersonation_session_id: str | None = None,  # NEW in Phase 13
) -> None:
    row: dict = {
        "admin_user_id": admin_user_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "details": details,
        "source": source,
        "impersonation_session_id": impersonation_session_id,  # NEW
    }
    # ... rest unchanged
```

### Pattern 4: Notification Suppression

**What:** Before firing any notification for a target user, check for an active impersonation session and suppress if found.

**When to use:** In `email_triage_service.py`, `briefing_digest_service.py`, any scheduled notification pathway.

```python
# Suppression helper (inline in notification services)
async def _is_impersonation_active(user_id: str) -> bool:
    """Return True if a super admin has an active impersonation session for this user."""
    from app.services.supabase import get_service_client
    from app.services.supabase_async import execute_async
    from datetime import datetime, timezone

    client = get_service_client()
    now = datetime.now(timezone.utc).isoformat()
    result = await execute_async(
        client.table("admin_impersonation_sessions")
        .select("id", count="exact")
        .eq("target_user_id", user_id)
        .eq("is_active", True)
        .gt("expires_at", now)
        .limit(1),
        op_name="impersonation.check_active",
    )
    return bool(result.count and result.count > 0)
```

### Pattern 5: SKIL-03 At-Risk User Identification

**What:** A new AdminAgent tool `get_at_risk_users` that correlates: (1) session activity decline over last 14 vs. prior 14 days, (2) Stripe subscription status (via existing integration proxy), (3) `last_sign_in_at` from Supabase Auth.

**When to use:** When admin asks "which users are at risk?" or "show me user health watch list."

```python
# app/agents/admin/tools/users_intelligence.py
async def get_at_risk_users(threshold_days_inactive: int = 7) -> dict:
    """
    Identifies at-risk users by correlating:
    - Declining message/session activity (14-day window vs prior 14 days)
    - Last login date (users inactive > threshold_days_inactive)
    - Billing status where available via Stripe integration

    Autonomy tier: auto (read-only analytics query).
    Returns: {"at_risk_users": [...], "criteria": {...}}
    """
```

**Data sources available:**
- `sessions` table: `user_id`, `updated_at` — last activity timestamp per user
- `session_events` table: `user_id`, `created_at` — message count per user per window
- `auth.admin.get_user_by_id` (asyncio.to_thread) — `last_sign_in_at`
- Stripe integration proxy (via `_fetch_stripe_summary`) — subscription status

**Note on Stripe data for SKIL-03:** Phase 11 already has the Stripe proxy in `integration_proxy.py` (`_fetch_stripe_summary`). SKIL-03 can call this via `IntegrationProxyService.call()` with session budget. Billing detail per user requires Stripe customer lookup by email — if Stripe integration is not configured, degrade gracefully to "billing status unknown."

### Pattern 6: SKIL-04 Support Playbooks

**What:** Prompt-injected reasoning in ADMIN_AGENT_INSTRUCTION. A supporting tool `get_user_support_context` pulls the user's recent session data, error patterns, and usage summary.

**Playbook prompt pattern (in ADMIN_AGENT_INSTRUCTION):**

```
## Interactive Impersonation Support Playbooks (SKIL-04)

When an impersonation session is active (the admin is in interactive mode for a specific user),
proactively call get_user_support_context(user_id) to build a support picture before the
admin takes any action. Surface findings as a structured support brief:

1. Usage summary: "Last active: {N} days ago. Messages sent in last 7 days: {N} (down {X}% from prior week)."
2. Error patterns: "3 tool_timeout errors in the last 48 hours on the financial_agent."
3. Suggested troubleshooting steps based on patterns:
   - High error rate on specific agent → check agent config, suggest clearing session state
   - Zero activity + active subscription → check if onboarding completed, suggest guided walkthrough
   - Declining usage + no recent errors → check if user is aware of relevant features
4. Actions available during impersonation: list only allow-listed endpoints that are safe to invoke.

Key: never suggest actions outside the allow-list. Clearly distinguish "what I can see" from "what can be done during impersonation."
```

### Anti-Patterns to Avoid

- **Extending the 30-minute timer silently:** The ImpersonationContext sessionStorage approach already prevents this. The backend `expires_at` field is authoritative — the frontend timer is a UX aid. The admin must call `POST /admin/impersonate/{userId}/start` again to get a new session row.
- **Checking the allow-list client-side only:** All allow-list enforcement must be in the backend middleware. The frontend hide-button pattern alone is insufficient.
- **Passing JWT as target user:** Interactive impersonation does NOT exchange tokens or act as the user in Supabase Auth. All calls are made with the admin's JWT + the `X-Impersonation-Session` header. The backend scopes data to the target user by reading `target_user_id` from the validated session row.
- **Writing to `admin_audit_log` without `impersonation_session_id`:** All actions during an impersonation session must carry the session UUID. Use `source="impersonation"` + `impersonation_session_id`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session expiry enforcement | Custom clock in Python | `expires_at` timestamptz column + GT filter in validate query | Postgres handles time math atomically; avoids race conditions |
| Token signing/encryption | JWT or HMAC for session tokens | Plain UUID row in Supabase with service-role access | Supabase RLS + service role is the established trust boundary; UUID is unguessable, row is authoritative |
| Notification suppression flag | Per-service boolean env var | DB query on `admin_impersonation_sessions` before sending | Centralised truth; no env var drift; auto-clears when session expires |
| User usage data aggregation | New materialized view | Query `sessions` + `session_events` Python-side | Same pattern as analytics_aggregator.py — acceptable at admin query scale |

---

## Common Pitfalls

### Pitfall 1: Banner color state divergence
**What goes wrong:** Phase 9 built the banner amber-to-red transition at 5-minute warning. Success criterion 1 says the banner is red from the moment interactive impersonation is activated (not just at the warning threshold).
**Why it happens:** Phase 9's ImpersonationBanner was designed for read-only mode; the "red = danger" signal wasn't needed until interactive.
**How to avoid:** Add a `mode` prop to ImpersonationProvider/ImpersonationBanner: `'read_only' | 'interactive'`. Interactive mode sets `bg-red-600` from activation; read-only retains the amber-to-red warning behavior.
**Warning signs:** Banner shows amber when entering interactive mode.

### Pitfall 2: Forgetting to deactivate session on exit
**What goes wrong:** Admin clicks "Exit Impersonation" in the frontend but the DB row stays `is_active=true`. The notification suppression remains active. Worse, a subsequent open of the same session URL within the 30-minute window would reuse the expired timer.
**Why it happens:** Phase 9's `exitImpersonation()` clears sessionStorage and redirects — it never calls the backend.
**How to avoid:** `exitImpersonation()` in ImpersonationContext must call `DELETE /admin/impersonate/sessions/{sessionId}` before navigating away. Use a fire-and-forget fetch (no await needed for UX responsiveness).
**Warning signs:** Notification suppression still active after admin returns to `/admin/users`.

### Pitfall 3: `log_admin_action` signature change breaks all callers
**What goes wrong:** Adding `impersonation_session_id` to `log_admin_action` as a positional argument would break every existing caller (30+ call sites across Phase 7-12 code).
**Why it happens:** Backward compat issue on a frequently-called function.
**How to avoid:** Add `impersonation_session_id: str | None = None` as a keyword-only argument with default `None`. All existing callers remain valid. Only impersonation-aware callers pass the value.
**Warning signs:** Import or call-site errors on `log_admin_action` across all admin tools.

### Pitfall 4: Super-admin gating not enforced
**What goes wrong:** USER-04 says "super admin" only — not all admins. The current `require_admin` middleware grants access to any admin role (junior_admin, senior_admin, admin, super_admin).
**Why it happens:** No `require_super_admin` dependency exists yet; Phase 15 adds role management.
**How to avoid:** For Phase 13, add an inline super-admin check in `POST /admin/impersonate/{userId}/start` that reads the `role` from the `user_roles` table (or checks `SUPER_ADMIN_EMAILS` env var as fallback). Do NOT add a new global middleware — keep it scoped to the activation endpoint only.
**Warning signs:** A senior_admin can activate interactive impersonation mode.

### Pitfall 5: SKIL-03 blocking on unavailable Stripe
**What goes wrong:** `get_at_risk_users` calls Stripe proxy. If Stripe isn't configured (it won't be in dev), the tool errors out or returns nothing.
**Why it happens:** SKIL-03 correlates billing status, but Stripe is an optional integration.
**How to avoid:** Degrade gracefully — `billing_status: "unknown (Stripe not configured)"` when the proxy call fails. At-risk classification based on usage + login data alone is still valid.
**Warning signs:** `get_at_risk_users` returns error when Stripe key is not set.

### Pitfall 6: `impersonate_user` tool now does more than return a URL
**What goes wrong:** The existing `impersonate_user` tool in `users.py` returns `{"impersonation_url": "...", "mode": "read_only"}`. Phase 13 changes the mode to interactive — but the tool must also trigger the session creation.
**Why it happens:** Tool was a stub for Phase 9's read-only mode.
**How to avoid:** Upgrade the tool to call `create_impersonation_session()` when executed at auto-tier, return `{"impersonation_url": "...", "mode": "interactive", "session_id": "..."}`. The frontend reads `session_id` from the response and stores it.

---

## Code Examples

### Migration: admin_impersonation_sessions table

```sql
-- supabase/migrations/2026032[N]000000_interactive_impersonation.sql
CREATE TABLE IF NOT EXISTS admin_impersonation_sessions (
    id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id    uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    target_user_id   uuid        NOT NULL,  -- plain UUID, no FK (matches app_projects pattern)
    is_active        boolean     NOT NULL DEFAULT true,
    expires_at       timestamptz NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now(),
    ended_at         timestamptz
);

CREATE INDEX IF NOT EXISTS idx_admin_impersonation_sessions_target_active
    ON admin_impersonation_sessions (target_user_id, is_active, expires_at DESC);

ALTER TABLE admin_impersonation_sessions ENABLE ROW LEVEL SECURITY;

-- Seed: interactive_impersonation permission for super admin activation
INSERT INTO admin_agent_permissions (action_category, action_name, autonomy_level, risk_level, description)
VALUES
    ('users', 'activate_impersonation', 'confirm', 'medium', 'Start interactive impersonation session for a user'),
    ('users', 'get_at_risk_users',      'auto',    'low',    'Identify users at risk based on usage, login, and billing data'),
    ('users', 'get_user_support_context', 'auto',  'low',    'Get usage and error context for support during impersonation')
ON CONFLICT (action_category, action_name) DO NOTHING;
```

### Frontend: ImpersonationContext session token storage

```typescript
// ImpersonationContext.tsx — Phase 13 additions
interface TargetUser {
  id: string;
  email: string;
  persona: Persona;
  agentName: string | null;
  sessionToken: string;   // NEW: backend-issued UUID from /admin/impersonate/{id}/start
}

// In ImpersonationProvider, store the token and attach to every user-context fetch:
const sessionToken = targetUser.sessionToken;

// Pass down via context so child components can attach to fetch calls:
const impersonationState = {
  ...existingState,
  sessionToken,      // NEW
  mode: 'interactive' as const,   // NEW
};
```

### Frontend: Activate interactive impersonation

```typescript
// In /admin/impersonate/[userId]/page.tsx
async function activateInteractiveMode(userId: string, token: string) {
  const res = await fetch(`${API_URL}/admin/impersonate/${userId}/start`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to start impersonation session');
  const { session_id } = await res.json();
  return session_id;  // store in ImpersonationProvider targetUser.sessionToken
}
```

---

## State of the Art

| Old Approach (Phase 9) | Current Approach (Phase 13) | Impact |
|------------------------|----------------------------|--------|
| Read-only impersonation, no backend session record | Interactive mode with `admin_impersonation_sessions` DB row | Actions can be tracked, suppressed, and expired authoritatively |
| `impersonate_user` tool returns URL only | Tool creates session, returns `session_id` for frontend | Audit trail closure: every action links to a session UUID |
| `impersonation_session_id` column in audit log — unused | Column populated for every impersonation action | AUDT-04 complete |
| Banner amber-to-red at 5-min warning | Banner red from activation in interactive mode | Visual clarity: amber=read-only, red=interactive |
| `exitImpersonation` clears sessionStorage only | Also calls DELETE session endpoint | Notification suppression ends correctly on exit |

---

## Open Questions

1. **SKIL-03: Which billing data field defines "at-risk" billing status?**
   - What we know: Stripe integration proxy in Phase 11 returns subscription data via `_fetch_stripe_summary()`. The return shape includes subscription status fields.
   - What's unclear: The exact Stripe subscription status field names returned by `_fetch_stripe_summary`. Phase 14 (Billing Dashboard) owns the full Stripe data model.
   - Recommendation: SKIL-03 should call the Stripe proxy and check for `status in ('past_due', 'unpaid', 'canceled')` — standard Stripe subscription statuses. Degrade to "billing unknown" if proxy call fails.

2. **Are there notification pathways beyond email_triage_service that need suppression?**
   - What we know: `email_triage_service.py` and `briefing_digest_service.py` are notification-adjacent. `scheduled_endpoints.py` handles background tasks.
   - What's unclear: Whether `webhooks.py` or other services fire user-facing notifications.
   - Recommendation: Suppress at the common notification dispatch points only. A single `_is_impersonation_active(user_id)` helper is sufficient for Phase 13; comprehensive suppression can be hardened in Phase 15 during full audit.

3. **How should the allow-list be configurable vs. hardcoded?**
   - What we know: The requirements specify "explicit allow-list of permitted endpoints." The planner must decide if this is code-level or admin-configurable.
   - What's unclear: Whether the admin panel needs a UI to manage the allow-list.
   - Recommendation: Hardcode the allow-list as a Python frozenset constant in Phase 13. Admin-configurable allow-list can be a Phase 15 enhancement (it fits the autonomy tier management pattern).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pytest.ini` / `pyproject.toml` (existing) |
| Quick run command | `uv run pytest tests/unit/admin/ -x -q` |
| Full suite command | `uv run pytest tests/unit/admin/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| USER-04 | `POST /admin/impersonate/{id}/start` creates DB session row and returns session_id | unit | `uv run pytest tests/unit/admin/test_impersonation_api.py -x` | ❌ Wave 0 |
| USER-04 | Allow-list: request to blocked path returns 403 with clear message | unit | `uv run pytest tests/unit/admin/test_impersonation_middleware.py::test_blocked_path -x` | ❌ Wave 0 |
| USER-04 | Allow-list: request to permitted path passes through | unit | `uv run pytest tests/unit/admin/test_impersonation_middleware.py::test_allowed_path -x` | ❌ Wave 0 |
| USER-04 | Expired session (expires_at in past) returns 403 | unit | `uv run pytest tests/unit/admin/test_impersonation_service.py::test_expired_session -x` | ❌ Wave 0 |
| USER-04 | Notification suppressed when active session exists for target user | unit | `uv run pytest tests/unit/admin/test_impersonation_service.py::test_notification_suppression -x` | ❌ Wave 0 |
| USER-04 | `DELETE /admin/impersonate/sessions/{id}` sets is_active=False | unit | `uv run pytest tests/unit/admin/test_impersonation_api.py::test_deactivate_session -x` | ❌ Wave 0 |
| AUDT-04 | `log_admin_action` with impersonation_session_id populates column | unit | `uv run pytest tests/unit/admin/test_audit.py::test_impersonation_session_id_written -x` | ❌ Wave 0 (extend existing test_audit.py) |
| AUDT-04 | Audit log row for impersonation action has session UUID, not null | unit | `uv run pytest tests/unit/admin/test_impersonation_api.py::test_audit_tagged -x` | ❌ Wave 0 |
| SKIL-03 | `get_at_risk_users` returns watch list with declining usage + inactive login | unit | `uv run pytest tests/unit/admin/test_user_intelligence_tools.py::test_get_at_risk_users -x` | ❌ Wave 0 |
| SKIL-03 | `get_at_risk_users` degrades gracefully when Stripe not configured | unit | `uv run pytest tests/unit/admin/test_user_intelligence_tools.py::test_at_risk_no_stripe -x` | ❌ Wave 0 |
| SKIL-04 | `get_user_support_context` returns recent session, error, and usage data | unit | `uv run pytest tests/unit/admin/test_user_intelligence_tools.py::test_get_support_context -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/admin/ -x -q`
- **Per wave merge:** `uv run pytest tests/unit/admin/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/admin/test_impersonation_api.py` — covers USER-04 API endpoints
- [ ] `tests/unit/admin/test_impersonation_middleware.py` — covers allow-list enforcement
- [ ] `tests/unit/admin/test_impersonation_service.py` — covers session create/validate/expire/suppress
- [ ] `tests/unit/admin/test_user_intelligence_tools.py` — covers SKIL-03 and SKIL-04 tools
- [ ] `tests/unit/admin/test_audit.py` — extend existing file to cover `impersonation_session_id` parameter

---

## Sources

### Primary (HIGH confidence)
- Codebase: `app/services/admin_audit.py` — confirmed `impersonation_session_id` column was schema-ready since Phase 7; `log_admin_action()` signature confirmed
- Codebase: `supabase/migrations/20260321300000_admin_panel_foundation.sql` — confirmed `admin_audit_log.impersonation_session_id uuid` column exists, nullable
- Codebase: `app/agents/admin/tools/users.py` — confirmed existing `impersonate_user` tool returns URL-only, needs upgrade
- Codebase: `frontend/src/contexts/ImpersonationContext.tsx` — confirmed sessionStorage timer pattern and `exitImpersonation()` does NOT call backend
- Codebase: `frontend/src/components/admin/ImpersonationBanner.tsx` — confirmed amber/red color logic; needs `mode` prop
- Codebase: `app/services/analytics_aggregator.py` — confirmed `sessions`, `session_events`, `workflow_executions` tables available for SKIL-03 usage correlation
- Codebase: `app/routers/admin/integrations.py` — confirmed Stripe proxy `_fetch_stripe_summary` exists for SKIL-03 billing correlation
- Codebase: `app/agents/admin/agent.py` — confirmed SKIL-01/SKIL-02 are prompt-injected patterns; SKIL-03/SKIL-04 should follow the same approach

### Secondary (MEDIUM confidence)
- Codebase: `app/middleware/admin_auth.py` — `require_admin` pattern used to model `require_super_admin` check for activation endpoint
- Codebase: Phase 9 CONTEXT.md — confirmed `X-Impersonate-User-Id` header was planned but not fully implemented; Phase 13 supersedes with `X-Impersonation-Session`

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are existing project dependencies; no new dependencies needed
- Architecture: HIGH — patterns directly derived from Phase 7-12 code inspection; no external sources required
- Pitfalls: HIGH — all identified by reading the Phase 9 implementation and cross-referencing what Phase 13 requirements change
- SKIL-03/SKIL-04: MEDIUM — data sources confirmed; exact Stripe field names for billing status are LOW until Phase 14 confirms the Stripe data model

**Research date:** 2026-03-23
**Valid until:** 2026-06-23 (stable patterns, internal codebase only — no external library dependencies added)
