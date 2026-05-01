---
phase: 89-knowledge-vault-auto-sync
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/document_service.py
  - tests/unit/services/test_document_service.py
autonomous: true
requirements: [HOTFIX-07]

must_haves:
  truths:
    - "Generating a PDF via DocumentService.generate_pdf upserts to media_assets AND ingests document text into the Knowledge Vault tagged document_type='pdf'"
    - "Generating a PPTX via DocumentService.generate_pptx upserts to media_assets AND ingests a synthetic descriptor into the Knowledge Vault tagged document_type='pitch_deck'"
    - "Vault ingest failure does NOT raise from _upload_document — the document widget is returned regardless"
    - "Vault ingest failure does NOT prevent the media_assets upsert from succeeding"
  artifacts:
    - path: "app/services/document_service.py"
      provides: "DocumentService._upload_document now ingests generated docs into Knowledge Vault after media_assets upsert"
      contains: "ingest_document_content"
    - path: "tests/unit/services/test_document_service.py"
      provides: "Unit tests asserting the ingest call fires with the correct document_type, content, title, user_id, and metadata for both PDF and PPTX paths; ingest failure is best-effort (caught + warning logged)"
      contains: "test_upload_document_ingests_pdf_to_vault"
  key_links:
    - from: "app/services/document_service.py:_upload_document"
      to: "app/rag/knowledge_vault.py:ingest_document_content"
      via: "best-effort try/except after media_assets upsert"
      pattern: "ingest_document_content"
    - from: "app/services/document_service.py:_upload_document"
      to: "app/services/document_text_extraction.py:extract_text_from_bytes"
      via: "PDF text extraction for searchable content"
      pattern: "extract_text_from_bytes"
---

<objective>
Close the third auto-ingest path: DocumentService.upload_to_storage currently writes generated PDFs and PPTX files to media_assets but never registers them in the Knowledge Vault. This plan adds a best-effort ingest call after the media_assets upsert so generate_pdf_report and generate_pitch_deck outputs become searchable via search_business_knowledge.

Purpose: Satisfy ROADMAP success criterion 3 ("When generate_pdf_report or generate_pitch_deck produces a file, it lands in the vault automatically") and HOTFIX-07. Closes the documented gap between document generation and RAG visibility — currently agent-generated PDFs are invisible to "find that pitch deck I made about X" type queries.

Output: DocumentService._upload_document now performs auto-ingest after media_assets upsert, with PDF body text extracted via the existing pypdf pipeline (RAG-searchable) and PPTX using a synthetic descriptor (transcription/captioning out of scope per CONTEXT). Best-effort failure handling matches director_service convention. Five unit tests assert the ingest contract.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/89-knowledge-vault-auto-sync/89-CONTEXT.md
@app/services/document_service.py
@app/rag/knowledge_vault.py
@app/services/document_text_extraction.py
@tests/unit/services/test_document_service.py

<interfaces>
<!-- Key contracts the executor needs. Extracted from the codebase. -->
<!-- Use these directly — no codebase exploration needed. -->

From app/rag/knowledge_vault.py:
```python
async def ingest_document_content(
    content: str,
    title: str,
    document_type: str = "document",
    user_id: str | None = None,
    agent_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """Ingest a document into the Knowledge Vault.

    Returns {"success": bool, "embedding_ids": list, "chunk_count": int, "title": str}.
    Returns {"success": False, "error": "Content cannot be empty", ...} for empty content.
    """
```

From app/services/document_text_extraction.py:
```python
def extract_text_from_bytes(
    file_bytes: bytes,
    mime_type: str | None,
    *,
    filename: str | None = None,
) -> Optional[str]:
    """Extract searchable text from raw file bytes.

    Returns extracted text (may be ""), or None if mime_type is not searchable.
    Raises ExtractionError when a supported format fails to parse.
    """

class ExtractionError(Exception):
    """Raised when a supported format cannot be parsed."""
```

From app/services/document_service.py (current shape — DO NOT regress):
```python
class DocumentService:
    async def generate_pdf(
        self, template_name: str, data: dict, user_id: str,
        session_id: str | None = None, title: str | None = None,
    ) -> dict[str, Any]: ...

    async def generate_pptx(
        self, slides_data: list[dict], user_id: str,
        session_id: str | None = None, title: str | None = None,
    ) -> dict[str, Any]: ...

    async def _upload_document(
        self,
        file_bytes: bytes,
        user_id: str,
        doc_id: str,
        filename: str,
        content_type: str,        # "application/pdf" or "application/vnd.openxml...presentationml.presentation"
        title: str,
        template_name: str,        # for PDF: e.g. "financial_report"; for PPTX: "pitch_deck"
        session_id: str | None,
        file_type: str,            # "pdf" or "pptx"
    ) -> dict[str, Any]:
        """Returns widget dict {type, title, data: {documentUrl, title, fileType, sizeBytes, templateName}, dismissible, expandable}."""
```

From the shipped pattern at app/services/director_service.py:551-568 (REFERENCE — match this idiom):
```python
try:
    from app.rag.knowledge_vault import ingest_document_content

    await ingest_document_content(
        content=f"Generated pro video: {prompt}. Asset ID: {asset_id}.",
        title=f"Video: {(prompt[:80] + '…') if len(prompt) > 80 else prompt}",
        document_type="media",
        user_id=user_id,
        metadata={"asset_id": asset_id, "asset_type": "video", **media_metadata},
    )
except Exception as exc:
    logger.warning("Knowledge vault ingest for director video failed: %s", exc)
```

Test fixture references (from tests/unit/services/test_document_service.py):
```python
def _mock_supabase():
    """Storage upload + create_signed_url, table.upsert.execute mocked. Returns MagicMock."""

def _mock_weasyprint_html():
    """Returns mock HTML class whose write_pdf() returns FAKE_PDF_BYTES."""

def _pdf_patches():
    """Tuple of (weasyprint, supabase_client, execute_async-AsyncMock) patches."""
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add Wave-0 failing tests for vault ingest contract</name>
  <files>tests/unit/services/test_document_service.py</files>
  <behavior>
    Add a new test class `TestVaultAutoIngest` in tests/unit/services/test_document_service.py with 5 tests. ALL must FAIL initially (RED) — they assert behavior that does not yet exist in document_service.py.

    - **test_upload_document_ingests_pdf_to_vault**: After `generate_pdf("financial_report", financial_data, user_id="user-1", session_id="sess-1", title="Q1 Report")`, `app.services.document_service.ingest_document_content` (an `AsyncMock` patched at the document_service import site) is called exactly once with kwargs:
      - `document_type="pdf"`
      - `title="Q1 Report"` (passes through from caller)
      - `user_id="user-1"`
      - `content` is a non-empty string (the extracted PDF text — mock `extract_text_from_bytes` to return `"Extracted body of the financial report."`)
      - `metadata` dict contains keys: `asset_id` (any UUID-shaped string), `bucket_id="generated-documents"`, `file_path` (starts with `"user-1/"`, ends with `".pdf"`), `template="financial_report"`, `session_id="sess-1"`, `file_type="pdf"`. Backward-compat: also asserts nested `metadata["asset_type"]` is set to `"document"` for legacy readers.

    - **test_upload_document_ingests_pptx_to_vault**: After `generate_pptx(slides_data, user_id="user-1", session_id="sess-2", title="Vision Deck")`, `ingest_document_content` is called once with `document_type="pitch_deck"`, `title="Vision Deck"`, `user_id="user-1"`. `content` is a non-empty synthetic descriptor string (mock `extract_text_from_bytes` to return None — PPTX is not in the searchable-MIME set; the wiring must fall back to a synthetic string like `f"Generated pitch deck: {title}. Slides: {len(slides_data)}. Asset ID: {asset_id}."`). Metadata contains `template="pitch_deck"`, `file_type="pptx"`, `bucket_id="generated-documents"`, plus the standardized fields.

    - **test_vault_ingest_failure_is_best_effort**: Patch `ingest_document_content` to raise `RuntimeError("Embedding service down")`. `generate_pdf(...)` MUST still return a valid widget (`result["type"] == "document"`, `result["data"]["documentUrl"]` non-empty). Assert that `caplog` captured a `WARNING`-level log containing the substring `"Knowledge vault ingest"` and the raised error message. Assert media_assets upsert (`execute_async` mock) was still called.

    - **test_text_extraction_failure_falls_back_to_descriptor**: For a PDF where `extract_text_from_bytes` raises `ExtractionError("PDF extraction failed: corrupt")`, the ingest still happens with a synthetic descriptor (e.g. `f"Generated PDF report ({template_name}): {title}. Asset ID: {asset_id}."`) and a `WARNING` log mentions `"document text extraction failed"`. Document widget is returned successfully. `document_type="pdf"` is preserved.

    - **test_empty_extracted_text_falls_back_to_descriptor**: When `extract_text_from_bytes` returns `""` (empty string — valid but unsearchable PDF), ingest is still attempted with a synthetic descriptor (NOT the empty string — `ingest_document_content` would early-return `success=False` for empty content). `document_type="pdf"` preserved.

    Run `uv run pytest tests/unit/services/test_document_service.py::TestVaultAutoIngest -x` and confirm ALL 5 tests fail with `AssertionError` or `AttributeError` referencing the missing `ingest_document_content` patch target. This is the RED state.

    Commit message: `test(89-01): add failing tests for DocumentService vault auto-ingest (HOTFIX-07)`.
  </behavior>
  <action>
    Open tests/unit/services/test_document_service.py. Append the new `TestVaultAutoIngest` class AFTER `TestUploadAndTrack` (end of file).

    Mock pattern (match existing `_pdf_patches` style):
    - `patch("app.services.document_service.ingest_document_content", new_callable=AsyncMock)` — this patch target REQUIRES that Task 2 add `from app.rag.knowledge_vault import ingest_document_content` at module scope OR uses an inline import. Either is fine; align the patch target accordingly. If Task 2 uses an inline `from app.rag.knowledge_vault import ingest_document_content` (matching director_service's local import), patch the function directly in its source module: `patch("app.rag.knowledge_vault.ingest_document_content", new_callable=AsyncMock)`. **The executor MUST pick one strategy and use it consistently across both Task 1 and Task 2.** Recommendation: module-scope import in Task 2 + patch at `app.services.document_service.ingest_document_content` for cleanest tests.
    - `patch("app.services.document_service.extract_text_from_bytes", return_value="...")` — same module-scope import strategy.

    Use `caplog` fixture (built-in pytest) with `caplog.set_level(logging.WARNING, logger="app.services.document_service")` to capture warnings.

    Reuse existing fixtures: `brand_profile`, `financial_data`, `slides_data`, `_mock_supabase`, `_mock_weasyprint_html`, `_pdf_patches`.

    Verify: every test fails because the production code does not yet import or call `ingest_document_content` / `extract_text_from_bytes`. Do NOT modify document_service.py in this task.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/services/test_document_service.py::TestVaultAutoIngest -x 2>&amp;1 | tail -30</automated>
  </verify>
  <done>
    5 new tests exist in tests/unit/services/test_document_service.py under `TestVaultAutoIngest`. All 5 FAIL with assertion or attribute errors referencing the missing ingest call. Existing tests in `TestGeneratePdf`, `TestGeneratePptx`, `TestRenderChart`, `TestUploadAndTrack` still pass (regression check). Commit `test(89-01): add failing tests for DocumentService vault auto-ingest (HOTFIX-07)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire vault ingest into DocumentService._upload_document</name>
  <files>app/services/document_service.py</files>
  <behavior>
    After this task, the 5 tests from Task 1 are GREEN. All existing DocumentService tests still pass.

    The `_upload_document` method (currently lines 376-455) gains a new step AFTER the media_assets upsert and BEFORE the widget return:

    1. Determine `document_type`: if `template_name == "pitch_deck"` → `"pitch_deck"`; else → `"pdf"` (the only other path through this method is `generate_pdf` with one of the 5 VALID_TEMPLATES — all map to "pdf").
    2. Determine ingest content:
       - For PDFs (`content_type == "application/pdf"`): try `extract_text_from_bytes(file_bytes, content_type, filename=filename)`. On `ExtractionError`, on `None` return, or on empty string return → fall back to synthetic descriptor `f"Generated PDF report ({template_name}): {title}. Asset ID: {doc_id}."` and log a warning `"document text extraction failed for {doc_id}: {exc}"` (extraction error case only).
       - For PPTX (`content_type` starts with `"application/vnd.openxmlformats-officedocument.presentationml"`): use synthetic descriptor `f"Generated pitch deck: {title}. Asset ID: {doc_id}."` (transcription out of scope per CONTEXT decision).
    3. Build standardized metadata dict matching CONTEXT schema:
       ```python
       ingest_metadata = {
           "asset_id": doc_id,
           "asset_type": "document",        # backward-compat for legacy readers (per CONTEXT)
           "bucket_id": DOCUMENT_BUCKET,    # "generated-documents"
           "file_path": path,
           "template": template_name,
           "file_type": file_type,
           "session_id": session_id,
       }
       ```
    4. Call `ingest_document_content(content=ingest_content, title=title, document_type=document_type, user_id=user_id, metadata=ingest_metadata)` inside a `try/except Exception as exc: logger.warning("Knowledge vault ingest for %s failed: %s", file_type, exc)`. The `try/except` MUST encompass both the extraction call AND the ingest call so any unexpected error is non-blocking.
    5. The widget return value is unchanged.

    Failure handling: best-effort. Any exception (extraction failure, embedding service down, network error) logs at WARNING and the document widget is returned regardless. The media_assets upsert MUST happen BEFORE the ingest attempt so an ingest failure cannot prevent storage tracking.

    Imports: add at module scope (top of file with the other imports):
    ```python
    from app.rag.knowledge_vault import ingest_document_content
    from app.services.document_text_extraction import ExtractionError, extract_text_from_bytes
    ```
    Module-scope imports (not lazy) are preferred here because: (a) document_text_extraction is already imported at module scope in app/routers/vault.py — same project pattern; (b) module-scope imports give a single, stable patch target for tests.

    Run `uv run pytest tests/unit/services/test_document_service.py -x` and confirm all 5 new TestVaultAutoIngest tests are GREEN AND the existing 18+ tests still pass.

    Lint: `uv run ruff check app/services/document_service.py --fix` and `uv run ruff format app/services/document_service.py`.

    Commit message: `feat(89-01): auto-ingest generated PDFs and pitch decks into Knowledge Vault (HOTFIX-07)`.
  </behavior>
  <action>
    Edit `app/services/document_service.py`:

    1. Add the two imports under existing imports (alphabetical placement: after `from app.services.supabase_async import execute_async`).

    2. Inside `_upload_document` method (around line 440, AFTER the `try/except` block that wraps the media_assets upsert at lines 414-440, BEFORE the `# Return widget dict` block at line 442):

    ```python
    # ------------------------------------------------------------------
    # Knowledge Vault auto-ingest (best-effort, non-blocking)
    # ------------------------------------------------------------------
    try:
        # Determine document_type for top-level vault tagging
        if template_name == "pitch_deck":
            document_type = "pitch_deck"
        else:
            document_type = "pdf"

        # Resolve searchable content
        ingest_content: str | None = None
        if content_type == "application/pdf":
            try:
                extracted = extract_text_from_bytes(
                    file_bytes, content_type, filename=filename,
                )
                if extracted:  # non-empty string
                    ingest_content = extracted
            except ExtractionError as exc:
                logger.warning(
                    "document text extraction failed for %s: %s", doc_id, exc,
                )

        # Fall back to synthetic descriptor when extraction unavailable / empty
        if not ingest_content:
            if document_type == "pitch_deck":
                ingest_content = (
                    f"Generated pitch deck: {title}. Asset ID: {doc_id}."
                )
            else:
                ingest_content = (
                    f"Generated PDF report ({template_name}): {title}. "
                    f"Asset ID: {doc_id}."
                )

        ingest_metadata = {
            "asset_id": doc_id,
            "asset_type": "document",  # backward-compat per CONTEXT
            "bucket_id": DOCUMENT_BUCKET,
            "file_path": path,
            "template": template_name,
            "file_type": file_type,
            "session_id": session_id,
        }

        await ingest_document_content(
            content=ingest_content,
            title=title,
            document_type=document_type,
            user_id=user_id,
            metadata=ingest_metadata,
        )
    except Exception as exc:
        logger.warning(
            "Knowledge vault ingest for %s failed: %s", file_type, exc,
        )
    ```

    3. Comply with project rules: no print, no bare except (use `except Exception`), no mutable default args. Docstring of `_upload_document` should mention the ingest step (one extra line in its docstring).

    4. Run `uv run pytest tests/unit/services/test_document_service.py -x` — confirm all tests GREEN.

    5. Run `uv run ruff check app/services/document_service.py --fix && uv run ruff format app/services/document_service.py && uv run ty check app/services/document_service.py`.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/services/test_document_service.py -x 2>&amp;1 | tail -20 &amp;&amp; uv run ruff check app/services/document_service.py 2>&amp;1 | tail -5</automated>
  </verify>
  <done>
    All 5 TestVaultAutoIngest tests pass. All existing DocumentService tests pass (regression). `ruff check` clean on document_service.py. `ty check` clean. The diff to document_service.py is additive (no behavior regression to existing widget shape, media_assets upsert, or weasyprint render). Commit `feat(89-01): auto-ingest generated PDFs and pitch decks into Knowledge Vault (HOTFIX-07)` lands.
  </done>
</task>

</tasks>

<verification>
End-to-end: `uv run pytest tests/unit/services/test_document_service.py -x` → all tests GREEN (existing + 5 new).

Manual smoke (deferred to phase-level UAT after 89-03): in a `make local-backend` session, ask the agent "create a financial report PDF about Q1" → confirm the PDF download widget returns AND a row appears in the `agent_knowledge` (or equivalent embeddings) table for the same `doc_id` with `document_type="pdf"`.
</verification>

<success_criteria>
- `app/services/document_service.py` imports `ingest_document_content` and `extract_text_from_bytes` at module scope.
- `DocumentService._upload_document` calls `ingest_document_content` after the media_assets upsert with `document_type` ∈ `{"pdf", "pitch_deck"}` and the standardized metadata schema (asset_id, bucket_id, file_path, template, file_type, session_id, asset_type for legacy).
- PDF body text is extracted via `extract_text_from_bytes` when `content_type == "application/pdf"`; falls back to synthetic descriptor on extraction failure or empty result.
- PPTX path uses synthetic descriptor (no extraction).
- All ingest failures are caught at the outer `try/except Exception` and logged at WARNING — the widget return is unaffected.
- `media_assets` upsert remains the first storage write; ingest is a separate step that cannot block it.
- 5 new pytest tests in `TestVaultAutoIngest` are GREEN; all 18+ existing DocumentService tests still GREEN.
- `ruff check` and `ty check` clean for document_service.py.
</success_criteria>

<output>
After completion, create `.planning/phases/89-knowledge-vault-auto-sync/89-01-document-service-vault-wiring-SUMMARY.md` documenting:
- Exact line numbers of the new ingest block
- Module-scope vs inline import decision and rationale
- Test count delta (existing N → existing N + 5 GREEN)
- Any deviations from this plan
</output>
