# Document Viewer Widget — Track B Design

> **Status:** DRAFT FOR REVIEW (2026-05-05).
> **Depends on:** `docs/superpowers/plans/2026-04-28-workspace-agent-canvas-phase2.md` (Track A — workspace command surface). Track B's `view_document_page` and `toggle_editor_sidebar` extend Track A's `workspace_command` enum, and the back-channel events extend Track A's `workspace_events` table.
> **Replaces:** today's `frontend/src/components/widgets/DocumentWidget.tsx` for *workspace canvas* usage. The download-chip variant stays in chat surfaces.

---

## 1. Goal

Give every document the user touches — agent-created PDFs/XLSX/PPTX/DOCX, user uploads, Google Docs/Sheets — an in-workspace viewer the agent can both **read content from** and **drive the user's view of**. Editing happens through the agent: the user types intent into a collapsible sidebar ("rewrite slide 2"), the agent mutates a canonical source, the binary re-renders, the viewer refreshes.

This widget is the first concrete client of Track A's command surface. If Track A gives agents a steering wheel for the workspace, Track B is the first vehicle that needs steering.

**Why now:** today's `DocumentWidget` is a download chip. Click → file opens in a new tab → agent has zero awareness of what's inside. Generating a doc and immediately losing all visibility into it breaks the "agent in full control" thesis.

**Tech stack:** Python 3.10+ (FastAPI, Google ADK, Pydantic), TypeScript/React 19 (Next.js), Supabase (PostgreSQL with JSONB + RLS), `react-pdf`, `react-data-grid`, `mammoth.js`, `react-markdown` (already in deps), `python-pptx` (already in deps), LibreOffice headless (for PPTX→PNG slide rendering), pytest with pytest-asyncio, Vitest with jsdom, uv (package manager), ruff (lint), ty (type checking).

---

## 2. Architecture Summary

### 2.1 Three document classes

| Class | Storage | Source of truth | Agent edits via |
|---|---|---|---|
| **Agent-created** (PDF/XLSX/PPTX/DOCX) | Supabase Storage (binary) + `document_sources` (JSONB source) | Source JSONB; binary is *derived output* | `edit_report_doc` / `edit_spreadsheet` / `edit_presentation` / `edit_word_doc` |
| **User-uploaded** | Supabase Vault (binary) | Binary at upload; **lazy-extracted** to JSONB source on first agent edit (forked-to-editable) | Same per-format tools after fork |
| **Google Docs** | User's Drive | Google API itself | `edit_google_doc` (uses existing `app/integrations/google/docs.py`, extended with read + section-edit) |
| **Google Sheets** | User's Drive | Google Sheets API | `edit_spreadsheet` — same tool as local XLSX, dispatches internally on `doc_class` |

Google Slides deferred. PowerPoint files stay PPTX, no Slides round-trip.

### 2.2 Lazy "fork to editable"

```
User uploads PDF
  ↓
Lives in Vault. No row in document_sources.
Viewer renders binary directly via react-pdf.
  ↓
[Agent's first read_document_content call]
  ↓
Extract text + structure → cache in document_sources.extracted_text
(no source JSON yet — read-only path)
  ↓
[Agent's first edit_*_doc call]
  ↓
Generate source JSONB (PDF→sectioned markdown, XLSX→sheet schema,
  PPTX→slide JSON, DOCX→markdown). Mark forked_from_upload=true.
Re-render binary from source. Original kept as v0 in document_versions.
  ↓
From here on: identical pipeline as agent-created docs.
```

### 2.3 Forward channel (agent → viewer)

```
Agent calls workspace_update(commands=[
    {action: "view_document_page", payload: {itemId, page: 3}}
])
  ↓
[Track A pipeline: SSE post-processor → sseParser → useBackgroundStream
 → dispatchWorkspaceCommand → ActiveWorkspace]
  ↓
DocumentViewerWidget receives command → scrolls to page 3 + emits
back-channel event "document_page_viewed"
```

### 2.4 Edit channel (sidebar → agent → re-render)

```
User types in sidebar chat: "make slide 3 more concise"
  ↓
Message routed through normal SSE chat path with metadata:
  scope = {document_id, current_page, doc_class}
  ↓
Agent's pre-turn callback injects:
  - Doc summary (title, type, structure)
  - Current page text (from document_sources.extracted_text)
  - Last 5 versions
  ↓
Agent calls edit_presentation(doc_id, op="edit_text", slide_index=3, content="...")
  ↓
Tool:
  1. Mutate document_sources.source (JSONB)
  2. Re-render PPTX via document_service.render_pptx(source)
  3. Pre-render slide PNGs (only changed slide(s))
  4. Insert row into document_versions
  5. Update document_sources.updated_at
  6. Return {new_version_id, new_render_url, diff_summary}
  ↓
SSE event with workspace_command "replace_active" carries the new
DocumentViewerWidget definition pointing at the new render_url.
Viewer iframe refreshes; sidebar shows agent confirmation message.
```

### 2.5 Undo

User clicks `↶ Undo` in version strip
  ↓
`POST /a2a/sessions/{id}/workspace_events` with `event_type=document_version_reverted`, `payload={target_version_id}`
  ↓
Endpoint: re-point `document_sources` at the target version's snapshot, regenerate render, return new `render_url`
  ↓
Same `replace_active` SSE event refreshes viewer

Undo is reversible — clicking it again redoes (forward through version chain).

---

## 3. File Plan

### 3.1 Backend

**Create:**
- `app/agents/tools/document_editor.py` — five edit tools + read tool + version tool (Section 4a)
- `app/services/document_extraction_service.py` — lazy extraction pipeline per format (PDF.js → pdfplumber, XLSX → openpyxl, PPTX → python-pptx, DOCX → python-docx)
- `app/services/document_source_service.py` — read/write `document_sources` table; binary regen
- `app/services/document_version_service.py` — version row insert; revert
- `app/services/slide_image_service.py` — PPTX → per-slide PNG via LibreOffice headless + `pdf2image`
- `app/routers/document_viewer.py` — `GET /documents/{id}/source`, `GET /documents/{id}/versions`, `POST /documents/{id}/revert`
- `supabase/migrations/20260505120000_document_editor.sql` — `document_sources` + `document_versions` tables + RLS
- `app/agents/tools/google_docs_extended.py` — extends existing Google Docs tool with `read_google_doc_content`, `replace_google_doc_section`

**Modify:**
- `app/services/document_service.py` — extract `render_pdf` / `render_xlsx` / `render_pptx` / `render_docx` as pure functions taking source JSON, returning bytes (already mostly true after commit `898194ea`; just make signatures uniform)
- `app/integrations/google/docs.py` — add `read_doc_content(doc_id)` and `replace_section(doc_id, anchor, content)`; existing append/create stay
- `app/agents/tools/__init__.py` — export new tools
- `app/agents/shared_instructions.py` — add `DOCUMENT_EDITOR_INSTRUCTION` block
- `app/fast_api_app.py` — register `document_viewer` router
- `app/sse_workspace_commands.py` (Track A file) — add `view_document_page` and `toggle_editor_sidebar` to allowed actions

**Test:**
- `app/tests/unit/test_document_extraction_service.py` — round-trip PDF/XLSX/PPTX/DOCX → source → re-render produces functionally equivalent output (text content matches; binary equality not required)
- `app/tests/unit/test_document_source_service.py`
- `app/tests/unit/test_document_version_service.py` — version insert, revert, redo
- `app/tests/unit/test_slide_image_service.py` — PPTX with 5 slides yields 5 PNGs
- `app/tests/unit/test_document_editor_tools.py` — each of the five edit tools returns the expected `_workspace_command`-style envelope and produces an updated `document_sources` row
- `app/tests/integration/test_document_viewer_router.py`
- `app/tests/integration/test_lazy_fork_to_editable.py` — upload PDF → first edit triggers extraction → source JSON appears → second edit reuses source

### 3.2 Frontend

**Create:**
- `frontend/src/components/widgets/DocumentViewerWidget.tsx` — main widget (renderer dispatch + sidebar)
- `frontend/src/components/widgets/document-viewer/PdfViewer.tsx` — `react-pdf` wrapper with page nav + highlight overlay
- `frontend/src/components/widgets/document-viewer/SheetViewer.tsx` — `react-data-grid` read-only with sheet tabs
- `frontend/src/components/widgets/document-viewer/SlideViewer.tsx` — slide strip + selected slide image
- `frontend/src/components/widgets/document-viewer/DocViewer.tsx` — `mammoth.js` HTML render
- `frontend/src/components/widgets/document-viewer/MarkdownViewer.tsx` — `react-markdown` (reuse from MarkdownReportWidget)
- `frontend/src/components/widgets/document-viewer/GoogleEmbedViewer.tsx` — iframe with `/preview` URL
- `frontend/src/components/widgets/document-viewer/EditorSidebar.tsx` — outline + scoped chat panel + version strip
- `frontend/src/components/widgets/document-viewer/VersionStrip.tsx` — current version indicator + Undo/Redo
- `frontend/src/services/documentEditor.ts` — typed client for `/documents/{id}/source`, versions, revert
- `frontend/src/types/documents.ts` — `DocClass`, `DocumentSource`, `DocumentVersion`, `DocumentViewerWidgetData`

**Modify:**
- `frontend/src/components/widgets/WidgetRegistry.tsx` — register `document_viewer` type
- `frontend/src/types/widgets.ts` — add `DocumentViewerWidgetData`, extend `WidgetType` union, mark `'document_viewer'` as workspace-canvas-eligible (i.e., NOT in `DASHBOARD_ONLY_WIDGET_TYPES`)
- `frontend/src/services/workspaceCommands.ts` (Track A file) — extend `WorkspaceCommand` union with `view_document_page` and `toggle_editor_sidebar`
- `frontend/src/components/dashboard/ActiveWorkspace.tsx` — handle the two new command actions
- `frontend/src/components/widgets/DocumentWidget.tsx` — keep existing chip behavior in chat; in workspace canvas, switch to `DocumentViewerWidget` (controlled by widget data shape)

**Test:**
- `frontend/src/components/widgets/__tests__/DocumentViewerWidget.test.tsx` — renderer dispatch by file type
- `frontend/src/components/widgets/document-viewer/__tests__/PdfViewer.test.tsx` — page nav events emit `document_page_viewed` back-channel POST
- `frontend/src/components/widgets/document-viewer/__tests__/EditorSidebar.test.tsx` — collapse/expand toggle, scoped chat, version strip undo
- `frontend/src/components/widgets/document-viewer/__tests__/SlideViewer.test.tsx` — strip click navigates + emits page event
- `frontend/src/services/__tests__/documentEditor.test.ts`

---

## 4. Tool Surface (concrete shapes)

### 4a. Read tool

```python
# app/agents/tools/document_editor.py

@agent_tool
def read_document_content(
    tool_context: ToolContextType,
    document_id: str,
    page_range: list[int] | None = None,  # 1-indexed; None = whole doc (capped)
) -> dict[str, Any]:
    """Read text + structure from a document into the agent's context.

    Use when the user asks about a doc's contents, references something
    inside it, or before calling any edit_* tool that needs the current
    state to make a sensible change. Triggers lazy text extraction on
    first call for user uploads.

    Returns:
        text: extracted text (capped at ~10K tokens; summarized above)
        structure: type, page_count, sheet_names, slide_count, outline
        truncated: bool — true when content exceeded the token cap
    """
```

### 4b. Five edit tools (one per class)

```python
@agent_tool
def edit_report_doc(
    tool_context: ToolContextType,
    document_id: str,
    op: Literal["replace_section", "append_section", "rewrite"],
    target: str | None = None,        # heading anchor for replace_section
    content: str = "",                # markdown
) -> dict[str, Any]:
    """Edit a markdown-source report (PDF or DOCX rendered from markdown).

    Mutates the canonical source, re-renders the binary, returns the new
    render URL. Creates a new version row. Use after read_document_content
    so you know the current structure.
    """

@agent_tool
def edit_spreadsheet(
    tool_context: ToolContextType,
    document_id: str,
    op: Literal["set_cell", "insert_row", "delete_row", "set_formula", "rename_sheet"],
    sheet: str,
    cell: str | None = None,          # "A1" form
    row: int | None = None,           # 1-indexed for insert/delete
    values: list[Any] | None = None,
    formula: str | None = None,
) -> dict[str, Any]:
    """Edit an XLSX/CSV spreadsheet OR a Google Sheet.

    Dispatches by document class: local XLSX/CSV mutates the source via
    openpyxl and re-renders; Google Sheets uses the Sheets API directly.
    Caller doesn't need to distinguish — the tool reads doc_class from
    document_sources and routes appropriately.
    """

@agent_tool
def edit_presentation(
    tool_context: ToolContextType,
    document_id: str,
    op: Literal["edit_text", "replace_image", "insert_slide", "delete_slide", "reorder", "set_speaker_notes"],
    slide_index: int | None = None,   # 0-indexed
    text_anchor: str | None = None,   # placeholder/shape ID; None = title
    content: str = "",
    new_order: list[int] | None = None,  # for reorder
    image_url: str | None = None,
) -> dict[str, Any]:
    """Edit a PPTX presentation. Re-renders the slide image strip on the
    affected slides only (not the whole deck — performance)."""

@agent_tool
def edit_word_doc(
    tool_context: ToolContextType,
    document_id: str,
    op: Literal["replace_paragraph", "append", "set_heading", "insert_table"],
    anchor: str | None = None,        # heading text or paragraph ID
    content: str = "",
) -> dict[str, Any]:
    """Edit a DOCX. Returns updated render URL."""

@agent_tool
def edit_google_doc(
    tool_context: ToolContextType,
    document_id: str,                 # this is the Google Doc ID
    op: Literal["replace_section", "append", "set_heading", "delete_section"],
    anchor: str | None = None,
    content: str = "",
) -> dict[str, Any]:
    """Edit a Google Doc. Calls Docs API directly. No binary re-render —
    the iframe reflects the new state automatically. Still creates a
    version row in document_versions for undo support."""
```

### 4c. Version tool

```python
@agent_tool
def list_document_versions(
    tool_context: ToolContextType,
    document_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    """List recent versions. Use when the user asks 'what did you change'
    or to find a version to revert to."""
```

Reverting via UI undo button does NOT need a tool — it's a `POST /documents/{id}/revert` direct from frontend, bypassing the agent.

### 4d. Track A workspace_command extensions

Extends the union in `frontend/src/services/workspaceCommands.ts`:

```ts
| { action: 'view_document_page'; payload: { itemId: string; page: number | string } }
| { action: 'toggle_editor_sidebar'; payload: { itemId: string; expanded: boolean } }
```

Backend extractor (`app/sse_workspace_commands.py`) accepts both in its allowlist.

### 4e. Track A workspace_events extensions

`workspace_events.event_type` CHECK constraint extended with:

```sql
'document_page_viewed', 'document_version_reverted'
```

Pre-turn callback (Track A's `active_workspace_items`) automatically picks up these events.

---

## 5. Database

```sql
-- supabase/migrations/20260505120000_document_editor.sql

CREATE TABLE document_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    document_id UUID NOT NULL UNIQUE,         -- one source per logical document
    doc_class TEXT NOT NULL CHECK (doc_class IN
        ('report','spreadsheet','presentation','word','google_doc','google_sheet')),
    source JSONB,                             -- canonical source; NULL until first extract+edit
    extracted_text TEXT,                      -- cached text for read_document_content
    extracted_at TIMESTAMPTZ,
    forked_from_upload BOOLEAN DEFAULT false,
    binary_url TEXT,                          -- signed URL of current render (NULL for google_*)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_document_sources_user ON document_sources(user_id);
CREATE INDEX idx_document_sources_doc ON document_sources(document_id);

CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source_snapshot JSONB,                    -- NULL for v0 (original upload, binary only)
    binary_url TEXT NOT NULL,                 -- signed URL at this version
    diff_summary TEXT,
    created_by TEXT NOT NULL CHECK (created_by IN ('agent','user','system')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_document_versions_doc ON document_versions(document_id, created_at DESC);

ALTER TABLE document_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see their own document sources"
    ON document_sources FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert their own document sources"
    ON document_sources FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users update their own document sources"
    ON document_sources FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Service role full access on document_sources"
    ON document_sources FOR ALL USING (auth.role() = 'service_role');

-- Same RLS pattern on document_versions.
```

---

## 6. Verification

### 6.1 Per-format round trip
- [ ] Generate a 3-section markdown report → render PDF. Agent calls `edit_report_doc(op="replace_section", target="Summary", content="new summary")`. Re-render. Page 1 contains "new summary"; pages 2-3 unchanged.
- [ ] Generate XLSX with 2 sheets, 10 rows each. Agent calls `edit_spreadsheet(op="set_cell", sheet="Sheet1", cell="B5", values=["42"])`. Re-render. Cell B5 = 42.
- [ ] Generate 5-slide PPTX. Agent calls `edit_presentation(op="edit_text", slide_index=2, content="...")`. Re-render. Slide 3 image PNG updated; slides 1, 2, 4, 5 PNGs unchanged (timestamp check).
- [ ] Generate DOCX from markdown. Agent calls `edit_word_doc(op="replace_paragraph", anchor="...", content="...")`. Re-render. Paragraph replaced.

### 6.2 Lazy fork
- [ ] User uploads `report.pdf`. No row in `document_sources`. Viewer renders via PDF.js direct from binary.
- [ ] Agent calls `read_document_content`. Row created with `extracted_text` populated; `source=NULL`.
- [ ] Agent calls `edit_report_doc(op="rewrite", content="...")`. Source JSON generated, `forked_from_upload=true`. `document_versions` has v0 (original PDF) and v1 (re-rendered).
- [ ] Click Undo on v1. View reverts to v0 PDF. Click Redo. View flips to v1.

### 6.3 Agent-driven view
- [ ] Agent emits `view_document_page(itemId="doc-1", page=3)`. PDF viewer scrolls to page 3 in <500ms.
- [ ] Agent emits `toggle_editor_sidebar(expanded=true)`. Sidebar opens.
- [ ] User scrolls to page 5 manually. `POST /a2a/sessions/{id}/workspace_events` fires with `event_type=document_page_viewed, payload={page: 5}`. Next agent turn's `active_workspace_items` summary contains "page 5 currently viewed".

### 6.4 Sidebar
- [ ] Click ✏ icon → sidebar expands. Click again → collapses. State persists per-doc per-session.
- [ ] Type "make slide 3 more concise" → agent processes → re-render → confirmation message in sidebar chat.
- [ ] Switch to a different doc → sidebar chat shows that doc's history, not the prior one's.

### 6.5 Lint / types / coverage
- [ ] `make lint` clean.
- [ ] `cd frontend && npm run lint` clean.
- [ ] `make test` and `cd frontend && npm test` all pass.
- [ ] No new ruff D-rule (docstring) violations on new files.

---

## 7. Risks & Tradeoffs

- **Binary re-render is a perf cliff for large XLSX / PPTX.** Re-rendering a 50-slide deck or 100-sheet workbook on every edit is slow. Mitigation: pre-render only the changed slide PNG (slide-level dirty tracking); for XLSX, keep the rendered file but patch only changed cells via `openpyxl` in-place when possible. **Where it still hurts:** structural changes (insert/delete row mid-sheet, reorder slides) need full re-render.
- **PPTX→PNG via LibreOffice headless adds a heavy dependency.** LibreOffice is ~500MB. Mitigation: separate Cloud Run service for slide rendering (already a pattern in this repo for video render); main API stays slim. Alternative: ship as part of the existing render path if size is acceptable; verify Cloud Run cold start impact before deciding.
- **Lazy extraction adds first-edit latency.** A user uploads a 200-page PDF and the agent's first edit takes 30 seconds while extraction runs. Mitigation: kick off extraction *opportunistically* on workspace open if a doc viewer widget is shown — agent's first edit then hits the cache. Worst case: show a "preparing for editing..." state once, never again.
- **`fork_from_upload=true` mutates the user's mental model of their file.** They uploaded a PDF; now there's a "v0 original + v1 agent-edited" version chain. Mitigation: original is never modified or deleted (v0 always available via Undo); UX surfaces it as "edited copy of report.pdf" when forked, with a clear "show original" affordance.
- **Google Docs API doesn't expose a native version history aligned with ours.** Reverting an `edit_google_doc` requires us to re-apply the inverse edit, not a true revert. Mitigation: store before-state snippets in `document_versions.source_snapshot` for Google docs too; revert = re-write the captured before-state via the API. Imperfect but functional.
- **`change_spec` schema drift between Python and TypeScript.** Five tools means five Pydantic models on backend mirroring five sets of frontend types. Mitigation: backend Pydantic models are the source of truth; the existing OpenAPI generator already produces TS types (`frontend/src/types/api.generated.ts` already in repo). Wire into the build.
- **Coupling to Track A.** Track B can't ship until Track A's 2a (forward channel) is in production. Mitigation: build Track B against the Track A plan *as-if-shipped* — test harnesses can stub `dispatchWorkspaceCommand`. Real integration test gates merging Track B until 2a is live.
- **Token cost on `read_document_content`.** A 200-page PDF returning 10K tokens of extracted text on every read kills the context budget. Mitigation: cap at 10K tokens AS DESIGNED (`truncated: true` flag), agent summarises into its own context if needed; agent default behavior is to use `page_range` after the first overview read.
- **Concurrent edits from multiple agents.** Two agents in the same conversation emit `edit_*` calls within 100ms of each other. Mitigation: optimistic locking on `document_sources.updated_at`; second tool call gets `status=error, reason="version_conflict"` and re-reads. Document the retry pattern in the agent instruction block.
- **Mobile.** All renderers tested desktop-first. PDF.js works mobile but interaction (page swipe vs scroll) needs tuning; sidebar collapses to bottom-sheet on small screens. **Out of scope for v1; tracked as follow-up.**

---

## 8. Out of Scope (this plan)

- Mobile-specific renderer tuning. Desktop-first; mobile follows.
- Real-time collaborative editing (CRDT, OT). Single-user-per-doc only.
- Inline (in-viewer) annotations or highlights drawn by the user. The viewer is read-display + chat-edit; freehand annotations not in v1.
- Google Slides API integration. PPTX users handle Slides via Drive themselves if needed.
- OCR for scanned PDFs. Extraction handles text-layer PDFs only; scanned PDFs return `extracted_text=""`. OCR pipeline is a follow-up.
- Document-level permissions / sharing distinct from session ownership. RLS = owner only.
- Versioned diffs richer than `diff_summary` text. No side-by-side visual diff in v1.
- Search-within-document. `Cmd+F` works in the browser for text-rendered formats; not augmented.
- Export-to-other-format (PDF→DOCX, PPTX→PDF besides slide rendering). Each doc stays in its own class.
- Custom branding/themes for re-rendered output. The render path uses existing `document_service.py` defaults.

---

## 9. Open Questions

1. **PPTX slide rendering — LibreOffice headless co-located with API container or separate service?** Either works. Co-located is simpler for v1 (one Cloud Run service to deploy); separate is cleaner long-term. Recommendation: co-locate for v1, factor out if cold-start regression is observed.
2. **Should the editor sidebar persist scroll position per doc per session?** Likely yes for UX, but adds frontend state surface. Recommendation: yes; store in `localStorage` keyed by `{sessionId}:{documentId}`.
3. **What's the cap on `document_versions` rows per document before we prune?** Storage isn't free. Recommendation: keep last 50 versions hot; older snapshots compressed and moved to cold storage. Defer pruning to a follow-up plan.

---

## 10. Dependencies on Track A

Track B must NOT begin merging until Track A Phase 2a ships. Specific shared surfaces:

| Track B uses | Track A provides |
|---|---|
| `workspace_command` SSE event type | Phase 2a: SSE post-processor + parser + dispatcher |
| `WorkspaceCommand` TS union | Phase 2a: `frontend/src/services/workspaceCommands.ts` |
| `dispatchWorkspaceCommand` | Phase 2a: same file |
| `WORKSPACE_COMMAND_EVENT` listener in `ActiveWorkspace` | Phase 2a: command handler |
| `POST /a2a/sessions/{id}/workspace_events` endpoint | Phase 2b: router |
| `workspace_events` table | Phase 2b: migration |
| `active_workspace_items` session memory | Phase 2d: pre-turn callback |
| `workspace_update` ADK tool (for emitting Track B's commands) | Phase 2c: tool |

Track B *extends* (not replaces) the `WorkspaceCommand` union, the `event_type` CHECK constraint, and the `_workspace_command` extractor allowlist. Each extension is an additive change — no breakage to Track A's tests.

---

## 11. Sequencing

Within Track B, after Track A's Phase 2a is in production:

| Sub-phase | Scope | Risk | Can ship alone |
|---|---|---|---|
| B1 | Backend: tables, services, lazy extraction, render-from-source pipeline | Med | ✓ (no UI change) |
| B2 | `read_document_content` + 5 edit tools wired to ContentCreationAgent | Med | ✓ after B1 |
| B3 | Frontend: `DocumentViewerWidget` shell + per-format renderers | Low | ✓ after B1 (uses existing chip data shape) |
| B4 | Editor sidebar + scoped chat + version strip | Med | After B3 |
| B5 | Workspace command extensions (`view_document_page`, `toggle_editor_sidebar`) + back-channel events | Low | After B3 + Track A's 2a |
| B6 | Rollout to MarketingAgent, ExecutiveAgent | Low | After B2, B5 |

Total estimate: ~3-4 weeks engineering for the full Track B once Track A's 2a is live.

---

## 12. Success Criteria

- Every doc the agent creates renders inline in the workspace canvas — no new-tab redirect for first-look.
- The agent can answer "what does page 3 say" without the user re-uploading or copy-pasting.
- The user can say "rewrite this slide to be more concise" and see the slide change in <10 seconds (for typical 10-50 page/slide docs) without leaving the workspace.
- Undo reverts the change in <2 seconds.
- User uploads (PDFs, XLSX, etc.) become editable on the first agent edit attempt without manual conversion.
- The viewer + sidebar match the visual language of the existing workspace canvas (no jarring style break).
