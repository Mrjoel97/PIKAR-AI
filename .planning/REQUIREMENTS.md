# Requirements: Pikar-AI v5.0 Persona Production Readiness

**Defined:** 2026-04-03
**Core Value:** Users describe what they want and the system autonomously generates and manages business operations — with differentiated experiences per persona tier

## v5.0 Requirements

Requirements to take all 4 personas (Solopreneur/Startup/SME/Enterprise) to 100% production readiness.

### Feature Gating

- [x] **GATE-01**: User sees upgrade prompts when accessing features not included in their persona tier
- [x] **GATE-02**: Backend API endpoints check user's persona tier and return 403 with upgrade message for restricted features
- [ ] **GATE-03**: Centralized tier-to-feature mapping config consumed by frontend sidebar, pages, and backend middleware
- [ ] **GATE-04**: Upgrade prompt component shows tier name, locked feature, and path to upgrade

### Backend Persona Awareness

- [x] **PERS-01**: ExecutiveAgent receives persona-specific system instructions (tone, complexity, terminology)
- [x] **PERS-02**: Each sub-agent receives persona context and adapts its behavior accordingly
- [x] **PERS-03**: Persona context is loaded from user profile on each chat session and injected into agent state

### Computed KPIs

- [ ] **KPI-01**: Solopreneur shell KPIs show real-time computed data (Cash Collected, Weekly Pipeline, Content Consistency)
- [ ] **KPI-02**: Startup shell KPIs show real-time computed data (MRR Growth, Activation & Conversion, Experiment Velocity)
- [ ] **KPI-03**: SME shell KPIs show real-time computed data (Department Performance, Process Cycle Time, Margin & Compliance)
- [ ] **KPI-04**: Enterprise shell KPIs show real-time computed data (Portfolio Health, Risk & Control Coverage, Reporting Quality)
- [ ] **KPI-05**: KPI service provides computed metrics from Supabase data per persona with API endpoint

### Teams & RBAC

- [ ] **TEAM-01**: User can share their workspace with team members (shared initiatives, content, workflows)
- [ ] **TEAM-02**: Admin/Editor/Viewer roles defined with specific permission sets
- [ ] **TEAM-03**: Permission checks enforce role-based access on frontend actions (buttons, forms, navigation)
- [ ] **TEAM-04**: Permission checks enforce role-based access on backend API endpoints
- [ ] **TEAM-05**: User can assign roles to team members in settings UI

### Enterprise Governance

- [ ] **GOV-01**: All significant actions are logged to an audit trail (who/what/when/context) in a dedicated table
- [ ] **GOV-02**: Portfolio health score aggregated from initiative status, risk coverage, and resource allocation
- [ ] **GOV-03**: Governance dashboard page showing audit logs, compliance status, approval chains, control coverage
- [ ] **GOV-04**: Multi-level approval chains (reviewer → approver → executive) for high-impact actions

### SME Department Coordination

- [ ] **DEPT-01**: Workflows can route tasks between departments (cross-department handoffs with status tracking)
- [ ] **DEPT-02**: Per-department dashboard with KPIs, active tasks, and health indicators
- [ ] **DEPT-03**: Agent routes questions to the appropriate department agent based on conversation context

## v6.0 Requirements (Deferred)

### Team Management
- **TEAM-06**: User can invite team members via email with configurable role
- **TEAM-07**: Invitation acceptance flow with account linking
- **TEAM-08**: Team member removal and role change notifications

### Enterprise Advanced
- **GOV-05**: SSO integration (SAML/OIDC)
- **GOV-06**: Custom workflow builder with visual editor (enterprise-exclusive)
- **GOV-07**: Data export API for enterprise reporting systems
- **GOV-08**: SLA monitoring and alerting

### Payment Enforcement
- **BILL-01**: Stripe payment enforcement per tier
- **BILL-02**: Hard feature gating requiring active subscription
- **BILL-03**: Usage-based billing for LLM tokens

## Out of Scope

| Feature | Reason |
|---------|--------|
| SSO (SAML/OIDC) | Complex enterprise feature — deferred to v6.0 |
| Payment/Stripe enforcement | User still fixing registration — deferred to v6.0 |
| Hard payment walls | Explicitly excluded — soft gating only for v5.0 |
| Custom workflow visual editor | High complexity — template-based workflows sufficient for now |
| Native mobile RBAC | Web-first; mobile uses same API permissions |
| Multi-tenant (separate orgs) | Single-org team model sufficient for v5.0 |
| Email invite flow | Deferred to v6.0 — v5.0 uses shared workspace link |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GATE-01 | Phase 32 | Complete |
| GATE-02 | Phase 32 | Complete |
| GATE-03 | Phase 32 | Pending |
| GATE-04 | Phase 32 | Pending |
| PERS-01 | Phase 33 | Complete |
| PERS-02 | Phase 33 | Complete |
| PERS-03 | Phase 33 | Complete |
| KPI-01 | Phase 34 | Pending |
| KPI-02 | Phase 34 | Pending |
| KPI-03 | Phase 34 | Pending |
| KPI-04 | Phase 34 | Pending |
| KPI-05 | Phase 34 | Pending |
| TEAM-01 | Phase 35 | Pending |
| TEAM-02 | Phase 35 | Pending |
| TEAM-03 | Phase 35 | Pending |
| TEAM-04 | Phase 35 | Pending |
| TEAM-05 | Phase 35 | Pending |
| GOV-01 | Phase 36 | Pending |
| GOV-02 | Phase 36 | Pending |
| GOV-03 | Phase 36 | Pending |
| GOV-04 | Phase 36 | Pending |
| DEPT-01 | Phase 37 | Pending |
| DEPT-02 | Phase 37 | Pending |
| DEPT-03 | Phase 37 | Pending |

**Coverage:**
- v5.0 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-03*
*Last updated: 2026-04-03 — traceability complete after roadmap creation*
