---
phase: 83-document-upload-bypass
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/chat/__test-utils__/chatHarness.ts
  - frontend/src/components/chat/__test-utils__/chatHarness.test.tsx
autonomous: true
requirements:
  - HOTFIX-01
must_haves:
  truths:
    - "renderChatInterface() helper renders <ChatInterface /> in jsdom without throwing"
    - "All 11 module-scope hooks in ChatInterface.tsx are pre-mocked with stable defaults"
    - "Per-test override mechanism exists for useFileUpload.uploadFile and global fetch"
  artifacts:
    - path: "frontend/src/components/chat/__test-utils__/chatHarness.ts"
      provides: "renderChatInterface(opts) helper that pre-mocks every hook used at module top-level in ChatInterface.tsx, plus supabase/client.createClient"
      min_lines: 80
    - path: "frontend/src/components/chat/__test-utils__/chatHarness.test.tsx"
      provides: "Smoke test confirming the harness renders without throwing and override hooks function"
      min_lines: 20
  key_links:
    - from: "chatHarness.ts"
      to: "vi.mock('@/hooks/useFileUpload', ...)"
      via: "module-scope vi.mock calls hoisted by vitest"
      pattern: "vi\\.mock\\(['\"]@/hooks/useFileUpload"
    - from: "chatHarness.ts"
      to: "vi.mock('@/lib/supabase/client', ...)"
      via: "createClient() returns a benign chainable stub"
      pattern: "createClient"
---

<objective>
Build a reusable test harness that allows component-level tests to render `<ChatInterface />` in jsdom without per-test re-mocking of 10+ module-scope hooks. This unblocks Plan 02's behavior tests.

Purpose: `ChatInterface.tsx` imports useAgentChat, useFileUpload, usePresence, useRealtimeSession, useSessionControl, useSessionMap, useTextToSpeech, useSpeechRecognition, useVoiceSession, usePersona, and `supabase/client.createClient` at module scope. The existing `ChatInterface.test.tsx` only mocks `useAgentChat` and gets away with it because that mock blocks the early code path. The Plan 02 tests need a deeper render to fire drag-drop events and inspect the attached-file pill — that requires every hook to have a benign default mock.

Output: `chatHarness.ts` exporting a `renderChatInterface(opts?)` helper with override hooks for the two things tests need to control (`uploadFile` mock, global `fetch` spy), plus a smoke test proving the harness works.
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

# Source files the harness mocks against
@frontend/src/components/chat/ChatInterface.tsx
@frontend/src/components/chat/ChatInterface.test.tsx
@frontend/src/hooks/useFileUpload.ts
@frontend/vitest.config.mts

<interfaces>
<!-- Module-scope imports in ChatInterface.tsx (lines 7-34) that the harness MUST mock -->
<!-- Every hook below is called unconditionally on first render — a missing mock crashes jsdom. -->

From frontend/src/components/chat/ChatInterface.tsx (top-of-file imports):
```typescript
import { useAgentChat, AgentMode } from '@/hooks/useAgentChat'
import { useFileUpload } from '@/hooks/useFileUpload'
import { useTextToSpeech } from '@/hooks/useTextToSpeech'
import { usePresence } from '@/hooks/usePresence'
import { useRealtimeSession } from '@/hooks/useRealtimeSession'
import { useSessionControl } from '@/contexts/SessionControlContext'
import { useSessionMap } from '@/contexts/SessionMapContext'
import { useSpeechRecognition } from '@/hooks/useSpeechRecognition'
import { useVoiceSession } from '@/hooks/useVoiceSession'
import { createClient } from '@/lib/supabase/client'
import { usePersona } from '@/contexts/PersonaContext'
```

From frontend/src/hooks/useFileUpload.ts (the contract Plan 02 will exercise):
```typescript
export interface UploadResult {
  filename: string;
  content: string;
  summary_prompt?: string;
}
export interface UploadOutcome {
  result: UploadResult | null;
  error: string | null;
}
export function useFileUpload(): {
  uploadFile: (file: File) => Promise<UploadOutcome>;
  uploadFileToVault: (file: File) => Promise<UploadOutcome>;
  isUploading: boolean;
};
```

From frontend/src/components/chat/ChatInterface.test.tsx (existing useAgentChat mock shape — preserve compatibility):
```typescript
vi.mocked(useAgentChat).mockReturnValue({
  messages: [...],
  sendMessage: vi.fn(),
  isStreaming: false,
  addMessage: vi.fn(),
  toggleWidgetMinimized: vi.fn(),
  isLoadingHistory: false,
  pinWidget: vi.fn(),
  sessionId: 'test-session-id',
  getSessionId: vi.fn(() => 'test-session-id'),
  stopGeneration: vi.fn(),
})
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create chatHarness.ts with module-scope mocks for all ChatInterface hooks</name>
  <files>frontend/src/components/chat/__test-utils__/chatHarness.ts, frontend/src/components/chat/__test-utils__/chatHarness.test.tsx</files>
  <behavior>
    The harness exports a `renderChatInterface(opts?)` function. Tests call it instead of `render(<ChatInterface />)` directly.

    Required behavior:
    - Test 1 (smoke): `renderChatInterface()` returns a `RenderResult` (from @testing-library/react) and the rendered output contains the chat input placeholder text `/Type your message/i`. No exceptions thrown.
    - Test 2 (uploadFile override): `renderChatInterface({ uploadFile: vi.fn().mockResolvedValue({ result: { filename: 'a.pdf', content: 'X', summary_prompt: '' }, error: null }) })` — the override is the function returned by useFileUpload().uploadFile inside the component.
    - Test 3 (addMessage exposure): the harness returns `{ addMessage, sendMessage, ...renderResult }` so behavior tests can assert on agent-chat callbacks without redoing the useAgentChat mock.
    - Test 4 (fetch spy): a `getFetchSpy()` helper returns the `vi.spyOn(global, 'fetch')` instance; tests can assert calls. Default implementation returns `Promise.resolve(new Response(null, { status: 200 }))` so any incidental fetches (Supabase, etc.) don't crash.
  </behavior>
  <action>
    1. Create directory `frontend/src/components/chat/__test-utils__/` if it doesn't exist (verify via `ls frontend/src/components/chat/__test-utils__ 2>/dev/null` first; do NOT use `mkdir -p` until confirmed).

    2. Write `frontend/src/components/chat/__test-utils__/chatHarness.ts`:
       - Use `vi.mock('@/hooks/...')` and `vi.mock('@/contexts/...')` at module scope for ALL of: useAgentChat, useFileUpload, useTextToSpeech, usePresence, useRealtimeSession, useSessionControl, useSessionMap, useSpeechRecognition, useVoiceSession, usePersona, AND `@/lib/supabase/client` (mock `createClient` to return a chainable stub: `{ from: () => ({ select: () => ({ eq: () => ({ data: [], error: null }) }) }), auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }) }, channel: () => ({ on: () => ({ subscribe: vi.fn() }), unsubscribe: vi.fn() }) }`).
       - Export `interface RenderChatOptions { uploadFile?: ReturnType<typeof vi.fn>; messages?: any[]; isStreaming?: boolean; addMessage?: ReturnType<typeof vi.fn>; sendMessage?: ReturnType<typeof vi.fn>; }`.
       - Export `function renderChatInterface(opts: RenderChatOptions = {})`:
         a. Resets all hook mocks each call: `vi.mocked(useAgentChat).mockReturnValue({...})`, `vi.mocked(useFileUpload).mockReturnValue({ uploadFile: opts.uploadFile ?? vi.fn().mockResolvedValue({ result: { filename: 'mock.txt', content: 'mock content', summary_prompt: '' }, error: null }), uploadFileToVault: vi.fn(), isUploading: false })`.
         b. For useAgentChat default values: match the existing test file's shape (line 23-34 of ChatInterface.test.tsx) — preserve `addMessage`, `sendMessage`, `toggleWidgetMinimized`, `isLoadingHistory: false`, `pinWidget`, `sessionId: 'test-session-id'`, `getSessionId`, `stopGeneration`. Allow `opts.messages`, `opts.isStreaming`, `opts.addMessage`, `opts.sendMessage` to override defaults.
         c. Stub the remaining hooks with safe no-op return shapes:
            - `usePresence()` -> `{ presentUsers: [], joinSession: vi.fn(), leaveSession: vi.fn() }` (read the actual hook signature first via `Read frontend/src/hooks/usePresence.ts` if uncertain; match what ChatInterface.tsx destructures).
            - `useRealtimeSession()` -> `{ /* benign defaults matching destructured fields */ }`.
            - `useSessionControl()` and `useSessionMap()` -> empty/stub objects matching the contexts' value types.
            - `useTextToSpeech()` -> `{ speak: vi.fn(), stop: vi.fn(), isSpeaking: false }`.
            - `useSpeechRecognition()` -> `{ start: vi.fn(), stop: vi.fn(), transcript: '', isListening: false, isSupported: true }`.
            - `useVoiceSession()` -> `{ start: vi.fn(), stop: vi.fn(), state: 'idle', /* whatever ChatInterface destructures */ }`.
            - `usePersona()` -> `{ persona: 'general', personaConfig: { /* benign */ } }`.
            - For each: open the actual hook file with Read FIRST and copy the return-type shape; do NOT guess. Anti-pattern to avoid: hand-rolling hook signatures from memory will produce TypeError on render and you'll spin debugging.
         d. Mocks `window.HTMLElement.prototype.scrollIntoView = vi.fn()` (matches existing test line 21).
         e. Sets up `vi.spyOn(global, 'fetch').mockImplementation(async () => new Response(null, { status: 200 }))` and stores the spy in a module-level `__fetchSpy` for `getFetchSpy()` to return.
         f. Renders `<ChatInterface />` via `@testing-library/react`'s `render()` and returns `{ ...renderResult, addMessage: <the mock from useAgentChat>, sendMessage: <ditto>, uploadFile: <the mock from useFileUpload>, getFetchSpy: () => __fetchSpy }`.
       - Do NOT use jsonwebtoken-style imports — this is purely test-utility code. Use `vi.fn()` from vitest.

    3. Write `frontend/src/components/chat/__test-utils__/chatHarness.test.tsx` with one `describe('chatHarness')` and four `it(...)` covering the four behaviors above. Use `@testing-library/react`'s `screen` and `cleanup`. Add `afterEach(() => { cleanup(); vi.clearAllMocks(); })`.

    4. Run `cd frontend && npx vitest run src/components/chat/__test-utils__/chatHarness.test.tsx` — must be GREEN.

    5. Sanity check: `cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep chatHarness` — must show NO errors. (If tsc reports type errors in unrelated files, that's pre-existing; only fail if errors mention chatHarness.)

    Reference: see `.planning/phases/83-document-upload-bypass/83-RESEARCH.md` § "Wave 0 Gaps" (lines 211-216) for the exhaustive hook list, and § "Implementation Notes" → "Gotchas" (lines 254-260) for the uploadFile mock shape.

    SUMMARY note for execute-phase to surface: This harness is a test-only utility — no production code paths change. The harness is intentionally permissive (returns benign defaults for all hooks); behavior tests in Plan 02 must override only what they assert on. If a future ChatInterface.tsx change adds a new module-scope hook, the harness needs updating in tandem.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/components/chat/__test-utils__/chatHarness.test.tsx</automated>
  </verify>
  <done>
    chatHarness.ts exists with all 11 module-scope mocks in place and exports renderChatInterface() with the documented override surface. chatHarness.test.tsx has 4 passing tests proving smoke-render, uploadFile override, addMessage/sendMessage exposure, and fetch-spy access. No TypeScript errors mentioning chatHarness in `tsc --noEmit`.
  </done>
</task>

</tasks>

<verification>
- [ ] `cd frontend && npx vitest run src/components/chat/__test-utils__/chatHarness.test.tsx` is GREEN (4 tests pass)
- [ ] `frontend/src/components/chat/__test-utils__/chatHarness.ts` exists and exports `renderChatInterface`, `RenderChatOptions`
- [ ] No type errors in `cd frontend && npx tsc --noEmit` that reference chatHarness
- [ ] Existing `frontend/src/components/chat/ChatInterface.test.tsx` still passes (`cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx`) — harness must not regress the 4 existing tests
</verification>

<success_criteria>
- Plan 02 can `import { renderChatInterface, type RenderChatOptions } from './__test-utils__/chatHarness'` and call `const { getFetchSpy, addMessage, uploadFile } = renderChatInterface({ uploadFile: vi.fn(...) })` to write its 5 behavior tests with zero per-test hook re-mocking.
</success_criteria>

<output>
After completion, create `.planning/phases/83-document-upload-bypass/83-01-SUMMARY.md` documenting:
- The 11 hooks mocked at module scope (list each with the destructured field shape used)
- The override surface of `RenderChatOptions`
- Note that this harness is reusable for any future ChatInterface tests, not just Phase 83
- Flag for QA: harness uses `Response` (jsdom polyfill) — if vitest config changes test environment to `node`, the global Response mock will need adjustment
</output>
