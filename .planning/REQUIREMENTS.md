# Requirements: Pikar-AI

**Defined:** 2026-03-12
**Core Value:** Reliable, production-ready multi-agent AI executive system

## v1.1 Requirements

Requirements for production readiness. Each maps to roadmap phases.

### Database Alignment

- [ ] **DB-01**: Missing tables created in Supabase: content_bundles, content_bundle_deliverables, workspace_items
- [ ] **DB-02**: Missing column added to skills table: agent_ids (jsonb)
- [ ] **DB-03**: Alembic migration regenerated or removed to match Supabase source of truth
- [ ] **DB-04**: SQLAlchemy ORM models updated to match actual Supabase schema (or removed if unused)

### Async Safety

- [ ] **ASYNC-01**: All service methods using sync .execute() migrated to execute_async() wrapper
- [ ] **ASYNC-02**: Services affected: analytics, campaign, compliance, task, support_ticket, recruitment, financial, content, initiative, onboarding, report_scheduler, journey_audit
- [ ] **ASYNC-03**: DatabaseSkillLoader stops bypassing circuit breaker via private _redis access
- [ ] **ASYNC-04**: CacheService singleton uses async-safe locking for initialization

### Frontend-Backend Alignment

- [ ] **FE-01**: CORS allow_headers includes x-pikar-persona, user-id, x-user-id
- [ ] **FE-02**: Departments page uses fetchWithAuth() instead of raw fetch()
- [ ] **FE-03**: Approval page uses fetchWithAuth() for authenticated requests
- [ ] **FE-04**: Frontend WorkflowExecution/WorkflowStep TypeScript interfaces match backend response schemas
- [ ] **FE-05**: Initiative API response extracts metadata JSONB fields into top-level response fields matching InitiativeOperationalRecord interface
- [ ] **FE-06**: SSE heartbeat/keepalive added to prevent Cloud Run proxy timeouts

### Security Hardening

- [ ] **SEC-01**: Security headers middleware added: X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security
- [ ] **SEC-02**: Rate limiter JWT decode requires valid secret (no unverified fallback)
- [ ] **SEC-03**: Token logging removed from auth.py (partial token exposure)
- [ ] **SEC-04**: CORS wildcard explicitly rejected in production environment
- [ ] **SEC-05**: File upload size validation added to files router

### Configuration & Deployment

- [ ] **CFG-01**: Config system unified: either AppSettings used everywhere or removed as dead code
- [ ] **CFG-02**: Redis env var naming aligned (REDIS_HOST vs CACHE_HOST inconsistency resolved)
- [ ] **CFG-03**: Dockerfile healthcheck instruction added
- [ ] **CFG-04**: SSE endpoint rate limiting added (per-user connection limits)
- [ ] **CFG-05**: Bypass flags (LOCAL_DEV_BYPASS, SKIP_ENV_VALIDATION) blocked in production Terraform

## v2 Requirements

Deferred to future release.

### Strategic Nurturing

- **STRAT-01**: Enhanced StrategicPlanningAgent for multi-phase roadmap generation
- **STRAT-02**: Automated Product Brief generator (PDF/Markdown)
- **STRAT-03**: ExecutiveAgent detects "Nurture to Venture" transitions

### Performance

- **PERF-01**: Distributed tracing with OpenTelemetry
- **PERF-02**: Structured JSON logging for Cloud Logging
- **PERF-03**: Connected accounts token encryption at rest

## Out of Scope

| Feature | Reason |
|---------|--------|
| New agent capabilities | Remediation milestone, no new features |
| Frontend UI redesign | Only fixing alignment, not adding features |
| Multi-tenant RLS overhaul | RLS already exists on all 76 tables |
| Mobile app | Web-first, not in scope |
| OAuth provider expansion | Current auth flow sufficient |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DB-01 | TBD | Pending |
| DB-02 | TBD | Pending |
| DB-03 | TBD | Pending |
| DB-04 | TBD | Pending |
| ASYNC-01 | TBD | Pending |
| ASYNC-02 | TBD | Pending |
| ASYNC-03 | TBD | Pending |
| ASYNC-04 | TBD | Pending |
| FE-01 | TBD | Pending |
| FE-02 | TBD | Pending |
| FE-03 | TBD | Pending |
| FE-04 | TBD | Pending |
| FE-05 | TBD | Pending |
| FE-06 | TBD | Pending |
| SEC-01 | TBD | Pending |
| SEC-02 | TBD | Pending |
| SEC-03 | TBD | Pending |
| SEC-04 | TBD | Pending |
| SEC-05 | TBD | Pending |
| CFG-01 | TBD | Pending |
| CFG-02 | TBD | Pending |
| CFG-03 | TBD | Pending |
| CFG-04 | TBD | Pending |
| CFG-05 | TBD | Pending |

**Coverage:**
- v1.1 requirements: 24 total
- Mapped to phases: 0
- Unmapped: 24

---
*Requirements defined: 2026-03-12*
*Last updated: 2026-03-12 after deep codebase + Supabase analysis*
