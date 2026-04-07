# Requirements: Pikar AI v7.0

**Defined:** 2026-04-06
**Core Value:** Users describe what they want in natural language and the system autonomously generates, manages, and grows their business operations

## v7.0 Requirements

Requirements for Production Readiness & Beta Launch. Each maps to roadmap phases.

### Security & Auth Hardening

- [ ] **AUTH-01**: User routes (/dashboard/*, /settings/*, /admin/*) are protected server-side via Next.js middleware — unauthenticated requests redirect to login
- [x] **AUTH-02**: User sees a meaningful error boundary UI when a page or component crashes, not a blank screen
- [x] **AUTH-03**: Admin can assign roles (admin, member, viewer) to workspace users via RBAC system
- [ ] **AUTH-04**: User actions that modify data are logged in an audit trail with actor, action, target, and timestamp
- [ ] **AUTH-05**: Admin can view audit trail logs filtered by user, action type, and date range

### Billing & Payments

- [ ] **BILL-01**: User can complete Stripe checkout flow and receive an active subscription
- [ ] **BILL-02**: Stripe webhook correctly processes subscription lifecycle events (created, updated, canceled, payment_failed)
- [ ] **BILL-03**: User subscription status is reflected in real-time in the app (active, past_due, canceled)
- [ ] **BILL-04**: Admin can view billing dashboard showing active subscriptions, MRR, and churn metrics
- [ ] **BILL-05**: User can manage their subscription (upgrade, downgrade, cancel) via Stripe Customer Portal

### Observability & Monitoring

- [ ] **OBS-01**: Application errors are captured and reported to Sentry with stack traces, user context, and request metadata
- [ ] **OBS-02**: Admin can view a monitoring dashboard showing agent response latency (p50, p95, p99)
- [ ] **OBS-03**: Admin can view error rate trends (by endpoint, by agent, by time period)
- [ ] **OBS-04**: Admin can view AI cost tracking (token usage per agent, per user, per day)
- [ ] **OBS-05**: Health endpoints return structured status for all critical dependencies (Supabase, Redis, Gemini, integrations)

### Load & Stress Testing

- [ ] **LOAD-01**: System handles 100 concurrent authenticated users without degraded response times (p95 < 3s for chat initiation)
- [ ] **LOAD-02**: SSE streaming handles 100 simultaneous connections without dropped connections or memory leaks
- [ ] **LOAD-03**: Database connection pooling is verified to handle concurrent load without exhaustion
- [ ] **LOAD-04**: Load test suite exists and can be run on-demand against staging environment

### Onboarding & UX Polish

- [ ] **UX-01**: User can complete full signup → persona selection → onboarding → first chat flow without errors
- [ ] **UX-02**: Google OAuth flow successfully grants Gmail and Calendar access and persists tokens
- [ ] **UX-03**: Every dashboard page shows a meaningful empty state (not blank) when no data exists
- [ ] **UX-04**: Shell header KPIs display real computed data (not placeholders) for the user's persona
- [ ] **UX-05**: Each agent responds with persona-appropriate tone, depth, and tool selection based on persona-specific instructions

### Persona & Feature Gating

- [ ] **GATE-01**: Features are soft-gated per persona tier — restricted features show upgrade prompts instead of hiding completely
- [ ] **GATE-02**: ExecutiveAgent is persona-aware — routes to appropriate agents and adjusts behavior based on user's persona tier
- [ ] **GATE-03**: Enterprise persona shows real portfolio health metrics computed from active initiatives and workflows
- [ ] **GATE-04**: SME persona has functional department coordination — tasks route to correct department agents with visibility controls

### Multi-User & Teams

- [ ] **TEAM-01**: User can invite team members to a workspace via email
- [ ] **TEAM-02**: Invited user can join workspace and see shared resources (initiatives, workflows, content)
- [ ] **TEAM-03**: Workspace admin can assign and change roles (admin, member) for team members
- [ ] **TEAM-04**: Team members see role-appropriate content — members cannot access admin functions

### Data Compliance

- [ ] **GDPR-01**: User can request full export of their personal data in a standard format (JSON/CSV)
- [ ] **GDPR-02**: User can request account deletion, which removes all personal data and anonymizes audit logs
- [ ] **GDPR-03**: Data deletion cascades correctly through all related tables (sessions, initiatives, workflows, content, integrations)

### Integration Quality

- [ ] **INTG-01**: OAuth connect/disconnect/reconnect cycle works end-to-end for all integration providers without stale token issues
- [ ] **INTG-02**: SSE streaming remains stable under concurrent multi-user load (no cross-session data leakage)
- [ ] **INTG-03**: Multi-user sessions maintain isolation — User A's chat context never bleeds into User B's session

### RAG Hardening

- [ ] **RAG-01**: Knowledge Vault ingestion processes documents and produces searchable embeddings with >80% relevance on test queries
- [ ] **RAG-02**: Knowledge search returns results within 2 seconds for typical queries
- [ ] **RAG-03**: RAG pipeline handles concurrent ingestion and search without corruption or deadlocks

## v8.0 Requirements (Deferred)

### Builder Dashboard
- **BLDR-01**: Builder dashboard with project status and resume capability
- **BLDR-02**: One-click deploy to public URL

### Advanced Enterprise
- **ENT-01**: SSO/SAML authentication for enterprise customers
- **ENT-02**: Data residency controls (region-specific storage)
- **ENT-03**: SOC 2 compliance certification preparation

## Out of Scope

| Feature | Reason |
|---------|--------|
| SSO/SAML authentication | Enterprise-only, not needed for solopreneur beta |
| Data residency controls | Requires infrastructure changes beyond this milestone |
| SOC 2 certification | Multi-month process, start after beta proves product-market fit |
| Mobile native app | Web-first, Capacitor hybrid covers mobile needs |
| Real-time WebSocket migration | SSE/polling sufficient for current scale |
| Multi-tenant admin | Founder-only admin for now |
| Payment enforcement on feature gates | Soft gating only — upgrade prompts, no hard blocks |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 49 | Pending |
| AUTH-02 | Phase 49 | Complete |
| AUTH-03 | Phase 49 | Complete |
| AUTH-04 | Phase 49 | Pending |
| AUTH-05 | Phase 49 | Pending |
| BILL-01 | Phase 50 | Pending |
| BILL-02 | Phase 50 | Pending |
| BILL-03 | Phase 50 | Pending |
| BILL-04 | Phase 50 | Pending |
| BILL-05 | Phase 50 | Pending |
| OBS-01 | Phase 51 | Pending |
| OBS-02 | Phase 51 | Pending |
| OBS-03 | Phase 51 | Pending |
| OBS-04 | Phase 51 | Pending |
| OBS-05 | Phase 51 | Pending |
| LOAD-01 | Phase 55 | Pending |
| LOAD-02 | Phase 55 | Pending |
| LOAD-03 | Phase 55 | Pending |
| LOAD-04 | Phase 55 | Pending |
| UX-01 | Phase 54 | Pending |
| UX-02 | Phase 54 | Pending |
| UX-03 | Phase 54 | Pending |
| UX-04 | Phase 52 | Pending |
| UX-05 | Phase 52 | Pending |
| GATE-01 | Phase 52 | Pending |
| GATE-02 | Phase 52 | Pending |
| GATE-03 | Phase 52 | Pending |
| GATE-04 | Phase 52 | Pending |
| TEAM-01 | Phase 53 | Pending |
| TEAM-02 | Phase 53 | Pending |
| TEAM-03 | Phase 53 | Pending |
| TEAM-04 | Phase 53 | Pending |
| GDPR-01 | Phase 56 | Pending |
| GDPR-02 | Phase 56 | Pending |
| GDPR-03 | Phase 56 | Pending |
| INTG-01 | Phase 55 | Pending |
| INTG-02 | Phase 55 | Pending |
| INTG-03 | Phase 55 | Pending |
| RAG-01 | Phase 56 | Pending |
| RAG-02 | Phase 56 | Pending |
| RAG-03 | Phase 56 | Pending |

**Coverage:**
- v7.0 requirements: 41 total (note: 41 requirements defined, header previously stated 40)
- Mapped to phases: 41
- Unmapped: 0

---
*Requirements defined: 2026-04-06*
*Last updated: 2026-04-06 after roadmap creation — traceability complete*
