# Admin Panel Design Spec

**Date:** 2026-03-21
**Status:** Approved
**Approach:** AI-First Admin (Approach 2)

## Overview

A founder-facing admin panel for Pikar-AI, centered around an AI Admin Assistant. The admin chat is powered by a dedicated Google ADK AdminAgent on the FastAPI backend, streamed to the frontend via SSE using the existing `fetchEventSource` pattern (consistent with the user-facing chat). The admin panel lives at `/admin/*` within the existing Next.js frontend, gated by a two-layer authorization system (env allowlist + database roles). The AI assistant is the primary interaction surface — dashboard pages exist for browsing and drilling into data, but the agent is how the founder gets things done.

## Core Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Location | `/admin/*` route group in existing app | Single codebase, shared layout system, simplest path |
| Primary UX | AI-first with chat as main interface | Founder efficiency — one interface to rule all domains |
| AI Provider | Google ADK AdminAgent on FastAPI, SSE via fetchEventSource | Consistent with existing chat infra, direct access to all backend services |
| Auth Layer 1 | `ADMIN_EMAILS` env var allowlist | Instant bootstrap, no migration needed |
| Auth Layer 2 | `user_roles` table with RLS | Queryable by AI agent, supports future team growth |
| Auth Logic | OR (either layer grants access) | Bootstrap via env, transition to DB roles |
| Agent Autonomy | Tiered: auto / confirm / blocked | Configurable per-action from `/admin/settings` |
| External Integrations | Server-side proxy, encrypted API keys in DB | No frontend API key exposure, UI-manageable |
| Impersonation | View + Interactive modes | Test any user's experience without separate login |
| Audit | All actions logged with source tagging | Full traceability for admin, agent, and impersonation actions |

---

## 1. Architecture & Routing

### Route Structure

```
/admin                       → Main admin view (AI chat + overview status cards)
/admin/layout.tsx            → AdminGuard, sidebar, persistent AI chat panel
/admin/users                 → User management table + filters
/admin/users/[id]            → Individual user detail + actions
/admin/monitoring            → System health dashboard (APIs, agents, infra)
/admin/analytics             → Usage dashboards, engagement, agent effectiveness
/admin/approvals             → Cross-user approval oversight
/admin/configuration         → Agent configs, feature toggles, workflow templates
/admin/billing               → Subscription management, revenue metrics
/admin/integrations          → External tool connection management
/admin/settings              → Agent autonomy permissions, admin preferences
/admin/impersonate/[userId]  → User impersonation view
```

### Layout

```
+----------------------------------------------------------+
|  Admin Header (Pikar Admin + system status indicator)     |
+-------------+--------------------------------------------+
|             |                                            |
|  Admin      |   Main Content Area                        |
|  Sidebar    |   (dashboard section or detail view)       |
|             |                                            |
|  - Overview |                                            |
|  - Users    |                                            |
|  - Monitor  |                                            |
|  - Analytics|                                            |
|  - Approvals|                                            |
|  - Config   |                                            |
|  - Billing  +--------------------------------------------+
|  - Integr.  |   AI Admin Assistant                       |
|  - Settings |   (expandable chat panel, docked bottom)   |
|             |   Collapsed: single input bar              |
|             |   Expanded: full chat with rich cards       |
+-------------+--------------------------------------------+
```

The AI assistant panel is persistent across all admin pages. It renders rich cards inline (action confirmations, data tables, charts, user profiles) rather than navigating away.

### Backend API Routes

New FastAPI routes under admin namespace:

- `POST /admin/chat` — AI assistant SSE streaming endpoint
- `GET/PATCH /admin/users`, `GET /admin/users/{id}` — User CRUD
- `GET /admin/monitoring/health` — Aggregated system health
- `GET /admin/monitoring/agents` — Agent performance metrics
- `GET /admin/monitoring/api-health` — API health check results
- `GET /admin/monitoring/incidents` — Active/resolved incidents
- `GET /admin/analytics/*` — Usage and engagement data
- `GET/POST /admin/configuration/*` — Agent config, feature flags, workflow CRUD
- `GET/POST /admin/integrations/*` — Integration management + proxy to external APIs
- `GET /admin/approvals` — Cross-user approval listing
- `POST /admin/approvals/{id}/override` — Admin override
- `GET /admin/billing/*` — Revenue and subscription data
- `GET /admin/audit-log` — Audit trail query

All endpoints guarded by `require_admin` FastAPI dependency.

---

## 2. Authorization Layer

### Layer 1: Environment Variable Gate

```
ADMIN_EMAILS=founder@example.com,cofounder@example.com
```

Checked server-side only (never exposed to the frontend bundle).

### Layer 2: Database Role

```sql
CREATE TABLE user_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin', 'super_admin')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id)
);

ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;

-- Use a SECURITY DEFINER function to avoid circular self-referencing RLS
CREATE OR REPLACE FUNCTION is_admin(check_user_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM user_roles
    WHERE user_id = check_user_id
    AND role IN ('admin', 'super_admin')
  );
$$;

CREATE POLICY "Admins can read user_roles" ON user_roles
  FOR SELECT USING (is_admin(auth.uid()));

CREATE POLICY "Super admins can modify user_roles" ON user_roles
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM user_roles
      WHERE user_id = auth.uid() AND role = 'super_admin'
    )
  );
```

### Frontend AdminGuard

Wraps `/admin/layout.tsx`:
1. Check Supabase session exists
2. Call server-side API endpoint `GET /admin/check-access` which checks email against `ADMIN_EMAILS` env var (server-side only, NOT `NEXT_PUBLIC_`) and queries `user_roles` table
3. Either check passes = allow (OR logic)
4. Neither passes = redirect to `/dashboard` with "Access denied" toast

**Security note:** The `ADMIN_EMAILS` env var must NOT use the `NEXT_PUBLIC_` prefix — it is only read server-side to prevent leaking admin email addresses in the client bundle.

### Backend require_admin Dependency

FastAPI dependency injected on all `/admin/*` routes:
1. Validate Supabase JWT from Authorization header
2. Extract email and user_id
3. Check env allowlist OR query user_roles
4. Return 403 if neither passes

---

## 3. AI Admin Assistant

### Architecture

```
User Input -> fetchEventSource('/admin/chat') (frontend, same pattern as useAgentChat)
                |
                v
              POST /admin/chat (FastAPI endpoint)
                |
                +-- require_admin dependency (auth check)
                +-- Load autonomy permissions from admin_agent_permissions
                +-- Build system prompt with permissions + platform context
                +-- Invoke AdminAgent (Google ADK agent with Gemini model)
                +-- AdminAgent has 30+ FunctionTool definitions organized by domain
                +-- Each tool checks autonomy level before execution
                +-- SSE stream response back to frontend
                +-- Frontend renders via existing SSE message/widget pattern
```

The AdminAgent is a new Google ADK agent (`app/agents/admin/agent.py`) following the same pattern as the existing specialized agents. It uses the existing Gemini model config with fallback (Pro -> Flash). The frontend consumes the SSE stream using a new `useAdminChat` hook built on `@microsoft/fetch-event-source`, consistent with the existing `useAgentChat` hook.

**Why ADK + FastAPI instead of a separate AI SDK setup:** The admin agent needs direct access to Supabase (service role), Redis, agent metrics, and all backend services. Running the AI in the Python backend avoids cross-service HTTP calls for every tool invocation and keeps all AI infrastructure in one place.

### System Prompt

Includes at each request:
- Platform context (what Pikar-AI is, agent hierarchy, architecture)
- Current autonomy permissions (fetched from `admin_agent_permissions`)
- Available tools with risk levels
- Instructions for propose-and-confirm on `confirm`-level actions
- Current system health summary (proactive awareness)

### Autonomy Configuration

```sql
CREATE TABLE admin_agent_permissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  action_category TEXT NOT NULL,
  action_name TEXT NOT NULL,
  autonomy_level TEXT NOT NULL DEFAULT 'confirm'
    CHECK (autonomy_level IN ('auto', 'confirm', 'blocked')),
  risk_level TEXT NOT NULL DEFAULT 'medium'
    CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
  description TEXT,
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(action_category, action_name)
);
```

Levels:
- **auto** — execute immediately, report result
- **confirm** — propose action card in chat, wait for admin click
- **blocked** — agent cannot perform, explains why

Defaults: reads = auto, writes = confirm, destructive = blocked.
Configurable from `/admin/settings`.

### Confirm Flow UX

When agent invokes a `confirm`-level tool, the chat renders:

```
+------------------------------------------+
| Action Requires Confirmation              |
|                                          |
| Suspend user jane@example.com            |
| Reason: Reported for spam activity       |
|                                          |
| This will immediately disable their      |
| access to all Pikar-AI services.         |
|                                          |
|   [Cancel]              [Confirm]        |
+------------------------------------------+
```

Confirm sends approval to agent. Cancel aborts. Logged to audit trail either way.

### Conversation Persistence

```sql
CREATE TABLE admin_chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_user_id UUID REFERENCES auth.users(id),
  title TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE admin_chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES admin_chat_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
  content TEXT NOT NULL,
  metadata JSONB,                      -- tool calls, confirmation cards, etc.
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_chat_messages_session
  ON admin_chat_messages(session_id, created_at ASC);
```

Messages stored as individual rows (not a single JSONB blob) to avoid write amplification on long conversations and enable partial loading/querying. Sessions persist across page loads. Agent can reference previous conversations.

### Proactive Behavior

On admin panel open, agent greets with:
- System health summary ("All systems healthy" or "1 active incident")
- Pending items ("3 approvals waiting, 2 Sentry issues since yesterday")
- Any anomalies detected since last visit

### Complete Tool Inventory

**User Management:**

| Tool | Default Autonomy | Description |
|------|-----------------|-------------|
| list_users | auto | Search/filter users with pagination |
| get_user_detail | auto | Full user profile, persona, activity |
| suspend_user | confirm | Disable a user account |
| unsuspend_user | confirm | Re-enable a user account |
| delete_user | blocked | Permanently delete a user |
| change_user_persona | confirm | Switch a user's persona tier |
| impersonate_user | confirm | Open impersonation view for a user |

**System Monitoring:**

| Tool | Default Autonomy | Description |
|------|-----------------|-------------|
| check_system_health | auto | Aggregate all /health/* endpoints |
| get_agent_metrics | auto | Token usage, response times, error rates per agent |
| get_redis_status | auto | Circuit breaker state, cache hit rates |
| get_active_sessions | auto | Current active user sessions |
| restart_cache | confirm | Flush and reinitialize Redis cache |

**API Health & Self-Healing:**

| Tool | Default Autonomy | Description |
|------|-----------------|-------------|
| get_api_health_summary | auto | Status of all monitored endpoints |
| get_api_health_history | auto | Trend data for an endpoint (24h/7d/30d) |
| get_active_incidents | auto | All unresolved API incidents |
| get_incident_detail | auto | Full timeline and context |
| run_diagnostic | auto | Deep check on a specific endpoint |
| check_error_logs | auto | Recent backend error logs by endpoint/agent |
| check_rate_limits | auto | Rate limit status for Gemini, Supabase, external APIs |
| toggle_endpoint | confirm | Temporarily disable/enable an endpoint |
| switch_model_fallback | confirm | Trigger Gemini Pro -> Flash fallback |
| flush_cache_for_endpoint | confirm | Clear cached responses for an endpoint |
| restart_service | confirm | Restart a backend service/worker |
| rollback_agent_config | confirm | Revert agent config to previous version |

**External Integrations:**

| Tool | Default Autonomy | Description |
|------|-----------------|-------------|
| sentry_get_issues | auto | Fetch recent Sentry errors |
| sentry_get_issue_detail | auto | Stack trace, affected users |
| sentry_resolve_issue | confirm | Mark Sentry issue resolved |
| posthog_query_events | auto | Query PostHog events/metrics |
| posthog_get_insights | auto | Fetch saved PostHog insights |
| posthog_create_annotation | confirm | Add PostHog timeline annotation |
| coderabbit_get_reviews | auto | Recent code review summaries |
| coderabbit_get_pr_review | auto | Specific PR review details |
| github_list_prs | auto | Recent pull requests |
| github_get_pr_status | auto | PR checks and status |

**Analytics:**

| Tool | Default Autonomy | Description |
|------|-----------------|-------------|
| get_usage_stats | auto | DAU, MAU, messages, workflows |
| get_agent_effectiveness | auto | Success rates, satisfaction per agent |
| get_engagement_report | auto | Feature adoption, retention |
| generate_report | auto | Summary report for date range |

**Configuration:**

| Tool | Default Autonomy | Description |
|------|-----------------|-------------|
| list_agent_configs | auto | Current agent instructions/settings |
| update_agent_instructions | confirm | Modify agent system prompt |
| toggle_feature | confirm | Enable/disable feature flag |
| list_workflow_templates | auto | Available workflow templates |
| update_workflow_template | confirm | Modify a workflow template |

**Billing:**

| Tool | Default Autonomy | Description |
|------|-----------------|-------------|
| get_revenue_metrics | auto | MRR, churn, LTV, plan distribution |
| get_user_subscription | auto | User's billing status |
| change_user_plan | confirm | Upgrade/downgrade user plan |
| issue_refund | confirm | Process a refund |

**Approvals:**

| Tool | Default Autonomy | Description |
|------|-----------------|-------------|
| list_all_approvals | auto | Cross-user pending/completed approvals |
| get_approval_detail | auto | Full approval request context |
| override_approval | confirm | Admin override on approval decision |

---

## 4. Admin Impersonation

### Modes

- **View Mode** (default): See user's dashboard exactly as they see it. Read-only — no interactions.
- **Interactive Mode** (confirm to enter): Full interaction — send messages, trigger workflows, test the complete UX as that user.

### Implementation

**Frontend:**
- `/admin/impersonate/[userId]` route wraps existing persona layouts
- `ImpersonationContext` provider overrides `PersonaContext` with target user's persona/data
- Persistent banner at top: "Viewing as: user@example.com (startup) [Exit] [Switch to Interactive]"
- Interactive mode requires explicit confirmation click

**Backend:**
- Admin endpoints accept optional `X-Impersonate-User-Id` header
- When present + requester is verified admin, data is scoped to target user
- All impersonation actions logged to `admin_audit_log`
- Interactive mode actions tagged separately in audit trail

**Impersonation Security Rules:**
- Admins cannot impersonate `super_admin` users
- Interactive mode requires `super_admin` role (view mode available to all admins)
- Impersonation sessions auto-expire after 30 minutes (configurable)
- Rate limit: max 10 impersonation sessions per hour per admin
- Impersonation of the same user by the admin who is currently impersonating is blocked (no nesting)

**AI Agent Integration:**
- Agent can invoke `impersonate_user` tool to open impersonation view
- Agent can query "what does user X see on their dashboard" by pulling their scoped data

---

## 5. External Integrations

### Storage

```sql
CREATE TABLE admin_integrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL UNIQUE,
  api_key_encrypted TEXT NOT NULL,     -- encrypted with Fernet (see Encryption Strategy below)
  base_url TEXT,
  config JSONB DEFAULT '{}',
  is_active BOOLEAN DEFAULT true,
  last_health_check TIMESTAMPTZ,
  health_status TEXT DEFAULT 'unknown',
  updated_by UUID REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### Encryption Strategy

API keys are encrypted at the application layer using **Fernet symmetric encryption** (from the `cryptography` Python package, already a transitive dependency):

- **Encryption key:** Stored in `ADMIN_ENCRYPTION_KEY` environment variable (generated via `Fernet.generate_key()`, 32-byte URL-safe base64)
- **Encrypt on write:** When an admin saves an API key, the backend encrypts it with Fernet before storing in the `api_key_encrypted` column
- **Decrypt on read:** When the backend needs to call an external API, it decrypts the key in memory, uses it, and never returns the decrypted value to the frontend
- **Frontend display:** Shows only `****...last4` of the key, never the full value
- **Key rotation:** To rotate the encryption key, a migration script re-encrypts all stored keys with the new key. Old key kept in `ADMIN_ENCRYPTION_KEY_PREVIOUS` temporarily for rollback.
- **Production:** For Google Cloud Run deployment, the encryption key should be stored in Secret Manager and injected as an env var

API keys managed from `/admin/integrations` UI — no redeployment needed.

### Supported Providers

| Provider | Config Fields | Capabilities |
|----------|--------------|--------------|
| Sentry | org_slug, project_slug, auth_token | Issues, stacktraces, resolve, release health, performance |
| PostHog | project_id, personal_api_key | Events, insights, dashboards, feature flags, annotations |
| CodeRabbit | api_key, repo_refs | PR reviews, summaries, code quality trends |
| GitHub | PAT, owner/repo | PRs, checks, issues, deployment status |
| Stripe | secret_key (read-only recommended) | Subscriptions, MRR, charges, refunds |

### Proxy Pattern

All external API calls go through FastAPI backend:

```
Frontend -> /admin/api/integrations/{provider}/{path}
              |-- require_admin middleware
              |-- Fetch + decrypt API key from admin_integrations
              |-- Call external API
              |-- Transform response to internal format
              |-- Return to frontend
```

### Health Monitoring

Background task pings each integration API periodically. Health status shown on integrations page and available to AI agent.

---

## 6. API Health Monitoring & Self-Healing

### What's Monitored

1. **Internal APIs**: All FastAPI endpoints, /health/*, agent tool endpoints
2. **External Providers**: Gemini API, Supabase, Redis, MCP integrations
3. **External Integrations**: Sentry, PostHog, CodeRabbit, GitHub, Stripe

### Data Model

```sql
CREATE TABLE api_health_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  endpoint TEXT NOT NULL,
  category TEXT NOT NULL,             -- 'internal', 'provider', 'integration'
  status TEXT NOT NULL,               -- 'healthy', 'degraded', 'down', 'timeout'
  response_time_ms INTEGER,
  status_code INTEGER,
  error_message TEXT,
  metadata JSONB,
  checked_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_health_checks_endpoint_time
  ON api_health_checks(endpoint, checked_at DESC);

CREATE TABLE api_incidents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  endpoint TEXT NOT NULL,
  category TEXT NOT NULL,
  incident_type TEXT NOT NULL,        -- 'down', 'degraded', 'error_spike', 'latency_spike'
  started_at TIMESTAMPTZ DEFAULT now(),
  resolved_at TIMESTAMPTZ,
  auto_remediation_attempted BOOLEAN DEFAULT false,
  remediation_action TEXT,
  remediation_result TEXT,            -- 'success', 'failed', 'escalated'
  details JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### Monitoring Loop

Runs via **Cloud Scheduler** (consistent with existing `scheduled_endpoints.py` pattern):

- Cloud Scheduler triggers `POST /admin/monitoring/run-check` every 60s
- Endpoint is authenticated via `WORKFLOW_SERVICE_SECRET` header (same pattern as existing scheduled endpoints)
- The handler pings all monitored endpoints, records to `api_health_checks`
- Detects anomalies: status changes, response time > 2x rolling avg, error rate > 5%, rate limit approaching
- If anomaly detected: creates `api_incident`, stores for AI agent to surface on next admin panel visit
- Critical incidents (multiple systems down) trigger email notification via existing email infrastructure
- Health check records auto-pruned after 30 days to prevent unbounded table growth

### Self-Healing Actions

| Incident | Agent Response | Autonomy |
|----------|---------------|----------|
| Redis connection lost | Check circuit breaker, attempt reconnect, verify fallback | auto |
| Gemini rate limited | Check quota, switch to Flash fallback, report | auto |
| Internal 5xx spike | Query logs, identify pattern, correlate with deploys | auto |
| Supabase timeout | Check status page, verify pool, test query | auto |
| Agent tool failing | Disable tool temporarily, notify admin, suggest fix | confirm |
| Integration unreachable | Mark degraded, retry with backoff, notify | auto |
| Multiple systems down | Aggregate findings into incident report, propose plan | confirm |

### Proactive Notifications

- On admin panel open: agent greets with status summary
- Critical incidents: email notification to admin email
- Approaching rate limits: early warning in chat

---

## 7. Audit Trail

```sql
CREATE TABLE admin_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_user_id UUID REFERENCES auth.users(id),
  action TEXT NOT NULL,
  target_type TEXT,
  target_id TEXT,
  details JSONB,
  source TEXT NOT NULL DEFAULT 'manual',  -- 'manual' | 'ai_agent' | 'impersonation'
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_audit_log_admin_time
  ON admin_audit_log(admin_user_id, created_at DESC);

CREATE INDEX idx_audit_log_action
  ON admin_audit_log(action, created_at DESC);
```

Every admin action is logged: manual dashboard actions, AI agent executions, and impersonation-mode interactions. Queryable from the AI agent and visible in a log viewer at `/admin/audit-log`.

---

## 8. Dashboard Sections

### Users (/admin/users)
- Searchable/filterable table: name, email, persona, signup date, last active, status
- User detail: profile, chat history count, workflows run, agent usage, subscription
- Actions: suspend, unsuspend, change persona, impersonate
- Bulk: CSV export, bulk email

### Monitoring (/admin/monitoring)
- Real-time status grid: internal endpoints + external providers with response times
- Active incidents panel with agent remediation status
- Response time trend sparklines (24h)
- Circuit breaker and rate limit status

### Analytics (/admin/analytics)
- KPI cards: DAU, MAU, messages, workflows, avg session duration
- Charts: user growth, messages/day, agent usage distribution, feature adoption
- Retention: cohort analysis (week-over-week)
- Agent effectiveness: per-agent success rate, response time, satisfaction

### Approvals (/admin/approvals)
- Cross-user approval view with status filters
- Admin override with reason field
- Metrics: avg approval time, rate by agent, overdue count

### Configuration (/admin/configuration)
- Agent config editor (instructions, model, retry settings)
- Feature flag toggles
- Workflow template management
- All changes versioned with rollback capability

```sql
CREATE TABLE admin_config_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  config_type TEXT NOT NULL,
  config_key TEXT NOT NULL,
  previous_value JSONB,
  new_value JSONB,
  changed_by UUID REFERENCES auth.users(id),
  change_source TEXT DEFAULT 'manual',
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### Billing (/admin/billing)
- Revenue: MRR, ARR, churn, LTV, ARPU
- Plan distribution chart
- Transaction table (from Stripe when connected)
- User billing lookup

### Integrations (/admin/integrations)
- Connection cards per provider with status indicators
- Configure modal: API key, base URL, provider-specific config
- Per-integration detail: recent API calls, health, usage

---

## 9. Phasing Plan

| Phase | Scope | AI Agent Gains |
|-------|-------|---------------|
| 1. Foundation | Auth (env gate + user_roles + is_admin()), /admin layout, sidebar, AdminGuard (server-side check), audit log, encryption utils, AI chat via ADK AdminAgent + fetchEventSource, config history table | Base conversation, check_system_health |
| 2. Monitoring | API health checks, /admin/monitoring, incident detection, health tables | All monitoring + diagnostic + self-healing tools |
| 3. Users | /admin/users table + detail, impersonation, suspend/unsuspend | User management tools, impersonate_user |
| 4. Analytics | /admin/analytics, KPI cards, charts, agent effectiveness | Analytics query tools, generate_report |
| 5. Integrations | /admin/integrations UI, Sentry + PostHog + CodeRabbit + GitHub proxy | All external integration tools |
| 6. Configuration | /admin/configuration, agent config editor, feature flags, workflow templates, versioning | Config tools, rollback_agent_config |
| 7. Approvals | /admin/approvals cross-user view, admin override | Approval tools, override_approval |
| 8. Billing | /admin/billing dashboard, Stripe integration | Billing tools, revenue metrics |
| 9. Permissions UI | /admin/settings, autonomy tier config, per-action permission editor | Self-aware permission management |

Each phase is independently deployable. The AI agent gains capabilities incrementally as each domain is built.

---

## 10. RLS & Access Control for Admin Tables

All admin tables are accessed via the **Supabase service role client** on the backend (bypassing RLS), since admin endpoints are already gated by the `require_admin` FastAPI dependency. This is consistent with the existing codebase pattern (e.g., `approvals.py` uses service role).

RLS is still enabled on all admin tables as a defense-in-depth measure, with policies that block all access via the anon key:

```sql
-- Applied to all admin tables: admin_agent_permissions, admin_chat_sessions,
-- admin_chat_messages, admin_integrations, api_health_checks, api_incidents,
-- admin_audit_log, admin_config_history
ALTER TABLE <table_name> ENABLE ROW LEVEL SECURITY;

-- No policies = deny all access via anon/authenticated roles
-- All access goes through service role (bypasses RLS)
```

The `user_roles` table is the exception — it has explicit RLS policies (see Section 2) because it may be queried from the frontend auth check flow.

---

## 11. Rate Limiting

Admin endpoints use `slowapi` rate limiting consistent with the existing codebase:

| Endpoint Category | Rate Limit | Rationale |
|-------------------|-----------|-----------|
| `POST /admin/chat` | 30 requests/minute | AI chat can be chatty; prevents runaway token usage |
| `GET /admin/*` (read endpoints) | 120 requests/minute | Dashboard browsing, polling |
| `POST/PATCH /admin/*` (write endpoints) | 30 requests/minute | Mutations should be deliberate |
| `/admin/integrations/*/proxy/*` | 60 requests/minute | Prevents amplifying requests to external APIs |
| `POST /admin/monitoring/run-check` | 2 requests/minute | Cloud Scheduler only, prevent abuse |

---

## 12. Testing Strategy

Each phase includes tests consistent with existing project standards:

- **Auth guard tests**: Unit tests for `require_admin` dependency (valid admin, invalid user, expired token, missing role)
- **AI agent tool tests**: Mock Supabase/Redis, verify tool execution, autonomy level enforcement, confirm flow
- **Impersonation tests**: Verify data scoping, audit logging, session expiry, privilege escalation prevention
- **Integration proxy tests**: Mock external APIs, verify error handling, key decryption, response transformation
- **API health check tests**: Mock endpoint responses, verify anomaly detection, incident creation
- **Frontend tests**: AdminGuard redirect behavior, chat rendering, confirmation card interactions

All tests run via `uv run pytest tests/unit/admin/` and `uv run pytest tests/integration/admin/`.

---

## 13. Admin Session Management

- Admin sessions inherit the Supabase auth session but with stricter controls:
  - Admin session timeout: 4 hours (shorter than regular user sessions)
  - Activity-based extension: session refreshes on each admin action
  - Forced logout: super_admin can revoke another admin's active sessions via the AI agent or UI
  - Active sessions visible in `/admin/settings` for audit

---

## Technical Stack

- **Frontend**: Next.js 16 App Router, React 19, Tailwind CSS 4, Framer Motion, Lucide icons, Sonner toasts (consistent with existing app)
- **AI Assistant**: Google ADK AdminAgent on FastAPI, Gemini Pro with Flash fallback, SSE streaming via `fetchEventSource` (consistent with existing chat)
- **Backend**: FastAPI, async Python, existing Supabase + Redis infra
- **Database**: Supabase PostgreSQL, service role access for admin tables, new tables for admin domain
- **External APIs**: Server-side proxy pattern, Fernet-encrypted key storage
- **Monitoring**: Cloud Scheduler for health check loop (existing pattern)
- **Rate Limiting**: slowapi (existing pattern)
- **Encryption**: Fernet symmetric encryption for API keys, key in env var / Secret Manager

## New Database Tables Summary

1. `user_roles` — admin/super_admin role assignments (with RLS + `is_admin()` function)
2. `admin_agent_permissions` — per-action autonomy configuration
3. `admin_chat_sessions` — AI assistant session metadata
4. `admin_chat_messages` — individual chat messages (normalized, not JSONB blob)
5. `admin_integrations` — external tool API key storage (Fernet encrypted)
6. `api_health_checks` — endpoint health check results (auto-pruned after 30 days)
7. `api_incidents` — detected incidents and remediation tracking
8. `admin_audit_log` — all admin action logging
9. `admin_config_history` — configuration change versioning

## Phasing Dependencies

While each phase is independently deployable, these dependencies must be respected:

- Phase 1 establishes: auth infrastructure, encryption utilities, audit log, base admin agent — all subsequent phases depend on this
- Phase 1 also establishes the config history table (needed by Phase 6's rollback, but general enough to use from Phase 1)
- Phase 5 (Integrations) requires the encryption utilities from Phase 1
- Phase 9 (Permissions UI) could optionally be moved to Phase 2 if fine-grained autonomy control is needed early; default permissions work without UI for initial phases
