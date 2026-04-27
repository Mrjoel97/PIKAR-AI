# App Builder Autopilot — Design

**Date:** 2026-04-27
**Status:** Draft, pending user review
**Owner:** Executive agent + new `AppBuilderOrchestrator`

---

## Goal

After a user completes the 5-question wizard at the start of a new app project, the agent autonomously drives the entire build flow (research → design brief → screens → ship) and only pauses for meaningful user decisions. The user can stay in chat and watch progress, or interact with the embedded canvas directly — both surfaces stay in sync.

## Non-Goals

- Running multiple autopilot sessions for the same user concurrently. One project at a time.
- Cross-session notifications (no email or push when a paused build is waiting).
- Replacing the manual stage-by-stage flow. Manual mode continues to work; autopilot is opt-in for new projects.
- Re-running the questioning wizard from chat. The wizard remains the canvas's responsibility.

## User-facing behavior

1. User opens the canvas widget in the workspace and answers the 5 questioning questions.
2. On the 5th answer, the canvas posts to `/app-builder/<id>/start-autopilot` with the brief. The chat agent says: *"Got your brief. I'm running research now and will pause when I need your input."*
3. Research runs (existing `run_design_research` SSE stream powers the canvas's research view). Chat agent posts a single status when research starts and another when results are ready.
4. **Pause A — Design brief approval.** Canvas shows the design system + sitemap (existing UI). Chat agent says: *"Design brief is ready. Approve in the canvas or tell me what to change."* User approves via the canvas's "Approve & Generate Build Plan" button. (User edits in canvas before approving — same as today.)
5. Build plan generates automatically; canvas advances to the building stage.
6. For each screen in the build plan:
   - Orchestrator triggers screen generation (3 variants).
   - Chat agent posts: *"Generating screen X of N: <screen name>"*.
   - **Pause B — Variant pick.** Canvas's `VariantComparisonGrid` shows 3 variants. User clicks one. Chat agent posts a brief acknowledgment.
   - **Pause C — Per-screen approval.** Canvas's `ApprovalCheckpointCard` is shown. User clicks "Approve". Orchestrator continues to next screen.
7. After the last screen is approved, orchestrator advances stage to `verifying`. Multi-page review UI appears in canvas.
8. Orchestrator advances stage to `shipping` automatically.
9. **Pause E — Ship target.** Chat agent posts a quick-reply widget: *"All screens approved. How do you want to ship?"* with buttons for React / PWA / Capacitor / Video. User clicks one.
10. Ship runs. On success, chat agent posts the download/preview link. Canvas's `done` page shows.

If the user closes the browser at any pause: state is in the DB, autopilot waits indefinitely. When the user reopens the canvas later (from chat or directly), the canvas routes to the current stage and the pause UI is still there.

## Architecture

### Components

1. **`AppBuilderOrchestrator`** — new service at `app/services/app_builder_orchestrator.py`. A per-project asyncio task driven by the project's `stage` and a new `autopilot_status` column. Owns the state machine, calls existing services (`run_design_research`, `_generate_build_plan`, `generate_screen_variants`, `build_all_pages`, `ship_project`), and pushes events through the existing chat SSE pipeline.
2. **`app_projects.autopilot_status` column** — new SQL migration adds a TEXT column with values: `idle`, `running`, `paused_brief`, `paused_variant`, `paused_screen`, `paused_ship`, `failed`, `done`. Defaults to `idle`. The orchestrator transitions this column atomically as it moves through stages.
3. **`app_projects.autopilot_session_id` column** — TEXT, nullable. Stores the chat session ID that started autopilot, so the orchestrator knows which session to narrate into.
4. **New API endpoints** under `app/routers/app_builder.py`:
   - `POST /app-builder/<id>/start-autopilot` — called by canvas when the 5th wizard answer is submitted. Body includes `session_id` (chat session for narration). Sets `autopilot_status=running`, kicks off the orchestrator task. Idempotent: a 409 if autopilot is already active for this project.
   - `POST /app-builder/<id>/resume-autopilot` — called by canvas after each pause is resolved (brief approved, variant picked, screen approved, ship target chosen). Resumes the orchestrator from its current paused state.
   - `GET /app-builder/<id>/autopilot-status` — returns current autopilot state for the canvas to render the right UI.
5. **New agent tool** `start_app_builder_autopilot(project_id, session_id, brief)` — only callable by Executive. Wraps the `start-autopilot` endpoint. Used when the chat agent receives the `app_builder.questioning_complete` signal from the canvas via a postMessage relay.
6. **Canvas → chat bridge** — when the canvas's iframe wants to talk to the chat agent (e.g., to signal questioning is done, or to acknowledge a variant pick), it uses `window.parent.postMessage`. The parent (`AppBuilderCanvasWidget`) listens and converts these into chat agent tool calls. This is the only new mechanism we add on the frontend.

### State machine

```
idle  ──(start-autopilot)──▶ running
running ──(research done)──▶ paused_brief
paused_brief ──(approve)──▶ running ──(generate screen N)──▶ paused_variant
paused_variant ──(pick)──▶ paused_screen
paused_screen ──(approve)──▶ running
                              │ (more screens)
                              └─▶ paused_variant (loop)
                              │ (last screen)
                              └─▶ paused_ship
paused_ship ──(target chosen)──▶ running ──(ship done)──▶ done

any state ──(unrecoverable error)──▶ failed
```

### Communication channels

- **Chat narration**: orchestrator publishes events into the same SSE pipeline that already powers `/a2a/app/run_sse` for the recorded `autopilot_session_id`. Each event renders as one agent text message plus an optional widget update. The exact wiring (whether we add a publish-to-session helper, reuse an existing bus, or have the orchestrator drive a synthetic agent turn) is decided during implementation planning — there is no `agent_event_bus.py` today; the closest analog is `research_event_bus.py` in `app/services/`, which we may model the implementation on or extend.
- **Canvas state sync**: the canvas already polls `getProject(projectId)` on layout mount. We add a small polling loop (every 3s while autopilot is active) on the `autopilot-status` endpoint so the canvas re-renders when the orchestrator transitions stages. (Alternative: SSE channel for canvas. Polling is simpler for now and the data is small.)

## Data model changes

```sql
-- supabase/migrations/<timestamp>_app_projects_autopilot.sql
ALTER TABLE app_projects
  ADD COLUMN autopilot_status TEXT NOT NULL DEFAULT 'idle'
    CHECK (autopilot_status IN ('idle','running','paused_brief','paused_variant','paused_screen','paused_ship','failed','done'));
ALTER TABLE app_projects
  ADD COLUMN autopilot_session_id TEXT;
ALTER TABLE app_projects
  ADD COLUMN autopilot_error TEXT;
```

No row-level security changes needed; existing project-owner RLS covers these columns.

## Error handling

- **Recoverable failure** (transient Stitch error, model timeout): orchestrator retries the failing step up to 3 times with exponential backoff. If still failing, transitions to `failed`, posts a chat message *"I hit an error generating screen X: <message>. You can retry from the canvas."*, leaves the canvas in its last good state.
- **Unrecoverable failure** (auth error, suspended project, missing API key): immediate transition to `failed` with the error in `autopilot_error`. Chat message includes a recovery suggestion.
- **User abandons mid-build**: no special handling; autopilot waits at the current pause indefinitely. State is in DB.
- **Browser closes mid-research / mid-build**: orchestrator is server-side, continues running. Reopening the canvas resumes from current stage.
- **User triggers manual action in canvas while autopilot is `running`**: the next orchestrator step checks `autopilot_status` before taking action; if the user manually advanced the stage, the orchestrator transitions to `failed` with a clean message *"You took control of the build — I'll stop autopilot. Restart it from chat any time."*

## Testing approach

- **Unit tests** for `AppBuilderOrchestrator` state transitions (mocked services). One test per transition.
- **Unit tests** for the new endpoints — auth, idempotency on start, status JSON shape.
- **Integration test** end-to-end: spin up a project, call start-autopilot with a stub brief, mock the screen generation service to return canned variants, drive through all pauses, assert final stage is `done`.
- **Frontend test** for the postMessage bridge in `AppBuilderCanvasWidget` — mocks `window.parent.postMessage` and asserts the chat tool call shape.

Mocks must NOT replace the real DB. Integration test uses the local Supabase via `supabase db reset --local`.

## Open questions

None blocking. The two we discussed are resolved:

- Variant pick UX: **in canvas** (no duplicate widget in chat).
- Ship target: **pause + ask** (do not auto-default to React).

## Out of scope

- Multi-project autopilot (one per user).
- Notifications when a paused build is waiting (email/push).
- Custom ship targets in autopilot (user can run `ship_project` manually for non-React targets after completion).
- Auto-restart on Cloud Run cold start mid-orchestration. The asyncio task lives in process memory; if the instance is recycled, the orchestrator resumes from DB state when the next status check or resume call comes in.
