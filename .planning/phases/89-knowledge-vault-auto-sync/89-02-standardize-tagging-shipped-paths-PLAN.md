---
phase: 89-knowledge-vault-auto-sync
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/director_service.py
  - app/agents/tools/media.py
  - tests/unit/test_director_service.py
  - tests/unit/test_media_routing.py
autonomous: true
requirements: [HOTFIX-07]

must_haves:
  truths:
    - "director_service video ingest writes top-level document_type='video' (not document_type='media')"
    - "media.py image ingest writes top-level document_type='image' (not document_type='media')"
    - "media.py video fallback ingest (line ~840) writes top-level document_type='video' (not document_type='media')"
    - "All three shipped paths preserve nested metadata.asset_type ('video' or 'image') for backward compatibility with legacy readers"
    - "All three shipped paths emit standardized metadata fields (asset_id, bucket_id, file_path where available, prompt where applicable, session_id, workflow_execution_id)"
  artifacts:
    - path: "app/services/director_service.py"
      provides: "Director video ingest tagged document_type='video' with standardized metadata schema"
      contains: 'document_type="video"'
    - path: "app/agents/tools/media.py"
      provides: "Image ingest tagged document_type='image' and video-fallback ingest tagged document_type='video', both with standardized metadata schema"
      contains: 'document_type="image"'
  key_links:
    - from: "app/services/director_service.py"
      to: "app/rag/knowledge_vault.py:ingest_document_content"
      via: "best-effort try/except, document_type='video', metadata.asset_type='video' for legacy"
      pattern: 'document_type="video"'
    - from: "app/agents/tools/media.py:generate_image"
      to: "app/rag/knowledge_vault.py:ingest_document_content"
      via: "_schedule_best_effort_task, document_type='image', metadata.asset_type='image' for legacy"
      pattern: 'document_type="image"'
    - from: "app/agents/tools/media.py:generate_video (fallback path ~line 840)"
      to: "app/rag/knowledge_vault.py:ingest_document_content"
      via: "_schedule_best_effort_task, document_type='video', metadata.asset_type='video' for legacy"
      pattern: 'document_type="video"'
---

<objective>
Standardize the tagging schema across the two already-shipped auto-ingest paths so all generated artifacts use a consistent top-level `document_type` field. Currently both video and image paths use `document_type="media"` with the asset type buried in `metadata.asset_type` — this makes filtering by content type require nested-key queries. CONTEXT decision is to promote `asset_type` to a first-class `document_type` value (one of `"video" | "image" | "pdf" | "pitch_deck" | "document"`) while keeping the nested field populated for legacy readers.

Purpose: Satisfy ROADMAP success criteria 1 ("director video registered in Knowledge Vault with metadata") and 2 ("image service generates an Imagen/Veo asset, lands in vault automatically") by upgrading their tagging to the shape that 89-03 will exercise via search_business_knowledge filtering. Without this, the new `document_type="pdf"` rows from 89-01 would coexist with `document_type="media"` rows from videos/images and the search filter contract would be split across two schemas.

Output: Three call sites updated (one in director_service.py, two in media.py — image gen and video fallback). Each writes `document_type="video"` or `document_type="image"` at the top level AND keeps `metadata.asset_type` populated. Standardized metadata field names across all three. No behavior change to the user-facing widget, the storage upload, or the media_assets upsert. 4 unit tests assert the new tagging contract.
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
@app/services/director_service.py
@app/agents/tools/media.py
@app/rag/knowledge_vault.py
@tests/unit/test_director_service.py
@tests/unit/test_media_routing.py

<interfaces>
<!-- Three current call sites — these are the EXACT shapes to upgrade. -->

**Site 1 — app/services/director_service.py:551-568 (video pro pipeline):**
```python
try:
    from app.rag.knowledge_vault import ingest_document_content

    await ingest_document_content(
        content=f"Generated pro video: {prompt}. Asset ID: {asset_id}.",
        title=f"Video: {(prompt[:80] + '…') if len(prompt) > 80 else prompt}",
        document_type="media",                              # ← change to "video"
        user_id=user_id,
        metadata={
            "asset_id": asset_id,
            "asset_type": "video",                           # ← keep for legacy
            **media_metadata,
        },
    )
except Exception as exc:
    logger.warning("Knowledge vault ingest for director video failed: %s", exc)
```
`media_metadata` (defined earlier in this method) already contains: `prompt`, `render_backend`, `nano_banana_mode`, `session_id`, `workflow_execution_id`, `bucket_id`, `file_path`. After upgrade: top-level `document_type="video"`, nested `metadata.asset_type="video"` retained.

**Site 2 — app/agents/tools/media.py:390-405 (image generation):**
```python
try:
    from app.rag.knowledge_vault import ingest_document_content

    ingest_content = (
        f"Generated image: {title}. Prompt: {prompt}. "
        f"Asset ID: {asset_id}. Stored in Knowledge Vault media."
    )
    _schedule_best_effort_task(
        ingest_document_content(
            content=ingest_content,
            title=f"Image: {title}",
            document_type="media",                           # ← change to "image"
            user_id=user_id,
            metadata={"asset_id": asset_id, "asset_type": "image"},  # ← expand
        ),
        f"image-ingest:{asset_id}",
    )
except Exception as e:
    logger.warning(f"Knowledge vault ingest for image failed: {e}")
```
Note: `request_scope` is in scope (line 381 reads `request_scope.get("session_id")` and `request_scope.get("workflow_execution_id")`) — use these to populate standardized metadata. `enhanced_prompt`, `style`, `result.get("model_used")` are also in scope.

**Site 3 — app/agents/tools/media.py:836-851 (video Veo fallback):**
```python
try:
    from app.rag.knowledge_vault import ingest_document_content

    ingest_content = (
        f"Generated video: {title}. Prompt: {prompt}. "
        f"Asset ID: {asset_id}. Stored in Knowledge Vault media."
    )
    _schedule_best_effort_task(
        ingest_document_content(
            content=ingest_content,
            title=f"Video: {title}",
            document_type="media",                           # ← change to "video"
            user_id=user_id,
            metadata={"asset_id": asset_id, "asset_type": "video"},  # ← expand
        ),
        f"video-ingest:{asset_id}",
    )
except Exception as e:
    logger.warning(f"Knowledge vault ingest for video failed: {e}")
```
In scope here: `prompt`, `source` (e.g. "veo"), `duration`, `request_scope.get("session_id")`, `request_scope.get("workflow_execution_id")`, `bucket_id`, `file_path`. Use these to populate standardized metadata.

**Standardized metadata schema (apply to all 3 sites — only fill keys whose values are in scope):**
```python
{
    "asset_id": <str>,
    "asset_type": "video" | "image",        # backward-compat per CONTEXT
    "bucket_id": <str>,                       # known at each site
    "file_path": <str>,                       # known at each site
    "prompt": <str>,                          # known at all 3 sites
    "render_backend": <str>,                  # video sites only (director, video fallback)
    "model_used": <str>,                      # image only
    "session_id": <str | None>,
    "workflow_execution_id": <str | None>,
}
```

**ingest_document_content signature (unchanged from app/rag/knowledge_vault.py:132):**
```python
async def ingest_document_content(
    content: str, title: str,
    document_type: str = "document",
    user_id: str | None = None, agent_id: str | None = None,
    metadata: dict | None = None,
) -> dict
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Update director_service.py video ingest tagging + add regression test</name>
  <files>app/services/director_service.py, tests/unit/test_director_service.py</files>
  <behavior>
    **Code change (app/services/director_service.py:551-568):**
    Change `document_type="media"` → `document_type="video"`. Keep `metadata={"asset_id": asset_id, "asset_type": "video", **media_metadata}` exactly as-is (the `**media_metadata` spread already covers `prompt`, `render_backend`, `nano_banana_mode`, `session_id`, `workflow_execution_id`, `bucket_id`, `file_path` per the existing media_metadata construction earlier in this method). Confirm by reading lines ~520-540 in director_service.py to verify what media_metadata contains; if `bucket_id` or `file_path` is missing from media_metadata at the call site, add them explicitly to the ingest metadata kwargs.

    Behavior: zero-impact on the user-facing video URL return, the media_assets upsert, or the storyboard pipeline. Only the document_type tag changes.

    **Test addition (tests/unit/test_director_service.py):**
    Add ONE new test `test_director_video_ingest_uses_document_type_video`:
    - Patch `app.rag.knowledge_vault.ingest_document_content` as `AsyncMock`.
    - Patch the storage upload + media_assets upsert path so `_upload_final_video` (or whichever method contains the line 551 ingest call — confirm via reading context) reaches the ingest line.
    - After running the upload, assert `ingest_document_content.call_args.kwargs["document_type"] == "video"`.
    - Assert `ingest_document_content.call_args.kwargs["metadata"]["asset_type"] == "video"` (legacy compat).
    - Assert `ingest_document_content.call_args.kwargs["metadata"]` contains `asset_id` and `prompt` keys.

    If the existing director_service test setup is heavy (full storyboard mock), prefer adding a narrower test that directly invokes the smallest method containing the ingest call. Read tests/unit/test_director_service.py (full file) before writing the test to align with existing patterns (`_SupabaseStub`, `monkeypatch`).

    Run: `uv run pytest tests/unit/test_director_service.py -x`. Test must be GREEN after the code change.

    Lint: `uv run ruff check app/services/director_service.py --fix && uv run ty check app/services/director_service.py`.

    Commit: `feat(89-02): tag director video ingest as document_type='video' (HOTFIX-07)`.
  </behavior>
  <action>
    1. Read tests/unit/test_director_service.py end-to-end to find the right hook point and fixture style.
    2. Read app/services/director_service.py around lines 510-570 to confirm `media_metadata` contents and the enclosing method name.
    3. Edit director_service.py: change `document_type="media"` → `document_type="video"` on line ~557. If `media_metadata` does not already include `bucket_id` and `file_path`, add them explicitly to the ingest metadata: `metadata={"asset_id": asset_id, "asset_type": "video", "bucket_id": <bucket>, "file_path": <path>, **media_metadata}`. Spread order is intentional — `media_metadata` last so any duplicate keys it carries override the explicit ones (CONTEXT requires backward compat, not strict overwrite).
    4. Append the new test in test_director_service.py. Use existing fixture style — wrap with `@pytest.mark.asyncio` if the target method is async.
    5. Run `uv run pytest tests/unit/test_director_service.py -x`.
    6. Run lint + type check.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_director_service.py -x 2>&amp;1 | tail -15 &amp;&amp; uv run ruff check app/services/director_service.py 2>&amp;1 | tail -3</automated>
  </verify>
  <done>
    director_service.py video ingest writes `document_type="video"` and preserves nested `asset_type="video"`. New test `test_director_video_ingest_uses_document_type_video` is GREEN. Existing director tests unchanged. Ruff + ty clean. Commit lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Update media.py image + video-fallback ingests + add regression tests</name>
  <files>app/agents/tools/media.py, tests/unit/test_media_routing.py</files>
  <behavior>
    **Code change A — app/agents/tools/media.py:390-405 (image gen):**
    - Change `document_type="media"` → `document_type="image"`.
    - Expand `metadata={"asset_id": asset_id, "asset_type": "image"}` to:
      ```python
      metadata={
          "asset_id": asset_id,
          "asset_type": "image",                     # backward-compat
          "bucket_id": bucket_id,
          "file_path": file_path,                    # may be None on storage failure — that's OK
          "prompt": enhanced_prompt,                 # already in scope at this point
          "style": style,
          "model_used": result.get("model_used"),
          "session_id": request_scope.get("session_id"),
          "workflow_execution_id": request_scope.get("workflow_execution_id"),
      }
      ```

    **Code change B — app/agents/tools/media.py:836-851 (video Veo fallback):**
    - Change `document_type="media"` → `document_type="video"`.
    - Expand `metadata={"asset_id": asset_id, "asset_type": "video"}` to:
      ```python
      metadata={
          "asset_id": asset_id,
          "asset_type": "video",                     # backward-compat
          "bucket_id": bucket_id,
          "file_path": file_path,
          "prompt": prompt,
          "source": source,                          # e.g. "veo"
          "duration": duration,
          "session_id": request_scope.get("session_id"),
          "workflow_execution_id": request_scope.get("workflow_execution_id"),
      }
      ```
    Confirm `bucket_id` and `file_path` variable names by reading lines ~795-835 (the surrounding method scope). If they have different local names, use the actual names.

    Behavior: no change to widget shape, no change to media_assets row, no change to `_register_media_contract`. Only the vault ingest tagging is upgraded.

    **Test additions (tests/unit/test_media_routing.py — or new file `tests/unit/test_phase89_media_tagging.py` if test_media_routing has heavy setup that doesn't fit):**
    Add 3 new tests:
    1. `test_image_gen_ingest_uses_document_type_image` — patch `app.rag.knowledge_vault.ingest_document_content` and `_schedule_best_effort_task` to capture the coroutine. Mock storage and `media_assets` insert. Run `generate_image(prompt="...", user_id="user-1")`. Assert the ingest coroutine kwargs include `document_type="image"`, `metadata["asset_type"]=="image"`, `metadata["asset_id"]`, `metadata["prompt"]`.
    2. `test_video_fallback_ingest_uses_document_type_video` — same pattern for `generate_video` fallback path. Assert `document_type="video"`, `metadata["asset_type"]=="video"`, `metadata["prompt"]`, `metadata["source"]`.
    3. `test_image_ingest_failure_does_not_break_widget_return` — patch `ingest_document_content` to raise. Assert `generate_image` still returns a non-None widget with `widget["type"] == "image"`. (Best-effort guarantee.)

    For `_schedule_best_effort_task` mocking strategy: patch `app.agents.tools.media._schedule_best_effort_task` with a stub that immediately awaits the coroutine via `asyncio.run` or stores it for inspection — choose based on existing test patterns. Read tests/unit/test_media_routing.py first to match conventions.

    Run: `uv run pytest tests/unit/test_media_routing.py tests/unit/test_phase89_media_tagging.py -x` (whichever file landed). All new tests GREEN.

    Lint: `uv run ruff check app/agents/tools/media.py --fix && uv run ty check app/agents/tools/media.py`.

    Commit: `feat(89-02): tag image and video-fallback ingests with explicit document_type (HOTFIX-07)`.
  </behavior>
  <action>
    1. Read tests/unit/test_media_routing.py fully to learn existing fixture/mock patterns for media.py functions.
    2. Read app/agents/tools/media.py lines 320-410 (image gen scope) and 750-855 (video fallback scope) to confirm local variable names (`bucket_id`, `file_path`, `enhanced_prompt`, `request_scope`, `result`, `style`, `source`, `duration`).
    3. Edit media.py site 1 (image): replace the `_schedule_best_effort_task(ingest_document_content(...))` block to use `document_type="image"` and the expanded metadata dict described above.
    4. Edit media.py site 2 (video fallback): same upgrade with `document_type="video"` and video-specific metadata.
    5. Decide test file location: if test_media_routing.py has lightweight stubs for `generate_image` / `generate_video`, append there. Otherwise create `tests/unit/test_phase89_media_tagging.py` with focused fixtures.
    6. Write the 3 tests. Patch targets:
       - `app.rag.knowledge_vault.ingest_document_content` (production import is local-scope inside media.py — patch in source module is more reliable than at the call site).
       - `app.agents.tools.media._schedule_best_effort_task` — replace with a stub that captures the coroutine for inspection. Example: `def fake_schedule(coro, label): captured.append((label, coro)); coro.close()` and assert via `coro.cr_frame.f_locals` OR (cleaner) patch `ingest_document_content` to a `MagicMock` returning a sentinel and assert `MagicMock.call_args.kwargs` directly — `_schedule_best_effort_task` will receive the already-built coroutine and its kwargs are inspectable on the MagicMock.
    7. Run pytest, lint, type check.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_media_routing.py tests/unit/test_phase89_media_tagging.py -x 2>&amp;1 | tail -20 &amp;&amp; uv run ruff check app/agents/tools/media.py 2>&amp;1 | tail -3</automated>
  </verify>
  <done>
    Both media.py ingest sites tagged with explicit `document_type` ("image" / "video"). Backward-compat `metadata.asset_type` preserved. Standardized metadata fields populated. 3 new tests GREEN. Existing media tests unchanged. Ruff + ty clean. Commit lands.
  </done>
</task>

</tasks>

<verification>
End-to-end: `uv run pytest tests/unit/test_director_service.py tests/unit/test_media_routing.py -x` (and the new test_phase89_media_tagging.py if created) → all GREEN.

Cross-cutting: grep `document_type="media"` across the repo — should return zero hits in production code paths after this plan (the string may still appear in tests asserting backward compat or in legacy migration notes; flag in SUMMARY).

`grep -rn 'document_type="media"' app/` should return zero matches.
</verification>

<success_criteria>
- `app/services/director_service.py` line ~557: `document_type="video"` (was `"media"`).
- `app/agents/tools/media.py` line ~398: `document_type="image"` (was `"media"`).
- `app/agents/tools/media.py` line ~844: `document_type="video"` (was `"media"`).
- All three call sites preserve `metadata.asset_type` for legacy readers.
- All three call sites populate the standardized metadata schema (asset_id, bucket_id, file_path, prompt, session_id, workflow_execution_id, plus type-specific fields).
- 4 new tests added (1 in test_director_service.py, 3 in test_media_routing.py or test_phase89_media_tagging.py); all GREEN.
- Existing tests in both test files unchanged and still GREEN.
- `ruff check` clean for both modified files. `ty check` clean.
- Zero `document_type="media"` strings remain in `app/` production code.
</success_criteria>

<output>
After completion, create `.planning/phases/89-knowledge-vault-auto-sync/89-02-standardize-tagging-shipped-paths-SUMMARY.md` documenting:
- Exact line numbers of the three call site changes
- Variable name confirmations (bucket_id, file_path, request_scope) for each site
- Test file location decision (test_media_routing.py vs new test_phase89_media_tagging.py) and rationale
- Confirmation that `grep document_type="media" app/` returns zero hits
- Any deviations from this plan
</output>
