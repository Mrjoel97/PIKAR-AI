---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Broader App Builder
current_phase: 16 (Foundation), plan 2 of 3 complete
status: executing
stopped_at: Completed 16-02-PLAN.md — StitchMCPService singleton, FastAPI lifespan wiring, ADK tool wrappers
last_updated: "2026-03-21T13:35:30Z"
last_activity: "2026-03-21 — 16-02 complete: StitchMCPService, fast_api_app.py lifespan, app_builder.py ADK tools, 5 unit tests"
progress:
  total_phases: 8
  completed_phases: 0
  total_plans: 3
  completed_plans: 2
  percent: 6
---

# Project State: pikar-ai

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-21)

**Core value:** Users describe what they want and the system autonomously generates and manages business operations
**Current focus:** Phase 16 — Foundation (v2.0 Broader App Builder)

## Current Position

Phase: 16 of 23 (Foundation)
Plan: 2 of 3 in current phase — complete
Status: In progress
Last activity: 2026-03-21 — 16-02 complete: StitchMCPService singleton, FastAPI lifespan wiring, ADK tool wrappers (generate_app_screen, list_stitch_tools)

Progress: [█░░░░░░░░░] 6% (v2.0)

## Active Milestones

### v3.0 Admin Panel (Phases 7-15) — Paused (switching to v2.0)
Current phase: 7 (Foundation), plan 5 of 5 complete
Next: Phase 8 (when v2.0 is complete or user resumes)

### v2.0 Broader App Builder (Phases 16-23) — Executing
Current phase: 16 (Foundation), plan 2 of 3 complete
Roadmap file: .planning/ROADMAP-v2.md
Requirements file: .planning/REQUIREMENTS-v2.md
Next: 16-03 (AppBuilderAgent + screen generation workflow)

## Performance Metrics

**Velocity:**
- Total plans completed (v3.0): 5
- Total plans completed (v2.0): 1
- Average duration: ~9 min
- Total execution time (v2.0): 9 min

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 07-foundation | 07-01 | 11 min | 2 | 11 |
| Phase 07-foundation P02 | 11 | 2 tasks | 11 files |
| Phase 07-foundation P07-03 | 7 min | 2 tasks | 3 files |
| 07-foundation | 07-04 | 7 min | 2 | 8 |
| Phase 07-foundation P07-05 | 10 | 2 tasks | 2 files |
| 16-foundation | 16-01 | 9 min | 2 | 3 |
| 16-foundation | 16-02 | 18 min | 2 | 4 |

## Accumulated Context

### Decisions

- (2026-03-04) v1.0 Milestone 1 completed: workflow hardening and Redis circuit breakers
- (2026-03-13) v1.1 Production Readiness shipped: 5 phases, 24 requirements, all complete
- (2026-03-21) v3.0 Admin Panel: AI-first approach with Google ADK AdminAgent on FastAPI
- (2026-03-21) Admin auth: two-layer (env allowlist + user_roles table), OR logic, server-side only
- (2026-03-21) Autonomy tiers: enforced in Python tool code, NOT in LLM system prompt
- (2026-03-21) MultiFernet encryption from day one — comma-separated ADMIN_ENCRYPTION_KEY
- (2026-03-21) Confirmation tokens: UUID-based, atomic single-consumption (UPDATE WHERE consumed=false)
- (2026-03-21) Health checks write directly to Supabase, bypassing the monitored FastAPI service
- (2026-03-21) External integrations: per-session call budgets + 2-5 min Redis cache to prevent rate exhaustion
- (2026-03-21) 07-01: require_admin OR logic — ADMIN_EMAILS env allowlist short-circuits DB call; admin_source field added to returned dict for audit
- (2026-03-21) 07-01: admin_audit_log.impersonation_session_id nullable UUID included now (schema-ready for Phase 13 AUDT-04, not populated until then)
- [Phase 07-foundation]: Autonomy enforcement in Python tool code (NOT LLM prompt): each tool queries admin_agent_permissions before executing
- [Phase 07-foundation]: Redis GETDEL for atomic confirmation token consumption — prevents replay on second consume
- [Phase 07-foundation]: AdminAgent uses FAST_AGENT_CONFIG (temperature=0.3) — tool-calling, not analysis
- [Phase 07-foundation]: Per-request ADK Runner with InMemorySessionService for admin chat (isolated from main runner)
- [Phase 07-foundation]: SSE first event contains session_id for frontend persistence without separate API call
- (2026-03-21) 07-04: AdminGuard is server-side only — redirect before client bundle loads, no UI flash possible
- (2026-03-21) 07-04: ConfirmationCard double-click protection via local clicked state, independent of async isProcessing prop
- (2026-03-21) 07-04: Audit log uses client-side fetch to support filter/pagination interactions without full page reload
- [Phase 07-foundation]: 07-05: Audit log uses service-role Supabase client (bypasses RLS) — admin middleware already enforces access, RLS would block cross-user audit queries
- [Phase 07-foundation]: 07-05: count=exact Supabase option returns total row count without a second query — used for audit log pagination
- (2026-03-21) v2.0 Broader App Builder: Stitch MCP over REST API — MCP provides richer tools and avoids per-call subprocess overhead
- (2026-03-21) v2.0: GSD-style creative workflow engine — guided discovery → brief → build → verify differentiates from v0/Bolt/Lovable
- (2026-03-21) v2.0: StitchMCPService singleton with FastAPI lifespan — avoids ADK session bug #2927 (per-call subprocess pattern)
- (2026-03-21) v2.0: Immediate asset download on generation — Stitch signed URLs expire in minutes; store in Supabase Storage for permanent URLs
- (2026-03-21) v2.0: Design system persistence per project — DESIGN.md locked after approval, injected into all subsequent prompts for visual consistency
- (2026-03-21) v2.0: Capacitor for hybrid mobile — native-like mobile from React output without requiring native dev skills
- (2026-03-21) v2.0: Windows dev requires ProactorEventLoop policy + --no-reload for MCP subprocess support
- (2026-03-21) 16-01: app_projects.user_id plain UUID (no FK to auth.users) — simplifies service-role testing; screen_variants.user_id FK auth.users for GDPR cascade delete
- (2026-03-21) 16-01: stitch-assets bucket public=true — HTML previews non-sensitive; security perimeter is Stitch API key, not bucket visibility
- (2026-03-21) 16-01: Migration applied via Supabase Management API (Docker not running); remote-only workflow confirmed for Windows dev environment
- (2026-03-21) 16-02: noqa: BLE001 directives removed — BLE001 not enabled in project ruff config
- (2026-03-21) 16-02: asyncio aliased as _asyncio_lifespan inside lifespan to avoid shadowing stdlib asyncio at module level
- (2026-03-21) 16-02: StitchMCPService has no start()/stop() methods — lifecycle managed externally from lifespan for clean separation

### Blockers/Concerns

- Phase 10 (Analytics): Confirm Supabase tier supports CREATE MATERIALIZED VIEW before committing to pre-aggregation. Fallback: scheduled daily summary table.
- Phase 11 (Integrations): Verify current rate limits and pagination behavior for Sentry, PostHog, GitHub APIs before implementing proxy tools.
- General: recharts 3.x has three breaking changes (activeIndex removal, CategoricalChartState, z-index) — check against any examples used in Phases 8 and 10.
- Phase 16 (v2.0): ADK MCPToolset session persistence bug #2927 — solution is mcp SDK directly (not ADK MCPToolset); test required on target environment.
- Phase 16 (v2.0): asyncio.Lock serializes all Stitch calls per FastAPI instance — first bottleneck at ~100 concurrent builders; mitigate with Cloud Run min-instances before scaling.

## Session Continuity

Last session: 2026-03-21T13:35:30Z
Stopped at: Completed 16-02-PLAN.md — StitchMCPService singleton, FastAPI lifespan wiring, ADK tool wrappers
Resume file: None
