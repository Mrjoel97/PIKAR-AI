# Roadmap: pikar-ai

## Milestones

- ✅ **v1.0 Core Reliability** - Phase 1 (shipped 2026-03-04)
- 🚧 **v1.1 Production Readiness** - Phases 2-6 (in progress)
- 📋 **v2.0 Strategic Nurturing** - Phases 7+ (planned)

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

### 🚧 v1.1 Production Readiness (In Progress)

**Milestone Goal:** Bridge all gaps between codebase and Supabase, resolve async blocking, align frontend-backend, and harden for production deployment.

## Phase Details

### Phase 2: Database Alignment
**Goal**: The Supabase schema and codebase are in full agreement — no missing tables, no missing columns, no stale migrations
**Depends on**: Phase 1
**Requirements**: DB-01, DB-02, DB-03, DB-04
**Success Criteria** (what must be TRUE):
  1. The existing content/workspace tables (`content_bundles`, `content_bundle_deliverables`, `workspace_items`) remain queryable and the active service layer writes the aligned contract, including audit ownership fields
  2. The `skills` table exposes `agent_ids` as `jsonb` and the runtime/custom-skill flows operate against that contract without schema errors
  3. Supabase migrations are the only schema authority in the repo; Alembic and stale SQLAlchemy migration entrypoints are removed
  4. Legacy ORM/database scaffolding that no longer matches Supabase is removed or neutralized so it cannot drift independently
**Plans**: 1 plan

Plans:
- [x] 02-01: Align skills/custom-skills schema, add content audit fields, and remove stale Alembic surfaces

Verification status:
- Targeted unit tests passed on 2026-03-12 and 2026-03-13
- Local database validation completed on 2026-03-13 through direct container replay of the pending migration chain
- Verified local schema includes `skills.agent_ids` as `jsonb`, `custom_skills` with the required runtime columns, and `created_by` on the content bundle tables

### Phase 3: Async Safety
**Goal**: No service method blocks the Python event loop — all database and cache calls are async-safe
**Depends on**: Phase 2
**Requirements**: ASYNC-01, ASYNC-02, ASYNC-03, ASYNC-04
**Success Criteria** (what must be TRUE):
  1. Running the full service layer under asyncio does not produce "blocking call in async context" warnings or event-loop stalls
  2. All 12 affected services (analytics, campaign, compliance, task, support_ticket, recruitment, financial, content, initiative, onboarding, report_scheduler, journey_audit) use execute_async() exclusively
  3. DatabaseSkillLoader accesses Redis through the public CacheService interface, not via private _redis access
  4. CacheService initialization is safe to call concurrently from multiple async coroutines without race conditions
**Plans**: TBD

### Phase 4: Frontend-Backend Alignment
**Goal**: The frontend communicates with the backend without auth failures, CORS errors, or type mismatches
**Depends on**: Phase 3
**Requirements**: FE-01, FE-02, FE-03, FE-04, FE-05, FE-06
**Success Criteria** (what must be TRUE):
  1. Browser console shows no CORS errors when the frontend sends x-pikar-persona, user-id, or x-user-id headers
  2. Departments and Approval pages complete authenticated requests without 401 errors
  3. TypeScript compiler reports zero type errors on WorkflowExecution and WorkflowStep interfaces against actual API responses
  4. Initiative detail pages render metadata fields (from JSONB) without undefined or missing field errors
  5. Long-running SSE connections on Cloud Run do not drop due to proxy timeout — heartbeat keeps them alive
**Plans**: TBD

### Phase 5: Security Hardening
**Goal**: The application enforces security controls in production — no exposed tokens, no bypassable auth, no missing headers
**Depends on**: Phase 4
**Requirements**: SEC-01, SEC-02, SEC-03, SEC-04, SEC-05
**Success Criteria** (what must be TRUE):
  1. HTTP responses include X-Content-Type-Options, X-Frame-Options, and Strict-Transport-Security headers on every endpoint
  2. Rate limiter rejects requests with invalid or missing JWTs rather than silently falling back to unverified claims
  3. Application logs contain no partial token strings from auth.py
  4. CORS configuration in production rejects wildcard origins and only allows explicitly listed domains
  5. File upload endpoint rejects requests exceeding the defined size limit with a 413 response
**Plans**: TBD

### Phase 6: Configuration and Deployment
**Goal**: The system deploys cleanly with a unified config, correct Docker health signaling, and no dev bypass flags in production
**Depends on**: Phase 5
**Requirements**: CFG-01, CFG-02, CFG-03, CFG-04, CFG-05
**Success Criteria** (what must be TRUE):
  1. A single config path is used throughout the codebase — AppSettings is either used everywhere or removed, with no dead import paths
  2. Redis connection uses one env var name consistently — no split between REDIS_HOST and CACHE_HOST
  3. Docker container reports healthy status via the healthcheck instruction before receiving traffic
  4. SSE endpoint enforces per-user connection limits, rejecting excess connections with a 429 response
  5. Terraform plan for production environment contains no LOCAL_DEV_BYPASS or SKIP_ENV_VALIDATION variables set to true
**Plans**: TBD

## Progress

**Execution Order:** 1 → 2 → 3 → 4 → 5 → 6

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Core Reliability | v1.0 | 2/2 | Complete | 2026-03-04 |
| 2. Database Alignment | v1.1 | 1/1 | Complete | 2026-03-13 |
| 3. Async Safety | v1.1 | 0/TBD | Not started | - |
| 4. Frontend-Backend Alignment | v1.1 | 0/TBD | Not started | - |
| 5. Security Hardening | v1.1 | 0/TBD | Not started | - |
| 6. Configuration and Deployment | v1.1 | 0/TBD | Not started | - |
