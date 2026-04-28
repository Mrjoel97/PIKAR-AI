# Workspace as Agent Canvas — Plan Draft

> **Status:** DRAFT FOR REVIEW. Do not execute yet — open questions in §3 must be answered first.
>
> **Author:** Claude (auto-drafted 2026-04-28 from conversation with PIKAR AI)
> **Related memory:** project_executive_enhancement.md, project_admin_panel.md (workspace UX referenced as gap)

---

## 1. Goal

Make the *agent workspace* — the surface a user actually works on next to the chat panel — feel like a clean, agent-controlled canvas instead of a static dashboard:

1. **Idle state** (no active prompt, fresh chat): show only the **Brief Card** + **Onboarding Tasks Checklist**. Hide KPI grid, Founder Board, Launchpad, default persona widget cards.
2. **Engaged state** (user has prompted the agent in the current session): hide brief + checklist, show the agent's live work — activity stream, thinking traces, generated artifacts (charts, briefings, plans, video specs, etc.).
3. **New chat reset**: workspace returns to idle state automatically.
4. **Agents get richer levers** to shape what the user sees on canvas — not just "render this widget" but also "set this layout," "highlight this artifact," "request approval inline," "replace the active item," and read back what the user did to it.

This plan covers two phases. **Phase 1** is a UI-only refactor that delivers (1)–(3) and is low-risk. **Phase 2** is a contract change between agents and the workspace that delivers (4) and is where most of the architecture work lives.

---

## 2. Architecture Summary

### What changes

**Phase 1 — UI gating**

- Lift the **Brief Card** out of `CommandCenter.tsx` into a standalone `<DashboardBriefCard persona={...} />` so it can render independently of the rest of the command-centre stack.
- In `PersonaDashboardLayout.tsx`, add an `isAgentEngaged` signal computed from:
  - `useChatSession().currentSessionId` has at least one user message, **or**
  - `WORKSPACE_ITEMS_EVENT` has produced ≥ 1 item this session, **or**
  - `WORKSPACE_ACTIVITY_EVENT` is in `phase: 'running'`.
- When `!isAgentEngaged && !isWorkspaceSurface`: render only `<DashboardBriefCard /> + <OnboardingChecklist />`. Skip session widgets, pinned widgets, default persona widgets, and `<CommandCenter />`.
- When `isAgentEngaged && !isWorkspaceSurface`: render `<AgentWorkArea />` (a thin wrapper that re-uses ActiveWorkspace's renderers — activity panel + workspace canvas + layout controls). Skip everything else.
- When `createNewChat()` fires: reset local widget state and the engaged flag for the *new* session id; brief + checklist re-appear.
- The dedicated `/dashboard/workspace` page (`surface="workspace"`) gains the same `<DashboardBriefCard /> + <OnboardingChecklist />` empty-state above ActiveWorkspace, so it matches the persona pages.

**Phase 2 — Agent ↔ Workspace contract**

Introduce a single typed `WorkspaceCommand` SSE event the agent can emit deliberately, and a `workspace_event` POST channel the UI uses to feed user actions back to the agent. Replace today's heuristic `save_widget` / `focus_widget` / `workspace_activity` parsing in `frontend/src/lib/sseParser.ts` with explicit agent-emitted commands while keeping the existing parsers as fallback for legacy outputs.

```
┌──────────────┐  WorkspaceCommand   ┌──────────────────┐
│  ADK Agent   │─────────(SSE)─────▶│  ActiveWorkspace │
│              │◀──────(tool)───────│  (canvas)        │
└──────────────┘  workspace_event    └──────────────────┘
```

**Outcomes:**

- Agents can declare intent: `{action: 'set_layout', mode: 'compare'}`, `{action: 'focus', item_id}`, `{action: 'highlight', region}`, `{action: 'request_approval', deliverable_id}`, `{action: 'replace_active', widget}`.
- UI emits back: `{event: 'item_closed', item_id}`, `{event: 'item_edited', item_id, diff}`, `{event: 'approval_decision', decision, comment}`. Agent receives these via a `read_workspace_events` tool call response on its next turn.
- Resumed sessions: when the agent re-enters a session, its memory contract includes `active_workspace_items` so it knows what's already on canvas.

### What stays the same

- Existing `WIDGET_CHANGE_EVENT` / `WORKSPACE_ITEMS_EVENT` / `WORKSPACE_ACTIVITY_EVENT` browser CustomEvents — they keep working as the in-process bus.
- `WidgetDisplayService` localStorage layer + Supabase `workspace_items` table — no schema change required for Phase 1.
- ChatInterface, SSE endpoint `POST /a2a/app/run_sse`, ADK agent code paths.
- `/dashboard/workspace` route — still works, gets a friendlier empty state.

---

## 3. Open Decisions (please answer before we execute)

1. **Brief Card persona match.** Today the brief is auto-derived from `getDashboardSummary(persona)` (`CommandCenter.tsx:144`). On a fresh user with no data, body is generic boilerplate. **Q:** keep that, or drive the brief from the OnboardingChecklist progress (e.g. "Complete your profile to unlock daily briefings")? *Recommendation:* keep `getDashboardSummary` as source of truth, add a `fallback` prop for empty-state copy.

2. **What counts as "engaged"?**
   - (a) **First user message ever in this session** (sticky — once engaged, stays engaged until new chat). *Recommendation.*
   - (b) **Streaming-only** — brief returns whenever the agent finishes responding.
   - (c) **Manual toggle** — user clicks "Show dashboard" to bring brief back without starting a new chat.
   *Recommendation:* (a) primary + (c) as an escape hatch via the existing "Clear workspace" button on ActiveWorkspace, which would also exit engaged mode.

3. **Pinned widgets — where do they live now?**
   - Today they render *between* OnboardingChecklist and CommandCenter on persona pages.
   - **Q:** when engaged, do pinned widgets disappear (clean canvas) or stay visible above the agent work area? *Recommendation:* disappear. Surface them via a "Pinned" tray in the chat panel header instead.

4. **Default persona widget sections** (revenue_chart, morning_briefing, kanban_board) — currently shown only when user has zero pinned widgets and hasn't dismissed defaults. **Q:** delete these from the persona dashboard surface entirely, or keep them as part of the idle state? *Recommendation:* delete from idle state. They competed with the brief for attention and were the original source of "command-centre cards leaking into workspace."

5. **Phase 2 scope.** The agent-side contract requires backend work (ADK callbacks, new tool, session-state field). **Q:** ship Phase 1 now, then decide on Phase 2 after using Phase 1 for a week? *Recommendation:* yes — Phase 1 unblocks the visible UX problem, Phase 2 is a much bigger surface area.

---

## 4. Phase 1 — File Plan

**Create:**
- `frontend/src/components/dashboard/DashboardBriefCard.tsx` — standalone brief card (extracted from `CommandCenter.tsx:391–426`).
- `frontend/src/components/dashboard/AgentWorkArea.tsx` — thin engaged-state wrapper. Renders `WORKSPACE_ACTIVITY_EVENT` activity stream + workspace canvas via existing `WidgetContainer`. Re-uses `ActiveWorkspace`'s `mergeWorkspaceItems`, `renderWorkspaceCanvas`, `renderWorkspaceControls` — refactor those into shared helpers under `frontend/src/components/workspace/`.
- `frontend/src/hooks/useAgentEngagement.ts` — hook that returns `{isEngaged, reset}` based on session messages + workspace events. Single source of truth so we don't recompute in three places.

**Modify:**
- `frontend/src/components/dashboard/PersonaDashboardLayout.tsx` — add engagement gating around the four content blocks (lines 343, 359, 390, 422) and replace the fall-through `<CommandCenter />` (line 462) with the brief/work-area split.
- `frontend/src/components/dashboard/ActiveWorkspace.tsx` — extract render helpers into `frontend/src/components/workspace/WorkspaceCanvas.tsx`. Add `<DashboardBriefCard /> + <OnboardingChecklist />` to the empty state (replaces the "No agent workspace items yet" placeholder block at lines 669–689).
- `frontend/src/components/dashboard/CommandCenter.tsx` — keep KPI/Launchpad/Founder Board for users who navigate to `/dashboard/command-center` directly. Remove brief from this component (now lives in `DashboardBriefCard`); CommandCenter imports and renders `<DashboardBriefCard />` at the same spot for the standalone command-centre route.
- `frontend/src/components/dashboard/OnboardingChecklist.tsx` — remove the `dashboardOnly` assumption baked into copy/CTAs; verify it works inside the workspace surface.

**Delete (or feature-flag off):**
- The default persona widget sections render block in `PersonaDashboardLayout.tsx:422–460` *if Q4 = "delete"*.

**Test:**
- `frontend/src/components/dashboard/__tests__/PersonaDashboardLayout.test.tsx` — add cases:
  - Idle session renders brief + checklist, no CommandCenter.
  - After a user message, brief disappears and AgentWorkArea mounts.
  - `createNewChat()` returns surface to idle.
  - `/dashboard/workspace` empty state shows brief + checklist.
- Manual UI verification in `make playground` is not enough; spin up `cd frontend && npm run dev` and walk both surfaces in a browser before claiming done.

---

## 5. Phase 2 — Agent ↔ Workspace Contract (Sketch)

> Detailed plan deferred until Phase 1 ships. Sketch is here so reviewers can flag fundamental disagreements early.

### 5.1 New SSE event: `workspace_command`

Backend emits via ADK callback when the agent's response includes a structured `workspace.commands[...]` block (or an explicit tool call):

```json
{
  "type": "workspace_command",
  "command": "set_layout",
  "payload": {"mode": "compare", "item_ids": ["w_123", "w_124"]}
}
```

Commands:
- `set_layout` — `mode: 'focus' | 'compare' | 'grid'`, optional item id list
- `focus` — `item_id`
- `highlight` — `item_id`, `region` (CSS selector or x/y/w/h)
- `request_approval` — `deliverable_id`, `prompt`
- `replace_active` — `widget` (full WidgetDefinition)
- `pin` / `unpin` — `item_id`
- `clear_canvas` — no payload

`frontend/src/lib/sseParser.ts` adds `'workspace_command'` to `ParsedSideEffect.type` and routes to a new `dispatchWorkspaceCommand()` in `widgetDisplay.ts`.

### 5.2 Back-channel: `workspace_event` POST

ActiveWorkspace POSTs to `/a2a/sessions/{session_id}/workspace_events` whenever a user closes/edits/approves/rearranges items. The endpoint writes to a new `workspace_events` table (session-scoped, append-only). Agent reads via a new `read_workspace_events(session_id, since_ts?)` tool — which becomes a callback the agent runs at the start of each turn.

### 5.3 Session memory: `active_workspace_items`

Augment session state in `app/services/session_service.py` with an `active_workspace_items: list[WorkspaceItemRef]`. Populated by the same SSE pipeline that writes to `workspace_items` table. ExecutiveAgent's pre-turn callback adds it to the model context so the agent doesn't re-emit artifacts that already exist.

### 5.4 Agent-side: opt-in tool

Single ADK tool `workspace.update(commands=[...])` agents call when they want to shape the canvas. Existing widget-emission paths keep working (legacy fallback). Agents are upgraded one at a time — start with ExecutiveAgent + Marketing (these produce the most artifacts).

---

## 6. Risks & Tradeoffs

- **Brief card extraction** can break the `/dashboard/command-center` route if we don't keep the visual layout identical. Mitigation: snapshot test on the standalone command-centre route.
- **Sticky engagement (Q2 option a)** means a user who sends one prompt and walks away never sees the brief again until they explicitly start a new chat. Mitigation: the empty "Clear workspace" button on ActiveWorkspace should also reset engagement. Document this in OnboardingChecklist.
- **Parser fallback in Phase 2** — keeping `save_widget`/`focus_widget` heuristic parsing alongside explicit `workspace_command` events doubles the surface area for bugs. Plan to deprecate after one milestone of usage data shows agents reliably emit explicit commands.
- **Backend tool & session-memory work in Phase 2** touches ExecutiveAgent — coordinate with the Executive Enhancement work captured in `project_executive_enhancement.md`. Will likely need a new requirement under v9 or v10 milestone.
- **`active_workspace_items` in session memory** can grow unbounded for long sessions. Cap at the most recent N (suggest 20) and surface a `more_items_in_history` flag.

---

## 7. Verification (Phase 1)

- [ ] `/startup`, `/sme`, `/solopreneur`, `/enterprise` all show only Brief Card + Onboarding Checklist on a fresh chat (no KPIs, no Launchpad, no Founder Board, no default widget sections).
- [ ] After the first user message, those four pages swap to the agent work area.
- [ ] `createNewChat()` from the chat sidebar returns the page to brief + checklist.
- [ ] `/dashboard/workspace` empty state matches: brief + checklist; agent output replaces them when present.
- [ ] `/dashboard/command-center` standalone route still renders a brief card identical to today's pixel layout.
- [ ] No regressions in widget pinning, session widget list, focus mode.
- [ ] `make lint` and `cd frontend && npm run lint && npm run typecheck` pass.

---

## 8. Out of Scope (this plan)

- Mobile layout changes (the persona pages have a separate `mobileLayout="fab"` path — verify but don't redesign).
- Renaming routes (keep `/dashboard/workspace`, persona pages, `/dashboard/command-center` URLs as-is).
- New widget types or visual redesign of existing widgets.
- Deeper changes to OnboardingChecklist's task definitions or progress tracking.
- Agent-side prompt/instruction changes — Phase 2 only adds tool surface, doesn't rewrite agent instructions.
