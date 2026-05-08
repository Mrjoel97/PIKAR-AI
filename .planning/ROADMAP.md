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
- ✅ **v10.0 Platform Hardening & Quality** - Phases 76-89 (shipped 2026-05-01, archive: [v10.0 roadmap](milestones/v10.0-ROADMAP.md), [v10.0 requirements](milestones/v10.0-REQUIREMENTS.md), [v10.0 audit](milestones/v10.0-MILESTONE-AUDIT.md))
- ⏸️ **v11.0 App Builder Beta** - Phases 90-94 — DEFERRED to v13.0 (declared 2026-05-01, deferred 2026-05-08; plans never written, scope preserved below)
- 🚧 **v12.0 Agent System Quality Upgrade** - Phases 95-100 (started 2026-05-08, 44 requirements across 6 phases; provenance: 2026-05-08 4-investigator audit)

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

### Phase 83: Document Upload Bypass

**Goal:** Files attach to chat input via standard `attachedFiles` flow and are processed inline on send via the existing `/api/upload` endpoint. The "detecting content type" indefinite loading state is eliminated by removing `/api/upload/smart` from the auto-attach path.
**Requirements**: HOTFIX-01
**Success Criteria** (what must be TRUE):
  1. Dropping a PDF / DOCX / XLSX / image into chat shows the file as an attached pill within 1s with no "detecting content type" toast or persistent spinner
  2. Pressing send delivers extracted file content inline to the agent, which processes it and responds within the normal chat flow
  3. Upload failure surfaces a single explicit system message — no infinite spinner, no stuck UI
  4. `/api/upload/smart` endpoint may remain in the codebase but is no longer called from chat attach handlers
**Depends on:** Phase 82
**Plans:** 2/2 plans complete

Plans:
- [x] 83-01-test-harness-PLAN.md — Wave 0 chatHarness test infra so Plan 02 behavior tests can render <ChatInterface /> without per-test re-mocking
- [x] 83-02-document-upload-bypass-fix-PLAN.md — Rewrite handleFileAttach + delete smart-upload state/handlers/JSX/import; add 5 behavior tests for HOTFIX-01

### Phase 84: Voice Gate Deadlock Fix

**Goal:** The brain-dump voice session is bidirectional — the agent greets, the user speaks, the agent responds, repeat — with no permanent mic gating after the intro. The `useVoiceSession` half-duplex gate releases when ALL playback buffers drain, not solely on `isPlayingRef`.
**Requirements**: HOTFIX-02
**Success Criteria** (what must be TRUE):
  1. After the agent's intro greeting completes, the user can speak and the audio reaches the server (verified via `input_transcription` in production logs)
  2. Within ~1s of the user pausing for `silence_duration_ms`, the model produces an audio response (verified via `model_turn` events)
  3. A full ≥4-turn conversation completes end-to-end with no stuck silence
  4. The mic gate is restored to multi-condition logic: suppress only while `isPlayingRef || playbackQueueRef.length > 0 || pendingTurnDelayRef || (recent remote activity within tail window)`
**Depends on:** Phase 83
**SC4 Status:** REJECTED during planning — see 84-RESEARCH.md §Q5. Root cause is server-side VAD not closing user turn; SC4 misdiagnoses the boundary. Plan implements a noise-floor RMS cutoff instead, satisfying SC1+SC2+SC3 without widening the gate.
**Plans:** 1/1 plans complete

Plans:
- [x] 84-01-noise-floor-cutoff-PLAN.md — Add noise-floor RMS cutoff in useVoiceSession.ts forwardInputChunk; SC4 explicitly rejected (HOTFIX-02)

### Phase 85: Render SSE Timeout

**Goal:** Long video renders complete and surface results to users by extending the chat SSE stream timeout. Renders that finish within Cloud Run's 600s request timeout should NOT trigger "Stream timeout — please retry your request."
**Requirements**: HOTFIX-03
**Success Criteria** (what must be TRUE):
  1. `_SSE_MAX_DURATION_S` in `app/routers/admin/chat.py` is raised from 300s to at least 600s
  2. A 30-second video render that completes in 7-9 minutes successfully streams its final asset URL to the user (no "Stream timeout" error)
  3. Heartbeat keepalive logic remains intact (no idle-disconnect during slow render steps)
  4. If render still exceeds 600s, the error is unchanged but documented as a known case requiring async-job-queue work (deferred to a later phase)
**Depends on:** Phase 84
**Plans:** 1/1 plans complete

Plans:
- [x] 85-01-sse-timeout-extension-PLAN.md — Raise SSE timeout 300s → 570s in both admin/chat.py and fast_api_app.py via SSE_MAX_DURATION_S env var (HOTFIX-03)

**SC1 Status:** Implemented at 570s, NOT the literal "≥ 600s" — engineering tradeoff for a 30s safety margin under Cloud Run's 600s --timeout (so SSE wins the race and the user sees the friendly error, not a raw 504). See 85-01-sse-timeout-extension-SUMMARY.md § "SC1 Literal-vs-Engineering Tradeoff" for full rationale.
**SC4 Status:** Deferred to a future async-job-queue phase. See `.planning/phases/85-render-sse-timeout/deferred-items.md`.

### Phase 86: Document Generation Skills Exposure

**Goal:** The Executive Agent and Content Agent can invoke `generate_pdf_report` and `generate_pitch_deck` when users request PDFs or PowerPoint presentations. Tools are imported into the executive agent's tool list and named in both agents' instruction prompts.
**Requirements**: HOTFIX-04
**Success Criteria** (what must be TRUE):
  1. Executive agent's `_EXECUTIVE_TOOLS` list (in `app/agent.py`) includes `*DOCUMENT_GEN_TOOLS`
  2. Executive instruction (`app/prompts/executive_instruction.txt`) names `generate_pdf_report` and `generate_pitch_deck` with their template options
  3. Content agent's `CONTENT_DIRECTOR_INSTRUCTION` mentions PDF and PowerPoint generation capability
  4. End-to-end: a user prompt "create a financial report PDF" results in `generate_pdf_report` being called and a downloadable PDF returned
  5. End-to-end: a user prompt "build me a pitch deck" results in `generate_pitch_deck` being called and a downloadable PPTX returned
**Depends on:** Phase 85
**Plans:** 1/1 plans complete

Plans:
- [x] 86-01-document-gen-skills-exposure-PLAN.md — HOTFIX-04: import + spread *DOCUMENT_GEN_TOOLS into _EXECUTIVE_TOOLS; name generate_pdf_report + generate_pitch_deck in both prompts (TDD: RED test suite + GREEN 3-file edit + manual UAT scaffold)

**SC1-SC3 Status:** Mechanical wiring complete and verified by 7 GREEN unit tests in `tests/unit/test_phase86_document_gen_wiring.py`.
**SC4/SC5 Status:** Mechanical proxy GREEN (tools return `{status, widget, fileType}` shape); real-Gemini routing portion awaits manual UAT in `86-MANUAL-UAT.md` against staging or `make local-backend`.

### Phase 87: Mic Dictation via Web Speech API

**Goal:** The chat input mic button uses the browser's `SpeechRecognition` API to dictate spoken words directly into the input field. No backend transcription, no "transcribing" intermediate state — words appear as the user speaks, ready to edit and send.
**Requirements**: HOTFIX-05
**Success Criteria** (what must be TRUE):
  1. Pressing the mic button on the chat input starts browser speech recognition; pressing again stops it
  2. Spoken words appear in the chat input field in real-time (interim results) and finalize on pause
  3. The user can edit the dictated text and press send like any typed message — no separate transcription step, no waiting screen
  4. If the browser doesn't support `SpeechRecognition` (Safari iOS in some versions), a clear fallback message tells the user to type instead
  5. The brain-dump voice feature is unaffected (it remains a separate, full-duplex session)
**Depends on:** Phase 86
**Plans:** 2/2 plans complete

Plans:
- [x] 87-01-speech-recognition-hook-rewrite-PLAN.md — HOTFIX-05: rewrote useSpeechRecognition.ts as a Web Speech API wrapper (~190 lines, 11-field shape preserved); installed @types/dom-speech-recognition; 8 unit tests GREEN
- [x] 87-02-chat-input-mic-integration-PLAN.md — HOTFIX-05: ChatInterface integration (textarea readOnly removed, suffix-ref live-stream, mid-dictation send via skipNextSpeechTranscriptCommitRef, simplified indicator) + 5 SC1-SC5 component tests + 1 boundary guard-rail GREEN + 87-MANUAL-UAT.md scaffold (6-row browser matrix). SC5 boundary preserved — useVoiceSession.ts and voice_session.py unchanged.

### Phase 88: Chat and Workspace Persistence + Multi-Session Tabs

**Goal:** Two-part phase. (a) Reconcile the chat-history-on-reload persistence work that shipped in commit `c8da1d99` (2026-04-27) without a corresponding GSD plan — verify the localStorage `session_id` round-trip and workspace hydration on real deploys. (b) Build multi-session tabs in the chat panel: users can keep up to N sessions open concurrently as tabs, each streaming independently, with the workspace following the active tab.
**Requirements**: HOTFIX-06, FEATURE-MULTI-SESSION-TABS
**Success Criteria** (what must be TRUE):
  1. [shipped — verify] After sending a message, refreshing the browser restores the same session — chat history visible, last agent response present (commit `c8da1d99`, `SessionControlContext.tsx:26-155`)
  2. [shipped — verify] Workspace artifacts restore from Supabase keyed on session_id (`ActiveWorkspace.tsx:317-355`)
  3. [shipped — verify] Starting a new chat (explicit user action) resets the session_id and clears workspace
  4. [open] Cross-browser-tab safety: opening the same session in a second browser tab doesn't corrupt either; last-write-wins is acceptable
  5. [shipped — verify] The chat history list shows all past sessions with previews via `/dashboard/history` and `refreshSessions`
  6. [data-layer ✓ Plan 88-02] Users can keep multiple chat sessions open concurrently as tabs in the chat panel header — cap configurable (default 5 free / 8 paid)
  7. [data-layer ✓ Plan 88-02] Open tabs persist across reload via localStorage key `pikar_open_tab_ids` alongside the existing `pikar_current_session_id`
  8. [new] Switching tabs swaps both the chat view AND the workspace view — workspace items follow the active tab's `session_id` (no stale items from prior tab)
  9. [new] Non-active tabs that are streaming or just finished a turn show an unread/streaming indicator on their tab pill
 10. [data-layer ✓ Plan 88-02] Closing a tab removes it from the open set and from `activeSessions` map; it does NOT delete the underlying session from Supabase (delete is a separate destructive action via `/dashboard/history`)
 11. [new] The "+" new-chat affordance is replaced with a discoverable tab strip; existing tiny `+` icon at `ChatInterface.tsx:1351` is superseded
**Depends on:** Phase 87
**Plans:** 4/4 plans complete

Plans:
- [x] 88-01-persistence-reconciliation-PLAN.md — HOTFIX-06: cross-tab safety storage event listener + retroactive verification of c8da1d99
- [x] 88-02-tab-state-PLAN.md — FEATURE-MULTI-SESSION-TABS: openTabIds state + tier-aware cap + localStorage persistence (no UI)
- [x] 88-03-tab-strip-ui-PLAN.md — FEATURE-MULTI-SESSION-TABS: TabStrip component + ChatInterface header restructure (replaces legacy +)
- [x] 88-04-streaming-indicator-PLAN.md — FEATURE-MULTI-SESSION-TABS: streaming/unread indicators + sonner cap toast + final UAT

### Phase 89: Knowledge Vault Auto Sync

**Goal:** Every artifact the agent creates (images, videos, generated documents) is automatically ingested into the Knowledge Vault tagged by session_id and content type, with no manual "Add to Vault" step required. The vault becomes a complete record of the agent's outputs alongside user uploads.
**Requirements**: HOTFIX-07
**Success Criteria** (what must be TRUE):
  1. When the director service uploads a finished video to `generated-videos` bucket, the same asset is registered in the Knowledge Vault with metadata (session_id, prompt, render_backend)
  2. When the image service generates an Imagen/Veo asset, it lands in the vault automatically
  3. When `generate_pdf_report` or `generate_pitch_deck` produces a file, it lands in the vault automatically
  4. Vault search (`search_business_knowledge`) can retrieve agent-generated assets by content + session
  5. Existing manual "Add to Vault" upload path remains functional for user-uploaded files
**Depends on:** Phase 88
**Plans:** 3/3 plans complete

Plans:
- [x] 89-01-document-service-vault-wiring-PLAN.md — HOTFIX-07: close the third auto-ingest path — DocumentService._upload_document now ingests generated PDFs (extracted text) and pitch decks (synthetic descriptor) into Knowledge Vault with document_type="pdf" / "pitch_deck" + standardized metadata; 5 unit tests
- [x] 89-02-standardize-tagging-shipped-paths-PLAN.md — HOTFIX-07: promote asset_type to top-level document_type across the 2 shipped paths (director_service.py video, media.py image + video fallback); preserve nested metadata.asset_type for legacy readers; 4 unit tests
- [x] 89-03-search-retrieval-regression-PLAN.md — HOTFIX-07: end-to-end regression suite asserting search_business_knowledge retrieves all 5 document_type values + manual upload branch unchanged + DocumentService PDF round-trip proxy; 89-MANUAL-UAT.md scaffold for real-Gemini SC1-SC5

---

## v11.0 App Builder Beta — DEFERRED to v13.0

**Status (2026-05-08):** DEFERRED. Phase 90-94 goals + success criteria were declared on 2026-05-01 but plans were never written. Milestone is bumped behind v12.0 Agent System Quality Upgrade (2026-05-08 audit identified higher-priority systemic gaps in the agent system itself). Scope below preserved verbatim for resumption in v13.0.

**Milestone Goal:** Take the existing app-builder generation engine (shipped in v2.0, refined since) and finish the wrap so non-technical users can create end-to-end landing pages and multi-page brochure websites — and publish them to a hosted URL — without leaving the platform. Web app and mobile app capabilities are explicitly out of scope for this milestone (deferred to v12.0+).

**Locked decisions** (recorded 2026-05-01, see [v11.0 PROJECT-CONTEXT](v11.0-PROJECT-CONTEXT.md)):
- **Hosting:** Static hosting via Supabase Storage + Cloud Run route serving HTML by slug (e.g. `pikar.app/sites/{slug}`); HTTPS via Cloudflare wildcard. Vercel API deploy deferred.
- **Beta scope:** Tier 1 only — single landing pages + multi-page brochure websites (5-10 pages). Blogs, e-commerce, web apps, mobile apps explicitly deferred.
- **Form submissions:** Routed to a `landing_form_submissions` Supabase table with email notification to project owner.
- **Beta cohort:** Closed/invited 50-100 users after Phase 94 ships; public beta is v12.0.

### Phase 90: Scope Narrowing + Onboarding

**Goal:** The app-builder questioning wizard, marketing copy, and empty states honestly reflect what we ship in v11.0 (landing pages + multi-page websites only). First-time users land with an anchor — at least one sample template they can fork in one click.
**Requirements**: BETA-01, BETA-02
**Success Criteria** (what must be TRUE):
  1. Questioning wizard step 1 ("What do you want to build?") shows only "Landing page" and "Multi-page website" — "Web app" and "Mobile app" either removed or marked "Coming soon" and disabled
  2. Questioning copy across all 5 steps consistently uses "website / landing page" language; no surfaces still say "app"
  3. `/app-builder/new` shows a "Try a sample" CTA that creates a pre-baked Coffee shop landing page project in <2s with a `seed_template` flag
  4. Empty state on `/app-builder` (when user has zero projects) shows the sample CTA + a 1-line tagline explaining the feature
  5. The questioning wizard can be completed start-to-finish in <90 seconds for a returning user
**Depends on:** none (independent of other v11.0 phases)
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 90 to break down)

### Phase 91: My Apps Dashboard

**Goal:** Users can see, resume, re-download, and delete all of their app-builder projects from a dedicated dashboard. Closing the tab no longer means losing your work; this is the long-deferred Phase 23 from the v2.0 milestone audit (gap BLDR-01).
**Requirements**: BETA-03, BETA-04
**Success Criteria** (what must be TRUE):
  1. `/app-builder` (when user has ≥1 project) renders a list of their projects with title, current stage, last-updated time, and thumbnail of the first generated screen if any
  2. Clicking a project navigates to its appropriate stage page (e.g. `/app-builder/{id}/building` if stage="building")
  3. Each project card has a "Re-download exports" link that re-fetches the most recent ship outputs (React/PWA ZIPs)
  4. Each project card has a destructive "Delete" action with confirm; deletion removes the project + all associated screens + Supabase storage assets
  5. Pagination or infinite scroll for users with >20 projects
  6. Dashboard loads in <500ms cold (cached for warm)
**Depends on:** Phase 90
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 91 to break down)

### Phase 92: Hosted Preview URL

**Goal:** When a user "ships" their site, they get a working public URL they can share with clients/customers — no ZIP download required, no manual hosting step. URL format: `pikar.app/sites/{slug}`. Closes v2.0 audit gaps FOUN-06 and BLDR-03.
**Requirements**: BETA-05, BETA-06, BETA-07
**Success Criteria** (what must be TRUE):
  1. After `/ship` completes for a project, a `published_sites` row is created with `slug`, `project_id`, `latest_html_url`, and `published_at`
  2. GET `pikar.app/sites/{slug}` returns the generated HTML/CSS/JS for that site (Cloud Run route serving from Supabase Storage)
  3. HTTPS works for all generated URLs (Cloudflare wildcard cert covering `*.pikar.app` or path-based `pikar.app/sites/*`)
  4. Caching: cold load <2s, warm load <300ms, cache invalidated on re-ship within 30s
  5. Re-shipping the same project updates the existing slug (does not create a new one)
  6. Slugs are user-editable post-ship (e.g. `pikar.app/sites/joes-coffee` instead of `pikar.app/sites/abc123`); collision detection prevents duplicate slugs across users
  7. The shipping page UI shows the live URL prominently after publish, with copy-to-clipboard and "Open in new tab" buttons
**Depends on:** Phase 91
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 92 to break down)

### Phase 93: Form Submissions + Production Hardening

**Goal:** Contact forms on generated landing pages actually capture submissions and notify the project owner. Production deployment is verified end-to-end on Cloud Run (Stitch subprocess + STITCH_API_KEY + Node runtime). Stitch failures degrade gracefully with status banners instead of silent empty screens.
**Requirements**: BETA-08, BETA-09, BETA-10
**Success Criteria** (what must be TRUE):
  1. Generated landing pages with `<form>` elements POST to `pikar.app/api/sites/{slug}/submit`; submissions land in a `landing_form_submissions` table with `slug`, `payload`, `submitted_at`, `submitter_ip`
  2. Project owner receives an email notification within 60s of each submission (via existing email integration; rate-limited to prevent spam)
  3. The owner can view all submissions for their project from the project dashboard with CSV export
  4. End-to-end smoke test on the deployed Cloud Run env: create project → questioning → research → build 1 screen → ship → load `pikar.app/sites/{slug}` → submit form → confirm row in DB
  5. `STITCH_API_KEY` confirmed set in Cloud Run; `npx @_davideast/stitch-mcp` confirmed runnable in Cloud Run runtime
  6. When `StitchMCPService.is_ready()` returns False, the building page shows a "Generation temporarily unavailable — we'll retry shortly" status banner instead of a blank/spinning state
  7. All user-facing error states use plain language ("We couldn't generate that screen — please try again or describe it differently") instead of stack traces or raw exception messages
**Depends on:** Phase 92
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 93 to break down)

### Phase 94: Beta UAT + Top-5 Friction Fixes

**Goal:** 3-5 invited users complete the full landing-page-creation flow end-to-end. Friction points are captured and the top 5 are fixed before the v11.0 milestone closes. After this phase, app-builder beta is open to a 50-100 user invited cohort.
**Requirements**: BETA-11
**Success Criteria** (what must be TRUE):
  1. ≥3 invited users complete the full flow (questioning → research → brief → 5-page brochure site → ship → see live URL) without dropping out
  2. UAT findings captured in `94-UAT-FINDINGS.md` with severity, frequency, and proposed fix
  3. Top 5 friction points (by severity × frequency) have shipped fixes verified in a re-test pass
  4. ≥1 of the test users would recommend the product to another non-technical user (NPS proxy)
  5. Beta-open checklist signed off (status banner OK, error states OK, dashboard OK, form submissions verified, Stitch health monitored)
**Depends on:** Phase 93
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 94 to break down)

---

## v12.0 Agent System Quality Upgrade

**Milestone Goal:** Convert the multi-agent system from "single-shot chat agents" into "30-60 minute capable executive operators with persistent memory and tangible deliverables." The 2026-05-08 audit identified four systemic patterns: (1) drifted sources of truth (prompts advertise tools agents don't own; ghost registries; hallucinated delegations), (2) one complete artifact pipeline (media) with everything else half-built, (3) long-task infrastructure half-exists/half-disabled (worker un-deployed, summarizer flag-gated off, sync I/O blocking the event loop), (4) research is mechanical where it should be generative. Phases 95-100 address each in turn, with bug fixes first to clear the ground.

**Provenance:** 2026-05-08 audit — 4 parallel investigators with ~400 file:line citations across `app/agents/`, `app/agents/tools/`, `app/prompts/`, `app/services/`, `app/persistence/`, `frontend/src/services/workspaceArtifacts.ts`, `frontend/src/hooks/useBackgroundStream.ts`, and the `chat_widgets` / `media_assets` / `agent_memory` schema surfaces.

**Coverage:** 44/44 v12.0 requirements mapped 1:1 to phases (10 QUALITY → 95, 6 REGISTRY → 96, 10 ARTIFACT → 97, 8 LONGTASK → 98, 6 RESEARCH → 99, 4 MEMORY → 100). Zero unmapped.

**Execution order:** 95 stands alone (10 atomic bug fixes). 96 depends on 95 (clean ground before consolidating registries). 97/98 depend on 95 (some bug fixes touch artifact + worker code paths). 99/100 depend on 96 (the manifest is the right place to add `quick_research` and to declare each agent's memory). 97 → 98 → 99 → 100 is the value-realization order; 97/98/99/100 may execute partially in parallel after 96 ships.

### Phase 95: Bug-Fix Sprint (Phase A)

**Goal:** Eliminate the 10 specific production bugs identified by the 2026-05-08 audit — ghost-tool advertisements, blocking image-generation I/O, agent escalation impossibilities, ResearchAgent memory corruption, deterministic-routing temperature mistakes, and unsafe untrusted code paths — so subsequent phases can build on a clean foundation instead of paving over bugs.
**Requirements**: QUALITY-01, QUALITY-02, QUALITY-03, QUALITY-04, QUALITY-05, QUALITY-06, QUALITY-07, QUALITY-08, QUALITY-09, QUALITY-10
**Success Criteria** (what must be TRUE):
  1. The Executive Agent never claims to use a tool it doesn't have — `executive_instruction.txt` references match the actual tool inventory (verifiable by grep + integration test) and a routing prompt for "show revenue stats" or "build me a landing page" hands off to the appropriate specialist instead of calling a non-existent local tool
  2. A user request for a data report routes successfully to `DataReportingAgent` end-to-end (specialized_agents wiring + executive routing table updated); a user request for a marketing campaign no longer dead-ends at "escalate to parent" — the campaign hand-off completes with a structured envelope or the CampaignAgent acts directly with `AD_PLATFORM_TOOLS`
  3. Generating an image during a chat does not block the SSE event loop — concurrent SSE streams continue to flow heartbeats while `media.py` performs the Supabase upload (verified by load test: 5 simultaneous image generations + heartbeat cadence intact)
  4. ResearchAgent retains context across at least 3 multi-turn requests (e.g. "research X" → "now compare to Y" → "summarize for an exec audience") without losing the prior turns; the broken `SELF_IMPROVEMENT_INSTRUCTIONS` block is no longer present in `app/agents/research/instructions.py`
  5. Customer support metric requests render as widgets (not silent failures) — `create_stat_widget`/`create_table_widget` is correctly resolved at `customer_support/agent.py:80`; Marketing routing at temperature 0.2 produces the same routing decision across 5 identical inputs; DataReportingAgent runs with `DEEP_AGENT_CONFIG` (no missing `generate_content_config` warning at agent.py:203/250)
  6. System emails respect `RESEND_FORWARD_TO` env var (no hardcoded personal email at `mcp/config.py:52`); `run_script` and `update_code` in `integration_tools.py` are either deleted or gated behind a feature-flag + path-traversal-guarded allowlist (verifiable: no agent's tool list registers them as exposed callables)
**Depends on:** none (stands alone — first phase of v12.0)
**Provenance:** 2026-05-08 audit
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 95 to break down)

### Phase 96: Single-Source Truth (Phase B)

**Goal:** Eliminate the entire class of ghost-tool / hallucinated-delegation bugs forever by establishing one canonical place — an `AgentManifest` Pydantic model — for each agent's name, model config, tool list, sub-agents, and prompt template. Prompts and the Executive routing table auto-generate from manifests so manual drift between sources of truth becomes structurally impossible.
**Requirements**: REGISTRY-01, REGISTRY-02, REGISTRY-03, REGISTRY-04, REGISTRY-05, REGISTRY-06
**Success Criteria** (what must be TRUE):
  1. Each agent has exactly one `AgentManifest` definition — `grep -r "class.*Manifest"` returns one definition per agent and zero parallel definitions in factory functions; deleting a tool from the manifest deletes it from the agent's runtime tool list AND from the agent's prompt's "Available Tools" section in a single edit
  2. The Executive Agent's "AVAILABLE SPECIALISTS" block is generated from the union of agent manifests, not hand-edited — modifying a specialist's manifest (e.g. renaming a tool or adding a sub-agent) re-renders the executive prompt section without manual prompt edits, and a CI check fails if the rendered prompt drifts from the manifest source
  3. Legacy / dead code is gone — `app/agents/tools/registry.py` (degraded-tool dispatcher) and `app/agents/tools/document_generation.py` (superseded by `document_gen.py`) are deleted from the repo; wrapper aliases `instagram_post_image`, `generate_short_video`, `generate_short_videos` are deleted and any caller now uses the canonical function names
  4. PDF generation has typed schemas — `generate_pdf_report` no longer accepts an untyped `data: dict[str, Any]`; instead it accepts a discriminated union of `TypedDict`s (one per template) so Gemini's tool-calling schema is concrete and template-specific arguments are validated at the framework boundary
**Depends on:** Phase 95 (bug-fix sprint must clean the ground first — ghost tools / dead registries identified in 95 are removed in 96)
**Provenance:** 2026-05-08 audit
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 96 to break down)

### Phase 97: Tangible Outputs (Phase C)

**Goal:** Extend the existing media-pipeline contract (storage → `media_assets` → `knowledge_vault` → `chat_widgets` → frontend → Vault) to every output type — Google Docs, Sheets, approvals, long-form text, markdown reports, briefings, director storyboards — so every agent response becomes a real, perpetuable artifact with bidirectional chat ↔ Vault deep-links and an explicit Save action on every message.
**Requirements**: ARTIFACT-01, ARTIFACT-02, ARTIFACT-03, ARTIFACT-04, ARTIFACT-05, ARTIFACT-06, ARTIFACT-07, ARTIFACT-08, ARTIFACT-09, ARTIFACT-10
**Success Criteria** (what must be TRUE):
  1. When an agent creates a Google Doc or Google Sheet during chat, the user sees a document widget in the chat stream that links to the file AND the file appears in Vault > Documents tab within 5s — both surfaces resolve via the same `chat_widgets` row (no client-only state, no auth-token-staleness gap)
  2. Approving an agent-emitted approval card in chat resumes the agent's pending workflow within 30 seconds without the user re-prompting — `approval` widget renders Approve/Reject buttons, decision POSTs to `/approvals/{token}/decision`, and the originating session receives the decision via Supabase realtime/poll so the agent's wait completes
  3. Long-form text outputs ≥200 chars persist as artifacts (lowered from 650), markdown reports persist server-side via `app/sse_utils.py` (not client-side `useBackgroundStream.ts`) so widgets survive auth-token expiration, and briefings + weekly reports emit downloadable PDFs that land in Vault — verifiable: a 250-char agent response creates a `chat_widgets` row, and the morning briefing produces a Vault-visible PDF
  4. Every chat message has a "Save to Vault" affordance that creates a `media_assets` row of type `note` and a corresponding "Find in Vault" chip on saved widgets; clicking a Vault entry deep-links back to its originating chat session via `media_assets.session_id`
  5. Director storyboard captions render as a structured `DirectorProgressCard` (scene-by-scene from `planning_done` payload at `director_service.py:350`) instead of dumping raw JSON into the trace drawer — visually verifiable in the UI
**Depends on:** Phase 95 (bug-fix sprint touches `media.py` artifact path; 97 extends that contract once it's clean)
**Provenance:** 2026-05-08 audit
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 97 to break down)

### Phase 98: 30-60min Capable (Phase D)

**Goal:** Make 30-60 minute agent tasks first-class — surviving client disconnects, instance restarts, cold starts, and proxy idle timeouts; showing meaningful progress at every tool-call boundary; and using deployed durable-job infrastructure rather than the half-disabled current state. Tasks expected to exceed 5 minutes return a `job_id` immediately and stream progress; the WorkflowWorker runs as a deployed Cloud Run Job; the conversation summarizer is enabled in production; the session event window holds 200+ events with visible truncation.
**Requirements**: LONGTASK-01, LONGTASK-02, LONGTASK-03, LONGTASK-04, LONGTASK-05, LONGTASK-06, LONGTASK-07, LONGTASK-08
**Success Criteria** (what must be TRUE):
  1. A 30-min agent task completes successfully after a 60-second client disconnect mid-stream and the user sees the final result on reconnect — long-running operations issue a `job_id`, the SSE stream polls job progress events, and the `WorkflowWorker` Cloud Run Job continues processing across the disconnect
  2. The `WorkflowWorker` is a deployed Cloud Run Job (not just `scripts/dev/run_worker.py`) triggered by Cloud Scheduler; `worker.py` uses `get_async_client()` for all Supabase reads/writes (no synchronous `.execute()` blocking the event loop at lines 97-99/115-117/121-123/315-317)
  3. `ENABLE_CONVERSATION_SUMMARIZER=true` in production and the summary injection at `app/persistence/supabase_session_service.py:448-462` is active for all sessions; the session event window holds ≥200 events (raised from 80) with a truncation banner emitted into the SSE stream when overflow occurs
  4. The Vertex context cache TTL is 3600s (raised from 600s) so a 30-60 min session avoids 2-5 cache rebuilds; `reap_stale_jobs` resets interrupted-but-not-errored steps to `pending` instead of `failed` (verifiable: kill the worker mid-step, restart, step resumes)
  5. The agent emits a structured progress event at every tool-call boundary — UI never goes silent during multi-minute tool runs (verifiable: a 5-minute deep-research call shows ≥3 visible progress events in the SSE stream with tool name + estimated duration)
**Depends on:** Phase 95 (bug-fix sprint touches worker code path — async I/O fix in `media.py` is the same pattern applied to `worker.py` here)
**Provenance:** 2026-05-08 audit
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 98 to break down)

### Phase 99: Generative Research (Phase E)

**Goal:** Move research from mechanical (string-concat synthesis, hardcoded 3 serial queries, source-counting confidence) to generative (parallel queries, LLM synthesis with structured claim/evidence tuples, follow-up hops based on initial findings, real LLM-graded confidence). Specialist agents call research without round-tripping through the Executive via a new `quick_research` tool, so research happens inside a specialist's turn.
**Requirements**: RESEARCH-01, RESEARCH-02, RESEARCH-03, RESEARCH-04, RESEARCH-05, RESEARCH-06
**Success Criteria** (what must be TRUE):
  1. Initial research queries execute in parallel — up-front search latency drops from ~90s to ~30s (verifiable by timing instrumentation around `deep_research.py:111`); the serial `await` loop is replaced with `asyncio.gather`
  2. Research synthesis is LLM-driven — `_synthesize_findings` returns structured `(claim, evidence, source-id, contradicts)` tuples produced by a Gemini Flash call (not string concatenation); after first synthesis, the model is prompted "what's missing? what questions does this raise?" and 1-3 follow-up queries fire (capped at 2 hops to bound cost)
  3. Research output includes LLM-graded confidence — `confidence_score` reflects source authority, recency, and agreement-across-sources (not mechanical source-counting); contradicting sources are surfaced as a distinct "conflicts" section in the rendered research card (not buried in prose)
  4. Specialist agents (Sales, Marketing, Content, Operations, etc.) call `quick_research` directly — a 1-query, 3-scrape, ~30s tool registered to all specialists' manifests so research happens inside a specialist's turn without round-tripping through the Executive (verifiable: a Sales agent question about a competitor invokes `quick_research` end-to-end without an Executive hop)
**Depends on:** Phase 96 (registry/manifest must exist before adding `quick_research` to every specialist's tool list — without manifests, this would be a 13-file manual edit instead of a one-line manifest entry)
**Provenance:** 2026-05-08 audit
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 99 to break down)

### Phase 100: Cross-Agent Memory (Phase F)

**Goal:** Convert agents from amnesiac specialists into operators-with-continuity by giving each its own persistent per-user memory (e.g. Sales agent remembers tracked deals, Financial remembers raised flags, Content remembers brand voice) that auto-injects into prompts via shared callbacks; and structuring agent-to-agent handoffs as `HandoffPacket` envelopes (intent + evidence + constraints + expected output shape) instead of re-deriving from session state. All sub-sub-agents (VideoDirector, GraphicDesigner, Copywriter, RiskReport, ConfigurationAgent, LeadScoring, etc.) are audited for required memory callback registration.
**Requirements**: MEMORY-01, MEMORY-02, MEMORY-03, MEMORY-04
**Success Criteria** (what must be TRUE):
  1. Each agent has structured per-user memory persisted in a new `agent_memory` table keyed by `(user_id, agent_name)` — verifiable: the Sales agent, asked the same question in two separate sessions a week apart, references the same tracked deal without re-prompting from session state
  2. Every agent's `before_model_callback` reads its own `agent_memory` row and injects relevant facts into the prompt for the upcoming turn (verifiable by prompt inspection: a Financial agent prompt for "what flags should I check?" includes previously raised flags from `agent_memory` without explicit tool call)
  3. Executive→specialist handoffs use a `HandoffPacket` envelope — intent, supporting evidence, constraints, and expected output shape are passed structurally; the receiving specialist no longer re-derives intent from session state (verifiable: a routed task to the Marketing agent receives a typed packet object, not a re-parsed user message)
  4. Every sub-sub-agent (VideoDirector, GraphicDesigner, Copywriter, RiskReport, ConfigurationAgent, LeadScoring, etc.) registers `context_memory_before_model_callback` + after-tool callback — audited and confirmed by a regression test that fails if any sub-agent factory returns an agent without both callbacks
**Depends on:** Phase 96 (the manifest is the right place to declare each agent's memory shape and register memory callbacks structurally; without manifests this is a 13-file scattered edit)
**Provenance:** 2026-05-08 audit
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 100 to break down)

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
**Plans**: 2 plans

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
**Plans**: 2 plans

Plans:
- [ ] 82-01: AGT-02: Admin agent decomposition into SystemHealth, UserManagement, Billing, Governance sub-agents with context callbacks
- [ ] 82-02: AGT-05: search_knowledge relocation to app/agents/tools/knowledge.py + cross-agent tool deduplication (blog pipeline, video generation, start_initiative_from_idea)

## Progress

**Execution Order:**
v10.0 executes in order: 76 → 77 → 78 → 79 → 80 → 81 → 82
(77, 78, 79, 81 can run in parallel after 76; 80 depends on 78+79; 82 depends on 81)

v12.0 executes: 95 (no GSD dep) → 96 (depends on 95) → 97/98 (depend on 95) → 99/100 (depend on 96)
(97/98/99/100 may execute partially in parallel after 96; value-realization order is 97 → 98 → 99 → 100)

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
| 78. DB & Cache Performance | 2/2 | Complete    | 2026-04-27 | - |
| 79. Architectural Resilience | 1/1 | Complete    | 2026-04-27 | - |
| 80. Workflow Consistency & API Contracts | 2/2 | Complete    | 2026-04-27 | - |
| 81. Agent Config Fixes | 2/2 | Complete    | 2026-04-27 | - |
| 82. Agent Restructuring | 2/2 | Complete    | 2026-04-27 | - |
| 85. Render SSE Timeout | v10.0-hotfix | Complete    | 2026-05-01 | 2026-04-30 |
| 86. Document Generation Skills Exposure | v10.0-hotfix | Complete    | 2026-05-01 | 2026-05-01 |
| 90. Scope Narrowing + Onboarding | v11.0 | 0/0 | Deferred to v13.0 | - |
| 91. My Apps Dashboard | v11.0 | 0/0 | Deferred to v13.0 | - |
| 92. Hosted Preview URL | v11.0 | 0/0 | Deferred to v13.0 | - |
| 93. Form Submissions + Production Hardening | v11.0 | 0/0 | Deferred to v13.0 | - |
| 94. Beta UAT + Top-5 Friction Fixes | v11.0 | 0/0 | Deferred to v13.0 | - |
| 95. Bug-Fix Sprint | v12.0 | 0/0 | Not started | - |
| 96. Single-Source Truth | v12.0 | 0/0 | Not started | - |
| 97. Tangible Outputs | v12.0 | 0/0 | Not started | - |
| 98. 30-60min Capable | v12.0 | 0/0 | Not started | - |
| 99. Generative Research | v12.0 | 0/0 | Not started | - |
| 100. Cross-Agent Memory | v12.0 | 0/0 | Not started | - |
