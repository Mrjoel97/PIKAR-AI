# Requirements: Pikar AI (v7.0 · v8.0 · v9.0)

**v7.0 defined:** 2026-04-06
**v9.0 defined:** 2026-04-11
**Core Value:** Users describe what they want in natural language and the system autonomously generates, manages, and grows their business operations

> **Note — parallel milestones:** v7.0 (Production Readiness, 88%) and v8.0 (Agent Ecosystem Enhancement, executing phases 57-70) are still in flight. v9.0 runs in parallel and closes the self-evolution gaps identified in the 2026-04-11 engineering assessment. Each milestone section owns its own requirement IDs and roadmap phases.

## v7.0 Requirements

Requirements for Production Readiness & Beta Launch. Each maps to roadmap phases.

### Security & Auth Hardening

- [x] **AUTH-01**: User routes (/dashboard/*, /settings/*, /admin/*) are protected server-side via Next.js middleware — unauthenticated requests redirect to login
- [x] **AUTH-02**: User sees a meaningful error boundary UI when a page or component crashes, not a blank screen
- [x] **AUTH-03**: Admin can assign roles (admin, member, viewer) to workspace users via RBAC system
- [x] **AUTH-04**: User actions that modify data are logged in an audit trail with actor, action, target, and timestamp
- [x] **AUTH-05**: Admin can view audit trail logs filtered by user, action type, and date range

### Billing & Payments

- [x] **BILL-01**: User can complete Stripe checkout flow and receive an active subscription
- [x] **BILL-02**: Stripe webhook correctly processes subscription lifecycle events (created, updated, canceled, payment_failed)
- [x] **BILL-03**: User subscription status is reflected in real-time in the app (active, past_due, canceled)
- [x] **BILL-04**: Admin can view billing dashboard showing active subscriptions, MRR, and churn metrics
- [x] **BILL-05**: User can manage their subscription (upgrade, downgrade, cancel) via Stripe Customer Portal

### Observability & Monitoring

- [ ] **OBS-01**: Application errors are captured and reported to Sentry with stack traces, user context, and request metadata
- [ ] **OBS-02**: Admin can view a monitoring dashboard showing agent response latency (p50, p95, p99)
- [ ] **OBS-03**: Admin can view error rate trends (by endpoint, by agent, by time period)
- [ ] **OBS-04**: Admin can view AI cost tracking (token usage per agent, per user, per day)
- [ ] **OBS-05**: Health endpoints return structured status for all critical dependencies (Supabase, Redis, Gemini, integrations)

### Load & Stress Testing

- [ ] **LOAD-01**: System handles 100 concurrent authenticated users without degraded response times (p95 < 3s for chat initiation)
- [ ] **LOAD-02**: SSE streaming handles 100 simultaneous connections without dropped connections or memory leaks
- [ ] **LOAD-03**: Database connection pooling is verified to handle concurrent load without exhaustion
- [ ] **LOAD-04**: Load test suite exists and can be run on-demand against staging environment

### Onboarding & UX Polish

- [ ] **UX-01**: User can complete full signup → persona selection → onboarding → first chat flow without errors
- [ ] **UX-02**: Google OAuth flow successfully grants Gmail and Calendar access and persists tokens
- [ ] **UX-03**: Every dashboard page shows a meaningful empty state (not blank) when no data exists
- [x] **UX-04**: Shell header KPIs display real computed data (not placeholders) for the user's persona
- [x] **UX-05**: Each agent responds with persona-appropriate tone, depth, and tool selection based on persona-specific instructions

### Persona & Feature Gating

- [x] **GATE-01**: Features are soft-gated per persona tier — restricted features show upgrade prompts instead of hiding completely
- [x] **GATE-02**: ExecutiveAgent is persona-aware — routes to appropriate agents and adjusts behavior based on user's persona tier
- [x] **GATE-03**: Enterprise persona shows real portfolio health metrics computed from active initiatives and workflows
- [x] **GATE-04**: SME persona has functional department coordination — tasks route to correct department agents with visibility controls

### Multi-User & Teams

- [ ] **TEAM-01**: User can invite team members to a workspace via email
- [ ] **TEAM-02**: Invited user can join workspace and see shared resources (initiatives, workflows, content)
- [ ] **TEAM-03**: Workspace admin can assign and change roles (admin, member) for team members
- [ ] **TEAM-04**: Team members see role-appropriate content — members cannot access admin functions

### Data Compliance

- [x] **GDPR-01**: User can request full export of their personal data in a standard format (JSON/CSV)
- [x] **GDPR-02**: User can request account deletion, which removes all personal data and anonymizes audit logs
- [x] **GDPR-03**: Data deletion cascades correctly through all related tables (sessions, initiatives, workflows, content, integrations)

### Integration Quality

- [ ] **INTG-01**: OAuth connect/disconnect/reconnect cycle works end-to-end for all integration providers without stale token issues
- [ ] **INTG-02**: SSE streaming remains stable under concurrent multi-user load (no cross-session data leakage)
- [ ] **INTG-03**: Multi-user sessions maintain isolation — User A's chat context never bleeds into User B's session

### RAG Hardening

- [x] **RAG-01**: Knowledge Vault ingestion processes documents and produces searchable embeddings with >80% relevance on test queries
- [x] **RAG-02**: Knowledge search returns results within 2 seconds for typical queries
- [x] **RAG-03**: RAG pipeline handles concurrent ingestion and search without corruption or deadlocks

## v9.0 Requirements — Self-Evolution Hardening

Requirements for closing the self-improvement engine feedback loop. Derived from the 2026-04-11 engineering assessment. Each maps to a v9.0 roadmap phase (Phase 71+).

### SIE — Skill Refinement Persistence

- [ ] **SIE-01**: Supabase migration creates `skill_versions(id, skill_name, version, knowledge, previous_version_id, source_action_id, created_by, created_at, is_active, metadata)` with a unique partial index on `(skill_name)` where `is_active=true`
- [ ] **SIE-02**: `SelfImprovementEngine._execute_skill_refined` writes the refined knowledge and bumped version to `skill_versions` and flips the `is_active` pointer inside a single transaction
- [ ] **SIE-03**: `SelfImprovementEngine._attempt_revert` loads the most-recent non-active version from `skill_versions` and restores it as active, so the validate → revert loop is actually reversible
- [ ] **SIE-04**: Skills registry startup hydration reads the active row from `skill_versions` for each registered skill, so refinements survive Cloud Run cold starts
- [ ] **SIE-05**: Admin API `GET /self-improvement/skills/{name}/history` returns the full version chain with diff summaries
- [ ] **SIE-06**: UAT gate — refine a skill via the engine, restart the FastAPI process, and confirm the agent serves the refined knowledge on the next call

### FBL — Closed Feedback Loop

- [ ] **FBL-01**: `InteractionLogger.log_interaction` accepts `task_completed`, `was_escalated`, `had_followup`, `user_feedback` kwargs and writes them to `interaction_logs` on insert (currently only response time and tokens land in the row, and the agent tool path crashes because the kwarg isn't declared)
- [ ] **FBL-02**: New route `POST /interactions/{id}/feedback` wired to `InteractionLogger.record_feedback`, rate-limited, workspace-scoped via existing auth middleware
- [ ] **FBL-03**: SSE chat stream emits the newly-created `interaction_id` as the final event so the frontend can anchor the feedback widget to the correct row
- [ ] **FBL-04**: Frontend `MessageItem` component shows thumbs-up / thumbs-down buttons on agent messages and posts to `/interactions/{id}/feedback` on click, with optimistic UI
- [ ] **FBL-05**: SSE `finally` block in `fast_api_app.py` infers `task_completed` from whether the final turn produced a tool-call error and passes it through to `log_interaction`
- [ ] **FBL-06**: Agent `report_interaction` tool updates the existing interaction row (matched by session_id + recency) instead of inserting a duplicate
- [ ] **FBL-07**: UAT gate — user sends a chat message, clicks thumbs-down, `interaction_logs.user_feedback='negative'` is written, and running `evaluate_skills` then produces a non-default `positive_rate` reflecting the real signal

### SCH — Scheduled Improvement Cycle

- [ ] **SCH-01**: New scheduled endpoint `POST /scheduled/self-improvement-cycle` gated by `X-Scheduler-Secret` header, calling `run_improvement_cycle(days=7, auto_execute=<admin_setting>)`
- [ ] **SCH-02**: Cloud Scheduler configuration and operator runbook to hit the new endpoint daily at 03:00 UTC (committed as docs, not infra code)
- [ ] **SCH-03**: Admin setting `self_improvement.auto_execute_enabled` (default false) and `self_improvement.auto_execute_risk_tiers` (default `["skill_demoted","pattern_extract"]`) readable by the engine
- [ ] **SCH-04**: `execute_improvement` honors the tier gate — actions outside the allowed tiers are created with status `pending_approval` instead of executing immediately
- [ ] **SCH-05**: New route `POST /self-improvement/actions/{id}/approve` executes a pending action; admin UI exposes an approval queue with approve/reject buttons
- [ ] **SCH-06**: Every auto-executed and every admin-approved action writes a row to `governance_audit_log` with action_type, skill_name, actor identity, and before/after effectiveness
- [ ] **SCH-07**: Safety circuit breaker — if two consecutive cycles regress average effectiveness by more than 5% or fail with errors, `auto_execute_enabled` auto-flips to false until an admin re-enables it from the dashboard
- [ ] **SCH-08**: UAT gate — operator hits the scheduled endpoint via curl, the cycle runs, the approval queue populates with `pending_approval` actions, and audit rows are written

### FIX — Engine Runtime Fixes

- [x] **FIX-01**: `SelfImprovementEngine._generate_with_gemini` uses the async Gemini client (`client.aio.models.generate_content` or `asyncio.to_thread`) so it no longer blocks the FastAPI event loop during improvement cycles
- [x] **FIX-02**: `identify_improvements` replaces `asyncio.get_event_loop().run_until_complete(bus.emit(...))` with plain `await bus.emit(...)`, eliminating the `RuntimeError: This event loop is already running` crash path
- [x] **FIX-03**: `skill_creator.find_similar_skills` uses `skill_embeddings` cosine similarity when the embeddings index is populated, with keyword overlap as the documented fallback for cold-start scenarios
- [x] **FIX-04**: `skill_embeddings.py` grows an async `build_index()` that backfills embeddings for the existing skill corpus on first boot and keeps them in sync on skill writes
- [x] **FIX-05**: Self-improvement cycle emits latency and outcome telemetry via the existing observability plumbing: `self_improvement.cycle_duration_ms`, `gemini_call_latency_ms`, `actions_executed_total`
- [x] **FIX-06**: Integration test asserts that `run_improvement_cycle` does not block the event loop for more than 500ms in any single await, measured with an asyncio task-scheduling probe

## v8.0 Requirements (Deferred items — v8.0 main scope lives in milestones/v8.0-REQUIREMENTS-DRAFT.md)

### Builder Dashboard
- **BLDR-01**: Builder dashboard with project status and resume capability
- **BLDR-02**: One-click deploy to public URL

### Advanced Enterprise
- **ENT-01**: SSO/SAML authentication for enterprise customers
- **ENT-02**: Data residency controls (region-specific storage)
- **ENT-03**: SOC 2 compliance certification preparation

## Out of Scope

| Feature | Reason |
|---------|--------|
| SSO/SAML authentication | Enterprise-only, not needed for solopreneur beta |
| Data residency controls | Requires infrastructure changes beyond this milestone |
| SOC 2 certification | Multi-month process, start after beta proves product-market fit |
| Mobile native app | Web-first, Capacitor hybrid covers mobile needs |
| Real-time WebSocket migration | SSE/polling sufficient for current scale |
| Multi-tenant admin | Founder-only admin for now |
| Payment enforcement on feature gates | Soft gating only — upgrade prompts, no hard blocks |
| v9.0: Model fine-tuning or RLHF | Loop closure is at skill-knowledge / workflow-template layer, not model weights |
| v9.0: Rewriting SelfImprovementEngine logic beyond the four identified gaps | Scope discipline — engine is implementation-complete, only the inputs/outputs/persistence are broken |
| v9.0: Cross-agent reward shaping | Multi-agent credit assignment is out of scope; per-skill effectiveness score is the only learning signal |
| v9.0: User-facing "AI is learning from you" marketing surface | Build the loop first; surface transparency to users in a follow-up milestone |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 49 | Complete |
| AUTH-02 | Phase 49 | Complete |
| AUTH-03 | Phase 49 | Complete |
| AUTH-04 | Phase 49 | Complete |
| AUTH-05 | Phase 49 | Complete |
| BILL-01 | Phase 50 | Complete |
| BILL-02 | Phase 50 | Complete |
| BILL-03 | Phase 50 | Complete |
| BILL-04 | Phase 50 | Complete |
| BILL-05 | Phase 50 | Complete |
| OBS-01 | Phase 51 | Pending |
| OBS-02 | Phase 51 | Pending |
| OBS-03 | Phase 51 | Pending |
| OBS-04 | Phase 51 | Pending |
| OBS-05 | Phase 51 | Pending |
| LOAD-01 | Phase 55 | Pending |
| LOAD-02 | Phase 55 | Pending |
| LOAD-03 | Phase 55 | Pending |
| LOAD-04 | Phase 55 | Pending |
| UX-01 | Phase 54 | Pending |
| UX-02 | Phase 54 | Pending |
| UX-03 | Phase 54 | Pending |
| UX-04 | Phase 52 | Complete |
| UX-05 | Phase 52 | Complete |
| GATE-01 | Phase 52 | Complete |
| GATE-02 | Phase 52 | Complete |
| GATE-03 | Phase 52 | Complete |
| GATE-04 | Phase 52 | Complete |
| TEAM-01 | Phase 53 | Pending |
| TEAM-02 | Phase 53 | Pending |
| TEAM-03 | Phase 53 | Pending |
| TEAM-04 | Phase 53 | Pending |
| GDPR-01 | Phase 56 | Complete |
| GDPR-02 | Phase 56 | Complete |
| GDPR-03 | Phase 56 | Complete |
| INTG-01 | Phase 55 | Pending |
| INTG-02 | Phase 55 | Pending |
| INTG-03 | Phase 55 | Pending |
| RAG-01 | Phase 56 | Complete |
| RAG-02 | Phase 56 | Complete |
| RAG-03 | Phase 56 | Complete |
| FIX-01 | Phase 71 | Complete |
| FIX-02 | Phase 71 | Complete |
| FIX-03 | Phase 71 | Complete |
| FIX-04 | Phase 71 | Complete |
| FIX-05 | Phase 71 | Complete |
| FIX-06 | Phase 71 | Complete |
| SIE-01 | Phase 72 | Pending |
| SIE-02 | Phase 72 | Pending |
| SIE-03 | Phase 72 | Pending |
| SIE-04 | Phase 72 | Pending |
| SIE-05 | Phase 72 | Pending |
| SIE-06 | Phase 72 | Pending |
| FBL-01 | Phase 73 | Pending |
| FBL-02 | Phase 73 | Pending |
| FBL-03 | Phase 73 | Pending |
| FBL-05 | Phase 73 | Pending |
| FBL-06 | Phase 73 | Pending |
| FBL-04 | Phase 74 | Pending |
| FBL-07 | Phase 74 | Pending |
| SCH-01 | Phase 75 | Pending |
| SCH-02 | Phase 75 | Pending |
| SCH-03 | Phase 75 | Pending |
| SCH-04 | Phase 75 | Pending |
| SCH-05 | Phase 75 | Pending |
| SCH-06 | Phase 75 | Pending |
| SCH-07 | Phase 75 | Pending |
| SCH-08 | Phase 75 | Pending |

**Coverage:**
- v7.0 requirements: 41 total — mapped to phases: 41 — unmapped: 0
- v9.0 requirements: 27 total — mapped to phases: 27 — unmapped: 0 ✓

---
*v7.0 requirements defined: 2026-04-06*
*v9.0 requirements defined: 2026-04-11*
*Last updated: 2026-04-12 — v9.0 traceability filled after roadmap creation (5 phases, 71-75)*
