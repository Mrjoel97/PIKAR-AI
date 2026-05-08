# Project: pikar-ai

## What This Is

A multi-agent AI executive system ("Chief of Staff") built on Google ADK that orchestrates 10 specialized agents through a central ExecutiveAgent. It empowers non-technical users to transform business ideas into operational ventures via intelligent agent-led workflows — including an AI-powered app builder that takes users from a vague idea to a deployable web/mobile app through a guided creative workflow. Frontend is Next.js 16 with React 19, backend is FastAPI/Supabase.

## Core Value

Users describe what they want in natural language and the system autonomously generates, manages, and grows their business operations — now including building the digital assets (landing pages, web apps, mobile apps) they need through a GSD-style creative workflow.

## Current Milestone: v12.0 Agent System Quality Upgrade

**Goal:** Convert the multi-agent system from "single-shot chat agents" into "30-60 minute capable executive operators with persistent memory and tangible deliverables" — eliminating drift between prompts/registries, universalizing the artifact pipeline, deploying long-task infrastructure, generative research, and cross-agent memory.

**Target features:**
- Phase A (95) — Bug-Fix Sprint: 10 critical production bugs (ghost tools, image-path async I/O, agent escalation impossibility, ResearchAgent corruption)
- Phase B (96) — Single-Source Truth: AgentManifest, prompt/registry auto-generation, dead-code deletion, typed PDF schemas
- Phase C (97) — Tangible Outputs: Universal artifact pipeline (docs/sheets/approvals/markdown/briefings → widgets → Vault), bidirectional chat ↔ Vault deep-links
- Phase D (98) — 30-60min Capable: Job-decoupled SSE, deployed WorkflowWorker, summarizer enabled, progress events
- Phase E (99) — Generative Research: Parallel queries, LLM synthesis, follow-up hops, specialist quick_research, real confidence grading
- Phase F (100) — Cross-Agent Memory: Per-agent memory table, structured handoff envelopes, sub-sub-agent callback audit

**Provenance:** Requirements derived from a 4-investigator parallel audit (2026-05-08) covering agent prompts, tool inventory health, inter-agent comms + long-running tasks + memory, and output delivery + UX. ~400 file:line citations across the four investigator reports.

## Queued Milestone: v13.0 Authentication & Connections Hardening

**Goal:** Fix the OAuth, token storage, and posting layer for social media + Google Workspace so end-users can authenticate their accounts safely and agents can act on their behalf.

**Target features:**
- Phase 101 — Security Hardening for `connected_accounts` (RLS scoped by `auth.uid()`, Fernet-encrypted tokens, Redis-backed PKCE state, capture `platform_user_id` in OAuth callback, async refresh path)
- Phase 102 — Google Workspace Credential Bridge (`google_workspace` in PROVIDER_REGISTRY, context_extractor injection, IntegrationManager refresh integration, frontend Connect card, env vars + startup validation)
- Phase 103 — LinkedIn Posting Fix (capture member URN at OAuth callback, migrate `/v2/ugcPosts` → `/rest/posts`, validate webhook signatures)
- Phase 104 — Twitter Media Upload Fix (full INIT → APPEND → FINALIZE → STATUS chunked flow; drop fictional `source_url` parameter)
- Phase 105 — YouTube Resumable Upload (proper resumable upload protocol; replace JSON `source_url`)
- Phase 106 — TikTok Publish Completion (poll `/v2/post/publish/status/fetch/` after init; return real video ID)
- Phase 107 — Facebook Video Resumable Upload (`upload_phase=start` → transfer → finish)
- Phase 108 — Hygiene & Coverage (Threads + Pinterest support, Content agent direct social tool wiring, mock-based test coverage, disconnect-and-revoke at provider)

**Provenance:** Requirements derived from a deep audit (2026-05-08) of `app/social/connector.py`, `app/social/publisher.py`, `app/services/google_workspace_auth_service.py`, `app/agents/tools/{docs,gmail,google_sheets,calendar_tool,forms,gmail_inbox,briefing_tools}.py`, `app/agents/context_extractor.py`, `app/config/integration_providers.py`, `supabase/migrations/0010_connected_accounts.sql`. Verified findings include: RLS `USING (true)` on `connected_accounts`, plaintext `access_token`/`refresh_token` columns, in-memory PKCE verifier dict, hardcoded `urn:li:person:PERSON_ID` in LinkedIn payload, INIT-only Twitter media upload with fictional `source_url`, zero writers to `tool_context.state["google_provider_token"]` despite 9 readers.

**Sequencing:** v13.0 follows v12.0 (Agent System Quality Upgrade). v11.0 App Builder Beta further deferred from v13.0 → v14.0 to make room for security-urgent auth work.

## Deferred Milestone: v11.0 App Builder Beta

**Status:** Phases 90-94 declared with goals + success criteria but no plans written. Deferred to v14.0 (was v13.0; pushed back to make room for v13.0 Authentication & Connections Hardening). v11.0 phases (Onboarding, Dashboard, Hosted Preview, Forms+Hardening, UAT) remain documented in `.planning/ROADMAP.md` and `.planning/v11.0-PROJECT-CONTEXT.md` for resumption in v14.0.

## Current State

**Latest shipped:** v10.0 Platform Hardening & Quality (2026-05-01) — 14 phases, 27 plans
**Currently deferred:** v11.0 App Builder Beta — phases 90-94 declared, plans not written, deferred to v14.0
**Active:** v12.0 Agent System Quality Upgrade — derived from 2026-05-08 audit; 6 phases (95-100) covering bug fixes, registry consolidation, artifact universalization, long-task infra, generative research, cross-agent memory
**Queued next:** v13.0 Authentication & Connections Hardening — derived from 2026-05-08 social/Google Workspace audit; 8 phases (101-108) covering OAuth security, Google Workspace bridge, per-platform posting fixes, hygiene

Platform is feature-complete through v10.0 with 13 specialized agents, 80+ tool modules, and full production infrastructure. Two parallel 2026-05-08 audits identified two distinct systemic gaps: (a) agent system quality (drifted sources of truth, half-built artifact pipelines, half-disabled long-task infra, mechanical research) addressed in v12.0; (b) authentication and posting layer (broken RLS, plaintext tokens, missing Google Workspace credential bridge, broken per-platform posting) addressed in v13.0.

**Key philosophy established:** Solopreneur is NOT a limited tier — full access to all non-team features. Team features use workspace-based access control with admin/member roles.

## Requirements

### Validated

- ✓ Workflow execution standardization — v1.0
- ✓ Redis circuit breakers for cache lookups — v1.0
- ✓ Deterministic argument mapping for workflow tools — v1.0
- ✓ Database schema alignment with codebase — v1.1
- ✓ Async event-loop safety across all services — v1.1
- ✓ Frontend-backend API and type alignment — v1.1
- ✓ Security headers and production hardening — v1.1
- ✓ Configuration system unification — v1.1
- ✓ Stitch MCP singleton integration with DB schema and asset persistence — v2.0
- ✓ GSD creative workflow engine (7-stage guided flow) — v2.0
- ✓ Creative questioning and design research — v2.0
- ✓ Design brief with user-approved design system — v2.0
- ✓ Screen variant generation and side-by-side preview — v2.0
- ✓ Iteration loop with version history and rollback — v2.0
- ✓ Multi-page builder with baton-loop pattern — v2.0
- ✓ React/TypeScript conversion pipeline — v2.0
- ✓ Output targets (PWA, Capacitor, Remotion video) — v2.0
- ✓ Ship pipeline with SSE progress streaming — v2.0
- ✓ Solopreneur full-featured unlock (7 features, no team-gating) — v6.0
- ✓ Tool honesty rename (16 misleading tools renamed) — v6.0
- ✓ Integration infrastructure (OAuth, webhooks, credential storage, sync state) — v6.0
- ✓ Data I/O (CSV import/export) and document generation (PDF, PPTX) — v6.0
- ✓ Financial integrations (Stripe revenue sync, Shopify e-commerce) — v6.0
- ✓ CRM bidirectional sync (HubSpot contacts + deals) and email sequences — v6.0
- ✓ Ad platform integration (Google Ads + Meta Ads with approval gates) — v6.0
- ✓ Project management integration (Linear + Asana bidirectional sync) — v6.0
- ✓ Communication & notifications (Slack + Teams with rich formatting) — v6.0
- ✓ External database queries (PostgreSQL + BigQuery NL-to-SQL) — v6.0
- ✓ Calendar intelligence (free/busy, meeting prep, follow-up suggestions) — v6.0
- ✓ Continuous intelligence (scheduled monitoring, knowledge graph, alerts) — v6.0
- ✓ Team collaboration (shared work, role-based visibility, activity feed) — v6.0
- ✓ Outbound webhooks (Zapier-compatible, event catalog, delivery logs) — v6.0

### Recently Completed

**v8.0 Agent Ecosystem Enhancement:**
- [x] Proactive intelligence layer (push notifications, anomaly, competitor, integration, and budget alerts)
- [x] Non-technical UX (suggestion chips, intent clarification, mobile-first summaries, guided workflows)
- [x] Cross-agent synthesis and unified action history
- [x] Financial, content, sales, marketing, operations, HR, compliance, customer support, data, and admin/research enhancement phases
- [x] Degraded tool replacement and cleanup

**v9.0 Self-Evolution Hardening:**
- [x] Persistent skill refinements
- [x] Closed feedback loop from chat interaction to effectiveness signal
- [x] Scheduled improvement cycle with approval queue and circuit breaker
- [x] Runtime fixes for the self-improvement path

**Deferred from v2.0 (Phase 23, not yet planned):**
- [ ] Builder dashboard with project status and resume capability
- [ ] One-click deploy to public URL

### Out of Scope

- Multi-tenant admin (multiple admin teams) — founder-only for now, expandable later
- Real-time WebSocket monitoring — SSE/polling sufficient for admin use
- Custom admin theming — uses existing app design system
- Admin mobile app — desktop-first admin panel
- Native iOS/Android development (Swift/Kotlin) — Capacitor hybrid covers mobile
- Backend/server-side code generation — UI/frontend generation only
- E-commerce checkout flows — beyond UI generation scope

## Context

- 10 specialized ADK agents (financial, content, strategic, sales, marketing, operations, HR, compliance, support, data)
- Frontend: Next.js 16, React 19, Tailwind CSS 4, Supabase auth, fetchEventSource SSE chat
- Backend: FastAPI, Google ADK, Gemini models with Pro→Flash fallback, Redis with circuit breaker
- App Builder: Stitch MCP singleton (Node.js subprocess), 15+ API routes, SSE streaming for build/ship, ~14,900 LOC Python + ~1,800 LOC TypeScript
- Existing chat uses `useAgentChat` hook with `@microsoft/fetch-event-source` — admin chat follows same pattern
- Existing health endpoints: /health/live, /health/connections, /health/cache, /health/embeddings, /health/video
- Persona-based routing (solopreneur/startup/sme/enterprise) with workspace RBAC (admin/member roles)
- 10 live external integrations: HubSpot, Stripe, Shopify, Google Ads, Meta Ads, Linear, Asana, Slack, Teams, external databases (PostgreSQL/BigQuery)
- Outbound webhook system with Zapier-compatible envelope, 9 event types, delivery retry + circuit breaker
- ResearchAgent with multi-track research, knowledge graph, and scheduled monitoring jobs
- slowapi rate limiting already in use across routers
- Full design spec: `docs/superpowers/specs/2026-03-21-admin-panel-design.md`

## Constraints

- **Existing Infra**: Must use existing patterns (ADK agents, fetchEventSource SSE, Supabase migrations, Cloud Scheduler)
- **Python AI**: Admin agent must be a Google ADK agent on FastAPI (not a separate Node.js AI SDK setup)
- **Schema Extension**: Add new admin tables via Supabase migrations, do not modify existing tables
- **Security**: API keys encrypted with Fernet, admin emails never exposed in client bundle
- **Backward Compat**: Admin panel must not affect existing user-facing routes or functionality

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Supabase migrations are source of truth (not Alembic) | Supabase has 96 migrations vs 1 stale Alembic file | ✓ Good |
| AI-first admin (chat-centered, not dashboard-centered) | Solo founder efficiency — one interface for all admin domains | ✓ Good |
| Google ADK AdminAgent (not Vercel AI SDK) | Consistent with existing chat infra, direct backend service access | ✓ Good |
| Two-layer auth (env allowlist + DB roles) | Bootstrap via env, transition to DB, OR logic for flexibility | ✓ Good |
| Fernet-encrypted credential storage with async-locked token refresh | Security + concurrent request safety for OAuth integrations | ✓ Good |
| Outbound webhook Zapier-compatible envelope | Standard {id, event, api_version, timestamp, data} enables catch-hook compatibility | ✓ Good |
| Smart auto-execute for external DB queries | Simple SELECTs run immediately, complex queries need confirmation | ✓ Good |
| Importance-based monitoring schedule (critical/normal/low) | Simpler mental model than cron expressions for solopreneurs | ✓ Good |
| Team-visible by default sharing model | Consistent with workspace-scoped queries, no new sharing columns needed | ✓ Good |
| Suggest-only follow-up scheduling (not auto-book) | User stays in control of calendar changes | ✓ Good |
| Fernet encryption for integration API keys | Application-layer encryption, key in env/Secret Manager, supports rotation | ✓ Good |
| Cloud Scheduler for health monitoring loop | Consistent with existing scheduled_endpoints.py pattern | ✓ Good |
| Server-side admin email check (not NEXT_PUBLIC_) | Prevents leaking admin identities in client bundle | ✓ Good |
| is_admin() SECURITY DEFINER function | Avoids circular self-referencing RLS on user_roles table | ✓ Good |
| Individual message rows (not JSONB blob) | Avoids write amplification, enables partial loading/querying | ✓ Good |
| Stitch MCP over REST API | MCP provides richer tools (edit_screens, project management) and follows stitch-skills standard | ✓ Good |
| GSD-style creative workflow | Guided discovery → brief → build → verify, not just "prompt → generate" — differentiates from v0/Bolt/Lovable | ✓ Good |
| User screen preview before creation | Creative control — preview variants, iterate, then finalize | ✓ Good |
| Capacitor for hybrid mobile | Native-like mobile from React output without requiring native dev skills | ✓ Good |
| Design system persistence per project | Visual consistency across multi-page apps, follows stitch-skills DESIGN.md pattern | ✓ Good |
| Prompt enhancer for screen generation | Gemini transforms vague user input into Stitch-optimized prompts with domain vocabulary | ✓ Good |
| Self-contained npm version resolution per generator | Avoids cross-service imports in parallel wave execution | ✓ Good |

| Solopreneur = full-featured single-user | Solopreneur locked out of workflows was wrong — they need automation most | — Pending |
| Real integrations over knowledge wrappers | Tools named after actions must perform those actions, or be renamed | — Pending |
| v9.0 runs in parallel with v8.0 execution | v8.0 agent-enhancement phases were long-running; self-improvement hardening ran independently and both milestones shipped successfully | ✓ Good |
| Feedback loop is the load-bearing gap, not the engine | The engine is already implemented — what's missing is the data channel. Fix the channel first, then the engine becomes useful without touching its logic | — Pending |
| Skill refinements persisted as versioned history, not mutation | A `skill_versions` table preserves provenance, enables meaningful revert, and survives Cloud Run cold starts — in-memory mutation fails on both | — Pending |
| Auto-execute gated by action risk tier | `skill_demoted` and `pattern_extract` are reversible/low-stakes; `skill_created` and `skill_refined` require admin approval because they touch user-visible agent behavior | — Pending |

---
*Last updated: 2026-05-08 after queuing v13.0 Authentication & Connections Hardening milestone (8 phases 101-108; v11.0 pushed to v14.0)*
