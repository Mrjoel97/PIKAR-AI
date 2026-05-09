---
gsd_state_version: 1.0
milestone: v12.0
milestone_name: Agent System Quality Upgrade
status: in_progress
stopped_at: Completed 106-01-status-polling-PLAN.md
last_updated: "2026-05-09T02:44:52.657Z"
last_activity: "2026-05-08 — v13.0 ROADMAP written. Inserted as a `<details><summary>📋 v13.0 Authentication & Connections Hardening (Phases 101-108) — QUEUED 2026-05-08</summary>` block after the v12.0 section. Each phase includes Goal, Requirements (REQ-IDs), Success Criteria (observable user behaviors / testable code states), Depends on, Provenance: 2026-05-08 audit, Plans: 0 plans (TBD). Top-level Milestones list updated: v11.0 status changed to "DEFERRED to v14.0", v13.0 added as 📋 queued. v11.0 phase rows in progress table updated from "Deferred to v13.0" → "Deferred to v14.0". Progress table appended with rows 101-108. REQUIREMENTS.md v13.0 traceability table populated with all 22 REQ-ID → Phase mappings (status: Pending). v11.0 BETA-* traceability rows preserved unchanged per instruction (do NOT touch v10.0/v11.0/v12.0 traceability sections); BETA-* coverage summary updated to "Deferred to v14.0"."
progress:
  total_phases: 34
  completed_phases: 18
  total_plans: 45
  completed_plans: 38
---

---
gsd_state_version: 1.0
milestone: v13.0
milestone_name: Authentication & Connections Hardening
status: in_progress
stopped_at: 102-02 complete (WORKSPACE-04 + WORKSPACE-05 shipped 2026-05-09 on feat/vault-fixes-and-agent-actions, commits 1db9e340 test-RED + 260ecf14 feat-GREEN refresh helper + deec7740 revoke-on-disconnect). Phase 102 has 102-01 (provider registry + before_model_callback bridge) and 102-02 (sync refresh helper + revoke) shipped. 102-03 (frontend connect/disconnect card) remains.
last_updated: "2026-05-09T02:05:00.000Z"
last_activity: 2026-05-09 — 102-02 token refresh + disconnect-revoke executed and shipped. New module app/services/google_workspace_token_refresh.py exports refresh_if_expiring() (sync httpx.Client mirror of async IntegrationManager._refresh_token, locked Approach C from 102-CONTEXT). Wired one-line refresh_if_expiring(tool_context) into 7 helpers (docs, gmail, google_sheets, calendar_tool, forms, gmail_inbox, briefing_tools.approve_draft). document_editor.py confirmed docstring-only reference per RESEARCH §1.8, no code change. GoogleWorkspaceAuthService.disconnect now resolves access token, POSTs to https://oauth2.googleapis.com/revoke (best-effort: WARNING on network/non-200 but proceeds), then runs the existing 4 _delete_rows + _set_disconnect_marker. 12 new pytest tests GREEN (8 TestRefreshIfExpiring + 4 TestDisconnectRevoke); 11 existing GoogleWorkspaceAuthService tests still GREEN; 55 regression tests still GREEN. Co-tenancy note: Tasks 1+2 commits incidentally swept in concurrent 103-02/104-01 staged content from the git index (orchestrator warned of parallel activity); 102-02 made no content modifications to those files. Phase 102 needs only 102-03 (frontend card) to close.
progress:
  total_phases: 8
  completed_phases: 0
  total_plans: 5
  completed_plans: 5
---

---
gsd_state_version: 1.0
milestone: v12.0
milestone_name: Agent System Quality Upgrade
status: roadmap_complete
stopped_at: ROADMAP.md written for v12.0 (6 phases 95-100, 44/44 requirements mapped 1:1, zero unmapped)
last_updated: "2026-05-08T12:00:00.000Z"
last_activity: 2026-05-08 — v12.0 ROADMAP section written. 6 phases declared with goals + 4-6 observable success criteria each + REQ-ID mappings + Provenance line + dependency chain (95 standalone, 96 depends on 95, 97/98 depend on 95, 99/100 depend on 96). Coverage 100% (44/44): Phase 95 owns QUALITY-01..10, Phase 96 owns REGISTRY-01..06, Phase 97 owns ARTIFACT-01..10, Phase 98 owns LONGTASK-01..08, Phase 99 owns RESEARCH-01..06, Phase 100 owns MEMORY-01..04. v11.0 (90-94) explicitly marked DEFERRED to v13.0 in milestone header. Top-level Milestones list in ROADMAP.md updated. REQUIREMENTS.md traceability table verified (already had all 44 v12.0 mappings). Ready for /gsd:plan-phase 95.
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

---
gsd_state_version: 1.0
milestone: v13.0
milestone_name: Authentication & Connections Hardening
status: queued
stopped_at: Defining requirements (post-audit milestone bootstrap)
last_updated: "2026-05-08T00:00:00.000Z"
last_activity: 2026-05-08 — v13.0 milestone queued behind v12.0. Derived from deep audit of social media OAuth/posting + Google Workspace credential plumbing (file:line citations across app/social/, app/agents/tools/google_*, app/services/google_workspace_auth_service.py, app/agents/context_extractor.py, supabase/migrations/0010_connected_accounts.sql). 8 phases (101-108) covering connected_accounts security hardening, Google Workspace credential bridge, LinkedIn/Twitter/YouTube/TikTok/Facebook posting fixes, and hygiene + test coverage. v11.0 App Builder Beta further deferred from v13.0 to v14.0.
progress:
  total_phases: 8
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

---
gsd_state_version: 1.0
milestone: v12.0
milestone_name: Agent System Quality Upgrade
status: planning
stopped_at: Defining requirements (post-audit milestone bootstrap)
last_updated: "2026-05-08T00:00:00.000Z"
last_activity: 2026-05-08 — v12.0 milestone declared after 4-investigator parallel audit of agent system. v11.0 (App Builder Beta, phases 90-94) deferred to v14.0 with plans never written. v12.0 covers 6 phases (95-100) — Bug-Fix Sprint, Single-Source Truth, Tangible Outputs, 30-60min Capable, Generative Research, Cross-Agent Memory. Requirements derived from audit; phases scoped 1:1 with audit findings.
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

---
gsd_state_version: 1.0
milestone: v11.0
milestone_name: App Builder Beta
status: planning
stopped_at: Completed 89-knowledge-vault-auto-sync 89-03-search-retrieval-regression-PLAN.md (Phase 89 complete pending gsd-verifier)
last_updated: "2026-05-02T02:13:06.958Z"
last_activity: 2026-05-01 — v10.0 milestone closed (14 phases, 27 plans shipped). v11.0 milestone roadmap created with 5 phases (90 Onboarding, 91 Dashboard, 92 Hosted Preview, 93 Forms + Hardening, 94 UAT). 11 BETA-* requirement IDs registered in REQUIREMENTS.md traceability.
progress:
  total_phases: 20
  completed_phases: 14
  total_plans: 27
  completed_plans: 27
---

---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Platform Hardening & Quality
status: planning
stopped_at: Completed 89-knowledge-vault-auto-sync 89-03-search-retrieval-regression-PLAN.md (Phase 89 complete pending gsd-verifier)
last_updated: "2026-05-01T23:04:42.468Z"
last_activity: 2026-05-02 — Phase 87 closed (HOTFIX-05). 87-02 wired ChatInterface for live interim streaming via suffix-ref pattern (input + speechTranscript + interimTranscript while isRecording), removed textarea readOnly gate (SC3 load-bearing), added skipNextSpeechTranscriptCommitRef flush-and-suppress pattern so handleSend can call stopRecording() to flush pending interim into final without a phantom append-after-send. Send button onClick uses displayedText.trim() so dictated text alone enables send. 6 new HOTFIX-05 tests GREEN incl. permanent SC5 boundary guard-rail (chat mic does not call useVoiceSession.connect/disconnect). Commits 629c406b (RED — tests + UAT) and ec81170a (GREEN — production edits). useVoiceSession.ts and app/routers/voice_session.py UNCHANGED line-for-line — verified via git diff --stat HEAD~2 HEAD returning empty for SC5-protected paths.
progress:
  total_phases: 15
  completed_phases: 14
  total_plans: 27
  completed_plans: 27
---

---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Platform Hardening & Quality
status: planning
stopped_at: Completed 89-knowledge-vault-auto-sync 89-03-search-retrieval-regression-PLAN.md (Phase 89 complete pending gsd-verifier)
last_updated: "2026-05-01T21:27:38.767Z"
last_activity: 2026-05-02 — Phase 87 closed (HOTFIX-05). 87-02 wired ChatInterface for live interim streaming via suffix-ref pattern (input + speechTranscript + interimTranscript while isRecording), removed textarea readOnly gate (SC3 load-bearing), added skipNextSpeechTranscriptCommitRef flush-and-suppress pattern so handleSend can call stopRecording() to flush pending interim into final without a phantom append-after-send. Send button onClick uses displayedText.trim() so dictated text alone enables send. 6 new HOTFIX-05 tests GREEN incl. permanent SC5 boundary guard-rail (chat mic does not call useVoiceSession.connect/disconnect). Commits 629c406b (RED — tests + UAT) and ec81170a (GREEN — production edits). useVoiceSession.ts and app/routers/voice_session.py UNCHANGED line-for-line — verified via git diff --stat HEAD~2 HEAD returning empty for SC5-protected paths.
progress:
  total_phases: 15
  completed_phases: 14
  total_plans: 27
  completed_plans: 27
  percent: 99
---

---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Platform Hardening & Quality
status: planning
stopped_at: Completed 87-mic-dictation-via-web-speech-api 87-02-chat-input-mic-integration-PLAN.md
last_updated: "2026-05-02T00:05:00Z"
last_activity: "2026-05-02 — Phase 87 COMPLETE (2/2 plans, HOTFIX-05). 87-01 rewrote useSpeechRecognition.ts as a Web Speech API wrapper (~190 lines, public 11-field shape preserved, 8/8 unit tests GREEN); 87-02 wired ChatInterface for live interim streaming (suffix-ref pattern), editable textarea mid-dictation (readOnly removed), mid-dictation Enter/Send (stopRecording flushes interim into final via skipNextSpeechTranscriptCommitRef), simplified Recording Indicator. 6 new HOTFIX-05 tests GREEN incl. SC5 boundary guard-rail (chat mic does not call useVoiceSession). useVoiceSession.ts and app/routers/voice_session.py UNCHANGED line-for-line; Phase 84 half-duplex gate intact. Manual UAT pending in 87-MANUAL-UAT.md across Chrome/Edge/Safari/Firefox/iOS Safari + brain-dump boundary smoke."
progress:
  [██████████] 99%
  completed_phases: 13
  total_plans: 27
  completed_plans: 26
  percent: 99
---

---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Platform Hardening & Quality
status: planning
stopped_at: Completed 89-knowledge-vault-auto-sync 89-01-document-service-vault-wiring-PLAN.md
last_updated: "2026-05-01T21:00:05.762Z"
last_activity: "2026-05-01 — 89-01-document-service-vault-wiring shipped (HOTFIX-07): DocumentService._upload_document now performs best-effort Knowledge Vault ingest after media_assets upsert; module-scope imports for ingest_document_content + extract_text_from_bytes + ExtractionError at app/services/document_service.py:27-31; new ingest block at lines 448-496; PDFs use real pypdf-extracted text, PPTX uses synthetic descriptor; standardized metadata schema (asset_id, asset_type, bucket_id, file_path, template, file_type, session_id). 5 new TestVaultAutoIngest tests GREEN; all 19 DocumentService tests GREEN. Commits cefcd73f (test) + d0d30646 (feat). Ran in parallel with 89-02 (disjoint files, no merge conflict)."
progress:
  total_phases: 15
  completed_phases: 12
  total_plans: 27
  completed_plans: 25
  percent: 98
---

---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Platform Hardening & Quality
status: planning
stopped_at: Completed 89-knowledge-vault-auto-sync 89-01-document-service-vault-wiring-PLAN.md
last_updated: "2026-05-01T20:53:51Z"
last_activity: "2026-05-01 — 89-01-document-service-vault-wiring shipped (HOTFIX-07): DocumentService._upload_document now performs best-effort Knowledge Vault ingest after media_assets upsert; module-scope imports for ingest_document_content + extract_text_from_bytes + ExtractionError at app/services/document_service.py:27-31; new ingest block at lines 448-496; PDFs use real pypdf-extracted text, PPTX uses synthetic descriptor; standardized metadata schema (asset_id, asset_type, bucket_id, file_path, template, file_type, session_id). 5 new TestVaultAutoIngest tests GREEN; all 19 DocumentService tests GREEN. Commits cefcd73f (test) + d0d30646 (feat). Ran in parallel with 89-02 (disjoint files, no merge conflict)."
progress:
  [██████████] 98%
  completed_phases: 12
  total_plans: 27
  completed_plans: 24
---

---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Platform Hardening & Quality
status: planning
stopped_at: Completed 86-document-generation-skills-exposure 86-01-document-gen-skills-exposure-PLAN.md
last_updated: "2026-05-01T01:40:14Z"
last_activity: 2026-05-01 — 86-01-document-gen-skills-exposure shipped (HOTFIX-04 GREEN). Executive Agent now imports DOCUMENT_GEN_TOOLS and spreads them into _EXECUTIVE_TOOLS; executive_instruction.txt section 23 names both tools and all 5 PDF templates; CONTENT_DIRECTOR_INSTRUCTION names PDF+PowerPoint capability. 7 wiring tests GREEN. Manual UAT scaffold awaits real-Gemini run.
progress:
  total_phases: 15
  completed_phases: 12
  total_plans: 23
  completed_plans: 22
---

---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Platform Hardening & Quality
status: planning
stopped_at: Completed 88-chat-and-workspace-persistence 88-04-streaming-indicator-PLAN.md
last_updated: "2026-05-01T01:35:33.266Z"
last_activity: 2026-05-01 — Phase 88 COMPLETE (4/4 plans). 88-04-streaming-indicator shipped (TabStrip indicators prop + ChatInterface useMemo + sonner cap toast; 5 new vitest tests; all 11 ROADMAP success criteria mapped)
progress:
  total_phases: 15
  completed_phases: 11
  total_plans: 22
  completed_plans: 21
---

---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Platform Hardening & Quality
status: planning
stopped_at: Completed 88-chat-and-workspace-persistence 88-03-tab-strip-ui-PLAN.md
last_updated: "2026-05-01T01:15:41.237Z"
last_activity: 2026-05-01 — 88-02-tab-state complete (openTabIds + openTab/closeTab + tier-derived cap; 9 new vitest tests GREEN)
progress:
  total_phases: 15
  completed_phases: 10
  total_plans: 21
  completed_plans: 20
---

---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Platform Hardening & Quality
status: planning
stopped_at: Completed 85-render-sse-timeout 85-01-sse-timeout-extension-PLAN.md
last_updated: "2026-05-01T00:53:12.082Z"
last_activity: 2026-04-30 — 85-01-sse-timeout-extension complete (SSE_MAX_DURATION_S=570 in both admin/chat.py + fast_api_app.py)
progress:
  total_phases: 15
  completed_phases: 10
  total_plans: 21
  completed_plans: 19
  percent: 98
---

---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Platform Hardening & Quality
status: planning
stopped_at: Completed 85-render-sse-timeout 85-01-sse-timeout-extension-PLAN.md
last_updated: "2026-05-01T00:46:40Z"
last_activity: 2026-04-30 — Phase 85 SSE timeout raised to 570s in both admin/chat.py and fast_api_app.py via SSE_MAX_DURATION_S env var
progress:
  [██████████] 98%
  completed_phases: 10
  total_plans: 21
  completed_plans: 18
---

---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Platform Hardening & Quality
status: planning
stopped_at: Completed 88-chat-and-workspace-persistence 88-01-persistence-reconciliation-PLAN.md
last_updated: "2026-04-30T20:55:20.915Z"
last_activity: 2026-04-26 — Roadmap written, 7 phases (76-82), 17/17 requirements mapped
progress:
  total_phases: 15
  completed_phases: 9
  total_plans: 20
  completed_plans: 17
---

---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Platform Hardening & Quality
status: planning
stopped_at: Completed 84-voice-gate-deadlock-fix 84-01-noise-floor-cutoff-PLAN.md
last_updated: "2026-04-30T20:02:20.441Z"
last_activity: 2026-04-26 — Roadmap written, 7 phases (76-82), 17/17 requirements mapped
progress:
  total_phases: 15
  completed_phases: 9
  total_plans: 20
  completed_plans: 16
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

See: .planning/PROJECT.md (updated 2026-05-08)

**Core value:** Users describe what they want in natural language and the system autonomously generates, manages, and grows their business operations
**Current focus:** v12.0 Agent System Quality Upgrade — convert single-shot agents into 30-60min-capable executive operators with persistent memory and tangible deliverables; derived from 2026-05-08 audit
**Queued next:** v13.0 Authentication & Connections Hardening — fix OAuth security, Google Workspace credential bridge, per-platform posting bugs (LinkedIn/Twitter/YouTube/TikTok/Facebook); derived from 2026-05-08 social/Workspace audit. **Roadmap defined 2026-05-08** with 8 phases (101-108) and 22 mapped requirements (5 AUTH + 6 WORKSPACE + 9 POST + 4 HYGIENE) — observable success criteria written, traceability populated, awaiting v12.0 completion before plan-phase.

## Current Position

Milestone: v12.0 Agent System Quality Upgrade — STARTED 2026-05-08, ROADMAP COMPLETE 2026-05-08
Phase: 95 of 100 (Phase A — Bug-Fix Sprint) — pending plan
Status: v12.0 roadmap written. 6 phases (95-100) declared with goals + observable success criteria + 1:1 REQ-ID mappings + dependency chain. Coverage 100% (44/44 v12.0 requirements). v11.0 (App Builder Beta, phases 90-94) marked DEFERRED to v14.0 in ROADMAP — plans never written, scope preserved verbatim. **v13.0 (Authentication & Connections Hardening, phases 101-108) ROADMAP DEFINED 2026-05-08** — 8 phases with formal Goals, Requirements, and 2-5 observable Success Criteria each; 22/22 REQ-IDs mapped (AUTH-01..05 → 101, WORKSPACE-01..06 → 102, POST-01..03 → 103, POST-04..06 → 104, POST-07 → 105, POST-08 → 106, POST-09 → 107, HYGIENE-01..04 → 108); sequencing 101 → 102/103 → 104-107 (parallel) → 108. Ready to break down Phase 95 via /gsd:plan-phase 95.
Last activity: 2026-05-08 — v13.0 ROADMAP written. Inserted as a `<details><summary>📋 v13.0 Authentication & Connections Hardening (Phases 101-108) — QUEUED 2026-05-08</summary>` block after the v12.0 section. Each phase includes Goal, Requirements (REQ-IDs), Success Criteria (observable user behaviors / testable code states), Depends on, Provenance: 2026-05-08 audit, Plans: 0 plans (TBD). Top-level Milestones list updated: v11.0 status changed to "DEFERRED to v14.0", v13.0 added as 📋 queued. v11.0 phase rows in progress table updated from "Deferred to v13.0" → "Deferred to v14.0". Progress table appended with rows 101-108. REQUIREMENTS.md v13.0 traceability table populated with all 22 REQ-ID → Phase mappings (status: Pending). v11.0 BETA-* traceability rows preserved unchanged per instruction (do NOT touch v10.0/v11.0/v12.0 traceability sections); BETA-* coverage summary updated to "Deferred to v14.0".

Progress: [░░░░░░░░░░] 0% (v12.0 roadmap done, first phase plan pending; v13.0 roadmap defined, awaiting v12.0 completion)

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
| Phase 83-document-upload-bypass P02 | 26 min | 3 tasks tasks | 2 files files |
| Phase 84-voice-gate-deadlock-fix P01 | 7 min | 2 tasks | 4 files |
| Phase 88-chat-and-workspace-persistence P01 | 18 min | 3 tasks tasks | 4 files files |
| Phase 85-render-sse-timeout P01 | 17 min | 2 tasks | 7 files |
| Phase 88-chat-and-workspace-persistence P02 | 22 min | 4 tasks tasks | 3 files files |
| Phase 88-chat-and-workspace-persistence P03 | 15min | 3 tasks | 5 files |
| Phase 86-document-generation-skills-exposure P01 | 9 min | 2 tasks | 5 files |
| Phase 89-knowledge-vault-auto-sync P01 | 6 | 2 tasks | 2 files |
| Phase 89-knowledge-vault-auto-sync P02 | 6 min | 2 tasks | 3 files |
| Phase 87-mic-dictation-via-web-speech-api P01 | 31 min | 2 tasks | 4 files |
| Phase 87-mic-dictation-via-web-speech-api P02 | 14 min | 2 tasks | 3 files |
| Phase 89-knowledge-vault-auto-sync P03 | 5min | 1 tasks | 2 files |
| Phase 104 P02 | 30m | 2 tasks | 3 files |
| Phase 106 P01 | 25min | 2 tasks | 2 files |

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
- [Phase 83-document-upload-bypass]: data-testid='chat-send-button' added to icon-only Send button as the canonical selector for behavior tests; existing 'disables input when streaming' test was assertion-stale (textarea is gated by isUploading/isSpeechTranscribing only; streaming swaps Send for Stop) and was rewritten to match production behavior
- [Phase 83-document-upload-bypass]: Smart-upload deletion is purely subtractive (~225 lines removed, ~16 added) in ChatInterface.tsx; SmartUploadToast.tsx, /api/upload/smart proxy, and backend smart_upload endpoint are all kept on disk per RESEARCH Open Questions and ROADMAP success criterion 4 — cleanup deferred to a follow-up PR for revert isolation
- [Phase 84-voice-gate-deadlock-fix]: REJECTED SC4 multi-condition gate widening; implemented noise-floor RMS cutoff (0.003 default, NEXT_PUBLIC_VOICE_NOISE_FLOOR_RMS override) inside forwardInputChunk AFTER the half-duplex gate — SC1+SC2+SC3 satisfied without widening the gate; Test 5 guard-rail fails CI if any future PR widens it
- [Phase 88-chat-and-workspace-persistence]: Used storage event over BroadcastChannel for cross-tab sync — last-write-wins acceptable per ROADMAP, zero new browser API surface
- [Phase 88-chat-and-workspace-persistence]: setVisibleSessionIdRaw (not the persisting setter) inside the storage handler — avoids feedback loop with localStorage.setItem
- [Phase 88-chat-and-workspace-persistence]: Synthetic StorageEvent dispatch for cross-tab vitest — jsdom does not fire storage from same-window setItem (W3C spec compliant)
- [Phase 85-render-sse-timeout]: SSE_MAX_DURATION_S env var raised from 300 → 570 (NOT 600 — 30s safety margin under Cloud Run's 600s --timeout so SSE wins the race and emits the friendly error instead of raw 504). Single env var governs both app/routers/admin/chat.py:_SSE_MAX_DURATION_S and app/fast_api_app.py:SSE_MAX_DURATION_S. SC1 literally said "≥ 600s"; we chose 570s — engineering tradeoff documented in plan SUMMARY and ROADMAP. SC4 (>570s renders) deferred to async-job-queue work, documented in deferred-items.md.
- [Phase 88-chat-and-workspace-persistence]: Plan 88-02: Consumer-side provider override pattern for tier-derived tab cap — useChatSession() reads tier from useSubscription (only available in dashboard tree) and pushes derived cap into root-tree SessionControlProvider via setTabCap; provider defaults to TAB_CAP_FREE=5 as the safe floor for non-dashboard consumers
- [Phase 88-chat-and-workspace-persistence]: Plan 88-02: Cap throw is synchronous BEFORE setOpenTabIds (not inside the setState updater) — React 18+ may re-run updaters during reconciliation, causing throws to fire from unexpected stack frames; openTab reads openTabIds from render closure for the cap-precondition
- [Phase 88-chat-and-workspace-persistence]: Plan 88-02: closeTab computes nextOpenTabIds from render closure (NOT from setState updater's prev) so promotion/fallback logic sees a deterministic value before React commits the batched state update
- [Phase 88-chat-and-workspace-persistence]: Plan 88-03: Stateless prop-driven TabStrip — no useState/useEffect/useContext, props-only contract; tests run without harness wrapping in 232ms; Plan 88-04 can add per-tab streaming/unread state via additive TabStripTab fields without refactoring the contract
- [Phase 88-chat-and-workspace-persistence]: Plan 88-03: Two-row header layout — agent identity row + TabStrip row inside a parent border-b wrapper; legacy + button at line ~1167 deleted; Plus icon dropped from lucide-react import; TabStrip's trailing + is the canonical new-chat affordance
- [Phase 88-chat-and-workspace-persistence]: Plan 88-03: 'New chat' fallback for tab labels covers the createNewChat → first-message → server-side title → refreshSessions latency window (~2-8s); without this, brand-new tabs would render with empty labels until the round-trip completes
- [Phase 88-chat-and-workspace-persistence]: Plan 88-03: Hover-reveal close X (opacity-0 group-hover:opacity-100, VS Code/Chrome/Firefox UX) + native HTML disabled attribute on the trailing + (browser-native click suppression + screen-reader 'button disabled' announcement); production toast for cap-reached deferred to Plan 88-04
- [Phase 88-chat-and-workspace-persistence]: Plan 88-04: Sparse indicator map (Record<id, state>) over per-tab state field — keeps active-tab override trivial AND additive prop (Plan 88-03 callers don't pass anything)
- [Phase 88-chat-and-workspace-persistence]: Plan 88-04: Indicator clear path leverages existing visibleSessionId-keyed useEffect (Phase 83) — handleTabSwitch does NOT add duplicate updateSessionState({hasUnread:false}); avoids race AND wasted work
- [Phase 88-chat-and-workspace-persistence]: Plan 88-04: UI-layer cap-toast — SessionControlContext.selectChat rethrows TabCapReachedError instead of console.warn; ChatInterface (UI layer) catches and surfaces sonner toast; data layer stays free of UI concerns (no sonner import)
- [Phase 88-chat-and-workspace-persistence]: Plan 88-04: vi.importActual passthrough mock for SessionControlContext in chatHarness — keeps production TabCapReachedError type-matching across the mock boundary; alternative (manual class re-export from mock factory) is brittle to drift
- [Phase 86-document-generation-skills-exposure]: Plan 86-01: Verbatim prose from research § Recommended Implementation copied without paraphrase — section 23 in executive_instruction.txt + ## BRANDED DOCUMENT GENERATION block in CONTENT_DIRECTOR_INSTRUCTION; ruff I001 autofix moved document_gen import alphabetically after deep_research (plan suggested between decision_journal and deep_research; ruff order is canonically correct)
- [Phase 86-document-generation-skills-exposure]: Plan 86-01: SC4/SC5 verification = unit (mechanical proxy via {status, widget, fileType} shape with monkeypatched DocumentService) + manual UAT (real-Gemini routing in 86-MANUAL-UAT.md); LLM-mocked integration tests rejected as brittle — research § Validation Architecture
- [Phase 86-document-generation-skills-exposure]: Plan 86-01: sales_proposal docstring fix (document_gen.py:53-65 missing 5th template) DEFERRED — runtime works (VALID_TEMPLATES check passes), only the LLM-facing description is stale; touches a 4th file outside plan's files_modified; defer to follow-up phase per scope discipline
- [Phase 89-knowledge-vault-auto-sync]: Plan 89-01: Module-scope import for ingest_document_content (single stable patch target); verified safe (knowledge_vault.py does NOT import document_service.py)
- [Phase 89-knowledge-vault-auto-sync]: Plan 89-01: PDF ingest uses real pypdf-extracted text via existing extract_text_from_bytes; PPTX uses synthetic descriptor (transcription explicitly out of scope per CONTEXT)
- [Phase 89-knowledge-vault-auto-sync]: Plan 89-02: Top-level document_type ('video'/'image') promoted at all 3 shipped ingest call sites; nested metadata.asset_type retained for legacy readers; standardized metadata schema applied (asset_id, bucket_id, file_path, prompt, plus type-specific fields)
- [Phase 89-knowledge-vault-auto-sync]: Plan 89-01: Outer try/except Exception wraps both extraction AND ingest so any unexpected error stays non-blocking; inner try/except ExtractionError lets supported-format parse failures fall back to synthetic descriptor without losing the WARNING log
- [Phase 89-knowledge-vault-auto-sync]: Plan 89-02: media.py video-fallback site uses 'file_path' as metadata KEY but local 'storage_path' as VALUE — local 'file_path' is unbound at media.py:861 (verified at media.py:815); writing 'file_path: file_path' would have raised NameError at runtime
- [Phase 89-knowledge-vault-auto-sync]: Plan 89-01: Empty extracted text ('') falls back to synthetic descriptor — sending empty content to ingest_document_content would early-return success=False; descriptor preserves asset_id/title link for vault search
- [Phase 89-knowledge-vault-auto-sync]: Plan 89-02: Director media_metadata gap closed by injecting render_backend, bucket_id, file_path explicitly at the ingest call site (these three were absent from media_metadata at director_service.py:514-522); spread order **media_metadata last to defend against future overlapping keys
- [Phase 89-knowledge-vault-auto-sync]: Plan 89-02: New tests in tests/unit/test_phase89_media_tagging.py (3 cases) over appending to test_media_routing.py — focused fixtures for _schedule_best_effort_task interception; dedicated _make_supabase MagicMock with both insert+upsert paths
- [Phase 89-knowledge-vault-auto-sync]: Plan 89-03: Test 4 reframed to real production-call inspection (generate_image + generate_video) over fixture-shape inspection — provides cross-plan backward-compat protection for nested metadata.asset_type that survives deletion or weakening of 89-02's per-plan tests
- [Phase 89-knowledge-vault-auto-sync]: Plan 89-03: Round-trip proxy pattern for write-then-search contracts — capture writer kwargs, feed identical dict into searcher mock; proves boundary contract holds without spinning up a real database
- [Phase 89-knowledge-vault-auto-sync]: Plan 89-03: Imports search_business_knowledge from app.agent (canonical at app/agent.py:131); verified app.orchestration.knowledge_tools has only 'add' tools and no search function
- [Phase 104]: Twitter v2 chunked video upload sleep ordering: sleep BEFORE each STATUS GET (honors API check_after_secs)

### Roadmap Evolution

- Phase 83 added: Document Upload Bypass — production hotfix bug 1/7
- Phase 84 added: Voice Gate Deadlock Fix — production hotfix bug 2/7
- Phase 85 added: Render SSE Timeout — production hotfix bug 3/7
- Phase 86 added: Document Generation Skills Exposure — production hotfix bug 4/7
- Phase 87 added: Mic Dictation via Web Speech API — production hotfix bug 5/7
- Phase 88 added: Chat and Workspace Persistence — production hotfix bug 6/7
- Phase 89 added: Knowledge Vault Auto Sync — production hotfix bug 7/7
- v13.0 ROADMAP defined 2026-05-08: 8 phases (101 Security Hardening for connected_accounts, 102 Google Workspace Credential Bridge, 103 LinkedIn Posting Fix, 104 Twitter Media Upload Fix, 105 YouTube Resumable Upload, 106 TikTok Publish Completion, 107 Facebook Video Resumable Upload, 108 Hygiene & Coverage). Sequencing 101 → 102/103 → 104/105/106/107 (parallel) → 108. Coverage 22/22 REQ-IDs. v11.0 BETA-* deferred from v13.0 → v14.0.

### Pending Todos

None yet.

### Blockers/Concerns

- PERF-01 (~20 files): largest single item in milestone; plan-phase should split into 2 plans by file batch
- ARCH-04 (OpenAPI codegen): requires CI pipeline changes — may need coordination with existing GitHub Actions setup
- Pre-existing failure in frontend/src/components/chat/ChatInterface.test.tsx — 4 tests crash with "useSessionControl must be used within a SessionControlProvider" due to ChatInterface.tsx adding 11 module-scope hooks after the test was written. Plan 01 cannot fix this (vi.mock is per-file). Documented in .planning/phases/83-document-upload-bypass/deferred-items.md; Plan 02 will adopt the harness inside ChatInterface.test.tsx to resolve.

## Session Continuity

Last session: 2026-05-09T02:44:52.628Z
Stopped at: Completed 106-01-status-polling-PLAN.md
Resume file: None
