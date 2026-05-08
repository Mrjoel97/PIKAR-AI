# Phase 104 Research: Twitter Media Upload Fix

**Researched:** 2026-05-08
**Domain:** X (Twitter) API v2 media upload — auth, image simple upload, video chunked flow
**Confidence:** HIGH (primary claims verified against docs.x.com + X Developer Community announcements)

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| POST-04 | Image simple upload (≤5MB) attaches to tweet | API Reference §"Simple Upload (Images)"; auth strategy §"Decision" |
| POST-05 | Video chunked upload (INIT→APPEND→FINALIZE→STATUS) | API Reference §"Chunked Upload (Videos / Large Images / GIFs)" |
| POST-06 | OAuth1.0a vs OAuth2 auth context decision | §"Critical Decision: Auth Strategy" |

## Summary

X (Twitter) launched **v2 media upload endpoints on January 13, 2025**, and **sunset the v1.1 `upload.twitter.com/1.1/media/upload.json` endpoints on June 9, 2025**. The current code at `app/social/publisher.py:43-63` is broken on three independent axes: (1) it calls the now-removed v1.1 host, (2) it sends a fictional `source_url` parameter that never existed in any X media upload endpoint (X only accepts inline binary or base64 — there is no fetch-from-URL mode), and (3) even the INIT step shape is wrong — chunked INIT requires `total_bytes`, not `source_url`, and image upload uses a single-shot multipart POST, not chunked.

The good news for our OAuth2 PKCE setup (`connector.py:32-38`): **the v2 endpoint `POST https://api.x.com/2/media/upload` accepts both OAuth 1.0a User Context AND OAuth 2.0 User Context tokens**, provided the OAuth2 token carries the **`media.write`** scope. Our current scope list is `tweet.read tweet.write users.read offline.access` — `media.write` is missing and must be added (which forces a re-authorization for already-connected users).

**Primary recommendation:** Stay on OAuth 2.0 PKCE (no OAuth 1.0a code path). Add `media.write` to scopes. Use simple upload for images ≤5MB and dedicated chunked sub-endpoints (`/initialize`, `/append`, `/{id}/finalize`, GET STATUS) for video. Delete the fictional `source_url` parameter; download bytes from `media_url` first, then upload as multipart binary.

## Current State

**File:** `app/social/publisher.py:43-63` (`_upload_media_twitter`)

What's wrong:

1. **Endpoint is dead.** `https://upload.twitter.com/1.1/media/upload.json` was sunset 2025-06-09 ([Extended deadline announcement](https://devcommunity.x.com/t/extended-deadline-for-v1-1-media-upload-endpoints/240122)).
2. **`source_url` is fiction.** No X media upload endpoint (v1.1 or v2, simple or chunked) has ever accepted a `source_url` field. The same fictional parameter appears at `publisher.py:329` (YouTube — also wrong, addressed by Phase 105) and `publisher.py:212` (Instagram — actually `video_url`, which is real for IG).
3. **INIT-only.** `_upload_media_twitter` returns the `media_id_string` from INIT but never calls APPEND/FINALIZE/STATUS — the upload is never completed and the returned `media_id` is invalid for tweet attachment.
4. **Auth header is bearer-only.** `publisher.py:112` builds `Authorization: Bearer {token}` from the OAuth2 access token. This works for v2 media upload IF the OAuth2 scope grants `media.write`, but our `connector.py:44` scope list omits it.
5. **Tweet POST shape at `publisher.py:129-133` is correct** — `POST https://api.twitter.com/2/tweets` with `{"text": ..., "media": {"media_ids": [...]}}`. No change needed there.

**Connector** (`app/social/connector.py:32-47`):
- `auth_url`: `https://twitter.com/i/oauth2/authorize` ✓ (correct OAuth2 PKCE URL)
- `token_url`: `https://api.twitter.com/2/oauth2/token` ✓
- `scopes`: `["tweet.read", "tweet.write", "users.read", "offline.access"]` ✗ — **missing `media.write`**
- `client_id_env` / `client_secret_env`: `TWITTER_CLIENT_ID` / `TWITTER_CLIENT_SECRET` (OAuth2 confidential-client credentials)

**.env.example (`.env.example:62-63`):** Only `TWITTER_CLIENT_ID` / `TWITTER_CLIENT_SECRET` defined. There are **no** `TWITTER_CONSUMER_KEY` / `TWITTER_CONSUMER_SECRET` env vars — adding an OAuth 1.0a code path would require new app-level credentials provisioned in the X Developer Portal AND a parallel signing implementation (HMAC-SHA1 over canonicalized request).

## API Reference (verified)

### v1.1 status
- `https://upload.twitter.com/1.1/media/upload.json` — **DEAD** as of 2025-06-09. Source: [Deprecating the v1.1 media upload endpoints](https://devcommunity.x.com/t/deprecating-the-v1-1-media-upload-endpoints/238196), [Extended deadline](https://devcommunity.x.com/t/extended-deadline-for-v1-1-media-upload-endpoints/240122). Calls return `403 / "The Twitter REST API v1 is no longer active"`.

### v2 endpoint family

**Base host:** `https://api.x.com` (not `api.twitter.com`; both resolve, but X's docs canonicalize on `api.x.com`).

| Operation | Method + URL | Auth | Body |
|-----------|--------------|------|------|
| **Simple upload** (single shot, images ≤5MB) | `POST https://api.x.com/2/media/upload` | OAuth 1.0a User Context **or** OAuth 2.0 User Context (`media.write`) | `multipart/form-data`; either `media` (raw binary) or `media_data` (base64). `media_category` optional but recommended (`tweet_image`, `tweet_gif`). |
| **Chunked INIT** | `POST https://api.x.com/2/media/upload/initialize` | same | JSON: `{"media_type": "video/mp4", "total_bytes": 12345678, "media_category": "tweet_video", "additional_owners": [...]}`. Returns `{"data": {"id": "<media_id>", "media_key": "...", "expires_after_secs": ...}}` |
| **Chunked APPEND** | `POST https://api.x.com/2/media/upload` | same | `multipart/form-data`: `command=APPEND`, `media_id=<id>`, `segment_index=<0..N>`, `media=<chunk binary, ≤4MB>`. Returns 204 No Content. *(Note: legacy `command=APPEND` form against the unified `/2/media/upload` endpoint is the documented chunked APPEND; X also exposes a dedicated APPEND sub-endpoint — see "Open Questions".)* |
| **Chunked FINALIZE** | `POST https://api.x.com/2/media/upload/{id}/finalize` | same | empty body. Returns `{"data": {"id": "...", "size": ..., "expires_after_secs": ..., "processing_info": {"state": "pending", "check_after_secs": 5}}}` |
| **STATUS poll** | `GET https://api.x.com/2/media/upload?command=STATUS&media_id={id}` | same | Query params only. Returns `{"data": {"processing_info": {"state": "succeeded" \| "in_progress" \| "pending" \| "failed", "check_after_secs": <int>, "progress_percent": <0..100>, "error": {"code": ..., "message": ...} (on failure)}}}` |
| **Tweet attach** | `POST https://api.twitter.com/2/tweets` | OAuth 2.0 user context (`tweet.write`) | `{"text": "...", "media": {"media_ids": ["<media_id>"]}}` |

Sources for above table:
- [Chunked Media Upload — docs.x.com](https://docs.x.com/x-api/media/quickstart/media-upload-chunked)
- [Initialize a media upload request — docs.x.com](https://docs.x.com/x-api/media/media-upload-initialize)
- [Finalize a media upload request — docs.x.com](https://docs.x.com/x-api/media/media-upload-finalize)
- [Media Upload Status — docs.x.com](https://docs.x.com/x-api/media/media-upload-status)
- [Best practices — docs.x.com](https://docs.x.com/x-api/media/quickstart/best-practices)
- [Announcing media upload endpoints in the X API v2 (2025-01-13)](https://devcommunity.x.com/t/announcing-media-upload-endpoints-in-the-x-api-v2/234175)

### `processing_info.state` lifecycle
`pending → in_progress → (succeeded | failed)`. Per [Media Upload Status](https://docs.x.com/x-api/media/media-upload-status): "You cannot use the media_id to create a Post or other entities before the state field is set to `succeeded`." Use `check_after_secs` from the latest STATUS response as the next sleep interval; if absent, default to 2s.

### Constraints (from docs.x.com best practices and INIT reference)

| Constraint | Value |
|------------|-------|
| Image max size (simple upload) | 5 MB |
| Image max size (chunked) | 5 MB (image) — chunked is rarely needed for images |
| GIF max size | 15 MB |
| Video max size | 512 MB (synced with X consumer limits — Premium tier higher) |
| Video max duration | 140 seconds (standard); longer for verified/Premium |
| Supported image MIMEs | `image/jpeg`, `image/png`, `image/gif`, `image/webp` |
| Supported video MIMEs | `video/mp4` (H.264 + AAC), `video/quicktime` |
| `media_category` values | `tweet_image`, `tweet_gif`, `tweet_video`, `dm_image`, `dm_gif`, `dm_video`, `subtitles`, `amplify_video` |
| Chunk size (APPEND) | ≤ 4 MB per chunk (recommended); max segment_index ~999 |

## Critical Decision: Auth Strategy

**Three options, evaluated:**

### Option A (RECOMMENDED): OAuth 2.0 User Context + add `media.write` scope
**Trade-offs:**
- ✅ Single auth path — no parallel OAuth 1.0a signing code, no new env vars, no DB schema changes
- ✅ Confirmed supported on `/2/media/upload` ([Media Upload thread](https://devcommunity.x.com/t/media-upload/238468), [How to Upload Media to Twitter API v2 Using OAuth 2.0?](https://devcommunity.x.com/t/how-to-upload-media-to-twitter-api-v2-using-oauth-2-0/238518)) — "supported authentication types are OAuth 1.0a User Context and OAuth 2.0 User Context"
- ✅ Reuses existing PKCE flow at `connector.py:213-255`
- ⚠️ Requires re-authorization for every connected Twitter account (changing scopes invalidates existing tokens). Migration: clear `connected_accounts` rows where `platform='twitter'` (or set `status='reconnect_required'`) and prompt re-auth.
- ⚠️ Some users on devcommunity report intermittent 403s with OAuth2 even with `media.write` ([/2/media/upload - not permitted to use OAuth2](https://devcommunity.x.com/t/2-media-upload-not-permitted-to-use-oauth2-on-this-endpoint/244602)). Mitigation: surface a precise error message instructing the user to reconnect with the new scope.

### Option B: Add OAuth 1.0a path alongside OAuth 2.0
**Trade-offs:**
- ❌ Requires new env vars (`TWITTER_CONSUMER_KEY`, `TWITTER_CONSUMER_SECRET`)
- ❌ Requires implementing OAuth 1.0a signing (HMAC-SHA1 with canonicalized parameter string + per-user `oauth_token` / `oauth_token_secret` exchange via `/oauth/request_token`, `/oauth/authorize`, `/oauth/access_token`)
- ❌ Two stored token shapes per platform; new schema column or re-encoded blob
- ❌ Adds attack surface and substantially more test paths
- ✅ Marginally more reliable per anecdotal community reports
- ✅ Some legacy v1.1-only operations (none we use) still need it

### Option C: Document limitation, disable media upload
- ❌ Regresses POST-04 / POST-05 success criteria
- Use only as a fallback if Option A unexpectedly fails in production after rollout

**Decision: Option A.** Migration steps:
1. Update `connector.py:44` scopes list to include `"media.write"`.
2. Add a one-time DB update to mark existing twitter connections `status='reconnect_required'` (or simply `revoked`).
3. Surface a frontend toast / banner when a twitter post fails with `403 forbidden` for media upload, instructing the user to reconnect.
4. Add a unit test asserting the scope list contains `media.write`.

## Implementation Approach

### Image upload (simple, ≤5MB) — `_upload_image_twitter`

```python
async def _upload_image_twitter(
    self, http: httpx.AsyncClient, headers: dict, media_url: str
) -> str | None:
    """Simple-shot image upload to X v2. Returns media_id_string."""
    # 1. Download bytes from caller-provided URL.
    img_resp = await http.get(media_url)
    img_resp.raise_for_status()
    img_bytes = img_resp.content
    if len(img_bytes) > 5 * 1024 * 1024:
        logger.warning("Image >5MB; falling back to chunked upload")
        return await self._upload_chunked_twitter(
            http, headers, img_bytes, media_type="image", mime="image/jpeg"
        )

    # 2. Sniff MIME (best-effort) for media_type form field.
    mime = img_resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()

    # 3. Multipart POST.
    upload_resp = await http.post(
        "https://api.x.com/2/media/upload",
        headers=headers,  # Authorization: Bearer <token with media.write>
        files={"media": ("upload", img_bytes, mime)},
        data={"media_category": "tweet_image"},
    )
    if upload_resp.status_code not in (200, 201):
        logger.warning("Twitter image upload failed: %s", upload_resp.text)
        return None
    return upload_resp.json().get("data", {}).get("id") \
        or upload_resp.json().get("media_id_string")
```

### Video upload (chunked) — `_upload_video_twitter`

```python
async def _upload_video_twitter(
    self, http: httpx.AsyncClient, headers: dict, media_url: str
) -> str | None:
    """Chunked video upload: INIT → APPEND → FINALIZE → STATUS poll."""
    # 1. Download full video to memory (or stream to /tmp for >100MB).
    vid_resp = await http.get(media_url)
    vid_resp.raise_for_status()
    vid_bytes = vid_resp.content
    total_bytes = len(vid_bytes)
    mime = vid_resp.headers.get("content-type", "video/mp4").split(";")[0].strip()

    # 2. INIT
    init_resp = await http.post(
        "https://api.x.com/2/media/upload/initialize",
        headers={**headers, "Content-Type": "application/json"},
        json={
            "media_type": mime,
            "total_bytes": total_bytes,
            "media_category": "tweet_video",
        },
    )
    if init_resp.status_code not in (200, 201, 202):
        logger.warning("Twitter video INIT failed: %s", init_resp.text)
        return None
    media_id = init_resp.json().get("data", {}).get("id")
    if not media_id:
        return None

    # 3. APPEND chunks (≤4MB each)
    chunk_size = 4 * 1024 * 1024
    for i in range(0, total_bytes, chunk_size):
        chunk = vid_bytes[i : i + chunk_size]
        seg_idx = i // chunk_size
        append_resp = await http.post(
            "https://api.x.com/2/media/upload",
            headers=headers,
            data={
                "command": "APPEND",
                "media_id": media_id,
                "segment_index": seg_idx,
            },
            files={"media": ("chunk", chunk, "application/octet-stream")},
        )
        if append_resp.status_code not in (200, 204):
            logger.warning("Twitter APPEND seg=%d failed: %s", seg_idx, append_resp.text)
            return None

    # 4. FINALIZE
    final_resp = await http.post(
        f"https://api.x.com/2/media/upload/{media_id}/finalize",
        headers=headers,
    )
    if final_resp.status_code not in (200, 201):
        logger.warning("Twitter FINALIZE failed: %s", final_resp.text)
        return None

    # 5. STATUS poll until succeeded (loop with cap to prevent runaway)
    proc = final_resp.json().get("data", {}).get("processing_info")
    if not proc:
        return media_id  # Already succeeded (rare but per docs possible)

    deadline = asyncio.get_event_loop().time() + 600  # 10-min cap
    while proc and proc.get("state") in ("pending", "in_progress"):
        if asyncio.get_event_loop().time() > deadline:
            logger.warning("Twitter STATUS poll timed out for media_id=%s", media_id)
            return None
        await asyncio.sleep(proc.get("check_after_secs", 2))
        status_resp = await http.get(
            "https://api.x.com/2/media/upload",
            headers=headers,
            params={"command": "STATUS", "media_id": media_id},
        )
        if status_resp.status_code != 200:
            logger.warning("Twitter STATUS failed: %s", status_resp.text)
            return None
        proc = status_resp.json().get("data", {}).get("processing_info")

    if proc and proc.get("state") == "failed":
        err = proc.get("error", {})
        logger.warning("Twitter media processing failed: %s", err)
        return None
    return media_id
```

### Refactored `post_with_media` Twitter branch (publisher.py:117-134)

Replace lines 117-134 with media-type dispatch:

```python
if platform == "twitter":
    tweet_payload: dict[str, Any] = {"text": content}
    if has_media:
        if media_type == "video":
            media_id = await self._upload_video_twitter(http, headers, media_urls[0])
        else:  # image, carousel-first, gif
            media_id = await self._upload_image_twitter(http, headers, media_urls[0])
        if not media_id:
            return {"error": "Twitter media upload failed (see logs); tweet not posted"}
        tweet_payload["media"] = {"media_ids": [media_id]}
    resp = await http.post(
        "https://api.twitter.com/2/tweets",
        headers={**headers, "Content-Type": "application/json"},
        json=tweet_payload,
    )
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth 1.0a HMAC-SHA1 signing | Custom signing of canonicalized request strings | Pick Option A (OAuth2) and avoid this entirely | Signing has a notorious number of edge cases (percent-encoding, parameter ordering, body inclusion rules); a single bug yields opaque 401s |
| Async chunked file IO | Manual asyncio.Queue producer/consumer | Just `await http.post` per chunk in a `for` loop | We're talking 30-second video = 8 chunks max; sequential is fine, simpler, and easier to test |
| Retry/backoff on STATUS poll | Custom retry decorator | Honor `check_after_secs` from response + cap total wait | The API tells you when to come back; respecting that avoids rate-limit penalties |
| Multipart encoding | Manual boundary construction | Use httpx `files=` parameter | httpx handles boundary, content-type, content-disposition correctly |

## Common Pitfalls

### Pitfall 1: Forgetting `media.write` scope
**What goes wrong:** OAuth2 token is issued, upload returns 403 with confusing error.
**Why it happens:** Default scope list omits `media.write`; users who already connected before this change have stale tokens.
**How to avoid:** Add to scopes list AND mark existing rows as `reconnect_required`. Add an integration test that asserts a freshly-issued token's response includes `media.write` in the granted scopes.

### Pitfall 2: Using `api.twitter.com` for media upload host
**What goes wrong:** Some legacy guides use `api.twitter.com/2/media/upload`; both hosts resolve but X's docs and rate-limit accounting canonicalize on `api.x.com`.
**How to avoid:** Use `api.x.com` for all media calls; keep `api.twitter.com` only for `/2/tweets` (where the canonical host is still that one — and yes, this is silly).

### Pitfall 3: Skipping STATUS poll
**What goes wrong:** FINALIZE returns 200 with `processing_info.state='pending'`; code attaches the `media_id` to the tweet immediately; tweet POST returns 400 "Media not ready" or the tweet is silently posted without media.
**How to avoid:** Always check for `processing_info` on FINALIZE; poll until `succeeded` or `failed`. Never attach a `media_id` whose processing state is anything but `succeeded`.

### Pitfall 4: Wrong `media_category`
**What goes wrong:** `tweet_image` for a video = INIT 400. Omitting `media_category` for video = upload succeeds but `media_id` is rejected by tweet POST (because the inferred category is `dm_video`, which isn't valid for tweets).
**How to avoid:** Always pass `media_category=tweet_video` for video, `tweet_image` for static images, `tweet_gif` for GIFs.

### Pitfall 5: APPEND `segment_index` skipped/duplicated
**What goes wrong:** Off-by-one in chunk loop = FINALIZE returns 400 "Segments missing".
**How to avoid:** Use `for i in range(0, total, chunk_size)` and `seg_idx = i // chunk_size` (zero-based, contiguous). Add a unit test asserting `segment_index` sequence is `[0, 1, 2, ...]`.

### Pitfall 6: Re-downloading media inside the upload helper
**What goes wrong:** `_upload_image_twitter` downloads from `media_url` even when caller already has bytes; doubles latency and bandwidth.
**Mitigation:** Accept either `media_url` (URL) or `media_bytes` (already-downloaded bytes); planner/Phase 105 may share a fetch helper.

## Code Examples (verified)

### Multipart form upload via httpx (image simple)
Source: pattern from [httpx multipart docs](https://www.python-httpx.org/quickstart/#sending-multipart-file-uploads), endpoint shape from [docs.x.com/x-api/media/quickstart](https://docs.x.com/x-api/media/quickstart):

```python
files = {"media": ("photo.jpg", img_bytes, "image/jpeg")}
data = {"media_category": "tweet_image"}
r = await http.post(
    "https://api.x.com/2/media/upload",
    headers={"Authorization": f"Bearer {token}"},
    files=files, data=data,
)
media_id = r.json()["data"]["id"]  # v2 envelope; older v1.1 used "media_id_string"
```

### STATUS polling pattern
Source: [Media Upload Status — docs.x.com](https://docs.x.com/x-api/media/media-upload-status):

```python
while True:
    r = await http.get(
        "https://api.x.com/2/media/upload",
        headers=headers,
        params={"command": "STATUS", "media_id": media_id},
    )
    info = r.json()["data"]["processing_info"]
    if info["state"] == "succeeded":
        break
    if info["state"] == "failed":
        raise RuntimeError(f"Processing failed: {info.get('error')}")
    await asyncio.sleep(info.get("check_after_secs", 2))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `upload.twitter.com/1.1/media/upload.json` | `api.x.com/2/media/upload` (+ `/initialize`, `/{id}/finalize`) | v1.1 sunset 2025-06-09 | Mandatory — old endpoint returns 403 |
| OAuth 1.0a only for media | OAuth 1.0a OR OAuth 2.0 User Context (`media.write`) | 2025-01-13 v2 GA | Eliminates dual-auth complexity |
| Single-flat command-as-form-field for INIT/FINALIZE | Dedicated sub-endpoints `/initialize`, `/{id}/finalize` (alongside legacy `command=` form) | 2025-Q1 | New endpoints preferred; legacy form-based still works for APPEND |
| `application/json` body for INIT | Same — INIT body is JSON via `/initialize` sub-endpoint | n/a | n/a |

**Deprecated/outdated:**
- `source_url` form field — never existed; remove from codebase (also affects YouTube branch at `publisher.py:329`, addressed by Phase 105)
- `upload.twitter.com` host — replace all references with `api.x.com`

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x with pytest-asyncio (per `pyproject.toml` and `make test`) |
| Config file | `pyproject.toml` (project-level) |
| Quick run command | `uv run pytest tests/unit/test_twitter_publisher.py -x` |
| Full suite command | `make test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| POST-04 | 4MB JPEG upload via simple endpoint, attached to tweet | unit (mocked httpx) | `uv run pytest tests/unit/test_twitter_publisher.py::test_image_simple_upload -x` | ❌ Wave 0 |
| POST-04 | Live: real 4MB JPEG posts to test account, image renders | smoke (gated, `RUN_LIVE=1`) | `uv run pytest tests/smoke/test_twitter_live.py::test_image_post -x` | ❌ Wave 0 |
| POST-05 | 30s 1080p video via INIT→APPEND→FINALIZE→STATUS=succeeded | unit (mocked httpx with state machine) | `uv run pytest tests/unit/test_twitter_publisher.py::test_video_chunked_upload -x` | ❌ Wave 0 |
| POST-05 | Verify fictional `source_url` absent | grep test | `uv run pytest tests/unit/test_twitter_publisher.py::test_no_fictional_source_url -x` | ❌ Wave 0 |
| POST-05 | Live: real 30s video posts and plays | smoke (gated) | `uv run pytest tests/smoke/test_twitter_live.py::test_video_post -x` | ❌ Wave 0 |
| POST-06 | OAuth2 scope list contains `media.write` | unit | `uv run pytest tests/unit/test_social_connector_security.py::test_twitter_scopes -x` | ✅ (extend existing) |
| POST-06 | 403 on missing scope surfaces clear error | unit (mocked 403 response) | `uv run pytest tests/unit/test_twitter_publisher.py::test_403_missing_scope_message -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/test_twitter_publisher.py -x` (~5s)
- **Per wave merge:** `make test` (full unit + integration + workflow validation)
- **Phase gate:** Full suite green + (optionally) `RUN_LIVE=1 uv run pytest tests/smoke/test_twitter_live.py` against a sandbox X account before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_twitter_publisher.py` — covers POST-04 (image), POST-05 (video state machine + grep for `source_url`), POST-06 (auth-error message)
- [ ] `tests/smoke/test_twitter_live.py` — gated live tests (POST-04, POST-05 success criterion 1 & 2)
- [ ] Extend `tests/unit/test_social_connector_security.py` with `test_twitter_scopes` asserting `media.write` is present

## Key Risks & Open Questions

1. **APPEND endpoint shape ambiguity.** docs.x.com primarily documents the legacy `command=APPEND` form against the unified `/2/media/upload` path. There are community references to a dedicated `/2/media/upload/append` sub-endpoint, but the docs are inconsistent. **Recommendation:** Use `command=APPEND` against the unified `/2/media/upload` endpoint (well-documented, broadly supported). If 4xx, planner can pivot to the sub-endpoint. Cite: [Chunked Media Upload — docs.x.com](https://docs.x.com/x-api/media/quickstart/media-upload-chunked).

2. **OAuth2 + `media.write` reliability.** Some community threads ([/2/media/upload — not permitted to use OAuth2](https://devcommunity.x.com/t/2-media-upload-not-permitted-to-use-oauth2-on-this-endpoint/244602)) report 403s even with the scope. X's first-party stance is that OAuth2 is supported. **Mitigation:** Robust error path → user-facing reconnect prompt; fall back plan documented (Option B / OAuth 1.0a) is deferred to a future phase if needed.

3. **Scope migration breaks existing connections.** Any user who connected Twitter pre-Phase-104 will have a token without `media.write`. **Mitigation:** Single-shot SQL migration to set `connected_accounts.status = 'reconnect_required'` for all `platform = 'twitter'` rows; frontend treats this status as "click to reconnect"; banner in dashboard.

4. **Free-tier rate limits.** X's free tier currently allows ~17 media uploads / 24h per user-context (community-reported, not in formal docs). Live smoke tests must run on a paid Basic tier or risk false failures; gate behind `RUN_LIVE=1` env to keep CI hermetic.

5. **Video size cap in single-shot.** docs.x.com Best Practices recommend chunked for any video regardless of size. **Decision:** Always chunked for `media_type == "video"`; never attempt simple upload for video.

6. **Memory pressure on large videos.** The reference implementation reads the full video into memory. For >100MB videos, this could be a problem on Cloud Run instances (memory tiers from 512Mi). **Mitigation:** Add a `MAX_VIDEO_BYTES_INMEMORY = 100 * 1024 * 1024` guard; for larger files, stream to `tempfile.NamedTemporaryFile` first then read in chunks. This is an open task for the planner — could be Phase-104 scope or deferred.

## Plan Decomposition Hint

Suggest **2 plans** to keep each plan reviewable and testable:

### Plan 104-01: Image Simple Upload + Auth Strategy
**Scope:**
- Add `media.write` to `connector.py` scopes
- DB migration to mark existing twitter connections `reconnect_required`
- Replace `_upload_media_twitter` with two helpers: `_upload_image_twitter` (simple) and `_upload_video_twitter` (stub, raises NotImplementedError)
- Wire the publisher branch to dispatch by `media_type`
- Delete the fictional `source_url` parameter
- Unit tests: scope check, image upload happy path, 403 missing-scope error path
- Frontend: error toast / banner for `reconnect_required` status

**Acceptance:** POST-04 success criterion 1 + POST-06 success criterion 3.

### Plan 104-02: Video Chunked Upload + STATUS Poll
**Scope:**
- Implement `_upload_video_twitter` full INIT→APPEND→FINALIZE→STATUS flow
- Add `MAX_VIDEO_BYTES_INMEMORY` guard with tempfile fallback (or defer)
- Honor `check_after_secs`; cap total wait at 10 minutes; surface `processing_info.error` on failure
- Unit tests: state machine through `pending → in_progress → succeeded`, `pending → failed`, timeout
- Smoke test (gated `RUN_LIVE=1`): real 30s 1080p video posts and plays

**Acceptance:** POST-05 success criterion 2.

**Dependency:** Plan 104-02 depends on 104-01 (auth setup must land first).

## Sources

### Primary (HIGH confidence)
- [Chunked Media Upload — docs.x.com](https://docs.x.com/x-api/media/quickstart/media-upload-chunked) — exact INIT/APPEND/FINALIZE/STATUS shapes
- [Initialize a media upload request — docs.x.com](https://docs.x.com/x-api/media/media-upload-initialize) — INIT endpoint reference
- [Finalize a media upload request — docs.x.com](https://docs.x.com/x-api/media/media-upload-finalize) — FINALIZE endpoint reference
- [Media Upload Status — docs.x.com](https://docs.x.com/x-api/media/media-upload-status) — STATUS state machine and `processing_info` shape
- [Best practices — docs.x.com](https://docs.x.com/x-api/media/quickstart/best-practices) — size limits, MIME types, recommendations
- [Announcing media upload endpoints in the X API v2 (2025-01-13)](https://devcommunity.x.com/t/announcing-media-upload-endpoints-in-the-x-api-v2/234175) — GA date and supported auth
- [Deprecating the v1.1 media upload endpoints](https://devcommunity.x.com/t/deprecating-the-v1-1-media-upload-endpoints/238196) — sunset notice
- [Extended deadline for v1.1 media upload endpoints](https://devcommunity.x.com/t/extended-deadline-for-v1-1-media-upload-endpoints/240122) — final sunset 2025-06-09

### Secondary (MEDIUM confidence — verified against primary)
- [How to Upload Media to Twitter API v2 Using OAuth 2.0?](https://devcommunity.x.com/t/how-to-upload-media-to-twitter-api-v2-using-oauth-2-0/238518) — confirms OAuth2 + `media.write` works
- [Media Upload — X API v2 (community thread)](https://devcommunity.x.com/t/media-upload/238468) — supported auth types
- [Request for OAuth 1.0a Compatibility with /2/media/upload](https://devcommunity.x.com/t/request-for-oauth-1-0a-compatibility-with-2-media-upload-endpoint/238993) — confirms both auths work
- [Tweeting Media with v2 of the Twitter API in Python](https://developer.x.com/en/docs/tutorials/tweeting-media-v2) — tweet attachment shape

### Tertiary (LOW confidence — flagged)
- [/2/media/upload — not permitted to use OAuth2](https://devcommunity.x.com/t/2-media-upload-not-permitted-to-use-oauth2-on-this-endpoint/244602) — anecdotal OAuth2 issues; treated as risk, not as blocker
- Free-tier rate limits (~17 media/24h) — community-reported, not in formal docs

## Metadata

**Confidence breakdown:**
- v2 endpoint URLs and shapes: HIGH — direct from docs.x.com
- OAuth2 + `media.write` support: HIGH — multiple primary sources confirm
- v1.1 sunset date (2025-06-09): HIGH — official announcement
- APPEND endpoint (form-based vs sub-endpoint): MEDIUM — docs slightly inconsistent; recommend form-based and pivot if needed
- Free-tier rate limits: LOW — community-reported only, flagged as smoke-test risk
- Memory pressure approach: MEDIUM — engineering judgment, not API-mandated

**Research date:** 2026-05-08
**Valid until:** 2026-06-08 (30 days; X API is currently stable post-v1.1-sunset)
