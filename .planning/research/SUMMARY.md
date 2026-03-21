# Project Research Summary

**Project:** Pikar-AI v3.0 — AI-First Admin Panel
**Domain:** AI-augmented internal admin panel for a multi-agent SaaS platform
**Researched:** 2026-03-21
**Confidence:** HIGH

## Executive Summary

The admin panel is an internal-only feature for the solo founder running the Pikar-AI platform. It is not a new product — it is a structured layer added on top of a well-established FastAPI + Google ADK + Next.js codebase. The core premise is "ask, don't click": a persistent AI chat panel backed by a new `AdminAgent` (Google ADK) replaces the current workflow of ad hoc Supabase SQL queries and manual `/health/*` endpoint polling. The research confirms that the existing stack handles every requirement cleanly: no significant new infrastructure is needed, just four minimal new packages (`httpx`, `posthog`, `sentry-sdk`, `PyGithub`) and two new frontend libraries (`recharts@^3.8.0`, `@tanstack/react-table@^8.21.3`).

The recommended architecture is an additive layer: a new `(admin)/` Next.js route group with server-side `AdminGuard`, a new `app/routers/admin/` FastAPI router package (all routes gated by a `require_admin` dependency), a new `app/agents/admin/` ADK agent with 30+ tools across seven domains, and three new support services (Fernet encryption, audit logger, health checker). Critically, the twelve existing infrastructure components — SSE streaming, JWT auth, Redis circuit breaker, Supabase client, Cloud Scheduler pattern, rate limiting — are reused unchanged. The AdminAgent is structurally identical to the existing 10 specialized agents; no ADK configuration changes are required.

The primary risk is not technical complexity but trust architecture. The admin agent can take real-world actions (suspend users, issue refunds, modify agent instructions). Research identifies ten concrete pitfalls, with four that must be resolved in Phase 1 before any other work begins: Python-enforced autonomy tiers (not LLM-enforced), idempotent confirmation tokens, MultiFernet key rotation support baked in from day one, and audit log schema that accommodates system-source actions. Missing any of these in the foundation phase creates expensive retrofits and, in the worst cases, unrecoverable security or data loss scenarios.

---

## Key Findings

### Recommended Stack

The existing stack requires only minimal additions. `cryptography` (Fernet) is already a direct dependency. The four new Python packages extend existing capabilities: `httpx` for async health monitoring (consistent with FastAPI's own patterns), `posthog` and `sentry-sdk` for server-side API proxy tools, and `PyGithub` for typed GitHub API access (note: PyGithub is synchronous and must be wrapped with `asyncio.to_thread()`). On the frontend, `recharts@^3.8.0` (not 2.x) is required because 3.x has native React 19 support and TypeScript generics that prevent runtime errors in admin dashboard charts; `@tanstack/react-table@^8.21.3` provides headless server-side pagination for user management tables.

What NOT to add is as important as what to add. `shadcn/ui`, Tremor, `react-query`, `ag-grid-react`, Celery, Alembic, and WebSocket libraries were all evaluated and rejected — each adds either infrastructure complexity that conflicts with existing patterns or is over-engineering for a founder-only panel.

**Core new technologies:**
- `httpx~=0.28.1`: Async HTTP client for health monitoring concurrent pings — consistent with FastAPI, superior ergonomics to aiohttp
- `recharts@^3.8.0`: React 19 native charts for analytics dashboards and monitoring sparklines — 3.x required, not 2.x
- `@tanstack/react-table@^8.21.3`: Headless server-side paginated tables for user management and audit log — pairs with existing Tailwind CSS 4
- `posthog~=7.9.12` + `sentry-sdk~=2.53.0` + `PyGithub~=2.8.1`: API proxy clients for external integration tools in the AdminAgent

### Expected Features

The feature set is organized into three priority tiers, anchored to a clear dependency graph. Auth gate is required by everything; audit trail is required by impersonation and agent accountability; Fernet utilities are required by all integrations.

**Must have for launch (P1 — Phases 1-3):**
- Admin auth gate (two-layer: `ADMIN_EMAILS` env OR `user_roles` DB table) — no admin feature is safe without this
- AI Admin Assistant with confirm-before-execute flow — core premise of the panel
- Audit trail with source tagging (`manual` / `ai_agent` / `impersonation` / `monitoring_loop`) — required by impersonation security model
- API health monitoring loop + dashboard — highest operational value after auth; replaces manual health polling
- User management (search, suspend/unsuspend, persona switch) + impersonation view mode — replaces direct Supabase queries for support actions
- Fernet encryption utilities — required by all external integrations built later

**Should have after validation (P2 — Phases 4-6):**
- Usage analytics dashboards (DAU/MAU, messages, workflows, per-agent effectiveness)
- External integrations (Sentry, PostHog, CodeRabbit, GitHub) with server-side proxy
- Agent config editor with full before/after diff display and one-click rollback

**Defer to future (P3 — Phases 7-9+):**
- Cross-user approval oversight and admin override
- Billing / revenue dashboard (Stripe)
- Tiered autonomy permissions UI (defaults cover solo-founder phase; UI is for later customization)
- Retention cohort analysis (needs 3+ months of user data to be meaningful)
- Proactive greeting with full multi-domain state (scaffolded early, enriched later)

**Anti-features confirmed off-scope:**
- Real-time WebSocket monitoring (SSE + 30s polling is indistinguishable at this scale)
- Mobile-first admin UI (destructive actions require deliberate desktop interaction)
- AI-generated code deployments from admin chat (catastrophic blast radius)
- Decrypted API keys anywhere in browser (XSS exposure)

### Architecture Approach

The admin panel is built as a first-class additive layer — not a workaround or a side panel bolted onto existing routes. It follows all five existing architectural patterns: the Next.js `(personas)/` route group pattern (mirrored as `(admin)/`), the ADK specialized agent factory pattern (AdminAgent is peer to the 10 existing agents), the `useAgentChat` SSE streaming pattern (mirrored as `useAdminChat`), the Cloud Scheduler + `WORKFLOW_SERVICE_SECRET` pattern (reused for the 60-second health check loop), and the `PersonaContext` pattern (wrapped by `ImpersonationContext` for impersonation sessions).

The database layer adds 9 new admin tables via two Supabase migration files. Existing tables are read but never structurally modified. All admin DB access uses the service role client that bypasses RLS, consistent with the existing `approvals.py` router pattern. A single `require_admin` FastAPI dependency gates every `/admin/*` endpoint, declared once and injected across all admin router files.

**Major components:**
1. `app/middleware/admin_auth.py` — `require_admin` FastAPI dependency: JWT verification + ADMIN_EMAILS env OR `is_admin()` DB function; gates all admin routes
2. `app/agents/admin/agent.py` + `app/agents/admin/tools/` — AdminAgent with 30+ FunctionTools across seven domains (users, monitoring, integrations, analytics, configuration, billing, approvals); autonomy check at each tool's Python boundary
3. `app/services/encryption.py` — MultiFernet encrypt/decrypt for API keys; key from `ADMIN_ENCRYPTION_KEY` env var; plaintext never returned to frontend
4. `app/services/admin_audit.py` — `log_admin_action()` writes source-tagged rows to `admin_audit_log`; NULL-safe for system-source actions
5. `app/services/health_checker.py` — Concurrent endpoint pinging via `asyncio.gather()` + `httpx`; writes to `api_health_checks`; creates `api_incidents`; writes directly to Supabase (not through monitored service)
6. `app/routers/admin/` — 10-file router package, one file per domain; all depend on `require_admin`
7. `frontend/src/app/(admin)/layout.tsx` — AdminGuard (server-side redirect) + sidebar + persistent chat panel
8. `frontend/src/contexts/ImpersonationContext.tsx` — Wraps PersonaContext; adds non-dismissible impersonation banner; auto-expires at 30 minutes

### Critical Pitfalls

Ten pitfalls were identified. The five most critical, with required prevention strategies:

1. **Prompt injection bypasses confirmation flow** — Enforce autonomy tiers in Python tool code, never in LLM system prompt. The confirmation gate is a `if autonomy == "confirm": return {requires_confirmation: True}` check in every tool function, not a prompt instruction. Wrap all external data in `<untrusted_data>` delimiters in agent context.

2. **Env-var auth path has no revocation mechanism** — Log every env-path access grant with `source: "env_allowlist"` in the audit trail. Display a UI warning once the first `user_roles` row exists: "Env-based admin emails are still active." For destructive actions, require DB role regardless of which path granted access.

3. **Single Fernet key rotation destroys all stored credentials** — Use `MultiFernet([new_key, old_key])` from day one. Build `scripts/rotate_encryption_key.py` before Phase 5 stores any live API keys. Support comma-separated `ADMIN_ENCRYPTION_KEY` in env.

4. **Duplicate confirmation execution via double-click or SSE reconnect** — Generate a UUID `confirmation_token` for each pending action. Backend enforces single-consumption via atomic `UPDATE ... WHERE consumed = false` (check rows affected = 1). Disable Confirm button optimistically on first click.

5. **Health monitoring loop cannot observe its own failures** — Write health check results directly to Supabase (not through the monitored FastAPI service). Emit a `CRITICAL` Cloud Logging entry if the write fails. Show a "monitoring data may be stale" banner in the admin UI if the most recent `api_health_checks` row is more than 5 minutes old.

Additional pitfalls to address in their respective phases: impersonation audit contamination (Phase 3), impersonation auth-state escape (Phase 3), config editor instruction injection (Phase 6), external API proxy rate exhaustion (Phase 5), and automated monitoring loop audit gaps (Phase 2 schema review).

---

## Implications for Roadmap

### Suggested Phase Structure

Research confirms a clear dependency order. Auth and trust infrastructure must be complete before any tools are built. Monitoring (the next highest operational value) follows. User management + impersonation is a natural third unit. Analytics and integrations are additive after core is validated.

### Phase 1: Foundation — Auth, Agent Shell, Audit Trail, Encryption

**Rationale:** Every subsequent feature depends on these four capabilities. The `require_admin` dependency gates all routes. The AdminAgent tool architecture (Python-enforced autonomy, confirmation token pattern) must be established before any tools are built or the trust model is unfixable without rewriting all tools. Fernet MultiFernet must be in from day one — it cannot be added after integrations store live keys without a data migration. Config history schema (a freebie at migration time) unblocks Phase 6 rollback at zero cost.

**Delivers:** Secure admin gate (frontend + backend), AdminAgent SSE chat with health check tools only, audit log table + viewer, Fernet encryption utilities, confirmation card UI, admin_chat_sessions persistence, Supabase migration files (both foundation + monitoring tables).

**Addresses:** Admin auth gate, AI Admin Assistant (base), Audit trail, Confirm-before-execute flow, Fernet encryption utilities

**Avoids:** Pitfall 1 (prompt injection), Pitfall 2 (env-auth bypass), Pitfall 3 (Fernet key loss), Pitfall 8 (duplicate confirmation)

**Research flag:** Standard patterns — no additional research needed. All patterns directly derived from existing codebase.

---

### Phase 2: Health Monitoring Dashboard

**Rationale:** Highest operational value after auth. Replaces current manual polling of `/health/*` endpoints. Uses the existing Cloud Scheduler pattern unchanged. The audit log schema must be validated before this phase writes system-source rows.

**Delivers:** `health_checker.py` service, `POST /admin/monitoring/run-check` Cloud Scheduler endpoint, monitoring dashboard (`/admin/monitoring`), sparkline charts (recharts), real-time health aggregation, incident detection and creation, stale-data warning banner.

**Addresses:** API health monitoring loop + dashboard, basic system health overview

**Avoids:** Pitfall 5 (circular health monitoring), Pitfall 10 (audit log missing system-source rows) — requires Phase 1 audit schema to support NULL admin_user_id for `monitoring_loop` source

**Uses:** `httpx` + `asyncio.gather()` for concurrent pings, `recharts` for sparklines, existing Cloud Scheduler + `WORKFLOW_SERVICE_SECRET` pattern

**Research flag:** Standard patterns — well-documented. Cloud Scheduler pattern exists in codebase.

---

### Phase 3: User Management + Impersonation (View Mode)

**Rationale:** The second most common founder support action (after health monitoring) is looking up and managing users. Impersonation view mode replaces "ask user for a screenshot." Both features share the user search infrastructure and the `ImpersonationContext`. The impersonation allow-list and auth-state escape blocklist must be defined here, before interactive mode is considered.

**Delivers:** User table with search/filter/pagination (`@tanstack/react-table`), suspend/unsuspend/persona-switch actions, user detail page, `ImpersonationContext` with non-dismissible banner, view-mode impersonation at `/admin/impersonate/[userId]`, impersonation session tagging in audit log.

**Addresses:** User management (search, suspend, persona switch), Admin impersonation (view mode)

**Avoids:** Pitfall 3 (impersonation audit contamination), Pitfall 7 (impersonation auth-state escape) — impersonation allow-list defined here

**Research flag:** Standard patterns for user tables. Impersonation middleware pattern needs careful implementation per PITFALLS.md but pattern is well-specified.

---

### Phase 4: Usage Analytics Dashboards

**Rationale:** Add when there are enough users for charts to be meaningful. All data comes from existing Supabase tables — no new data collection. Materialized views or pre-aggregated daily stats must be implemented from the start to avoid `COUNT(*)` performance traps on large `interaction_logs` tables.

**Delivers:** DAU/MAU charts, message volume trends, workflow activity, per-agent effectiveness metrics (success rate, avg response time), analytics router + recharts visualizations.

**Addresses:** Usage analytics (DAU/MAU, messages, workflows), per-agent effectiveness analytics

**Avoids:** Performance trap: `COUNT(*)` full-table scans — use pre-aggregated stats or materialized views from day one

**Uses:** `recharts` (already added in Phase 2), existing Supabase tables

**Research flag:** Standard analytics patterns. Pre-aggregation strategy may need brief research during planning to confirm materialized view approach for this Supabase version.

---

### Phase 5: External Integrations (Sentry, PostHog, CodeRabbit, GitHub)

**Rationale:** Add when the product is in production and errors/events need monitoring. Requires Fernet utilities from Phase 1 for API key storage. Response caching (Redis, 2-5 minute TTL) and per-session call budgets must be in the proxy implementation from the start — retrofitting caching across 10+ tool implementations is error-prone.

**Delivers:** Integration management UI (`/admin/integrations`), `admin_integrations` table populated, proxy routes for each provider, AI agent tools for Sentry issues, PostHog events, CodeRabbit reviews, GitHub PRs, per-session API call budgets in Redis.

**Addresses:** External integrations (Sentry, PostHog, CodeRabbit, GitHub), Fernet-encrypted integration API key management

**Avoids:** Pitfall 9 (API proxy rate amplification) — caching and call budgets in initial implementation

**Uses:** `posthog`, `sentry-sdk`, `PyGithub` (wrap in `asyncio.to_thread()`), existing Redis for caching

**Research flag:** Needs research during planning — API-specific rate limits and response shapes for Sentry, PostHog, CodeRabbit need verification before tool implementations.

---

### Phase 6: Agent Configuration Editor + Feature Flags

**Rationale:** Add when prompt tuning becomes a regular activity. The `admin_config_history` table was created in Phase 1 migration (zero cost). The confirmation UX for instruction updates must show full before/after diffs — this is a Phase 6 implementation requirement, not a Phase 1 concern.

**Delivers:** Agent config editor with before/after diff display, one-click rollback from config history, feature flag toggle UI, `update_agent_instructions` tool (confirm-tier, rate-limited to 5 calls/hour/session), injection validation on instruction text.

**Addresses:** Agent config editor with versioning and rollback, Feature flag toggles

**Avoids:** Pitfall 6 (instruction injection via config editor) — diff display and text validation in initial implementation

**Research flag:** Standard patterns. ADK session context behavior (changes not applied mid-session) is already documented in PITFALLS.md.

---

### Phase 7: Interactive Impersonation Mode

**Rationale:** Add after view mode (Phase 3) is validated as safe. Requires `super_admin` gate. Notification suppression during impersonation must be in place before this goes live. Keep an allow-list (not deny-list) of what interactive mode can do.

**Delivers:** Interactive impersonation at `super_admin` level, endpoint allow-list middleware, notification suppression, impersonation banner color-coded red, auto-expire at 30 minutes via Redis TTL.

**Addresses:** Interactive impersonation mode

**Avoids:** Pitfall 3 (audit contamination — already addressed in Phase 3 schema), Pitfall 7 (auth-state escape — allow-list replaces deny-list)

**Research flag:** Standard patterns. Implementation is well-specified in ARCHITECTURE.md and PITFALLS.md.

---

### Phase 8: Billing Dashboard (Stripe)

**Rationale:** Add when Stripe is connected and MRR is non-trivial. Use a restricted read-only Stripe key for the dashboard; a separate key (also restricted) for the `issue_refund` confirm-tier tool.

**Delivers:** Revenue dashboard (MRR, ARR, churn, plan distribution), `get_revenue_metrics` tool, `issue_refund` confirm-tier tool, Stripe integration stored via Fernet (Phase 1 pattern).

**Addresses:** Billing / revenue dashboard

**Research flag:** Standard Stripe API patterns. Restricted key scopes need verification.

---

### Phase 9: Approval Oversight + Permissions UI

**Rationale:** Add when user volume makes approval backlogs real and when default autonomy tiers need customization. Both are low-complexity features that were deferred because the defaults cover the solo-founder stage.

**Delivers:** Cross-user approval oversight at `/admin/approvals`, admin override tool (confirm-tier), tiered autonomy permissions editor at `/admin/settings`, per-action autonomy configuration UI.

**Addresses:** Cross-user approval oversight + admin override, Tiered autonomy permissions UI

**Research flag:** Standard patterns. No additional research needed.

---

### Phase Ordering Rationale

- **Security-first ordering:** Phase 1 auth and trust architecture gates everything. No phase is safe to ship without it.
- **Dependency graph drives order:** Fernet (Phase 1) is required by Integrations (Phase 5) and Billing (Phase 8). Audit log schema (Phase 1) is required by Impersonation (Phase 3). User management (Phase 3) is required by Interactive Impersonation (Phase 7). Config history schema (Phase 1 migration) is required by Config Editor (Phase 6).
- **Value-per-effort ordering:** Monitoring (Phase 2) delivers maximum operational value for a solo founder with minimal complexity. User management + impersonation (Phase 3) eliminates the most common support friction.
- **Deferred complexity:** Cohort retention analysis, bulk CSV export, and proactive greeting enrichment are excluded from the primary roadmap — not enough user data exists at launch to make them valuable, and they carry the highest implementation complexity.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 5 (Integrations):** Sentry, PostHog, CodeRabbit API rate limits and response schemas need verification before tool implementations. Pagination behavior differs across providers.
- **Phase 4 (Analytics):** Confirm materialized view availability and syntax for this Supabase version before committing to pre-aggregation strategy.

Phases with well-documented patterns (skip research-phase):
- **Phase 1 (Foundation):** All patterns derived directly from existing codebase. ADK agent factory, Fernet, JWT auth, SSE streaming — fully documented.
- **Phase 2 (Monitoring):** Cloud Scheduler pattern exists verbatim in `scheduled_endpoints.py`. httpx concurrent health checks pattern documented in STACK.md.
- **Phase 3 (Users):** TanStack Table server-side pagination, Supabase user queries — standard patterns.
- **Phase 6 (Config):** ADK session context behavior documented. Config history table already in Phase 1 migration.
- **Phase 7-9:** Well-specified in ARCHITECTURE.md and PITFALLS.md.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All additions verified against PyPI, npm, and official docs. No speculative packages — each solves a specific, identified need. PyGithub sync limitation documented and mitigated. |
| Features | HIGH | Grounded in an approved, detailed design spec (`docs/superpowers/specs/2026-03-21-admin-panel-design.md`) plus industry pattern research. Feature dependency graph validated against codebase structure. |
| Architecture | HIGH | All patterns derived directly from the existing codebase. No external speculation — the admin panel is structurally identical to patterns already proven in the repository. |
| Pitfalls | HIGH | Auth/impersonation pitfalls verified against OWASP 2025 and CVEs. Fernet rotation against official cryptography docs. ADK confirmation flow against official ADK docs. |

**Overall confidence: HIGH**

### Gaps to Address

- **PyGithub async wrapping:** `asyncio.to_thread()` pattern for PyGithub calls needs careful implementation to avoid blocking the event loop. Test under load before Phase 5 ships.
- **Recharts 3.x breaking changes:** Three breaking changes documented in STACK.md (`activeIndex` removal, `CategoricalChartState`, z-index) — must be verified against any recharts examples used during Phase 2/4 implementation.
- **Supabase materialized view availability:** Confirm whether the current Supabase version/tier supports `CREATE MATERIALIZED VIEW` and `REFRESH MATERIALIZED VIEW CONCURRENTLY` before committing to the Phase 4 analytics pre-aggregation approach. Fallback is a scheduled daily aggregation into a summary table.
- **Admin panel responsive design:** Spec says desktop-first. Confirm minimum supported viewport width before Phase 1 layout is built (affects sidebar + persistent chat panel layout decisions).
- **Proactive greeting enrichment:** The multi-domain proactive greeting (incidents + approvals + integration status at startup) is scaffolded in Phase 1 (health only) and enriched progressively. The enrichment steps should be formally added to later phases during roadmap creation rather than left implicit.

---

## Sources

### Primary (HIGH confidence)
- Design spec: `docs/superpowers/specs/2026-03-21-admin-panel-design.md` — complete feature spec, confirmed approved
- PyPI: httpx 0.28.1, posthog 7.9.12, sentry-sdk 2.53.0, PyGithub 2.8.1 — version and compatibility verified
- recharts 3.8.0 release + 3.0 migration guide — React 19 support confirmed
- @tanstack/react-table 8.21.3 — server-side pagination pattern verified
- cryptography 46.0.x Fernet docs — MultiFernet rotation pattern verified
- Google ADK FunctionTool patterns — agent factory and tool docstring patterns confirmed
- OWASP LLM Top 10 2025 (LLM01: Prompt Injection) — pitfall 1 grounding
- Official cryptography.io Fernet docs — pitfall 3 grounding

### Secondary (MEDIUM confidence)
- Knight First Amendment Institute — AI agent autonomy levels taxonomy
- AWS Bedrock Agents + Cloudflare Agents — human-in-the-loop confirmation patterns
- Auth0, Authress — user impersonation security practices
- StrongDM — audit logging best practices
- LaunchDarkly — feature flag operational patterns
- Microsoft Ignite 2025 (M365 Admin AI) — competitor admin AI panel patterns

### Tertiary (LOW confidence)
- dotcom-monitor, api7.ai — API health monitoring patterns (corroborates approach, not authoritative)
- PostHog vs Sentry comparison (PostHog blog) — rate limit figures for Phase 5 planning; verify against current provider docs before implementation

---

*Research completed: 2026-03-21*
*Ready for roadmap: yes*
