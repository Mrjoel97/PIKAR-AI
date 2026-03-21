# Phase 7: Foundation - Research

**Researched:** 2026-03-21
**Domain:** Admin panel trust infrastructure — FastAPI auth dependency, Google ADK AdminAgent, Redis confirmation tokens, Fernet encryption, Supabase migrations, Next.js admin layout
**Confidence:** HIGH — all findings derived directly from the existing codebase; no external speculation needed

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Authorization**
- Two-layer auth: `ADMIN_EMAILS` env var (server-side only, NOT `NEXT_PUBLIC_`) OR `user_roles` DB table
- OR logic: either check grants access
- Backend: `require_admin` FastAPI dependency on all `/admin/*` routes — validates Supabase JWT, checks email against env allowlist OR queries `is_admin()` DB function
- Frontend: `AdminGuard` component in `/admin/layout.tsx` — calls server-side endpoint `GET /admin/check-access` (NOT client-side env var check)
- Non-admin redirect: server-side redirect to `/dashboard` with "Access denied" toast

**Database Schema**
- `user_roles`, `is_admin()` SECURITY DEFINER, `admin_agent_permissions`, `admin_chat_sessions`, `admin_chat_messages`, `admin_audit_log`, `admin_config_history`, `admin_integrations`, `api_health_checks`, `api_incidents` — all specified
- RLS enabled on all admin tables with no policies (deny via anon — all access through service role)
- Seed `admin_agent_permissions` with defaults: reads=auto, writes=confirm, destructive=blocked

**AI Admin Assistant**
- `AdminAgent` at `app/agents/admin/agent.py` — factory pattern matching `create_financial_agent()`
- Uses `get_model()` and `get_fallback_model()` from `app/agents/shared.py`
- System prompt includes platform context, current autonomy permissions, available tools with risk levels
- Phase 7 tools only: `check_system_health` (hits existing /health/* endpoints)
- SSE endpoint: `POST /admin/chat` on FastAPI
- Frontend: `useAdminChat` hook built on `@microsoft/fetch-event-source` — mirrors `useAgentChat`

**Autonomy Enforcement**
- Enforced in Python tool code, NOT in LLM system prompt
- Each tool checks `admin_agent_permissions` table before executing
- Confirmation tokens: UUID-based, stored in Redis with TTL, atomic single-consumption via `GETDEL` or `DELETE` with check

**Confirm Flow Frontend**
- Confirm-tier response renders action confirmation card
- Confirm sends `confirmation_token` back to agent endpoint
- Double-click protection: disable Confirm button on first click + server-side single-use check

**Fernet Encryption**
- `app/services/encryption.py` — MultiFernet from day one
- `ADMIN_ENCRYPTION_KEY` env var (comma-separated for rotation support)
- Phase 7 creates the utility; Phase 11 (Integrations) uses it

**Audit Trail**
- `app/services/admin_audit.py` — `log_admin_action()`
- Source tags: 'manual', 'ai_agent', 'impersonation', 'monitoring_loop'
- `admin_user_id` can be NULL for monitoring_loop

**Frontend Layout**
- Route group: `src/app/(admin)/` with `layout.tsx`
- AdminGuard + admin sidebar + persistent AI chat panel (docked bottom, collapsible)
- Sidebar nav: Overview, Users, Monitor, Analytics, Approvals, Config, Billing, Integrations, Settings
- Uses existing design system: Tailwind CSS 4, Lucide icons, Framer Motion, Sonner toasts, dark theme

**Backend Structure**
- `app/routers/admin/` — router package
- `app/routers/admin/__init__.py`, `auth.py`, `chat.py`, `audit.py`
- `app/middleware/admin_auth.py` — `require_admin` dependency
- `app/agents/admin/agent.py` — AdminAgent
- `app/agents/admin/tools/` — tool modules
- `app/services/encryption.py`, `app/services/admin_audit.py`

**Rate Limiting**
- `POST /admin/chat`: 30 requests/minute
- `GET /admin/*`: 120 requests/minute
- Using existing `slowapi` pattern

### Claude's Discretion
- Exact ADK tool definition patterns for the confirm/auto/blocked flow
- Redis key structure for confirmation tokens
- Admin sidebar component implementation details
- Chat panel expand/collapse animation approach
- Audit log pagination and filter implementation
- Error handling patterns for SSE reconnection in admin chat

### Deferred Ideas (OUT OF SCOPE)
- Domain-specific agent tools (users, monitoring, analytics, integrations, config, billing, approvals) — Phases 8-15
- External integration proxy and Fernet-encrypted key storage — Phase 11
- User impersonation — Phase 9/13
- Feature flag UI — Phase 12
- Approval oversight — Phase 15
- Billing dashboard — Phase 14
- Permissions configuration UI — Phase 15
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-01 | Admin can access admin panel when their email is in ADMIN_EMAILS env var | `require_admin` dependency reads `ADMIN_EMAILS` env, `verify_token` pattern confirmed in `app/app_utils/auth.py` |
| AUTH-02 | Admin can access admin panel when they have admin role in user_roles table | `is_admin()` SECURITY DEFINER function queries `user_roles`; service client bypasses RLS |
| AUTH-03 | System grants access via OR logic (either env allowlist or DB role) | `require_admin` checks env first, falls back to DB — either path returns admin user dict |
| AUTH-04 | Admin email check runs server-side only, never exposed in client bundle | `require_admin` is a FastAPI Depends; `AdminGuard` calls `GET /admin/check-access` server-side; no NEXT_PUBLIC_ |
| AUTH-05 | Non-admin users are redirected away from admin routes (server-side AdminGuard) | Next.js server component reads response from `/admin/check-access`; returns redirect on 403 |
| ASST-01 | Admin can chat with AI Admin Assistant via persistent SSE chat panel | `useAdminChat` mirrors `useAgentChat`; `POST /admin/chat` streams via `StreamingResponse` + ADK Runner |
| ASST-02 | AdminAgent has 30+ tools (users, monitoring, integrations, analytics, config, billing, approvals) | Phase 7 scopes only `check_system_health`; tool registration pattern confirmed in `create_financial_agent()` |
| ASST-03 | Each tool action has a Python-enforced autonomy tier (auto/confirm/blocked) | Tool function reads `admin_agent_permissions` table, returns `{requires_confirmation: True, ...}` on confirm tier |
| ASST-04 | Confirm-tier actions show a confirmation card with action details and Confirm/Reject buttons | Frontend detects `requires_confirmation` in SSE stream, renders `ConfirmationCard` component |
| ASST-05 | Confirmation tokens are UUID-based with atomic single-consumption | Redis `SET token uuid EX 300 NX` + `GETDEL` for atomic consume; or UPDATE WHERE consumed=false with rowcount check |
| ASST-06 | Admin chat sessions persist across page refreshes (admin_chat_sessions table) | `useAdminChat` loads history from `admin_chat_messages` on mount; session ID stored in `admin_chat_sessions` |
| AUDT-01 | All admin actions logged to admin_audit_log with source tags | `log_admin_action()` called at every tool execution boundary and manual action handler |
| AUDT-02 | API keys encrypted with MultiFernet (supports key rotation from day one) | `app/services/encryption.py` wraps `MultiFernet([Fernet(k) for k in keys])`; `cryptography>=46.0.3` already installed |
| AUDT-03 | Admin can browse and filter audit trail entries in UI | `GET /admin/audit-log` with query params; `admin_audit_log` table queried via service client |
| AUDT-04 | Impersonation actions tagged with impersonation_session_id in audit log | `admin_audit_log.details` JSONB stores `impersonation_session_id`; out of scope Phase 7 but schema accommodates it |
</phase_requirements>

---

## Summary

Phase 7 lays the trust infrastructure that all subsequent admin phases depend on. The research confirms that every required capability maps cleanly to existing codebase patterns — no novel technology decisions are needed. The existing `verify_token` function in `app/app_utils/auth.py` is the direct base for `require_admin`; the `create_financial_agent()` factory in `app/agents/financial/agent.py` is the exact template for `AdminAgent`; the `useAgentChat` hook in `frontend/src/hooks/useAgentChat.ts` is the direct template for `useAdminChat`; the `Sidebar` component in `frontend/src/components/layout/Sidebar.tsx` is the template for the admin sidebar; and the `CacheService` in `app/services/cache.py` provides the Redis primitive (`redis.asyncio`) needed for confirmation tokens.

The most architecturally critical decision — enforcing autonomy tiers in Python tool code rather than LLM system prompt — is already locked by the user. This means every tool function must contain an explicit DB lookup before executing. The implementation pattern for this is straightforward: query `admin_agent_permissions` for the `(action_category, action_name)` pair, branch on `autonomy_level`, and either execute, return a confirmation-pending dict, or return a blocked explanation. The LLM never sees the enforcement logic.

The next most critical decision — atomic confirmation token consumption — is implementable with the existing `redis.asyncio` client. The correct pattern is `SET key uuid EX 300 NX` on generation and `GETDEL key` on consumption (Redis 6.2+); the `CacheService` singleton provides the connection. The migration file for admin tables should be named with the `20260321` timestamp prefix pattern (the latest migrations use `20260321XXXXXX_` format) and should include all 9 admin tables plus the `is_admin()` SECURITY DEFINER function.

**Primary recommendation:** Build `require_admin` and the Supabase migration first (Wave 0), then `AdminAgent` with the health tool (Wave 1), then `useAdminChat` + the admin layout (Wave 2), then Fernet encryption + audit log (Wave 3). Every subsequent phase plugs into these four foundations.

---

## Standard Stack

### Core (no new packages needed for Phase 7)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| `cryptography` (Fernet) | `>=46.0.3` | MultiFernet encrypt/decrypt for `app/services/encryption.py` | Already in pyproject.toml |
| `redis.asyncio` | `>=5.0.0,<6.0.0` | Confirmation token storage (`SET`, `GETDEL`) | Already in pyproject.toml (`redis>=5.0.0,<6.0.0`) |
| `slowapi` | `>=0.1.9` | Rate limiting on `/admin/*` routes (30/min chat, 120/min reads) | Already in pyproject.toml |
| `PyJWT` | `>=2.8.0` | JWT decoding in `require_admin` | Already in pyproject.toml |
| `google-adk` | installed | `Agent`, `Runner`, `InMemorySessionService` for AdminAgent | Already installed (used by all 10 agents) |
| `@microsoft/fetch-event-source` | `^2.0.1` | SSE streaming in `useAdminChat` | Already in frontend/package.json |

**Phase 7 requires zero new package installs.** All dependencies are already present.

### What NOT to Add (Phase 7)

| Avoid | Why |
|-------|-----|
| `httpx` (Phase 7) | Not needed until Phase 8 health monitoring loop; `check_system_health` tool can use internal function calls |
| Any new frontend chart library | Charts are deferred to Phase 8+ |
| `@tanstack/react-table` | Tables are deferred to Phase 8+ |

---

## Architecture Patterns

### Recommended Project Structure (Phase 7 additions only)

```
app/
├── middleware/
│   └── admin_auth.py          # require_admin FastAPI dependency (NEW)
├── routers/
│   └── admin/                 # NEW router package
│       ├── __init__.py        # router registration, prefix="/admin"
│       ├── auth.py            # GET /admin/check-access
│       ├── chat.py            # POST /admin/chat (SSE)
│       └── audit.py           # GET /admin/audit-log
├── agents/
│   └── admin/                 # NEW agent package
│       ├── __init__.py
│       ├── agent.py           # AdminAgent + create_admin_agent()
│       └── tools/
│           ├── __init__.py
│           └── health.py      # check_system_health tool (Phase 7 only)
└── services/
    ├── encryption.py          # NEW: MultiFernet wrap/unwrap
    └── admin_audit.py         # NEW: log_admin_action()

frontend/src/
├── app/
│   └── (admin)/               # NEW route group (parallel to (personas)/)
│       ├── layout.tsx         # AdminGuard + sidebar + chat panel
│       ├── page.tsx           # /admin overview redirect
│       └── audit-log/
│           └── page.tsx       # Audit log viewer
└── hooks/
    └── useAdminChat.ts        # NEW: mirrors useAgentChat.ts

supabase/migrations/
└── 20260321300000_admin_panel_foundation.sql   # NEW: all 9 admin tables + is_admin()
```

### Pattern 1: require_admin FastAPI Dependency

**What:** A FastAPI `Depends` that validates the Supabase JWT and then checks ADMIN_EMAILS env OR `is_admin()` DB function. Returns a user dict on success; raises HTTP 403 on failure.

**When to use:** Inject as `Depends` on every endpoint in `app/routers/admin/`.

```python
# app/middleware/admin_auth.py
import logging
import os

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.app_utils.auth import verify_token
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """FastAPI dependency: validates JWT and checks admin access.

    Checks ADMIN_EMAILS env var first (fast path), then falls back to
    is_admin() DB function. Logs which path granted access for audit coverage.

    Returns:
        User dict with id, email, admin_source ('env_allowlist' | 'db_role')

    Raises:
        HTTPException 403 if not admin
    """
    user = await verify_token(credentials)
    email = user.get("email", "")

    # Path 1: env allowlist (bootstrap path — always active while set)
    admin_emails_raw = os.environ.get("ADMIN_EMAILS", "")
    admin_emails = [e.strip().lower() for e in admin_emails_raw.split(",") if e.strip()]
    if email.lower() in admin_emails:
        logger.info("Admin access granted via env_allowlist for %s", email)
        return {**user, "admin_source": "env_allowlist"}

    # Path 2: user_roles table
    try:
        client = get_service_client()
        result = client.rpc("is_admin", {"user_id_param": user["id"]}).execute()
        if result.data is True:
            logger.info("Admin access granted via db_role for %s", email)
            return {**user, "admin_source": "db_role"}
    except Exception as exc:
        logger.error("is_admin() DB check failed: %s", exc)
        raise HTTPException(status_code=503, detail="Admin access check unavailable")

    logger.warning("Admin access denied for %s", email)
    raise HTTPException(status_code=403, detail="Admin access required")
```

**Key notes from reading `app/app_utils/auth.py`:**
- `verify_token` takes `HTTPAuthorizationCredentials` from `Security(security)` but also works with `Depends(security)` — use `Depends` so it composes cleanly
- `verify_token` calls `supabase.auth.get_user(token)` which validates against Supabase (not just local JWT decode) — this is the correct pattern for admin routes
- The `admin_source` field in the returned dict is critical for audit logging; every admin action should record which path granted access

### Pattern 2: AdminAgent Factory (mirrors create_financial_agent)

**What:** ADK `Agent` with Python async tool functions. The agent itself is a singleton plus a factory function for future workflow use. Tools register as plain async functions; ADK auto-wraps them.

**When to use:** All tool functions live in `app/agents/admin/tools/`. The agent module exports `admin_agent` (singleton) and `create_admin_agent()`.

```python
# app/agents/admin/agent.py
from app.agents.base_agent import PikarAgent as Agent
from app.agents.shared import FAST_AGENT_CONFIG, get_model, get_fallback_model
from app.agents.admin.tools.health import check_system_health

ADMIN_AGENT_INSTRUCTION = """You are the AdminAgent for Pikar-AI platform management.

You have access to tools that can read and modify platform state. Each tool enforces
its own autonomy tier:
- AUTO: executes immediately
- CONFIRM: returns a confirmation request you must surface to the admin
- BLOCKED: cannot be executed; explain why

When a tool returns requires_confirmation=true, respond with the confirmation details
and wait for the admin to confirm before proceeding. Never attempt to bypass
confirmation by calling the tool again without a confirmation_token.

Current platform: Pikar-AI multi-agent executive system
Available tools in Phase 7: check_system_health
"""

admin_agent = Agent(
    name="AdminAgent",
    model=get_model(),
    description="AI admin assistant for platform management — reads health, executes confirmed actions",
    instruction=ADMIN_AGENT_INSTRUCTION,
    tools=[check_system_health],
    generate_content_config=FAST_AGENT_CONFIG,
)


def create_admin_agent(name_suffix: str = "") -> Agent:
    """Create a fresh AdminAgent instance for workflow use."""
    agent_name = f"AdminAgent{name_suffix}" if name_suffix else "AdminAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="AI admin assistant for platform management",
        instruction=ADMIN_AGENT_INSTRUCTION,
        tools=[check_system_health],
        generate_content_config=FAST_AGENT_CONFIG,
    )
```

### Pattern 3: Autonomy-Enforced Tool Function

**What:** Every tool function checks the `admin_agent_permissions` table at its Python boundary before executing. The LLM never sees the enforcement logic.

**When to use:** Every tool in `app/agents/admin/tools/`.

```python
# app/agents/admin/tools/health.py
import logging
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)


async def check_system_health() -> dict:
    """Check the health status of all platform services.

    Returns a summary of /health/live, /health/connections, /health/cache,
    and /health/embeddings endpoints.

    Returns:
        Dict with overall_status ('healthy'|'degraded'|'unhealthy'),
        services dict, and summary string.
    """
    # Autonomy check: reads are 'auto' tier — no confirmation needed
    # Still check the DB to ensure the permission hasn't been overridden
    try:
        client = get_service_client()
        res = (
            client.table("admin_agent_permissions")
            .select("autonomy_level")
            .eq("action_name", "check_system_health")
            .limit(1)
            .execute()
        )
        if res.data:
            level = res.data[0].get("autonomy_level", "auto")
            if level == "blocked":
                return {"error": "check_system_health is blocked by admin configuration"}
            if level == "confirm":
                import uuid
                token = str(uuid.uuid4())
                # Store in Redis with TTL (handled by caller in Phase 7)
                return {
                    "requires_confirmation": True,
                    "confirmation_token": token,
                    "action_details": {
                        "action": "check_system_health",
                        "risk_level": "low",
                        "description": "Read system health status",
                    },
                }
    except Exception as exc:
        logger.warning("Could not verify autonomy level, defaulting to auto: %s", exc)

    # Execute: call existing health endpoints internally
    # In Phase 7, import the health check function directly rather than HTTP call
    from app.fast_api_app import get_liveness
    results = {}
    try:
        results["live"] = await get_liveness()
    except Exception as exc:
        results["live"] = {"status": "error", "error": str(exc)}

    overall = "healthy" if all(
        r.get("status") in ("alive", "healthy") for r in results.values()
    ) else "degraded"

    return {"overall_status": overall, "services": results}
```

**CRITICAL NOTE:** The DB permission check must happen before ANY side effect. For Phase 7's `check_system_health` this is a read, but the pattern must be in place from the start.

### Pattern 4: Confirmation Token (Redis atomic)

**What:** UUID token stored in Redis with TTL. Consumed atomically via `GETDEL` (Redis 6.2+). The `CacheService` provides the `redis.asyncio` client.

**Redis key structure:** `admin:confirm:{token_uuid}` → JSON blob `{"action": ..., "admin_user_id": ..., "expires_at": ...}`

```python
# app/routers/admin/chat.py  (confirmation consumption)
import json
import uuid as uuid_lib

from app.services.cache import get_cache_service


async def store_confirmation_token(token: str, action_details: dict, admin_user_id: str) -> bool:
    """Store confirmation token in Redis with 5-minute TTL."""
    cache = get_cache_service()
    redis_client = await cache._get_redis()
    if redis_client is None:
        return False  # Degrade gracefully — confirmation not available without Redis
    payload = json.dumps({"action_details": action_details, "admin_user_id": admin_user_id})
    key = f"admin:confirm:{token}"
    await redis_client.set(key, payload, ex=300)  # 5-minute TTL
    return True


async def consume_confirmation_token(token: str) -> dict | None:
    """Consume confirmation token atomically. Returns None if already consumed or expired."""
    cache = get_cache_service()
    redis_client = await cache._get_redis()
    if redis_client is None:
        return None
    key = f"admin:confirm:{token}"
    raw = await redis_client.getdel(key)  # Atomic: get + delete in one operation
    if raw is None:
        return None  # Already consumed or expired
    return json.loads(raw)
```

**Note on `_get_redis()`:** `CacheService` exposes `self._redis` (the `redis.asyncio.Redis` instance). Access it directly or add a thin `get_redis_client()` accessor. Do NOT use the `@with_circuit_breaker` wrapped methods (which return `CacheResult`) for confirmation tokens — use the raw client for `GETDEL` semantics.

### Pattern 5: SSE Admin Chat Endpoint

**What:** `POST /admin/chat` streams ADK `Runner` output as SSE, mirroring the existing A2A `/run_sse` pattern but simpler (no A2A protocol envelope). The admin chat is a direct runner invocation.

**When to use:** `app/routers/admin/chat.py`

```python
# app/routers/admin/chat.py  (skeleton)
import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.middleware.admin_auth import require_admin
from app.middleware.rate_limiter import limiter
from app.agents.admin.agent import admin_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)


@router.post("/chat")
@limiter.limit("30/minute")
async def admin_chat(
    request: Request,
    admin_user: dict = Depends(require_admin),
):
    """SSE streaming chat endpoint for the AdminAgent.

    Accepts: {session_id, message, confirmation_token?}
    Streams: text/event-stream with agent output chunks
    """
    body = await request.json()
    message = body.get("message", "")
    session_id = body.get("session_id") or f"admin-{admin_user['id']}-{...}"
    confirmation_token = body.get("confirmation_token")

    async def event_generator():
        # If confirmation_token provided, verify and inject into context
        # Run ADK runner, yield SSE chunks
        ...

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### Pattern 6: useAdminChat Hook

**What:** Direct port of `useAgentChat.ts` with three key differences:
1. Endpoint is `${API_URL}/admin/chat` not `/a2a/app/run_sse`
2. History loads from `admin_chat_messages` Supabase table (not `session_events`)
3. Detects `requires_confirmation: true` in streamed data and sets `pendingConfirmation` state

**When to use:** `frontend/src/hooks/useAdminChat.ts`

**Key differences from useAgentChat (from direct code inspection):**
- `useAgentChat` calls `supabase.from('session_events').select(...)` for history — `useAdminChat` calls `supabase.from('admin_chat_messages').select(...)` ordered by `created_at`
- `useAgentChat` dispatches `widgetDisplay` events — not needed for admin chat (no widgets)
- `useAgentChat` uses `agentMode: AgentMode` param — admin chat does not use `auto/collab/ask` modes
- Add `pendingConfirmation` state: `{ token: string, action_details: {...} } | null`
- Add `confirmAction(token)` and `rejectAction()` methods

### Pattern 7: Admin Layout + AdminGuard

**What:** `src/app/(admin)/layout.tsx` is a Next.js server component that calls `GET /admin/check-access` and redirects non-admins before rendering children.

**Why server component (not client):** Prevents the admin UI from flashing before the redirect. The personas layout (`(personas)/layout.tsx`) is also a server component (just wraps in `<section>`). The dashboard layout wraps with `NotificationProvider` — similarly minimal. The admin layout follows the same pattern but adds the redirect logic.

```tsx
// src/app/(admin)/layout.tsx  — server component
import { redirect } from 'next/navigation';
import { cookies } from 'next/headers';

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Server-side access check — never leaks ADMIN_EMAILS to client
  const cookieStore = cookies();
  const token = cookieStore.get('sb-access-token')?.value;

  // Call backend check-access; redirect on failure
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  try {
    const res = await fetch(`${apiUrl}/admin/check-access`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      redirect('/dashboard');
    }
  } catch {
    redirect('/dashboard');
  }

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      <AdminSidebar />
      <main className="flex-1 overflow-y-auto">{children}</main>
      <AdminChatPanel />
    </div>
  );
}
```

**Note on token retrieval:** Supabase stores the session in `localStorage` client-side, but the server component needs the token. The correct approach is to use Supabase's SSR cookie helpers (`@supabase/ssr`) which store the session in cookies. The existing app uses `createClient` from `@/lib/supabase/client` (client-side) — check whether `@supabase/ssr` is already installed for server component auth.

### Pattern 8: Supabase Migration Naming

**What:** Latest migrations use ISO timestamp prefix `YYYYMMDDHHMMSS_description.sql`. The next admin migration follows this pattern.

**Migration filename:** `20260321300000_admin_panel_foundation.sql`

**Migration structure:**
1. Create `user_roles` table with `role` CHECK constraint
2. Create `is_admin()` SECURITY DEFINER function (avoids circular RLS self-reference)
3. Create `admin_agent_permissions` table
4. Create `admin_chat_sessions` and `admin_chat_messages` tables
5. Create `admin_audit_log` table (NULL-safe `admin_user_id` for `monitoring_loop` source)
6. Create `admin_config_history` table (free at migration time, used in Phase 12)
7. Create `admin_integrations` table (used in Phase 11)
8. Create `api_health_checks` and `api_incidents` tables (used in Phase 8)
9. Enable RLS on all 9 tables (no policies — service role access only)
10. Seed `admin_agent_permissions` defaults

```sql
-- is_admin() function (SECURITY DEFINER to avoid circular RLS)
CREATE OR REPLACE FUNCTION is_admin(user_id_param uuid)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM user_roles
    WHERE user_id = user_id_param
    AND role IN ('admin', 'super_admin', 'senior_admin', 'junior_admin')
  );
END;
$$;
```

### Pattern 9: Fernet MultiFernet Service

**What:** Thin wrapper around `cryptography.fernet.MultiFernet`. Reads `ADMIN_ENCRYPTION_KEY` as comma-separated list; primary key is first. Never returns plaintext to frontend.

```python
# app/services/encryption.py
import os
from cryptography.fernet import Fernet, MultiFernet


def _get_fernet() -> MultiFernet:
    """Build MultiFernet from ADMIN_ENCRYPTION_KEY env var (comma-separated)."""
    raw = os.environ.get("ADMIN_ENCRYPTION_KEY", "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        raise RuntimeError("ADMIN_ENCRYPTION_KEY is not configured")
    return MultiFernet([Fernet(k.encode() if isinstance(k, str) else k) for k in keys])


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret string for storage. Returns base64-encoded ciphertext."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a stored secret. Raises InvalidToken if key mismatch."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()
```

### Anti-Patterns to Avoid

- **Enforcing autonomy in LLM system prompt:** The system prompt may describe tiers for context, but the actual check must be in Python tool code. An instruction like "always ask for confirmation before suspending users" is bypassed by prompt injection.
- **Using `Fernet(single_key)` instead of `MultiFernet([keys])`:** Blocks key rotation without data loss. Always use `MultiFernet` from day one even with one key.
- **Storing `admin_chat_messages` as a JSONB blob per session:** The spec requires individual rows. Blob storage prevents pagination, search, and row-level operations.
- **Calling `verify_token` from the Depends chain twice:** `require_admin` should call `verify_token` once and reuse the result. Do not chain `Depends(verify_token)` separately.
- **Using `UPDATE WHERE consumed = false` for token consumption:** Race condition between two concurrent requests. Use `GETDEL` (Redis 6.2+) or `SET NX` + `DEL` with WATCH for true atomicity.
- **Fetching the Supabase auth token from cookies without `@supabase/ssr`:** The standard Supabase client stores session in `localStorage`, not accessible in server components. Check whether `@supabase/ssr` is installed before building `AdminLayout`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT verification in require_admin | Custom JWT decode logic | `verify_token()` from `app/app_utils/auth.py` | Already handles Supabase token validation + optional secret verification + strict mode |
| Rate limiting admin endpoints | Custom request counter | `@limiter.limit("30/minute")` from existing `slowapi` setup | `limiter` is already on `app.state`; just decorate |
| Redis connection management | New `redis.asyncio.Redis` instance | `get_cache_service()._redis` | `CacheService` singleton handles connection pooling, circuit breaker, and TLS |
| SSE streaming boilerplate | Custom `asyncio.Queue` + generator | ADK `Runner.run_async()` + `StreamingResponse` | Existing pattern in `fast_api_app.py`; AdminAgent runs identically to ExecutiveAgent |
| Token UUID generation | `secrets.token_hex()` custom format | `str(uuid.uuid4())` | UUID4 is the spec; uuid is already imported everywhere in the codebase |
| Supabase service client | New client initialization | `get_service_client()` from `app/services/supabase` | Singleton with connection pooling; bypasses RLS; used by all 26 existing routers |

---

## Common Pitfalls

### Pitfall 1: AdminGuard token is unavailable in server component

**What goes wrong:** `layout.tsx` tries to read the Supabase token from `localStorage` or `cookies()`, but the standard `createClient` (used everywhere in the existing app) stores sessions only in `localStorage`. Server components cannot read `localStorage`. The `AdminGuard` silently redirects everyone to `/dashboard`.

**Why it happens:** The existing app is client-side auth. `useAgentChat` calls `supabase.auth.getSession()` in a client hook, which works. A server component does not have access to the browser storage.

**How to avoid:**
- Check whether `@supabase/ssr` is installed: `grep -r "@supabase/ssr" frontend/package.json`
- If installed, use `createServerClient` from `@supabase/ssr` with `cookies()` — it reads the session from cookies set by the Supabase auth flow
- If not installed, the `AdminGuard` must be a client component that runs the check in a `useEffect` — acceptable but less secure (page renders briefly before redirect)
- Alternative: make `AdminLayout` a client component that calls `GET /admin/check-access` in `useEffect` and shows a loading state while checking

**Warning signs:** All admin routes redirect to `/dashboard` even for valid admins; `session` is null in server component.

### Pitfall 2: ADK Runner for AdminAgent needs its own session service

**What goes wrong:** The existing `runner` in `fast_api_app.py` is bound to `adk_app` (the ExecutiveAgent app). Creating a separate Runner for AdminAgent using the same `session_service` causes session namespace collisions between user chat sessions and admin sessions.

**Why it happens:** `Runner` takes an `app` parameter that determines the agent namespace. If `AdminAgent` sessions are stored under the same Supabase `session_events` table with `app_name='agents'`, they pollute the user-facing session history.

**How to avoid:**
- Create a dedicated `admin_runner = Runner(app=admin_adk_app, session_service=InMemorySessionService())` in `app/routers/admin/chat.py`
- Use `InMemorySessionService` for admin sessions in Phase 7 (history is loaded from `admin_chat_messages` table directly, not from ADK session store)
- Admin chat history persistence goes to `admin_chat_messages` via `log_admin_action()` / direct insert, not via ADK's session persistence

**Warning signs:** User chat history shows admin interactions; admin sessions appear in the user-facing session list.

### Pitfall 3: `require_admin` blocks the SSE stream before it starts

**What goes wrong:** `POST /admin/chat` is decorated with `require_admin` as a `Depends`. FastAPI resolves all dependencies synchronously before calling the endpoint. If `is_admin()` DB query is slow (>500ms), the SSE connection appears to hang before any bytes are sent — `fetchEventSource` may timeout or the user sees a blank panel.

**Why it happens:** `require_admin` calls `supabase.auth.get_user(token)` (network call) + `is_admin()` RPC (DB call). In production with cold connections, this can take 200-800ms before any streaming begins.

**How to avoid:**
- Cache the admin check result in Redis for a short TTL (e.g. 30 seconds) keyed by `admin:auth:{user_id}` — eliminates the DB call on subsequent requests
- On the frontend, send an immediate "typing indicator" via a pre-flight `GET /admin/check-access` call (which is already needed for `AdminGuard`), so the user knows the session is alive before the chat request fires

**Warning signs:** Admin chat panel shows no response for >1 second on first message; `fetchEventSource` fires `onerror` before receiving any bytes.

### Pitfall 4: Redis unavailable blocks confirmation token flow

**What goes wrong:** `store_confirmation_token()` fails silently if Redis is down (circuit breaker is open). The tool returns `requires_confirmation: True` but the token is never stored. When the admin clicks Confirm, `consume_confirmation_token()` returns `None` and the action is blocked forever. The admin cannot confirm any action.

**Why it happens:** `CacheService` circuit breaker opens after 5 failures (configurable via `REDIS_CB_FAILURE_THRESHOLD`). The `@with_circuit_breaker` wrapped methods return `False` / `CacheResult.from_error()` instead of raising.

**How to avoid:**
- Check return value of `store_confirmation_token()` — if False, return an error to the agent instead of returning a confirmation-pending dict
- The agent should respond: "Cannot create confirmation token: cache unavailable. Try again in a moment."
- Never silently drop the token storage failure; it creates phantom pending confirmations

**Warning signs:** Admin sees "Confirm" button but clicking it returns "token not found or expired"; Redis health endpoint shows circuit breaker open.

### Pitfall 5: `admin_chat_messages` session history load collides with active stream

**What goes wrong:** `useAdminChat` loads history on mount from `admin_chat_messages`. If the user refreshes mid-stream, the partial message from the previous stream is stored as an incomplete row. On next load, the partial message appears in history.

**Why it happens:** `admin_chat_messages` stores individual rows on insert. If the stream is interrupted before the agent finishes, the partial content is already written.

**How to avoid:**
- Only write the agent message row to `admin_chat_messages` when the stream completes (in the `finally` block after SSE generator exhausts)
- Write user message row immediately; write agent message row on stream close
- Add a `is_complete: boolean` column to `admin_chat_messages` for future use

**Warning signs:** Refreshing during a long agent response shows truncated previous messages in chat history.

### Pitfall 6: Accessing `CacheService._redis` directly may be None

**What goes wrong:** `get_cache_service()._redis` is `None` if the connection pool has not been initialized or if the circuit breaker is open. Calling `await redis_client.getdel(key)` raises `AttributeError: 'NoneType' object has no attribute 'getdel'`.

**Why it happens:** `CacheService.__init__` sets `self._redis = None` and only initializes it lazily via `prewarm()` or the first cache operation. The circuit breaker can also set it back to `None` on repeated failures.

**How to avoid:**
- Always guard: `if redis_client is None: return None` before any Redis operation
- Or add a `get_raw_redis()` method to `CacheService` that explicitly connects and returns the client, raising a clear exception if unavailable

---

## Code Examples

### Existing verify_token signature (from app/app_utils/auth.py)

```python
# Source: app/app_utils/auth.py lines 56-109
async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """Returns dict: {id, email, metadata, role, jwt_claims?}"""
```

**For require_admin:** call as `user = await verify_token(credentials)` where `credentials` is obtained via `Depends(security)`. The return dict always has `id` and `email`.

### Existing limiter usage pattern (from app/routers/a2a.py)

```python
# Source: app/routers/a2a.py lines 53-55
@router.get("/tasks/{task_id}")
@limiter.limit(get_user_persona_limit)
async def get_task_status(request: Request, ...):
```

For admin routes, use a fixed string instead of `get_user_persona_limit`:

```python
@router.post("/chat")
@limiter.limit("30/minute")
async def admin_chat(request: Request, admin_user: dict = Depends(require_admin)):
```

### Existing service client pattern (from app/routers/approvals.py)

```python
# Source: app/routers/approvals.py line 13
from app.services.supabase import get_service_client
# Used as: client = get_service_client()  (synchronous, bypasses RLS)
```

### Existing router registration pattern (from app/fast_api_app.py lines 669-697)

```python
# Add to fast_api_app.py imports section:
from app.routers.admin import router as admin_router

# Add to include_router section:
app.include_router(admin_router, tags=["Admin"])
```

The `app/routers/admin/__init__.py` should create a parent router with `prefix="/admin"` and include the sub-routers:

```python
# app/routers/admin/__init__.py
from fastapi import APIRouter
from app.routers.admin.auth import router as auth_router
from app.routers.admin.chat import router as chat_router
from app.routers.admin.audit import router as audit_router

router = APIRouter(prefix="/admin")
router.include_router(auth_router)
router.include_router(chat_router)
router.include_router(audit_router)
```

### Agent tools list pattern (from app/agents/financial/agent.py lines 153-167)

```python
# Source: app/agents/financial/agent.py
from app.agents.tools.base import sanitize_tools

FINANCIAL_AGENT_TOOLS = sanitize_tools([get_revenue_stats, mcp_web_search, ...])

financial_agent = Agent(
    name="FinancialAnalysisAgent",
    ...
    tools=FINANCIAL_AGENT_TOOLS,
)
```

AdminAgent should also use `sanitize_tools()` — it de-dupes and validates the tool list.

### CacheService Redis access pattern (from app/services/cache.py)

```python
# The cache service exposes self._redis as redis.asyncio.Redis
# Access via: cache = get_cache_service(); redis_client = cache._redis
# BUT: _redis may be None. Always guard.

from app.services.cache import get_cache_service

cache = get_cache_service()
redis_client = cache._redis
if redis_client is None:
    # Redis not available — degrade gracefully
    raise HTTPException(503, detail="Cache service unavailable")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single Fernet key | MultiFernet with comma-separated keys | Phase 7 (new) | Enables zero-downtime key rotation |
| Ad hoc admin access via direct Supabase SQL | require_admin FastAPI dependency | Phase 7 (new) | Every admin route is auditable from day one |
| No admin session persistence | admin_chat_sessions + admin_chat_messages rows | Phase 7 (new) | Admin chat survives page refresh |
| LLM-enforced action gates | Python tool code enforces autonomy tiers | Phase 7 (new) | Injection-resistant; cannot be bypassed via prompt |

**Deprecated/outdated:**
- None — this is entirely new infrastructure

---

## Open Questions

1. **`@supabase/ssr` availability for server component AdminGuard**
   - What we know: The existing frontend uses `createClient` from `@/lib/supabase/client` (client-side only)
   - What's unclear: Whether `@supabase/ssr` is installed and configured for server component cookie-based auth
   - Recommendation: Check `frontend/package.json` for `@supabase/ssr` before building `AdminLayout`. If not present, Wave 0 must install it (`npm install @supabase/ssr`) or `AdminGuard` must be a client component.

2. **ADK Runner isolation for AdminAgent**
   - What we know: The existing `runner` in `fast_api_app.py` is bound to `adk_app` (the main app). `Runner` takes `session_service` as a parameter.
   - What's unclear: Whether creating a separate `Runner` instance for AdminAgent requires any global setup (e.g., `GOOGLE_GENAI_USE_VERTEXAI` env) beyond what is already done in `fast_api_app.py`
   - Recommendation: Create `admin_runner = Runner(app=admin_adk_app, session_service=InMemorySessionService())` directly in `app/routers/admin/chat.py` rather than in `fast_api_app.py` to keep admin infrastructure self-contained. No global setup changes needed.

3. **Redis `GETDEL` availability (requires Redis 6.2+)**
   - What we know: `redis>=5.0.0,<6.0.0` (Python client) is installed. The actual Redis server version may vary between local Docker and production.
   - What's unclear: Whether the Redis server version in the Docker compose and Cloud Run environment supports `GETDEL` (Redis 6.2+)
   - Recommendation: Wave 0 should verify `docker compose exec redis redis-server --version`. If Redis < 6.2, use Lua script for atomic get-and-delete instead: `redis_client.eval("local v=redis.call('GET',KEYS[1]) if v then redis.call('DEL',KEYS[1]) end return v", 1, key)`

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (configured in pyproject.toml) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/unit/test_admin_*.py -x` |
| Full suite command | `uv run pytest tests/ -x --ignore=tests/load_test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | require_admin grants access for email in ADMIN_EMAILS | unit | `uv run pytest tests/unit/test_admin_auth.py::test_env_allowlist_grants_access -x` | Wave 0 |
| AUTH-02 | require_admin grants access for DB role | unit | `uv run pytest tests/unit/test_admin_auth.py::test_db_role_grants_access -x` | Wave 0 |
| AUTH-03 | require_admin OR logic: either path grants access | unit | `uv run pytest tests/unit/test_admin_auth.py::test_or_logic -x` | Wave 0 |
| AUTH-04 | ADMIN_EMAILS never in client bundle (no NEXT_PUBLIC_) | smoke | manual env audit — no automated test possible | manual-only |
| AUTH-05 | Non-admin gets HTTP 403 from require_admin | unit | `uv run pytest tests/unit/test_admin_auth.py::test_non_admin_gets_403 -x` | Wave 0 |
| ASST-01 | POST /admin/chat returns SSE stream | integration | `uv run pytest tests/integration/test_admin_chat.py::test_sse_stream -x` | Wave 0 |
| ASST-03 | Auto-tier tool executes without confirmation | unit | `uv run pytest tests/unit/test_admin_tools.py::test_auto_tier_executes -x` | Wave 0 |
| ASST-03 | Confirm-tier tool returns requires_confirmation dict | unit | `uv run pytest tests/unit/test_admin_tools.py::test_confirm_tier_returns_token -x` | Wave 0 |
| ASST-03 | Blocked-tier tool returns error without executing | unit | `uv run pytest tests/unit/test_admin_tools.py::test_blocked_tier_refuses -x` | Wave 0 |
| ASST-05 | Confirmation token consumed atomically (no double-use) | unit | `uv run pytest tests/unit/test_admin_tokens.py::test_token_single_consumption -x` | Wave 0 |
| ASST-06 | Chat history loads from admin_chat_messages on mount | unit | `uv run pytest tests/unit/test_admin_chat_history.py -x` | Wave 0 |
| AUDT-01 | log_admin_action writes row to admin_audit_log | unit | `uv run pytest tests/unit/test_admin_audit.py::test_log_action_writes_row -x` | Wave 0 |
| AUDT-02 | encrypt_secret + decrypt_secret round-trip | unit | `uv run pytest tests/unit/test_encryption.py::test_fernet_roundtrip -x` | Wave 0 |
| AUDT-02 | MultiFernet key rotation: old key still decrypts | unit | `uv run pytest tests/unit/test_encryption.py::test_key_rotation -x` | Wave 0 |
| AUDT-03 | GET /admin/audit-log returns paginated rows | integration | `uv run pytest tests/integration/test_admin_audit_log.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/test_admin_auth.py tests/unit/test_admin_tools.py tests/unit/test_encryption.py -x`
- **Per wave merge:** `uv run pytest tests/unit/ tests/integration/test_admin_*.py -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_admin_auth.py` — covers AUTH-01..05 (require_admin unit tests with mocked Supabase)
- [ ] `tests/unit/test_admin_tools.py` — covers ASST-03 (autonomy tier enforcement with mocked DB)
- [ ] `tests/unit/test_admin_tokens.py` — covers ASST-05 (Redis token atomic consumption, mocked redis client)
- [ ] `tests/unit/test_encryption.py` — covers AUDT-02 (Fernet round-trip, key rotation)
- [ ] `tests/unit/test_admin_audit.py` — covers AUDT-01 (log_admin_action with mocked Supabase service client)
- [ ] `tests/unit/test_admin_chat_history.py` — covers ASST-06 (history load logic, mocked Supabase)
- [ ] `tests/integration/test_admin_chat.py` — covers ASST-01 (SSE stream test with TestClient)
- [ ] `tests/integration/test_admin_audit_log.py` — covers AUDT-03 (audit log endpoint with TestClient)
- [ ] Existing `tests/unit/conftest.py` already mocks `google.adk` — new admin agent tests inherit this mock

---

## Sources

### Primary (HIGH confidence)

- `app/app_utils/auth.py` — `verify_token` signature, `get_user_id_from_bearer_token`, strict auth mode pattern; read directly
- `app/agents/financial/agent.py` — `create_financial_agent()` factory pattern, `Agent` constructor with `tools`, `sanitize_tools` usage; read directly
- `app/agents/shared.py` — `get_model()`, `get_fallback_model()`, `FAST_AGENT_CONFIG`, `DEEP_AGENT_CONFIG`; read directly
- `app/fast_api_app.py` — router registration pattern, `app.include_router()`, `limiter` setup, CORS config; read directly
- `app/services/cache.py` — `CacheService` singleton, `_redis` attribute, `with_circuit_breaker`, TTL constants; read directly
- `app/middleware/rate_limiter.py` — `limiter = Limiter(...)`, `@limiter.limit()` usage; read directly
- `app/routers/approvals.py` — `get_service_client()` usage, `APIRouter`, `HTTPException` patterns; read directly
- `app/routers/a2a.py` — router with prefix, `Depends(get_current_user_id)` pattern; read directly
- `app/services/scheduled_endpoints.py` — `_verify_scheduler()` dependency pattern (model for `require_admin`); read directly
- `frontend/src/hooks/useAgentChat.ts` — complete SSE hook implementation; read directly (790 lines)
- `frontend/src/components/layout/Sidebar.tsx` — sidebar pattern with nav items, badge, Lucide icons; read directly
- `frontend/src/app/(personas)/layout.tsx` — minimal server component route group layout; read directly
- `frontend/src/app/layout.tsx` — root layout with Toaster, font setup; read directly
- `tests/unit/conftest.py` — mock setup for google.adk; read directly
- `supabase/migrations/` — migration naming pattern confirmed: latest is `20260321200000_security_fixes.sql`
- `pyproject.toml` — confirmed `cryptography>=46.0.3`, `redis>=5.0.0,<6.0.0`, `slowapi>=0.1.9`, `PyJWT>=2.8.0` all present
- `.planning/config.json` — `nyquist_validation: true`; pytest + vitest preferences confirmed

### Secondary (MEDIUM confidence)

- `.planning/research/STACK.md` — verified Fernet, httpx, recharts, TanStack recommendations
- `.planning/research/ARCHITECTURE.md` — system diagram, component list, data flow; verified against codebase
- `.planning/research/PITFALLS.md` — 10 pitfalls with prevention strategies; verified against code patterns

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new packages; all dependencies confirmed present in pyproject.toml
- Architecture: HIGH — every pattern derived from existing files read directly
- Pitfalls: HIGH — grounded in actual code reading (CacheService._redis may be None, AdminGuard server component token issue, ADK Runner namespace isolation)

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable stack; ADK API may change if google-adk is upgraded)
