# Requirements: pikar-ai

**Active milestone:** v12.0 Agent System Quality Upgrade
**Queued milestone:** v13.0 Authentication & Connections Hardening
**Defined:** 2026-04-26 (v10.0); 2026-05-01 (v11.0); 2026-05-08 (v12.0 + v13.0)
**Core Value:** Users describe what they want in natural language and the system autonomously generates, manages, and grows their business operations

## v13.0 Requirements (Authentication & Connections Hardening)

Requirements derived from a deep audit (2026-05-08) of the social media OAuth/posting layer and the Google Workspace credential plumbing. Goal: end-users can safely authenticate their accounts so agents can act on their behalf — fixing four systemic gaps surfaced by file:line evidence: (1) `connected_accounts` RLS policy is `USING (true)`, granting any authenticated user read access to every user's tokens; (2) OAuth tokens stored in plaintext, unlike `integration_credentials` which uses Fernet; (3) `tool_context.state["google_provider_token"]` is read by 9 tool files but written by 0 — Google Workspace works only via the legacy Supabase Auth Google identity provider, not the per-integration OAuth model; (4) per-platform posting code contains placeholder values (`urn:li:person:PERSON_ID`), missing API steps (Twitter chunked upload INIT-only, TikTok no status poll), and wrong protocols (YouTube JSON instead of resumable, Facebook `file_url` instead of upload phases).

### Security Hardening (Phase 101)

Stop the bleeding on `connected_accounts` before any user is told their tokens are safe.

- [ ] **AUTH-01**: `connected_accounts` row-level security policy enforces `auth.uid()::text = user_id` for both `USING` and `WITH CHECK` (replaces current permissive `USING (true)`)
- [ ] **AUTH-02**: `connected_accounts.access_token` and `refresh_token` stored Fernet-encrypted at rest; `connector.py` writes through `encrypt_secret()` and reads through `decrypt_secret()` (mirrors `integration_credentials` pattern)
- [ ] **AUTH-03**: PKCE code verifiers persisted in Redis with 10-minute TTL keyed by state token; survive Cloud Run container recycles and horizontal scaling (replaces in-memory `_pkce_verifiers` dict)
- [x] **AUTH-04**: OAuth callback captures `platform_user_id` and `platform_username` from each provider's profile endpoint and persists alongside the token row (unblocks LinkedIn URN, enables per-platform identity lookups) — shipped 2026-05-09 (commits 195fe3a6 + 1e02f6bb on feat/vault-fixes-and-agent-actions)
- [ ] **AUTH-05**: Token refresh path uses `httpx.AsyncClient`; does not block the event loop when called from async tools

### Google Workspace Credential Bridge (Phase 102)

The single highest-leverage fix in the milestone — wires nine existing tools to the existing per-user credential store.

- [ ] **WORKSPACE-01**: User can connect their Google Workspace account via an in-app "Connect Google Workspace" card on the configuration page (popup OAuth flow with `postMessage` callback)
- [ ] **WORKSPACE-02**: `PROVIDER_REGISTRY` includes a `google_workspace` entry with scopes for Docs, Sheets, Drive (file), Gmail (send), Calendar, Forms, and `userinfo.email`; uses `GOOGLE_WORKSPACE_CLIENT_ID`/`SECRET` env vars
- [ ] **WORKSPACE-03**: Agent context extractor (`context_memory_before_model_callback` in `app/agents/context_extractor.py`) injects the requesting user's Google Workspace credentials into `tool_context.state["google_provider_token"]` and `["google_refresh_token"]` before tool execution by calling `GoogleWorkspaceAuthService.resolve_credentials()`
- [ ] **WORKSPACE-04**: Each Google Workspace tool helper (`_get_docs_service`, `_get_gmail_service`, `_get_sheets_service`, `_get_calendar_service`, `_get_forms_service`, etc.) calls `IntegrationManager.get_valid_token(user_id, "google_workspace")` to auto-refresh tokens within 5 minutes of expiry
- [ ] **WORKSPACE-05**: Disconnecting a Google Workspace account revokes the token at Google (POST to `https://oauth2.googleapis.com/revoke`) and clears the local `integration_credentials` row
- [ ] **WORKSPACE-06**: `.env.example` documents `GOOGLE_WORKSPACE_CLIENT_ID`, `GOOGLE_WORKSPACE_CLIENT_SECRET`, `GOOGLE_WORKSPACE_REDIRECT_URI`; startup validation logs a warning when missing in non-test environments

### LinkedIn Posting Fix (Phase 103)

- [ ] **POST-01**: LinkedIn OAuth callback fetches the member's URN from `/v2/userinfo` (`sub` claim) and stores it as `platform_user_id`; publisher uses `urn:li:person:{platform_user_id}` as the post `author` (replaces literal `urn:li:person:PERSON_ID` placeholder)
- [ ] **POST-02**: LinkedIn posting migrates from deprecated `/v2/ugcPosts` to `/rest/posts` with `LinkedIn-Version: 202401` header; supports text, single-image, and video posts
- [ ] **POST-03**: LinkedIn webhook signatures validated against `LINKEDIN_WEBHOOK_SECRET` on inbound events (env var already exists, never enforced)

### Twitter Media Upload Fix (Phase 104)

- [x] **POST-04**: Twitter image posts (≤5MB) use `POST media/upload` simple endpoint (single request); v1.1 `media_id` attached to v2 tweet via `media.media_ids`
- [ ] **POST-05**: Twitter video posts use full chunked upload (`INIT` → `APPEND` with binary chunks → `FINALIZE` → `STATUS` poll until `succeeded`) before tweet creation; the fictional `source_url` parameter is removed
- [x] **POST-06**: Twitter posting handles OAuth1.0a context if media upload (v1.1) requires it; alternatively documents the user-context auth requirement

### YouTube Resumable Upload (Phase 105)

- [ ] **POST-07**: YouTube video uploads use the resumable protocol — `POST /upload/youtube/v3/videos?uploadType=resumable&part=snippet,status` returns a session URL, then video bytes are PUT to that URL; replaces the JSON-only request with fictional `source_url`

### TikTok Publish Completion (Phase 106)

- [ ] **POST-08**: TikTok video posting polls `POST /v2/post/publish/status/fetch/` after `init/` returns `publish_id` until `status` is `PUBLISH_COMPLETE` or terminal failure; returns the resulting video ID to the caller (init-only flow no longer reports false success)

### Facebook Video Resumable Upload (Phase 107)

- [ ] **POST-09**: Facebook video uploads use the Graph API resumable protocol (`upload_phase=start` to get session ID + chunk size, `upload_phase=transfer` for chunks, `upload_phase=finish` to publish); replaces the broken `file_url` JSON request

### Hygiene & Coverage (Phase 108)

- [ ] **HYGIENE-01**: User can connect Threads accounts and the Marketing agent can post text/image to Threads (Meta Threads API; shares Facebook OAuth)
- [ ] **HYGIENE-02**: User can connect Pinterest accounts (separate OAuth client) and the Marketing agent can post pins
- [ ] **HYGIENE-03**: ContentAgent has direct access to `SOCIAL_TOOLS` (no skill-bridge indirection); LLM can post drafted content to social without delegating to a sub-agent
- [ ] **HYGIENE-04**: Mock-based unit tests cover `connector.handle_callback` per platform (state/PKCE round-trip, `platform_user_id` capture) and `publisher.post_with_media` request shape per platform; minimum 80% line coverage on `app/social/`

## v12.0 Requirements (Agent System Quality Upgrade)

Requirements derived from a 4-investigator parallel audit of the multi-agent system on 2026-05-08. Goal: convert the system from "single-shot chat agents" into "30-60 minute capable executive operators with persistent memory and tangible deliverables." The audit identified 4 systemic patterns: (1) drifted sources of truth, (2) one complete artifact pipeline (media) with everything else half-built, (3) long-task infrastructure half-exists/half-disabled, (4) research is mechanical where it should be generative.

### Bug-Fix Sprint (Phase 95 / Phase A)

10 critical bugs identified by the audit that affect production today. Each is a small, scoped fix.

- [ ] **QUALITY-01**: Image generation does not block the event loop — `app/agents/tools/media.py:455-496` Supabase storage upload + `media_assets.insert().execute()` wrapped in `asyncio.to_thread` (matches video-path fix from Phase 89)
- [ ] **QUALITY-02**: Executive Agent prompt advertises only tools it actually owns — `app/prompts/executive_instruction.txt` line 8 (`get_revenue_stats`) and lines 146-150 (5 landing-page tools) removed and replaced with delegation rules
- [ ] **QUALITY-03**: User can route data-reporting requests to `DataReportingAgent` — agent wired into `app/agents/specialized_agents.py:71-83` and added to Executive routing table in `executive_instruction.txt`
- [ ] **QUALITY-04**: Marketing campaign wizard hand-off completes successfully — `app/agents/marketing/agent.py:215` "escalate to parent" instruction replaced with structured handoff envelope OR `CampaignAgent` granted direct `AD_PLATFORM_TOOLS`
- [ ] **QUALITY-05**: ResearchAgent retains context across multi-turn sessions — `*CONTEXT_MEMORY_TOOLS` + `before_model_callback` + after-tool callback added; broken `SELF_IMPROVEMENT_INSTRUCTIONS` block removed from `app/agents/research/instructions.py`
- [ ] **QUALITY-06**: Customer support metrics render as widgets — `create_stat_widget` reference at `app/agents/customer_support/agent.py:80` either replaced with `create_table_widget` or the function added to `ui_widgets.py`
- [ ] **QUALITY-07**: Marketing routing decisions are deterministic — `MarketingAutomationAgent` switched from `CREATIVE_AGENT_CONFIG` (T=0.7) to `ROUTING_AGENT_CONFIG` (T=0.2)
- [ ] **QUALITY-08**: `DataReportingAgent` operates with controlled temperature — `generate_content_config=DEEP_AGENT_CONFIG` added at `app/agents/reporting/agent.py:203` and `:250`
- [ ] **QUALITY-09**: System emails use organization-wide configuration — `app/mcp/config.py:52` hardcoded personal email replaced with `RESEND_FORWARD_TO` env var
- [ ] **QUALITY-10**: Untrusted code paths cannot be executed via tools — `integration_tools.py:466 run_script` and `:534 update_code` either deleted (no agent registers them) or gated behind feature flag + allowlist + path-traversal guard

### Single-Source Truth (Phase 96 / Phase B)

Eliminate the entire class of ghost-tool / hallucinated-delegation bugs forever by establishing one canonical place for each agent's capabilities.

- [ ] **REGISTRY-01**: Each agent has exactly one `AgentManifest` (Pydantic model) defining its name, model config, tool list, sub-agents, and prompt template — no parallel definitions in factory functions or registry files
- [ ] **REGISTRY-02**: Agent prompts auto-generate their "Available Tools" section from the manifest — manual prompt-tool drift becomes structurally impossible
- [ ] **REGISTRY-03**: Executive routing table auto-generates from the union of agent manifests — `executive_instruction.txt` AVAILABLE SPECIALISTS block sourced from manifests, not hand-edited
- [ ] **REGISTRY-04**: Legacy registries removed — `app/agents/tools/registry.py` (degraded-tool dispatcher with 40+ unused imports) and `app/agents/tools/document_generation.py` (superseded by `document_gen.py`) deleted from repo
- [ ] **REGISTRY-05**: Wrapper/duplicate tools removed — `instagram_post_image`, `generate_short_video`, `generate_short_videos` (single-line aliases for existing tools) deleted; agent instructions updated to call canonical functions
- [ ] **REGISTRY-06**: PDF generation has typed schemas per template — `generate_pdf_report(data: dict[str, Any])` at `app/agents/tools/document_gen.py:43` replaced with discriminated union of `TypedDict`s (one per template) so Gemini's tool-calling schema is concrete

### Tangible Outputs (Phase 97 / Phase C)

Extend the media-pipeline contract (storage → media_assets → knowledge_vault → chat_widgets → frontend → Vault) to every output type so every agent response becomes a real, perpetuable artifact.

- [ ] **ARTIFACT-01**: Google Docs created by agents render as document widgets in chat — `create_document` in `app/agents/tools/docs.py:106-113` returns a widget envelope with `type: "document"` (type already exists in `RENDERABLE_WIDGET_TYPES`); persisted via `_finalize_widget` to `chat_widgets`
- [ ] **ARTIFACT-02**: Google Sheets created by agents render as document widgets in chat — `create_spreadsheet` in `app/agents/tools/google_sheets.py` returns a widget envelope; persisted to `chat_widgets`; appears in Vault > Documents tab
- [ ] **ARTIFACT-03**: Approvals render as inline interactive cards — new `approval` widget type with `action_type`, `token`, `expiry`; `MessageItem.tsx` renders Approve/Reject buttons that POST to `/approvals/{token}/decision`
- [ ] **ARTIFACT-04**: Approval decisions resume the originating session — when user approves/rejects, the originating session is notified (Supabase realtime or polling); the agent's pending workflow continues automatically
- [ ] **ARTIFACT-05**: Long-form text agent outputs persist as artifacts when ≥200 chars — `LONGFORM_MIN_CHARS` lowered from 650 → 200 in `frontend/src/services/workspaceArtifacts.ts:7`
- [ ] **ARTIFACT-06**: Markdown report widgets persist server-side — `buildMarkdownWorkspaceWidget` logic moved from `useBackgroundStream.ts:688` (client-side) to `app/sse_utils.py` SSE post-processor; written via `persist_chat_widget` so survives auth-token staleness
- [ ] **ARTIFACT-07**: Briefings and weekly reports become downloadable artifacts — `/briefing/weekly-report` and Morning Briefing emit a PDF via `generate_pdf_report`, write to `media_assets`, and appear in Vault
- [ ] **ARTIFACT-08**: Chat messages link bidirectionally to their Vault entries — `media_assets.session_id` (already stored in metadata) is queried by `VaultInterface.tsx`; "View in chat" link in Vault, "Find in Vault" chip on chat widgets
- [ ] **ARTIFACT-09**: Every chat message has an explicit "Save to Vault" action — `MessageItem.tsx` adds a Save button that calls `WidgetDisplayService.saveWidget` + writes a `media_assets` row with `asset_type = "note"`
- [ ] **ARTIFACT-10**: Director storyboard captions render as a structured card — new `DirectorProgressCard` component renders scene-by-scene captions from `planning_done` event payload (`director_service.py:350`) instead of dumping raw JSON into the trace drawer

### 30-60min Capable (Phase 98 / Phase D)

Make 30-60 minute tasks first-class — survive disconnects, instance restarts, cold-starts, and proxy idle timeouts; show meaningful progress throughout.

- [ ] **LONGTASK-01**: Tasks expected to exceed 5 minutes run as durable jobs and survive client disconnect — long-running operations return a `job_id` immediately; SSE stream polls job progress events (uses existing `WorkflowWorker` ai_jobs queue)
- [ ] **LONGTASK-02**: `WorkflowWorker` runs as a deployed Cloud Run Job in production — currently a separate process invoked via `scripts/dev/run_worker.py` only; production deployment + Cloud Scheduler trigger added
- [ ] **LONGTASK-03**: Workflow worker uses async Supabase client — `app/workflows/worker.py:97-99,115-117,121-123,315-317` synchronous `.execute()` calls switched to `get_async_client()` so they don't block the event loop
- [ ] **LONGTASK-04**: Conversation summarizer is enabled in production — `ENABLE_CONVERSATION_SUMMARIZER=true`; summary injection at `app/persistence/supabase_session_service.py:448-462` active for all sessions
- [ ] **LONGTASK-05**: Session event window holds 200+ events with visible truncation banner — `SESSION_MAX_EVENTS` raised from 80 → 200; truncation event emitted into SSE stream so the frontend banner triggers
- [ ] **LONGTASK-06**: Vertex context cache TTL exceeds long-task duration — `ContextCacheConfig.ttl_seconds` raised from 600s → 3600s in `app/agent.py:435` so a 30-60 min session avoids 2-5 cache rebuilds
- [ ] **LONGTASK-07**: Interrupted-but-not-errored workflow steps resume on next worker poll — `reap_stale_jobs` in `app/workflows/worker.py:321` resets such steps to `pending` instead of marking them `failed`
- [ ] **LONGTASK-08**: Agent emits visible progress events at every tool-call boundary — `app/fast_api_app.py` event_generator pushes structured `data:` events (tool name, estimated duration) at tool start/end via existing `progress_queue`, so the UI never goes silent during multi-minute tool runs

### Generative Research (Phase 99 / Phase E)

Move research from mechanical (string-concat synthesis, hardcoded 3 queries) to generative (LLM reasoning, parallel execution, multi-hop branching).

- [ ] **RESEARCH-01**: Initial search queries execute in parallel — `app/agents/tools/deep_research.py:111` serial `await` loop replaced with `asyncio.gather`; up-front search latency drops from ~90s to ~30s
- [ ] **RESEARCH-02**: Research synthesis uses LLM reasoning — `_synthesize_findings` (currently string concatenation) replaced with a Gemini Flash call producing structured `(claim, evidence, source-id, contradicts)` tuples
- [ ] **RESEARCH-03**: Research can issue follow-up queries based on initial findings — after first synthesis, the model is prompted "what's missing? what questions does this raise?"; 1-3 additional queries fire; cap at 2 hops to bound cost
- [ ] **RESEARCH-04**: Specialist agents call research without round-trip through Executive — new `quick_research` tool (1 query, 3 scrapes, ~30s) registered to all specialist agents so research happens inside a specialist turn
- [ ] **RESEARCH-05**: Research output includes LLM-graded confidence — `confidence_score` in `deep_research.py:198` replaced with LLM grading on (source authority, recency, agreement-across-sources) instead of mechanical source-counting
- [ ] **RESEARCH-06**: Conflicting sources are surfaced explicitly in the research card — synthesis output flags contradictions; frontend rendering shows them as a distinct "conflicts" section instead of being buried in prose

### Cross-Agent Memory & Communication (Phase 100 / Phase F)

Convert agents from amnesiac specialists into operators-with-continuity by giving each its own persistent memory and structured handoff envelopes.

- [ ] **MEMORY-01**: Each agent has structured per-user memory persisted across sessions — new `agent_memory` table keyed by `(user_id, agent_name)` with structured facts (e.g., Sales agent remembers tracked deals; Financial remembers raised flags; Content remembers brand voice)
- [ ] **MEMORY-02**: Agent memory injects into prompts via shared callback — every agent's `before_model_callback` reads its own memory row and injects relevant facts into the prompt for the upcoming turn
- [ ] **MEMORY-03**: Agent-to-agent handoffs use a `HandoffPacket` envelope — when Executive routes to a specialist, intent + evidence + constraints + expected output shape are passed structurally instead of being re-derived from session state
- [ ] **MEMORY-04**: All sub-sub-agents register required memory callbacks — VideoDirector, GraphicDesigner, Copywriter, RiskReport, ConfigurationAgent, LeadScoring, etc. audited and confirmed to register `context_memory_before_model_callback` + after-tool callback (regression risk per `app/agents/content/agent.py:21-24` historical comment)

## v11.0 Requirements (App Builder Beta — DEFERRED to v14.0)

Phases 90-94 declared with goals + success criteria but plans never written. Originally deferred 2026-05-08 in favor of v12.0 agent quality work; further deferred from v13.0 → v14.0 on 2026-05-08 in favor of v13.0 Authentication & Connections Hardening (security-urgent OAuth/posting fixes). Resumes in v14.0.

Requirements for taking the app-builder generation engine to closed beta. Scope is **landing pages + multi-page brochure websites only**. Web app and mobile app capabilities deferred to v12.0+.

### Onboarding & Scope

- [ ] **BETA-01**: Questioning wizard step 1 offers only "Landing page" and "Multi-page website"; "Web app" / "Mobile app" removed or marked "Coming soon" disabled
- [ ] **BETA-02**: First-time user lands on `/app-builder/new` with a "Try a sample" CTA that creates a Coffee shop landing page seed project in <2s

### Project Management

- [ ] **BETA-03**: `/app-builder` dashboard lists all user projects with title, stage, last-updated, and thumbnail; loads <500ms warm
- [ ] **BETA-04**: Each project supports resume, re-download exports, and delete; deletion cleans Supabase storage + screens

### Hosted Publishing

- [ ] **BETA-05**: Ship completion creates `published_sites` row and serves the site at `pikar.app/sites/{slug}` from Supabase Storage via Cloud Run route
- [ ] **BETA-06**: HTTPS via Cloudflare wildcard or path-based cert; cold load <2s, warm <300ms, cache invalidated on re-ship within 30s
- [ ] **BETA-07**: Slug is user-editable post-ship with collision detection; re-shipping updates existing slug, does not create new

### Live Site Functionality

- [ ] **BETA-08**: Generated forms POST to `pikar.app/api/sites/{slug}/submit`; submissions land in `landing_form_submissions` table with rate limiting
- [ ] **BETA-09**: Project owner receives email notification within 60s of each submission; can view + CSV-export submissions from project dashboard

### Production Hardening

- [ ] **BETA-10**: End-to-end smoke test on deployed Cloud Run env; `STITCH_API_KEY` + `npx @_davideast/stitch-mcp` runtime verified; Stitch failures show user-facing status banners with plain-language copy

### Beta Acceptance

- [ ] **BETA-11**: ≥3 invited users complete the full flow without dropping out; top 5 UAT friction fixes shipped; beta-open checklist signed off

## v10.0 Requirements (shipped, archived)

See [milestones/v10.0-REQUIREMENTS.md](milestones/v10.0-REQUIREMENTS.md) for the canonical record.

Below is the v10.0 traceability for cross-reference; do not modify these IDs.

## v10.0 Requirements

Requirements for Platform Hardening & Quality milestone. Each maps to roadmap phases.

### Security

- [x] **SEC-01**: Webhook endpoints return HTTP 500 when signing secret is unconfigured instead of processing unauthenticated payloads (Linear, Asana)
- [x] **SEC-02**: Slack interact handler validates response_url against *.slack.com allowlist before issuing outbound POST (SSRF prevention)
- [x] **SEC-03**: resolve_request_user_id defaults allow_header_fallback=False; x-user-id header never used for authorization decisions
- [x] **SEC-04**: dompurify added as explicit frontend dependency with typeof window guard for SSR safety

### Performance

- [x] **PERF-01**: 20+ sync tool wrappers converted from ThreadPoolExecutor+asyncio.run to native async def with direct await
- [x] **PERF-02**: N+1 sequential writes in workflow engine resume, session rollback, and session fork replaced with batch operations
- [x] **PERF-03**: Analytics aggregator uses SQL COUNT(DISTINCT) or Supabase count aggregate instead of fetching full rows to count in Python
- [x] **PERF-04**: Tool cache uses bounded TTLCache with maxsize; Redis key namespace enforced via REDIS_KEY_PREFIXES constants; generic cache methods guard connection

### Architecture

- [x] **ARCH-01**: SupabaseSessionService methods wrapped with circuit breaker; retry set expanded to cover httpx.HTTPStatusError (5xx responses)
- [x] **ARCH-02**: Rate limiting falls back to in-process SlowAPI limiter when Redis circuit breaker opens; CRITICAL alert logged
- [x] **ARCH-03**: Workflow concurrent-execution check made atomic via Postgres advisory lock, DB constraint, or single INSERT...WHERE subquery
- [x] **ARCH-04**: OpenAPI-to-TypeScript codegen established in CI pipeline; manually maintained frontend types in services/*.ts replaced with generated types

### Agent Quality

- [x] **AGT-01**: Sales agent parent model upgraded from get_fast_model() (Flash) to get_model() (Pro) with DEEP_AGENT_CONFIG
- [x] **AGT-02**: Admin agent decomposed into 4-5 focused sub-agents (SystemHealth, UserManagement, Billing, Governance); context callbacks added
- [x] **AGT-03**: HR, Operations, and Customer Support agents upgraded from ROUTING_AGENT_CONFIG (max_output_tokens=1024) to DEEP_AGENT_CONFIG (max_output_tokens=4096)
- [x] **AGT-04**: Missing shared instruction blocks (escalation, skills registry, self-improvement) added to Sales, Operations, Compliance, Customer Support, Reporting, and Research agents
- [x] **AGT-05**: search_knowledge moved from app.agents.content.tools to app.agents.tools/knowledge.py; cross-agent tool duplication (blog pipeline, video generation, start_initiative_from_idea) resolved

## Hotfix Requirements

Production-bug requirements added after v10.0 milestone planning.

- [x] **HOTFIX-01** (Phase 83): Chat file attachment now uses the standard `attachedFiles` + `/api/upload` path directly; `/api/upload/smart` is no longer invoked from chat auto-attach flows, removing the indefinite "detecting content type" loading state while preserving inline extracted-content delivery and explicit failure messaging.
- [x] **HOTFIX-02** (Phase 84): Brain-dump voice sessions recover after the intro turn and sustain a full multi-turn conversation without permanent mic gating. The shipped fix uses a noise-floor RMS cutoff in `useVoiceSession` rather than the originally proposed SC4 gate rewrite; 5 manual UAT cases were approved by the user on 2026-04-30.
- [x] **HOTFIX-03** (Phase 85): SSE stream maximum duration extended from 300s → 570s in both `app/routers/admin/chat.py:_SSE_MAX_DURATION_S` and `app/fast_api_app.py:SSE_MAX_DURATION_S`, governed by single `SSE_MAX_DURATION_S` env var. 570s gives a 30s safety margin under Cloud Run's 600s --timeout. Long video renders (typical 7-9 min) now surface their final asset URL instead of dying mid-stream. SC4 (>570s renders) deferred to async-job-queue work.
- [x] **HOTFIX-04** (Phase 86): Executive Agent and Content Director can invoke `generate_pdf_report` and `generate_pitch_deck` from natural-language prompts. `_EXECUTIVE_TOOLS` now includes `*DOCUMENT_GEN_TOOLS`, both prompts name the PDF/PPTX capability, 7 wiring tests are GREEN, and manual UAT was approved by the user on 2026-05-01.
- [x] **HOTFIX-05** (Phase 87): Chat-input mic button uses the browser `SpeechRecognition` API for in-browser dictation. Plan 87-01 rewrote `frontend/src/hooks/useSpeechRecognition.ts` as a Web Speech API wrapper (~190 lines, public 11-field shape preserved); Plan 87-02 wired `frontend/src/components/chat/ChatInterface.tsx`: textarea `readOnly` removed (SC3), `displayedText` folds `interimTranscript` live via suffix-ref pattern (SC2), mid-dictation Enter/Send auto-stops recognition with `skipNextSpeechTranscriptCommitRef` flush, simplified Recording Indicator drops the dead Transcribing branch. SC5 boundary preserved — `frontend/src/hooks/useVoiceSession.ts` and `app/routers/voice_session.py` UNCHANGED line-for-line; permanent guard-rail test "chat mic does not call useVoiceSession" added to `ChatInterface.test.tsx`. Manual UAT approved by the user on 2026-05-01 across the 6-row browser matrix in `87-MANUAL-UAT.md`.
- [x] **HOTFIX-06** (Phase 88): Chat session and workspace state survive page reload via `pikar_current_session_id` localStorage key in `frontend/src/contexts/SessionControlContext.tsx`; `useLayoutEffect` restores synchronously before paint; cross-browser-tab safety via `storage` event listener (last-write-wins). The persistence path itself shipped in commit `c8da1d99` (2026-04-27); Phase 88 Plan 88-01 retroactively added vitest behavior coverage and the cross-tab listener.
- [x] **HOTFIX-07** (Phase 89): Generated PDFs and pitch decks auto-ingest into the Knowledge Vault so `search_business_knowledge` can find them. Plan 89-01 wires `DocumentService._upload_document` → `ingest_document_content` with PDF body text via existing pypdf pipeline and PPTX synthetic descriptor; standardized metadata schema {asset_id, asset_type, bucket_id, file_path, template, file_type, session_id}. Plan 89-02 tags video/image/Veo-fallback ingests with explicit top-level `document_type` (`"video"` / `"image"`); director ingest gains `render_backend`, `bucket_id`, `file_path` fields; nested `metadata.asset_type` preserved for backward-compat. Plan 89-03 adds 4 retrieval regression tests + `89-MANUAL-UAT.md` scaffold; Test 4 invokes real `generate_image` and Veo-fallback paths with `ingest_document_content` patched to assert both schemas land. All 51 phase tests GREEN. Commits cefcd73f, d0d30646, 22627612, f0a72c97, 9d1f9126.

## Feature Requirements

Net-new user-facing features that landed alongside hotfix work and are tracked for traceability rather than as hardening tasks.

- [x] **FEATURE-MULTI-SESSION-TABS** (Phase 88): Users can keep multiple chat sessions open concurrently as tabs in the chat panel header (cap 5 free / 8 paid, tier-derived via consumer-side `useChatSession()` override). Open tabs persist across reload via `pikar_open_tab_ids` localStorage key. Switching tabs swaps both the chat view and the workspace view (workspace items follow active tab's `session_id` via existing `ActiveWorkspace` re-query). Non-active tabs that are streaming or just finished a turn show a streaming/unread indicator. Closing a tab removes it from the open set and `activeSessions` map but does NOT delete the underlying session. New `<TabStrip />` component supersedes the legacy unlabeled `+` icon in `frontend/src/components/chat/ChatInterface.tsx`.

## Future Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Deeper Performance

- **PERF-F01**: SSE event loop optimized (merged queue pattern replacing dual-task polling)
- **PERF-F02**: Session state update optimized (lightweight get_session_state instead of full session+events fetch)
- **PERF-F03**: SSE connection counter moved from Redis SCAN to atomic INCR/DECR counter

### Deeper Architecture

- **ARCH-F01**: API versioning with /v1/ prefix on all routes
- **ARCH-F02**: Database migration naming standardized (exclusively timestamp-based)
- **ARCH-F03**: Pre-SSE-stream Supabase calls parallelized with asyncio.gather

### Deeper Agent Quality

- **AGT-F01**: Orphaned financial tools (save_finance_assumption, list_finance_assumptions) wired or removed
- **AGT-F02**: Dead shared instruction blocks (TLDR, INTENT_CLARIFICATION, CROSS_AGENT_HELP) removed or adopted
- **AGT-F03**: Research agent factory updated with persona parameter for consistency
- **AGT-F04**: Deep research daily quota per user via Redis counter

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full SSE architecture rewrite | Current SSE works; optimizations are incremental, not rewrite |
| Gemini 3 migration | Planned separately per memory (Oct 2026+); different scope entirely |
| New feature development | v10.0 is hardening only; no new user-facing capabilities |
| Frontend redesign | Styling/UX not in scope for hardening milestone |
| Admin agent UI changes | Backend decomposition only; admin frontend unchanged |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SEC-01 | Phase 76 | Complete |
| SEC-02 | Phase 76 | Complete |
| SEC-03 | Phase 76 | Complete |
| SEC-04 | Phase 76 | Complete |
| PERF-01 | Phase 77 | Complete |
| PERF-02 | Phase 78 | Complete |
| PERF-03 | Phase 78 | Complete |
| PERF-04 | Phase 78 | Complete |
| ARCH-01 | Phase 79 | Complete |
| ARCH-02 | Phase 79 | Complete |
| ARCH-03 | Phase 80 | Complete |
| ARCH-04 | Phase 80 | Complete |
| AGT-01 | Phase 81 | Complete |
| AGT-02 | Phase 82 | Complete |
| HOTFIX-01 | Phase 83 | Complete |
| HOTFIX-02 | Phase 84 | Complete |
| AGT-03 | Phase 81 | Complete |
| AGT-04 | Phase 81 | Complete |
| AGT-05 | Phase 82 | Complete |
| HOTFIX-03 | Phase 85 | Complete |
| HOTFIX-04 | Phase 86 | Complete |
| HOTFIX-05 | Phase 87 | Complete |
| HOTFIX-06 | Phase 88 | Complete |
| HOTFIX-07 | Phase 89 | Complete |
| BETA-01 | Phase 90 | Deferred to v13.0 |
| BETA-02 | Phase 90 | Deferred to v13.0 |
| BETA-03 | Phase 91 | Deferred to v13.0 |
| BETA-04 | Phase 91 | Deferred to v13.0 |
| BETA-05 | Phase 92 | Deferred to v13.0 |
| BETA-06 | Phase 92 | Deferred to v13.0 |
| BETA-07 | Phase 92 | Deferred to v13.0 |
| BETA-08 | Phase 93 | Deferred to v13.0 |
| BETA-09 | Phase 93 | Deferred to v13.0 |
| BETA-10 | Phase 93 | Deferred to v13.0 |
| BETA-11 | Phase 94 | Deferred to v13.0 |
| FEATURE-MULTI-SESSION-TABS | Phase 88 | Complete |
| QUALITY-01 | Phase 95 | Pending |
| QUALITY-02 | Phase 95 | Pending |
| QUALITY-03 | Phase 95 | Pending |
| QUALITY-04 | Phase 95 | Pending |
| QUALITY-05 | Phase 95 | Pending |
| QUALITY-06 | Phase 95 | Pending |
| QUALITY-07 | Phase 95 | Pending |
| QUALITY-08 | Phase 95 | Pending |
| QUALITY-09 | Phase 95 | Pending |
| QUALITY-10 | Phase 95 | Pending |
| REGISTRY-01 | Phase 96 | Pending |
| REGISTRY-02 | Phase 96 | Pending |
| REGISTRY-03 | Phase 96 | Pending |
| REGISTRY-04 | Phase 96 | Pending |
| REGISTRY-05 | Phase 96 | Pending |
| REGISTRY-06 | Phase 96 | Pending |
| ARTIFACT-01 | Phase 97 | Pending |
| ARTIFACT-02 | Phase 97 | Pending |
| ARTIFACT-03 | Phase 97 | Pending |
| ARTIFACT-04 | Phase 97 | Pending |
| ARTIFACT-05 | Phase 97 | Pending |
| ARTIFACT-06 | Phase 97 | Pending |
| ARTIFACT-07 | Phase 97 | Pending |
| ARTIFACT-08 | Phase 97 | Pending |
| ARTIFACT-09 | Phase 97 | Pending |
| ARTIFACT-10 | Phase 97 | Pending |
| LONGTASK-01 | Phase 98 | Pending |
| LONGTASK-02 | Phase 98 | Pending |
| LONGTASK-03 | Phase 98 | Pending |
| LONGTASK-04 | Phase 98 | Pending |
| LONGTASK-05 | Phase 98 | Pending |
| LONGTASK-06 | Phase 98 | Pending |
| LONGTASK-07 | Phase 98 | Pending |
| LONGTASK-08 | Phase 98 | Pending |
| RESEARCH-01 | Phase 99 | Pending |
| RESEARCH-02 | Phase 99 | Pending |
| RESEARCH-03 | Phase 99 | Pending |
| RESEARCH-04 | Phase 99 | Pending |
| RESEARCH-05 | Phase 99 | Pending |
| RESEARCH-06 | Phase 99 | Pending |
| MEMORY-01 | Phase 100 | Pending |
| MEMORY-02 | Phase 100 | Pending |
| MEMORY-03 | Phase 100 | Pending |
| MEMORY-04 | Phase 100 | Pending |
| AUTH-01 | Phase 101 | Pending |
| AUTH-02 | Phase 101 | Pending |
| AUTH-03 | Phase 101 | Pending |
| AUTH-04 | Phase 101 | Complete (101-03 commits 195fe3a6 + 1e02f6bb) |
| AUTH-05 | Phase 101 | Pending |
| WORKSPACE-01 | Phase 102 | Pending |
| WORKSPACE-02 | Phase 102 | Pending |
| WORKSPACE-03 | Phase 102 | Pending |
| WORKSPACE-04 | Phase 102 | Pending |
| WORKSPACE-05 | Phase 102 | Pending |
| WORKSPACE-06 | Phase 102 | Pending |
| POST-01 | Phase 103 | Pending |
| POST-02 | Phase 103 | Pending |
| POST-03 | Phase 103 | Pending |
| POST-04 | Phase 104 | Complete |
| POST-05 | Phase 104 | Pending |
| POST-06 | Phase 104 | Complete |
| POST-07 | Phase 105 | Pending |
| POST-08 | Phase 106 | Pending |
| POST-09 | Phase 107 | Pending |
| HYGIENE-01 | Phase 108 | Pending |
| HYGIENE-02 | Phase 108 | Pending |
| HYGIENE-03 | Phase 108 | Pending |
| HYGIENE-04 | Phase 108 | Pending |

**Coverage:**
- Core v10.0 requirements: 17 total — Complete
- Post-plan hotfix/feature requirements: 8 total — Complete
- v11.0 BETA requirements: 11 total — Deferred to v14.0
- v12.0 active requirements: 44 total (10 QUALITY + 6 REGISTRY + 10 ARTIFACT + 8 LONGTASK + 6 RESEARCH + 4 MEMORY) — Pending
- v13.0 queued requirements: 22 total (5 AUTH + 6 WORKSPACE + 9 POST + 4 HYGIENE) — Pending
- Mapped to phases: 100% (44/44 v12.0; 22/22 v13.0)
- Unmapped: 0

---
*Requirements defined: 2026-04-26*
*Last updated: 2026-05-08 — v13.0 Authentication & Connections Hardening roadmap defined with 22 requirements across 8 phases (101-108): 5 AUTH → 101, 6 WORKSPACE → 102, 3 POST → 103, 3 POST → 104, 1 POST → 105, 1 POST → 106, 1 POST → 107, 4 HYGIENE → 108. v11.0 BETA-* requirements further deferred from v13.0 → v14.0. Provenance: 2026-05-08 deep audit of social/Workspace OAuth and posting layer.*
