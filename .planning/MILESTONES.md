# Milestones

## v13.0 Authentication & Connections Hardening (Shipped: 2026-05-09)

**Phases completed:** 8 phases (101-108), 18 plans, ~50 atomic commits
**Timeline:** 2 days (2026-05-08 → 2026-05-09)
**Tests added:** 207 unit tests in `tests/unit/social/`; `app/social/` line coverage 83.42% (gate: 80% via `make test-social`)

**Delivered:** OAuth security hardening, the Google Workspace credential bridge, and end-to-end posting fixes across 8 social platforms. End-users can now safely authenticate their accounts so agents can act on their behalf.

**Key accomplishments:**
1. Security hardening for `connected_accounts`: RLS scoped by `auth.uid()`, Fernet-encrypted tokens (with one-time backfill script), Postgres-backed PKCE persistence (`oauth_pkce_states` table), per-provider `platform_user_id`/`platform_username` capture, async refresh with per-(user, platform) `asyncio.Lock` (Phase 101)
2. Google Workspace credential bridge: `google_workspace` in PROVIDER_REGISTRY; `context_memory_before_model_callback` injects creds via `GoogleWorkspaceAuthService.resolve_credentials()` — closes the "9 readers, 0 writers" gap; sync `refresh_if_expiring` helper wired into 7 tool helpers (docs/gmail/sheets/calendar/forms/inbox/briefing); disconnect revokes at Google before deleting local row; in-app Connect/Disconnect card on configuration page (Phase 102)
3. LinkedIn posting end-to-end: member URN captured via `/v2/userinfo` `sub` claim; migrated `/v2/ugcPosts` (deprecated) → `/rest/posts` with `LinkedIn-Version: 202401`; image (3-step initialize-upload) + video (4-step) flows; webhook signature validation against `LINKEDIN_WEBHOOK_SECRET` (Phase 103)
4. Twitter v2 media upload migration: v1.1 sunset 2025-06-09; `media.write` scope added; image simple upload + video chunked INIT→APPEND→FINALIZE→STATUS poll (honors `check_after_secs`, 600s cap); reconnect SQL migration for existing accounts (Phase 104)
5. YouTube resumable upload: two-step `uploadType=resumable` protocol (POST → Location → PUT bytes); 16-reason structured error map (replaces fictional `source_url` JSON) (Phase 105)
6. TikTok publish completion: async polling of `/v2/post/publish/status/fetch/` until `PUBLISH_COMPLETE` or terminal failure (5s cadence, 5min cap); returns real `video_id`; bonus `/content/init/` → `/video/init/` URL fix (Phase 106)
7. Facebook video resumable upload: three-phase Graph API (`upload_phase=start` → `transfer` chunks → `finish`) with retry-once on 5xx; Page-token capture at OAuth callback via `GET /me/accounts` with auto-select-first; API version bumped v18.0 → v23.0 (Phase 107)
8. Hygiene & coverage: Threads (Meta App via Facebook OAuth) and Pinterest (separate OAuth, `/v5/pins`) added; ContentAgent has direct `SOCIAL_TOOLS` access (no skill-bridge indirection); `disconnect_account` POSTs to provider revoke endpoint BEFORE deleting local row across the matrix (LinkedIn, Twitter, Google, TikTok, Meta `DELETE /me/permissions`); 161-test coverage backfill (Phase 108)

**Architectural decisions:**
- Postgres-backed PKCE (not Redis) per the manual prep commit `861a2bc9` — simpler than dual-store and durable across Cloud Run scaling
- Hybrid sync `refresh_if_expiring` (Phase 102) instead of literal async `IntegrationManager.get_valid_token` per WORKSPACE-04's wording — locked in 102-CONTEXT.md
- Twitter v2 media upload (not OAuth1.0a) — keeps the existing OAuth2 PKCE flow intact

**Known follow-ups:**
- Twitter `>100MB` videos: log warning, in-memory only; tempfile fallback queued as future perf phase
- Facebook Page-selection UI for multi-Page accounts (auto-select for now; full pages list in `metadata.available_pages`)
- Threads revoke endpoint MEDIUM confidence (`graph.threads.net/v1.0/me/permissions`) — verify with live account
- Pinterest revoke skipped (no API endpoint per Pinterest docs)

**Archive:** [ROADMAP](ROADMAP.md) (v13.0 section) | [REQUIREMENTS](REQUIREMENTS.md) (v13.0 section) | PR [#21](https://github.com/Mrjoel97/PIKAR-AI/pull/21) | merge commit `f83a2bec`

---

## v10.0 Platform Hardening & Quality (Shipped: 2026-05-01)

**Phases completed:** 14 phases (76-89), 27 plans
**Timeline:** 6 days (2026-04-26 -> 2026-05-01)

**Delivered:** Platform hardening across security, performance, architecture resilience, and agent quality, followed by a production hotfix sweep for uploads, voice, SSE stability, document generation, chat persistence, and Knowledge Vault auto-sync.

**Key accomplishments:**
1. Security, performance, and architecture hardening across phases 76-80, including webhook secret enforcement, native async tool conversion, batch-write performance fixes, circuit-breaker/rate-limit resilience, and OpenAPI-to-TypeScript codegen
2. Agent quality fixes across phases 81-82, including Sales/HR/Operations/Customer Support config corrections and Admin agent decomposition into focused sub-agents with canonical shared knowledge tooling
3. Production hotfix closure across phases 83-89, including chat upload bypass, voice deadlock recovery, SSE timeout extension, document-generation tool exposure, browser mic dictation, multi-session chat persistence, and automatic Knowledge Vault ingest for generated artifacts

**Archive:** [ROADMAP](milestones/v10.0-ROADMAP.md) | [REQUIREMENTS](milestones/v10.0-REQUIREMENTS.md) | [AUDIT](milestones/v10.0-MILESTONE-AUDIT.md)

---

## v8.0 Agent Ecosystem Enhancement (Shipped: 2026-04-13)

**Phases completed:** 14 phases (57-70), 48 plans
**Timeline:** 4 days (2026-04-10 → 2026-04-13)

**Delivered:** Full agent-ecosystem enhancement across proactive alerts, non-technical UX, cross-agent synthesis, and the remaining specialist-agent gaps, plus degraded-tool cleanup across the platform.

**Key accomplishments:**
1. Proactive intelligence foundations with daily briefings, anomaly detection, competitor monitoring, and integration/budget alerts (Phases 57-59)
2. Financial, content, sales, and marketing agent enhancement with real forecasting, auto-scheduling, CRM tooling, campaign attribution, and campaign guidance (Phases 60-63)
3. Operations, HR, compliance, and customer support upgrades with SOP tooling, hiring funnel support, compliance workflows, and customer health automation (Phases 64-67)
4. Data and admin/research enhancements with NL analytics, weekly reporting, cohort analysis, self-diagnosis, persona-aware research, and monitoring subscriptions (Phases 68-69)
5. Degraded tool cleanup that replaced or retired the remaining placeholder tools, closing the milestone with zero degraded-module carryover (Phase 70)

**Archive:** [ROADMAP](milestones/v8.0-ROADMAP-DRAFT.md) | [REQUIREMENTS](milestones/v8.0-REQUIREMENTS-DRAFT.md)

---

## v9.0 Self-Evolution Hardening (Shipped: 2026-04-12)

**Phases completed:** 5 phases (71-75), 13 plans
**Timeline:** 1 day (2026-04-12)
**Tests added:** 129

**Delivered:** Complete AI self-improvement governance stack — async engine, persistent skill versions, user feedback loop from thumbs-up/down to effectiveness scores, scheduled daily improvement cycle with risk-tiered execution, admin approval queue, governance audit logging, and regression circuit breaker.

**Key accomplishments:**
1. Async Gemini client + event bus await fix + telemetry instrumentation — event loop no longer blocks during SSE chat streams (Phase 71)
2. Skill version persistence with unique partial index — refinements survive Cloud Run cold starts, version chain with rollback, startup hydration (Phase 72)
3. Feedback loop backend — fixed InteractionLogger kwargs crash, added POST /interactions/{id}/feedback, SSE interaction_id emission with task_completed inference (Phase 73)
4. Feedback loop frontend — MessageFeedback thumbs-up/down component with optimistic UI, SSE interaction_id capture, full closed-loop verification (Phase 74)
5. Scheduled improvement cycle — daily POST trigger with X-Scheduler-Secret, risk-tiered auto_execute (safe actions run immediately, dangerous ones queue), admin approve/reject, governance audit logging, circuit breaker auto-disables after 2 consecutive regressions (Phase 75)

**Archive:** [ROADMAP](milestones/v9.0-ROADMAP.md) | [REQUIREMENTS](milestones/v9.0-REQUIREMENTS.md)

---

## v7.0 Production Readiness & Beta Launch (Shipped: 2026-04-12)

**Phases completed:** 9 phases (49-56 + 53.1), 33 plans
**Timeline:** 5 days (2026-04-07 → 2026-04-11)

**Delivered:** Production-grade security, billing, observability, multi-tenancy, onboarding, and compliance — the full stack needed for beta launch with real users and real payments.

**Key accomplishments:**
1. Server-side auth hardening with JWKS validation, Next.js proxy route enforcement, AuditLogMiddleware with 34-entry allow-list (Phase 49)
2. Stripe billing with webhook idempotency ledger, subscription lifecycle, metered usage reporting (Phase 50)
3. Observability dashboard with agent latency percentiles, error rates, AI cost tracking, Sentry SDK integration (Phase 51)
4. Persona-based feature gating with tier enforcement, workspace-scoped permissions (Phase 52)
5. Multi-user teams with invite flow, RBAC, workspace isolation, team billing (Phase 53 + 53.1)
6. Onboarding wizard with Google Workspace OAuth, guided setup, progressive disclosure (Phase 54)
7. Integration quality with contract tests, load testing baselines, error budget monitoring (Phase 55)
8. GDPR compliance with data export/deletion, consent management, RAG evaluation contracts (Phase 56)

**Archive:** [ROADMAP](milestones/v7.0-ROADMAP.md) | [REQUIREMENTS](milestones/v7.0-REQUIREMENTS.md)

---

## v6.0 Real-World Integration & Solopreneur Unlock (Shipped: 2026-04-06)

**Phases completed:** 11 phases, 34 plans, 4 tasks

**Key accomplishments:**
- (none recorded)

---

## v2.0 Broader App Builder (Shipped: 2026-03-23)

**Phases completed:** 7 phases (16-22), 19 plans
**Timeline:** 3 days (2026-03-21 → 2026-03-23)
**New code:** ~14,900 Python + ~1,800 TypeScript

**Delivered:** GSD-powered creative workflow that takes users from a vague app idea through AI design research, screen generation with variant comparison, iterative editing with version control, multi-page assembly, and export to React/TypeScript, PWA, Capacitor, and walkthrough video.

**Key accomplishments:**
1. Stitch MCP singleton integration — persistent Node.js subprocess managing design-to-code with prompt enhancement and Supabase asset persistence
2. 7-stage GSD creative workflow — questioning → research → brief → building → verifying → shipping → done with approval checkpoints
3. AI design research — competitor analysis via Tavily, design system generation, sitemap/build plan creation
4. Multi-variant screen generation — 2-3 variants per screen via Stitch MCP, side-by-side comparison, device-specific layouts, version history with rollback
5. Baton-loop multi-page builder — autonomous multi-page generation with auto-nav injection, shared design system, page reordering
6. Ship pipeline — HTML-to-React (Gemini Flash), PWA generator, Capacitor scaffold, Remotion walkthrough video, SSE progress streaming

**Known Gaps (deferred to Phase 23):**
- FOUN-06: One-click deploy to public URL
- BLDR-01: Builder dashboard with project status/resume
- BLDR-03: One-click deploy button

**Archive:** [ROADMAP](milestones/v2.0-ROADMAP.md) | [REQUIREMENTS](milestones/v2.0-REQUIREMENTS.md) | [AUDIT](milestones/v2.0-MILESTONE-AUDIT.md)

---

