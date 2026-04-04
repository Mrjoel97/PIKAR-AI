# Phase 40: Data I/O & Document Generation - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable users to move data in and out of Pikar via CSV import/export, and enable agents to produce polished, branded documents (PDF reports, PowerPoint pitch decks) from any analysis output. Documents are stored in Supabase Storage and downloadable from chat.

</domain>

<decisions>
## Implementation Decisions

### CSV Import Experience
- **Import targets:** All user-facing tables — contacts, financial_records, tasks, initiatives, content_bundles, support_tickets, candidates, risks, audits
- **Flow:** Upload CSV → column mapping UI with AI-suggested mappings (Gemini Flash analyzes headers) → preview first 10 rows → validation with row-level error reporting → commit with SSE progress for large files
- **Mapping persistence:** Save successful mappings per table per user so repeat imports auto-map
- **Error handling:** Validation runs BEFORE commit. Errors shown per-row with field name and reason. User can fix and re-upload, or commit only valid rows (skip errors).
- **File size limit:** 50MB max (from pitfall P14). Larger files rejected with helpful message.
- **Backend:** New `app/services/data_import_service.py` using `polars` for fast CSV parsing. Process via `ai_jobs` queue for large files (>1000 rows). SSE progress via existing streaming pattern.
- **Frontend:** New upload component on each data table page + agent can trigger via chat command

### CSV Export
- **Exportable tables:** Same set as import — contacts, financial_records, tasks, initiatives, content_bundles, support_tickets, candidates, risks, audits
- **Trigger points:** Two ways — (1) "Export" button on dashboard data table pages, (2) agent chat command "export contacts to CSV"
- **Format:** Standard CSV with headers. UTF-8 encoding. Timestamps in ISO 8601.
- **Backend:** `app/services/data_export_service.py` — queries table with user's RLS, streams to CSV, returns Supabase Storage signed URL
- **Agent tool:** `export_data_to_csv(table_name, filters?)` registered on DataAnalysisAgent

### Document Generation — PDF Reports
- **Branding:** User's brand profile (logo + colors from `brand_profiles` table). Falls back to Pikar default branding if no profile exists.
- **Library:** `weasyprint` for HTML → PDF (from stack research). HTML templates with Jinja2 for variable injection.
- **Templates:** 4 built-in templates:
  1. **Financial Report** — revenue summary, key metrics table, trend chart (embedded as base64 SVG), AI analysis section
  2. **Project Proposal** — executive summary, objectives, timeline, budget estimate, next steps
  3. **Meeting Summary** — attendees, key points, decisions made, action items with owners
  4. **Competitive Analysis** — competitor comparison table, SWOT grid, strategic recommendations
- **Generation flow:** Agent collects data → fills Jinja2 template → weasyprint renders PDF → uploads to Supabase Storage (`generated-documents` bucket) → returns signed download URL in chat as a widget
- **Processing:** Via `ai_jobs` queue (weasyprint can be memory-intensive per pitfall P14). Max 50 pages per document.

### Document Generation — PowerPoint Decks
- **Library:** `python-pptx` (from stack research)
- **Templates:** Pitch deck template with branded slides (title, content, chart, comparison, closing)
- **Slides auto-generated** from strategic planning output — agent determines slide count and content
- **Charts:** Matplotlib renders charts as images, embedded in slides
- **Storage:** Same pattern as PDF — Supabase Storage + signed URL in chat

### Agent Integration
- **New agent tools:**
  - `import_csv_data(table_name, file_url)` — triggers import pipeline, returns job status
  - `export_data_to_csv(table_name, filters?)` — generates CSV, returns download URL
  - `generate_pdf_report(template, data, title?)` — generates branded PDF, returns download URL
  - `generate_pitch_deck(content, title?)` — generates PPTX, returns download URL
- **Tool registration:** `import_csv_data` and `export_data_to_csv` on DataAnalysisAgent. `generate_pdf_report` and `generate_pitch_deck` on ALL agents (any agent can produce a document).
- **Chat widget:** New `document` widget type in WidgetRegistry — shows file icon, title, size, and download button. Reuse existing media widget pattern.
- **Conversation linking:** Generated documents stored with `session_id` reference so they appear in chat history

### Claude's Discretion
- Exact Jinja2 template HTML/CSS for each of the 4 PDF templates
- Exact PPTX slide layouts and styling
- AI column mapping prompt engineering (how Gemini Flash suggests mappings)
- Chart rendering approach for PDF embeds (matplotlib → SVG vs matplotlib → PNG)
- SSE progress message format for import
- Whether to show import preview in a modal or inline
- Exact export CSV column ordering
- Error message wording for validation failures

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/director_service.py`: Pattern for async media generation (Supabase Storage upload, signed URLs)
- `app/agents/tools/media.py`: `generate_image()` tool pattern — returns storage URL + widget data
- `frontend/src/components/widgets/WidgetRegistry.tsx`: Widget type registration pattern
- `frontend/src/hooks/useBackgroundStream.ts`: SSE streaming pattern for progress updates
- `app/routers/files.py`: Existing file upload endpoint
- `app/services/base_service.py`: BaseService with Supabase client for RLS queries
- Existing `brand_profiles` table with logo_url and brand colors

### Established Patterns
- Media generation via `ai_jobs` queue with SSE progress (director_service pattern)
- File storage in Supabase Storage buckets with signed URLs
- Agent tools return structured data that frontend renders as widgets
- Export/download via signed Supabase Storage URLs (existing for videos, images)

### Integration Points
- `app/agents/data/agent.py`: Add import/export tools to DataAnalysisAgent
- `app/agents/tools/tool_registry.py`: Register document tools for all agents
- `frontend/src/components/widgets/WidgetRegistry.tsx`: Add `document` widget type
- `app/fast_api_app.py`: Mount new data I/O router
- `supabase/migrations/`: Create `generated-documents` storage bucket if not exists

</code_context>

<specifics>
## Specific Ideas

- PDF reports should feel professional — the kind of document you'd email to a client or present to a board
- CSV import should be forgiving — never silently discard data, always show what was skipped and why
- "Export as PDF" should work from any agent analysis — it's a universal capability, not domain-specific

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 40-data-i-o-document-generation*
*Context gathered: 2026-04-04*
