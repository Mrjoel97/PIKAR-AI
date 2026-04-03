# Roadmap: pikar-ai

## Milestones

- ✅ **v1.0 Core Reliability** - Phase 1 (shipped 2026-03-04)
- ✅ **v1.1 Production Readiness** - Phases 2-6 (shipped 2026-03-13, archive: [v1.1 roadmap](milestones/v1.1-ROADMAP.md), [v1.1 requirements](milestones/v1.1-REQUIREMENTS.md))
- ✅ **v2.0 Broader App Builder** - Phases 16-22 (shipped 2026-03-23, archive: [v2.0 roadmap](milestones/v2.0-ROADMAP.md), [v2.0 requirements](milestones/v2.0-REQUIREMENTS.md))
- ✅ **v3.0 Admin Panel** - Phases 7-15 + 12.1 (shipped 2026-03-26, archive: [v3.0 roadmap](milestones/v3.0-ROADMAP.md), [v3.0 requirements](milestones/v3.0-REQUIREMENTS.md))
- 🚧 **v4.0 Production Scale & Persona UX** - Phases 26-31 (in progress)
- 🚧 **v5.0 Persona Production Readiness** - Phases 32-37 (planned)

## Phases

<details>
<summary>✅ v1.0 Core Reliability (Phase 1) - SHIPPED 2026-03-04</summary>

### Phase 1: Core Reliability
**Goal**: Workflow execution is deterministic and Redis caching is resilient
**Plans**: 2 plans

Plans:
- [x] 01-01: Standardize workflow execution and argument mapping
- [x] 01-02: Implement Redis circuit breakers for cache lookups

</details>

<details>
<summary>✅ v1.1 Production Readiness (Phases 2-6) - SHIPPED 2026-03-13</summary>

See archived roadmap: [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)

</details>

### 🚧 v3.0 Admin Panel (In Progress)

**Milestone Goal:** AI-first admin panel giving the founder a single chat-centered interface to manage the entire platform — users, monitoring, integrations, analytics, configuration, billing, and approvals.

## Phases

- [x] **Phase 7: Foundation** - Auth gate, AdminAgent shell, audit trail, Fernet encryption, confirmation flow (completed 2026-03-21)
- [x] **Phase 8: Health Monitoring** - Concurrent health checks, Cloud Scheduler loop, monitoring dashboard with sparklines (completed 2026-03-21)
- [x] **Phase 9: User Management + Impersonation View** - User table, suspend/unsuspend, persona switch, read-only impersonation (completed 2026-03-21)
- [x] **Phase 10: Usage Analytics** - DAU/MAU charts, agent effectiveness metrics, feature and API usage dashboards (completed 2026-03-22)
- [x] **Phase 11: External Integrations** - Sentry, PostHog, GitHub, Stripe proxy connections with Fernet-encrypted key storage + cross-service diagnostic skills (completed 2026-03-22)
- [x] **Phase 12: Agent Config + Feature Flags** - Config editor with diff/rollback, feature flag toggles, MCP/API endpoint config + impact assessment and rollback skills (completed 2026-03-23)
- [x] **Phase 12.1: Agent Knowledge Base** - AdminAgent tools for uploading docs/images/videos as agent training data, system-scope RAG, knowledge management + curation skill (completed 2026-03-23)
- [x] **Phase 13: Interactive Impersonation** - Super-admin interactive mode, endpoint allow-list, notification suppression, 30-min expiry + user intelligence skills (completed 2026-03-23)
- [x] **Phase 14: Billing Dashboard** - MRR/ARR/churn revenue dashboard, Stripe metrics, refund confirm-tier tool + analytics interpretation and revenue forecasting skills (completed 2026-03-25)
- [x] **Phase 15: Approval Oversight + Permissions + Role Management** - Cross-user approvals, admin override, autonomy tier editor, multi-tier admin roles + governance skills and daily operational digest (completed 2026-03-25)

## Phase Details

### Phase 7: Foundation
**Goal**: The admin panel is securely accessible, the AdminAgent can chat over SSE, every action is auditable, and the trust architecture (autonomy tiers, confirmation tokens, Fernet encryption) is enforced from day one
**Depends on**: Nothing (first v3.0 phase — builds on existing v1.1 infra)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, ASST-01, ASST-03, ASST-04, ASST-05, ASST-06, AUDT-01, AUDT-02, AUDT-03
**Success Criteria** (what must be TRUE):
  1. A non-admin user navigating to any `/admin/*` route is redirected server-side without any admin UI rendering
  2. An admin whose email is in ADMIN_EMAILS env var (or has DB user_roles admin entry) can reach the admin panel and start a chat session with the AdminAgent
  3. A confirm-tier action attempted via the AdminAgent returns a confirmation card — the action does not execute until the admin clicks Confirm, and a second click (double-execution) is rejected
  4. The admin chat session persists across a full browser refresh — conversation history reloads from admin_chat_sessions
  5. Every admin action (including AI-agent actions) produces an audit log row with the correct source tag visible in the audit trail UI
**Plans**: 5 plans

Plans:
- [ ] 07-01-PLAN.md — Database migration, require_admin middleware, MultiFernet encryption service
- [ ] 07-02-PLAN.md — AdminAgent with autonomy enforcement, confirmation tokens, audit logging
- [ ] 07-03-PLAN.md — SSE chat endpoint with session persistence and confirmation handling
- [ ] 07-04-PLAN.md — Admin frontend layout, chat panel, confirmation card, audit log viewer
- [ ] 07-05-PLAN.md — Audit log API endpoint + end-to-end verification checkpoint

### Phase 8: Health Monitoring
**Goal**: The system continuously monitors all health endpoints on a 60-second loop, auto-creates and resolves incidents, and the admin can see live status at a glance on a dashboard
**Depends on**: Phase 7
**Requirements**: HLTH-01, HLTH-02, HLTH-03, HLTH-04, HLTH-05, HLTH-06
**Success Criteria** (what must be TRUE):
  1. Admin can open `/admin/monitoring` and see current status cards for all health endpoints, with sparkline charts showing recent history
  2. When a health endpoint goes down, an incident is automatically created and visible in the dashboard within 90 seconds (60s loop + propagation)
  3. When the endpoint recovers, the incident closes automatically and the status card turns green
  4. If health check data is more than 5 minutes old (e.g., Cloud Scheduler paused), a stale-data warning banner appears on the dashboard
**Plans**: 3 plans

Plans:
- [ ] 08-01-PLAN.md — Health monitor service, incident lifecycle, Cloud Scheduler endpoint, DB index migration
- [ ] 08-02-PLAN.md — Monitoring status API endpoint, AdminAgent monitoring tools (7 tools)
- [ ] 08-03-PLAN.md — Monitoring dashboard frontend with sparkline charts, stale-data banner, end-to-end verification

### Phase 9: User Management + Impersonation View
**Goal**: The admin can find any user, take basic account actions, and view the app exactly as that user sees it — without any of those actions appearing as user-originated in the audit log
**Depends on**: Phase 7
**Requirements**: USER-01, USER-02, USER-03, USER-05
**Success Criteria** (what must be TRUE):
  1. Admin can search users by email or name, filter by status/persona, and paginate through results in a table
  2. Admin can suspend a user and the user's subsequent login attempt is blocked; admin can unsuspend and access is restored
  3. Admin can switch a user's persona (e.g., solopreneur to enterprise) and the change is reflected in the user's next session
  4. Admin can enter impersonation view mode for any user — a non-dismissible banner remains visible at all times — and browse the app as that user in read-only mode
**Plans**: 4 plans

Plans:
- [ ] 09-01-PLAN.md — Migration seed + backend user management API endpoints (5 endpoints) + unit tests
- [ ] 09-02-PLAN.md — AdminAgent user tools (6 tools) with autonomy enforcement + registration
- [ ] 09-03-PLAN.md — Frontend user table with TanStack Table + user detail page with actions
- [ ] 09-04-PLAN.md — Impersonation view mode: ImpersonationContext, non-dismissible banner, view page

### Phase 10: Usage Analytics
**Goal**: The admin can see how the platform is being used — who is active, which agents are effective, and what features and API calls are being made — all from pre-aggregated data that does not degrade under load
**Depends on**: Phase 7
**Requirements**: ANLT-01, ANLT-02, ANLT-04, ANLT-05
**Success Criteria** (what must be TRUE):
  1. Admin can view DAU and MAU charts on the analytics dashboard showing trends over the past 30 days
  2. Admin can view per-agent effectiveness metrics showing success rate and average response time for each of the 10 specialized agents
  3. Admin can view feature usage and API call activity breakdowns showing which capabilities are being exercised
  4. Admin can view a configuration status overview showing active feature flags and current agent config versions
**Plans**: 3 plans

Plans:
- [ ] 10-01-PLAN.md — Summary table migration + aggregation service with tests
- [ ] 10-02-PLAN.md — Analytics API router + AdminAgent analytics tools (4 tools) with tests
- [ ] 10-03-PLAN.md — Analytics dashboard frontend with KPI cards, charts, and config status

### Phase 11: External Integrations
**Goal**: The admin can connect Sentry, PostHog, GitHub, and Stripe via encrypted API keys and query each service through the AdminAgent — with responses cached so a single chat session cannot exhaust provider rate limits
**Depends on**: Phase 7 (Fernet encryption)
**Requirements**: INTG-01, INTG-02, INTG-03, INTG-04, INTG-05, INTG-06, SKIL-01, SKIL-02
**Success Criteria** (what must be TRUE):
  1. Admin can enter an API key for Sentry, PostHog, GitHub, or Stripe on the integrations page — the key is stored encrypted and the plaintext is never returned to the browser after save
  2. Admin can ask the AdminAgent "show me recent Sentry errors" and receive a formatted response proxied through the backend without the API key being exposed
  3. Admin can ask the AdminAgent about GitHub PRs or PostHog events and receive cached responses (repeated identical queries within the TTL window return instantly without hitting the provider again)
  4. A single chat session cannot exceed per-session API call budgets for any integration provider
  5. AdminAgent can correlate errors across Sentry, PostHog, and health incidents to suggest probable root causes
  6. AdminAgent can detect response time degradation trends and proactively alert before they become incidents
**Plans**: 3 plans

Plans:
- [ ] 11-01-PLAN.md — Integration proxy service + CRUD/proxy API router + PyGithub dependency + tests
- [ ] 11-02-PLAN.md — AdminAgent integration tools (6 tools) with autonomy enforcement + registration
- [ ] 11-03-PLAN.md — Frontend /admin/integrations page with provider cards, configure modal, test connection

### Phase 12: Agent Config + Feature Flags
**Goal**: The admin can edit any agent's instructions with a visible before/after diff, roll back to any previous version in one click, and toggle feature flags — with injection validation preventing malicious instruction content from reaching the LLM
**Depends on**: Phase 7 (config history schema created in Phase 7 migration)
**Requirements**: CONF-01, CONF-02, CONF-03, CONF-04, CONF-05, SKIL-07, SKIL-08
**Success Criteria** (what must be TRUE):
  1. Admin can open the config editor for any agent and see the current instructions with a before/after diff when edits are made — the update does not apply until confirmed
  2. Admin can view the full version history for any agent config and restore any previous version in one click
  3. Admin can toggle a feature flag on or off from the UI and the change takes effect for new sessions within 60 seconds
  4. Admin can view and update autonomy tier assignments (auto/confirm/blocked) for individual AdminAgent actions
  5. AdminAgent can assess impact of config changes by analyzing which workflows depend on the target agent before applying
  6. AdminAgent can recommend rollback when a config change correlates with degraded agent effectiveness metrics
**Plans**: 3 plans

Plans:
- [ ] 12-01-PLAN.md — DB migration (agent configs + feature flags tables) + config service with diff/validation/flag caching
- [ ] 12-02-PLAN.md — AdminAgent config tools (10 tools) + REST API router + agent registration + tests
- [ ] 12-03-PLAN.md — Frontend /admin/config page with instruction editor, version history, flag toggles, autonomy table

### Phase 12.1: Agent Knowledge Base
**Goal**: The admin can train any specialized agent with business-specific knowledge — documents, images, and videos — by chatting with the AdminAgent, which handles upload, processing, embedding, and assignment. System-scope knowledge is available to all users without per-user duplication.
**Depends on**: Phase 12 (agent config infrastructure), Phase 7 (AdminAgent, audit trail)
**Requirements**: KNOW-01, KNOW-02, KNOW-03, KNOW-04, KNOW-05, KNOW-06, KNOW-07, SKIL-09
**Success Criteria** (what must be TRUE):
  1. Admin can tell the AdminAgent "Train the financial agent with this quarterly report" and upload a PDF — the document is chunked, embedded, and assigned to the financial agent's knowledge scope
  2. Admin can upload images (product photos, brand assets) and videos (training videos, demos) — images get metadata + description embeddings, videos get transcript extraction + frame references
  3. Admin can assign knowledge to a specific agent or make it globally available — global knowledge is searched by all agents for all users without duplicating embeddings
  4. Admin can ask the AdminAgent "What does the marketing agent know?" and get a summary of its knowledge entries — and can ask to remove outdated entries (confirm-tier deletion)
  5. Admin can view `/admin/knowledge` showing upload history, per-agent knowledge counts, total embeddings, and storage usage
  6. AdminAgent can validate uploaded training data for relevance, detect near-duplicate content, and recommend optimal chunking strategy
**Plans**: 3 plans

Plans:
- [ ] 12.1-01-PLAN.md — DB migration (admin_knowledge_entries table, match_system_knowledge RPC, storage bucket) + knowledge service with extraction/embedding/search
- [ ] 12.1-02-PLAN.md — AdminAgent knowledge tools (8 tools) + REST API router + agent registration + tests
- [ ] 12.1-03-PLAN.md — Frontend /admin/knowledge page with upload panel, agent cards, storage stats, history table

### Phase 13: Interactive Impersonation
**Goal**: Super admins can take actions inside the app on behalf of any user for support purposes — with an explicit allow-list of permitted endpoints, automatic 30-minute expiry, and no impersonation actions contaminating the user's own audit history
**Depends on**: Phase 9 (view mode validated safe, impersonation allow-list defined)
**Requirements**: USER-04, AUDT-04, SKIL-03, SKIL-04
**Success Criteria** (what must be TRUE):
  1. A super admin can activate interactive impersonation for any user — the banner turns red and all subsequent actions are tagged with the impersonation session ID in the audit log, not attributed to the user
  2. Interactive impersonation only allows actions on the explicit endpoint allow-list — attempts to access blocked endpoints are rejected with a clear message
  3. The impersonation session auto-expires after 30 minutes and cannot be extended without re-activating
  4. Notifications that would normally fire for the user are suppressed during an active impersonation session
  5. AdminAgent can identify at-risk users by correlating declining usage with billing status and last login
  6. AdminAgent provides structured support playbooks during interactive impersonation sessions
**Plans**: 3 plans

Plans:
- [ ] 13-01-PLAN.md — DB migration + impersonation service + audit upgrade + API endpoints with super-admin gate
- [ ] 13-02-PLAN.md — AdminAgent user intelligence tools (SKIL-03, SKIL-04) + impersonate_user upgrade + registration
- [ ] 13-03-PLAN.md — Frontend interactive mode: banner upgrade, session activation, context token passing + verification

### Phase 14: Billing Dashboard
**Goal**: The admin can see current revenue health (MRR, ARR, churn, plan distribution) pulled from Stripe and can issue refunds through a confirm-tier action — using a restricted read-only Stripe key that limits blast radius
**Depends on**: Phase 11 (Stripe integration proxy and Fernet key storage)
**Requirements**: ANLT-03, SKIL-05, SKIL-06, SKIL-10, SKIL-11
**Success Criteria** (what must be TRUE):
  1. Admin can view the billing dashboard showing MRR, ARR, churn rate, and plan distribution pulled live from Stripe
  2. Admin can ask the AdminAgent to issue a refund — a confirmation card appears with the refund details — the refund executes only after explicit confirmation and is logged in the audit trail
  3. AdminAgent can detect statistical anomalies in DAU/MAU and agent effectiveness (>2 std dev from 30-day baseline)
  4. AdminAgent can generate executive summary narratives from raw analytics with actionable recommendations
  5. AdminAgent can forecast MRR/ARR trends from historical subscription data
  6. AdminAgent can assess refund risk by cross-referencing customer LTV and usage before processing
**Plans**: 2 plans

Plans:
- [ ] 14-01-PLAN.md — Billing permission seeds + Stripe fetch helpers + 7 billing tools + API router + AdminAgent registration + tests
- [ ] 14-02-PLAN.md — Frontend /admin/billing page with KPI cards, plan distribution chart + visual verification

### Phase 15: Approval Oversight + Permissions + Role Management
**Goal**: The admin can see and act on all pending approvals, reconfigure AdminAgent autonomy tiers, and manage a multi-tier admin hierarchy — super admin can create junior_admin, senior_admin, and admin accounts with scoped access permissions per section and action
**Depends on**: Phase 7 (audit trail, user_roles table), Phase 12 (autonomy tier config schema)
**Requirements**: APPR-01, APPR-02, ROLE-01, ROLE-02, ROLE-03, ROLE-04, ASST-02, SKIL-12, SKIL-13, SKIL-14, SKIL-15, SKIL-16
**Success Criteria** (what must be TRUE):
  1. Admin can view a unified approval queue at `/admin/approvals` showing all pending approvals across all users, filterable by user and approval type
  2. Admin can approve or reject any pending approval on behalf of a user — the action is a confirm-tier AdminAgent action and is tagged as admin-override in the audit log
  3. Admin can use the permissions UI at `/admin/settings` to change the autonomy tier (auto/confirm/blocked) for any AdminAgent action — changes persist and take effect for subsequent chat sessions
  4. Super admin can create new admin accounts with roles (junior_admin, senior_admin, admin) and each role has appropriate access restrictions — junior_admin is read-only by default, senior_admin has full access except role management
  5. Super admin can configure per-role permissions defining which admin sections and write actions each role can access
  6. AdminAgent has 30+ tools across all 7 domains (ASST-02 — cross-phase requirement, verified complete at Phase 15)
  7. AdminAgent can recommend autonomy tiers for new tools and suggest per-role permissions based on admin responsibilities
  8. AdminAgent can summarize audit logs into narrative compliance reports
  9. AdminAgent produces a daily operational digest covering pending approvals, at-risk users, anomalous metrics, and upcoming expirations
  10. AdminAgent can classify issue severity and route escalations to super admin with structured context
**Plans**: 3 plans

Plans:
- [ ] 15-01-PLAN.md — Migration + role service + middleware enhancement + admin approval queue and override endpoints + role CRUD API
- [ ] 15-02-PLAN.md — 8 governance AdminAgent tools (SKIL-12 through SKIL-16 + approval/role management) + AdminAgent registration + tests
- [ ] 15-03-PLAN.md — Frontend /admin/approvals page + /admin/settings page (autonomy tiers, role management, role permissions tabs) + visual verification

## Progress

**Execution Order:**
Phases execute in numeric order: 7 → 8 → 9 → 10 → 11 → 12 → 12.1 → 13 → 14 → 15

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Core Reliability | v1.0 | 2/2 | Complete | 2026-03-04 |
| 2-6. Production Readiness | v1.1 | — | Complete | 2026-03-13 |
| 7. Foundation | 5/5 | Complete   | 2026-03-21 | - |
| 8. Health Monitoring | 3/3 | Complete    | 2026-03-21 | - |
| 9. User Management + Impersonation View | 4/4 | Complete    | 2026-03-21 | - |
| 10. Usage Analytics | 3/3 | Complete    | 2026-03-22 | - |
| 11. External Integrations | 3/3 | Complete    | 2026-03-22 | - |
| 12. Agent Config + Feature Flags | 3/3 | Complete    | 2026-03-23 | - |
| 12.1. Agent Knowledge Base | 3/3 | Complete    | 2026-03-23 | - |
| 13. Interactive Impersonation | 3/3 | Complete    | 2026-03-23 | - |
| 14. Billing Dashboard | 2/2 | Complete    | 2026-03-25 | - |
| 15. Approval Oversight + Permissions UI | 3/3 | Complete    | 2026-03-25 | - |

</details>

### 🚧 v4.0 Production Scale & Persona UX (In Progress)

**Milestone Goal:** Make the app production-ready for 1000+ concurrent users and deliver persona-differentiated frontend experiences — while ensuring all agents are available to all personas with rate limits as the only differentiator.

## Phases

- [x] **Phase 26: Async Supabase & Connection Pooling** — Migrate sync Supabase client to async, configure httpx connection limits, eliminate thread pool bottleneck (completed 2026-03-26)
- [x] **Phase 27: Production Deployment Hardening** — Fix InMemory fallbacks, SSE stream timeouts, Docker production config, Cloud Run scaling parameters (completed 2026-03-26)
- [x] **Phase 27.1: Input Sanitization & Security Hardening** — Fix HTML injection, add CSP/Referrer-Policy/X-XSS-Protection headers, DOMPurify frontend, Pydantic validators (completed 2026-03-27)
- [x] **Phase 28: Persona Agent Equalization** — Remove preferred_agents restrictions, make all agents available to all personas, rate limits as sole differentiator (completed 2026-03-26)
- [x] **Phase 29: Persona-Specific Frontend UX** — Build persona-aware navigation, tailored dashboards per persona, replace stub shell components (completed 2026-03-26)
- [x] **Phase 30: Persona Default Widgets** — Pre-populated starter widgets per persona, shell header fade-in animation (completed 2026-03-27)
- [ ] **Phase 31: Persona Empty States & Section Headers** — Persona-tailored empty states with setup CTAs, section headers for widget groups

## Phase Details

### Phase 26: Async Supabase & Connection Pooling
**Goal**: The Supabase client uses async HTTP throughout, with proper connection pool limits, eliminating the 200-thread bottleneck that would choke at 1000+ concurrent users
**Depends on**: Nothing (independent infrastructure improvement)
**Success Criteria** (what must be TRUE):
  1. `supabase_client.py` uses `httpx.AsyncClient` with `httpx.Limits(max_connections=200, max_keepalive_connections=50)` — no sync HTTP client remains in the hot path
  2. All Supabase operations (session service, task store, workflow engine, cache, RAG) use native async calls — no `asyncio.to_thread()` wrapping sync Supabase calls
  3. Thread pool size can be reduced from 200 to default (32) because DB calls no longer consume threads
  4. Under simulated load of 500 concurrent requests, p99 latency is <2s for DB-backed endpoints (vs current thread-queuing behavior)
**Plans**: 3 plans

Plans:
- [ ] 26-01-PLAN.md — AsyncSupabaseService singleton with httpx.AsyncClient connection pooling, execute_async upgrade, async circuit breaker
- [ ] 26-02-PLAN.md — Migrate hot-path consumers (session service, task store, workflow engine, RAG) to native async client
- [ ] 26-03-PLAN.md — Thread pool reduction from 200 to 32, async client lifecycle in FastAPI lifespan, concurrency verification

### Phase 27: Production Deployment Hardening
**Goal**: All InMemory fallbacks are eliminated in production, SSE streams have server-side timeouts, Docker uses gunicorn in production mode, and Cloud Run scaling is configured for 1000+ users
**Depends on**: Phase 26 (async client must be in place before scaling config)
**Success Criteria** (what must be TRUE):
  1. `InMemorySessionService` and `InMemoryArtifactService` are never used in production — startup fails fast if Supabase or GCS is unavailable rather than silently degrading to in-memory
  2. SSE chat streams have a configurable server-side timeout (default 300s) — stuck connections are cleaned up proactively, not just via 5-min TTL
  3. Docker production entrypoint uses `gunicorn` with `gunicorn.conf.py` (4 workers, 1000 connections/worker) — not `uvicorn --reload`
  4. Cloud Run service config specifies `min_instances: 2`, `max_instances: 20`, `concurrency: 250` for the backend service
  5. `LOGS_BUCKET_NAME` is required in production — startup validation rejects missing GCS artifact bucket
  6. In-memory persona cache in rate_limiter.py is replaced with Redis-backed cache shared across replicas
**Plans**: 2 plans

Plans:
- [ ] 27-01-PLAN.md — Fail-fast production guards for InMemory fallbacks + LOGS_BUCKET_NAME validation
- [ ] 27-02-PLAN.md — Docker production config, Cloud Run service YAML, Redis persona cache

### Phase 27.1: Input Sanitization & Security Hardening (INSERTED)
**Goal**: All user-supplied content interpolated into HTML is escaped to prevent XSS, security response headers (CSP, Referrer-Policy, X-XSS-Protection) are set on every response, the frontend uses DOMPurify for HTML sanitization, and API request models have proper length constraints
**Depends on**: Phase 27
**Requirements**: SECU-01, SECU-02, SECU-05
**Success Criteria** (what must be TRUE):
  1. HTML injection payloads in form submissions, landing page generation, message sending, and email forwarding are escaped via `html.escape()` — script tags render as text, not execute
  2. Every HTTP response includes Content-Security-Policy, Referrer-Policy (strict-origin-when-cross-origin), and X-XSS-Protection (1; mode=block) headers
  3. The public page viewer (`/p/[id]`) uses DOMPurify instead of a hand-rolled DOM sanitizer
  4. Community post/comment creation rejects oversized inputs at the Pydantic validation layer
**Plans**: 2 plans

Plans:
- [ ] 27.1-01-PLAN.md — Fix HTML injection in form_handler, landing_page, integration_tools, webhooks + add CSP/Referrer-Policy/X-XSS-Protection security headers
- [ ] 27.1-02-PLAN.md — Replace hand-rolled sanitizer with DOMPurify + add Pydantic validators to community router

### Phase 28: Persona Agent Equalization
**Goal**: All 10+ agents are available to every persona — the only differentiator between personas is rate limits (solopreneur: 10/min, startup: 30/min, SME: 60/min, enterprise: 120/min), not agent access
**Depends on**: Nothing (independent policy change)
**Success Criteria** (what must be TRUE):
  1. `preferred_agents` field in PersonaPolicy no longer restricts agent routing — all agents are available to all personas
  2. The Executive Agent routes to any specialized agent regardless of persona — persona only affects agent behavior (via prompt fragments), not availability
  3. Rate limit enforcement correctly applies persona-specific limits: 10/min (solopreneur), 30/min (startup), 60/min (SME), 120/min (enterprise)
  4. Workflow templates are available to all personas unless explicitly scoped — persona enforcement mode applies behavioral tuning, not access restriction
  5. Backend tests verify that a solopreneur user can invoke all 10 agent types successfully (just rate-limited)
**Plans**: 1 plan

Plans:
- [ ] 28-01-PLAN.md — Equalize preferred_agents across all personas, update prompt injection, write equalization test suite

### Phase 29: Persona-Specific Frontend UX
**Goal**: Each persona gets a differentiated dashboard experience — persona-aware sidebar navigation, tailored widget layouts, and meaningful shell components that reflect each business type's priorities
**Depends on**: Phase 28 (agent access equalized first)
**Success Criteria** (what must be TRUE):
  1. Sidebar navigation shows persona-relevant items first (e.g., solopreneur sees Content/Sales/Finance prominently; enterprise sees Compliance/Reports/Approvals) — all items remain accessible, just prioritized differently
  2. Each persona's dashboard page shows a tailored default widget layout reflecting their KPIs and priorities from PersonaPolicy
  3. Shell components (SolopreneurShell, SmeShell, StartupShell, EnterpriseShell) are fully implemented with appropriate theming, header content, and persona-specific quick actions — not 14-line stubs
  4. The dashboard page renders differently for each persona type (not the same generic layout for all)
  5. Onboarding flow correctly sets the persona and the first dashboard experience matches the selected persona
**Plans**: 3 plans

Plans:
- [ ] 29-01-PLAN.md — Persona-aware sidebar navigation with per-persona priority ordering
- [ ] 29-02-PLAN.md — Fully implemented shell components with persona-specific theming and quick actions
- [ ] 29-03-PLAN.md — Persona-specific dashboard pages, widget layouts, and onboarding connection

### Phase 30: Persona Default Widgets
**Goal**: New users see a pre-populated dashboard with persona-relevant starter widgets instead of an empty gallery — solopreneurs see revenue/content/pipeline widgets, enterprise sees compliance/reports/approvals
**Depends on**: Phase 29 (persona shell components and dashboard wiring must exist)
**Success Criteria** (what must be TRUE):
  1. A new solopreneur user with zero pinned widgets sees 4 default starter widgets: Revenue Chart, Morning Briefing, Kanban Board, Campaign Hub
  2. A new startup user sees: Revenue Chart, Morning Briefing, Initiative Dashboard, Workflow Observability
  3. A new SME user sees: Department Activity, Morning Briefing, Revenue Chart, Workflow Observability
  4. A new enterprise user sees: Department Activity, Morning Briefing, Revenue Chart, Boardroom
  5. Default widgets only appear when the user has zero pinned widgets — once they pin or dismiss widgets, defaults are no longer shown
  6. Shell header fade-in animation on persona page load (subtle `motion.div` opacity transition)
**Plans**: 1 plan

Plans:
- [x] 30-01-PLAN.md — Persona default widget config + dashboard wiring + shell header fade-in animation

### Phase 31: Persona Empty States & Section Headers
**Goal**: Widget empty states are persona-tailored with actionable setup prompts, and default widget grids use persona-specific section headers that group widgets by business domain
**Depends on**: Phase 30 (default widgets must exist to show empty states within them)
**Success Criteria** (what must be TRUE):
  1. When a solopreneur's Revenue Chart has no data, it shows "Connect Stripe to track your cash flow" with a link to /settings/integrations — not a generic "No data available"
  2. When a startup's Initiative Dashboard has no initiatives, it shows "Create your first growth experiment" with a link to /dashboard/initiatives/new
  3. Each persona's default widget grid is grouped under section headers (solopreneur: "Revenue & Pipeline" + "Content & Marketing"; startup: "Growth Metrics" + "Experiment Velocity"; SME: "Operations Health" + "Reporting"; enterprise: "Portfolio Overview" + "Governance")
  4. Empty state messages reference the persona's core objectives and KPIs from PersonaPolicy — not generic text
  5. All empty states include a primary CTA button that routes to the most relevant setup/creation page
  6. Section headers are responsive — full text on desktop, abbreviated on mobile
**Plans**: 2 plans

Plans:
- [ ] 31-01-PLAN.md — Persona empty state config + PersonaEmptyState component + wire into 8 widgets
- [ ] 31-02-PLAN.md — Section headers in personaWidgetDefaults + PersonaDashboardLayout rendering

## Progress

**Execution Order:**
Phases execute in numeric order: 26 → 27 → 27.1 → 28 → 29 → 30 → 31

| Phase | Plans Complete | Status | Completed |
|-------|---------------|--------|-----------|
| 26. Async Supabase & Connection Pooling | 3/3 | Complete    | 2026-03-26 |
| 27. Production Deployment Hardening | 2/2 | Complete    | 2026-03-26 |
| 27.1. Input Sanitization & Security Hardening | 2/2 | Complete    | 2026-03-27 |
| 28. Persona Agent Equalization | 1/1 | Complete    | 2026-03-26 |
| 29. Persona-Specific Frontend UX | 3/3 | Complete    | 2026-03-26 |
| 30. Persona Default Widgets | 1/1 | Complete    | 2026-03-27 |
| 31. Persona Empty States & Section Headers | 0/2 | Planned | - |

---

### 🚧 v5.0 Persona Production Readiness (Planned)

**Milestone Goal:** Take all 4 personas (Solopreneur, Startup, SME, Enterprise) from partial completion to 100% production-ready. Close every gap identified in the persona readiness audit: soft feature gating, backend persona awareness, computed KPIs, multi-user foundations, department coordination, enterprise governance primitives, and real functional differentiation beyond cosmetic branding.

## Phases

- [x] **Phase 32: Feature Gating Foundation** — Centralized tier-to-feature config, upgrade prompts, backend 403 enforcement, gating UI components (completed 2026-04-03)
- [ ] **Phase 33: Backend Persona Awareness** — ExecutiveAgent persona-specific instructions, sub-agent persona context injection, session-level persona loading
- [ ] **Phase 34: Computed KPIs** — Per-persona KPI computation service, real data wired into all 4 persona shell headers
- [ ] **Phase 35: Teams & RBAC** — Team workspace model, Admin/Editor/Viewer roles, permission enforcement on frontend and backend
- [ ] **Phase 36: Enterprise Governance** — Audit trail table, portfolio health scoring, governance dashboard, multi-level approval chains
- [ ] **Phase 37: SME Department Coordination** — Cross-department task routing, per-department dashboards, agent routing to department agents

## Phase Details

### Phase 32: Feature Gating Foundation
**Goal**: Every persona tier has a clearly enforced feature boundary — locked features show upgrade prompts instead of broken or hidden UI, and the backend rejects restricted access with a clear message
**Depends on**: Phase 31 (persona UX foundations must be in place)
**Requirements**: GATE-01, GATE-02, GATE-03, GATE-04
**Success Criteria** (what must be TRUE):
  1. A solopreneur user clicking a Startup-or-higher feature sees an upgrade prompt showing their current tier, the locked feature name, and a path to upgrade — not a 404 or empty page
  2. A backend API call to a restricted endpoint from the wrong persona tier returns HTTP 403 with an upgrade message — the restricted action is never executed
  3. Adding or removing a feature from a tier's access list requires changing exactly one centralized config file — no per-page conditional logic needs updating
  4. The upgrade prompt component renders consistently across sidebar items, page headers, and widget tiles — same visual treatment in all contexts
**Plans**: 3 plans

Plans:
- [ ] 32-01-PLAN.md — Centralized feature gating config + UpgradePrompt component + useFeatureGate hook
- [ ] 32-02-PLAN.md — Frontend sidebar lock icons + GatedPage wrapper for dashboard pages
- [ ] 32-03-PLAN.md — Backend Python gating config + require_feature FastAPI dependency + router enforcement

### Phase 33: Backend Persona Awareness
**Goal**: The ExecutiveAgent and all 10 sub-agents receive and apply persona-specific behavioral instructions on every chat session — a solopreneur gets plain-language, action-focused responses while an enterprise user gets structured, compliance-aware outputs
**Depends on**: Phase 32 (gating config establishes persona model used throughout)
**Requirements**: PERS-01, PERS-02, PERS-03
**Success Criteria** (what must be TRUE):
  1. A solopreneur's chat messages produce responses in a direct, informal tone with concrete next-steps — the same question from an enterprise user produces a structured, formal response referencing governance and compliance considerations
  2. Each specialized sub-agent (financial, content, strategic, etc.) applies persona-appropriate depth and terminology — a solopreneur asking the financial agent gets a cash flow summary, an enterprise user gets portfolio analysis
  3. Persona context is loaded once at session start from the user's Supabase profile and injected into agent state — it does not require the user to re-state their persona in each message
**Plans**: 2 plans

Plans:
- [ ] 33-01-PLAN.md — Persona behavioral instructions module (48 persona-agent combinations) + integration into prompt pipeline
- [ ] 33-02-PLAN.md — Harden persona session loading + end-to-end tests + human verification checkpoint

### Phase 34: Computed KPIs
**Goal**: Every persona's shell header shows real numbers computed from actual Supabase data — not placeholder zeros or hardcoded mock values
**Depends on**: Phase 32 (persona tier determines which KPI set to compute)
**Requirements**: KPI-01, KPI-02, KPI-03, KPI-04, KPI-05
**Success Criteria** (what must be TRUE):
  1. A solopreneur's shell header shows Cash Collected, Weekly Pipeline, and Content Consistency values computed from their actual workflow and content records
  2. A startup user's shell header shows MRR Growth, Activation & Conversion rate, and Experiment Velocity derived from their initiative and financial data
  3. An SME user's shell header shows Department Performance, Process Cycle Time, and Margin & Compliance values aggregated from their department activity records
  4. An enterprise user's shell header shows Portfolio Health score, Risk & Control Coverage percentage, and Reporting Quality index computed from their portfolio data
  5. KPI values refresh on page load and update within 60 seconds of underlying data changes — a dedicated API endpoint returns the full KPI set for the requesting user's persona
**Plans**: TBD

### Phase 35: Teams & RBAC
**Goal**: Users on Startup/SME/Enterprise tiers can share their workspace with teammates, and every action in the app is gated by role-based permissions — Admins can do everything, Editors can create and edit, Viewers can only read
**Depends on**: Phase 32 (feature gating config — team features are tier-restricted)
**Requirements**: TEAM-01, TEAM-02, TEAM-03, TEAM-04, TEAM-05
**Success Criteria** (what must be TRUE):
  1. A workspace owner can generate a share link that adds a new member to their workspace — the invited member sees shared initiatives, workflows, and content on their dashboard
  2. An Editor team member can create and edit initiatives and workflows but cannot access billing settings or manage other team members
  3. A Viewer team member can browse all shared workspace content but all create/edit/delete actions are visibly disabled — clicking them shows a "contact your admin" message
  4. A backend API call that would modify workspace data from a Viewer-role session returns HTTP 403 — the role check happens server-side, not only in the UI
  5. A workspace Admin can open the team settings page, see all current members with their roles, and change any member's role from a dropdown
**Plans**: TBD

### Phase 36: Enterprise Governance
**Goal**: Enterprise users have full audit visibility into who did what and when, a quantified portfolio health score, a governance dashboard, and multi-level approval chains for high-impact actions
**Depends on**: Phase 35 (RBAC roles are required for approval chain role assignments)
**Requirements**: GOV-01, GOV-02, GOV-03, GOV-04
**Success Criteria** (what must be TRUE):
  1. Every significant action (initiative creation/deletion, workflow execution, role change, approval decision) produces an audit log row with actor identity, action type, timestamp, and affected resource — visible in a paginated log
  2. An enterprise user's portfolio health score is a single numeric value (0-100) computed from initiative completion rate, risk coverage, and resource allocation — it updates when any of those underlying values change
  3. An enterprise user can open the governance dashboard and see audit log, compliance status summary, pending approval chains, and control coverage metrics in one view
  4. A high-impact action (e.g., bulk workflow execution, data export, budget change) triggers a multi-level approval chain — the action is blocked until all required approvers (reviewer → approver → executive) have confirmed
**Plans**: TBD

### Phase 37: SME Department Coordination
**Goal**: SME users can route tasks between departments, each department has a visible health dashboard, and the AI automatically routes department-specific questions to the right specialized agent
**Depends on**: Phase 35 (team/role model needed for cross-department handoff ownership)
**Requirements**: DEPT-01, DEPT-02, DEPT-03
**Success Criteria** (what must be TRUE):
  1. An SME user can assign a workflow task to a different department — the receiving department's task list shows the handoff with originating department, status, and due date
  2. Each department (Finance, Operations, Marketing, Sales, HR, Compliance) has a dashboard page showing its active tasks, KPI indicators, and a health status (green/yellow/red) based on task completion rate
  3. When an SME user asks the agent a question that belongs to a specific department (e.g., "what's our payroll this month?"), the agent routes to the HR agent — not the generic ExecutiveAgent — without the user needing to specify which agent
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 32 → 33 → 34 → 35 → 36 → 37

| Phase | Plans Complete | Status | Completed |
|-------|---------------|--------|-----------|
| 32. Feature Gating Foundation | 3/3 | Complete    | 2026-04-03 |
| 33. Backend Persona Awareness | 0/2 | Planned | - |
| 34. Computed KPIs | 0/TBD | Not started | - |
| 35. Teams & RBAC | 0/TBD | Not started | - |
| 36. Enterprise Governance | 0/TBD | Not started | - |
| 37. SME Department Coordination | 0/TBD | Not started | - |
