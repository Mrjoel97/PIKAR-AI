# Phase 83: Document Upload Bypass — Research

**Researched:** 2026-04-30
**Domain:** Frontend chat input file-attach flow (Next.js / React 19 / TypeScript)
**Confidence:** HIGH (all findings traced to specific file:line in this repo)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HOTFIX-01 | Files attach to chat input via the standard `attachedFiles` flow and are processed inline on send via the existing `/api/upload` endpoint. The "detecting content type" indefinite loading state is eliminated by removing `/api/upload/smart` from the auto-attach path. | All findings below. The fix is a frontend-only delete-and-rewire in `ChatInterface.tsx` — the existing `/api/upload` extraction already supports PDF/DOCX/XLSX/text and the existing `handleSend` already serializes `attachedFiles` inline. |

Note: HOTFIX-01 is listed in `.planning/ROADMAP.md` Phase 83 entry but has not yet been added to `.planning/REQUIREMENTS.md`. Planner should treat the roadmap success criteria (lines 92-96 of ROADMAP.md) as the authoritative requirement text.
</phase_requirements>

## Phase Summary

The chat input currently routes every single-file drop through `/api/upload/smart` to fetch a "Context Sniffer" preview, which produces an "Detecting content type..." spinner that can hang indefinitely (35s proxy timeout, 30s client timeout, 2 attempts) before the file ever reaches the `attachedFiles` pill. The fix is to delete the smart-upload auto-call from `handleFileAttach`, attach the file directly to `attachedFiles`, and let the existing `handleSend` flow (which already calls `/api/upload` and inlines the extracted text into the agent message) do its job.

## Current Implementation

### The auto-call to /api/upload/smart that must be removed

**Single call site:** `frontend/src/components/chat/ChatInterface.tsx:1125`

```ts
// Inside handleSmartUpload (lines 1077-1188)
const response = await fetch(`${baseUrl}/api/upload/smart`, {
  method: 'POST',
  headers,
  body: formData,
  signal: controller.signal,
});
```

**Wired into the attach handler:** `ChatInterface.tsx:1262-1272`

```ts
const handleFileAttach = (file: File) => {
  if (isStreaming || isUploading) return;
  if (smartUploadResult) {
    handleSmartUploadDismiss();
  }
  // Try the smart upload endpoint to detect content type
  handleSmartUpload(file);   // <-- REMOVE; replace with direct attach to attachedFiles
};
```

**Triggered from two places:**
1. Drag-and-drop (single file): `ChatInterface.tsx:1331` — `<FileDropZone onFileDrop={handleFileAttach} ...>`
2. File picker (single file): `ChatInterface.tsx:1768` — `handleFilesAttach(e.target.files)` → `handleFileAttach(newFiles[0])` for `length === 1` (line 1280-1283)

Multi-file drops/picks already bypass the smart endpoint and attach directly (lines 1285-1295) — that path is the model the single-file path should follow.

### The "Detecting content type..." indicator

`ChatInterface.tsx:1535-1540`

```tsx
{isSmartUploading && (
  <div className="mb-2 flex items-center gap-2 p-2 bg-indigo-50 rounded-lg border border-indigo-200">
    <Loader2 size={14} className="animate-spin text-indigo-500" />
    <span className="text-xs font-medium text-indigo-600">Detecting content type...</span>
  </div>
)}
```

`isSmartUploading` is local state (line 124) toggled `true` at the start of `handleSmartUpload` (line 1080) and reset in the `finally` block (line 1186). It is NOT tied to `useFileUpload.isUploading` — it is its own state, so removing the smart-upload call removes the spinner cleanly.

### The SmartUploadToast follow-up UI

`ChatInterface.tsx:1513-1521` renders `<SmartUploadToast result={smartUploadResult} ...>` when the smart endpoint returns. The toast offers "Add to Vault" / "Analyze Now" / dismiss actions handled by `handleSmartUploadAddToVault` (line 1191), `handleSmartUploadAnalyzeNow` (line 1216), and `handleSmartUploadDismiss` (line 1248). Since the smart endpoint will no longer be called from chat attach, the toast will never render — the state, callbacks, and the `SmartUploadToast` import become dead code.

### State variables that become dead code

`ChatInterface.tsx:122-130`:
- `smartUploadResult` / `setSmartUploadResult`
- `isSmartUploading` / `setIsSmartUploading`
- `isSmartUploadFollowupActive` / `setIsSmartUploadFollowupActive`
- `smartUploadFile` / `setSmartUploadFile`

### How `attachedFiles` is currently serialized to the agent (KEEP — works correctly)

`ChatInterface.tsx:858-958` — `handleSend()`:

```ts
if (attachedFiles.length > 0) {
  for (const file of attachedFiles) {
    const { result, error } = await uploadFile(file);   // calls /api/upload
    if (result) {
      fileContents.push(`**Attached File: ${result.filename}**\n${result.content}`);
    } else {
      failedFiles.push({ name: file.name, error: error ?? 'Unknown error' });
    }
  }
  // ... aggregates fileContents into messageToSend, surfaces failedFiles via addMessage({role:'system', ...})
  // Lines 882-891: emits a SINGLE explicit system message listing every failed attachment with reason
  setAttachedFiles([]);  // line 896 — always cleared after send attempt
}
```

This is exactly the "send inline content + single explicit failure message" behaviour that success criteria 2 and 3 require. **No changes needed in `handleSend`.**

### `/api/upload` is the right endpoint (KEEP)

- **Frontend hook:** `frontend/src/hooks/useFileUpload.ts:116-172` — `uploadFile()` POSTs to `/api/upload` via Next.js proxy, 90s timeout, up to 4 retry attempts on external aborts, returns `{ result: { filename, content, summary_prompt } | null, error: string | null }`.
- **Next.js proxy:** `frontend/src/app/api/upload/route.ts` — streams multipart body to backend `${BACKEND_URL}/upload` (no smart proxy timeout — uses the simple proxy in the same dir as `smart/route.ts`).
- **Backend handler:** `app/routers/files.py:315-362` — `upload_file()`:
  - Calls `_extract_file_content()` which dispatches by extension to PDF (`pypdf`), DOCX (`python-docx`), XLSX (via `app/services/document_text_extraction.py`), or plain text.
  - Returns `FileUploadResponse(filename, content, summary_prompt)`.
- **Image support nuance:** `_extract_file_content` handles `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, plain text. For images, the response still returns successfully but with extraction-failure markers (e.g. "[Image content cannot be extracted...]") — i.e. images attach and send, but the inline text is a placeholder. This matches today's behaviour after the smart-toast is dismissed and the file is attached normally.

### Existing tests that touch the path

- `frontend/src/app/api/upload/smart/__tests__/route.test.ts` — tests the **proxy** behaviour (401, 504). The proxy stays in the codebase (success criterion 4 explicitly allows this), so this file does NOT need to be deleted. Recommend leaving it intact to keep the proxy under test.
- `frontend/src/components/chat/ChatInterface.test.tsx` — does NOT currently test smart upload (verified: zero matches for `smart`/`upload`/`Detecting`). No tests need to be updated; new tests need to be added.

## Target Implementation

### What changes (minimal, frontend-only)

1. **`ChatInterface.tsx:1262-1272` — replace `handleFileAttach`:**
   ```ts
   const handleFileAttach = (file: File) => {
     if (isStreaming || isUploading) return;
     setAttachedFiles(prev => {
       const exists = prev.some(f => f.name === file.name && f.size === file.size);
       return exists ? prev : [...prev, file];
     });
   };
   ```
   This is exactly what the existing multi-file path already does (lines 1286-1295) — pull that pattern down.

2. **`ChatInterface.tsx:1077-1188` — delete `handleSmartUpload` entirely.**

3. **`ChatInterface.tsx:1191-1259` — delete `handleSmartUploadAddToVault`, `handleSmartUploadAnalyzeNow`, `handleSmartUploadDismiss`.**

4. **`ChatInterface.tsx:122-130` — delete the four smart-upload state variables.**

5. **`ChatInterface.tsx:1513-1521` — delete the `<SmartUploadToast ...>` JSX block.**

6. **`ChatInterface.tsx:1534-1540` — delete the `isSmartUploading` "Detecting content type..." JSX block.**

7. **`ChatInterface.tsx:12` — remove the `import { SmartUploadToast, SmartUploadResult } from '@/components/chat/SmartUploadToast'` import.**

8. **`ChatInterface.tsx:1275-1296` — `handleFilesAttach` simplifies: drop the special-case for `length === 1` (the single-file path now matches the multi-file path), or keep it pointing at the new `handleFileAttach`.** Recommend: keep `handleFilesAttach` as a single de-duped batch attach for both single and multi-file callers (drag-drop and file-input).

### What stays (no changes required)

- `/api/upload/smart` Next.js proxy (`route.ts`, `smart/route.ts`) — kept per success criterion 4.
- `app/routers/files.py:742-807` `smart_upload` backend endpoint — kept (no chat caller, but referenced nowhere else either; deletion is out of scope).
- `SmartUploadToast.tsx` component — becomes unused after the import is removed; recommend leaving on disk and noting in plan as a follow-up cleanup (or delete in same PR — planner's call). If deleted, also delete `SmartUploadResult` type re-export.
- `useFileUpload.ts` `uploadFile()` and `uploadFileToVault()` — both still in use (uploadFile by `handleSend`, uploadFileToVault by other paths).
- `handleSend` (lines 858-958) — already correct.

### Net diff size estimate

~120 lines deleted, ~6 lines added in `ChatInterface.tsx`. Pure subtraction — the only "new" code is the small `handleFileAttach` rewrite that mirrors the existing multi-file branch.

## Files Involved

### Must modify (1 file)
- `frontend/src/components/chat/ChatInterface.tsx` — delete smart-upload state, handlers, JSX, and import; rewrite `handleFileAttach` to attach directly to `attachedFiles`.

### Must read (context, no edits)
- `frontend/src/hooks/useFileUpload.ts` — confirm `uploadFile()` signature and behaviour.
- `frontend/src/app/api/upload/route.ts` — confirm proxy behaviour (no edits).
- `app/routers/files.py:315-362` — confirm `/upload` extracts PDF/DOCX/XLSX (no edits).
- `frontend/src/components/chat/FileDropZone.tsx` — confirm callback signatures.
- `frontend/src/components/chat/SmartUploadToast.tsx` — confirm component is dead-code candidate.

### Tests
- **New unit/component test:** `frontend/src/components/chat/ChatInterface.test.tsx` — extend existing file (collocated next to source, vitest jsdom).
- **Optional cleanup:** if `SmartUploadToast.tsx` is deleted, also remove its (currently absent) tests; nothing to change in `frontend/src/app/api/upload/smart/__tests__/route.test.ts` — proxy keeps working.

### Test infrastructure
- Framework: **Vitest 4.0.18** (frontend/package.json:64), jsdom environment (vitest.config.mts), `@testing-library/react`.
- Run command: `cd frontend && npm test` → `node ./scripts/run-vitest.mjs`.
- Single-file run: `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx`.

## Validation Architecture

> Nyquist validation enabled (workflow.nyquist_validation = true in `.planning/config.json`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.0.18 (jsdom) + @testing-library/react |
| Config file | `frontend/vitest.config.mts` |
| Quick run command | `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx` |
| Full suite command | `cd frontend && npm test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HOTFIX-01.1 | Single-file drop attaches as a pill within ~one render tick; no `/api/upload/smart` fetch is issued | unit (component) | `npx vitest run src/components/chat/ChatInterface.test.tsx -t "drop attaches without smart"` | ✅ extend existing |
| HOTFIX-01.1 | "Detecting content type..." copy never renders on attach | unit (component) | `npx vitest run src/components/chat/ChatInterface.test.tsx -t "no detecting content type indicator"` | ✅ extend existing |
| HOTFIX-01.2 | On send with attached files, `/api/upload` is called and the inlined `result.content` is included in the message passed to `sendMessage` | unit (component) | `npx vitest run src/components/chat/ChatInterface.test.tsx -t "send delivers extracted content inline"` | ✅ extend existing |
| HOTFIX-01.3 | When `/api/upload` returns an error, `addMessage({role:'system', text: ...})` is called exactly once with the failure reason and `attachedFiles` is cleared (no spinner stuck) | unit (component) | `npx vitest run src/components/chat/ChatInterface.test.tsx -t "upload failure renders single system message"` | ✅ extend existing |
| HOTFIX-01.4 | The `/api/upload/smart` proxy is not invoked from `handleFileAttach` — assert global `fetch` was not called with a URL matching `/api/upload/smart` after a drop | unit (component) | `npx vitest run src/components/chat/ChatInterface.test.tsx -t "drop does not fetch smart endpoint"` | ✅ extend existing |
| HOTFIX-01 (manual UAT) | Drop each of PDF / DOCX / XLSX / image into chat → pill shows in ≤1s, send → agent reply | manual | UAT checklist in plan SUMMARY | manual |

### Sampling Rate
- **Per task commit:** `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx` (one file, ~2-5s)
- **Per wave merge:** `cd frontend && npm test` (full vitest suite)
- **Phase gate:** Full suite green + manual UAT (PDF + DOCX + XLSX + image drop-and-send each verified live) before `/gsd:verify-work`.

### Wave 0 Gaps
- Existing `ChatInterface.test.tsx` mocks `useAgentChat` only. Wave 0 needs to extend mocks to cover:
  - `useFileUpload` (return controllable `uploadFile` mock + `isUploading: false`)
  - `supabase/client` (`createClient`) so `handleSmartUpload`-era auth code paths don't blow up during render — actually moot once smart code is deleted, but render still hits `createClient` for other paths (presence detection etc.)
  - `usePresence`, `useRealtimeSession`, `useSessionControl`, `useSessionMap`, `useTextToSpeech`, `useSpeechRecognition`, `useVoiceSession`, `usePersona` — these hooks are imported at module scope; existing test gets away with it because `useAgentChat` mock blocks the early code path. Adding fire-drop tests requires deeper render — may need a shared `__mocks__/chat-test-harness.ts` helper that mocks all of them with stable defaults.

  Recommended Wave 0 task: add `frontend/src/components/chat/__test-utils__/chatHarness.ts` exporting a `renderChatInterface(opts)` helper that pre-mocks every hook used at module top-level. This unblocks all four behaviour tests.
- No framework install needed — Vitest, jsdom, and `@testing-library/react` are already in `frontend/package.json`.

## Open Questions / Risks

1. **Should `SmartUploadToast.tsx` be deleted in the same PR or left as dead code?**
   - Recommendation: leave it (and the unused `SmartUploadResult` interface) in this hotfix PR, mark for cleanup in a follow-up. Reduces blast radius and keeps the hotfix to a clean revert if needed.

2. **Should the backend `/upload/smart` endpoint be deleted?**
   - Out of scope. Success criterion 4 explicitly says "may remain in the codebase". Don't touch backend in this hotfix.

3. **Does `/api/upload` extract IMAGE content for inline delivery?**
   - No — `_extract_file_content` returns a placeholder for images. Acceptance criterion 2 says "extracted file content inline" but the user-facing requirement is "image attaches as a pill, send works without infinite spinner" — the placeholder text satisfies that. The agent will receive a message like "Attached File: photo.jpg\n[Image content cannot be extracted...]" which is honest and non-breaking. **Document this in the plan SUMMARY so QA expects it.**

4. **`handleSend` 4-attempt retry loop on `/api/upload`:**
   - `useFileUpload.uploadFile` retries up to 4 times with backoff (lines 30-31). Total worst-case wait: 0+1.5+3.5+7=12s of backoff plus 4×90s timeout per attempt = ~6 minutes max before surfacing failure. This is the existing behaviour and is NOT broken by this hotfix, but planner should note: success criterion 3 ("upload failure surfaces a single explicit system message — no infinite spinner") is satisfied by the current `handleSend` failure-handling block; the long worst-case is acceptable because the chat-input button is disabled (`isUploading`) for the duration with a spinner that DOES eventually resolve.

5. **The proxy `/api/upload/smart/__tests__/route.test.ts` references a 35s timeout case.**
   - Keep this test. The proxy is still on disk per success criterion 4. No risk.

6. **Type safety after `SmartUploadResult` import removal:**
   - `frontend/src/types/api.generated.ts` also references "SmartUpload" (per Grep). Verify generated types are unaffected — these are auto-generated from OpenAPI and reflect the backend endpoint, which is staying. Leave generated types alone; do not regenerate as part of this hotfix.

7. **No CONTEXT.md exists for this phase.**
   - The user has not run `/gsd:discuss-phase` for Phase 83. There are no locked decisions or discretion areas. Planner has full discretion within the bounds of the four success criteria.

## Implementation Notes

### Ordering hints
1. **Single PR, single commit** is appropriate for this hotfix — the change is purely subtractive frontend code with one rewritten function.
2. **Delete in this order to avoid transient compile errors:**
   - Add the new `handleFileAttach` body first
   - Remove the smart-upload JSX (toast + spinner)
   - Remove the four smart-upload handlers
   - Remove the four state variables
   - Remove the import line
3. **Run `npx tsc --noEmit` (or rely on Next dev typecheck) between steps** if the planner is unsure — TypeScript will catch missed references immediately.

### Gotchas
- **Don't remove `handleFilesAttach`'s multi-file branch** — it's still wired to drag-drop and file-input for `length > 1`. Just merge the `length === 1` path into the same de-duped attach loop.
- **`isUploading` and `isStreaming` guards in `handleFileAttach` must stay** — preserves the existing "no attach during upload/stream" behaviour.
- **Don't accidentally remove `SmartUploadToast.tsx`'s exported `SmartUploadResult` type if anything else imports it.** Grep showed only `ChatInterface.tsx` and the toast's own self-export; safe to leave alone if `SmartUploadToast.tsx` is kept on disk.
- **The `// @vitest-environment jsdom` directive at the top of `ChatInterface.test.tsx`** is currently a comment, not the standard `@vitest-environment node`/`jsdom` pragma — vitest.config.mts already defaults to jsdom globally, so this is fine. New tests don't need their own pragma.
- **When mocking `useFileUpload`, return `uploadFile` as a `vi.fn()` resolving to `{ result: { filename, content, summary_prompt }, error: null }`** for the success case and `{ result: null, error: 'Backend rejected' }` for the failure case. Match the `UploadOutcome` shape exactly.
- **For the "no smart fetch issued" assertion**, mock global `fetch` with `vi.spyOn(global, 'fetch')`, then assert `expect(fetchSpy).not.toHaveBeenCalledWith(expect.stringContaining('/api/upload/smart'), expect.anything())` after the drop event.

### Lint/format
- Project uses **Ruff** for Python (no Python touched here) and **ESLint** for frontend (`frontend/package.json:12`). Run `cd frontend && npm run lint` before commit.
- Watch for unused-import lint warnings on `SmartUploadToast`/`SmartUploadResult` — those are exactly what we want to remove.

## Sources

### Primary (HIGH confidence — all in-repo)
- `frontend/src/components/chat/ChatInterface.tsx` (lines 1, 12, 116-130, 858-958, 1077-1296, 1331, 1513-1540, 1761-1772) — every smart-upload call site, every `attachedFiles` reference, the send handler.
- `frontend/src/hooks/useFileUpload.ts` (lines 1-233) — `uploadFile`/`uploadFileToVault` contract.
- `frontend/src/app/api/upload/route.ts` and `frontend/src/app/api/upload/smart/route.ts` — both Next.js proxy implementations.
- `frontend/src/app/api/upload/smart/__tests__/route.test.ts` — existing proxy tests (proxy stays, tests stay).
- `frontend/src/components/chat/FileDropZone.tsx` — drag-drop callback contract.
- `frontend/src/components/chat/SmartUploadToast.tsx` — component-to-be-orphaned.
- `frontend/src/components/chat/ChatInterface.test.tsx` — existing test scaffold to extend.
- `frontend/vitest.config.mts` and `frontend/package.json` — test framework versions and run scripts.
- `app/routers/files.py` (lines 315-362, 742-807) — backend `/upload` and `/upload/smart` handlers.
- `app/routers/files.py` (lines 60-220) — `_extract_file_content` dispatcher confirming PDF/DOCX/XLSX/text support.
- `.planning/ROADMAP.md` (Phase 83 entry, lines 88-101) — authoritative success criteria.
- `.planning/REQUIREMENTS.md` — checked, HOTFIX-01 not yet recorded; planner should not block on this gap.
- `.planning/config.json` — confirms `nyquist_validation: true`, `frontend: vitest`.

### Secondary
None needed — every claim in this research is directly verifiable in the working tree.

### Tertiary
None.

## Metadata

**Confidence breakdown:**
- Standard stack (vitest/jsdom): HIGH — pinned versions in package.json
- Architecture (call sites, state model): HIGH — every `/api/upload/smart` reference enumerated; every `attachedFiles` reference enumerated; only one component file involved
- Pitfalls (hook mocking, multi-file branch preservation): HIGH — read every relevant line directly
- Backend support for inline extraction: HIGH — `_extract_file_content` source read for all four file types

**Research date:** 2026-04-30
**Valid until:** 2026-05-30 (codebase is stable; only frontend changes from outside this PR could invalidate file:line citations)
