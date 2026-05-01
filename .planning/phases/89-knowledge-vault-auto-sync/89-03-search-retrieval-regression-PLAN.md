---
phase: 89-knowledge-vault-auto-sync
plan: 03
type: execute
wave: 2
depends_on: [89-01, 89-02]
files_modified:
  - tests/unit/test_phase89_vault_retrieval.py
autonomous: true
requirements: [HOTFIX-07]

must_haves:
  truths:
    - "search_business_knowledge returns results that include rows ingested with document_type='pdf', 'pitch_deck', 'video', 'image', and 'document' in a single mixed ranked list"
    - "Manual upload via /vault/process router still ingests with document_type='uploaded_document' and is retrievable — no regression from 89-01 or 89-02"
    - "An end-to-end pytest scenario asserts that a mocked PDF ingest from DocumentService produces a row that semantic_search retrieves when queried"
  artifacts:
    - path: "tests/unit/test_phase89_vault_retrieval.py"
      provides: "End-to-end regression suite asserting (a) search retrieval works with the new document_type values, (b) manual upload path is unchanged, (c) DocumentService ingest is observable via the search path"
      contains: "test_pdf_ingest_is_retrievable_via_search"
  key_links:
    - from: "tests/unit/test_phase89_vault_retrieval.py"
      to: "app/services/document_service.py"
      via: "DocumentService.generate_pdf with mocked supabase + ingest_document_content"
      pattern: "DocumentService"
    - from: "tests/unit/test_phase89_vault_retrieval.py"
      to: "app/rag/search_service.py"
      via: "semantic_search with mocked match_embeddings RPC"
      pattern: "semantic_search|match_embeddings"
    - from: "tests/unit/test_phase89_vault_retrieval.py"
      to: "app/routers/vault.py"
      via: "/vault/process flow regression — confirms document_type='uploaded_document' branch still works after 89-01/02"
      pattern: "process_document_for_rag"
---

<objective>
Verify the phase end-to-end: assert that the new `document_type` values written by 89-01 and 89-02 round-trip through `search_business_knowledge` AND that the manual upload path (`/vault/process`) continues to work unchanged. This is regression coverage — no production code changes.

Purpose: Satisfy ROADMAP success criteria 4 ("Vault search can retrieve agent-generated assets by content + session") and 5 ("Existing manual 'Add to Vault' upload path remains functional"). Without this verification we have no proof that the data layer change in 89-01/02 actually produces searchable results — the user-perspective acceptance test from CONTEXT specifics ("I asked the agent to generate a pitch deck about Q4 strategy yesterday. Today I ask 'find my Q4 strategy deck' — it surfaces in vault search results.") needs an automated proxy.

Output: One new test module `tests/unit/test_phase89_vault_retrieval.py` with 4 tests covering the three must_haves above. Manual UAT scaffold (89-MANUAL-UAT.md) for real-Gemini round-trip verification.
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
@.planning/phases/89-knowledge-vault-auto-sync/89-01-document-service-vault-wiring-PLAN.md
@.planning/phases/89-knowledge-vault-auto-sync/89-02-standardize-tagging-shipped-paths-PLAN.md
@app/rag/search_service.py
@app/rag/knowledge_vault.py
@app/orchestration/knowledge_tools.py
@app/agent.py
@app/routers/vault.py
@app/services/document_service.py
@app/services/document_text_extraction.py

<interfaces>
<!-- Search retrieval call chain (read-only — DO NOT modify). -->

**Top-level entry point (app/agent.py:131):**
```python
async def search_business_knowledge(query: str) -> dict:
    user_id = get_current_user_id()
    return await search_knowledge(query, top_k=5, user_id=user_id)
    # Returns {"results": [...], "query": query} or
    #         {"results": [], "query": query, "error": str, "note": "..."}
```

**Underlying call (app/rag/knowledge_vault.py:187):**
```python
async def search_knowledge(query: str, top_k: int = 5, user_id: str | None = None) -> dict:
    client = await get_supabase_client()
    results = await semantic_search(client, query, top_k, user_id)
    return {"results": results, "query": query}
```

**Vector search (app/rag/search_service.py:61):**
```python
async def semantic_search(
    supabase_client, query: str, top_k: int = 5,
    user_id: str | None = None, agent_id: str | None = None,
    similarity_threshold: float = 0.5,
) -> list[dict]:
    query_embedding = generate_embedding(query)        # imports embedding_service
    rpc_params = {"query_embedding": ..., "match_count": ..., "match_threshold": ...}
    if user_id: rpc_params["filter_user_id"] = user_id
    response = await supabase_client.rpc("match_embeddings", rpc_params).execute()
    return format_search_results(response.data) if response.data else []

def format_search_results(raw_results: list[dict]) -> list[dict]:
    """Output rows: {content, similarity, metadata, source_type, source_id}"""
```

**Manual upload path (app/routers/vault.py:378):**
```python
@router.post("/process", response_model=ProcessDocumentResponse)
async def process_document_for_rag(request, body: ProcessDocumentRequest, current_user_id):
    # ... downloads from storage, runs extract_text_from_bytes, calls:
    result = await ingest_document_content(
        content=content,
        title=filename,
        document_type="uploaded_document",     # ← THIS branch must keep working
        user_id=user_id,
        metadata={"file_path": body.file_path},
    )
```

**Test fixture pattern (from tests/integration/test_knowledge_vault.py — reuse where applicable):**
- Mock `app.rag.search_service.generate_embedding` to return a fixed-length list (e.g. `[0.1] * 768`) — avoids hitting Gemini.
- Mock the supabase client's `.rpc("match_embeddings", ...).execute()` to return a `MagicMock(data=[...])` shaped like `format_search_results` expects.
- Mock `get_supabase_client` (in app/rag/knowledge_vault.py) for the search_knowledge entry point.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Write end-to-end retrieval regression tests + manual UAT scaffold</name>
  <files>tests/unit/test_phase89_vault_retrieval.py, .planning/phases/89-knowledge-vault-auto-sync/89-MANUAL-UAT.md</files>
  <behavior>
    Create `tests/unit/test_phase89_vault_retrieval.py` with 4 tests. All must be GREEN against the post-89-01/post-89-02 codebase. No production code changes in this plan.

    **Test 1 — test_search_returns_mixed_document_types:**
    - Mock `app.rag.search_service.generate_embedding` → `[0.1] * 768`.
    - Mock `get_supabase_client` (in `app.rag.knowledge_vault`) to return a MagicMock whose `.rpc("match_embeddings", ...).execute()` returns rows representing all 5 document_type values:
      ```python
      mock_response = MagicMock(data=[
          {"content": "Q4 strategy outline...", "similarity": 0.92, "source_type": "pdf",
           "metadata": {"document_type": "pdf", "asset_id": "p1", "template": "competitive_analysis"},
           "source_id": "p1"},
          {"content": "Pitch deck for fundraising...", "similarity": 0.88, "source_type": "pitch_deck",
           "metadata": {"document_type": "pitch_deck", "asset_id": "pd1"}, "source_id": "pd1"},
          {"content": "Generated pro video: Q4...", "similarity": 0.85, "source_type": "video",
           "metadata": {"document_type": "video", "asset_id": "v1", "asset_type": "video"},
           "source_id": "v1"},
          {"content": "Generated image: hero...", "similarity": 0.81, "source_type": "image",
           "metadata": {"document_type": "image", "asset_id": "i1", "asset_type": "image"},
           "source_id": "i1"},
          {"content": "User-uploaded business plan", "similarity": 0.78, "source_type": "uploaded_document",
           "metadata": {"document_type": "uploaded_document", "file_path": "user-1/plan.pdf"},
           "source_id": "u1"},
      ])
      ```
    - Set request user context (`app.services.request_context.set_request_user_id` or equivalent) — confirm via reading request_context.py how to set user_id for the test.
    - Call `from app.agent import search_business_knowledge; result = await search_business_knowledge("Q4 strategy")`.
    - Assert `result["error"]` is absent.
    - Assert `len(result["results"]) == 5`.
    - Assert the returned source_type values are `{"pdf", "pitch_deck", "video", "image", "uploaded_document"}`.
    - Assert the order matches similarity-descending (top result is the pdf with similarity 0.92).
    - This proves the retrieval contract: 5 different document_type values surface in a single mixed ranked list (CONTEXT decision: "single ranked list, sorted by relevance").

    **Test 2 — test_pdf_ingest_is_retrievable_via_search (the user-perspective E2E):**
    The CONTEXT specifics example: "I asked the agent to generate a pitch deck about Q4 strategy yesterday. Today I ask 'find my Q4 strategy deck' — it surfaces in vault search results."
    - Patch `app.services.document_service.ingest_document_content` as `AsyncMock` to capture what DocumentService writes.
    - Patch storage upload + media_assets execute_async (use the existing `_pdf_patches`-like helper from test_document_service or replicate inline).
    - Run `await DocumentService().generate_pdf("financial_report", financial_data, user_id="user-1", session_id="sess-1", title="Q4 Strategy Deck")`.
    - Capture the kwargs DocumentService passed to `ingest_document_content`. Assert `document_type="pdf"`, `metadata["template"]=="financial_report"`.
    - Now wire that same captured row into the search mock's `match_embeddings` response (i.e. the row that the DocumentService ingest WOULD have created becomes the row the search returns).
    - Call `search_business_knowledge("Q4 Strategy")` → assert the result includes a row whose `metadata["document_type"] == "pdf"` AND whose `metadata["template"] == "financial_report"`.
    - This is the round-trip proxy: DocumentService writes → search retrieves. Bridges the integration boundary without hitting real Supabase.

    **Test 3 — test_manual_upload_branch_unchanged_after_phase89:**
    Regression for ROADMAP success criterion 5.
    - Patch `extract_text_from_bytes` to return `"User uploaded content"`.
    - Patch `ingest_document_content` as AsyncMock.
    - Patch the storage download in `app.routers.vault` to return some bytes.
    - Patch `_assert_storage_access` to no-op.
    - Patch `get_service_client` to return a mock with `.table("vault_documents").select("file_type")...execute()` returning `MagicMock(data=[{"file_type": "application/pdf"}])` and `.table("vault_documents").update(...).eq(...).eq(...).execute()` no-op.
    - Build a FastAPI TestClient or directly call `process_document_for_rag(request, body, current_user_id="user-1")` with a mock Request.
    - Assert `ingest_document_content` was called with `document_type="uploaded_document"` (unchanged from pre-89 behavior).
    - This proves 89-01 and 89-02 did not regress the existing manual upload path.

    **Test 4 — test_legacy_metadata_asset_type_still_present:**
    Backward-compat assertion. Reuse the test_search_returns_mixed_document_types fixture data. Assert that the video and image rows in the search response have BOTH:
    - `metadata["document_type"]` set to "video" or "image" (new top-level field)
    - `metadata["asset_type"]` set to "video" or "image" (legacy nested field)
    This protects against a future PR that strips the legacy field.

    Run: `uv run pytest tests/unit/test_phase89_vault_retrieval.py -x`. All 4 GREEN.

    Lint: `uv run ruff check tests/unit/test_phase89_vault_retrieval.py --fix`.

    **Manual UAT scaffold:**
    Create `.planning/phases/89-knowledge-vault-auto-sync/89-MANUAL-UAT.md` with:
    - Section 1: Setup (`make local-backend`, real Gemini key required).
    - Section 2: SC1 verification — generate a video via the chat (e.g. "make me a 30-second video about Q4 strategy"), wait for completion, query the embeddings table directly: `SELECT document_type, metadata FROM agent_knowledge WHERE document_type='video' ORDER BY created_at DESC LIMIT 1` — confirm the row exists with the expected metadata.
    - Section 3: SC2 verification — same for image.
    - Section 4: SC3 verification — generate a PDF via "create a financial report PDF for Q4", confirm `document_type='pdf'` row appears with extracted text in `content`.
    - Section 5: SC4 verification — after the above 3 generations, ask "find my Q4 strategy materials" → expect `search_business_knowledge` to surface all 3 (PDF, video, image).
    - Section 6: SC5 verification — upload a PDF via the /dashboard/vault UI, confirm `document_type='uploaded_document'` row appears.
    - Each section: explicit pass/fail checkbox. UAT runner records actual SQL output / agent response inline.

    Commit: `test(89-03): add vault retrieval regression suite + manual UAT scaffold (HOTFIX-07)`.
  </behavior>
  <action>
    1. Read `app/services/request_context.py` to learn how to set `user_id` for the test scope (likely a contextvar setter).
    2. Read `tests/integration/test_knowledge_vault.py` to crib the search_service mocking pattern.
    3. Create `tests/unit/test_phase89_vault_retrieval.py`:
       - Imports: `pytest`, `from unittest.mock import AsyncMock, MagicMock, patch`.
       - Module-level fixtures for the 5-row mock response and the embedding mock.
       - 4 test functions decorated with `@pytest.mark.asyncio` where needed.
       - Use `monkeypatch` for the request_context user_id setter.
    4. Write all 4 tests as specified.
    5. Create `.planning/phases/89-knowledge-vault-auto-sync/89-MANUAL-UAT.md` with the 6 sections.
    6. Run pytest, run ruff.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_phase89_vault_retrieval.py -x 2>&amp;1 | tail -15 &amp;&amp; uv run ruff check tests/unit/test_phase89_vault_retrieval.py 2>&amp;1 | tail -3</automated>
  </verify>
  <done>
    `tests/unit/test_phase89_vault_retrieval.py` exists with 4 GREEN tests. `89-MANUAL-UAT.md` exists with 6 sections (one per ROADMAP SC). Ruff clean on the new test file. The full phase 89 ROADMAP success criteria 4 + 5 are covered by automated tests; SC1, SC2, SC3 have the regression coverage from 89-01 + 89-02 and additionally a manual UAT path. Commit lands.
  </done>
</task>

</tasks>

<verification>
End-to-end: `uv run pytest tests/unit/test_phase89_vault_retrieval.py tests/unit/services/test_document_service.py tests/unit/test_director_service.py tests/unit/test_media_routing.py -x` → all GREEN. (Combined regression run across 89-01, 89-02, 89-03 outputs.)

Phase-level success: all 5 ROADMAP criteria for Phase 89 mapped:
- SC1 (director video lands in vault) → 89-02 Task 1 test + 89-03 Test 1
- SC2 (image lands in vault) → 89-02 Task 2 test + 89-03 Test 1
- SC3 (PDF/PPTX lands in vault) → 89-01 Task 2 test + 89-03 Test 1, 2
- SC4 (search retrieves agent-generated) → 89-03 Test 1, 2 (automated) + 89-MANUAL-UAT.md Section 5
- SC5 (manual upload still works) → 89-03 Test 3 (regression) + 89-MANUAL-UAT.md Section 6
</verification>

<success_criteria>
- `tests/unit/test_phase89_vault_retrieval.py` exists with 4 tests, all GREEN.
- Test 1 asserts mixed document_type values surface in a single ranked list (CONTEXT decision verified).
- Test 2 is the user-perspective round-trip proxy (DocumentService PDF write → search retrieves).
- Test 3 confirms the manual upload `/vault/process` branch writes `document_type="uploaded_document"` unchanged (no 89-01/02 regression).
- Test 4 asserts backward-compat `metadata.asset_type` is still present alongside the new top-level `document_type`.
- `89-MANUAL-UAT.md` scaffold exists with 6 sections covering all 5 ROADMAP SCs.
- Combined run with the 89-01 and 89-02 test additions: all green; zero existing-test regressions.
</success_criteria>

<output>
After completion, create `.planning/phases/89-knowledge-vault-auto-sync/89-03-search-retrieval-regression-SUMMARY.md` documenting:
- The 4 test names and their precise assertions
- Mock pattern chosen for `match_embeddings` RPC and embedding generation
- Confirmation that all 5 ROADMAP SCs are mapped (with the SC→test mapping table)
- Manual UAT runner instructions (link to 89-MANUAL-UAT.md)
- Any deviations from this plan
</output>
