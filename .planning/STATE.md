---
gsd_state_version: 1.0
milestone: v9.0
milestone_name: Self-Evolution Hardening
status: ready_to_plan
stopped_at: v9.0 roadmap created — 5 phases (71-75), 27 requirements mapped, 100% coverage
last_updated: "2026-04-12T06:00:00.000Z"
last_activity: 2026-04-12 — v9.0 roadmap created with 5 phases; traceability complete; ready to plan Phase 71
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
in_flight_milestones:
  - v7.0 Production Readiness & Beta Launch (88%, Phase 56 executing)
  - v8.0 Agent Ecosystem Enhancement (Phase 63 in-progress, 64-70 pending)
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-11)

**Core value:** Users describe what they want in natural language and the system autonomously generates, manages, and grows their business operations
**Current focus:** v9.0 Self-Evolution Hardening — 5 phases (71-75) closing the four gaps (skill persistence, feedback loop, scheduled improvement cycle, runtime bugs). v7.0 Phase 56 and v8.0 phases 63-70 continue in parallel.

## Current Position

Milestone: v9.0 Self-Evolution Hardening
Phase: Phase 71 of 75 — not started (ready to plan)
Plan: —
Status: Ready to plan
Last activity: 2026-04-12 — v9.0 roadmap created with 5 phases, all 27 requirements mapped

Progress: [░░░░░░░░░░] 0%

## Parallel Milestones

- **v7.0** — Phase 56 GDPR/RAG hardening (56-01 through 56-04 planned, executing)
- **v8.0** — Agent-enhancement phases 63-04, 64-70 (63-03 shipped, 63-04 next, 64-70 pending)

## Performance Metrics

**Velocity:**
- Total plans completed: 15 (v6.0 + v7.0) / 72 (all milestones)
- Average duration: 12min
- Total execution time: ~198min

**By Phase (recent):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 49 | 5 | 85min | 17min |
| 50 | 4 | 83min | 21min |
| 51 | 4 | 104min | 26min |

**Recent Trend:**
- Last 5 plans: 25min, 35min, 24min, 20min (Phase 51)
- Trend: Stable

*Updated after each plan completion*
| Phase 57 P02 | 4min | 2 tasks | 6 files |
| Phase 52-persona-feature-gating P02 | 11 | 2 tasks | 5 files |
| Phase 57 P01 | 9min | 2 tasks | 7 files |
| Phase 52-persona-feature-gating P01 | 18 | 2 tasks | 13 files |
| Phase 52-persona-feature-gating P03 | 21 | 2 tasks | 5 files |
| Phase 57 P03 | 13min | 2 tasks | 5 files |
| Phase 52-persona-feature-gating P04 | 16 | 2 tasks | 6 files |
| Phase 58 P03 | 9min | 2 tasks | 6 files |
| Phase 58 P01 | 9min | 2 tasks | 7 files |
| Phase 58 P04 | 8min | 2 tasks | 7 files |
| Phase 58 P02 | 13min | 2 tasks | 7 files |
| Phase 59 P01 | 6min | 2 tasks | 5 files |
| Phase 59 P02 | 5min | 2 tasks | 5 files |
| Phase 59 P03 | 8min | 3 tasks | 9 files |
| Phase 60 P01 | 8min | 2 tasks | 5 files |
| Phase 60 P02 | 9min | 2 tasks | 4 files |
| Phase 60 P04 | 15min | 2 tasks | 8 files |
| Phase 61 P01 | 7min | 2 tasks | 3 files |
| Phase 60 P03 | 9min | 2 tasks | 6 files |
| Phase 61 P02 | 9min | 2 tasks | 3 files |
| Phase 53 P01 | 43min | 2 tasks | 5 files |
| Phase 53 P02 | 13min | 2 tasks | 9 files |
| Phase 53 P03 | 37min | 2 tasks | 5 files |
| Phase 53 P04 | 22min | 2 tasks | 11 files |
| Phase 56 P01 | 20min | 3 tasks | 5 files |
| Phase 61-content-agent-enhancement P04 | 20 | 2 tasks | 4 files |
| Phase 56 P02 | 15 | 3 tasks | 5 files |
| Phase 56-gdpr-rag-hardening P03 | 11 | 3 tasks | 8 files |
| Phase 56-gdpr-rag-hardening P04 | 14 | 3 tasks | 7 files |
| Phase 62-sales-agent-enhancement P01 | 11 | 2 tasks | 3 files |
| Phase 62-sales-agent-enhancement P02 | 15 | 3 tasks | 4 files |
| Phase 62-sales-agent-enhancement P03 | 18 | 2 tasks | 5 files |
| Phase 62-sales-agent-enhancement P04 | 19 | 2 tasks | 6 files |
| Phase 63-marketing-agent-enhancement P01 | 8 | 2 tasks | 4 files |
| Phase 63-marketing-agent-enhancement P02 | 25min | 2 tasks | 4 files |
| Phase 63-marketing-agent-enhancement P03 | 6min | 2 tasks | 2 files |

## Accumulated Context

### Roadmap Evolution

- Phase 53.1 inserted after Phase 53 to close auth and middleware consistency gaps before Onboarding & UX Polish begins
- The inserted phase owns five approved fixes in sequence: backend auth unification, rate-limit identity hardening, proxy consolidation, backend-owned invite privilege reads, and legacy auth guard cleanup
- Phase 54 is now complete across three plans: onboarding-to-first-chat completion, Google Workspace credential persistence/status truthfulness, and dashboard empty-state polish
- Phase 55 is now complete across three plans: disconnect truthfulness, stale-state cleanup, backend-owned Google Workspace disconnect, SSE/session isolation guardrails, and a canonical load harness with threshold evaluation/runbook
- Phase 56 is now planned across four plans: personal data export, deletion cascade hardening + audit anonymization, Knowledge Vault auth/ingestion truthfulness, and the final RAG relevance/latency/concurrency contract

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- v8.0 roadmap: Phase 57 (Proactive Intelligence) first -- notification infrastructure feeds into FIN-03, FIN-05, OPS-04, LEGAL-03, DATA-02, ADMIN-03
- v8.0 roadmap: Phase 58 (Non-Technical UX) second -- suggestion chips and TL;DR mode improve every subsequent agent enhancement
- v8.0 roadmap: Phase 59 (Cross-Agent) third -- unified action history and cross-agent synthesis are cross-cutting
- v8.0 roadmap: Phases 60-69 (agent-specific) follow ecosystem infra in any order but logically sequential
- v8.0 roadmap: Phase 70 (Degraded Tool Cleanup) last -- agent phases may replace some degraded tools during their own work
- v7.0 gap closure active: phases 49-55 are fully executed in code, Phase 56 is fully planned inside GSD, and deferred runtime UAT for 50/51/55 remains open
- [Phase 56]: Privacy work executes in this order: export first, then deletion hardening, then vault auth/ingestion correctness, then the governed RAG contract
- [Phase 56]: User-vault proxy routes must forward bearer auth and file-type-aware extraction must replace raw byte decoding before relevance/latency metrics can be trusted
- [Phase 56]: `delete_user_account()` must be re-inventoried against newer user-linked tables and governance audit anonymization before v7 can be considered privacy-complete
- [Phase 53-01]: Invite email flow maps UI Member -> backend editor, expands invite roles to include admin, and keeps the working /dashboard/team/join token route live until 53-04 ships the public /invite/[token] page
- [Phase 53-02]: Admin-only role hiding must be enforced in both Sidebar and PremiumShell because PremiumShell renders the live dashboard navigation for most pages
- [Phase 53-02]: Server-side /admin access denials redirect through /dashboard?notice=workspace-admin-only so members still receive the informational toast even when the backend blocks the page before client guard mount
- [Phase 53-02]: Configuration page is guarded alongside billing to close the direct-link loophole for an admin-only nav destination
- [Phase 53-03]: Team management UI is split from analytics by introducing /dashboard/settings/team, while /dashboard/team remains the analytics dashboard
- [Phase 53-03]: Invite resend now uses backend token rotation first and reuses that refreshed token for email delivery to avoid duplicate pending invites
- [Phase 53-04]: Public invite acceptance requires auth returnUrl propagation through login, signup, and OAuth callback -- the invite page alone is not enough
- [Phase 53-04]: Legacy /dashboard/team/join invite URLs now redirect to /invite/{token} so previously-sent emails remain usable after the route migration
- [Phase 53-04]: Role UI now presents only Admin and Member, while legacy viewer records are normalized to Member vocabulary in the frontend until backend data is resaved
- [Phase 53.1-01]: Canonical backend auth now lives in app_utils.auth while onboarding remains the compatibility import path for existing routers; middleware resolves authenticated identity from bearer JWTs before any header fallback
- [Phase 53.1-02]: Active Next.js route protection now delegates auth validation to the shared getClaims()-based proxy helper, and public invite metadata is served from a backend-owned endpoint instead of a frontend service-role route
- [Phase 54]: Post-onboarding and checklist launch prompts must land on a chat-enabled surface and be consumed exactly once; a hidden-chat command-center landing does not satisfy UX-01
- [Phase 54-01]: Launch prompts create a fresh chat session before auto-send so onboarding, initiative, and checklist handoffs never get swallowed by restored history or the welcome-message shell
- [Phase 54]: Google Workspace should only report connected when reusable stored credentials exist; Google identity presence alone is not enough for UX-02
- [Phase 54-02]: Supabase OAuth callback now syncs Google provider tokens through a server-only backend endpoint, while runtime Google consumers resolve canonical `integration_credentials` first and fall back to legacy refresh sources only for compatibility
- [Phase 54]: Dashboard no-data states should reuse actionable empty-state patterns with a clear next step rather than passive placeholder copy
- [Phase 54-03]: Shared EmptyState now supports both link and button CTAs so Finance, Governance, Content, Portfolio, and Departments can standardize zero-data UX on one contract
- [Phase 54-03]: Content distinguishes "no content exists yet" from "filters hid existing content" so the default calendar never falls back to a silent blank state
- [Phase 55-01]: Disconnected providers only surface sync-error status when usable credentials still exist; stale sync residue alone must read as disconnected
- [Phase 55-01]: Google Workspace disconnect records an explicit backend tombstone so legacy refresh-token fallbacks cannot keep the integration falsely connected after a user disconnects
- [Phase 55-02]: SSE chat ignores request-body user_id when bearer-authenticated identity is present; authenticated ownership must come from the token path only
- [Phase 55-02]: Session metadata cache keys must include app_name + user_id + session_id; session_id-only caching is unsafe for multi-user reuse
- [Phase 55-02]: Background stream updates and activity events remain attached to the producing session rather than being retargeted to whichever session is currently visible
- [Phase 55-03]: Canonical load testing runs through tests/load_test/locustfile.py, with report_assertions.py evaluating Locust *_stats.csv artifacts against chat p95/fail-ratio thresholds and optional /health/connections captures
- [Phase 55-03]: The default Locust mix keeps ChatHeavyUser as a minority stress cohort instead of an accidental 50/50 split with the standard authenticated user class
- [Phase 57-02]: Rolling 30-day baseline with 7-point minimum for anomaly detection; 4 persona tones for budget pacing
- [Phase 52-persona-feature-gating]: Used custom DOM event bus for 403→UpgradeGateModal bridge; keeps api.ts free of React dependencies
- [Phase 57]: Proactive alert dedup via DB unique constraint (user_id, alert_type, alert_key) rather than Redis TTL for durable daily alerts
- [Phase 57]: KPI change threshold at 5% and stalled initiative threshold at 7 days for daily briefing relevance filtering
- [Phase 52-persona-feature-gating]: Subscription-first persona resolution: subscriptions.tier beats profile.persona; wrapped in try/except to fall through gracefully
- [Phase 52-persona-feature-gating]: Singleton agents remain persona-agnostic; only factory-created instances (per-request/workflow) get persona injection
- [Phase 52-persona-feature-gating]: KpiHeader renders only when currentPersona set — admin-safe, mirrors existing try/catch pattern
- [Phase 52-persona-feature-gating]: Zero-state hint via string match on value (/usr/bin/bash, 0, 0%) — no extra backend flag needed
- [Phase 52-persona-feature-gating]: refreshKey counter pattern for useKpis refresh — simplest correct re-trigger approach
- [Phase 57-03]: MVP connectivity checks limited to Google, Slack, Stripe; keyword-based competitor change classification (no LLM) for low-latency inline classification
- [Phase 52-persona-feature-gating]: Enrichment metrics (initiative_breakdown, workflow_success_rate, revenue_trend) appended to components dict — non-weighted, preserves existing score computation
- [Phase 52-persona-feature-gating]: Departments page not behind GatedPage — departments router has no require_feature dependency, available to all authenticated users
- [Phase 58]: IIFE pattern in MessageItem for scoped TL;DR variable extraction without component-level state
- [Phase 58]: ExecutiveAgent-only TL;DR instruction injection; sub-agents inherit via conversation-level system prompt
- [Phase 58]: Reserved slot for activity followups to guarantee visibility in weighted suggestion pool
- [Phase 58]: SuggestionChips shown only on fresh sessions (messages.length===0); mid-conversation contextual suggestions deferred
- [Phase 58]: Reused delimiter-parser-then-component pattern from TL;DR (58-01) for intent clarification consistency
- [Phase 58]: Intent detection chains after TL;DR: tldr strip -> intent strip -> markdown render
- [Phase 58]: Lazy _get_engine() wrapper for workflow discovery service testability without circular imports
- [Phase 58]: Client-side intent prefix detection for parallel NL workflow search (no extra backend latency)
- [Phase 58]: 15-second auto-dismiss timer for WorkflowLauncher to prevent stale suggestions
- [Phase 59]: Per-domain try/except inside each _gather method plus asyncio.gather return_exceptions for double-layer fault tolerance in cross-agent synthesis
- [Phase 59-02]: Fire-and-forget logging pattern (matching InteractionLogger) for unified action history -- exceptions caught and warned, never propagated
- [Phase 59-02]: Singleton service with module-level log_agent_action() convenience function for zero-friction adoption by other services
- [Phase 59]: ilike topic search for decision queries (simpler API than full tsquery); 7-day window + 24h inactivity threshold for nudge eligibility; contextual per-step nudge messages rather than generic reminders
- [Phase 60-01]: Five weighted factors for health score: revenue_trend (25%), runway_months (25%), cash_flow_ratio (20%), collection_rate (15%), burn_stability (15%)
- [Phase 60-01]: Insufficient data returns score 50 (yellow) with explicit explanation rather than failing
- [Phase 60-01]: Burn stability mirrors runway scoring -- both reflect same risk dimension from different angles
- [Phase 60]: Lazy DB imports in expense categorization service for testability without full Supabase client chain
- [Phase 60]: Stateless categorizer per-call instantiation -- cheap to create, no singleton needed
- [Phase 60-04]: Lazy DB imports (no BaseService inheritance) for ForecastService and ScenarioModelingService; module-level helper functions for patchable test mocking
- [Phase 60-04]: Weighted linear regression with recent_weight=2.0 for high-confidence forecasts; confidence tier thresholds at 3 and 6 months of data
- [Phase 60]: Lazy imports for InvoiceFollowupService and TaxReminderService inside aggregator to avoid circular dependency chains
- [Phase 60]: is_reminder_due checks 0-14 days before deadline (not after) to avoid stale reminders post-deadline
- [Phase 61-01]: simple_create_content tool structures context and saves draft; LLM generates text using returned prompt_context (tool does not generate text itself)
- [Phase 61-01]: Brand profile loading is optional (try/except) -- enhances output but never blocks content creation
- [Phase 61-02]: Pre-computed platform timing lookup tables instead of runtime PLATFORM_GUIDELINES string parsing for determinism and testability
- [Phase 61-02]: Two-mode tool pattern (schedule=False for suggestion, schedule=True for action) gives user explicit confirmation before scheduling
- [Phase 56-01]: JSON archive format for personal data export; single file covering all 14 domains is simpler to audit and store than per-table CSVs
- [Phase 56-01]: Recursive _redact_sensitive_data covers nested dicts/lists so session_events.event_data tokens and similar nested secrets are always caught
- [Phase 56-01]: PersonalDataExportService 14-domain inventory is the authoritative checklist for 56-02 deletion cascade hardening
- [Phase 61-04]: Module-level ContentCalendarService is a lazy factory function (not class import) to avoid Supabase chain at import time while remaining patch-friendly for tests
- [Phase 61-04]: get_social_analytics re-exported at module level from lazy wrapper so tests can patch app.services.content_performance_service.get_social_analytics without triggering social analytics import chain
- [Phase 56-02]: Anonymize governance_audit_log rather than delete: rows serve compliance audit trail; actor identity removed via sentinel UUID + NULL ip_address
- [Phase 56-02]: Sentinel UUID '00000000-0000-0000-0000-000000000000' for governance anonymization: user_id is NOT NULL so NULL would require schema change; sentinel is unambiguous to all consumers
- [Phase 56-02]: Migration-as-SQL-source-of-truth testing: integration tests parse migration file for coverage assertions, no live DB needed in CI
- [Phase 56-03]: extract_text_from_bytes returns None for storage-only formats rather than raising — None is the signal to the caller that embedding is not applicable
- [Phase 56-03]: Vault proxy forwards Authorization header from incoming Next.js request to backend — backend remains sole trust boundary, body user_id removed from both proxy calls
- [Phase 56-03]: isSearchableFileType in VaultInterface mirrors backend MIME set; RAG processing only triggered for searchable file types on upload
- [Phase 56-04]: Eval uses cosine similarity between query and document embeddings without a live Supabase vector store — measures embedding quality directly as the true relevance signal
- [Phase 56-04]: Zero-vector embedding fallback causes eval to fail loudly when credentials absent — CI reveals credential gaps rather than silently passing
- [Phase 56-04]: Concurrent regression tests use sys.modules supabase stubs injected before app module import — avoids live Supabase SDK while testing real knowledge_vault.py code paths
- [Phase 62-01]: Lazy import HubSpotService inside generate_followup_email; CRM enrichment is non-fatal (try/except); test mock path targets app.services.hubspot_service.HubSpotService
- [Phase 62-02]: Lazy imports inside tool functions to avoid app.agents.__init__ chain in tests
- [Phase 62-02]: Classify at-risk by early-stage + close_date within 14 days OR amount < 50% of pipeline average
- [Phase 62-02]: Migration committed as SQL artifact only -- NOT applied to live DB per plan instructions
- [Phase 62-03]: Patch at service module level (app.services.document_service.DocumentService) not at tool module level for lazy-import tool testing
- [Phase 62-03]: HubSpot enrichment in generate_sales_proposal is non-fatal (try/except); proposal degrades gracefully when CRM unavailable
- [Phase 62-03]: Single As Quoted fallback line item when total_amount given without line_items — keeps sales_proposal template table populated
- [Phase 62-04]: Module-level HubSpotService/AdminService imports in hubspot_tools.py enable patch targeting in tests without internal refactoring
- [Phase 62-04]: score_hubspot_lead checks hubspot_contact_id before push -- contacts without HS ID degrade to local-only silently
- [Phase 62-04]: sync_deal_notes always writes to local hubspot_deals.properties even when HubSpot push succeeds -- local DB is source of truth for last_meeting_notes
- [Phase 63-marketing-agent-enhancement]: [Phase 63-01]: WoW percentage uses conversion counts (not spend) as the narrated trend signal because customer-count change is the marketing-meaningful number users care about
- [Phase 63-marketing-agent-enhancement]: [Phase 63-01]: _compute_wow returns None when prior baseline is zero; caller renders 'new this week' instead of synthesizing a 0% or infinite delta
- [Phase 63-marketing-agent-enhancement]: [Phase 63-01]: summarize_campaign_performance returns both summary_text and the full structured dict so the agent can answer per-campaign follow-ups without re-calling the tool
- [Phase 63-02]: CrossChannelAttributionService unifies google_ads, meta_ads, email, organic into one ROAS-comparable view — organic = Shopify total minus attributed paid/email revenue
- [Phase 63-02]: Budget reallocation safety caps: shift min(20% of source daily spend, $50/day); channels within 10% ROAS are 'well-balanced' and return no-action
- [Phase 63-02]: Attribution tools placed on MarketingAgent PARENT (not a sub-agent) because cross-channel ROAS and budget allocation are strategic decisions, not campaign-specific CRUD
- [Phase 63-02]: Organic channel is excluded from reallocation source list (no spend lever to shift); share-of-revenue rounding drift assigned to largest-revenue channel so totals always sum to 100%
- [Phase 63-03]: Conversational campaign wizard is instruction-driven (no new tools/services) — 6-step flow lives entirely inside _CAMPAIGN_INSTRUCTION
- [Phase 63-03]: Platform auto-recommendation heuristic: product/visual → Meta Ads; service/B2B/search intent → Google Ads; local → Google; awareness → Meta-first
- [Phase 63-03]: connect_google_ads_status / connect_meta_ads_status wired on CampaignAgent (not AdPlatformAgent) so the wizard verifies connectivity before recommending a platform
- [Phase 63-03]: Real ad API calls stay on AdPlatformAgent — wizard escalates to parent → AdPlatformAgent for create_google_ads_campaign / create_meta_ads_campaign, keeping budget cap safety centralized
- [Phase 63-03]: Explicit Step 5 user confirmation gate plus PAUSED-state default give two independent safety layers before any ad spend is committed

### Pending Todos

None yet.

### Blockers/Concerns

- Ad platform OAuth approval (Google Ads, Meta) may have multi-week review cycles -- plan early if needed.
- 32 degraded tools to replace -- FIN-06 done (generate_forecast, create_forecast replaced in Phase 60-04); remaining in agent-specific phases (SALES-06, MKT-06, OPS-06, HR-06, DATA-05) and Phase 70.

## Session Continuity

Last session: 2026-04-11T19:42:35Z
Stopped at: Completed 63-03 (conversational campaign creation wizard on CampaignAgent)
Resume file: None
