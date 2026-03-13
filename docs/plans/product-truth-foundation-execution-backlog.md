# Product Truth Foundation Execution Backlog

Date: 2026-03-12
Status: Proposed
Companion docs:
- `docs/plans/gtm-production-operating-plan.md`
- `.planning/ROADMAP.md`

## Goal

Convert the current product from feature-rich but operationally fragile into a trustworthy system that can support repeatable GTM motion.

This backlog is the implementation layer for the "Product Truth Foundation" phase from the GTM operating plan. It translates the audit into subsystem tickets with sequencing, owners, and exit gates.

## Scope

This phase is about trust, not breadth.

In scope:
- schema ownership
- auth and security correctness
- workflow truthfulness
- frontend-backend contract alignment
- CI/CD and release gates
- documentation and messaging truthfulness

Out of scope:
- new persona-specific premium features
- broad enterprise feature expansion
- major UI redesigns not required for trust or activation

## Workstream Map

| Workstream | Maps To | Primary Outcome |
|---|---|---|
| Data Contract Ownership | Roadmap Phase 2 | One canonical schema and storage contract |
| Async and Execution Safety | Roadmap Phase 3 | No hidden blocking or duplicate execution behavior |
| Frontend-Backend Contract | Roadmap Phase 4 | Core user journeys use one authenticated, typed path |
| Security and Secrets | Roadmap Phase 5 | Production-safe auth, headers, and secret handling |
| Release and Deployment Truth | Roadmap Phase 6 plus cross-cutting | Every release validates the real product stack |

## Priority Order

### Wave A: Immediate blockers

- PTF-01 Schema inventory and drift report
- PTF-05 Header and CORS alignment
- PTF-09 Disable simulated workflow success in production
- PTF-13 Remove frontend fallbacks from core journeys
- PTF-16 Add minimum CI release gate for backend, frontend, and migrations

### Wave B: Hardening blockers

- PTF-02 Move out-of-band schema into canonical Supabase migrations
- PTF-06 Remove caller-supplied user identity trust
- PTF-07 Remove anon-to-service-role fallback
- PTF-10 Unify workflow execution authority
- PTF-11 Convert hot async paths to async-safe database access
- PTF-17 Wire Supabase Edge Functions and migrations into deployment

### Wave C: Confidence multipliers

- PTF-03 Fix bucket and storage contract mismatches
- PTF-04 Add schema drift CI checks
- PTF-08 Harden OAuth and integration secret handling
- PTF-12 Replace private cache access and validate concurrency safety
- PTF-14 Publish typed contract definitions for core API surfaces
- PTF-15 Add core canary E2E journeys
- PTF-18 Align docs and product claims to shipped capability

## Backlog Tickets

### Data Contract Ownership

#### PTF-01: Produce a canonical schema inventory
- Owner: Platform + Backend
- Why: We need one source of truth before changing anything else.
- Scope:
  - inventory all live tables, views, buckets, and Edge Function dependencies referenced by code
  - compare against `supabase/migrations`
  - identify anything defined outside the canonical chain
  - classify each mismatch as `adopt`, `migrate`, or `delete`
- Definition of done:
  - one inventory document exists in-repo
  - every referenced table and bucket has a canonical owner
  - unknown schema dependencies are zero
- Depends on: none
- Persona impact: invisible to users directly, but foundational for every segment

#### PTF-02: Move out-of-band schema into canonical Supabase migrations
- Owner: Platform + Backend
- Why: Environment drift is a production killer.
- Scope:
  - move app-local SQL and non-canonical migration files into `supabase/migrations`
  - reconcile legacy migration strategy conflicts
  - remove duplicate schema definitions
- Definition of done:
  - `supabase/migrations` is the only schema authority
  - no production-required table depends on app-local SQL files outside the canonical path
  - deployment instructions use one migration mechanism
- Depends on: PTF-01
- Persona impact: improves reliability for all personas

#### PTF-03: Repair storage and bucket contract mismatches
- Owner: Backend + Frontend
- Why: Legacy bucket names and storage assumptions break user-visible flows.
- Scope:
  - fix bucket and table naming drift across vault, workspace, and media flows
  - update UI and backend references to canonical names
  - verify uploads, previews, and retrieval in the same environment
- Definition of done:
  - no core file flow references legacy bucket names
  - upload, list, preview, and download all work in one deployed stack
- Depends on: PTF-01
- Persona impact: strong for solopreneur and startup, moderate for SME

#### PTF-04: Add schema drift checks to CI
- Owner: Platform
- Why: Drift will come back unless it is checked automatically.
- Scope:
  - add a script or check that compares code references and canonical migrations
  - fail CI when required tables or buckets are missing from the canonical chain
- Definition of done:
  - CI fails on new out-of-band schema additions
  - migration conflicts are surfaced before release
- Depends on: PTF-01, PTF-02
- Persona impact: indirect but critical for release safety

### Security and Secrets

#### PTF-05: Align frontend headers, backend auth, and CORS
- Owner: Frontend + Backend
- Why: Persona-aware requests should not fail in the browser.
- Scope:
  - allow required persona and user headers on backend CORS config
  - verify frontend sends only expected headers
  - ensure authenticated requests work from browser and proxy routes
- Definition of done:
  - no CORS errors on persona-aware core journeys
  - no 401s caused by header mismatch on core dashboard, initiative, workflow, and configuration flows
- Depends on: none
- Persona impact: high for all active users

#### PTF-06: Remove trust in caller-supplied user identity
- Owner: Backend
- Why: Request identity must come from verified auth context, not request bodies or query params.
- Scope:
  - audit all endpoints that accept `user_id`
  - replace caller-controlled identity with resolved auth identity
  - add tests for cross-user access attempts
- Definition of done:
  - no privileged route trusts a caller-supplied `user_id` when auth context is available
  - negative authorization tests exist for sensitive endpoints
- Depends on: PTF-05
- Persona impact: foundational for SME and enterprise credibility, still important for all users

#### PTF-07: Remove unsafe service-role and anon fallbacks
- Owner: Backend + Platform
- Why: Quiet elevation paths make production behavior unsafe and hard to reason about.
- Scope:
  - remove anon-to-service-role fallbacks
  - make missing required keys fail fast
  - document which services may legitimately use service-role access and why
- Definition of done:
  - missing anon credentials cannot silently widen privilege
  - service-role use is explicit and documented
- Depends on: PTF-01
- Persona impact: indirect but essential for trust

#### PTF-08: Harden integration secrets and OAuth state
- Owner: Backend + Platform
- Why: In-memory PKCE state and weak fallback secrets are not production-safe.
- Scope:
  - store OAuth verifier/state in durable shared storage
  - implement token refresh where required
  - remove default-derived encryption behavior for user configuration
  - validate all required secret env vars at startup
- Definition of done:
  - OAuth works across multiple instances
  - secret misconfiguration fails startup or the affected integration path cleanly
  - no sensitive path depends on fallback-derived encryption keys
- Depends on: PTF-07
- Persona impact: high for startup and SME customers using integrations

### Workflow Truthfulness and Async Safety

#### PTF-09: Disable simulated or degraded workflow success in production
- Owner: Backend
- Why: Users cannot trust outcomes if the system reports success on fallback logic.
- Scope:
  - locate all simulated or degraded execution paths
  - gate them behind explicit non-production flags
  - surface truthful status when execution cannot proceed
- Definition of done:
  - production workflows never report success from mock or degraded execution branches
  - failures are explicit and user-visible
- Depends on: none
- Persona impact: highest-value fix across all personas

#### PTF-10: Unify workflow execution authority
- Owner: Backend + Platform
- Why: Multiple execution paths increase drift and inconsistent behavior.
- Scope:
  - define one source of truth for workflow state transitions
  - document the roles of FastAPI, Edge Functions, and worker paths
  - remove or constrain overlapping execution logic
- Definition of done:
  - one execution authority owns final workflow truth
  - duplicate state transition logic is removed or clearly delegated
- Depends on: PTF-09
- Persona impact: high for startup and SME, foundational for enterprise later

#### PTF-11: Convert hot async paths to async-safe data access
- Owner: Backend
- Why: Blocking `.execute()` calls in async paths threaten performance and reliability.
- Scope:
  - migrate the highest-traffic async service and router paths first
  - prioritize onboarding, initiatives, workflows, vault, and report scheduling
  - replace blocking Supabase access in async request paths
- Definition of done:
  - no known hot async path uses blocking database access
  - representative async tests run without blocking-call warnings
- Depends on: PTF-01
- Persona impact: improves responsiveness across all personas

#### PTF-12: Replace private cache access and validate concurrency safety
- Owner: Backend
- Why: Private cache usage and race-prone initialization create hard-to-reproduce failures.
- Scope:
  - replace direct `_redis` access with public cache service methods
  - validate safe concurrent initialization
  - add targeted tests for cache startup behavior
- Definition of done:
  - no business logic depends on private cache internals
  - cache initialization is safe under concurrent startup conditions
- Depends on: PTF-11
- Persona impact: indirect, but supports workflow reliability

### Frontend-Backend Contract

#### PTF-13: Remove frontend bypasses from core user journeys
- Owner: Frontend + Backend
- Why: Core business logic should not split between browser-side direct table access and backend APIs.
- Scope:
  - identify where initiatives, workspace, configuration, or workflows bypass the backend
  - replace browser fallbacks with one authenticated backend path for production journeys
  - keep local-dev helpers only behind explicit development flags
- Definition of done:
  - onboarding, initiatives, workflows, workspace, and configuration use canonical API paths in production
  - no critical production flow depends on direct browser-side schema knowledge
- Depends on: PTF-05, PTF-01
- Persona impact: high for all users, especially team-oriented accounts

#### PTF-14: Publish typed contracts for core API surfaces
- Owner: Frontend + Backend
- Why: Type drift is already causing test and runtime fragility.
- Scope:
  - define shared response contracts for workflows, initiatives, workspace items, and configuration status
  - align frontend types to actual backend responses
  - remove stale or speculative frontend assumptions
- Definition of done:
  - core API surfaces have one documented contract each
  - TypeScript and backend tests validate the same shapes
- Depends on: PTF-13
- Persona impact: indirect but important for UX reliability

### Release and Deployment Truth

#### PTF-15: Add core canary end-to-end journeys
- Owner: QA + Frontend + Backend
- Why: Unit tests alone will not prove the product works as sold.
- Scope:
  - define canary journeys for onboarding, initiative creation, workflow execution, workspace artifact persistence, and configuration status
  - run them in a deployed or production-like environment
- Definition of done:
  - at least five canary journeys run automatically before widening rollout
  - failures identify the broken subsystem clearly
- Depends on: PTF-13, PTF-14, PTF-16
- Persona impact: directly improves release confidence for every segment

#### PTF-16: Add a minimum trustworthy CI release gate
- Owner: Platform
- Why: Current CI does not validate the real shipped experience.
- Scope:
  - require backend tests for core services and routers
  - require frontend tests and frontend build
  - require migration integrity checks
- Definition of done:
  - pull requests cannot merge without passing minimum cross-stack checks
  - CI status reflects backend, frontend, and schema readiness together
- Depends on: none
- Persona impact: indirect but essential for scale

#### PTF-17: Deploy Supabase migrations and Edge Functions through the release path
- Owner: Platform
- Why: Backend-only deployment is not enough for a Supabase-centric product.
- Scope:
  - wire Supabase schema migrations into deploy flow
  - wire Edge Function deployment into the same controlled path
  - document rollback expectations
- Definition of done:
  - release instructions cover backend, frontend, migrations, and Edge Functions together
  - no manual hidden step is required to make a release functional
- Depends on: PTF-02, PTF-16
- Persona impact: indirect, but critical for operational consistency

#### PTF-18: Align docs and product claims to verified capability
- Owner: Product Marketing + Engineering
- Why: Trust is lost when messaging exceeds what the product proves.
- Scope:
  - update README, frontend setup docs, testing docs, and capability claims
  - distinguish shipped functionality from planned functionality
  - make public-facing value props reflect the strongest real user loop
- Definition of done:
  - setup docs describe the actual stack
  - no major product claim lacks a clear implementation path or shipped proof
- Depends on: PTF-09, PTF-13, PTF-16
- Persona impact: strong for sales credibility and onboarding clarity

## Suggested Delivery Sequence

### Sprint 1
- PTF-01
- PTF-05
- PTF-09
- PTF-16

### Sprint 2
- PTF-02
- PTF-06
- PTF-07
- PTF-13

### Sprint 3
- PTF-10
- PTF-11
- PTF-14
- PTF-17

### Sprint 4
- PTF-03
- PTF-04
- PTF-08
- PTF-12
- PTF-15
- PTF-18

## Exit Criteria

This phase is complete when all of the following are true:

- production schema ownership is canonical and automated
- workflow success reflects real execution only
- core browser journeys use one authenticated backend contract
- auth, identity, and secret handling are production-safe
- CI validates backend, frontend, migrations, and deployment-critical paths together
- product messaging accurately reflects verified capability

## Commercial Impact

If this phase succeeds, the product becomes sellable with confidence to:
- solopreneurs
- startups

And pilotable with far less risk to:
- SMEs

Enterprise selling should still wait for the later governance and admin hardening phases, but this backlog removes the trust blockers that currently limit every GTM motion.
