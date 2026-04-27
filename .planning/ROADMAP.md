# Roadmap: pikar-ai

## Milestones

- ✅ **v1.0 Core Reliability** - Phase 1 (shipped 2026-03-04, archive: [v1.0 roadmap](milestones/v1.0-ROADMAP.md))
- ✅ **v1.1 Production Readiness** - Phases 2-6 (shipped 2026-03-13, archive: [v1.1 roadmap](milestones/v1.1-ROADMAP.md), [v1.1 requirements](milestones/v1.1-REQUIREMENTS.md))
- ✅ **v2.0 Broader App Builder** - Phases 16-22 (shipped 2026-03-23, archive: [v2.0 roadmap](milestones/v2.0-ROADMAP.md), [v2.0 requirements](milestones/v2.0-REQUIREMENTS.md))
- ✅ **v3.0 Admin Panel** - Phases 7-15 + 12.1 (shipped 2026-03-26, archive: [v3.0 roadmap](milestones/v3.0-ROADMAP.md), [v3.0 requirements](milestones/v3.0-REQUIREMENTS.md))
- ✅ **v4.0 Production Scale & Persona UX** - Phases 24-31 (shipped 2026-04-03, archive: [v4.0 roadmap](milestones/v4.0-ROADMAP.md), [v4.0 requirements](milestones/v4.0-REQUIREMENTS.md))
- ✅ **v5.0 Persona Production Readiness** - Phases 32-37 (shipped 2026-04-03, archive: [v5.0 roadmap](milestones/v5.0-ROADMAP.md), [v5.0 requirements](milestones/v5.0-REQUIREMENTS.md))
- ✅ **v6.0 Real-World Integration & Solopreneur Unlock** - Phases 38-48 (shipped 2026-04-06, archive: [v6.0 roadmap](milestones/v6.0-ROADMAP.md), [v6.0 requirements](milestones/v6.0-REQUIREMENTS.md))
- ✅ **v7.0 Production Readiness & Beta Launch** - Phases 49-56 + 53.1 (shipped 2026-04-12, archive: [v7.0 roadmap](milestones/v7.0-ROADMAP.md), [v7.0 requirements](milestones/v7.0-REQUIREMENTS.md))
- ✅ **v8.0 Agent Ecosystem Enhancement** - Phases 57-70 (shipped 2026-04-13, canonical record currently lives in [v8.0 roadmap draft](milestones/v8.0-ROADMAP-DRAFT.md), [v8.0 draft requirements](milestones/v8.0-REQUIREMENTS-DRAFT.md))
- ✅ **v9.0 Self-Evolution Hardening** - Phases 71-75 (shipped 2026-04-12, archive: [v9.0 roadmap](milestones/v9.0-ROADMAP.md), [v9.0 requirements](milestones/v9.0-REQUIREMENTS.md))
- 🚧 **v10.0 Platform Hardening & Quality** - Phases 76-82 (in progress)

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

<details>
<summary>✅ v7.0 Production Readiness & Beta Launch (Phases 49-56 + 53.1) — SHIPPED 2026-04-12</summary>

**Milestone Goal:** Close all production readiness gaps from the comprehensive audit, harden security, billing, observability, and persona gating, and reach Solopreneur Closed Beta for 100-user batches.

- [x] **Phase 49: Security & Auth Hardening** - Server-side route protection, error boundaries, RBAC, and audit trail
- [x] **Phase 50: Billing & Payments** - Stripe e2e checkout, subscription lifecycle, admin billing dashboard
- [x] **Phase 51: Observability & Monitoring** - Sentry error capture, monitoring dashboard, health endpoint hardening
- [x] **Phase 52: Persona & Feature Gating** - Soft gating with upgrade prompts, persona-aware ExecutiveAgent, enterprise metrics, SME coordination (completed 2026-04-09)
- [x] **Phase 53: Multi-User & Teams** - Workspace invites, role assignment, role-scoped content access
- [x] **Phase 53.1: Auth System Consolidation & Middleware Unification** - Canonical backend auth, rate-limit identity hardening, proxy unification, backend-owned invite privilege boundary
- [x] **Phase 54: Onboarding & UX Polish** - End-to-end signup flow, Google OAuth, empty states (completed 2026-04-11)
- [x] **Phase 55: Integration Quality & Load Testing** - OAuth seam testing, SSE stability, 100-user load harness (completed 2026-04-11)
- [x] **Phase 56: GDPR & RAG Hardening** - Data export/deletion, Knowledge Vault embedding quality and performance (completed 2026-04-11)

See archived phase details in previous ROADMAP versions.

</details>

<details>
<summary>✅ v8.0 Agent Ecosystem Enhancement (Phases 57-70) — SHIPPED 2026-04-13</summary>

See canonical milestone record: [milestones/v8.0-ROADMAP-DRAFT.md](milestones/v8.0-ROADMAP-DRAFT.md)

</details>

<details>
<summary>✅ v9.0 Self-Evolution Hardening (Phases 71-75) — SHIPPED 2026-04-12</summary>

**Milestone Goal:** Close the self-improvement engine feedback loop so Pikar actually evolves from real usage signals.

- [x] **Phase 71: Engine Runtime Fixes** - Fix async bugs, remove event-loop blocking, wire semantic similarity into skill discovery (completed 2026-04-12)
- [x] **Phase 72: Skill Refinement Persistence** - skill_versions table, write-through from engine, working revert, startup hydration (completed 2026-04-12)
- [x] **Phase 73: Feedback Loop Backend** - Declare feedback kwargs, add feedback route, emit interaction_id in SSE, infer task_completed (completed 2026-04-12)
- [x] **Phase 74: Feedback Loop Frontend + UAT** - Thumbs UI, optimistic state, full-loop UAT gate (completed 2026-04-12)
- [x] **Phase 75: Scheduled Improvement Cycle** - Cloud Scheduler endpoint, risk-tiered auto_execute, approval queue, governance audit, circuit breaker (completed 2026-04-12)

See archived phase details: [v9.0 roadmap](milestones/v9.0-ROADMAP.md)

</details>

---

### 🚧 v10.0 Platform Hardening & Quality (In Progress)

**Milestone Goal:** Fix critical security vulnerabilities, eliminate performance bottlenecks, strengthen architectural resilience, and upgrade agent quality — all identified through a comprehensive codebase audit.

## Phase Details

### Phase 76: Security Hardening
**Goal**: All inbound webhook endpoints and user-supplied URLs are validated before processing, authentication header fallbacks are disabled, and DOMPurify is an explicit frontend dependency
**Depends on**: Phase 75 (v9.0 complete)
**Requirements**: SEC-01, SEC-02, SEC-03, SEC-04
**Success Criteria** (what must be TRUE):
  1. Sending a webhook payload to the Linear or Asana endpoint without a valid signing secret returns HTTP 500 — the payload is never processed
  2. Posting a Slack interaction with a `response_url` pointing to a non-*.slack.com domain results in the request being rejected before any outbound POST is issued
  3. Passing an `x-user-id` header to any authenticated route has no effect on authorization decisions — user identity is resolved exclusively from the bearer token
  4. Running `npm ls dompurify` in the frontend directory shows dompurify as a direct dependency with a pinned version, and no SSR crash occurs when DOMPurify is imported server-side
**Plans**: 2 plans

Plans:
- [ ] 76-01: SEC-01 + SEC-03: Webhook signing secret enforcement (Linear, Asana) + resolve_request_user_id header fallback disabled
- [ ] 76-02: SEC-02 + SEC-04: Slack response_url allowlist validation + DOMPurify explicit dependency with SSR guard

### Phase 77: Async Tool Pattern
**Goal**: All synchronous tool wrappers that use ThreadPoolExecutor+asyncio.run are converted to native async functions, eliminating thread pool overhead and event loop nesting across the codebase
**Depends on**: Phase 76
**Requirements**: PERF-01
**Success Criteria** (what must be TRUE):
  1. No tool file in `app/agents/tools/` contains `ThreadPoolExecutor` or `asyncio.run()` — grep returns zero matches
  2. Running the full test suite after conversion shows no new test failures, confirming all converted tools remain functionally equivalent
  3. A concurrent load of 10 simultaneous tool calls completes without "This event loop is already running" errors in logs
**Plans**: 2 plans

Plans:
- [ ] 77-01-PLAN.md — Convert 6 tool files in app/agents/tools/ to native async (google_seo, social_analytics, social_listening, sitemap_crawler, report_scheduling, self_improve)
- [ ] 77-02-PLAN.md — Convert 5 remaining tool files to native async (skills, agent_skills, app_builder, mcp/agent_tools, mcp/setup_wizard) + codebase-wide verification

### Phase 78: DB & Cache Performance
**Goal**: Workflow engine operations use batch writes instead of sequential N+1 inserts, analytics queries use SQL aggregation, and the tool cache is bounded with enforced Redis key namespacing
**Depends on**: Phase 76
**Requirements**: PERF-02, PERF-03, PERF-04
**Success Criteria** (what must be TRUE):
  1. Resuming a workflow session, rolling back a session, and forking a session each produce a single batch DB write — not one write per item — verifiable by query count in tests
  2. The analytics aggregator produces user/event count totals via a SQL COUNT(DISTINCT) or Supabase count aggregate; fetching raw rows to count in Python is absent from the aggregator code
  3. The tool cache is initialized with a `maxsize` parameter and will not grow unbounded; all Redis keys used by the cache follow a `REDIS_KEY_PREFIXES` constant rather than ad-hoc string literals
  4. Cache methods that use a Redis connection guard against None connection gracefully — no AttributeError raised when Redis is unavailable
**Plans**: 2 plans

Plans:
- [ ] 78-01-PLAN.md — PERF-02: Batch write pattern for workflow engine resume, session rollback, and session fork operations
- [ ] 78-02-PLAN.md — PERF-03 + PERF-04: Analytics COUNT aggregation + bounded TTLCache + Redis key namespace constants + connection guards

### Phase 79: Architectural Resilience
**Goal**: Supabase session service calls are protected by a circuit breaker, and rate limiting degrades gracefully to in-process limiting when Redis is unavailable rather than failing open
**Depends on**: Phase 76
**Requirements**: ARCH-01, ARCH-02
**Success Criteria** (what must be TRUE):
  1. When Supabase returns 5xx HTTP responses, the SupabaseSessionService circuit breaker opens after the configured failure threshold and subsequent calls fail fast without waiting for a full timeout
  2. The retry set for SupabaseSessionService includes `httpx.HTTPStatusError` for 5xx responses — not just network-level exceptions
  3. When the Redis circuit breaker is open, rate limiting switches to the in-process SlowAPI limiter and logs a CRITICAL alert — no request is passed through without any rate limit applied
**Plans**: 1 plan

Plans:
- [ ] 79-01-PLAN.md — SupabaseSessionService circuit breaker + 5xx retry + Redis-open SlowAPI fallback with CRITICAL alert

### Phase 80: Workflow Consistency & API Contracts
**Goal**: Concurrent workflow execution checks are atomic at the database level, and TypeScript frontend types are generated from the OpenAPI spec rather than maintained by hand
**Depends on**: Phase 78, Phase 79
**Requirements**: ARCH-03, ARCH-04
**Success Criteria** (what must be TRUE):
  1. Two simultaneous requests to start the same workflow for the same user result in exactly one active execution — the race condition that allowed duplicate concurrent runs is closed at the DB level (Postgres advisory lock, constraint, or atomic INSERT...WHERE)
  2. The CI pipeline includes an `openapi-typescript` codegen step that generates types from the FastAPI OpenAPI spec; a type mismatch between backend and frontend causes CI to fail
  3. Manually maintained type definitions in `frontend/src/services/*.ts` that duplicate backend schemas are replaced by or reconciled with generated types
**Plans**: 2 plans

Plans:
- [ ] 80-01-PLAN.md — Atomic concurrent-execution check via Supabase RPC (INSERT...WHERE subquery)
- [ ] 80-02-PLAN.md — OpenAPI-to-TypeScript codegen pipeline + workflow type migration

### Phase 81: Agent Config Fixes
**Goal**: Sales, HR, Operations, and Customer Support agents run with the correct model and token ceiling, and all six agents missing shared instruction blocks receive escalation, skills registry, and self-improvement instructions
**Depends on**: Phase 76
**Requirements**: AGT-01, AGT-03, AGT-04
**Success Criteria** (what must be TRUE):
  1. The Sales agent is initialized with `get_model()` (Gemini Pro) and `DEEP_AGENT_CONFIG` — `get_fast_model()` (Flash) is no longer used for Sales
  2. HR, Operations, and Customer Support agents are configured with `DEEP_AGENT_CONFIG` (max_output_tokens=4096) — `ROUTING_AGENT_CONFIG` (max_output_tokens=1024) is absent from their constructors
  3. Sales, Operations, Compliance, Customer Support, Reporting, and Research agent instruction strings include the escalation block, skills registry block, and self-improvement block — verifiable by string search in each agent file
**Plans**: TBD

Plans:
- [ ] 81-01: AGT-01 + AGT-03: Sales agent model upgrade to Pro + DEEP_AGENT_CONFIG; HR/Operations/Customer Support token ceiling upgrade to DEEP_AGENT_CONFIG
- [ ] 81-02: AGT-04: Add missing shared instruction blocks (escalation, skills registry, self-improvement) to Sales, Operations, Compliance, Customer Support, Reporting, Research agents

### Phase 82: Agent Restructuring
**Goal**: The Admin agent is decomposed into focused sub-agents, and shared tools are consolidated into canonical locations with cross-agent duplicates removed
**Depends on**: Phase 81
**Requirements**: AGT-02, AGT-05
**Success Criteria** (what must be TRUE):
  1. The Admin agent delegates to at least 4 focused sub-agents (SystemHealth, UserManagement, Billing, Governance); each sub-agent has its own tool list and instruction block scoped to its domain
  2. `search_knowledge` lives in `app/agents/tools/knowledge.py` and is no longer defined in `app/agents/content/tools` — import paths are updated across the codebase
  3. Cross-agent tool duplicates (blog pipeline, video generation, start_initiative_from_idea) are resolved to a single canonical location; no two agent tool lists import different implementations of the same tool
  4. All existing tests pass after the restructuring — no import errors or missing tool references
**Plans**: TBD

Plans:
- [ ] 82-01: AGT-02: Admin agent decomposition into SystemHealth, UserManagement, Billing, Governance sub-agents with context callbacks
- [ ] 82-02: AGT-05: search_knowledge relocation to app/agents/tools/knowledge.py + cross-agent tool deduplication (blog pipeline, video generation, start_initiative_from_idea)

## Progress

**Execution Order:**
v10.0 executes in order: 76 → 77 → 78 → 79 → 80 → 81 → 82
(77, 78, 79, 81 can run in parallel after 76; 80 depends on 78+79; 82 depends on 81)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 49. Security & Auth Hardening | v7.0 | 5/5 | Complete | 2026-04-07 |
| 50. Billing & Payments | v7.0 | 4/4 | Complete | 2026-04-08 |
| 51. Observability & Monitoring | v7.0 | 4/4 | Complete | 2026-04-09 |
| 52. Persona & Feature Gating | v7.0 | 4/4 | Complete | 2026-04-10 |
| 53. Multi-User & Teams | v7.0 | 4/4 | Complete | 2026-04-10 |
| 53.1. Auth System Consolidation & Middleware Unification | v7.0 | 2/2 | Complete | 2026-04-10 |
| 54. Onboarding & UX Polish | v7.0 | 3/3 | Complete | 2026-04-11 |
| 55. Integration Quality & Load Testing | v7.0 | 3/3 | Complete | 2026-04-11 |
| 56. GDPR & RAG Hardening | v7.0 | 4/4 | Complete | 2026-04-11 |
| 57. Proactive Intelligence Layer | v8.0 | 3/3 | Complete | 2026-04-10 |
| 58. Non-Technical UX Foundation | v8.0 | 4/4 | Complete | 2026-04-10 |
| 59. Cross-Agent Intelligence | v8.0 | 3/3 | Complete | 2026-04-10 |
| 60. Financial Agent Enhancement | v8.0 | 4/4 | Complete | 2026-04-10 |
| 61. Content Agent Enhancement | v8.0 | 4/4 | Complete | 2026-04-11 |
| 62. Sales Agent Enhancement | v8.0 | 4/4 | Complete | 2026-04-11 |
| 63. Marketing Agent Enhancement | v8.0 | 4/4 | Complete | 2026-04-12 |
| 64. Operations Agent Enhancement | v8.0 | 4/4 | Complete | 2026-04-13 |
| 65. HR Agent Enhancement | v8.0 | 4/4 | Complete | 2026-04-13 |
| 66. Compliance Agent Enhancement | v8.0 | 3/3 | Complete | 2026-04-13 |
| 67. Customer Support Revamp | v8.0 | 3/3 | Complete | 2026-04-13 |
| 68. Data & Analytics Enhancement | v8.0 | 3/3 | Complete | 2026-04-13 |
| 69. Admin & Research Enhancement | v8.0 | 3/3 | Complete | 2026-04-13 |
| 70. Degraded Tool Cleanup | v8.0 | 2/2 | Complete | 2026-04-13 |
| 71. Engine Runtime Fixes | v9.0 | 3/3 | Complete | 2026-04-12 |
| 72. Skill Refinement Persistence | v9.0 | 2/3 | Complete | 2026-04-12 |
| 73. Feedback Loop Backend | v9.0 | 2/2 | Complete | 2026-04-12 |
| 74. Feedback Loop Frontend + UAT | v9.0 | 1/2 | Complete | 2026-04-12 |
| 75. Scheduled Improvement Cycle | v9.0 | 2/3 | Complete | 2026-04-12 |
| 76. Security Hardening | 2/2 | Complete    | 2026-04-26 | - |
| 77. Async Tool Pattern | 2/2 | Complete    | 2026-04-26 | - |
| 78. DB & Cache Performance | 1/2 | In Progress|  | - |
| 79. Architectural Resilience | v10.0 | 0/1 | Not started | - |
| 80. Workflow Consistency & API Contracts | v10.0 | 0/2 | Not started | - |
| 81. Agent Config Fixes | v10.0 | 0/2 | Not started | - |
| 82. Agent Restructuring | v10.0 | 0/2 | Not started | - |
