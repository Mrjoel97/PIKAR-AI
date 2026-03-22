# Roadmap: pikar-ai

## Milestones

- ✅ **v1.0 Core Reliability** - Phase 1 (shipped 2026-03-04)
- ✅ **v1.1 Production Readiness** - Phases 2-6 (shipped 2026-03-13, archive: [v1.1 roadmap](milestones/v1.1-ROADMAP.md), [v1.1 requirements](milestones/v1.1-REQUIREMENTS.md))
- 🚧 **v3.0 Admin Panel** - Phases 7-15 + 12.1 (in progress)
- 📋 **v2.0 Strategic Nurturing** - Not yet decomposed into phases

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
- [ ] **Phase 12: Agent Config + Feature Flags** - Config editor with diff/rollback, feature flag toggles, MCP/API endpoint config + impact assessment and rollback skills
- [ ] **Phase 12.1: Agent Knowledge Base** - AdminAgent tools for uploading docs/images/videos as agent training data, system-scope RAG, knowledge management + curation skill
- [ ] **Phase 13: Interactive Impersonation** - Super-admin interactive mode, endpoint allow-list, notification suppression, 30-min expiry + user intelligence skills
- [ ] **Phase 14: Billing Dashboard** - MRR/ARR/churn revenue dashboard, Stripe metrics, refund confirm-tier tool + analytics interpretation and revenue forecasting skills
- [ ] **Phase 15: Approval Oversight + Permissions + Role Management** - Cross-user approvals, admin override, autonomy tier editor, multi-tier admin roles + governance skills and daily operational digest

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
**Plans**: TBD

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
**Plans**: TBD

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
**Plans**: TBD

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
**Plans**: TBD

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
| 12. Agent Config + Feature Flags | v3.0 | 0/3 | Not started | - |
| 12.1. Agent Knowledge Base | v3.0 | 0/TBD | Not started | - |
| 13. Interactive Impersonation | v3.0 | 0/TBD | Not started | - |
| 14. Billing Dashboard | v3.0 | 0/TBD | Not started | - |
| 15. Approval Oversight + Permissions UI | v3.0 | 0/TBD | Not started | - |
