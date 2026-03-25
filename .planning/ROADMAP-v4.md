# Roadmap: pikar-ai v4.0 Production Scale & Persona Readiness

**Milestone:** v4.0 Production Scale & Persona Readiness
**Defined:** 2026-03-25
**Phase range:** 24-31 (phases 1-22 used by v1.0/v2.0, phase 23 deferred)
**Total phases:** 8
**Total requirements:** 57

---

## Phases

- [ ] **Phase 24: App Server + Database + Redis Scaling** - Multi-worker uvicorn, Gunicorn process management, thread pool sizing, connection pool tuning, and Redis pool expansion — the infrastructure foundation everything else depends on
- [ ] **Phase 25: SSE Streaming + Distributed Rate Limiting** - Redis-backed SSE connection tracking across replicas, backpressure, and Redis sliding-window rate limits replacing all per-process limiters
- [ ] **Phase 26: Auth Optimization + Security Hardening** - JWT caching, local-only token validation, reduced frontend polling, and CSP/CORS/request-body security headers
- [ ] **Phase 27: Observability** - Sentry (Python + Next.js), OpenTelemetry traces, latency histograms, structured logging, and Slack/email alerting
- [ ] **Phase 28: Feature Flags** - Redis-backed feature flag store with per-user and per-persona targeting, gradual rollout, admin CRUD API, and audit trail
- [ ] **Phase 29: Persona Frontend Differentiation** - Distinct dashboard layouts, persona-gated navigation, feature hiding, tailored onboarding, and differentiated persona shell components
- [ ] **Phase 30: LLM Cost Control** - Per-user daily token budgets, cost recording per request, Gemini burst queue, usage dashboard, and budget threshold alerts
- [ ] **Phase 31: Persona Backend Enforcement** - Middleware persona-tier validation, subscription integration points, tool availability gating, and persona usage analytics

---

## Phase Details

### Phase 24: App Server + Database + Redis Scaling
**Goal**: The backend runs with multiple workers, connection pools sized for production, and Redis scaled to handle distributed workloads at 1000+ concurrent users
**Depends on**: Nothing (infrastructure foundation)
**Requirements**: SERV-01, SERV-02, SERV-03, SERV-04, SERV-05, DBSC-01, DBSC-02, DBSC-03, DBSC-04, RDSC-01, RDSC-02, RDSC-03, RDSC-04
**Success Criteria** (what must be TRUE):
  1. The backend starts with 4+ uvicorn workers under Gunicorn and automatically restarts crashed workers without downtime
  2. Active SSE connections drain before a worker shuts down — no in-flight connections abruptly terminated on deploy
  3. A sustained burst of requests does not exhaust the Supabase or Redis connection pool — /health/connections reports pool utilization within safe bounds
  4. JWT hot-path validation completes without any Supabase network round-trip — measurable via /health/connections latency drop
  5. Redis latency per operation is visible in the health endpoint and memory usage alerts fire before pool exhaustion
**Plans**: 3 plans
Plans:
- [ ] 24-01-PLAN.md — Gunicorn process manager: multi-worker CMD, graceful shutdown, concurrency caps
- [ ] 24-02-PLAN.md — Redis scaling: 200-connection pool, per-op latency tracking, memory alerts, key namespaces
- [ ] 24-03-PLAN.md — DB + auth scaling: 200-worker thread pool, Supabase pool constant, 60s JWT LRU cache

### Phase 25: SSE Streaming + Distributed Rate Limiting
**Goal**: SSE connections are tracked in Redis so all Cloud Run replicas share state, backpressure protects against overload, and rate limits are enforced consistently across processes
**Depends on**: Phase 24 (Redis pool must be scaled before adding Redis-backed tracking)
**Requirements**: SSES-01, SSES-02, SSES-03, SSES-04, SSES-05, RATE-01, RATE-02, RATE-03, RATE-04, RATE-05
**Success Criteria** (what must be TRUE):
  1. A user who opens SSE connections on two different replicas hits the per-user connection limit — the third connection is rejected regardless of which replica it lands on
  2. When a Cloud Run instance crashes, its orphaned SSE connection entries expire via Redis TTL within one TTL window — no stale entries persist indefinitely
  3. New SSE connections are rejected with an appropriate HTTP 503 when the server-wide load threshold is exceeded
  4. API rate limit counters are shared across all replicas — a user who hammers one replica cannot bypass limits by hitting a second replica
  5. Every rate-limited response includes X-RateLimit-Limit, X-RateLimit-Remaining, and Retry-After headers so clients can back off correctly
**Plans**: 2 plans
Plans:
- [ ] 25-01-PLAN.md — Redis-backed SSE connection tracking: async INCR/DECR with TTL, backpressure, SSE rate limiting, health count
- [ ] 25-02-PLAN.md — Distributed rate limiting: Redis sliding-window for API + MCP, rate-limit response headers

### Phase 26: Auth Optimization + Security Hardening
**Goal**: Authentication is fast and resilient, and the application sends correct security headers protecting users from XSS, CSRF, and data leakage
**Depends on**: Phase 24 (Redis LRU cache backing JWT cache requires scaled Redis)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, SECU-01, SECU-02, SECU-03, SECU-04, SECU-05
**Success Criteria** (what must be TRUE):
  1. A repeated request from the same authenticated user within 60 seconds does not trigger a Supabase auth.get_user() network call — token is served from LRU cache
  2. All production API responses include Content-Security-Policy, Referrer-Policy, and X-XSS-Protection headers with correct values
  3. A request body exceeding 10MB is rejected at the middleware layer with HTTP 413 before reaching any route handler
  4. CORS preflight requests from an unlisted origin are rejected in production — no wildcard origins present in response headers
  5. A frontend session with a failed token refresh shows the user a graceful re-login prompt instead of a hard redirect or blank error screen
**Plans**: TBD

### Phase 27: Observability
**Goal**: Errors are automatically captured in Sentry, distributed traces flow to Cloud Trace, latency is measured per endpoint, and on-call alerts fire before users notice problems
**Depends on**: Phase 24 (stable infrastructure before instrumenting it)
**Requirements**: OBSV-01, OBSV-02, OBSV-03, OBSV-04, OBSV-05, OBSV-06
**Success Criteria** (what must be TRUE):
  1. An unhandled Python exception in any route handler creates a Sentry issue automatically, with a stack trace and the originating user's session context
  2. An unhandled React error boundary fires a Sentry event from the frontend with component stack included
  3. A single user request produces a correlated trace visible in Cloud Trace spanning the Next.js frontend call through the FastAPI backend
  4. The 95th-percentile latency for any individual endpoint is readable from structured metrics — no manual log parsing required
  5. A health check failure or sudden error spike sends a Slack or email alert within five minutes of the event
**Plans**: TBD

### Phase 28: Feature Flags
**Goal**: New features can be enabled for specific users or persona tiers without a code deploy, with gradual percentage rollout and a complete audit trail of every change
**Depends on**: Phase 24 (Redis store), Phase 27 (flag changes should be observable)
**Requirements**: FLAG-01, FLAG-02, FLAG-03, FLAG-04, FLAG-05
**Success Criteria** (what must be TRUE):
  1. An admin can toggle a feature flag via the management API and the change takes effect for targeted users within one TTL window — no restart required
  2. A flag scoped to the enterprise persona is invisible to solopreneur users — the feature it gates does not render or respond for them
  3. A flag set to 10% rollout consistently assigns the same subset of users to the enabled bucket across all replicas — no flickering between on/off states for the same user
  4. Every flag create, update, and delete is recorded in the audit trail with the before value, after value, and acting admin identity
**Plans**: TBD

### Phase 29: Persona Frontend Differentiation
**Goal**: Each persona — solopreneur, startup, SME, enterprise — has a visually and functionally distinct frontend experience: different navigation, different dashboard widgets, gated features, and tailored onboarding
**Depends on**: Phase 28 (feature gating logic should use feature flags where appropriate)
**Requirements**: PFUI-01, PFUI-02, PFUI-03, PFUI-04, PFUI-05
**Success Criteria** (what must be TRUE):
  1. A solopreneur user and an enterprise user see different dashboard widget layouts — the enterprise user has additional widgets not present in the solopreneur view
  2. The sidebar navigation for a solopreneur has fewer items than for an enterprise user — at least one enterprise-only nav item is absent from the solopreneur sidebar
  3. An enterprise-only feature — when accessed directly by URL by a solopreneur — shows a gated/upgrade prompt instead of the feature content
  4. First-time users on each persona see a different set of suggested first actions during onboarding — not a single shared list
  5. Each persona shell has a distinct visual identity beyond header color — typography, layout density, or component styling that a user would notice switching between personas
**Plans**: TBD

### Phase 30: LLM Cost Control
**Goal**: Every agent interaction tracks token usage and cost, per-user daily budgets are enforced before requests reach Gemini, and a usage dashboard makes spend visible to users and admins
**Depends on**: Phase 27 (observability must be in place before cost visibility is meaningful), Phase 31 (persona tier affects budget limits)
**Requirements**: COST-01, COST-02, COST-03, COST-04, COST-05
**Success Criteria** (what must be TRUE):
  1. A user who exhausts their daily token budget receives a clear, user-friendly message that their limit is reached — subsequent agent requests are blocked until the budget resets
  2. Every completed agent interaction writes a database row with the request's token count and estimated dollar cost
  3. A burst of concurrent Gemini API calls from one user does not cause API quota errors — the burst queue serializes or throttles them within configured limits
  4. A user can navigate to a usage dashboard page and see their token consumption trend and estimated cost for the past 7 and 30 days
  5. When a user reaches 80% of their daily token budget, they receive an in-app alert before they are hard-blocked
**Plans**: TBD

### Phase 31: Persona Backend Enforcement
**Goal**: The backend enforces persona-tier access rules for every API call — features, agent tools, and usage caps match the user's subscription tier, and usage patterns are tracked for capacity planning
**Depends on**: Phase 28 (feature flags drive tool gating), Phase 29 (frontend gating is meaningful only when backend matches)
**Requirements**: PBEN-01, PBEN-02, PBEN-03, PBEN-04
**Success Criteria** (what must be TRUE):
  1. An API request from a solopreneur user to an enterprise-only endpoint returns HTTP 403 — the middleware rejects it before the route handler executes
  2. The codebase contains defined integration points (hooks or middleware stubs) for a billing/subscription system to upgrade a user's persona tier — not just a hardcoded tier check
  3. A solopreneur user's agent interaction only surfaces solopreneur-allowed tools — enterprise tools are absent from the tool selection step, not just hidden in the UI
  4. Every agent interaction logs the acting user's persona tier to the analytics table — aggregate per-tier usage is queryable without manual log parsing
**Plans**: TBD

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 24. App Server + Database + Redis Scaling | 0/3 | Planned | - |
| 25. SSE Streaming + Distributed Rate Limiting | 0/2 | Planned | - |
| 26. Auth Optimization + Security Hardening | 0/? | Not started | - |
| 27. Observability | 0/? | Not started | - |
| 28. Feature Flags | 0/? | Not started | - |
| 29. Persona Frontend Differentiation | 0/? | Not started | - |
| 30. LLM Cost Control | 0/? | Not started | - |
| 31. Persona Backend Enforcement | 0/? | Not started | - |

---

## Coverage Map

| Requirement | Phase |
|-------------|-------|
| SERV-01 | 24 |
| SERV-02 | 24 |
| SERV-03 | 24 |
| SERV-04 | 24 |
| SERV-05 | 24 |
| DBSC-01 | 24 |
| DBSC-02 | 24 |
| DBSC-03 | 24 |
| DBSC-04 | 24 |
| RDSC-01 | 24 |
| RDSC-02 | 24 |
| RDSC-03 | 24 |
| RDSC-04 | 24 |
| SSES-01 | 25 |
| SSES-02 | 25 |
| SSES-03 | 25 |
| SSES-04 | 25 |
| SSES-05 | 25 |
| RATE-01 | 25 |
| RATE-02 | 25 |
| RATE-03 | 25 |
| RATE-04 | 25 |
| RATE-05 | 25 |
| AUTH-01 | 26 |
| AUTH-02 | 26 |
| AUTH-03 | 26 |
| AUTH-04 | 26 |
| SECU-01 | 26 |
| SECU-02 | 26 |
| SECU-03 | 26 |
| SECU-04 | 26 |
| SECU-05 | 26 |
| OBSV-01 | 27 |
| OBSV-02 | 27 |
| OBSV-03 | 27 |
| OBSV-04 | 27 |
| OBSV-05 | 27 |
| OBSV-06 | 27 |
| FLAG-01 | 28 |
| FLAG-02 | 28 |
| FLAG-03 | 28 |
| FLAG-04 | 28 |
| FLAG-05 | 28 |
| PFUI-01 | 29 |
| PFUI-02 | 29 |
| PFUI-03 | 29 |
| PFUI-04 | 29 |
| PFUI-05 | 29 |
| COST-01 | 30 |
| COST-02 | 30 |
| COST-03 | 30 |
| COST-04 | 30 |
| COST-05 | 30 |
| PBEN-01 | 31 |
| PBEN-02 | 31 |
| PBEN-03 | 31 |
| PBEN-04 | 31 |

**Mapped: 57/57**

---
*Roadmap created: 2026-03-25*
*Last updated: 2026-03-25 — Phase 24 planned (3 plans); Phase 25 planned (2 plans)*
