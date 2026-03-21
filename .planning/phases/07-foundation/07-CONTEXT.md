# Phase 7: Foundation - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning
**Source:** PRD Express Path (docs/superpowers/specs/2026-03-21-admin-panel-design.md)

<domain>
## Phase Boundary

This phase delivers the secure admin panel shell — authorization, the AI admin assistant chat, audit trail, Fernet encryption, and the confirmation flow. After this phase, an admin can access `/admin`, chat with the AdminAgent over SSE, see confirmation cards for dangerous actions, browse the audit log, and have chat sessions persist across page loads. No domain-specific tools (users, monitoring, analytics) are included — only the trust infrastructure and base agent.

**Requirements:** AUTH-01..05, ASST-01..06, AUDT-01..04 (15 total)

</domain>

<decisions>
## Implementation Decisions

### Authorization
- Two-layer auth: `ADMIN_EMAILS` env var (server-side only, NOT `NEXT_PUBLIC_`) OR `user_roles` DB table
- OR logic: either check grants access
- Backend: `require_admin` FastAPI dependency on all `/admin/*` routes — validates Supabase JWT, checks email against env allowlist OR queries `is_admin()` DB function
- Frontend: `AdminGuard` component in `/admin/layout.tsx` — calls server-side endpoint `GET /admin/check-access` (NOT client-side env var check)
- Non-admin redirect: server-side redirect to `/dashboard` with "Access denied" toast

### Database Schema (Supabase migration)
- `user_roles` table: id, user_id (FK auth.users), role (user/junior_admin/senior_admin/admin/super_admin), created_at, updated_at, UNIQUE(user_id)
- `is_admin()` SECURITY DEFINER function to avoid circular self-referencing RLS
- `admin_agent_permissions` table: action_category, action_name, autonomy_level (auto/confirm/blocked), risk_level, description
- `admin_chat_sessions` table: id, admin_user_id (FK), title, created_at, updated_at
- `admin_chat_messages` table: id, session_id (FK), role, content, metadata (JSONB), created_at — individual rows, NOT JSONB blob
- `admin_audit_log` table: id, admin_user_id (FK), action, target_type, target_id, details (JSONB), source (manual/ai_agent/impersonation/monitoring_loop), created_at
- `admin_config_history` table: id, config_type, config_key, previous_value (JSONB), new_value (JSONB), changed_by (FK), change_source, created_at
- `admin_integrations` table: id, provider, api_key_encrypted, base_url, config (JSONB), is_active, health_status, updated_by (FK), timestamps
- `api_health_checks` table: id, endpoint, category, status, response_time_ms, status_code, error_message, metadata, checked_at
- `api_incidents` table: id, endpoint, category, incident_type, started_at, resolved_at, auto_remediation_attempted, remediation_action, remediation_result, details, created_at
- RLS enabled on all admin tables with no policies (deny via anon — all access through service role)
- Seed `admin_agent_permissions` with defaults: reads=auto, writes=confirm, destructive=blocked

### AI Admin Assistant
- `AdminAgent` is a Google ADK agent at `app/agents/admin/agent.py` — follows existing factory pattern (like `create_financial_agent()`)
- Uses `get_model()` and `get_fallback_model()` from `app/agents/shared.py` (Gemini Pro -> Flash)
- System prompt includes: platform context, current autonomy permissions (queried from DB), available tools with risk levels, confirm instructions
- For Phase 7: only basic tools — `check_system_health` (hits existing /health/* endpoints)
- SSE streaming endpoint: `POST /admin/chat` on FastAPI
- Frontend: `useAdminChat` hook built on `@microsoft/fetch-event-source` — mirrors existing `useAgentChat`

### Autonomy Enforcement
- Autonomy tiers enforced in Python tool code, NOT in LLM system prompt
- Each tool function checks `admin_agent_permissions` table before executing
- `auto`: execute immediately, return result
- `confirm`: return `{requires_confirmation: True, confirmation_token: uuid, action_details: {...}}`
- `blocked`: return explanation, do not execute
- Confirmation tokens: UUID-based, stored in Redis with TTL, atomic single-consumption via `GETDEL` or `DELETE` with check

### Confirm Flow Frontend
- When agent returns a confirm-tier response, chat renders an action confirmation card
- Card has [Cancel] and [Confirm] buttons
- Confirm sends the `confirmation_token` back to the agent endpoint
- Backend verifies token is unused (atomic check), executes action, marks token consumed
- Double-click protection: disable Confirm button on first click + server-side single-use check

### Fernet Encryption
- `app/services/encryption.py` — MultiFernet from day one
- Encryption key in `ADMIN_ENCRYPTION_KEY` env var (comma-separated for rotation support)
- `MultiFernet([Fernet(key) for key in keys])` pattern
- Encrypt on write, decrypt on read — plaintext never returned to frontend
- Phase 7 creates the utility; Phase 5 (Integrations) will use it to store API keys

### Audit Trail
- `app/services/admin_audit.py` — `log_admin_action()` function
- Parameters: admin_user_id, action, target_type, target_id, details, source
- Source tags: 'manual' (dashboard clicks), 'ai_agent' (agent tool execution), 'impersonation' (impersonation mode), 'monitoring_loop' (automated health checks)
- admin_user_id can be NULL for monitoring_loop source
- Audit log viewer UI at `/admin/audit-log` — table with filters

### Frontend Layout
- Route group: `src/app/(admin)/` with `layout.tsx`
- Layout includes: AdminGuard, admin sidebar, persistent AI chat panel (docked bottom)
- Chat panel: collapsible (single input bar when collapsed, full chat when expanded)
- Sidebar nav: Overview, Users, Monitor, Analytics, Approvals, Config, Billing, Integrations, Settings
- Uses existing design system: Tailwind CSS 4, Lucide icons, Framer Motion, Sonner toasts
- Dark theme consistent with existing dashboard

### Backend Structure
- `app/routers/admin/` — new router package
- `app/routers/admin/__init__.py` — router registration
- `app/routers/admin/auth.py` — `GET /admin/check-access`
- `app/routers/admin/chat.py` — `POST /admin/chat` SSE endpoint
- `app/routers/admin/audit.py` — `GET /admin/audit-log`
- `app/middleware/admin_auth.py` — `require_admin` dependency
- `app/agents/admin/agent.py` — AdminAgent
- `app/agents/admin/tools/` — tool modules
- `app/services/encryption.py` — MultiFernet utilities
- `app/services/admin_audit.py` — audit logging service

### Rate Limiting
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

</decisions>

<specifics>
## Specific Ideas

- AdminAgent greeting on panel open: "All systems healthy" or "1 active incident" — health check only in Phase 7
- Proactive greeting is a fetch-on-mount that gets the latest health summary
- Admin chat input placeholder: "Ask me anything about the platform..."
- Confirmation card should show action name, target, risk level, and consequences

</specifics>

<deferred>
## Deferred Ideas

- Domain-specific agent tools (users, monitoring, analytics, integrations, config, billing, approvals) — Phases 8-15
- External integration proxy and Fernet-encrypted key storage — Phase 11
- User impersonation — Phase 9/13
- Feature flag UI — Phase 12
- Approval oversight — Phase 15
- Billing dashboard — Phase 14
- Permissions configuration UI — Phase 15

</deferred>

---

*Phase: 07-foundation*
*Context gathered: 2026-03-21 via PRD Express Path*
