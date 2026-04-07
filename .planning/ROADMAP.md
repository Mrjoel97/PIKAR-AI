# Roadmap: pikar-ai

## Milestones

- ✅ **v1.0 Core Reliability** - Phase 1 (shipped 2026-03-04, archive: [v1.0 roadmap](milestones/v1.0-ROADMAP.md))
- ✅ **v1.1 Production Readiness** - Phases 2-6 (shipped 2026-03-13, archive: [v1.1 roadmap](milestones/v1.1-ROADMAP.md), [v1.1 requirements](milestones/v1.1-REQUIREMENTS.md))
- ✅ **v2.0 Broader App Builder** - Phases 16-22 (shipped 2026-03-23, archive: [v2.0 roadmap](milestones/v2.0-ROADMAP.md), [v2.0 requirements](milestones/v2.0-REQUIREMENTS.md))
- ✅ **v3.0 Admin Panel** - Phases 7-15 + 12.1 (shipped 2026-03-26, archive: [v3.0 roadmap](milestones/v3.0-ROADMAP.md), [v3.0 requirements](milestones/v3.0-REQUIREMENTS.md))
- ✅ **v4.0 Production Scale & Persona UX** - Phases 24-31 (shipped 2026-04-03, archive: [v4.0 roadmap](milestones/v4.0-ROADMAP.md), [v4.0 requirements](milestones/v4.0-REQUIREMENTS.md))
- ✅ **v5.0 Persona Production Readiness** - Phases 32-37 (shipped 2026-04-03, archive: [v5.0 roadmap](milestones/v5.0-ROADMAP.md), [v5.0 requirements](milestones/v5.0-REQUIREMENTS.md))
- ✅ **v6.0 Real-World Integration & Solopreneur Unlock** - Phases 38-48 (shipped 2026-04-06, archive: [v6.0 roadmap](milestones/v6.0-ROADMAP.md), [v6.0 requirements](milestones/v6.0-REQUIREMENTS.md))
- 🚧 **v7.0 Production Readiness & Beta Launch** - Phases 49-56 (in progress)

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

<details>
<summary>✅ v2.0 Broader App Builder (Phases 16-22) - SHIPPED 2026-03-23</summary>

See archived roadmap: [milestones/v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md)

</details>

<details>
<summary>✅ v3.0 Admin Panel (Phases 7-15 + 12.1) - SHIPPED 2026-03-26</summary>

See archived roadmap: [milestones/v3.0-ROADMAP.md](milestones/v3.0-ROADMAP.md)

</details>

<details>
<summary>✅ v4.0 Production Scale & Persona UX (Phases 26-31) - SHIPPED 2026-04-03</summary>

**Phases completed:** 7 phases (26-31 + 27.1), all plans complete
**Delivered:** Async Supabase, production deployment hardening, security headers, persona agent equalization, persona-specific frontend UX, default widgets, empty states.

</details>

<details>
<summary>✅ v5.0 Persona Production Readiness (Phases 32-37) - SHIPPED 2026-04-03</summary>

**Phases completed:** 6 phases (32-37), all plans complete
**Delivered:** Feature gating, backend persona awareness, computed KPIs, teams & RBAC, enterprise governance, SME department coordination.

</details>

<details>
<summary>✅ v6.0 Real-World Integration & Solopreneur Unlock (Phases 38-48) — SHIPPED 2026-04-06</summary>

- [x] Phase 38: Solopreneur Unlock & Tool Honesty (3/3 plans) — completed 2026-04-04
- [x] Phase 39: Integration Infrastructure (3/3 plans) — completed 2026-04-04
- [x] Phase 40: Data I/O & Document Generation (3/3 plans) — completed 2026-04-04
- [x] Phase 41: Financial Integrations (3/3 plans) — completed 2026-04-04
- [x] Phase 42: CRM & Email Automation (3/3 plans) — completed 2026-04-04
- [x] Phase 43: Ad Platform Integration (3/3 plans) — completed 2026-04-05
- [x] Phase 44: Project Management Integration (3/3 plans) — completed 2026-04-05
- [x] Phase 45: Communication & Notifications (5/5 plans) — completed 2026-04-05
- [x] Phase 46: Analytics & Continuous Intelligence (5/5 plans) — completed 2026-04-06
- [x] Phase 47: Team Collaboration & Webhook Polish (3/3 plans) — completed 2026-04-06
- [x] Phase 48: Notification Event Type Wiring (1/1 plan) — completed 2026-04-06

Full details: [v6.0 roadmap archive](milestones/v6.0-ROADMAP.md)

</details>

---

### 🚧 v7.0 Production Readiness & Beta Launch (In Progress)

**Milestone Goal:** Close all production readiness gaps from the comprehensive audit, harden security, billing, observability, and persona gating, and reach Solopreneur Closed Beta for 100-user batches.

- [x] **Phase 49: Security & Auth Hardening** - Server-side route protection, error boundaries, RBAC, and audit trail
- [ ] **Phase 50: Billing & Payments** - Stripe e2e checkout, subscription lifecycle, admin billing dashboard
- [ ] **Phase 51: Observability & Monitoring** - Sentry error capture, monitoring dashboard, health endpoint hardening
- [ ] **Phase 52: Persona & Feature Gating** - Soft gating with upgrade prompts, persona-aware ExecutiveAgent, enterprise metrics, SME coordination
- [ ] **Phase 53: Multi-User & Teams** - Workspace invites, role assignment, role-scoped content access
- [ ] **Phase 54: Onboarding & UX Polish** - End-to-end signup flow, Google OAuth, empty states
- [ ] **Phase 55: Integration Quality & Load Testing** - OAuth seam testing, SSE stability, 100-user load tests
- [ ] **Phase 56: GDPR & RAG Hardening** - Data export/deletion, Knowledge Vault embedding quality and performance

## Phase Details

### Phase 49: Security & Auth Hardening
**Goal**: Users and admins are protected by server-side route enforcement, visible error recovery, granular role access, and a complete audit trail
**Depends on**: Phase 48 (v6.0 complete)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05
**Success Criteria** (what must be TRUE):
  1. Visiting /dashboard, /settings, or /admin without a valid session redirects to the login page — no unauthenticated page content is served
  2. When a React component throws an unhandled error, the user sees a meaningful error UI with a recovery option instead of a blank screen
  3. A workspace admin can assign admin, member, or viewer roles to other users via the RBAC interface
  4. Every data-mutating action (create, update, delete) produces an audit log row with actor identity, action name, target resource, and timestamp
  5. An admin can filter and view audit logs by user, action type, and date range
**Plans**: 5 plans
  - [x] 49-01-PLAN.md — AUTH-01: Server-side Next.js proxy for protected route enforcement
  - [x] 49-02-PLAN.md — AUTH-02: RootErrorBoundary component wired into root and personas layouts
  - [x] 49-03-PLAN.md — AUTH-03: Workspace RBAC role assignment UI consolidation (admin/editor/viewer)
  - [x] 49-04-PLAN.md — AUTH-04: Centralised AuditLogMiddleware for governance_audit_log mutation coverage
  - [x] 49-05-PLAN.md — AUTH-05: Admin governance audit log viewer with user/action/date filters

### Phase 50: Billing & Payments
**Goal**: Users can purchase and manage subscriptions end-to-end through Stripe, and admins have visibility into billing health
**Depends on**: Phase 49
**Requirements**: BILL-01, BILL-02, BILL-03, BILL-04, BILL-05
**Success Criteria** (what must be TRUE):
  1. A user who completes Stripe checkout receives an active subscription reflected immediately in their account
  2. Stripe webhook events (created, updated, canceled, payment_failed) update the user's subscription status in the app without manual intervention
  3. The user's subscription badge (active / past_due / canceled) updates in real-time without a page reload
  4. An admin can view a billing dashboard showing current active subscriptions, MRR, and churn rate
  5. A user can upgrade, downgrade, or cancel their plan via the Stripe Customer Portal without contacting support
**Plans**: 4 plans
  - [ ] 50-01-PLAN.md — BILL-02: Stripe webhook idempotency + missing lifecycle events (customer.subscription.created, invoice.payment_succeeded)
  - [ ] 50-02-PLAN.md — BILL-03: Supabase Realtime SubscriptionContext + SubscriptionBadge component
  - [ ] 50-03-PLAN.md — BILL-04: BillingMetricsService with DB-native MRR and real time-windowed churn rate
  - [ ] 50-04-PLAN.md — BILL-01 + BILL-05: SubscriptionBadge placement in PremiumShell + Stripe CLI end-to-end UAT

### Phase 51: Observability & Monitoring
**Goal**: Errors are automatically captured with full context and admins can monitor agent performance, error trends, and AI costs in real-time
**Depends on**: Phase 49
**Requirements**: OBS-01, OBS-02, OBS-03, OBS-04, OBS-05
**Success Criteria** (what must be TRUE):
  1. An unhandled exception in any request produces a Sentry event containing the stack trace, user identity, and request metadata
  2. An admin can view a dashboard showing agent response latency at p50, p95, and p99 percentiles
  3. An admin can drill into error rate trends filtered by endpoint, agent, and time period
  4. An admin can see AI token usage broken down by agent, user, and day
  5. All health endpoints return structured JSON status for Supabase, Redis, Gemini, and active integrations
**Plans**: TBD

### Phase 52: Persona & Feature Gating
**Goal**: Each persona tier sees appropriate features with upgrade prompts, the ExecutiveAgent adapts its routing and tone per persona, and enterprise/SME-specific metrics are real
**Depends on**: Phase 50
**Requirements**: GATE-01, GATE-02, GATE-03, GATE-04, UX-04, UX-05
**Success Criteria** (what must be TRUE):
  1. A user on a restricted tier sees an upgrade prompt (not a blank space or error) when they access a feature above their tier
  2. The ExecutiveAgent routes to tier-appropriate agents and adjusts response depth and tool selection based on the user's persona
  3. Enterprise users see a portfolio health dashboard populated with real data from active initiatives and workflows — not placeholder values
  4. SME users can route tasks to specific department agents and see role-filtered results per the department's visibility rules
  5. Shell header KPIs display computed values derived from the user's real data for their persona tier
**Plans**: TBD

### Phase 53: Multi-User & Teams
**Goal**: Workspace owners can invite and manage team members with role-based access, and members see only what their role permits
**Depends on**: Phase 49
**Requirements**: TEAM-01, TEAM-02, TEAM-03, TEAM-04
**Success Criteria** (what must be TRUE):
  1. A workspace admin can send email invitations to new team members from the workspace settings
  2. An invited user can accept the invitation, join the workspace, and immediately access shared initiatives, workflows, and content
  3. A workspace admin can change a team member's role (admin or member) and the change takes effect on the member's next action
  4. A member cannot access admin-only functions — attempting to do so returns a permission error, not a blank page or crash
**Plans**: TBD

### Phase 54: Onboarding & UX Polish
**Goal**: New users can complete the full signup-to-first-chat journey without errors, Google OAuth persists correctly, and every page has a meaningful empty state
**Depends on**: Phase 52, Phase 53
**Requirements**: UX-01, UX-02, UX-03
**Success Criteria** (what must be TRUE):
  1. A new user can complete signup, select a persona, step through onboarding, and send their first chat message without encountering any errors or dead ends
  2. Google OAuth successfully grants Gmail and Calendar access, persists the tokens, and a subsequent agent action that requires calendar access works without re-authentication
  3. Every dashboard page that can have zero data shows a descriptive empty state UI with a suggested action — no blank panels or loading spinners that never resolve
**Plans**: TBD

### Phase 55: Integration Quality & Load Testing
**Goal**: All OAuth integrations work reliably through connect/disconnect/reconnect cycles, SSE handles concurrent multi-user load without leakage, and the system is verified to sustain 100 concurrent users
**Depends on**: Phase 51
**Requirements**: INTG-01, INTG-02, INTG-03, LOAD-01, LOAD-02, LOAD-03, LOAD-04
**Success Criteria** (what must be TRUE):
  1. An integration can be connected, disconnected, and reconnected for all OAuth providers without leaving stale tokens or broken state
  2. SSE streaming with 100 simultaneous users produces no cross-session data leakage — User A's response never appears in User B's stream
  3. 100 concurrent authenticated users can initiate chats with p95 response time under 3 seconds
  4. Database connection pool handles 100 concurrent requests without exhaustion errors in logs
  5. A load test suite can be executed on-demand against the staging environment and produces a pass/fail report
**Plans**: TBD

### Phase 56: GDPR & RAG Hardening
**Goal**: Users have full control over their personal data through export and deletion, and the Knowledge Vault reliably ingests documents and returns relevant search results
**Depends on**: Phase 55
**Requirements**: GDPR-01, GDPR-02, GDPR-03, RAG-01, RAG-02, RAG-03
**Success Criteria** (what must be TRUE):
  1. A user can request and receive a full export of their personal data as a downloadable JSON or CSV archive
  2. A user can request account deletion, which removes personal data and anonymizes audit log references within a confirmed time window
  3. Deleting an account cascades correctly through all related tables with no orphaned rows in sessions, initiatives, workflows, content, or integrations
  4. A document uploaded to the Knowledge Vault becomes searchable and returns results with greater than 80% relevance on a defined test query set
  5. Knowledge search returns results within 2 seconds under normal load and handles concurrent ingestion without corruption or deadlocks
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 49 → 50 → 51 → 52 → 53 → 54 → 55 → 56

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 49. Security & Auth Hardening | v7.0 | 5/5 | Complete | 2026-04-07 |
| 50. Billing & Payments | 1/4 | In Progress|  | - |
| 51. Observability & Monitoring | v7.0 | 0/? | Not started | - |
| 52. Persona & Feature Gating | v7.0 | 0/? | Not started | - |
| 53. Multi-User & Teams | v7.0 | 0/? | Not started | - |
| 54. Onboarding & UX Polish | v7.0 | 0/? | Not started | - |
| 55. Integration Quality & Load Testing | v7.0 | 0/? | Not started | - |
| 56. GDPR & RAG Hardening | v7.0 | 0/? | Not started | - |
