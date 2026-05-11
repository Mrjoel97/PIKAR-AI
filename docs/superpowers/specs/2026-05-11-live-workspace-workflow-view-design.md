# Live Workspace Workflow View — Design Spec

**Date:** 2026-05-11
**Status:** Draft, pending user review
**Scope:** Spec A of two (Spec B — Branching Engine + Node-Graph Authoring — is a follow-up)

## Summary

When an agent kicks off a workflow today, the user has no live view of what's happening unless the agent explicitly calls the `display_workflow_timeline` tool. The execution runs invisibly; approvals surface in disconnected UI; per-step outcomes live only in raw `output_data` JSON.

This spec adds a **Live Workspace Workflow View** — a transparency layer that auto-spawns a `workflow_timeline` workspace item whenever a workflow starts, shows the run's name, goal, steps, and per-step outcomes, and renders pending human-gated approvals inline. It is an **enhancement** of the existing `WorkflowTimelineWidget` and the existing workspace canvas; no new widget framework, no new layout primitive.

## Problem

Today:

- `start_workflow_execution()` writes to `workflow_executions` and `workflow_steps` but does not emit a workspace_item — the agent must remember to call `display_workflow_timeline(execution_id)`. In practice it often doesn't.
- `WorkflowTimelineWidget` shows step status, duration, and tool name. It does not show the **goal** (why this run exists) or a human-readable **outcome** for each step.
- Approvals for `human_gated` steps live in a separate approvals UI; the user must context-switch to act on them.
- The view does not differentiate between an interactive run (user just started this) and a non-interactive run (scheduler kicked it off at 3am). All runs would be equally loud, or equally hidden, depending on whether the agent called the display tool.

## Goals

1. Every workflow run is visible by default in the initiating user's workspace canvas.
2. The view shows **name**, **goal**, **steps**, and **per-step outcomes** with confirmation of completion before the next step starts.
3. Steps that require human approval render an inline action; the user does not leave the workspace to act.
4. Non-interactive runs (scheduler, cron, webhook) appear without dominating the workspace, but escalate visually if they need attention.
5. The view works in the workspace canvas's existing `focus` layout mode without new layout machinery.

## Non-Goals

- New workflow engine capabilities (branching, conditionals, sub-flows) — those are Spec B.
- Replacing `WorkflowTimelineWidget` — this spec enhances it.
- Cross-user visibility (team-wide workflow inbox) — out of scope; each user sees runs they initiated.
- Migrating existing tools to return structured `summary` strings — opt-in; v1 ships with LLM fallback.
- Editing or authoring workflows — Spec B covers the node-graph editor.

## Decisions (from brainstorming)

| Question | Decision |
|---|---|
| Confirmation semantics | Hybrid — passive ✓ for safe steps; gate only on existing `human_gated` steps (no new gating logic) |
| Auto-spawn behavior | Always spawn; collapse non-interactive runs to a one-line strip |
| Content source | Hybrid — `executions.goal` column populated at start, `steps.outcome_text` populated by tool-returned `summary` or LLM fallback |
| Path | Enhance existing `WorkflowTimelineWidget`; do not rebuild |
| Approval surfacing | Card-level banner **and** step row morphs into an approval card |
| Persistence | Completed runs persist 48h then auto-archive; failed runs persist until dismissed |

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                  AGENT / USER / SCHEDULER                          │
└────────────────────────────────┬───────────────────────────────────┘
                                 │ start_workflow_execution(goal=...)
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  app/workflows/engine.py                                           │
│   • inserts workflow_executions row + goal              [CHANGED]  │
│   • calls workspace_items.emit_for_execution(...)            [NEW] │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  app/workflows/step_executor.py                                    │
│   • on step done → OutcomeWriter.write(step, output_data)    [NEW] │
│       precedence: tool-returned "summary" → LLM (bg) → status      │
│   • on step waiting_approval → emit step-paused SSE event    [NEW] │
└────────────────────────────────┬───────────────────────────────────┘
                                 │ SSE stream (existing transport)
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  frontend/src/components/widgets/WorkflowTimelineWidget.tsx        │
│   • renders goal header                                      [NEW] │
│   • renders per-step outcome_text                            [NEW] │
│   • inline Approve / Reject for human_gated waiting_approval [NEW] │
│   • card-level banner when any step paused for approval      [NEW] │
│   • collapsed-strip variant when payload.interactive=false   [NEW] │
│   • per-execution SSE subscription                           [NEW] │
└────────────────────────────────────────────────────────────────────┘
```

### Component boundaries

- **`WorkspaceItemEmitter`** (`app/services/workspace_items.py`, new) — single responsibility: given a workflow execution and a `run_source`, decide layout mode and emit a workspace_item row. Other features (initiative phases, briefings) can reuse it.
- **`OutcomeWriter`** (`app/workflows/outcome_writer.py`, new) — single responsibility: given a step and its `output_data`, write `outcome_text` and `outcome_source`. Pure function plus a background job hook.
- **`WorkflowTimelineWidget`** (existing, enhanced) — single responsibility: render one execution. No coupling to other widgets or workspace state.

## Backend changes

### Migration

One file: `supabase/migrations/<timestamp>_workflow_run_view.sql`

```sql
ALTER TABLE workflow_executions
    ADD COLUMN IF NOT EXISTS goal TEXT;

ALTER TABLE workflow_steps
    ADD COLUMN IF NOT EXISTS outcome_text TEXT,
    ADD COLUMN IF NOT EXISTS outcome_source TEXT
        CHECK (outcome_source IS NULL OR outcome_source IN ('tool', 'llm', 'status'));

ALTER TABLE workspace_items
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_workflow_steps_outcome_pending
    ON workflow_steps (workflow_execution_id)
    WHERE status = 'completed' AND outcome_text IS NULL;

CREATE INDEX IF NOT EXISTS idx_workspace_items_active
    ON workspace_items (user_id)
    WHERE archived_at IS NULL;
```

The first partial index speeds up the background LLM-summary worker's scan for pending outcomes. The second keeps the active-canvas read path fast as the archive grows.

### `app/workflows/engine.py`

- `start_workflow_execution()` gains a `goal: str | None = None` parameter.
- Agents and the UI pass the user's actual request (e.g. "build me a Q3 marketing plan"), not the template description.
- After the execution row is inserted, call `workspace_items.emit_for_execution(execution, run_source)`.

### `app/services/workspace_items.py` (new)

```python
async def emit_for_execution(execution, run_source: str) -> None:
    interactive = run_source in {"user_ui", "agent_ui"}
    layout_mode = "focus" if interactive else "embedded"
    await insert_workspace_item(
        user_id=execution.user_id,
        widget_type="workflow_timeline",
        workflow_execution_id=execution.id,
        layout_mode=layout_mode,
        widget_payload={"interactive": interactive},
    )
```

The function is the *only* place that maps `run_source` to layout mode. If product later wants webhook-initiated runs to be interactive too, one line changes.

### `app/workflows/step_executor.py`

After a step transitions to `completed`, `failed`, or `skipped`:

1. Read the tool's return value. If it is a mapping containing a `summary` string:
   - If ≤ 280 chars → write directly with `outcome_source="tool"`.
   - If > 280 chars → truncate to 277 chars + `"..."`, still write with `outcome_source="tool"`. (The tool author intended a summary; verbosity is not a reason to fall through to LLM.)
2. Otherwise, enqueue a background job (`OutcomeSummaryWorker`, polling the partial index) that calls Gemini Flash with a fixed prompt and writes back with `outcome_source="llm"`.
3. If the LLM call fails or quota trips, fall back to a deterministic string derived from `status + tool_name + duration_ms` with `outcome_source="status"`.

When a step transitions to `waiting_approval`, emit a `workflow.step.paused` SSE event on the execution channel so the widget can update without re-polling.

### SSE endpoint

`GET /workflows/executions/{id}/stream` — server-sent events for one execution. Verify whether this endpoint already exists in `app/routers/workflows.py`; if not, add it. Event types: `workflow.step.started`, `workflow.step.completed`, `workflow.step.paused`, `workflow.step.failed`, `workflow.execution.completed`, `workflow.execution.failed`.

## Frontend changes

### `WorkflowTimelineWidget.tsx`

Three render additions:

**Header block** (new, at the top of the widget):
- Workflow `name` (from existing fetch)
- Workflow `goal` (italicized, smaller, one line truncated with hover-to-expand)
- If `payload.interactive === false`, render in collapsed-strip mode instead — a single line: `▶ {name} • {status} • step {n} of {total}`. Click to expand.

**Per-step row** (modify existing):
- Current line: status icon + step name + tool name + duration
- New second line: `outcome_text` (or a shimmer placeholder if `outcome_source` is null and the step is `completed`)
- If `status === "waiting_approval"`, the row body morphs into an inline approval card with:
  - Step name + the reason for the gate (`required_approval` or `risk_level`)
  - **Approve** button → POST `/workflows/executions/{id}/steps/{step_id}/approve`
  - **Reject** button → POST `/workflows/executions/{id}/steps/{step_id}/reject`
  - Optimistic UI: button click greys the row immediately; SSE event confirms

**Card-level banner** (new):
- When any step in the current execution is `waiting_approval`, the widget container gets an amber 2px top border and the header shows `⏸ Awaiting your approval`.

### Live updates

The widget currently fetches on mount. Add a `useEffect` that opens an `EventSource` to `/workflows/executions/{id}/stream`, updates step state from events, and closes the stream when execution status is terminal.

### Focused mode

The existing `WorkspaceCanvas` Focus toggle already passes `fullFocus={true}` to the panel. The widget reads this prop and renders:
- Larger fonts in the header
- More vertical room per step (2 lines instead of 1 by default)
- A collapsible `output_data` inspector under each step (raw JSON, for debugging)

No new layout primitive — the Focus button in the canvas is the entry point.

## Concurrent workflows

- Up to 3 interactive runs (`WORKFLOW_MAX_CONCURRENT_PER_USER`) render as separate workspace items, switched via the existing item-selector buttons in `WorkspaceCanvas`.
- Non-interactive runs stack as collapsed strips at the bottom of the canvas. Each strip auto-expands to a full card if its execution enters `waiting_approval`.

## Persistence

- **Completed runs**: workspace_item persists for 48 hours after `completed_at`, then a daily cleanup job sets `archived_at = now()` (not a delete). User can still find it via workspace history (a separate view that queries `archived_at IS NOT NULL`).
- **Failed runs**: persist with `archived_at` null until the user explicitly dismisses (manual archive), on the assumption that failures need attention.
- **Cancelled runs**: same as completed (48h auto-archive).
- A scheduled job (`workspace_items_cleanup`) runs once daily to set `archived_at` on eligible rows; reuses existing Cloud Scheduler infrastructure.

## Error handling

- **Emitter failure** (e.g. workspace_items insert raises) — log, do not fail the workflow start. The execution proceeds; the user just doesn't get the visualization. This matches existing graceful-degradation patterns in the codebase (circuit breaker on Redis, fallback to direct DB).
- **LLM summary failure** — handled by the `status` fallback in `OutcomeWriter`.
- **SSE disconnect** — widget reconnects with exponential backoff (1s, 2s, 4s, 8s, capped at 30s), and re-fetches state on reconnect to reconcile.
- **Approve endpoint failure** — surface inline in the approval card with a retry button. Do not advance the workflow until a successful response is received.

## Testing surface

Unit:
- `WorkspaceItemEmitter.emit_for_execution` produces the correct payload for each `run_source`
- `OutcomeWriter` precedence: tool-summary > LLM > status
- `OutcomeSummaryWorker` skips steps with non-null `outcome_text`

Integration:
- A workflow with one `human_gated` step → workspace shows approval inline → approving advances execution
- A scheduler-initiated workflow that pauses for approval → strip auto-expands to full card
- Two concurrent interactive runs → both render as workspace items, switchable

Frontend (Vitest / RTL):
- `WorkflowTimelineWidget` renders running / paused-for-approval / completed / failed states
- Collapsed-strip variant renders correctly when `payload.interactive === false`
- SSE event handler updates step state without re-fetching

End-to-end: skipped for v1; covered by integration tests.

## Rollout

1. Migration applied
2. Backend changes deployed (emitter + OutcomeWriter + SSE endpoint)
3. Frontend widget enhancement shipped behind a `LIVE_WORKFLOW_VIEW` feature flag
4. Internal verification with one team's workflows
5. Flag flipped to default-on; remove flag in next release

## Out of scope / Follow-ups

- Tools migrating to return structured `summary` strings — opt-in, no deadline
- Team-wide workflow inbox (cross-user visibility) — future spec
- Workflow editing / authoring in the canvas — Spec B
- Branching execution rendering — depends on Spec B
- Real-time collaboration on approvals (e.g. "you have 3 unread approval requests") — future spec

## Open questions

None at spec time. All design decisions resolved during brainstorming. Implementation may surface ambiguities — those will be handled in the implementation plan.
