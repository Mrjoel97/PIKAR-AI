---
phase: 83-document-upload-bypass
plan: 02
type: execute
wave: 2
depends_on:
  - "83-01"
files_modified:
  - frontend/src/components/chat/ChatInterface.tsx
  - frontend/src/components/chat/ChatInterface.test.tsx
autonomous: true
requirements:
  - HOTFIX-01
must_haves:
  truths:
    - "Dropping a PDF / DOCX / XLSX / image into chat shows the file as an attached pill within ~one render tick with no 'detecting content type' toast or persistent spinner"
    - "Pressing send delivers extracted file content inline (via /api/upload) to the agent in the message passed to sendMessage"
    - "Upload failure surfaces a single explicit system message (addMessage with role:'system') — attachedFiles is cleared, no infinite spinner"
    - "/api/upload/smart endpoint may remain in the codebase but is no longer called from chat attach handlers — global fetch is never invoked with a /api/upload/smart URL after a drop event"
  artifacts:
    - path: "frontend/src/components/chat/ChatInterface.tsx"
      provides: "Rewritten handleFileAttach that pushes directly into attachedFiles; smart-upload state, handlers, JSX, and import deleted"
      contains: "handleFileAttach"
    - path: "frontend/src/components/chat/ChatInterface.test.tsx"
      provides: "5 new behavior tests covering all four success criteria using the chatHarness from Plan 01"
      contains: "drop attaches without smart"
  key_links:
    - from: "ChatInterface.tsx handleFileAttach"
      to: "setAttachedFiles"
      via: "direct state update with name+size dedup, mirrors the existing multi-file branch (lines 1286-1295)"
      pattern: "setAttachedFiles\\("
    - from: "ChatInterface.tsx handleSend (lines 858-958, UNCHANGED)"
      to: "/api/upload via uploadFile()"
      via: "for-loop over attachedFiles, inlines result.content into messageToSend"
      pattern: "uploadFile\\(file\\)"
    - from: "ChatInterface.tsx handleSend failure branch"
      to: "addMessage({role:'system', ...})"
      via: "single explicit failure message after the upload loop completes"
      pattern: "addMessage.*system"
---

<objective>
Eliminate the indefinite "Detecting content type..." spinner by removing the auto-call to `/api/upload/smart` from the chat attach path. Single-file drops now attach directly to `attachedFiles`, identical to the existing multi-file behavior. The existing `handleSend` flow (which already calls `/api/upload` and inlines extracted content, with proper failure handling) does the rest — no changes needed there.

Purpose: Production hotfix. Users currently get stuck on "Detecting content type..." for up to 35s+ when dropping any file because the smart-upload proxy is in front of `/api/upload`. The smart-upload preview UX is not worth this regression.

Output: ~120 lines deleted from ChatInterface.tsx, ~6 lines added; 5 new behavior tests in ChatInterface.test.tsx covering all four ROADMAP success criteria; existing 4 tests continue to pass.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/83-document-upload-bypass/83-RESEARCH.md
@.planning/phases/83-document-upload-bypass/83-VALIDATION.md
@.planning/phases/83-document-upload-bypass/83-01-SUMMARY.md

# Source under modification
@frontend/src/components/chat/ChatInterface.tsx
@frontend/src/components/chat/ChatInterface.test.tsx

# Reference (DO NOT modify)
@frontend/src/hooks/useFileUpload.ts
@frontend/src/components/chat/FileDropZone.tsx
@frontend/src/components/chat/SmartUploadToast.tsx

<interfaces>
<!-- Existing handleSend flow (UNCHANGED — included so executor does not "fix" what already works). -->
<!-- ChatInterface.tsx lines 858-958 — the upload-loop that this plan deliberately leaves alone. -->

```typescript
// EXISTING handleSend behavior (do not modify):
if (attachedFiles.length > 0) {
  const fileContents: string[] = [];
  const failedFiles: { name: string; error: string }[] = [];
  for (const file of attachedFiles) {
    const { result, error } = await uploadFile(file);  // POSTs to /api/upload (NOT smart)
    if (result) {
      fileContents.push(`**Attached File: ${result.filename}**\n${result.content}`);
    } else {
      failedFiles.push({ name: file.name, error: error ?? 'Unknown error' });
    }
  }
  // If failedFiles.length > 0, calls addMessage({role:'system', text: <single combined message>}).
  // Always clears attachedFiles after the loop (line 896): setAttachedFiles([]).
  // Inlines fileContents into messageToSend before sendMessage.
}
```

<!-- The existing multi-file attach branch (lines 1286-1295) — TARGET pattern to mirror in handleFileAttach -->
```typescript
// Existing handleFilesAttach multi-file branch (mirror this in single-file handleFileAttach):
setAttachedFiles(prev => {
  const newDeduped = newFiles.filter(
    nf => !prev.some(pf => pf.name === nf.name && pf.size === nf.size)
  );
  return [...prev, ...newDeduped];
});
```

<!-- Plan 01 harness API -->
```typescript
import { renderChatInterface, type RenderChatOptions } from './__test-utils__/chatHarness';

const { getFetchSpy, addMessage, uploadFile, sendMessage } = renderChatInterface({
  uploadFile: vi.fn().mockResolvedValue({
    result: { filename: 'doc.pdf', content: 'extracted text', summary_prompt: '' },
    error: null,
  }),
});
```

<!-- FileDropZone callback (frontend/src/components/chat/FileDropZone.tsx) -->
```typescript
interface FileDropZoneProps {
  onFileDrop: (file: File) => void;     // single-file callback
  onFilesDrop: (files: FileList) => void; // multi-file callback
}
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add 5 RED behavior tests covering all four success criteria</name>
  <files>frontend/src/components/chat/ChatInterface.test.tsx</files>
  <behavior>
    All 5 tests should FAIL against the current `ChatInterface.tsx` (because handleSmartUpload still fires and the JSX still renders "Detecting content type..."). They will GREEN after Task 2 deletes the smart-upload code.

    - Test 1: "drop attaches without smart" — fire a `drop` event with one PDF File on the FileDropZone; assert (a) the dropped file's name appears in the rendered DOM as an attached pill within `await waitFor(...)`, and (b) `getFetchSpy()` was NOT called with any URL containing `/api/upload/smart`. Maps to HOTFIX-01.1 + HOTFIX-01.4.

    - Test 2: "no detecting content type indicator" — same drop event; assert `screen.queryByText(/Detecting content type/i)` is null both immediately and after a `flushSync`/`await act` cycle. Maps to HOTFIX-01.1.

    - Test 3: "send delivers extracted content inline" — drop a file, then click send. Assert: the `uploadFile` override mock was called once with the dropped File; the `sendMessage` mock was called once with a string CONTAINING `**Attached File: doc.pdf**` and `extracted text`. Maps to HOTFIX-01.2.

    - Test 4: "upload failure renders single system message" — render with `uploadFile: vi.fn().mockResolvedValue({ result: null, error: 'Backend rejected' })`; drop a file; click send; assert `addMessage` was called EXACTLY once with an object whose `role === 'system'` and `text` contains `'Backend rejected'` AND the file's name; assert no spinner remains (`screen.queryByText(/Detecting content type/i)` is null and the input is not disabled by upload state after the failure resolves).

    - Test 5: "drop does not fetch smart endpoint" — explicit standalone assertion. Drop a file; advance any pending microtasks; assert `getFetchSpy()` was never called with a URL string matching the regex `/\/api\/upload\/smart/`. Maps to HOTFIX-01.4.
  </behavior>
  <action>
    1. Read existing `frontend/src/components/chat/ChatInterface.test.tsx` in full first (it's ~80+ lines) to confirm the existing 4 tests still use the inline `vi.mock('@/hooks/useAgentChat')` pattern. The new tests will use `renderChatInterface` from the harness instead. Both patterns can coexist in the same file — the harness's module-scope `vi.mock()` calls augment, not conflict with, the existing inline mock (vitest hoists `vi.mock` regardless of position).

    2. At the top of the file (after the existing imports), add:
       ```typescript
       import { renderChatInterface } from './__test-utils__/chatHarness'
       ```

    3. Add a new `describe('ChatInterface — file attach hotfix (HOTFIX-01)', () => { ... })` block at the bottom of the file (do NOT modify the existing describe block). Inside it, write the 5 tests defined in <behavior> above.

    4. Drag-drop simulation pattern (use this exact form, since FileDropZone uses native HTML5 drag events):
       ```typescript
       const dropZone = screen.getByTestId('chat-file-drop-zone'); // or query by role/text — verify the actual selector by reading FileDropZone.tsx FIRST
       const file = new File(['dummy content'], 'doc.pdf', { type: 'application/pdf' });
       const dataTransfer = { files: [file], items: [{ kind: 'file', type: 'application/pdf', getAsFile: () => file }], types: ['Files'] };
       fireEvent.drop(dropZone, { dataTransfer });
       ```
       If FileDropZone has no `data-testid`, query by its drop-target role or, as a fallback, `container.querySelector('[role="presentation"]')` after reading the actual implementation. Anti-pattern to avoid: never assume a selector — open `FileDropZone.tsx` and use the real element shape. (Why: jsdom does not synthesize drag-drop events from a CSS class alone.)

    5. For Test 3 (send), after the drop:
       ```typescript
       await waitFor(() => expect(screen.getByText(/doc\.pdf/)).toBeTruthy());
       const input = screen.getByPlaceholderText(/Type your message/i);
       fireEvent.change(input, { target: { value: 'Summarize this' } });
       const sendButton = screen.getAllByRole('button').find(b => /send/i.test(b.getAttribute('aria-label') ?? '')) ?? screen.getByRole('button');
       fireEvent.click(sendButton);
       await waitFor(() => expect(uploadFile).toHaveBeenCalledTimes(1));
       expect(sendMessage).toHaveBeenCalledTimes(1);
       const sentMessage = sendMessage.mock.calls[0][0] as string;
       expect(sentMessage).toContain('**Attached File: doc.pdf**');
       expect(sentMessage).toContain('extracted text');
       ```

    6. For Test 4 (failure), use:
       ```typescript
       const uploadFileMock = vi.fn().mockResolvedValue({ result: null, error: 'Backend rejected' });
       const addMessageMock = vi.fn();
       const { } = renderChatInterface({ uploadFile: uploadFileMock, addMessage: addMessageMock });
       // ... drop, click send, await waitFor(() => expect(uploadFileMock).toHaveBeenCalled())
       await waitFor(() => expect(addMessageMock).toHaveBeenCalledTimes(1));
       const call = addMessageMock.mock.calls[0][0];
       expect(call.role).toBe('system');
       expect(call.text).toMatch(/doc\.pdf/);
       expect(call.text).toMatch(/Backend rejected/);
       expect(screen.queryByText(/Detecting content type/i)).toBeNull();
       ```

    7. Run the 5 tests in isolation (filter by the new describe title): `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "file attach hotfix"`. **They MUST FAIL** at this stage — that's the RED step. Specifically:
       - Tests 1, 2, 5 will fail because `handleSmartUpload` is still being called and "Detecting content type" still renders.
       - Tests 3, 4 may pass partially (because handleSend already does the right thing), but the smart-upload toast intercept can interfere — record actual failure modes in a comment for Task 2 to verify the fix.

    8. Commit RED state: `git add frontend/src/components/chat/ChatInterface.test.tsx && git commit -m "test(83-02): add failing tests for HOTFIX-01 attach bypass"` (do NOT push).

    SUMMARY note: the test for criterion HOTFIX-01.2 verifies INLINE content delivery via `sendMessage` argument inspection, not via end-to-end SSE — that's intentional, the SSE flow is already covered elsewhere and is out of scope for this hotfix.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "file attach hotfix"</automated>
  </verify>
  <done>
    5 new tests added to ChatInterface.test.tsx under describe "ChatInterface — file attach hotfix (HOTFIX-01)". Running the focused vitest command shows all 5 FAILING (RED state). Existing 4 tests in the file still PASS. Test file committed (RED commit) with message `test(83-02): add failing tests for HOTFIX-01 attach bypass`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Rewrite handleFileAttach and delete smart-upload state, handlers, JSX, and import (GREEN)</name>
  <files>frontend/src/components/chat/ChatInterface.tsx</files>
  <behavior>
    After this task, all 5 tests from Task 1 turn GREEN, the 4 existing tests still pass, and `cd frontend && npm run lint` reports no new warnings on this file.

    The component should:
    - On any file drop or file-picker selection, push the file directly into `attachedFiles` (with name+size dedup) within one render tick.
    - Never call `/api/upload/smart`.
    - Never render "Detecting content type..." anywhere.
    - Continue to call `/api/upload` only on send (existing handleSend, untouched).
    - Continue to surface a single system message on upload failure (existing handleSend, untouched).
  </behavior>
  <action>
    Make the following edits to `frontend/src/components/chat/ChatInterface.tsx` IN THIS ORDER (the order matters — TypeScript will catch missed references between steps):

    **Step 1 — Rewrite handleFileAttach (lines 1262-1272). Replace with:**
    ```tsx
    const handleFileAttach = (file: File) => {
      if (isStreaming || isUploading) return;
      setAttachedFiles(prev => {
        const exists = prev.some(f => f.name === file.name && f.size === file.size);
        return exists ? prev : [...prev, file];
      });
    };
    ```
    This mirrors the existing multi-file branch (lines 1286-1295) — name+size dedup, no smart-upload call. Keep the `isStreaming || isUploading` guard.

    **Step 2 — Delete the "Detecting content type..." JSX (lines 1535-1540 in current file).** Remove the entire `{isSmartUploading && (<div>...Detecting content type...</div>)}` block.

    **Step 3 — Delete the SmartUploadToast JSX (lines 1513-1521).** Remove the `<SmartUploadToast result={smartUploadResult} ... />` block.

    **Step 4 — Delete the four smart-upload handlers (lines 1077-1259):** `handleSmartUpload`, `handleSmartUploadAddToVault`, `handleSmartUploadAnalyzeNow`, `handleSmartUploadDismiss`. Delete entire functions.

    **Step 5 — Delete the four smart-upload state variables (lines 122-130):** `smartUploadResult`/`setSmartUploadResult`, `isSmartUploading`/`setIsSmartUploading`, `isSmartUploadFollowupActive`/`setIsSmartUploadFollowupActive`, `smartUploadFile`/`setSmartUploadFile`. Remove all four `useState` calls.

    **Step 6 — Remove the import (line 12):** `import { SmartUploadToast, SmartUploadResult } from '@/components/chat/SmartUploadToast'`. Delete the entire line.

    **Step 7 — Audit `handleFilesAttach` (lines 1275-1296):** Confirm the single-file special-case (lines 1280-1283 calling `handleFileAttach(newFiles[0])`) still works correctly with the new direct-attach handleFileAttach. The existing branch already calls `handleFileAttach` for `length === 1` — the rewritten handleFileAttach is now equivalent to the multi-file path's logic, so behavior unifies. No change required to handleFilesAttach itself.

    **DO NOT delete:**
    - `frontend/src/components/chat/SmartUploadToast.tsx` — leave on disk (per RESEARCH.md "Open Questions" #1, deferred to follow-up cleanup).
    - `frontend/src/app/api/upload/smart/route.ts` — proxy stays (success criterion 4 explicitly allows).
    - `app/routers/files.py:742-807` smart_upload backend — out of scope.
    - `frontend/src/types/api.generated.ts` — auto-generated, out of scope.

    **DO NOT modify:**
    - `handleSend` (lines 858-958) — already correct, do not "improve" it.
    - The `isUploading || isStreaming` early return — keep it.
    - Drag-drop wiring at line 1331 (`<FileDropZone onFileDrop={handleFileAttach}>`) — still correct.

    **Verify between steps:** After steps 1-3, run `cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep ChatInterface | head -20`. There WILL be temporary errors (missing `setIsSmartUploading` etc) — they should resolve after step 5. After step 6, the same command should show NO errors mentioning ChatInterface.tsx (pre-existing errors in unrelated files are fine).

    **Run the failing tests now:**
    ```bash
    cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "file attach hotfix"
    ```
    All 5 tests must turn GREEN. If any fail, debug — do NOT modify the test assertions; the production code is wrong, fix it.

    **Run the full file to confirm no regressions on existing tests:**
    ```bash
    cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx
    ```
    All 9 tests (4 existing + 5 new) must pass.

    **Lint check:**
    ```bash
    cd frontend && npx eslint src/components/chat/ChatInterface.tsx
    ```
    No new warnings on this file.

    Commit GREEN state: `git add frontend/src/components/chat/ChatInterface.tsx && git commit -m "fix(83-02): bypass /api/upload/smart in chat attach (HOTFIX-01)"`.

    SUMMARY note for execute-phase: image files attach and send successfully, but the inline content delivered to the agent is a placeholder string like `[Image content cannot be extracted...]` because `app/routers/files.py::_extract_file_content` does not OCR images. This is by design and out of scope for this hotfix — flag in the SUMMARY.md so QA/UAT testers expect the placeholder behavior for the image case.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx</automated>
  </verify>
  <done>
    All 9 tests in ChatInterface.test.tsx pass (4 existing + 5 new HOTFIX-01 behavior tests). `npx eslint src/components/chat/ChatInterface.tsx` reports no new warnings. ChatInterface.tsx no longer imports SmartUploadToast, no longer contains `isSmartUploading` or `handleSmartUpload`, and no longer renders "Detecting content type...". File reduced by ~120 lines net. GREEN commit exists with message `fix(83-02): bypass /api/upload/smart in chat attach (HOTFIX-01)`.
  </done>
</task>

<task type="auto">
  <name>Task 3: Full vitest suite + lint pass + checkpoint summary</name>
  <files>(none — verification-only)</files>
  <action>
    1. Run the full frontend test suite: `cd frontend && npm test`. Must be GREEN. (Pre-existing failures in unrelated files should not be present at HEAD per STATE.md — if any appear, document them in the summary as "pre-existing, not caused by this hotfix" and confirm by checking out main + running the same command.)

    2. Run the full lint: `cd frontend && npm run lint`. Must be clean (or no NEW warnings vs main).

    3. TypeScript safety: `cd frontend && npx tsc --noEmit -p tsconfig.json`. Confirm no errors anywhere referencing ChatInterface.tsx, SmartUploadToast (might warn about unused exports if no other files import it — that's expected, document it), or chatHarness.

    4. Manual UAT preparation note (do not actually run UAT in this task — UAT is a separate phase gate per VALIDATION.md):
       - Backend startup: `make local-backend`
       - Frontend startup: `cd frontend && npm run dev`
       - 4 test files needed at hand: a small PDF, DOCX, XLSX, and JPG/PNG.
       - Expected outcomes per RESEARCH.md "Open Questions" #3: PDF/DOCX/XLSX deliver real extracted text; image delivers a placeholder string but the file still attaches and sends and the agent responds.
       - Failure path: stop the backend, drop a file, send — confirm a single system message appears and the input becomes usable again (no infinite spinner).

    5. Document the manual UAT checklist in `83-02-SUMMARY.md` (per the <output> block below) so `/gsd:verify-work` and any human UAT reviewer have a clear script to follow.
  </action>
  <verify>
    <automated>cd frontend && npm test && cd frontend && npm run lint</automated>
  </verify>
  <done>
    Full vitest suite GREEN. Frontend lint clean (no NEW warnings introduced by this PR). TypeScript compile clean for ChatInterface.tsx and chatHarness. SUMMARY.md drafted with manual UAT script and the image-extraction-placeholder caveat documented for QA.
  </done>
</task>

</tasks>

<verification>
**Per-task automated verification (matches `83-VALIDATION.md` Per-Task Verification Map):**

| Task | Command | Maps To |
|------|---------|---------|
| 1 (RED) | `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "file attach hotfix"` (must FAIL) | HOTFIX-01.1, .2, .3, .4 (all 5 sub-tests) |
| 2 (GREEN) | `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx` (must PASS, all 9 tests) | HOTFIX-01.1, .2, .3, .4 |
| 3 (Suite) | `cd frontend && npm test` (must PASS) and `cd frontend && npm run lint` (must be clean) | Phase gate |

**Behavior assertions covering the four ROADMAP success criteria:**
1. ✅ "drop attaches without smart" + "no detecting content type indicator" → success criterion 1
2. ✅ "send delivers extracted content inline" → success criterion 2
3. ✅ "upload failure renders single system message" → success criterion 3
4. ✅ "drop does not fetch smart endpoint" → success criterion 4

**Manual UAT (deferred to phase gate, not this plan):** Drop each of PDF / DOCX / XLSX / image into chat → pill within ≤1s, no toast, send → agent reply. Stop backend, drop, send → single system message, no spinner.
</verification>

<success_criteria>
- All four ROADMAP success criteria for Phase 83 are observable in the rendered DOM and verifiable via the 5 new vitest behavior tests.
- The git diff for this plan is purely subtractive in production code (~120 lines deleted, ~6 added in ChatInterface.tsx) plus additive in tests (5 new tests + harness import).
- The smart-upload proxy at `frontend/src/app/api/upload/smart/route.ts` is untouched (preserves criterion 4).
- The backend `/upload/smart` endpoint at `app/routers/files.py:742-807` is untouched.
- `frontend/src/components/chat/SmartUploadToast.tsx` remains on disk as dead code (per RESEARCH.md decision; cleanup deferred).
</success_criteria>

<output>
After completion, create `.planning/phases/83-document-upload-bypass/83-02-SUMMARY.md` documenting:
1. **What changed:** handleFileAttach rewritten, smart-upload state/handlers/JSX/import deleted from ChatInterface.tsx.
2. **What stayed:** /api/upload/smart proxy and backend endpoint, handleSend logic, SmartUploadToast.tsx component file (dead code, follow-up cleanup).
3. **Test coverage added:** 5 behavior tests in describe "ChatInterface — file attach hotfix (HOTFIX-01)" mapping to all four ROADMAP success criteria.
4. **QA caveat — image files:** /api/upload returns a placeholder string for image extraction (`[Image content cannot be extracted...]`). The image still attaches as a pill and the message still sends — this is by design and out of scope for this hotfix. UAT testers should expect the placeholder text, not real image content/OCR.
5. **Manual UAT script:** the 5-step procedure from VALIDATION.md "Manual-Only Verifications" — drop each of PDF/DOCX/XLSX/image, send, observe; force backend failure to confirm single system message + recoverable UI.
6. **Follow-up cleanup tracking (NOT in this PR):** delete `frontend/src/components/chat/SmartUploadToast.tsx`, the `SmartUploadResult` interface, the `frontend/src/app/api/upload/smart/route.ts` proxy + tests, and the backend `smart_upload` endpoint (`app/routers/files.py:742-807`) once we're confident no consumers remain. Track in next `RETROSPECTIVE.md` cycle.
7. **Diff size confirmation:** ~120 lines deleted, ~6 added in production; pure subtractive hotfix, single-revert friendly.
</output>
