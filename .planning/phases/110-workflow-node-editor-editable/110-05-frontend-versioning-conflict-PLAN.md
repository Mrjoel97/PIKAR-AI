---
phase: 110-workflow-node-editor-editable
plan: 05
type: execute
wave: 5
depends_on: [110-02, 110-04]
files_modified:
  - frontend/src/components/workflows/editor/VersionSelector.tsx
  - frontend/src/components/workflows/editor/HistoryPane.tsx
  - frontend/src/components/workflows/editor/ConflictModal.tsx
  - frontend/src/components/workflows/editor/NodeCanvas.tsx
  - frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx
  - frontend/src/services/workflows.ts
  - frontend/src/__tests__/workflows/VersionSelector.test.tsx
  - frontend/src/__tests__/workflows/HistoryPane.test.tsx
  - frontend/src/__tests__/workflows/ConflictModal.test.tsx
  - frontend/src/__tests__/workflows/editor-conflict-flow.test.tsx
  - tests/integration/test_editor_save_reload_round_trip.py
autonomous: true
requirements:
  - NODEEDITOR-VERSION-02
  - NODEEDITOR-CONCURRENCY-01
gap_closure: false

must_haves:
  truths:
    - "The editor toolbar shows a version selector dropdown listing the recent versions (latest at top with a 'current' badge) — clicking a non-current version shows a 'v3 preview' pill that disables editing without rendering v3's graph content (full per-version preview deferred — would require new GET /templates/{id}/versions/{vid} endpoint not in Plan 02's scope)"
    - "A View History pane (slide-in or modal) lists ALL versions for the template with version_number, saved_at, saved_by_user_name, and comment; each row has a Revert button"
    - "Clicking Revert on version X calls POST /workflows/templates/{id}/revert/{vid}; on success the editor reloads from the new latest version (version_number = max+1, parent_version_id = X.id); sonner toast 'Reverted to version X — new version Y created'"
    - "When PUT save returns 412 (ETagMismatchError thrown by saveTemplate), a ConflictModal appears with three buttons: 'View their changes' / 'Overwrite' / 'Cancel'"
    - "ConflictModal 'View their changes' loads the fresh template body that came in the 412 response, replaces editor state, sonner-toasts 'Loaded latest version; your unsaved edits were discarded'"
    - "ConflictModal 'Overwrite' re-sends saveTemplate with the fresh ETag from `body.etag` of the 412 response (B-2 wire format — not from header); requires a secondary confirm prompt 'Are you sure you want to overwrite the other user's changes?'"
    - "ConflictModal 'Cancel' closes the modal leaving local editor state intact; user can manually copy work elsewhere before reloading"
    - "End-to-end editor round-trip works: drag a node onto the canvas → click Save → page reloads (or simulated soft-reload) → the new node is present in the loaded graph; covered by tests/integration/test_editor_save_reload_round_trip.py (ROADMAP criterion #1 end-to-end)"
  artifacts:
    - path: "frontend/src/components/workflows/editor/VersionSelector.tsx"
      provides: "Toolbar dropdown component listing recent versions; controlled component (selectedVersionId + onSelect props); 'current' badge on the live version"
      contains: "VersionSelector"
    - path: "frontend/src/components/workflows/editor/HistoryPane.tsx"
      provides: "Slide-in pane with full history list + Revert buttons; opens via toolbar 'History' button"
      contains: "HistoryPane"
    - path: "frontend/src/components/workflows/editor/ConflictModal.tsx"
      provides: "Three-button modal (View their changes / Overwrite / Cancel) shown on 412 from saveTemplate"
      contains: "ConflictModal"
    - path: "frontend/src/services/workflows.ts"
      provides: "getTemplateHistory(id) + revertTemplate(id, versionId, etag) service methods"
      contains: "getTemplateHistory"
    - path: "tests/integration/test_editor_save_reload_round_trip.py"
      provides: "I-4 round-trip integration test — drag, save, reload, verify node persists; covers ROADMAP criterion #1 end-to-end"
      contains: "test_editor_round_trip"
  key_links:
    - from: "PUT save 412 response"
      to: "ConflictModal shown via state setShowConflictModal(true)"
      via: "page.tsx catches ETagMismatchError from saveTemplate; stores fresh template+etag (from err.freshEtag which is body.etag per B-2) in state; renders ConflictModal"
      pattern: "ETagMismatchError"
    - from: "ConflictModal Overwrite path"
      to: "saveTemplate(templateId, payload, freshEtag)"
      via: "Uses the stashed body.etag from the 412 ETagMismatchError — NOT a header value, NOT a re-fetched GET"
      pattern: "body.etag"
    - from: "ConflictModal Revert button"
      to: "revertTemplate() in services/workflows.ts → POST /workflows/templates/{id}/revert/{vid}"
      via: "Direct service call with If-Match header (the current local etag); revertTemplate returns new etag in body per Plan 02 B-2 contract"
      pattern: "revertTemplate"
    - from: "HistoryPane Revert click"
      to: "Same revertTemplate call → on success, page reloads from new latest version"
      via: "Confirmation dialog → revertTemplate → toast + setState(new graph from response)"
      pattern: "revertTemplate"
---

<objective>
Plug versioning UI + concurrency conflict resolution onto Plan 04's editor. Adds three new components (VersionSelector, HistoryPane, ConflictModal), two service methods (getTemplateHistory, revertTemplate), and wires the editor page to surface 412 conflicts as the spec-required three-button modal instead of Plan 04's temporary toast. Closes the loop on Spec B decision 6 (If-Match optimistic locking).

B-1: Plan 05 moved to Wave 5 (depends_on [110-02, 110-04]) since Plan 04 was promoted to Wave 4. Wave count for Phase 110 is now 5 (intentional sequential safety per B-1).

Purpose: Implements roadmap success criteria #4 (version selector dropdown + History pane + Revert), #5 + #6 (412 conflict body returns fresh template; modal lets user choose view/overwrite/cancel). Does NOT touch backend code — Plan 02 already shipped all required endpoints.
Output: 3 new components, 2 new service methods, page.tsx wiring update, 4 new test files (~25 combined tests), and 1 end-to-end integration test (I-4 covering ROADMAP criterion #1).
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/110-workflow-node-editor-editable/110-CONTEXT.md
@.planning/phases/110-workflow-node-editor-editable/110-02-SUMMARY.md
@.planning/phases/110-workflow-node-editor-editable/110-04-SUMMARY.md
@frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx
@frontend/src/components/workflows/editor/NodeCanvas.tsx
@frontend/src/services/workflows.ts

<interfaces>
<!-- From Plans 02 + 04: -->
// app/routers/workflows.py:
//   GET /workflows/templates/{id}/history             -> list[HistoryItem]
//   POST /workflows/templates/{id}/revert/{vid}       -> WorkflowTemplateVersion + etag in body (B-2)
//
// frontend/src/services/workflows.ts:
//   export class ETagMismatchError extends Error { currentTemplate, freshEtag }   // freshEtag from body.etag per B-2
//   export class CopyForkError extends Error { copiedTemplateId, seedName }       // W-4
//   export class ValidationFailedError extends Error { errors }                   // B-1 wave-3 PUT validation
//   export async function saveTemplate(id, payload, etag): Promise<SaveTemplateResult>   // returns {version, etag}
//   export async function validateTemplate(id, graph): Promise<ValidationError[]>
//   export type WorkflowTemplateVersion = components['schemas']['WorkflowTemplateVersion'];
//   export type HistoryItem = components['schemas']['HistoryItem'];
//   export type WorkflowTemplate = components['schemas']['WorkflowTemplateResponse'];
//
// frontend/src/components/workflows/editor/NodeCanvas.tsx:
//   Props: { template, editable?, onChange?, selectedNodeId?, onSelectNode?, validationErrors? }
//   The component already supports being passed an arbitrary template object via the `template` prop.
//
// frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx:
//   Plan 04 ships state: template, etag, nodes, edges, layout, selectedNodeId, dirty, saving, comment
//   Save flow exists; 412 currently shows a sonner toast (Plan 04 placeholder); 409 redirects; 400 surfaces ValidationFailedError toast
</interfaces>

<context_notes>
- **B-1 (wave 5):** Plan 05 depends on Plans 02 (backend endpoints) + 04 (editor page + saveTemplate). Wave 5 — runs last. If Plan 04 has not landed, this plan cannot ship the conflict modal wiring; the components themselves (VersionSelector, HistoryPane, ConflictModal) can still be built standalone.
- **I-2 fix: scope-reduce per-version preview** — Plan 04's `must_haves.truths` originally said "previews that version's graph in read-only mode". The implementation in Plan 05 Task 05-04 step 5 deliberately scope-reduces this: do NOT fetch v3's graph content; instead show a "v3 preview" pill that disables editing while keeping the current canvas state visible. Full per-version graph preview would require a new GET /templates/{id}/versions/{vid} endpoint that Plan 02 did NOT ship. Deferred to a follow-up. The must_haves frontmatter now reflects the actual scope (no contradiction).
- **I-4: round-trip integration test** — add `tests/integration/test_editor_save_reload_round_trip.py` to this plan's close-out: exercises drag → save → reload → assert node present. Cheap addition; explicitly covers ROADMAP criterion #1 end-to-end. Should NOT require running a real browser — use FastAPI TestClient for the backend side + assert the response state matches what the editor would have after a reload (mounting the saved graph state in the test).
- Revert flow: user clicks Revert on v3 in HistoryPane → confirmation dialog "Reverting will create a new version (v6) with v3's content. Continue?" → on confirm, POST revert → on success the editor's state replaces from the new version. Toast.
- Conflict modal "View their changes" is destructive of local state — confirm before applying? Spec says no secondary confirm for "View" (only for "Overwrite"). Implement spec literally: View = immediate apply with a toast warning, Overwrite = secondary confirm.
- **B-2 reinforcement:** ConflictModal's Overwrite path sends `If-Match: <freshEtag>` where `freshEtag` is the value stashed in conflictState (originally from `err.freshEtag` which was read from `body.etag` in Plan 04's saveTemplate). Do NOT re-read from response headers or re-fetch via GET. The body is canonical for PUT responses.
- A simple Tailwind/native modal pattern (no Radix). Background opacity + centered card. Mirror the comment modal Plan 04 added.
- Tests: vitest + @testing-library/react. Mock fetch via vi.spyOn. Mirror patterns from existing test files.
- Branch hygiene: every task includes an automated branch-check verify step (W-6).
- After this plan, Phase 110 is shipping-complete. Final integration test (preferably) runs end-to-end: create template → save v1 → edit + save v2 → check history shows v1+v2 → revert to v1 → check history shows v1+v2+v3 (v3 = revert) → save → check execution would pin to the latest current_version_id.
</context_notes>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 05-01: getTemplateHistory + revertTemplate service methods + revert typed flow</name>
  <files>frontend/src/services/workflows.ts</files>
  <behavior>
    Tests (target 6-8 tests):
    - getTemplateHistory returns array of HistoryItem from GET /history
    - getTemplateHistory rejects on 404 (template not found)
    - getTemplateHistory rejects on 403 (forbidden)
    - revertTemplate sends POST with If-Match header (the current local etag, sent verbatim)
    - revertTemplate on 412 throws ETagMismatchError with body.etag as freshEtag (B-2)
    - revertTemplate on 200 returns SaveTemplateResult-shaped {version, etag} — body has both keys per Plan 02 contract
  </behavior>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted (W-6).

Add to `frontend/src/services/workflows.ts`:

```typescript
export async function getTemplateHistory(templateId: string): Promise<HistoryItem[]> {
  const res = await fetch(`${API_BASE}/workflows/templates/${templateId}/history`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 404) throw new Error('Template not found');
  if (res.status === 403) throw new Error('Forbidden');
  if (!res.ok) throw new Error(`History fetch failed: ${res.status}`);
  return res.json();
}

export async function revertTemplate(
  templateId: string,
  versionId: string,
  etag: string,
): Promise<SaveTemplateResult> {
  const res = await fetch(`${API_BASE}/workflows/templates/${templateId}/revert/${versionId}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'If-Match': etag,                   // verbatim (already quoted from prior state)
      'Content-Type': 'application/json',
    },
  });
  if (res.status === 412) {
    const body = await res.json();
    // B-2: fresh etag from body.etag (NOT header)
    throw new ETagMismatchError(body, body.etag);
  }
  if (!res.ok) throw new Error(`Revert failed: ${res.status} ${await res.text()}`);
  // 200: body has {version, etag} per Plan 02 SaveTemplateSuccessResponse model
  return res.json();
}

// Per-version graph fetch is OUT OF SCOPE for Phase 110 (I-2 scope reduction).
// Plan 05 ships a "v3 preview" pill that disables editing without rendering v3's
// graph content. Full preview would require a new GET /templates/{id}/versions/{vid}
// endpoint not in Plan 02's scope — deferred.
```

Tests via fetch mocking. Mirror existing service test patterns. Specifically assert that revertTemplate on 200 returns `{version, etag}` shape (B-2 parity with saveTemplate).
  </action>
  <verify>
    <automated>cd frontend && grep -c "getTemplateHistory\|revertTemplate" src/services/workflows.ts</automated>
    <automated>cd frontend && npx vitest run src/__tests__/services 2>&1 | tail -10 || cd frontend && npx vitest run src/__tests__/workflows 2>&1 | grep -E "revertTemplate|getTemplateHistory" | tail -10</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Two new service functions exported; >=6 tests pass; revertTemplate returns {version, etag} shape (B-2); revertTemplate 412 reads body.etag for freshEtag; tsc clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 05-02: VersionSelector + HistoryPane components</name>
  <files>frontend/src/components/workflows/editor/VersionSelector.tsx, frontend/src/components/workflows/editor/HistoryPane.tsx, frontend/src/__tests__/workflows/VersionSelector.test.tsx, frontend/src/__tests__/workflows/HistoryPane.test.tsx</files>
  <behavior>
    VersionSelector tests (target 4-5 tests):
    - Renders dropdown with versions sorted newest-first
    - "current" badge on the version matching template.current_version_id
    - Click on a non-current version calls onSelectVersion(versionId) prop
    - "View History" link inside dropdown calls onOpenHistory prop
    - Empty history shows "Just saved v1" placeholder

    HistoryPane tests (target 5-7 tests):
    - Renders all versions with version_number, saved_at (relative time), saved_by_user_name, comment
    - Each row has a Revert button (except for the current version)
    - Click Revert opens a confirmation dialog
    - Confirming the dialog calls onRevert(versionId) prop
    - Close button calls onClose
    - Empty history shows "No version history yet"
  </behavior>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

1. `VersionSelector.tsx`:

```typescript
'use client';
import { useState } from 'react';
import type { HistoryItem } from '@/services/workflows';
import { ChevronDown, History as HistoryIcon } from 'lucide-react';

type Props = {
  history: HistoryItem[];
  currentVersionId: string | null;
  onSelectVersion: (versionId: string) => void;
  onOpenHistory: () => void;
};

export function VersionSelector({ history, currentVersionId, onSelectVersion, onOpenHistory }: Props) {
  const [open, setOpen] = useState(false);
  const current = history.find(v => v.version_id === currentVersionId);

  return (
    <div className="relative" data-testid="version-selector">
      <button onClick={() => setOpen(!open)} className="text-sm border rounded px-2 py-1 flex items-center gap-1">
        {current ? `v${current.version_number}` : 'v1'}
        <span className="text-[10px] bg-emerald-100 px-1 rounded">current</span>
        <ChevronDown size={12} />
      </button>
      {open && (
        <div className="absolute right-0 mt-1 w-64 bg-white dark:bg-zinc-900 border rounded shadow-lg z-20">
          {history.slice(0, 5).map(v => (
            <button
              key={v.version_id}
              onClick={() => { onSelectVersion(v.version_id); setOpen(false); }}
              className="block w-full text-left px-3 py-2 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800"
            >
              <div className="flex justify-between">
                <span>v{v.version_number}</span>
                {v.version_id === currentVersionId && <span className="text-[10px] bg-emerald-100 px-1 rounded">current</span>}
              </div>
              <div className="text-[10px] text-zinc-500">{v.saved_at} · {v.saved_by_user_name ?? 'unknown'}</div>
              {v.comment && <div className="text-[11px] text-zinc-600 truncate">{v.comment}</div>}
            </button>
          ))}
          <button
            onClick={() => { onOpenHistory(); setOpen(false); }}
            className="w-full text-left px-3 py-2 text-sm border-t flex items-center gap-1"
          >
            <HistoryIcon size={12} /> View full history
          </button>
        </div>
      )}
    </div>
  );
}
```

2. `HistoryPane.tsx`:

```typescript
'use client';
import { useState } from 'react';
import type { HistoryItem } from '@/services/workflows';
import { X, RotateCcw } from 'lucide-react';

type Props = {
  history: HistoryItem[];
  currentVersionId: string | null;
  onRevert: (versionId: string) => void;
  onClose: () => void;
};

export function HistoryPane({ history, currentVersionId, onRevert, onClose }: Props) {
  const [confirmRevertId, setConfirmRevertId] = useState<string | null>(null);

  return (
    <aside className="fixed right-0 top-0 h-full w-96 bg-white dark:bg-zinc-900 border-l shadow-xl z-30 overflow-y-auto" data-testid="history-pane">
      <header className="p-4 border-b flex justify-between items-center">
        <h2 className="font-semibold">Version history</h2>
        <button onClick={onClose}><X size={16} /></button>
      </header>
      <ol className="divide-y">
        {history.length === 0 && <li className="p-4 text-zinc-500 text-sm">No version history yet.</li>}
        {history.map(v => (
          <li key={v.version_id} className="p-4 space-y-1">
            <div className="flex justify-between items-baseline">
              <strong>v{v.version_number}</strong>
              {v.version_id === currentVersionId && <span className="text-[10px] bg-emerald-100 px-1 rounded">current</span>}
            </div>
            <div className="text-xs text-zinc-500">{v.saved_at} · {v.saved_by_user_name ?? 'unknown'}</div>
            {v.comment && <div className="text-sm text-zinc-700">{v.comment}</div>}
            {v.version_id !== currentVersionId && (
              <button
                onClick={() => setConfirmRevertId(v.version_id)}
                className="text-xs flex items-center gap-1 text-blue-600 hover:underline"
                data-testid={`revert-button-${v.version_id}`}
              >
                <RotateCcw size={11} /> Revert to this version
              </button>
            )}
          </li>
        ))}
      </ol>
      {confirmRevertId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-40">
          <div className="bg-white dark:bg-zinc-900 p-6 rounded shadow-xl w-96 space-y-3">
            <h3 className="font-semibold">Revert to earlier version?</h3>
            <p className="text-sm text-zinc-500">A new version will be created with this content; your current version stays in history.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirmRevertId(null)} className="px-3 py-1.5 rounded border">Cancel</button>
              <button
                onClick={() => { onRevert(confirmRevertId); setConfirmRevertId(null); }}
                className="px-3 py-1.5 rounded bg-blue-600 text-white"
              >
                Revert
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
```

3. Tests at `frontend/src/__tests__/workflows/VersionSelector.test.tsx` and `frontend/src/__tests__/workflows/HistoryPane.test.tsx`. Combined target >=10 tests.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/__tests__/workflows/VersionSelector.test.tsx src/__tests__/workflows/HistoryPane.test.tsx 2>&1 | tail -20</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Both components exist; tests pass; tsc clean; matches spec UI shape (current badge, revert confirmation, etc).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 05-03: ConflictModal component</name>
  <files>frontend/src/components/workflows/editor/ConflictModal.tsx, frontend/src/__tests__/workflows/ConflictModal.test.tsx</files>
  <behavior>
    Tests (target 5-7 tests):
    - Renders three buttons: "View their changes" / "Overwrite" / "Cancel"
    - View calls onViewTheirChanges() prop
    - Overwrite shows secondary confirm; confirming calls onOverwrite() prop
    - Cancel calls onCancel() prop
    - Modal is closed (DOM unmount) when controlled prop `open` is false
    - Displays the conflicting saver's identity if known (from freshTemplate.last_saved_by or fallback to "another user")
    - Pressing Escape calls onCancel
  </behavior>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

Create `ConflictModal.tsx`:

```typescript
'use client';
import { useState, useEffect } from 'react';
import type { WorkflowTemplate } from '@/services/workflows';
import { AlertTriangle, X } from 'lucide-react';

type Props = {
  open: boolean;
  freshTemplate: WorkflowTemplate | null;
  onViewTheirChanges: () => void;
  onOverwrite: () => void;
  onCancel: () => void;
};

export function ConflictModal({ open, freshTemplate, onViewTheirChanges, onOverwrite, onCancel }: Props) {
  const [showOverwriteConfirm, setShowOverwriteConfirm] = useState(false);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onCancel(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" role="dialog" data-testid="conflict-modal">
      <div className="bg-white dark:bg-zinc-900 p-6 rounded shadow-xl w-[480px] space-y-3">
        <header className="flex items-center gap-2">
          <AlertTriangle className="text-amber-500" size={20} />
          <h2 className="font-semibold">Save conflict</h2>
          <button onClick={onCancel} className="ml-auto"><X size={16} /></button>
        </header>
        <p className="text-sm text-zinc-700 dark:text-zinc-300">
          Another save happened since you opened this template. How do you want to resolve it?
        </p>
        {!showOverwriteConfirm && (
          <div className="flex justify-end gap-2 pt-2">
            <button onClick={onCancel} className="px-3 py-1.5 rounded border" data-testid="conflict-cancel">Cancel</button>
            <button onClick={() => setShowOverwriteConfirm(true)} className="px-3 py-1.5 rounded border border-red-300 text-red-700" data-testid="conflict-overwrite">Overwrite</button>
            <button onClick={onViewTheirChanges} className="px-3 py-1.5 rounded bg-emerald-600 text-white" data-testid="conflict-view">View their changes</button>
          </div>
        )}
        {showOverwriteConfirm && (
          <div className="border-t pt-3 space-y-2">
            <p className="text-sm text-red-700">
              This will permanently replace the other user's saved changes. Continue?
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowOverwriteConfirm(false)} className="px-3 py-1.5 rounded border">Back</button>
              <button onClick={onOverwrite} className="px-3 py-1.5 rounded bg-red-600 text-white" data-testid="conflict-overwrite-confirm">Yes, overwrite</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
```

Tests via @testing-library/react + vitest. Cover all three buttons, Escape key, secondary confirm flow, open=false unmount.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/__tests__/workflows/ConflictModal.test.tsx 2>&1 | tail -15</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Component exists; >=5 tests pass; tsc clean; matches three-button spec shape.</done>
</task>

<task type="auto">
  <name>Task 05-04: Wire all three components into editor page + handle 412 with ConflictModal (Overwrite uses body.etag — B-2)</name>
  <files>frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx, frontend/src/__tests__/workflows/editor-conflict-flow.test.tsx</files>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

Modify the editor page from Plan 04 to:

1. Load template history on mount: `useEffect(() => { getTemplateHistory(templateId).then(setHistory) })`. Refresh history after every successful save.

2. Mount VersionSelector in the toolbar alongside the Save button:

```typescript
<VersionSelector
  history={history}
  currentVersionId={template?.current_version_id ?? null}
  onSelectVersion={handlePreviewVersion}
  onOpenHistory={() => setHistoryOpen(true)}
/>
```

3. Mount HistoryPane (conditionally rendered when historyOpen state is true):

```typescript
{historyOpen && (
  <HistoryPane
    history={history}
    currentVersionId={template?.current_version_id ?? null}
    onRevert={handleRevert}
    onClose={() => setHistoryOpen(false)}
  />
)}
```

4. `handleRevert(versionId)`:
   - Show a sonner.promise wrapper around revertTemplate(templateId, versionId, etag).
   - On success: read the new `{version, etag}` from the response (B-2 body shape); refresh template + history; update local etag from `result.etag`; toast "Reverted to v3 — new v6 created".
   - On ETagMismatchError: show ConflictModal (use err.freshEtag from body — B-2).
   - On other errors: toast.error.

5. `handlePreviewVersion(versionId)`:
   - **I-2 scope reduction:** do NOT fetch v3's graph content. Set a `previewVersionId` state to `versionId`.
   - Show a pill "v3 preview" with a "Back to my edits" button.
   - When previewVersionId is set, DISABLE the editor (NodeCanvas in read-only mode + disable Save button + grey out NodePalette) WITHOUT rendering v3's content. The canvas keeps showing the user's current working state, just non-editable.
   - "Back to my edits" clears previewVersionId.
   - Document in SUMMARY that full per-version graph preview is deferred (would require new GET /templates/{id}/versions/{vid} endpoint not in Plan 02's scope).

6. Mount ConflictModal:

```typescript
<ConflictModal
  open={conflictState !== null}
  freshTemplate={conflictState?.freshTemplate ?? null}
  onViewTheirChanges={() => {
    if (!conflictState) return;
    setTemplate(conflictState.freshTemplate);
    setEtag(conflictState.freshEtag);                // B-2: this is body.etag from 412 response
    setNodes(conflictState.freshTemplate.graph_nodes ?? []);
    setEdges(conflictState.freshTemplate.graph_edges ?? []);
    setLayout(conflictState.freshTemplate.graph_layout ?? {});
    setDirty(false);
    setConflictState(null);
    toast.warning('Loaded latest version — your unsaved edits were discarded');
  }}
  onOverwrite={async () => {
    if (!conflictState) return;
    try {
      // B-2: Overwrite re-sends saveTemplate with the fresh ETag stashed from
      //      the 412 ETagMismatchError. That value came from body.etag (Plan 04's
      //      saveTemplate read body.etag, NOT response header). Do NOT re-fetch.
      const result = await saveTemplate(
        templateId,
        { graph_nodes: nodes, graph_edges: edges, graph_layout: layout, comment },
        conflictState.freshEtag,
      );
      setEtag(result.etag);                          // B-2: next ETag from result.etag (body)
      setConflictState(null);
      setDirty(false);
      toast.success(`Overwritten — saved as v${result.version.version_number}`);
    } catch (err) {
      if (err instanceof ETagMismatchError) {
        // race continued — update fresh state from body.etag and stay in conflict mode
        setConflictState({ freshTemplate: err.currentTemplate, freshEtag: err.freshEtag });
      } else {
        toast.error(`Overwrite failed: ${(err as Error).message}`);
      }
    }
  }}
  onCancel={() => setConflictState(null)}
/>
```

7. Update Plan 04's catch block for saveTemplate's ETagMismatchError — instead of `toast.error('Conflict...')`, do `setConflictState({ freshTemplate: err.currentTemplate, freshEtag: err.freshEtag })`.

8. Add integration test at `frontend/src/__tests__/workflows/editor-conflict-flow.test.tsx` (target 4-6 tests): Full mounting of the editor page with mocked fetch — simulate save → 412 → modal appears → click Overwrite → confirm → second save fires with fresh etag (from body) → success.

Specifically assert in tests:
- `test_overwrite_uses_freshEtag_from_412_body_not_header` — mock 412 response with `body.etag = '"X"'` AND `headers.etag = '"WRONG"'`; click Overwrite → assert the next PUT request's `If-Match` header is `'"X"'` (body, not header).
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/__tests__/workflows/editor-conflict-flow.test.tsx 2>&1 | tail -20</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Page renders VersionSelector + HistoryPane + ConflictModal in correct positions; 412 flow shows ConflictModal (NOT Plan 04's toast placeholder); Overwrite uses body.etag (B-2); Revert flow works end-to-end; integration test passes; "v3 preview" pill scope-reduces per I-2 (no v3 graph fetch).</done>
</task>

<task type="auto">
  <name>Task 05-05: End-to-end round-trip integration test (I-4 — ROADMAP criterion #1)</name>
  <files>tests/integration/test_editor_save_reload_round_trip.py</files>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

Create `tests/integration/test_editor_save_reload_round_trip.py` — covers ROADMAP criterion #1 end-to-end. This is a cheap addition (I-4) that asserts the editor's drag → save → reload round-trip actually works at the API level.

```python
"""End-to-end editor round-trip — I-4 close-out.

Drag node → save → reload → verify node persists. Uses FastAPI TestClient on the
backend to simulate what the editor consumer would do, without spinning up a real browser.

Covers ROADMAP criterion #1 at the API level.
"""

import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
    reason="Requires Supabase creds",
)


def test_editor_round_trip_save_and_reload_preserves_added_node():
    """Save a graph with a new agent-action node → reload → assert it's there.

    Steps:
      1. GET /workflows/templates/{seed_template_id} → capture body + ETag header
      2. Mutate the response body: append a new agent-action node to graph_nodes,
         and a corresponding edge. This simulates a frontend drag-drop addition.
      3. PUT /workflows/templates/{template_id} with If-Match = captured ETag,
         body = mutated graph. Assert 200. Capture the new ETag from response body.
         (Note: if {template_id} is a seed, expect 409 → follow copy_template_id, redo PUT.)
      4. GET /workflows/templates/{template_id_or_copy} → reload.
      5. Assert the response body's graph_nodes contains the appended node by id.
      6. Assert graph_edges contains the new edge.
      7. Assert version_number incremented (or version exists in /history with the new node).
    """


def test_editor_round_trip_revert_restores_prior_state():
    """Save v1 → modify → save v2 → revert to v1 → load → assert state matches v1.

    Steps:
      1. Establish a template with a known v1 graph.
      2. Modify graph_nodes; PUT → captures new ETag; assert version_number=2.
      3. Pull /history; capture v1's version_id.
      4. POST /revert/{v1_version_id} with If-Match = current etag.
         Assert 200 with new version_number = 3.
      5. GET /workflows/templates/{id} → assert graph_nodes matches v1's nodes (NOT v2's).
      6. Assert /history now shows v1, v2, v3 (v3 = revert).
    """
```

2 tests minimum. They SKIP without creds. They directly assert ROADMAP criterion #1 end-to-end (drag → save → reload preserves state).

Place this file at `tests/integration/` (NOT `frontend/src/__tests__/`) because it exercises the backend round-trip, not the React rendering layer.
  </action>
  <verify>
    <automated>uv run pytest tests/integration/test_editor_save_reload_round_trip.py --collect-only -q 2>&1 | tail -10</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Test file exists; 2 tests collected by pytest; tests SKIP cleanly when creds absent; covers ROADMAP criterion #1 end-to-end at the API layer.</done>
</task>

</tasks>

<verification>
End-to-end manual UAT:

1. Open template editor; verify VersionSelector shows "v1 current" by default.
2. Make an edit; save with comment "test save 2"; verify VersionSelector now shows "v2 current".
3. Click VersionSelector → "View full history" → HistoryPane shows v1 + v2 with timestamps.
4. Click Revert on v1 → confirm dialog → confirm → toast "Reverted to v1 — new v3 created" → VersionSelector shows "v3 current".
5. Open template in two tabs; save in tab 1; in tab 2 click Save → ConflictModal appears with three buttons.
6. Click "View their changes" → editor canvas refreshes to tab 1's saved state → toast warning.
7. Make new edits; click Save → ConflictModal appears again (race continued); click Overwrite → secondary confirm → "Yes, overwrite" → toast success. (B-2: the Overwrite PUT carries body.etag from the 412 response, not header.)
8. Click an older version in VersionSelector → see "v3 preview" pill, editor disabled, current canvas state still visible (NO v3 graph rendered — I-2 scope reduction). Click "Back to my edits" → editor re-enabled.

Automated:
- `cd frontend && npx vitest run src/__tests__/workflows/` — all tests including new ones pass.
- `cd frontend && npx tsc --noEmit` — clean.
- ESLint clean.
- `uv run pytest tests/integration/test_editor_save_reload_round_trip.py --collect-only` — 2 tests collected (skip-on-no-creds).
- Branch hygiene: every commit on the Phase 110 branch (W-6, automated in every task).
</verification>

<success_criteria>
This plan ships when:
- 3 new editor components: VersionSelector, HistoryPane, ConflictModal.
- 2 new service methods: getTemplateHistory, revertTemplate (both reading body.etag per B-2).
- 1 page.tsx update wiring everything together (replaces Plan 04's 412 placeholder; Overwrite path uses body.etag from B-2).
- I-2 scope-reduction: per-version graph preview is a pill, NOT a content render. Documented in must_haves + SUMMARY.
- I-4 round-trip integration test: tests/integration/test_editor_save_reload_round_trip.py with 2 tests.
- 4 new vitest test files with combined >=25 tests passing.
- npx tsc --noEmit + ESLint clean.
- Plan SUMMARY committed.
- Phase 110 ROADMAP success criteria #1 (drag/connect/configure/save end-to-end — I-4 round-trip test), #4 (version selector + History + Revert), #5 (ETag + 412 + If-Match — already shipped backend; UI now closes the loop), #6 (three-button conflict modal exactly per spec) all met.
- Phase 110 fully ships at this plan's completion. Final orchestrator action: write Phase 110 VERIFICATION.md asserting all 10 ROADMAP success criteria.
</success_criteria>

<output>
After completion, create `.planning/phases/110-workflow-node-editor-editable/110-05-SUMMARY.md` with the standard sections. Specifically document: (a) confirmation that per-version graph preview was scope-reduced per I-2 to a disabled-editor pill (no v3 graph fetch); (b) Escape key handling pattern (does ConflictModal trap focus correctly?); (c) interaction between history refresh and save success; (d) confirmation that the Overwrite PUT carries body.etag from the 412 response (B-2 verified end-to-end); (e) the I-4 round-trip integration test results (collection-only on this workstation; full pass deferred to CI).

ALSO write a Phase 110 close-out section in the SUMMARY noting: all 7 NODEEDITOR-* requirement IDs now mapped to shipped plans (01-05), the 10 ROADMAP success criteria are met (or which are deferred and why), and recommend running `/gsd:verify-phase 110` to formalize the close.
</output>
</content>
</invoke>