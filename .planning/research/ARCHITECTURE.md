# Architecture Research

**Domain:** AI-first admin panel integration into existing FastAPI/ADK/Next.js system
**Researched:** 2026-03-21
**Confidence:** HIGH — all patterns derived directly from the existing codebase and approved design spec; no external speculation needed for integration architecture.

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (Next.js 16, App Router)                    │
│                                                                                │
│  ┌─────────────────────────────────────────────┐  ┌───────────────────────┐  │
│  │           /admin/* route group (NEW)          │  │  Existing app routes  │  │
│  │  ┌───────────────────────────────────────┐   │  │  (unchanged)          │  │
│  │  │  AdminGuard (layout.tsx) — server-side│   │  │                       │  │
│  │  │  GET /admin/check-access → 302 or pass│   │  └───────────────────────┘  │
│  │  └────────────────────┬──────────────────┘   │                            │
│  │         ┌─────────────┼────────────────┐      │                            │
│  │  ┌──────▼──────┐ ┌────▼────┐ ┌─────────▼──┐  │                            │
│  │  │ Dashboard   │ │ Users   │ │ Monitoring  │  │                            │
│  │  │ /admin      │ │/users/* │ │/monitoring  │  │                            │
│  │  └─────────────┘ └─────────┘ └────────────┘  │                            │
│  │  + Analytics / Approvals / Config / Billing   │                            │
│  │  + Integrations / Settings / Audit            │                            │
│  │                                               │                            │
│  │  ┌───────────────────────────────────────┐   │                            │
│  │  │  useAdminChat hook (NEW)               │   │                            │
│  │  │  mirrors useAgentChat pattern          │   │                            │
│  │  │  fetchEventSource → POST /admin/chat   │   │                            │
│  │  └───────────────────────────────────────┘   │                            │
│  │                                               │                            │
│  │  ┌───────────────────────────────────────┐   │                            │
│  │  │  ImpersonationContext (NEW)            │   │                            │
│  │  │  wraps PersonaContext for /impersonate │   │                            │
│  │  └───────────────────────────────────────┘   │                            │
│  └─────────────────────────────────────────────┘                            │
└──────────────────────────────────────────────────────────────────────────────┘
                     │ SSE stream / REST (JWT Authorization header)
┌──────────────────────────────────────────────────────────────────────────────┐
│                          BACKEND (FastAPI)                                     │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  fast_api_app.py — existing routers + NEW admin router registration   │    │
│  └──────────────────────┬───────────────────────────────────────────────┘    │
│                          │                                                     │
│  ┌───────────────────────▼──────────────────────────────────────────────┐    │
│  │  app/routers/admin/ (NEW router package)                              │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │    │
│  │  │  chat.py     │ │  users.py    │ │ monitoring.py│ │analytics.py│  │    │
│  │  │  POST/chat   │ │  GET/PATCH   │ │  GET/health  │ │  GET/stats │  │    │
│  │  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └────────────┘  │    │
│  │  ┌──────┴───────────────────────────────────┴──────────────────────┐  │    │
│  │  │  require_admin FastAPI dependency (NEW) — checks ADMIN_EMAILS   │  │    │
│  │  │  env var OR user_roles table, raises 403 on fail                │  │    │
│  │  └─────────────────────────────────────────────────────────────────┘  │    │
│  └───────────────────────┬──────────────────────────────────────────────┘    │
│                           │                                                    │
│  ┌────────────────────────▼─────────────────────────────────────────────┐    │
│  │  Google ADK Agent Layer                                               │    │
│  │  ┌────────────────────────────┐  ┌────────────────────────────────┐  │    │
│  │  │  AdminAgent (NEW)          │  │  ExecutiveAgent + 10 specialized│  │    │
│  │  │  app/agents/admin/agent.py │  │  agents (UNCHANGED)            │  │    │
│  │  │  30+ FunctionTools by domain│  └────────────────────────────────┘  │    │
│  │  │  reads admin_agent_permissions│                                    │    │
│  │  │  before each tool execution   │                                    │    │
│  │  └────────────────────────────┘                                      │    │
│  └───────────────────────┬──────────────────────────────────────────────┘    │
│                           │                                                    │
│  ┌────────────────────────▼─────────────────────────────────────────────┐    │
│  │  app/agents/admin/tools/ (NEW tool modules)                           │    │
│  │  users.py │ monitoring.py │ integrations.py │ analytics.py            │    │
│  │  configuration.py │ billing.py │ approvals.py                         │    │
│  └───────────────────────┬──────────────────────────────────────────────┘    │
│                           │                                                    │
│  ┌────────────────────────▼─────────────────────────────────────────────┐    │
│  │  Support Services (NEW + EXISTING)                                    │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │    │
│  │  │ encryption.py(N) │  │ audit_logger.py(N)│  │ health_checker.py(N│  │    │
│  │  │ Fernet key wrap  │  │ admin_audit_log  │  │ Cloud Scheduler loop│  │    │
│  │  └──────────────────┘  └──────────────────┘  └────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │    │
│  │  │ Existing: cache.py, supabase.py, scheduled_endpoints.py (all REUSED)│  │    │
│  │  └──────────────────────────────────────────────────────────────────┘  │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
│  Cloud Scheduler → POST /admin/monitoring/run-check (every 60s)               │
│  (same WORKFLOW_SERVICE_SECRET auth pattern as scheduled_endpoints.py)        │
└──────────────────────────────────────────────────────────────────────────────┘
                     │ service role (bypasses RLS)
┌──────────────────────────────────────────────────────────────────────────────┐
│                          Supabase (PostgreSQL)                                 │
│                                                                                │
│  EXISTING TABLES (read by admin, never structurally modified)                  │
│  auth.users │ profiles │ workflows │ approvals │ sessions │ ai_jobs            │
│                                                                                │
│  NEW ADMIN TABLES (service role only, RLS blocks anon)                         │
│  user_roles │ admin_agent_permissions │ admin_chat_sessions                    │
│  admin_chat_messages │ admin_integrations │ api_health_checks                  │
│  api_incidents │ admin_audit_log │ admin_config_history                        │
│                                                                                │
│  EXCEPTION: user_roles has explicit RLS for frontend auth check flow           │
└──────────────────────────────────────────────────────────────────────────────┘
                     │ Fernet-encrypted keys decrypted at call time
┌──────────────────────────────────────────────────────────────────────────────┐
│              External Integration APIs (server-side proxy only)                │
│  Sentry │ PostHog │ CodeRabbit │ GitHub │ Stripe                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Status |
|-----------|---------------|--------|
| `frontend/src/app/(admin)/layout.tsx` | AdminGuard: calls `GET /admin/check-access`, redirects non-admins, renders sidebar + persistent chat panel | NEW |
| `frontend/src/app/(admin)/` route pages | Dashboard pages for each domain: users, monitoring, analytics, approvals, config, billing, integrations, settings | NEW |
| `frontend/src/hooks/useAdminChat.ts` | fetchEventSource wrapper for `POST /admin/chat`, same shape as `useAgentChat` but targets admin endpoint | NEW |
| `frontend/src/contexts/ImpersonationContext.tsx` | Overrides PersonaContext for `/admin/impersonate/[userId]`, persists impersonation banner | NEW |
| `app/routers/admin/` | FastAPI router package — all `/admin/*` endpoints; each file owns one domain; all depend on `require_admin` | NEW |
| `app/middleware/admin_auth.py` | `require_admin` FastAPI dependency: validates JWT, checks `ADMIN_EMAILS` env OR `user_roles` table, returns 403 on fail | NEW |
| `app/agents/admin/agent.py` | Google ADK `AdminAgent`: Gemini Pro/Flash model, 30+ FunctionTools, loads autonomy permissions from DB before each invocation | NEW |
| `app/agents/admin/tools/` | Seven tool modules (users, monitoring, integrations, analytics, configuration, billing, approvals) each returning structured dicts for the agent | NEW |
| `app/services/encryption.py` | Fernet symmetric encryption: `encrypt_api_key()`, `decrypt_api_key()`, key from `ADMIN_ENCRYPTION_KEY` env var; never returns plaintext to frontend | NEW |
| `app/services/admin_audit.py` | `log_admin_action()` writes to `admin_audit_log` with source tag (`manual`/`ai_agent`/`impersonation`) | NEW |
| `app/services/health_checker.py` | Pings internal endpoints, external providers, and admin integrations; writes to `api_health_checks`; detects anomalies and creates `api_incidents` | NEW |
| `app/routers/admin/monitoring.py` | Handles `POST /admin/monitoring/run-check` (Cloud Scheduler hook) + `GET /admin/monitoring/*` read endpoints | NEW |
| `supabase/migrations/20260321*_admin_*.sql` | Nine new admin tables via Supabase migration chain | NEW |
| `app/services/scheduled_endpoints.py` | Existing Cloud Scheduler pattern — REUSED unchanged; `run-check` follows identical auth pattern | EXISTING (model) |
| `app/app_utils/auth.py` | Existing JWT verification (`verify_token`, `verify_token_fast`) — REUSED by `require_admin` | EXISTING (reused) |
| `app/services/supabase.py` | `get_service_client()` — REUSED unchanged for all admin DB access | EXISTING (reused) |
| `app/services/cache.py` | Redis circuit breaker — REUSED; `get_redis_status` admin tool reads its state | EXISTING (reused) |
| `app/middleware/rate_limiter.py` | slowapi `limiter` — REUSED; admin routes add their own `@limiter.limit()` decorators | EXISTING (reused) |
| `frontend/src/contexts/PersonaContext.tsx` | Existing context — WRAPPED (not modified) by `ImpersonationContext` during impersonation sessions | EXISTING (wrapped) |
| `frontend/src/hooks/useAgentChat.ts` | Existing hook — REFERENCED as the pattern for `useAdminChat`; not modified | EXISTING (model) |

---

## Recommended Project Structure

```
app/
├── agents/
│   └── admin/                          # NEW: admin agent package
│       ├── __init__.py
│       ├── agent.py                    # AdminAgent definition (ADK agent, 30+ tools)
│       └── tools/                      # NEW: admin tool modules
│           ├── __init__.py
│           ├── users.py                # list_users, get_user_detail, suspend_user, etc.
│           ├── monitoring.py           # check_system_health, get_agent_metrics, etc.
│           ├── integrations.py         # sentry_*, posthog_*, coderabbit_*, github_*, etc.
│           ├── analytics.py            # get_usage_stats, get_agent_effectiveness, etc.
│           ├── configuration.py        # list_agent_configs, update_agent_instructions, etc.
│           ├── billing.py              # get_revenue_metrics, change_user_plan, etc.
│           └── approvals.py            # list_all_approvals, override_approval, etc.
├── middleware/
│   ├── rate_limiter.py                 # EXISTING — reused
│   └── admin_auth.py                   # NEW: require_admin FastAPI dependency
├── routers/
│   ├── (existing routers — unchanged)
│   └── admin/                          # NEW: admin router package
│       ├── __init__.py
│       ├── chat.py                     # POST /admin/chat (SSE streaming)
│       ├── users.py                    # GET/PATCH /admin/users, GET /admin/users/{id}
│       ├── monitoring.py               # GET /admin/monitoring/*, POST /admin/monitoring/run-check
│       ├── analytics.py                # GET /admin/analytics/*
│       ├── approvals.py                # GET /admin/approvals, POST /admin/approvals/{id}/override
│       ├── configuration.py            # GET/POST /admin/configuration/*
│       ├── integrations.py             # GET/POST /admin/integrations/*, proxy routes
│       ├── billing.py                  # GET /admin/billing/*
│       ├── audit.py                    # GET /admin/audit-log
│       └── access.py                   # GET /admin/check-access (frontend auth check)
├── services/
│   ├── (existing services — unchanged)
│   ├── encryption.py                   # NEW: Fernet encrypt/decrypt for API keys
│   ├── admin_audit.py                  # NEW: log_admin_action() with source tagging
│   └── health_checker.py               # NEW: endpoint pinger, anomaly detector, incident creator
└── config/
    └── validation.py                   # MODIFY: add ADMIN_EMAILS, ADMIN_ENCRYPTION_KEY to env var registry

supabase/migrations/
├── (existing 96 migrations — unchanged)
├── 20260322000000_admin_foundation.sql  # user_roles + is_admin() + admin_agent_permissions
│                                        # + admin_chat_sessions + admin_chat_messages
│                                        # + admin_audit_log + admin_config_history
└── 20260322100000_admin_monitoring.sql  # admin_integrations + api_health_checks + api_incidents

frontend/src/
├── app/
│   ├── (personas)/                      # EXISTING — unchanged
│   └── (admin)/                         # NEW: admin route group
│       ├── layout.tsx                   # AdminGuard + sidebar + persistent chat panel
│       ├── page.tsx                     # /admin — overview + status cards
│       ├── users/
│       │   ├── page.tsx                 # User table with search/filters
│       │   └── [id]/page.tsx            # User detail + actions
│       ├── monitoring/page.tsx          # Health dashboard
│       ├── analytics/page.tsx           # Usage dashboards
│       ├── approvals/page.tsx           # Cross-user approval oversight
│       ├── configuration/page.tsx       # Agent config editor + feature flags
│       ├── billing/page.tsx             # Revenue dashboard
│       ├── integrations/page.tsx        # External tool connection management
│       ├── settings/page.tsx            # Autonomy permissions editor
│       ├── audit-log/page.tsx           # Audit trail viewer
│       └── impersonate/[userId]/page.tsx# Impersonation view wrapper
├── contexts/
│   ├── PersonaContext.tsx               # EXISTING — unchanged
│   └── ImpersonationContext.tsx         # NEW: wraps PersonaContext, adds banner
└── hooks/
    ├── useAgentChat.ts                  # EXISTING — unchanged (pattern model)
    └── useAdminChat.ts                  # NEW: mirrors useAgentChat for /admin/chat SSE
```

### Structure Rationale

- **`app/agents/admin/` as a package:** Mirrors every existing specialized agent (`app/agents/financial/`, `app/agents/content/`, etc.). The AdminAgent is a first-class ADK agent, not a special case.
- **`app/routers/admin/` as a package:** The 9+ admin domains would bloat a single file. One file per domain keeps each under 200 lines. The `require_admin` dependency is declared once in `admin_auth.py` and injected per-router.
- **`(admin)/` Next.js route group:** Parallel to `(personas)/` — same isolation pattern. Shared layout (AdminGuard + sidebar) applies to all admin pages without polluting the user-facing layout.
- **Two migration files:** The foundation migration contains all tables needed for Phase 1 (auth, agent, chat, audit, config versioning). The monitoring migration is a separate file because the health check tables have different access patterns (high write volume, 30-day pruning) and may need independent index tuning.

---

## Architectural Patterns

### Pattern 1: Two-Layer Admin Authorization (env OR database)

**What:** `require_admin` FastAPI dependency checks `ADMIN_EMAILS` environment variable first (fast, no DB), then falls back to querying `user_roles` table. Either passing grants access (OR logic). This uses the existing `verify_token` / `verify_token_fast` from `app/app_utils/auth.py` as the JWT validation step.

**When to use:** Every `/admin/*` endpoint. Injected via `Depends(require_admin)` on the router prefix.

**Trade-offs:** OR logic means removing an email from `ADMIN_EMAILS` does not revoke if they have a DB role. Intentional — the env var is for bootstrap; DB roles are for ongoing management. For revocation, remove from both.

**Example:**
```python
# app/middleware/admin_auth.py
async def require_admin(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Client = Depends(get_service_client),
) -> dict:
    user = await verify_token(credentials)           # existing auth util
    email = user["email"]
    user_id = user["id"]

    # Layer 1: env allowlist (server-side only, never NEXT_PUBLIC_)
    admin_emails = {e.strip() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()}
    if email in admin_emails:
        return user

    # Layer 2: database role
    result = db.rpc("is_admin", {"check_user_id": user_id}).execute()
    if result.data:
        return user

    raise HTTPException(status_code=403, detail="Admin access required")
```

### Pattern 2: AdminAgent with Pre-Invocation Autonomy Check

**What:** The `AdminAgent` is a standard Google ADK agent. Before each tool executes, the tool itself reads its autonomy level from `admin_agent_permissions`. `auto` = execute and return result. `confirm` = return a structured confirmation card to the frontend instead of executing. `blocked` = raise a descriptive error. The autonomy levels are loaded into the system prompt at request time so the agent knows not to attempt blocked actions.

**When to use:** Every tool in `app/agents/admin/tools/`.

**Trade-offs:** Loading permissions on every `/admin/chat` request adds one DB read. Acceptable — permissions rarely change and can be cached with a 60-second TTL per admin session. Storing this in the system prompt (not just the tool) means the model learns to not propose blocked actions, reducing wasted confirm/block cycles.

**Example:**
```python
# app/agents/admin/tools/users.py
async def suspend_user(user_id: str, reason: str) -> dict:
    autonomy = await get_action_autonomy("user_management", "suspend_user")
    if autonomy == "blocked":
        return {"error": "suspend_user is blocked by current permissions"}
    if autonomy == "confirm":
        # Return confirmation card data — agent formats this into chat widget
        return {
            "requires_confirmation": True,
            "action": "suspend_user",
            "params": {"user_id": user_id, "reason": reason},
            "description": f"Suspend user {user_id}. Reason: {reason}",
            "consequence": "This will immediately disable their access to all Pikar-AI services.",
        }
    # autonomy == "auto"
    await _do_suspend(user_id, reason)
    await log_admin_action("suspend_user", "user", user_id, source="ai_agent")
    return {"success": True, "user_id": user_id}
```

### Pattern 3: Server-Side Integration Proxy with Fernet Encryption

**What:** External API keys (Sentry, PostHog, etc.) are stored encrypted in `admin_integrations.api_key_encrypted` using Fernet symmetric encryption. The encryption key lives in `ADMIN_ENCRYPTION_KEY` env var (or Secret Manager in production). All calls to external APIs go through FastAPI backend routes — the frontend never sees a decrypted key or calls external APIs directly.

**When to use:** Every external integration call from the admin panel.

**Trade-offs:** Server-side proxy adds latency (~50ms roundtrip overhead) vs. direct browser calls. Acceptable given this is an admin panel, not a real-time user-facing feature. The security benefit (keys never in client bundle) outweighs the latency.

**Example:**
```python
# app/services/encryption.py
from cryptography.fernet import Fernet

def encrypt_api_key(plaintext: str) -> str:
    key = os.getenv("ADMIN_ENCRYPTION_KEY").encode()
    return Fernet(key).encrypt(plaintext.encode()).decode()

def decrypt_api_key(ciphertext: str) -> str:
    key = os.getenv("ADMIN_ENCRYPTION_KEY").encode()
    return Fernet(key).decrypt(ciphertext.encode()).decode()

# app/routers/admin/integrations.py
@router.get("/integrations/{provider}/issues")
async def proxy_integration(provider: str, _admin=Depends(require_admin)):
    row = db.table("admin_integrations").select("*").eq("provider", provider).single().execute()
    api_key = decrypt_api_key(row.data["api_key_encrypted"])  # in-memory only
    response = await httpx.AsyncClient().get(
        f"{row.data['base_url']}/api/0/issues/",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    # api_key goes out of scope here — never written to logs or returned
    return transform_response(provider, response.json())
```

### Pattern 4: Cloud Scheduler Health Loop (Existing Pattern Extended)

**What:** Cloud Scheduler sends `POST /admin/monitoring/run-check` every 60 seconds, authenticated via `WORKFLOW_SERVICE_SECRET` header — the same pattern used by `app/routers/scheduled_endpoints.py` for daily reports and digests. The handler runs async health pings for all monitored endpoints, writes results to `api_health_checks`, and creates `api_incidents` when anomalies are detected.

**When to use:** Health monitoring only. No user-facing requests use this endpoint.

**Trade-offs:** Cloud Scheduler has a 1-minute minimum interval. For sub-minute alerting, would need a background asyncio task. For admin use, 60-second polling is acceptable.

### Pattern 5: Admin Impersonation via Context Override

**What:** `/admin/impersonate/[userId]` renders the existing persona layouts but wraps them in an `ImpersonationContext` that overrides `PersonaContext` with the target user's data. The backend accepts an optional `X-Impersonate-User-Id` header on admin endpoints — when present and requester is a verified admin, data queries are scoped to the target user. All impersonation actions are tagged `source: "impersonation"` in `admin_audit_log`.

**When to use:** When an admin needs to debug or test a specific user's experience.

**Trade-offs:** Interactive mode (full interaction as the target user) requires `super_admin` role. View mode (read-only) is available to all admins. Sessions auto-expire at 30 minutes to limit audit surface.

---

## Data Flow

### Flow 1: Admin Chat Request (Standard)

```
Admin types message in useAdminChat hook
    │ fetchEventSource POST /admin/chat {message, session_id}
    │ Authorization: Bearer <admin JWT>
    ▼
FastAPI: require_admin dependency
    │ verify JWT (existing verify_token)
    │ check ADMIN_EMAILS env OR is_admin() DB function
    │ 403 if neither passes
    ▼
chat.py handler
    │ load autonomy permissions from admin_agent_permissions (one DB read, cacheable)
    │ load recent health summary for system prompt context
    │ load pending items (approvals, incidents) count
    ▼
AdminAgent invocation (Google ADK, Gemini Pro → Flash fallback)
    │ system prompt: platform context + autonomy levels + current health
    │ tool definitions: 30+ FunctionTools
    ▼
Tool execution (example: check_system_health)
    │ check autonomy level (auto for read tools)
    │ aggregate /health/live, /health/connections, /health/cache, /health/embeddings
    │ query api_incidents for active unresolved incidents
    │ log to admin_audit_log (source: "ai_agent")
    ▼
SSE stream response → useAdminChat → AdminChatPanel renders message
    │ plain text OR structured widget (confirmation card, data table, chart)
    ▼
Session persisted: admin_chat_sessions + admin_chat_messages (individual rows)
```

### Flow 2: Confirm-Level Tool Action

```
Admin: "Suspend user jane@example.com for spam"
    ▼
AdminAgent invokes suspend_user tool
    │ autonomy check → "confirm"
    │ returns {requires_confirmation: true, action, params, description, consequence}
    ▼
SSE stream: agent returns ConfirmationCard widget data
    ▼
Frontend renders confirmation card in chat:
    ┌─────────────────────────────┐
    │ Action Requires Confirmation│
    │ Suspend jane@example.com    │
    │ Reason: spam activity       │
    │ [Cancel]        [Confirm]   │
    └─────────────────────────────┘
    ▼
Admin clicks Confirm
    │ Frontend: POST /admin/users/{id}/suspend {confirmed: true, action_token}
    ▼
Backend: executes suspension
    │ updates user status in Supabase
    │ logs to admin_audit_log (source: "ai_agent", confirmed=true)
    ▼
Agent receives confirmation result, streams summary to chat
```

### Flow 3: External Integration Proxy

```
Admin chat: "Show me the latest Sentry errors"
    ▼
AdminAgent invokes sentry_get_issues tool (autonomy: auto)
    ▼
app/agents/admin/tools/integrations.py
    │ fetch admin_integrations row for provider="sentry"
    │ decrypt api_key_encrypted → plaintext key (in-memory only)
    │ GET https://sentry.io/api/0/projects/{org}/{proj}/issues/
    │   Authorization: Bearer {decrypted_key}
    │ transform response to internal format
    │ plaintext key goes out of scope
    ▼
Agent formats results as structured data
    ▼
SSE stream: renders as data table widget in admin chat
```

### Flow 4: Health Check Monitoring Loop

```
Cloud Scheduler → POST /admin/monitoring/run-check (every 60s)
    │ X-Scheduler-Secret: {WORKFLOW_SERVICE_SECRET}
    ▼
monitoring.py handler
    │ verify scheduler secret (identical to scheduled_endpoints.py pattern)
    ▼
health_checker.py
    │ async ping all internal endpoints (/health/live, /health/connections, etc.)
    │ async check Gemini API, Supabase, Redis availability
    │ async ping each active admin_integration (Sentry, PostHog, etc.)
    │ write results to api_health_checks
    ▼
anomaly detection
    │ status changed since last check?
    │ response time > 2x rolling 1h average?
    │ error rate > 5% in last 10 checks?
    │ rate limit approaching threshold?
    ▼
if anomaly: INSERT api_incidents
    │ if critical (multiple systems): send email via existing email infra
    ▼
Next admin panel open → AdminAgent proactive greeting includes incident count
```

### Flow 5: Impersonation Session

```
Admin: clicks "Impersonate" on user detail page (or via agent tool)
    ▼
Frontend: GET /admin/users/{id}/impersonate-token
    │ require_admin validates admin JWT
    │ creates short-lived impersonation token (30min TTL) stored in DB
    │ logs to admin_audit_log (source: "manual")
    ▼
Frontend: navigate to /admin/impersonate/{userId}
    │ ImpersonationContext loads target user's profile/persona
    │ renders existing persona layout with user's data
    │ persistent banner: "Viewing as: user@example.com [Exit] [Switch to Interactive]"
    ▼
All backend requests from impersonation view:
    │ include X-Impersonate-User-Id: {userId} header
    │ admin JWT in Authorization header (not target user's JWT)
    ▼
Backend: require_admin validates admin JWT
    │ detects X-Impersonate-User-Id header
    │ scopes data queries to target user
    │ logs all reads/writes to admin_audit_log (source: "impersonation")
```

---

## New vs. Modified Components

### New Components (Phase 1 must build first)

| Component | Type | Phase |
|-----------|------|-------|
| `supabase/migrations/20260322*_admin_foundation.sql` | DB migration | 1 |
| `supabase/migrations/20260322*_admin_monitoring.sql` | DB migration | 2 |
| `app/middleware/admin_auth.py` | Python module | 1 |
| `app/services/encryption.py` | Python module | 1 |
| `app/services/admin_audit.py` | Python module | 1 |
| `app/agents/admin/agent.py` | ADK agent | 1 |
| `app/agents/admin/tools/` (all 7 modules) | ADK tool modules | 1-8 |
| `app/routers/admin/` (all 10 router files) | FastAPI routers | 1-9 |
| `app/services/health_checker.py` | Python module | 2 |
| `frontend/src/app/(admin)/` (all pages) | Next.js pages | 1-9 |
| `frontend/src/hooks/useAdminChat.ts` | React hook | 1 |
| `frontend/src/contexts/ImpersonationContext.tsx` | React context | 3 |

### Modified Components (minimal changes, backward-compatible)

| Component | Change | Risk |
|-----------|--------|------|
| `app/fast_api_app.py` | Register `admin` router package | LOW — additive only |
| `app/config/validation.py` | Add `ADMIN_EMAILS`, `ADMIN_ENCRYPTION_KEY` to env registry | LOW — additive only |
| `frontend/src/app/layout.tsx` or root layout | Ensure `(admin)` route group is recognized by App Router | LOW — Next.js route groups are automatic |
| Cloud Scheduler config | Add new job: `POST /admin/monitoring/run-check` every 60s | LOW — additive, separate from existing jobs |

### Existing Components That Are NOT Modified

These are reused as-is; no changes needed:

- `app/app_utils/auth.py` — `verify_token` and `verify_token_fast` reused by `require_admin`
- `app/services/supabase.py` — `get_service_client()` reused by all admin services
- `app/services/cache.py` — Redis circuit breaker reused; admin tools query its state
- `app/middleware/rate_limiter.py` — `limiter` instance reused for admin route decorators
- `app/agents/shared.py` — `get_model()`, `get_fallback_model()` reused by AdminAgent
- `app/agents/base_agent.py` — `PikarAgent` base class reused by AdminAgent
- `frontend/src/hooks/useAgentChat.ts` — pattern model for `useAdminChat`; not changed
- `frontend/src/contexts/PersonaContext.tsx` — wrapped by ImpersonationContext, not changed
- `app/routers/approvals.py` — existing user-facing approval flow unchanged; admin gets a separate cross-user view

---

## Anti-Patterns

### Anti-Pattern 1: Admin Email Check in NEXT_PUBLIC_ Variable

**What people do:** Set `NEXT_PUBLIC_ADMIN_EMAILS=founder@example.com` to make the check available client-side.

**Why it's wrong:** `NEXT_PUBLIC_` variables are inlined into the JavaScript bundle, visible to any user who views page source. This leaks admin email addresses and makes it trivially easy for an attacker to identify admin accounts for targeted attacks.

**Do this instead:** Keep `ADMIN_EMAILS` as a server-side-only env var. The frontend calls `GET /admin/check-access` which checks server-side and returns `{allowed: boolean}` — never the actual email list.

### Anti-Pattern 2: Using Supabase Auth JWT for Admin Impersonation

**What people do:** Generate a Supabase auth session token for the target user and use it as the authorization credential during impersonation, effectively logging in as the user.

**Why it's wrong:** Supabase auth tokens have real permissions. An admin session using a user's token could trigger auth events, corrupt session state, and circumvent audit logging. You cannot distinguish "admin impersonating" from "user acting" at the auth layer.

**Do this instead:** The admin keeps their own JWT (validated via `require_admin`). An `X-Impersonate-User-Id` header signals data scoping on the backend. The backend verifies admin identity, then scopes queries. The target user's session is never touched.

### Anti-Pattern 3: AdminAgent as a Subprocess or Separate Service

**What people do:** Create a separate Node.js service for the admin AI (using Vercel AI SDK or similar) to "keep admin concerns separate."

**Why it's wrong:** Admin tools need direct access to Supabase service role, Redis state, all 10 specialized agents' metrics, internal health endpoints, and the encryption service. A separate service requires HTTP calls for every tool invocation, complicates auth (service-to-service secrets), and doubles deployment surface.

**Do this instead:** `AdminAgent` is a standard Google ADK agent in `app/agents/admin/agent.py`, exactly like `FinancialAgent` or `ContentAgent`. It runs in the same FastAPI process, shares the same DB client, and reuses `get_model()` and `get_fallback_model()` from `app/agents/shared.py`.

### Anti-Pattern 4: Storing Admin Audit Logs in Redis

**What people do:** Write admin action audit entries to Redis for speed, planning to flush to DB later.

**Why it's wrong:** Redis is not durable storage. Circuit breaker flips and data is lost. Audit logs must be append-only and permanent. The existing `admin_audit_log` DB table with an indexed write is fast enough for admin-frequency operations (not high-throughput user-facing requests).

**Do this instead:** Write audit entries synchronously to Supabase via service role client before returning success from each action. Use `asyncio.create_task()` if you need fire-and-forget, but ensure errors are logged and monitored.

### Anti-Pattern 5: Single Migration File for All Admin Tables

**What people do:** Dump all 9 admin tables into one migration file.

**Why it's wrong:** `api_health_checks` is a high-write table with 30-day auto-prune requirements. `user_roles` needs explicit RLS policies. `admin_integrations` contains encrypted data requiring careful column handling. Mixing these creates a migration that is hard to review and harder to roll back selectively.

**Do this instead:** Two migration files minimum: foundation tables (roles, permissions, chat, audit, config history) in one file; monitoring tables (health checks, incidents, integrations) in a second file. Each file is independently reviewable and rollback-able.

### Anti-Pattern 6: Feature Flags Stored Only in Environment Variables

**What people do:** Implement feature flags as env vars (`FEATURE_X_ENABLED=1`), reasoning it avoids a DB round trip.

**Why it's wrong:** The admin panel's value proposition includes toggling features from the UI without redeployment. Env var feature flags require a redeploy to change. The existing `app/services/feature_flags.py` shows this pattern is already in place — the admin panel must supersede it with DB-backed flags.

**Do this instead:** Add a `feature_flags` table (can be part of `admin_config_history` pattern) and have the feature flag service check DB first, fall back to env var only for bootstrap. The admin configuration UI writes to DB; env vars become override-only.

---

## Integration Points

### Reused Backend Patterns

| Existing Pattern | How Admin Panel Reuses It |
|-----------------|---------------------------|
| `verify_token()` in `app_utils/auth.py` | `require_admin` calls this as its first step |
| `get_service_client()` in `services/supabase.py` | All admin DB operations use service role |
| `WORKFLOW_SERVICE_SECRET` auth in `scheduled_endpoints.py` | `POST /admin/monitoring/run-check` uses identical header auth |
| `limiter` from `middleware/rate_limiter.py` | Admin routes add `@limiter.limit("30/minute")` decorators |
| `get_model()` / `get_fallback_model()` from `agents/shared.py` | AdminAgent uses these for Gemini Pro → Flash fallback |
| `PikarAgent` base class from `agents/base_agent.py` | AdminAgent extends this |
| `fetchEventSource` + `useAgentChat` pattern | `useAdminChat` is a near-copy targeting `/admin/chat` |
| Existing `/health/*` endpoints | `check_system_health` admin tool aggregates these directly |
| Existing `/approval/*` routes | Admin cross-user approval view queries same `approvals` table via service role |

### External Service Boundaries

| Service | Integration Pattern | Key Detail |
|---------|---------------------|------------|
| Sentry | Server-side proxy via httpx, `api_key_encrypted` in DB | Never expose token to frontend |
| PostHog | Server-side proxy, `api_key_encrypted` | Project ID stored in `config` JSONB column |
| CodeRabbit | Server-side proxy, `api_key_encrypted` | `repo_refs` array in `config` JSONB |
| GitHub | Server-side proxy, PAT in `api_key_encrypted` | owner/repo stored in `config` JSONB |
| Stripe | Server-side proxy, secret key in `api_key_encrypted` | Use read-only restricted key; no write ops without confirm autonomy |
| Gemini API | Existing ADK/shared.py patterns — no change | AdminAgent shares model config with all other agents |
| Cloud Scheduler | Existing GCP scheduler — add one new job | `POST /admin/monitoring/run-check`, 60s interval, `WORKFLOW_SERVICE_SECRET` auth |

### Internal Module Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| AdminAgent ↔ admin tool modules | ADK FunctionTool invocation (same process) | No HTTP; direct Python function call |
| Admin tools ↔ Supabase | `get_service_client()` synchronous queries | Same pattern as all other services |
| Admin tools ↔ Redis | Import `cache.py` directly; read circuit breaker state | Read-only from admin tools; no direct writes |
| Admin tools ↔ existing agents | Query `agent_metrics` and `telemetry` tables; no direct agent invocation | Admin does not orchestrate user agents |
| Frontend `/admin/*` ↔ backend `/admin/*` | REST + SSE over HTTPS; Admin JWT in Authorization header | Same CORS and transport as existing user-facing API |
| ImpersonationContext ↔ PersonaContext | React context wrapping (ImpersonationContext provides same interface) | PersonaContext.tsx not modified |
| `health_checker.py` ↔ internal `/health/*` endpoints | `httpx.AsyncClient` HTTP calls to own FastAPI server | Localhost calls within Cloud Run; low latency |

---

## Build Order (Phase Dependencies)

The following order respects hard dependencies. Each phase is independently deployable.

```
Phase 1 — Foundation (all subsequent phases depend on this)
  ├── supabase migration: user_roles + is_admin() + admin_agent_permissions
  │                       + admin_chat_sessions/messages + admin_audit_log
  │                       + admin_config_history
  ├── app/middleware/admin_auth.py (require_admin dependency)
  ├── app/services/encryption.py (Fernet utilities)
  ├── app/services/admin_audit.py (log_admin_action)
  ├── app/routers/admin/access.py (GET /admin/check-access for AdminGuard)
  ├── app/routers/admin/chat.py (POST /admin/chat SSE endpoint)
  ├── app/agents/admin/agent.py (AdminAgent with base tools only)
  ├── frontend/(admin)/layout.tsx (AdminGuard + sidebar + chat panel)
  └── frontend/hooks/useAdminChat.ts

Phase 2 — Monitoring (requires Phase 1 auth; depends on monitoring migration)
  ├── supabase migration: admin_integrations + api_health_checks + api_incidents
  ├── app/services/health_checker.py
  ├── app/routers/admin/monitoring.py (+ run-check Cloud Scheduler endpoint)
  ├── app/agents/admin/tools/monitoring.py (all monitoring tools)
  └── frontend/(admin)/monitoring/page.tsx

Phase 3 — Users (requires Phase 1 auth)
  ├── app/routers/admin/users.py
  ├── app/agents/admin/tools/users.py
  ├── frontend/(admin)/users/page.tsx + [id]/page.tsx
  ├── frontend/contexts/ImpersonationContext.tsx
  └── frontend/(admin)/impersonate/[userId]/page.tsx

Phase 4 — Analytics (requires Phase 1; reads existing telemetry/sessions tables)
  ├── app/routers/admin/analytics.py
  ├── app/agents/admin/tools/analytics.py
  └── frontend/(admin)/analytics/page.tsx

Phase 5 — Integrations (requires Phase 1 encryption + Phase 2 monitoring migration)
  ├── app/routers/admin/integrations.py (+ proxy routes)
  ├── app/agents/admin/tools/integrations.py (sentry/posthog/coderabbit/github tools)
  └── frontend/(admin)/integrations/page.tsx

Phase 6 — Configuration (requires Phase 1 admin_config_history table)
  ├── app/routers/admin/configuration.py
  ├── app/agents/admin/tools/configuration.py
  └── frontend/(admin)/configuration/page.tsx

Phase 7 — Approvals (requires Phase 1; reads existing approvals table)
  ├── app/routers/admin/approvals.py
  ├── app/agents/admin/tools/approvals.py
  └── frontend/(admin)/approvals/page.tsx

Phase 8 — Billing (requires Phase 5 integrations for Stripe proxy)
  ├── app/routers/admin/billing.py (Stripe proxy routes)
  ├── app/agents/admin/tools/billing.py
  └── frontend/(admin)/billing/page.tsx

Phase 9 — Permissions UI (requires Phase 1 admin_agent_permissions table)
  ├── app/routers/admin/settings.py (GET/PATCH /admin/settings/permissions)
  └── frontend/(admin)/settings/page.tsx
```

**Critical path:** Phase 1 (auth + encryption + base agent + AdminGuard) must be complete before any other phase starts. Phases 2-4 can run in parallel after Phase 1. Phase 8 (Billing) has a hard dependency on Phase 5 (Integrations) if Stripe data is sourced through the integration proxy.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Solo founder use (1-5 admin users) | Current design is correct. Single FastAPI process, no queue needed. Admin actions are low-frequency by nature. |
| Small team (5-20 admin users) | AdminAgent's 30-minute confirm session timeouts may collide. Add session_owner check to prevent two admins acting on the same confirmation card. Rate limits as-is are sufficient. |
| Enterprise multi-team admin | Out of scope per PROJECT.md. Would require: per-team role scoping in `user_roles`, multi-tenant `admin_agent_permissions`, and audit log filtering. Current schema supports extension (add `team_id` column to `user_roles`) but this is not planned. |

**First bottleneck:** Gemini API rate limits when AdminAgent is actively debugging incidents (check_system_health → check_error_logs → get_agent_metrics → run_diagnostic in sequence). Mitigation: `admin_agent_permissions` set `auto` for all read tools and the Flash fallback handles burst.

**Second bottleneck:** `api_health_checks` table growth. 60-second checks across 20+ endpoints = ~28,800 rows/day. Without pruning, this hits PostgreSQL row limits within months. The 30-day auto-prune in the monitoring migration (scheduled DELETE via pg_cron or Cloud Scheduler) is not optional.

---

## Sources

- `docs/superpowers/specs/2026-03-21-admin-panel-design.md` — Full design spec (approved, internal)
- `.planning/PROJECT.md` — Milestone context and constraints
- `app/app_utils/auth.py` — Existing JWT verification pattern (reused by require_admin)
- `app/routers/approvals.py` — Service role access pattern for sensitive data
- `app/services/scheduled_endpoints.py` — Cloud Scheduler auth pattern (model for run-check)
- `app/agents/shared.py` — Model config and retry options (reused by AdminAgent)
- `app/middleware/rate_limiter.py` — slowapi limiter instance (reused for admin routes)
- `frontend/src/hooks/useAgentChat.ts` — SSE chat hook pattern (model for useAdminChat)
- `frontend/src/contexts/PersonaContext.tsx` — Context wrapping pattern for ImpersonationContext

---

*Architecture research for: v3.0 Admin Panel integration with existing pikar-ai system*
*Researched: 2026-03-21*
