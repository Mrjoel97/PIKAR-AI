---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Platform Hardening & Quality
status: planning
stopped_at: Completed 83-document-upload-bypass 83-01-test-harness-PLAN.md
last_updated: "2026-04-30T17:56:12.345Z"
last_activity: 2026-04-26 — Roadmap written, 7 phases (76-82), 17/17 requirements mapped
progress:
  total_phases: 15
  completed_phases: 7
  total_plans: 15
  completed_plans: 14
  percent: 99
---

---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Platform Hardening & Quality
status: planning
stopped_at: Completed 82-agent-restructuring 82-02-PLAN.md
last_updated: "2026-04-30T17:03:23.878Z"
last_activity: 2026-04-26 — Roadmap written, 7 phases (76-82), 17/17 requirements mapped
progress:
  [██████████] 99%
  completed_phases: 7
  total_plans: 13
  completed_plans: 13
---

---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Platform Hardening & Quality
status: planning
stopped_at: Completed 82-agent-restructuring 82-02-PLAN.md
last_updated: "2026-04-27T22:35:56.723Z"
last_activity: 2026-04-26 — Roadmap written, 7 phases (76-82), 17/17 requirements mapped
progress:
  total_phases: 8
  completed_phases: 7
  total_plans: 13
  completed_plans: 13
  percent: 97
---

---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Platform Hardening & Quality
status: planning
stopped_at: Completed 80-workflow-consistency-api-contracts 80-01-PLAN.md
last_updated: "2026-04-27T12:16:08.979Z"
last_activity: 2026-04-26 — Roadmap written, 7 phases (76-82), 17/17 requirements mapped
progress:
  [██████████] 97%
  completed_phases: 4
  total_plans: 13
  completed_plans: 8
---

---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Platform Hardening & Quality
status: planning
stopped_at: Completed 78-db-cache-performance 78-02-PLAN.md
last_updated: "2026-04-27T11:41:12.387Z"
last_activity: 2026-04-26 — Roadmap written, 7 phases (76-82), 17/17 requirements mapped
progress:
  total_phases: 8
  completed_phases: 4
  total_plans: 9
  completed_plans: 7
  percent: 15
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-26)

**Core value:** Users describe what they want in natural language and the system autonomously generates, manages, and grows their business operations
**Current focus:** v10.0 Platform Hardening & Quality — security, performance, architecture resilience, and agent quality fixes identified by comprehensive audit

## Current Position

Phase: 76 of 81 (Security Hardening) — ready to plan
Plan: —
Status: Ready to plan
Last activity: 2026-04-26 — Roadmap written, 7 phases (76-82), 17/17 requirements mapped

Progress: [█░░░░░░░░░] 15%

## Performance Metrics

**Velocity:**
- Recent plans average ~12 min each (v9.0 baseline)
- Total plans in v10.0: 13 estimated (TBD by plan-phase)

**By Phase (v10.0 — not yet started):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 76. Security Hardening | TBD | - | - |
| 77. Async Tool Pattern | TBD | - | - |
| 78. DB & Cache Performance | TBD | - | - |
| 79. Architectural Resilience | TBD | - | - |
| 80. Workflow Consistency & API Contracts | TBD | - | - |
| 81. Agent Config Fixes | TBD | - | - |
| 82. Agent Restructuring | TBD | - | - |

*Updated after each plan completion*
| Phase 76-security-hardening P02 | 18 | 2 tasks | 5 files |
| Phase 76-security-hardening P01 | 10 | 2 tasks | 5 files |
| Phase 77-async-tool-pattern P01 | 22 | 2 tasks | 7 files |
| Phase 77-async-tool-pattern P02 | 17 | 2 tasks | 5 files |
| Phase 78-db-cache-performance P01 | 15 | 1 tasks | 3 files |
| Phase 79-architectural-resilience P01 | 25 | 2 tasks | 4 files |
| Phase 78-db-cache-performance P02 | 35 | 2 tasks | 6 files |
| Phase 80-workflow-consistency-api-contracts P01 | 25 | 2 tasks | 4 files |
| Phase 80-workflow-consistency-api-contracts P02 | 50 | 2 tasks | 43 files |
| Phase 81-agent-config-fixes P01 | 12 | 2 tasks | 4 files |
| Phase 81-agent-config-fixes P02 | 7 | 2 tasks | 6 files |
| Phase 82-agent-restructuring P02 | 26 | 2 tasks | 12 files |
| Phase 83-document-upload-bypass P01 | 7 min | 1 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting v10.0:

- v10.0 start: Phase 76 (Security) first — independent fixes, unblock all others
- v10.0 ordering: 77/78/79/81 can run in parallel after 76; 80 depends on 78+79; 82 depends on 81
- v10.0 scope: hardening only — no new user-facing features, no Gemini 3 migration
- [Phase 76-security-hardening]: Slack allowlist uses frozenset with hooks.slack.com + api.slack.com + *.slack.com pattern; non-HTTPS rejected
- [Phase 76-security-hardening]: DOMPurify loaded lazily via require() inside getPurify() for SSR safety; synchronous API preserved for page.tsx call sites
- [Phase 76-security-hardening]: Webhook handlers fail-closed (HTTP 500) when signing secrets absent; matches Shopify/Stripe pattern already in codebase
- [Phase 76-security-hardening]: resolve_request_user_id default changed to allow_header_fallback=False; no production callers affected (grep confirmed)
- [Phase 77-async-tool-pattern]: ADK tool functions must be async def with direct await — ThreadPoolExecutor+asyncio.run is an anti-pattern that causes RuntimeError and per-invocation thread overhead
- [Phase 77-async-tool-pattern]: _resolve_connection_id in report_scheduling.py kept sync — SpreadsheetConnectionService.get_connection() is synchronous; tests calling async tool functions must use @pytest.mark.asyncio and await
- [Phase 77-async-tool-pattern]: app_builder.py: deleted _run_async centralized helper entirely — cleaner than leaving deprecated, prevents future misuse
- [Phase 77-async-tool-pattern]: setup_wizard.py: only mcp_test_integration converted — remaining 6 functions call synchronous services
- [Phase 78-db-cache-performance]: fork_session uses direct table.insert(bulk_rows) instead of append_event RPC — forked events get sequential versions without per-event atomicity overhead, eliminating N round-trips
- [Phase 78-db-cache-performance]: Batch pattern: collect IDs into list, guard on non-empty, issue single .in_() UPDATE — applied to resume_execution, rollback_session, and fork_session
- [Phase 79-architectural-resilience]: Rate limiter checks Redis CB state synchronously at function entry before any async Redis call
- [Phase 79-architectural-resilience]: In-process rate limit fallback uses fixed-window per-user counter with CRITICAL log once on first activation via _FALLBACK_ACTIVE flag
- [Phase 79-architectural-resilience]: supabase_circuit_breaker integrated at _execute_with_retry chokepoint — no per-method decoration needed
- [Phase 78-db-cache-performance]: cachetools.TTLCache uses a single global TTL; set_cached ttl param retained for API compatibility but cache-wide 30s governs — documented in docstring
- [Phase 78-db-cache-performance]: DAU/MAU count semantics preserved as total row count (not DISTINCT user_id) — DISTINCT counts deferred to future RPC function
- [Phase 78-db-cache-performance]: All Redis keys use REDIS_KEY_PREFIXES constants; stats counters namespaced pikar:stats:hits/misses
- [Phase 80-workflow-consistency-api-contracts]: Atomic INSERT...SELECT...WHERE replaces SELECT COUNT + INSERT TOCTOU race at the database level
- [Phase 80-workflow-consistency-api-contracts]: p_max_concurrent=0 treated as unlimited; SQL function skips count check entirely via IF branch
- [Phase 80-workflow-consistency-api-contracts]: OpenAPI schema exported via uv run python without server; temp .py file avoids shell quoting issues on Windows
- [Phase 80-workflow-consistency-api-contracts]: from __future__ import annotations removed from all 34 app/routers/*.py files — deferred annotation evaluation prevents Pydantic TypeAdapter from resolving ForwardRefs during schema generation
- [Phase 80-workflow-consistency-api-contracts]: WorkflowExecution and WorkflowTrigger types kept hand-maintained — backend exposes execution as untyped dict in OpenAPI spec; TODO(ARCH-04) tags added as breadcrumbs
- [Phase 81-agent-config-fixes]: Sales uses get_model() (Pro) + DEEP_AGENT_CONFIG — parent SalesIntelligenceAgent was incorrectly on Flash despite handling complex deal analysis
- [Phase 81-agent-config-fixes]: HR/Ops/CS keep get_routing_model() — only token ceiling raised from ROUTING_AGENT_CONFIG (1024) to DEEP_AGENT_CONFIG (4096) to prevent silent truncation
- [Phase 81-agent-config-fixes]: Reporting agent keeps legacy use_skill/list_available_skills from enhanced_tools alongside new instruction blocks — no tool changes needed
- [Phase 81-agent-config-fixes]: Research agent instructions.py converted from plain string to concatenated expression; tool list not modified — skill tools will be wired in a future phase
- [Phase 82-agent-restructuring]: search_knowledge canonical home is app.agents.tools.knowledge; content/__init__.py re-exports for backward compat
- [Phase 82-agent-restructuring]: Marketing parent delegates video/image/blog to Content Agent; start_initiative_from_idea only in InitiativeOpsAgent sub-agent
- [Phase 83-document-upload-bypass]: chatHarness uses module-scope vi.mock + per-render mockReturnValue; hook return shapes copied verbatim from each hook's TS signature; jsdom polyfills (scrollIntoView, matchMedia) live inside the harness rather than vitest.config.mts

### Roadmap Evolution

- Phase 83 added: Document Upload Bypass — production hotfix bug 1/7
- Phase 84 added: Voice Gate Deadlock Fix — production hotfix bug 2/7
- Phase 85 added: Render SSE Timeout — production hotfix bug 3/7
- Phase 86 added: Document Generation Skills Exposure — production hotfix bug 4/7
- Phase 87 added: Mic Dictation via Web Speech API — production hotfix bug 5/7
- Phase 88 added: Chat and Workspace Persistence — production hotfix bug 6/7
- Phase 89 added: Knowledge Vault Auto Sync — production hotfix bug 7/7

### Pending Todos

None yet.

### Blockers/Concerns

- PERF-01 (~20 files): largest single item in milestone; plan-phase should split into 2 plans by file batch
- ARCH-04 (OpenAPI codegen): requires CI pipeline changes — may need coordination with existing GitHub Actions setup
- Pre-existing failure in frontend/src/components/chat/ChatInterface.test.tsx — 4 tests crash with "useSessionControl must be used within a SessionControlProvider" due to ChatInterface.tsx adding 11 module-scope hooks after the test was written. Plan 01 cannot fix this (vi.mock is per-file). Documented in .planning/phases/83-document-upload-bypass/deferred-items.md; Plan 02 will adopt the harness inside ChatInterface.test.tsx to resolve.

## Session Continuity

Last session: 2026-04-30T17:55:42.135Z
Stopped at: Completed 83-document-upload-bypass 83-01-test-harness-PLAN.md
Resume file: None
