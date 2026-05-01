# Phase 89: Knowledge Vault Auto Sync - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Auto-ingest the artifacts the agent creates (videos, images, PDFs, pitch decks) into the Knowledge Vault, tagged by `session_id` and content type, so `search_business_knowledge` can retrieve them alongside user uploads.

**Critical scoping observation from codebase scout:** auto-ingest is already wired for **2 of 3** artifact types:
- Videos: `app/services/director_service.py:552-570` calls `ingest_document_content(document_type="media", metadata={asset_id, asset_type: "video", ...})` after the storage upload completes.
- Images: `app/agents/tools/media.py:386+` calls `ingest_document_content` for Imagen/Veo assets via `_schedule_best_effort_task`.
- **PDFs / PPTX (the gap):** `app/services/document_service.py:388-440` writes generated docs to `media_assets` but never calls `ingest_document_content` — so `generate_pdf_report` and `generate_pitch_deck` outputs are invisible to RAG search today.

This phase therefore reduces to: close the third path, standardize the tagging schema across all three, verify search retrieval, and add regression coverage. Manual "Add to Vault" upload (`app/routers/vault.py /process` endpoint) stays untouched.

</domain>

<decisions>
## Implementation Decisions

### Ingest payload — what content lands in the vault

- **PDFs / pitch decks:** ingest the **actual document text** (real RAG-searchable content), extracted via the existing `app/services/document_text_extraction.py` pipeline. Title and metadata also stored. This is what makes `"find that pitch deck I made about X"` actually work.
- **Videos / images:** keep the existing synthetic descriptor pattern (`"Generated <type>: {prompt}. Asset ID: {asset_id}."`). Real audio transcription / vision-to-text would be valuable but is out of scope for this hotfix phase.
- **Reasoning:** Document body extraction is already implemented and cheap to invoke; transcription/captioning is a separate capability with its own model + cost considerations.

### Tagging & taxonomy — single `document_type` field across all paths

- Promote `asset_type` to a **top-level `document_type`** value with this enum:
  - `"video"` — director_service output
  - `"image"` — Imagen/Veo output via media.py
  - `"pdf"` — `generate_pdf_report` output
  - `"pitch_deck"` — `generate_pitch_deck` output
  - `"document"` — **reserved for user-uploaded files** (current `app/routers/vault.py /process` flow)
- Standardize metadata schema across all three generated paths:
  ```
  metadata = {
    "session_id": <str | None>,           # required when available
    "asset_id": <uuid>,                   # storage asset id
    "bucket_id": <str>,                   # generated-videos / knowledge-vault / etc.
    "file_path": <str>,                   # storage path
    "prompt": <str>,                      # for video/image
    "render_backend": <str>,              # video only
    "model_used": <str>,                  # image only
    "template": <str>,                    # pdf only
    "workflow_execution_id": <str | None>,
  }
  ```
- Migration of existing `"media"` entries: backward-compatible — keep nested `metadata.asset_type` populated for old rows; new rows write both top-level `document_type` and (for legacy readers) the nested field.

### Failure handling — best-effort, non-blocking

- All three paths follow the existing video/image convention: ingest is wrapped in `try/except`, failures log a warning, the agent's primary response (the file download URL) is returned regardless.
- For the new PDF/PPTX path, use the same `_schedule_best_effort_task` fire-and-forget helper that `media.py` already uses, OR an inline `try/except` matching `director_service.py` — planner picks the more idiomatic fit for `DocumentService`.
- **Reasoning:** The user-visible deliverable is the document download; vault ingest is a search optimization. RAG hiccups must not regress doc generation latency or success rate.

### Search retrieval visibility — single mixed result list

- `search_business_knowledge` returns generated artifacts and user uploads in **one ranked list**, sorted by relevance.
- Callers that want filtering get an optional `document_type` parameter (single value or list) — e.g. `search_business_knowledge(query, document_type=["pdf", "pitch_deck"])` to find only generated docs.
- No segmentation in default results, no opt-in flag for generated content. Default behavior matches ROADMAP criterion 4 ("vault search can retrieve agent-generated assets").

### Claude's Discretion

- Exact placement of the new ingest call inside `DocumentService.upload_to_storage` (before or after `media_assets` upsert) — planner picks based on existing flow.
- Test scaffolding choice (real Supabase fixture vs `unittest.mock` of the supabase client) — planner aligns with existing backend test conventions in `tests/unit/services/`.
- Whether to add a single shared `_ingest_to_vault(document_type, content, metadata)` helper that the three paths converge on, or keep the three call sites with their existing inline patterns. Helper extraction is preferred IF it doesn't break the best-effort scheduling differences.
- Search retrieval verification: planner decides whether to add a real integration test or a unit test that asserts the RAG client query parameters.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/rag/knowledge_vault.py:ingest_document_content(content, title, document_type, user_id, metadata)` — the canonical ingest entry point; both video and image paths already call this. Phase 89 standardizes around it.
- `app/services/document_text_extraction.py` — existing extraction pipeline; PDF/PPTX path can reuse to produce the `content` argument from generated bytes.
- `_schedule_best_effort_task` (in `app/agents/tools/media.py`) — fire-and-forget async scheduler; candidate for reuse in DocumentService.

### Established Patterns
- **Best-effort vault ingest after artifact upload** — try/except with warning log, agent response returned regardless. Pattern shipped in `director_service.py:552-570` and `media.py:386+`. Phase 89's PDF/PPTX wiring follows this contract.
- **Metadata as nested dict on a single `document_type="media"` row** — current pattern; Phase 89 promotes `asset_type` to a first-class field so search filters work without nested-key queries.
- **Synthetic descriptor strings for non-text artifacts** — `"Generated pro video: {prompt}..."` indexed for query, real bytes stored separately.

### Integration Points
- `app/services/document_service.py:388-440` — `upload_to_storage` is where the new ingest call lands (the third path, currently the gap).
- `app/agents/tools/document_gen.py:41-114` — caller of DocumentService for `generate_pdf_report` / `generate_pitch_deck`. No changes expected here (just makes the underlying service auto-ingest).
- `app/rag/search_service.py` and `app/orchestration/knowledge_tools.py` — `search_business_knowledge` resolution; verify retrieval works with the new `document_type` values.
- `app/routers/vault.py /process` (lines 378+) — manual upload path; success criterion 5 verification only, no code changes.

</code_context>

<specifics>
## Specific Ideas

- The user-perspective acceptance test: "I asked the agent to generate a pitch deck about Q4 strategy yesterday. Today I ask 'find my Q4 strategy deck' — it surfaces in vault search results." If that round-trip works end-to-end, the phase succeeds.
- Match the existing video/image convention exactly for PDF/PPTX — same `try/except` shape, same metadata field names where they overlap. Consistency over novelty.

</specifics>

<deferred>
## Deferred Ideas

- **Audio transcription for video / vision-to-text for image** — would make video/image vault entries truly searchable on visual/spoken content, not just the generation prompt. Separate phase: needs Whisper/multimodal-model integration, cost/latency analysis, and likely a job-queue pattern so it doesn't block ingest.
- **Search UI changes** — separating "Your uploads" from "Agent-generated" sections in `/dashboard/vault`, opt-in flags, dedicated filter pills. UX scope, separate phase.
- **De-duplication policy on regeneration** — current behavior: regenerating a video for the same prompt creates a new vault entry. Whether to supersede the old entry, soft-link to it, or retain both is a UX decision worth its own phase.
- **Migration backfill for existing `media_assets` rows that never reached the vault** — for users whose generated artifacts pre-date this phase, a one-shot backfill script could populate the vault. Out of scope for this hotfix; raise as a separate ticket if customers ask.

</deferred>

---

*Phase: 89-knowledge-vault-auto-sync*
*Context gathered: 2026-04-30 via locked-defaults express path (4 gray areas, all locked at recommendation)*
