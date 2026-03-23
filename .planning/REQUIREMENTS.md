# Requirements: pikar-ai v3.0 Admin Panel

**Defined:** 2026-03-21
**Core Value:** AI-first admin panel giving the founder a single chat-centered interface to manage the entire platform — users, monitoring, integrations, analytics, configuration, billing, and approvals

## v3.0 Requirements

### Authentication & Authorization

- [x] **AUTH-01**: Admin can access admin panel when their email is in ADMIN_EMAILS env var
- [x] **AUTH-02**: Admin can access admin panel when they have admin role in user_roles table
- [x] **AUTH-03**: System grants access via OR logic (either env allowlist or DB role)
- [x] **AUTH-04**: Admin email check runs server-side only, never exposed in client bundle
- [x] **AUTH-05**: Non-admin users are redirected away from admin routes (server-side AdminGuard)

### AI Admin Assistant

- [x] **ASST-01**: Admin can chat with AI Admin Assistant via persistent SSE chat panel
- [ ] **ASST-02**: AdminAgent has 30+ tools across 7 domains (users, monitoring, integrations, analytics, config, billing, approvals)
- [x] **ASST-03**: Each tool action has a Python-enforced autonomy tier (auto/confirm/blocked)
- [x] **ASST-04**: Confirm-tier actions show a confirmation card with action details and Confirm/Reject buttons
- [x] **ASST-05**: Confirmation tokens are UUID-based with atomic single-consumption (no double-execution)
- [x] **ASST-06**: Admin chat sessions persist across page refreshes (admin_chat_sessions table)

### Health Monitoring

- [x] **HLTH-01**: System pings all /health/* endpoints concurrently via httpx + asyncio.gather()
- [x] **HLTH-02**: Cloud Scheduler triggers health check loop every 60 seconds
- [x] **HLTH-03**: System auto-creates incidents when endpoints fail and tracks recovery
- [x] **HLTH-04**: Admin can view monitoring dashboard with sparkline charts and status cards
- [x] **HLTH-05**: Dashboard shows stale-data warning if latest check is >5 minutes old
- [x] **HLTH-06**: Health results write directly to Supabase (not through monitored service)

### User Management

- [x] **USER-01**: Admin can search, filter, and paginate users in a table view
- [x] **USER-02**: Admin can suspend and unsuspend user accounts
- [x] **USER-03**: Admin can view impersonation (see app as any user, read-only, non-dismissible banner)
- [ ] **USER-04**: Super admin can use interactive impersonation (allow-listed endpoints, notification suppression, 30-min expiry)
- [x] **USER-05**: Admin can switch a user's persona

### Security & Audit

- [x] **AUDT-01**: All admin actions logged to admin_audit_log with source tags (manual/ai_agent/impersonation/monitoring_loop)
- [x] **AUDT-02**: API keys encrypted with MultiFernet (supports key rotation from day one)
- [x] **AUDT-03**: Admin can browse and filter audit trail entries in UI
- [ ] **AUDT-04**: Impersonation actions tagged with impersonation_session_id in audit log

### Analytics

- [x] **ANLT-01**: Admin can view usage dashboards (DAU, MAU, message volume, workflow activity)
- [x] **ANLT-02**: Admin can view per-agent effectiveness metrics (success rate, avg response time)
- [ ] **ANLT-03**: Admin can view billing dashboard (MRR, ARR, churn, plan distribution)
- [x] **ANLT-04**: Admin can view feature usage activities and API call activities
- [x] **ANLT-05**: Admin can view configuration status overview

### External Integrations

- [x] **INTG-01**: Admin can connect Sentry and view error issues via server-side proxy
- [x] **INTG-02**: Admin can connect PostHog and view product analytics via server-side proxy
- [x] **INTG-03**: Admin can connect GitHub and view PRs/issues via server-side proxy
- [x] **INTG-04**: Admin can connect Stripe and view revenue metrics via server-side proxy
- [x] **INTG-05**: Integration API keys stored with Fernet encryption, managed from UI
- [x] **INTG-06**: API proxy responses cached in Redis (2-5 min TTL) with per-session call budgets

### Configuration Management

- [x] **CONF-01**: Admin can edit agent instructions with before/after diff display
- [x] **CONF-02**: System tracks config version history with one-click rollback
- [x] **CONF-03**: Admin can toggle feature flags from UI
- [x] **CONF-04**: Admin can configure per-action autonomy tiers (auto/confirm/blocked)
- [x] **CONF-05**: Admin can manage MCP server and API endpoint configurations

### Agent Knowledge Base

- [x] **KNOW-01**: Admin can instruct the AdminAgent to upload and process documents (PDF, DOCX, TXT, MD) as training data for any specialized agent
- [x] **KNOW-02**: Admin can instruct the AdminAgent to process images (PNG, JPG, SVG) — stored in Supabase Storage with metadata and text descriptions embedded into the knowledge base
- [x] **KNOW-03**: Admin can instruct the AdminAgent to process videos — transcripts extracted and chunked into the knowledge base, key frames stored as image references
- [x] **KNOW-04**: Admin can assign uploaded knowledge to specific agents (financial, content, marketing, etc.) or make it globally available to all agents
- [x] **KNOW-05**: Admin can ask the AdminAgent to list, search, and remove knowledge entries per agent — with confirm-tier deletion
- [x] **KNOW-06**: System-scoped knowledge (uploaded by admin) is available to all users' agent queries without duplicating embeddings per user
- [x] **KNOW-07**: Admin can view a knowledge base management page showing upload history, per-agent knowledge counts, and storage usage

### Approval Oversight

- [ ] **APPR-01**: Admin can view and manage all pending approvals across users
- [ ] **APPR-02**: Admin can approve/reject on behalf of users (confirm-tier action)

### Role Management

- [ ] **ROLE-01**: Super admin can create admin accounts and assign roles (junior_admin, senior_admin, admin, super_admin)
- [ ] **ROLE-02**: Super admin can define per-role access permissions (which admin sections and actions each role can access)
- [ ] **ROLE-03**: Senior admin has access to all admin features except role management
- [ ] **ROLE-04**: Junior admin has read-only access by default, with configurable write permissions per section

### AI Admin Skills

Skills are reasoning patterns and prompt-injected capabilities that make the AdminAgent smarter — going beyond raw tool calls to interpret data, detect patterns, and provide actionable recommendations.

#### Diagnostics & Troubleshooting (Phase 11)

- [x] **SKIL-01**: AdminAgent can correlate errors across Sentry, PostHog, and health incidents to suggest probable root causes — not just "endpoint X is down" but "Sentry shows OOM errors on the embeddings worker, which explains the /health/embeddings failures"
- [x] **SKIL-02**: AdminAgent can detect response time degradation trends and proactively alert before they become incidents — comparing current P95 against 7-day rolling baseline

#### User Intelligence (Phase 13)

- [ ] **SKIL-03**: AdminAgent can identify at-risk users by correlating declining usage (messages, workflows) with billing status and last login — surfaces a "watch list" when asked about user health
- [ ] **SKIL-04**: AdminAgent provides structured support playbooks during interactive impersonation — suggests common troubleshooting steps based on the user's recent errors and usage patterns

#### Analytics Interpretation (Phase 14)

- [ ] **SKIL-05**: AdminAgent can detect statistical anomalies in DAU/MAU, agent effectiveness, and feature usage — flags when metrics deviate >2 standard deviations from 30-day baseline
- [ ] **SKIL-06**: AdminAgent can generate executive summary narratives from raw analytics — translating numbers into "DAU grew 12% week-over-week, driven by the content agent's 40% increase in usage" with actionable recommendations

#### Configuration Management (Phase 12)

- [x] **SKIL-07**: AdminAgent can assess impact of agent config changes by analyzing which workflows depend on the target agent — warns before applying changes that affect high-traffic agents
- [x] **SKIL-08**: AdminAgent can recommend rollback when a config change correlates with degraded agent effectiveness metrics — compares pre/post-change performance windows

#### Knowledge Curation (Phase 12.1)

- [x] **SKIL-09**: AdminAgent can validate uploaded training data for relevance, detect near-duplicate content across existing knowledge entries, and recommend optimal chunking strategy based on document type

#### Revenue & Billing (Phase 14)

- [ ] **SKIL-10**: AdminAgent can forecast MRR/ARR trends from historical subscription data — projects next-month revenue based on current growth rate and known churn
- [ ] **SKIL-11**: AdminAgent can assess refund risk by cross-referencing customer LTV, usage patterns, and subscription tenure before processing confirm-tier refunds

#### Governance & Compliance (Phase 15)

- [ ] **SKIL-12**: AdminAgent can recommend appropriate autonomy tiers for new tools based on risk profile — analyzing whether the action is read-only, mutates user data, or involves financial transactions
- [ ] **SKIL-13**: AdminAgent can summarize audit log entries into human-readable narrative compliance reports — grouping by time period, admin actor, and action severity
- [ ] **SKIL-14**: AdminAgent can suggest per-role permissions when creating junior/senior admin accounts — recommending which sections and write actions each role should access based on the admin's stated responsibilities

#### Operational Awareness (Phase 15 — capstone)

- [ ] **SKIL-15**: AdminAgent produces a daily operational digest covering pending approvals, at-risk users, anomalous metrics, stale integrations, and upcoming subscription expirations — delivered as the first response in a new admin chat session
- [ ] **SKIL-16**: AdminAgent can classify issue severity and route escalations to super admin when severity exceeds the current admin's role scope — with structured escalation context (what happened, what was tried, what's needed)

## Future Requirements

### Retention & Advanced Analytics

- **RETN-01**: Retention cohort analysis (needs 3+ months user data)
- **RETN-02**: Conversion funnel analysis
- **RETN-03**: Bulk CSV export of analytics data

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-tenant admin (separate organizations with own admin teams) | Single-org admin hierarchy sufficient for now |
| Real-time WebSocket monitoring | SSE + 30s polling is indistinguishable at this scale |
| Custom admin theming | Uses existing app design system |
| Admin mobile app | Desktop-first admin panel, destructive actions require deliberate desktop interaction |
| AI-generated code deployments from admin chat | Catastrophic blast radius |
| Decrypted API keys displayed in browser | XSS exposure risk |
| CodeRabbit integration | Deprioritized — Sentry, PostHog, GitHub, Stripe cover core needs |

## Traceability

| Requirement | Phase | Status | Notes |
|-------------|-------|--------|-------|
| AUTH-01 | Phase 7 | Complete | |
| AUTH-02 | Phase 7 | Complete | |
| AUTH-03 | Phase 7 | Complete | |
| AUTH-04 | Phase 7 | Complete | |
| AUTH-05 | Phase 7 | Complete | |
| ASST-01 | Phase 7 | Complete | |
| ASST-02 | Phases 8-15 | Pending | Cross-phase: foundation in Phase 7 (1 tool + autonomy infra), tools added incrementally in Phases 8-15. Complete when all 7 domains have tools. |
| ASST-03 | Phase 7 | Complete | |
| ASST-04 | Phase 7 | Complete | |
| ASST-05 | Phase 7 | Complete | |
| ASST-06 | Phase 7 | Complete | |
| AUDT-01 | Phase 7 | Complete | |
| AUDT-02 | Phase 7 | Complete | |
| AUDT-03 | Phase 7 | Complete | |
| AUDT-04 | Phase 13 | Pending | Requires impersonation (Phase 9/13). Schema-ready: nullable impersonation_session_id column added in Phase 7 migration. |
| HLTH-01 | Phase 8 | Complete | |
| HLTH-02 | Phase 8 | Complete | |
| HLTH-03 | Phase 8 | Complete | |
| HLTH-04 | Phase 8 | Complete | |
| HLTH-05 | Phase 8 | Complete | |
| HLTH-06 | Phase 8 | Complete | |
| USER-01 | Phase 9 | Complete | |
| USER-02 | Phase 9 | Complete | |
| USER-03 | Phase 9 | Complete | |
| USER-05 | Phase 9 | Complete | |
| ANLT-01 | Phase 10 | Complete | |
| ANLT-02 | Phase 10 | Complete | |
| ANLT-04 | Phase 10 | Complete | |
| ANLT-05 | Phase 10 | Complete | |
| INTG-01 | Phase 11 | Complete | |
| INTG-02 | Phase 11 | Complete | |
| INTG-03 | Phase 11 | Complete | |
| INTG-04 | Phase 11 | Complete | |
| INTG-05 | Phase 11 | Complete | |
| INTG-06 | Phase 11 | Complete | |
| CONF-01 | Phase 12 | Complete | |
| CONF-02 | Phase 12 | Complete | |
| CONF-03 | Phase 12 | Complete | |
| CONF-04 | Phase 12 | Complete | |
| CONF-05 | Phase 12 | Complete | |
| KNOW-01 | Phase 12.1 | Complete | |
| KNOW-02 | Phase 12.1 | Complete | |
| KNOW-03 | Phase 12.1 | Complete | |
| KNOW-04 | Phase 12.1 | Complete | |
| KNOW-05 | Phase 12.1 | Complete | |
| KNOW-06 | Phase 12.1 | Complete | |
| KNOW-07 | Phase 12.1 | Complete | |
| USER-04 | Phase 13 | Pending | |
| ANLT-03 | Phase 14 | Pending | |
| APPR-01 | Phase 15 | Pending | |
| APPR-02 | Phase 15 | Pending | |
| ROLE-01 | Phase 15 | Pending | |
| ROLE-02 | Phase 15 | Pending | |
| ROLE-03 | Phase 15 | Pending | |
| ROLE-04 | Phase 15 | Pending | |
| SKIL-01 | Phase 11 | Complete | Cross-service error correlation (requires Sentry + PostHog + health data) |
| SKIL-02 | Phase 11 | Complete | Performance trend detection (requires integration metrics) |
| SKIL-03 | Phase 13 | Pending | At-risk user identification (requires user + billing + usage data) |
| SKIL-04 | Phase 13 | Pending | Impersonation support playbooks (requires interactive impersonation) |
| SKIL-05 | Phase 14 | Pending | Anomaly detection in analytics (requires analytics + billing data) |
| SKIL-06 | Phase 14 | Pending | Executive summary narration (requires analytics + billing data) |
| SKIL-07 | Phase 12 | Complete | Config change impact assessment (requires agent config infrastructure) |
| SKIL-08 | Phase 12 | Complete | Config rollback recommendation (requires config history + effectiveness metrics) |
| SKIL-09 | Phase 12.1 | Complete | Knowledge validation and dedup (requires knowledge base infrastructure) |
| SKIL-10 | Phase 14 | Pending | Revenue forecasting (requires Stripe integration data) |
| SKIL-11 | Phase 14 | Pending | Refund risk assessment (requires Stripe + usage data) |
| SKIL-12 | Phase 15 | Pending | Autonomy tier recommendation (requires full tool inventory) |
| SKIL-13 | Phase 15 | Pending | Audit narrative reports (requires full audit trail data) |
| SKIL-14 | Phase 15 | Pending | Role permission suggestions (requires role management) |
| SKIL-15 | Phase 15 | Pending | Daily operational digest (capstone — requires all prior domains) |
| SKIL-16 | Phase 15 | Pending | Severity classification and escalation routing (requires role hierarchy) |

**Coverage:**
- v3.0 requirements: 71 total
- Mapped to phases: 71
- Unmapped: 0

---
*Requirements defined: 2026-03-21*
*Last updated: 2026-03-22 — Added 16 AI Admin Skills requirements (SKIL-01 through SKIL-16) mapped to Phases 11-15*