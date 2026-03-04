# Codebase Concerns

**Analysis Date:** 2026-03-04

## Tech Debt

**Workflow worker argument mapping (`app/workflows/worker.py`):**
- Issue: Step execution still relies on broad `**sys_context` invocation and a `TypeError` fallback to no-arg calls (explicit FIXME at line ~286)
- Why: Early MVP execution path prioritized generality over strict tool signature contracts
- Impact: Steps can succeed with wrong/missing inputs or fail non-deterministically for tools requiring structured args
- Fix approach: Introduce explicit step input schema + deterministic arg mapping/validation before invocation

**Dual workflow execution paths (`app/workflows/engine.py` + `app/workflows/worker.py` + `supabase/functions/execute-workflow/index.ts`):**
- Issue: Runtime behavior is split across backend engine, legacy worker logic, and edge function orchestration
- Why: Evolution from local worker execution to edge-driven orchestration
- Impact: Higher cognitive load, multiple fallback branches, and harder incident debugging
- Fix approach: Consolidate to one canonical execution path and deprecate legacy worker codepaths

**Migration numbering collisions (`supabase/migrations/`):**
- Issue: Duplicate numeric prefixes exist (`0037_*`, `0053_*`, `0054_*`), plus mixed timestamped and numbered migrations
- Why: Parallel development streams and backfills
- Impact: Review and rollout ordering is harder to reason about; risk of operator confusion during manual migration audits
- Fix approach: Adopt one monotonic migration naming strategy and document ordering guarantees

## Known Bugs

**Persona-aware rate limits often collapse to default (`app/middleware/rate_limiter.py`):**
- Symptoms: Authenticated requests can still be throttled at default `10/minute` instead of persona-specific tiers
- Trigger: Missing `x-pikar-persona` header/cookie and no warm in-memory persona cache
- Workaround: Ensure frontend proxy always supplies persona header/cookie
- Root cause: DB lookup for persona is intentionally skipped in request path; fallback is default limit

**Template list can silently fall back to seed metadata (`app/workflows/engine.py`):**
- Symptoms: `list_templates` may return seed/template metadata not reflecting current DB state
- Trigger: Query timeout (`3.0s`) or schema mismatch in lifecycle-aware query
- Workaround: Verify template records directly in Supabase when list output appears stale
- Root cause: Aggressive timeout and fallback logic prioritizes availability over strict source fidelity

## Security Considerations

**Stripe webhook verification is optional (`app/routers/webhooks.py`):**
- Risk: If `STRIPE_WEBHOOK_SECRET` is unset, endpoint accepts raw JSON payload without signature verification
- Current mitigation: Warning log is emitted
- Recommendations: Require secret in non-development environments and hard-fail startup when missing

**Health endpoints expose internal diagnostics (`app/routers/health.py`):**
- Risk: `/health/cache` and `/health/connections` include infrastructure details (host, ports, config readiness)
- Current mitigation: None in route-level auth checks
- Recommendations: Gate detailed health endpoints behind admin auth or network allowlists

**Permissive auth mode is configuration-sensitive (`app/app_utils/auth.py`):**
- Risk: If `REQUIRE_STRICT_AUTH` is not enabled, invalid/missing-token handling can be more permissive in some flows
- Current mitigation: strict mode support exists and is documented
- Recommendations: Enforce strict mode by default in deployed environments and alert on permissive mode

## Performance Bottlenecks

**Workflow template query timeout threshold (`app/workflows/engine.py`):**
- Problem: Template listing has a hard `3.0s` timeout before fallback
- Measurement: Timeout constant is explicit in code path
- Cause: Network/DB latency sensitivity without progressive retry strategy
- Improvement path: Add short retry budget and cache recent successful template lists

**Connector fan-out and pagination caps in finance reads (`app/services/stripe_revenue_service.py`):**
- Problem: Revenue fetch may paginate through large Stripe datasets and perform in-memory aggregation
- Measurement: Loops are capped at `1000` records per source in current implementation
- Cause: Pull-based API traversal on request path
- Improvement path: Background sync to normalized tables + cached report windows

## Fragile Areas

**Session event shaping and context window truncation (`app/persistence/supabase_session_service.py`):**
- Why fragile: Event compaction replaces heavy payload fields and truncates by event count
- Common failures: Missing context details for media-heavy sessions; debugging difficulty when context is compacted
- Safe modification: Keep schema-compatible event compaction and expand telemetry before changing truncation rules
- Test coverage: Memory/session tests exist, but real payload-volume regression risks remain

**Agent parent ownership constraints (`app/agent.py`, `app/agents/specialized_agents.py`):**
- Why fragile: ADK enforces one parent per agent instance; reuse mistakes cause runtime parent-assignment errors
- Common failures: Reusing singleton sub-agents in fallback/parallel contexts
- Safe modification: Always use `create_*_agent` factories for non-primary trees
- Test coverage: Factory tests exist, but orchestration permutations are broad

**Workflow callback auth dependency chain (`app/workflows/engine.py`, `app/app_utils/auth.py`, `app/services/edge_functions.py`):**
- Why fragile: Strict mode requires aligned `BACKEND_API_URL` + `WORKFLOW_SERVICE_SECRET`
- Common failures: Executions remain pending when callback infra config is incomplete
- Safe modification: Validate required callback config at deploy/startup and fail fast for user-visible workflows
- Test coverage: Integration checks exist, but environment drift remains a risk

## Scaling Limits

**Session context window:**
- Current capacity: Last `SESSION_MAX_EVENTS` (default 80) events loaded per session
- Limit: Older events are excluded from active context window
- Symptoms at limit: Long conversations can lose earlier context details
- Scaling path: Hybrid retrieval from summarized memory + selective historical recall

**Redis connection defaults:**
- Current capacity: `REDIS_MAX_CONNECTIONS` defaults to 20 in runtime config
- Limit: High concurrency can queue/fail cache operations if pool is undersized
- Symptoms at limit: Cache misses increase and fallback DB load rises
- Scaling path: Tune pool size per deployment and monitor circuit breaker state

**Stripe revenue pull limits:**
- Current capacity: Request-time retrieval capped at 1000 records per source path
- Limit: Large transaction histories may be incomplete for broad windows
- Symptoms at limit: Underreported totals for high-volume accounts
- Scaling path: Incremental sync job + warehouse-style aggregation layer

## Dependencies at Risk

**Deprecated workflow tool marker (`app/workflows/template_validation.py`):**
- Risk: `sent_contract` is explicitly deprecated but may still exist in legacy templates
- Impact: Template validation failures for old payloads
- Migration plan: Add automated migration/remap for deprecated tool references

**Optional A2A/ADK import paths (`app/fast_api_app.py`):**
- Risk: Runtime can degrade to reduced capabilities when optional components fail to import
- Impact: A2A routes/features may be unavailable while app still starts
- Migration plan: Add deployment-time capability checks and explicit readiness assertions

## Missing Critical Features

**CI lacks broad regression execution (`.github/workflows/ci.yml`):**
- Problem: Current workflow validates template scripts but does not run backend/frontend test suites by default
- Current workaround: Run `make test` / frontend tests manually or in external pipelines
- Blocks: Early detection of API/service/UI regressions in pull requests
- Implementation complexity: Low to medium (extend CI matrix with pytest + frontend vitest + lint)

**No dedicated frontend E2E suite in repo:**
- Problem: UI flow validation relies on component/service tests, with no Playwright/Cypress-style full journey tests
- Current workaround: Manual dashboard/chat/onboarding verification
- Blocks: Confidence in cross-page auth/session/navigation flows
- Implementation complexity: Medium

## Test Coverage Gaps

**Webhook security behavior:**
- What's not tested: Explicit test coverage for `STRIPE_WEBHOOK_SECRET` absent-path behavior and signature enforcement edge cases
- Risk: Security regressions could ship unnoticed
- Priority: High
- Difficulty to test: Medium (requires deterministic webhook fixture/signature harness)

**Strict vs permissive auth mode paths:**
- What's not tested: End-to-end route behavior across `REQUIRE_STRICT_AUTH`/`ALLOW_ANONYMOUS_CHAT` combinations
- Risk: Environment misconfiguration can weaken expected auth guarantees
- Priority: High
- Difficulty to test: Medium

**Legacy workflow worker argument mapping:**
- What's not tested: Broad matrix of tool signatures against worker fallback invocation path
- Risk: Step execution failures or silent partial execution
- Priority: Medium
- Difficulty to test: Medium

---

*Concerns audit: 2026-03-04*
*Update as issues are fixed or new ones discovered*
