# Phase 107 Context: Facebook Video Resumable Upload

**Authored:** 2026-05-08
**Source:** No `/gsd:discuss-phase` ran. Decisions captured here are derived from the Phase 107 RESEARCH.md (verified against Meta Graph API v23.0+ reference) and a planner audit of `app/social/connector.py:handle_callback` performed during `/gsd:plan-phase`.

## Decisions

These decisions are **LOCKED**. Plans MUST honor them exactly.

### D-1: API version standardized at v23.0
- Hardcoded `v18.0` in `app/social/publisher.py` and `app/social/connector.py` expired **2026-01-26** (we are 3+ months past expiry as of today, 2026-05-08).
- Standardize on **`v23.0`** (active per Meta versioning page; v25.0 is current GA but v23.0 is the conservative pick that buys ~12 months before re-audit).
- Introduce a single module-level constant `FB_GRAPH_API_VERSION = "v23.0"` in `app/social/publisher.py` and reference it via f-string interpolation everywhere a Facebook/Instagram URL is constructed in that file. The `connector.py` PLATFORM_CONFIGS entries for `facebook` and `instagram` are also bumped to v23.0 in this phase.

### D-2: Host = `graph.facebook.com` (not `graph-video.facebook.com`)
- ROADMAP success criterion 1 wording uses `graph-video.facebook.com`. **Both hosts are documented as valid by Meta**; the `graph-video.*` host is a legacy alias kept alive for compat. Meta's current reference docs use `graph.facebook.com`, which is also what the rest of `publisher.py` already targets for `/me/photos`, `/me/feed`, and Instagram endpoints.
- **Decision:** Standardize on `graph.facebook.com`. The plan documents this micro-divergence from SC-1 wording in the Plan 107-01 task action so reviewers see the rationale.

### D-3: Three-phase resumable upload using `multipart/form-data`
- Phase 1 `upload_phase=start` form fields: `access_token`, `file_size`.
- Phase 2 `upload_phase=transfer` form fields per chunk: `access_token`, `upload_session_id`, `start_offset`, `video_file_chunk` (binary slice via `httpx` `files=` arg).
- Phase 3 `upload_phase=finish` form fields: `access_token`, `upload_session_id`, `description`, optional `title`. `published=true` is the documented default — DO NOT set it explicitly (matches the existing immediate-post intent).
- Loop termination: response `start_offset == end_offset`.
- The broken JSON `file_url` body MUST be absent from `app/social/` after the change (verifiable by `grep -r "file_url" app/social/`).

### D-4: Retry-once on transfer-chunk failure (per SC-2)
- Implement `_post_chunk_with_retry(http, url, data, files) -> httpx.Response`.
- Retry triggers: `httpx.RequestError`, `httpx.ReadTimeout`, and 5xx status codes.
- 4xx responses do NOT retry — surface immediately as structured error.
- After a single retry exhausts, raise `FacebookUploadError(phase="transfer", session_id=..., reason=...)`.

### D-5: Page-token capture during OAuth callback (Plan 107-02)
- **Audit result (2026-05-08):** `grep -n "me/accounts" app/social/` returns zero matches. `app/social/connector.py:handle_callback` (lines 257-345) stores whatever token comes back from the OAuth code-exchange (a User token) in `connected_accounts.access_token`, leaves `platform_user_id` NULL, and writes nothing to `metadata`. **Page-token capture is NOT implemented today.**
- **Plan 107-02 IS REQUIRED** to satisfy SC-1 ("video appears in the Page's feed within 60 seconds"). Without a Page token, `phase=start` will return a permission error and the unit tests in 107-01 will pass while the live flow fails.
- After Plan 107-02:
  - `connected_accounts.platform_user_id` = the Page ID (TEXT).
  - `connected_accounts.access_token` = Fernet-encrypted **Page** access token.
  - `connected_accounts.metadata` JSONB carries `{"user_token_enc": "<fernet ciphertext of the User token, kept for future Page re-listing>", "available_pages": [{"id": "...", "name": "..."}, ...], "selected_page_id": "...", "selected_page_name": "..."}`.
  - If the user has zero Pages → callback returns `{"error": "facebook_no_pages_found"}` (no row written).
  - If the user has one Page → auto-select.
  - If multi-Page → auto-select the first Page for now (UI for selection is deferred to Phase 108 hygiene); the full Pages list is stashed in `metadata.available_pages` so a future endpoint can let the user switch.

### D-6: Test framework — `respx` for httpx mocking
- Add `respx>=0.21.0` to `[dev]` dependencies in `pyproject.toml`.
- Create `tests/unit/social/__init__.py` and `tests/unit/social/conftest.py` (Wave 0 of Plan 107-01).
- Create `tests/unit/social/test_publisher_facebook.py` (the SC-1 / SC-2 mock-based tests).
- Create `tests/unit/social/test_connector_facebook_pages.py` (Plan 107-02 OAuth-callback Page-token capture tests).

### D-7: Streaming vs in-memory video bytes
- For SC-1 ("30-second 1080p MP4", typically 5-15 MB), in-memory `bytes` is sufficient.
- The helper signature accepts `video_bytes: bytes`. Streaming is documented as a follow-up note in 107-01-SUMMARY but NOT implemented in this phase.
- Caller (`post_with_media`) fetches `media_urls[0]` via `httpx.AsyncClient.get(...)` and passes `.content` to `_upload_facebook_video`.

### D-8: `post_with_media` plumbing — resolve Page ID + token from `connected_accounts`
- Today, `_get_token_or_error` returns just the access token. After 107-02, the Facebook branch needs **both** the Page access token (from `access_token`) AND the Page ID (from `platform_user_id`).
- Add a new helper `_get_facebook_page_context(user_id) -> tuple[(page_id, page_token) | None, error_dict | None]` in `publisher.py` that fetches the row, decrypts the access token, and returns the pair. The Facebook video branch uses this; the photo and feed branches keep using `_get_token_or_error` for now (they post to `/me/*` which works with whatever token is stored — though the photo path is also Page-targeted in practice; full migration of all FB branches to Page tokens is documented as a Phase 108 hygiene task).

## Deferred Ideas (OUT OF SCOPE)

These ideas were considered and explicitly deferred. **Plans MUST NOT include them.**

- **Streaming uploads via `httpx.AsyncClient.stream()`** — not needed at SC-1's 30-second 1080p target; documented as future work.
- **Resumption of partial uploads across process restarts** — SC-2 says "retry once", not "persist session and resume later".
- **Scheduled/draft posts via `scheduled_publish_time`** — `published=true` is the implicit default; no UI exists to schedule.
- **Page-selection UI for multi-Page users** — Plan 107-02 auto-selects the first Page and stashes the full list in `metadata`; a `GET /api/social/facebook/pages` + `POST /api/social/facebook/select-page` pair is deferred to Phase 108 hygiene.
- **Migrating `/me/photos` and `/me/feed` Facebook branches to Page tokens** — only the video branch is fixed in 107-01. The photo and feed branches keep their current behavior (deferred to Phase 108).
- **Instagram video posting** — separate publisher branch (`publisher.py:202-224`); uses container/publish flow; out of scope for Phase 107.
- **`upload_phase=cancel` cleanup on aborted uploads** — not in SC.
- **Refactoring the entire `post_with_media` to per-platform private methods** — keep the `if/elif` chain; only the Facebook video sub-branch changes.

## Claude's Discretion

These areas allow Claude to make reasonable choices. Document them in the relevant SUMMARY.

- Exact module placement of `FacebookUploadError` (recommend top of `publisher.py` near other module-scope definitions).
- Logger names for warning messages (recommend `app.social.publisher` — the existing module logger).
- Whether the `_post_chunk_with_retry` helper sleeps between attempts (recommend a short `await asyncio.sleep(0.5)` before the retry to give the server a moment).
- Whether the `connected_accounts` row insertion in 107-02 includes `platform_username` (recommend storing the selected Page's name there for UI display).
- Whether to add a structured-log (logger.info) line on each phase boundary in `_upload_facebook_video` (recommend yes — `start`, `transfer chunk N/M`, `finish`).

## Open Questions (for executor — answerable from code)

- Is there an existing module utility for fetching a remote URL into bytes that we should reuse instead of inlining `httpx.AsyncClient.get`? (Search `app/social/` and `app/services/` first; if none, inline.)
- Does `_encrypt_token`/`_decrypt_token` support multi-token encryption per row, or do we need a separate helper for the metadata-stashed user-token ciphertext? (Spot check: the existing helpers operate on plain strings, so reusing them on the user token is straightforward.)
