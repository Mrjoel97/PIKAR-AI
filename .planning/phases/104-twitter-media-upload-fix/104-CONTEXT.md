# Phase 104 Context: Twitter Media Upload Fix

**Phase:** 104-twitter-media-upload-fix
**Milestone:** v13.0
**Created:** 2026-05-08
**Source:** Synthesised from `.planning/phases/104-twitter-media-upload-fix/104-RESEARCH.md` (HIGH confidence) + ROADMAP.md Phase 104 entry + REQUIREMENTS.md POST-04/05/06 + audit of `app/social/publisher.py:43-63` and `app/social/connector.py:32-47`.

## What is broken

`app/social/publisher.py:43-63` (`_upload_media_twitter`) is a stub that:

1. Calls `https://upload.twitter.com/1.1/media/upload.json` — **DEAD** since 2025-06-09 (X v1.1 sunset).
2. Sends a `source_url` form field — **fictional**; X has never accepted "fetch-from-URL" media; the API only takes inline binary or base64.
3. Returns immediately after the (broken) `INIT` step — never APPENDs / FINALIZEs / polls STATUS, so even if the host worked the returned `media_id` would be invalid for tweet attachment.
4. Relies on the OAuth2 access token at `connector.py:44`, whose scope list `["tweet.read", "tweet.write", "users.read", "offline.access"]` is **missing `media.write`** — required by the v2 media upload endpoints.

Net effect: every Twitter post with a media attachment silently posts as text-only or fails outright. The publisher branch at `publisher.py:117-134` does pass `media_ids` correctly to `/2/tweets`, so once `media_id` resolution is fixed the tweet attach path needs no change.

## Locked Decisions (NON-NEGOTIABLE)

These decisions are settled by RESEARCH.md and the ROADMAP success criteria. Plans MUST honor them and MUST NOT revisit.

### Auth strategy: Option A — OAuth 2.0 PKCE + add `media.write` scope
- **No** OAuth 1.0a code path. No new env vars. No HMAC-SHA1 signing.
- Add `"media.write"` to `connector.py:44` scopes list.
- All existing Twitter `connected_accounts` rows are invalidated by the scope change — they MUST be marked `status = 'reconnect_required'` via a SQL migration so the frontend can prompt re-auth. Connector code MUST treat `reconnect_required` the same as `revoked` (i.e. `get_access_token` returns `None`).
- Surface a clear error to the agent when a Twitter post fails 403 on media upload, instructing the user to reconnect with the new scope.

### Endpoint shapes (from docs.x.com, HIGH confidence)
| Operation | URL | Method | Body |
|-----------|-----|--------|------|
| Image simple upload | `https://api.x.com/2/media/upload` | POST | multipart with `media` (binary), `media_category=tweet_image` |
| Chunked INIT | `https://api.x.com/2/media/upload/initialize` | POST | JSON `{"media_type", "total_bytes", "media_category": "tweet_video"}` |
| Chunked APPEND | `https://api.x.com/2/media/upload` | POST | multipart with `command=APPEND`, `media_id`, `segment_index`, `media` chunk |
| Chunked FINALIZE | `https://api.x.com/2/media/upload/{id}/finalize` | POST | empty body |
| STATUS poll | `https://api.x.com/2/media/upload?command=STATUS&media_id={id}` | GET | query params only |
| Tweet attach | `https://api.twitter.com/2/tweets` | POST | JSON `{"text", "media": {"media_ids": [...]}}` (unchanged) |

- Media host is **`api.x.com`** (NOT `api.twitter.com`).
- Tweet host stays `api.twitter.com` (yes, this is asymmetric).

### Media-type dispatch
- `media_type == "video"` → ALWAYS chunked flow, regardless of file size (per docs.x.com Best Practices).
- `media_type ∈ {"image", "carousel", "gif"}` → simple upload to `/2/media/upload` if ≤ 5MB. Carousel only attaches the first URL (X allows up to 4 media per tweet but Phase 104 ships single-media; multi-media is out of scope).

### Constants
- Image cap (simple): 5 MB
- APPEND chunk size: 4 MB
- STATUS poll: honor `check_after_secs` from each response; fallback 2s; total wait cap 600s (10 min).
- `media_category` MUST be `tweet_image` for images, `tweet_video` for videos, `tweet_gif` for GIFs.

### Symbol changes
- **DELETE** `_upload_media_twitter` (publisher.py:43-63).
- **ADD** `_upload_image_twitter` (simple shot) — Plan 104-01.
- **ADD** `_upload_video_twitter` (chunked INIT/APPEND/FINALIZE/STATUS) — Plan 104-02.
- The `source_url` literal must be **absent** from `app/social/publisher.py` after Plan 104-01 (verifiable by `grep -F 'source_url' app/social/publisher.py` returning empty for the Twitter branch — note YouTube branch line 329 stays untouched until Phase 105).

## Deferred Ideas (NOT in this phase)

- **Carousel / multi-media tweets.** Single media only. Multi-media is a future enhancement.
- **OAuth 1.0a fallback.** Documented in RESEARCH §"Option B" but explicitly NOT pursued. If post-rollout monitoring shows ≥10% of users hitting OAuth2-specific 403s, a follow-up phase can revisit.
- **Memory-pressure tempfile fallback for >100MB videos.** Open question (see below). Default behavior for v13.0: read into memory, log warning if >100MB, proceed. A tempfile path can land later as a perf phase if Cloud Run OOMs surface in production telemetry.
- **YouTube `source_url` removal at `publisher.py:329`.** That is Phase 105's job. Plan 104-01's grep test must scope to the Twitter branch only, NOT to the whole file.
- **Instagram `video_url`** at `publisher.py:212`. That field IS real for IG and stays.
- **Cross-platform helper for "download bytes from URL".** Could be shared with Phase 105/107 — defer; each phase implements its own download for now to keep blast radius small.

## Claude's Discretion

These the executor decides during implementation; they do NOT need user sign-off:

- **APPEND endpoint shape.** RESEARCH flags ambiguity between `command=APPEND` form against `/2/media/upload` (well-documented, recommended) vs a dedicated `/2/media/upload/append` sub-endpoint (referenced in some community posts, docs inconsistent). **Default: `command=APPEND` form against `/2/media/upload`.** If smoke tests show 4xx, executor pivots to the sub-endpoint and updates unit tests.
- **MIME sniffing.** Use `Content-Type` header from the bytes-fetch response, fall back to `image/jpeg` / `video/mp4` if absent. Don't pull in a sniffing dependency.
- **Where to download bytes from `media_url`.** Inside the upload helper (matches RESEARCH reference impl). One extra HTTP round-trip is acceptable.
- **Frontend `reconnect_required` UX surface.** A `frontend/src/app/dashboard/configuration/page.tsx` toast/banner is sufficient; do NOT add a new admin page. If the existing `connected: false` rendering at line 290 already covers the reconnect case once the row is marked, no frontend change is needed beyond a conditional copy update.
- **STATUS-poll error surfacing.** A returned dict like `{"error": "Twitter video processing failed: <reason>"}` from `post_with_media` matches the existing error-shape convention (`publisher.py:108-110` `_get_token_or_error`).

## Open Questions (flagged for executor)

| # | Question | Default Path | Pivot Trigger |
|---|----------|--------------|----------------|
| 1 | APPEND endpoint shape (form `command=APPEND` vs sub-endpoint `/append`) | `command=APPEND` against `/2/media/upload` | First live smoke test returns 4xx with "unknown command" or "endpoint not found" |
| 2 | Memory pressure on >100MB videos | Read full bytes into memory; emit `logger.warning` if `total_bytes > 100 * 1024 * 1024` | Cloud Run OOM in production telemetry → ship tempfile fallback in a follow-up phase |
| 3 | OAuth2 + `media.write` reliability (community 403 reports) | Trust X's stated support; surface clear error on 403 | If ≥10% of users hit 403 post-rollout, schedule Option B (OAuth 1.0a) phase |

## Requirements coverage

| Req | Plan | Acceptance |
|-----|------|-----------|
| POST-04 (image simple upload + tweet attach) | 104-01 | Mock test asserts one POST to `api.x.com/2/media/upload` (multipart, `media_category=tweet_image`), returned `media_id` attached to `/2/tweets` body; smoke test (gated `RUN_LIVE=1`) posts a real 4MB JPEG |
| POST-05 (video chunked INIT→APPEND→FINALIZE→STATUS) | 104-02 | Mock state-machine test exercises `pending → in_progress → succeeded`, `pending → failed`, and timeout paths; grep test asserts `source_url` absent from Twitter branch; smoke test (gated) posts a real 30s 1080p video |
| POST-06 (auth strategy + scope) | 104-01 | Unit test asserts `connector.PLATFORM_CONFIGS["twitter"]["scopes"]` contains `"media.write"`; mock 403 test asserts user-friendly reconnect error message |

## Files in scope (touched by 104-XX plans)

- `app/social/connector.py` — scope addition (Plan 104-01)
- `app/social/publisher.py` — replace `_upload_media_twitter`, add `_upload_image_twitter` (Plan 104-01) and `_upload_video_twitter` (Plan 104-02), update Twitter branch dispatch
- `supabase/migrations/2026{N}_twitter_reconnect_required.sql` — one-shot migration marking existing Twitter rows for re-auth (Plan 104-01)
- `tests/unit/test_twitter_publisher.py` — NEW; image happy path, video state machine, grep-absence, auth error (Plans 104-01, 104-02)
- `tests/unit/test_social_connector_security.py` — extend with `test_twitter_scopes` (Plan 104-01)
- `tests/smoke/__init__.py` + `tests/smoke/test_twitter_live.py` — NEW; gated `RUN_LIVE=1` live tests (Plans 104-01, 104-02)

## Dependencies

- **Phase 101** (encrypted token reads) — already shipped per Phase 101 status; `connector.get_access_token` already decrypts. No work needed.
- **Plan 104-02 depends on Plan 104-01** — auth setup (scope + reconnect migration) lands first. Without `media.write` in scopes, every video upload would 403.

## Test strategy

- **Wave 0 (RED):** Each plan starts by scaffolding the failing tests in `tests/unit/test_twitter_publisher.py` (and extending `tests/unit/test_social_connector_security.py` for 104-01). Tests fail because the production code still calls v1.1 / lacks the helpers.
- **Wave 1 (GREEN):** Replace `_upload_media_twitter`, wire the dispatch, add the scope, ship the migration. All Wave 0 tests turn green.
- **Live smoke tests** (`tests/smoke/test_twitter_live.py`) are gated by `RUN_LIVE=1` env var (skipped by default in CI). They require `TWITTER_TEST_USER_ID` and a paid-tier connected account; run manually before phase verification. CI never hits the live X API.
- **Mock pattern:** `httpx.AsyncClient.post` / `.get` patched at the call site with `respx` (already in dev deps via httpx) OR with `unittest.mock.AsyncMock` returning `MagicMock(status_code=200, json=lambda: {...}, text="...")`. Keep the test file consistent with `tests/unit/test_social_connector_security.py`'s manual-fake style if `respx` is not yet a dep.

## Out of scope (do NOT touch)

- LinkedIn / Facebook / Instagram / TikTok / YouTube branches in `publisher.py`.
- The `/2/tweets` POST shape at `publisher.py:129-133`.
- OAuth callback / refresh logic.
- The encryption layer at `app/services/encryption.py`.
- Rate-limit handling beyond surfacing the 403 message.
