# Phase 103 Research: LinkedIn Posting Fix

**Researched:** 2026-05-08
**Domain:** LinkedIn Marketing/Community-Management REST API + LinkedIn OIDC + LinkedIn webhooks (HMAC verification)
**Confidence:** HIGH (all three workstreams verified against canonical Microsoft Learn docs at li-lms-2026-04 versioning)

---

## Summary

Phase 103 fixes three concrete defects in `app/social/`:

1. **POST-01 — Hardcoded URN.** `app/social/publisher.py:162` writes the literal string `"urn:li:person:PERSON_ID"` as the post author. Every member-authored LinkedIn post is currently broken (rejected with `INVALID_URN_ID` 400). Fix: at OAuth callback time, GET `https://api.linkedin.com/v2/userinfo` with the freshly-issued bearer token; persist the `sub` claim into `connected_accounts.platform_user_id` (column already exists per `supabase/migrations/0010_connected_accounts.sql:8`); at publish time, compose `urn:li:person:{platform_user_id}` as the `author` value.

2. **POST-02 — Deprecated endpoint.** `app/social/publisher.py:155-171` still calls `/v2/ugcPosts` with the legacy `specificContent.com.linkedin.ugc.ShareContent` envelope. The Posts API replaces ugcPosts; the request shape is dramatically flatter (`commentary` top-level, `visibility` is a plain string, `content.media.id` for image/video URN). The new endpoint requires `LinkedIn-Version: 202401` (or newer) plus the existing `X-Restli-Protocol-Version: 2.0.0`. Fix: rewrite the LinkedIn branch of `post_with_media`; route image-attached posts through `/rest/images?action=initializeUpload` → `PUT` binary to returned `uploadUrl` → use returned `urn:li:image:...` as `content.media.id`; route video posts through `/rest/videos?action=initializeUpload` → `PUT` chunks per `uploadInstructions` → `/rest/videos?action=finalizeUpload` with collected `ETag` part IDs → use returned `urn:li:video:...` as `content.media.id`.

3. **POST-03 — Webhook signature audit defect.** `app/social/linkedin_webhook.py:37-58` and `app/routers/webhooks.py:104` exist BUT are **wrong on three details**: the header is `X-LI-Signature` (not `X-LinkedIn-Signature`), the value is prefixed `hmacsha256=` (the prefix must be stripped before HMAC compare), and the secret is `LINKEDIN_CLIENT_SECRET` (not `LINKEDIN_WEBHOOK_SECRET`). The POST-03 audit assumption that `LINKEDIN_WEBHOOK_SECRET` is "never enforced" is partially right (current `verify_signature` IS called from `webhooks.py:105`, but it uses the wrong secret and wrong header name, so all real LinkedIn signatures fail and current production logs would show 100% rejection). Fix: rewrite `verify_signature` to use `LINKEDIN_CLIENT_SECRET`, strip the `hmacsha256=` prefix, and read the `X-LI-Signature` header. Decide whether to keep `LINKEDIN_WEBHOOK_SECRET` env var as a separate "shared secret" we control (off-spec but provides defense-in-depth) — recommendation: **drop it; trust LinkedIn's spec**, document deprecation in `.env.example`.

**Primary recommendation:** Two plans. Plan 103-01 owns POST-01 + POST-02 (URN capture in callback + Posts API migration with image/video support, all in `app/social/`); Plan 103-02 owns POST-03 (webhook signature realignment in `app/social/linkedin_webhook.py` + `app/routers/webhooks.py`, with backward-compat shim if any deployed environments populated `LINKEDIN_WEBHOOK_SECRET`).

---

## User Constraints

No `CONTEXT.md` exists for Phase 103 (none was authored by `/gsd:discuss-phase`). The phase's scope is fully defined by `ROADMAP.md` lines 480-493 and `REQUIREMENTS.md` POST-01/02/03. Treat the success criteria as locked.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| **POST-01** | OAuth callback fetches member URN from `/v2/userinfo` `sub` claim, stores as `platform_user_id`; publisher uses `urn:li:person:{platform_user_id}` as `author` | Verified: OIDC discovery doc (`https://www.linkedin.com/oauth/.well-known/openid-configuration`) lists `userinfo_endpoint=https://api.linkedin.com/v2/userinfo` with `sub` claim returning a per-app pairwise identifier; the canonical post-creation example at Microsoft Learn explicitly uses `"author": "urn:li:person:5abc_dEfgH"` for member-authored posts when `q=author` finder is used. Existing `connected_accounts.platform_user_id TEXT` column at `supabase/migrations/0010_connected_accounts.sql:8` is ready. Storage value: store the **bare sub** (e.g. `782bbtaQ`) — NOT the full URN — so the URN can be reconstructed deterministically. (See Open Question 1 on pairwise vs canonical member ID.) |
| **POST-02** | Migrate from `/v2/ugcPosts` → `/rest/posts` with `LinkedIn-Version: 202401`; support text, single-image, video | Verified: full request shapes for text-only, image, and video posts captured from canonical Posts API doc (li-lms-2026-04). New shape uses top-level `commentary`, top-level `visibility: "PUBLIC"`, `distribution.feedDistribution: "MAIN_FEED"`, `content.media.id: "urn:li:image:..."` or `urn:li:video:...`. Image upload: `POST /rest/images?action=initializeUpload` returns `value.uploadUrl` + `value.image` (URN); `PUT` raw bytes to `uploadUrl`. Video upload: `POST /rest/videos?action=initializeUpload` with `fileSizeBytes` returns multi-part `uploadInstructions[]` + `uploadToken`; `PUT` each chunk; collect ETag from each part; `POST /rest/videos?action=finalizeUpload` with `uploadedPartIds[]` and `uploadToken`. Success status: **201** for `/rest/posts` (post URN returned in `x-restli-id` response header), **200** for image/video init, **200** for video upload chunks (returns ETag header), **200** for video finalize. |
| **POST-03** | Validate `X-LI-Signature` HMAC-SHA256 on inbound webhooks | Verified against canonical Microsoft Learn webhook validation doc dated 2025-08-27. Specification quote: *"The POST request sent by LinkedIn will include a header called `X-LI-Signature`. The value of this header is the HMACSHA256 hash of the JSON-encoded string representation of the POST body prefixed by `hmacsha256=` and it is computed using your app's clientSecret."* Existing GET challenge handler at `app/routers/webhooks.py:46-86` is correct (uses `LINKEDIN_CLIENT_SECRET`, hex-encoded HMACSHA256 of `challengeCode`). Existing POST verify at `app/routers/webhooks.py:104` reads the **wrong** header (`X-LinkedIn-Signature` instead of `X-LI-Signature`) and `linkedin_webhook.py:32-58` uses **wrong** secret env (`LINKEDIN_WEBHOOK_SECRET` instead of `LINKEDIN_CLIENT_SECRET`) and **doesn't strip** the `hmacsha256=` prefix. |

---

## Current State (file:line evidence)

### Hardcoded placeholder (POST-01)
- `app/social/publisher.py:162` — `"author": "urn:li:person:PERSON_ID"` is a literal string. Every member-authored LinkedIn post fails LinkedIn's URN validator with HTTP 400 `INVALID_URN_ID`. The publisher reaches this line on every LinkedIn `post_text`/`post_with_media` invocation.
- `app/social/connector.py:206-232` — `handle_callback` exchanges code for token, then directly upserts into `connected_accounts` with `access_token`/`refresh_token`/`scopes`/`status`. **Never** populates `platform_user_id` or `platform_username` (columns at migration:8-9).
- LinkedIn scopes already include `openid` and `profile` (`connector.py:28`), which are the exact permissions required to call `/v2/userinfo` per the OIDC spec. **No new scope is needed.**

### Deprecated endpoint (POST-02)
- `app/social/publisher.py:155-171` — POSTs to `https://api.linkedin.com/v2/ugcPosts` with the legacy v2 envelope. Body uses `specificContent.com.linkedin.ugc.ShareContent.shareCommentary.text` and `visibility.com.linkedin.ugc.MemberNetworkVisibility: "PUBLIC"`. The Microsoft Learn ugcPosts doc carries a **Deprecation Notice** banner ("the Posts API replaces the ugcPosts API"); Marketing version 202504 is sunset.
- The `share_media_category` switching at `publisher.py:137-154` does NOT actually upload media — it just embeds raw `originalUrl` strings into a `media[]` array. This shape was never valid for UGC posts and is definitely not valid for `/rest/posts`. So even if the URN were correct, image/video posts would fail (and have been failing).
- No `LinkedIn-Version` header is ever sent.

### Webhook handler exists but is broken (POST-03)
- `app/social/linkedin_webhook.py` exists (137 lines). `verify_signature` at line 37 uses `os.environ["LINKEDIN_WEBHOOK_SECRET"]` and reads `signature` parameter as hex-encoded HMAC-SHA256 with **no prefix handling**.
- `app/routers/webhooks.py:104` reads `request.headers.get("X-LinkedIn-Signature", "")`. **LinkedIn does not send this header.** It sends `X-LI-Signature`. Result: every real LinkedIn webhook is rejected with 403.
- `app/routers/webhooks.py:107` raises 403 on signature mismatch (POST-03 success criterion #3 says "rejected with HTTP 401" — this is a discrepancy worth resolving with the planner; I recommend keeping 403 because the audit success criterion was probably written without checking existing code, and 403 is more correct semantically for "credential present but invalid"; either is RFC-compliant; the auditor and planner can decide).
- `LINKEDIN_WEBHOOK_SECRET` env var is configured in `.env.example:87`, `cloud-run-service.yaml:73-74`, `terraform/vars/env.tfvars:48`, and `cloudflare/public-api/src/index.ts:14655` — but per the official LinkedIn spec it is **not a real LinkedIn concept**. LinkedIn signs with `clientSecret`. The existing `LINKEDIN_WEBHOOK_SECRET` env var should be deprecated in favor of the existing `LINKEDIN_CLIENT_SECRET`.

### Phase 101 coordination
- Phase 101 (Security Hardening, AUTH-04) generalizes "OAuth callback captures `platform_user_id` for ALL providers." Phase 103 implements the LinkedIn-specific provider hook that AUTH-04 will plug into.
- **Coordination strategy:** Phase 103 should NOT block on Phase 101. Implement a per-platform "fetch identity" function in `connector.py` (e.g., `_fetch_linkedin_identity(token: str) -> tuple[str, str]`) and call it inline at the end of `handle_callback` for `platform == "linkedin"`. Phase 101 will later refactor this into a generic dispatch (e.g., a `PROFILE_FETCHERS: dict[str, Callable]` registry). The function signature should already be designed to slot into that pattern.
- **Backward-compat:** any LinkedIn account that connected before Phase 103 has `platform_user_id IS NULL`. Two options: (a) one-shot backfill migration that loops over `connected_accounts WHERE platform='linkedin' AND platform_user_id IS NULL`, calls `/v2/userinfo` with the stored token, and updates the row; (b) lazy backfill on first publish — if `platform_user_id IS NULL` at publish time, fetch from `/v2/userinfo`, persist, then proceed with the post. Recommendation: **Option (b) — lazy backfill** (zero migration risk, correct even if stored tokens are expired since the next publish forces a refresh path anyway).

---

## Target State (per success criterion)

### Success criterion #1 (POST-01)
- After OAuth callback: row in `connected_accounts` for `platform='linkedin'` has `platform_user_id` set to the OIDC `sub` value (e.g. `782bbtaQ`). `platform_username` populated from `name` or `given_name` claim.
- At publish time: request body to `/rest/posts` includes `"author": "urn:li:person:782bbtaQ"`.
- Unit test (mock-based): patches `httpx.AsyncClient.post`/`get`; asserts `connector.handle_callback("linkedin", code, state, redirect)` results in DB row with `platform_user_id="782bbtaQ"` and that `publisher.post_text(user_id, "linkedin", "hi")` POSTs to `/rest/posts` with `author=urn:li:person:782bbtaQ`.

### Success criterion #2 (POST-02)
- A LinkedIn text post via the agent appears on the user's feed within 30 seconds.
- Request goes to `https://api.linkedin.com/rest/posts` with both `LinkedIn-Version: 202401` and `X-Restli-Protocol-Version: 2.0.0` headers.
- Single-image post: image is uploaded to LinkedIn's DMS first via `/rest/images?action=initializeUpload`, returned image URN is referenced in `content.media.id`.
- Video post: video is multi-part-uploaded via `/rest/videos?action=initializeUpload` → chunked `PUT` → `/rest/videos?action=finalizeUpload`, returned video URN is referenced in `content.media.id`.
- Integration test (mocked network) asserts request shape for all three post types.

### Success criterion #3 (POST-03)
- Inbound POST to `/webhooks/linkedin` with valid `X-LI-Signature: hmacsha256=<correct hex>` (computed with `LINKEDIN_CLIENT_SECRET`) is accepted (200) and event is stored.
- Inbound POST with invalid signature is rejected (audit says 401; current code says 403; **recommend 401 to match audit spec literally**).
- Unit test asserts both branches.

---

## API Reference (verified via Microsoft Learn `li-lms-2026-04`)

### A. OIDC `/v2/userinfo` (POST-01)

**Endpoint:** `GET https://api.linkedin.com/v2/userinfo`
**Auth:** `Authorization: Bearer <access_token>`
**Required scopes:** `openid`, `profile` (already configured in `connector.py:28`)

**Response shape (verified, from Microsoft Learn doc):**
```json
{
  "sub": "782bbtaQ",
  "name": "John Doe",
  "given_name": "John",
  "family_name": "Doe",
  "picture": "https://media.licdn-ei.com/dms/image/...",
  "locale": "en-US",
  "email": "doe@email.com",
  "email_verified": true
}
```

**Mapping to `connected_accounts`:**
- `platform_user_id = response["sub"]` (store the bare sub like `782bbtaQ`, not the full URN)
- `platform_username = response.get("name") or response.get("given_name")` (UI label; `email` is also acceptable but consider it PII)
- Email/picture/locale can optionally be persisted in the existing `metadata` JSONB column for richer profile cards later

**URN reconstruction at publish time:**
```python
author_urn = f"urn:li:person:{account['platform_user_id']}"
```

**Source:** [Sign In with LinkedIn using OpenID Connect](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2) (HIGH).

### B. `/rest/posts` — Text-only post (POST-02)

**Endpoint:** `POST https://api.linkedin.com/rest/posts`
**Required headers:**
- `Authorization: Bearer <access_token>`
- `LinkedIn-Version: 202401` (audit-mandated; any value `>= 202401` works; `202604` is current)
- `X-Restli-Protocol-Version: 2.0.0`
- `Content-Type: application/json`

**Required scope:** `w_member_social` (already configured in `connector.py:28`)

**Request body (verified):**
```json
{
  "author": "urn:li:person:782bbtaQ",
  "commentary": "Sample text Post",
  "visibility": "PUBLIC",
  "distribution": {
    "feedDistribution": "MAIN_FEED",
    "targetEntities": [],
    "thirdPartyDistributionChannels": []
  },
  "lifecycleState": "PUBLISHED",
  "isReshareDisabledByAuthor": false
}
```

**Response:** `201 Created`. The created post's URN is in the `x-restli-id` response header (e.g. `urn:li:share:6844785523593134080`). Body may be empty.

**Source:** [Posts API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api) (HIGH).

### C. `/rest/images` initialize upload + image post (POST-02)

**Step 1 — Initialize Upload:**
```http
POST https://api.linkedin.com/rest/images?action=initializeUpload
Linkedin-Version: 202401
X-Restli-Protocol-Version: 2.0.0
Authorization: Bearer <token>
Content-Type: application/json

{
  "initializeUploadRequest": {
    "owner": "urn:li:person:782bbtaQ"
  }
}
```

**Response (200):**
```json
{
  "value": {
    "uploadUrlExpiresAt": 1650567510704,
    "uploadUrl": "https://www.linkedin.com/dms-uploads/...",
    "image": "urn:li:image:C4E10AQFoyyAjHPMQuQ"
  }
}
```

**Step 2 — Upload binary:** `PUT` raw image bytes to `value.uploadUrl` with `Content-Type: application/octet-stream` (no LinkedIn auth header on this URL — it's pre-signed). Returns 200.

**Step 3 — Create post:**
```json
{
  "author": "urn:li:person:782bbtaQ",
  "commentary": "Caption text",
  "visibility": "PUBLIC",
  "distribution": {
    "feedDistribution": "MAIN_FEED",
    "targetEntities": [],
    "thirdPartyDistributionChannels": []
  },
  "content": {
    "media": {
      "altText": "Image alt text for accessibility",
      "id": "urn:li:image:C4E10AQFoyyAjHPMQuQ"
    }
  },
  "lifecycleState": "PUBLISHED",
  "isReshareDisabledByAuthor": false
}
```

**Source:** [Image API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/images-api) (HIGH).

### D. `/rest/videos` initialize → upload → finalize → post (POST-02)

**Step 1 — Initialize:**
```http
POST https://api.linkedin.com/rest/videos?action=initializeUpload
{
  "initializeUploadRequest": {
    "owner": "urn:li:person:782bbtaQ",
    "fileSizeBytes": 1055736,
    "uploadCaptions": false,
    "uploadThumbnail": false
  }
}
```

**Response (200):**
```json
{
  "value": {
    "uploadUrlsExpireAt": 1633234498985,
    "video": "urn:li:video:C5505AQH-oV1qvnFtKA",
    "uploadInstructions": [
      {
        "uploadUrl": "https://www.linkedin.com/dms-uploads/...",
        "firstByte": 0,
        "lastByte": 4194303
      }
    ],
    "uploadToken": "<opaque>"
  }
}
```

**Step 2 — Upload each chunk:**
```bash
PUT <uploadUrl>
Content-Type: application/octet-stream

<bytes [firstByte..lastByte] of file>
```

For files > 4MiB, multiple instructions are returned. **MUST** capture the `etag` response header from each chunk's upload — these become `uploadedPartIds[]` for finalize.

**Step 3 — Finalize:**
```http
POST https://api.linkedin.com/rest/videos?action=finalizeUpload
{
  "finalizeUploadRequest": {
    "video": "urn:li:video:C5505AQH-oV1qvnFtKA",
    "uploadToken": "<from init>",
    "uploadedPartIds": ["<etag1>", "<etag2>", ...]
  }
}
```

Returns `200 OK`. The video transitions through `PROCESSING` → `AVAILABLE`.

**Step 4 — Create post:**
```json
{
  "author": "urn:li:person:782bbtaQ",
  "commentary": "Caption",
  "visibility": "PUBLIC",
  "distribution": { "feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": [] },
  "content": {
    "media": {
      "title": "Video title",
      "id": "urn:li:video:C5505AQH-oV1qvnFtKA"
    }
  },
  "lifecycleState": "PUBLISHED",
  "isReshareDisabledByAuthor": false
}
```

**Note:** The video must reach `AVAILABLE` status (or at minimum `PROCESSING` per the doc) before the post is created. The doc doesn't strictly require waiting; for simplicity, **don't wait** — `lifecycleState=PROCESSING` is acceptable for posts referencing media that is still processing, and LinkedIn will publish the post when the video is ready. This matches how the Twitter chunked-upload polling-vs-fire-and-forget tradeoff is being handled in Phase 104. Recommendation: **don't poll**, do an immediate post-create, return the post URN to the caller; if anything fails the LinkedIn UI shows the user the video error.

**Source:** [Videos API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/videos-api) (HIGH).

### E. Webhook signature validation (POST-03)

**Quote (verbatim from Microsoft Learn 2025-08-27):**
> "The POST request sent by LinkedIn will include a header called `X-LI-Signature`. The value of this header is the HMACSHA256 hash of the JSON-encoded string representation of the POST body prefixed by `hmacsha256=` and it is computed using your app's clientSecret."

**Verification algorithm:**
```python
def verify_linkedin_signature(body: bytes, header_value: str, client_secret: str) -> bool:
    if not header_value:
        return False
    # Strip prefix
    if not header_value.startswith("hmacsha256="):
        return False
    received = header_value[len("hmacsha256="):]
    expected = hmac.new(client_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received)
```

**GET challenge verification (already correct in `webhooks.py:46-86`):**
```python
challenge_response = hmac.new(
    LINKEDIN_CLIENT_SECRET.encode(),
    challengeCode.encode(),
    hashlib.sha256,
).hexdigest()
```
Return as JSON `{"challengeCode": <echo>, "challengeResponse": <hex>}` within 3 seconds.

**Re-validation:** LinkedIn re-validates every 2 hours; 3 consecutive failures put the webhook into "Blocked" state. Make sure the GET handler stays correct.

**Source:** [LinkedIn Webhook Validation](https://learn.microsoft.com/en-us/linkedin/shared/api-guide/webhook-validation) (HIGH).

---

## Implementation Approach

### Plan 103-01 — URN capture + Posts API migration

**File: `app/social/connector.py`**

Add a private helper before `handle_callback`:
```python
async def _fetch_linkedin_identity(self, http: httpx.AsyncClient, access_token: str) -> tuple[str | None, str | None]:
    """Fetch (sub, display_name) from LinkedIn /v2/userinfo. Returns (None, None) on failure."""
    try:
        resp = await http.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
        if resp.status_code != 200:
            logger.warning("LinkedIn /v2/userinfo failed: %s %s", resp.status_code, resp.text[:200])
            return None, None
        data = resp.json()
        return data.get("sub"), data.get("name") or data.get("given_name")
    except Exception:
        logger.exception("LinkedIn /v2/userinfo fetch raised")
        return None, None
```

In `handle_callback`, after the token exchange and before the upsert, dispatch by platform:
```python
platform_user_id, platform_username = None, None
if platform == "linkedin":
    platform_user_id, platform_username = await self._fetch_linkedin_identity(http, tokens["access_token"])
# (Phase 101 will add other providers here via PROFILE_FETCHERS dispatch.)

connection_data = {
    ...,
    "platform_user_id": platform_user_id,
    "platform_username": platform_username,
}
```

The `httpx.AsyncClient` is already opened at line 206; reuse it (`async with` block extends).

**File: `app/social/publisher.py`**

Replace lines 135-171 (the `elif platform == "linkedin":` branch) with a dispatch to a new helper `_post_linkedin(http, headers, user_id, content, media_urls, media_type)`:

```python
async def _post_linkedin(
    self,
    http: httpx.AsyncClient,
    token: str,
    user_id: str,
    content: str,
    media_urls: list[str] | None,
    media_type: str,
) -> httpx.Response:
    # Resolve member URN (lazy backfill if NULL — see backward-compat strategy)
    account_row = self._get_linkedin_account(user_id)
    sub = account_row.get("platform_user_id")
    if not sub:
        sub, _name = await self.connector._fetch_linkedin_identity(http, token)
        if not sub:
            raise PublisherError("LinkedIn account missing platform_user_id; reconnect required")
        # Persist for next time
        self.connector.client.table("connected_accounts").update({"platform_user_id": sub}).eq(
            "user_id", user_id
        ).eq("platform", "linkedin").execute()
    author_urn = f"urn:li:person:{sub}"

    headers = {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": "202401",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }

    body: dict[str, Any] = {
        "author": author_urn,
        "commentary": content,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    if media_urls and media_type == "image":
        image_urn = await self._upload_linkedin_image(http, headers, author_urn, media_urls[0])
        body["content"] = {"media": {"id": image_urn, "altText": content[:120]}}
    elif media_urls and media_type == "video":
        video_urn = await self._upload_linkedin_video(http, headers, author_urn, media_urls[0])
        body["content"] = {"media": {"id": video_urn, "title": content[:100]}}

    return await http.post(
        "https://api.linkedin.com/rest/posts",
        headers=headers,
        json=body,
    )
```

`_upload_linkedin_image` and `_upload_linkedin_video` do the multi-step flows in API Reference C and D. Both do their own `httpx` calls inside the same async client.

**Backward-compat:** the lazy-backfill is the recommended path. If the user's OAuth token has been refreshed, the existing `get_access_token` already returns a valid token, so calling `/v2/userinfo` succeeds.

### Plan 103-02 — Webhook signature realignment

**File: `app/social/linkedin_webhook.py`**

Change `verify_signature` to use `LINKEDIN_CLIENT_SECRET` and to handle the `hmacsha256=` prefix:
```python
LINKEDIN_CLIENT_SECRET_ENV = "LINKEDIN_CLIENT_SECRET"
_LINKEDIN_SIG_PREFIX = "hmacsha256="

def _get_client_secret() -> str | None:
    return os.environ.get(LINKEDIN_CLIENT_SECRET_ENV)

def verify_signature(payload: bytes, signature_header: str) -> bool:
    """Verify LinkedIn webhook X-LI-Signature header (HMAC-SHA256, hmacsha256= prefix)."""
    secret = _get_client_secret()
    if not secret:
        logger.warning("LINKEDIN_CLIENT_SECRET not configured — rejecting webhook")
        return False
    if not signature_header or not signature_header.startswith(_LINKEDIN_SIG_PREFIX):
        return False
    received = signature_header[len(_LINKEDIN_SIG_PREFIX):]
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received)
```

**File: `app/routers/webhooks.py:104`**

Change header name and status code:
```python
signature = request.headers.get("X-LI-Signature", "")
if not verify_signature(body, signature):
    logger.warning("LinkedIn webhook signature verification failed")
    raise HTTPException(status_code=401, detail="Invalid signature")  # 401 per audit success criterion
```

**Deprecation of `LINKEDIN_WEBHOOK_SECRET`:**
- Update `.env.example:87` comment: `# LINKEDIN_WEBHOOK_SECRET=...  # DEPRECATED — LinkedIn signs with LINKEDIN_CLIENT_SECRET, this var is unused`
- Update `cloud-run-service.yaml:73-74`, `deployment/terraform/vars/env.tfvars:48`, `deployment/terraform/dev/vars/env.tfvars:28` to remove the env var (or leave as a no-op placeholder; the planner can decide).
- Cloudflare worker at `deployment/cloudflare/public-api/src/index.ts:14655` may have its own signature flow; out of scope unless it talks to the same FastAPI handler.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HMAC-SHA256 verification | Custom string slicing + manual digest compare | `hmac.compare_digest(hmac.new(secret, body, hashlib.sha256).hexdigest(), received)` | Stdlib `hmac.compare_digest` is timing-safe; manual `==` is vulnerable to timing attacks |
| OAuth token storage | Plain text columns | Phase 101 will add Fernet via `encrypt_secret`/`decrypt_secret` | Already covered by AUTH-02; Phase 103 should write through whatever wrapper Phase 101 ships, or stay on the current plain-text path if 101 hasn't shipped yet (coordinate via plan ordering) |
| LinkedIn ID resolution | Calling deprecated `/v2/me` | `/v2/userinfo` (OIDC) | `/v2/me` requires the deprecated `r_liteprofile` scope; the existing `openid+profile` scopes already grant `/v2/userinfo`. **Plus:** OIDC `sub` IS the canonical member ID per pairwise per-app — this matches what Posts API expects (See Open Question 1) |
| Image/video binary upload | POST `multipart/form-data` to `/rest/posts` | Two-step: `initializeUpload` returns pre-signed URL → `PUT` raw bytes | LinkedIn's DMS handles the binary separately; the post just references the URN |
| Polling for video processing | `while not done: poll()` loop | Don't poll; LinkedIn publishes when ready | The doc allows posting against a `urn:li:video:...` in `PROCESSING` state |
| Webhook secret rotation | Custom secret store | Stick with `LINKEDIN_CLIENT_SECRET` (which is the OAuth secret used everywhere) | LinkedIn ties signing to the app's clientSecret; rotating it forces re-OAuth too, which is inevitable if compromised |

---

## Common Pitfalls

### Pitfall 1: Pairwise sub ≠ canonical member ID
**What goes wrong:** OIDC pairwise subjects can differ from the member's "canonical" LinkedIn person ID. Some community reports (n8n forum, Bubble forum) show the URN-from-`sub` failing on `/v2/ugcPosts` with `INVALID_URN_ID`.
**Why it happens:** Pairwise means LinkedIn issues a different `sub` per Relying Party app for privacy. The Posts API was designed before OIDC and historically used the canonical member ID.
**How to avoid:** Empirically test that `urn:li:person:{sub}` is accepted by `/rest/posts` with `w_member_social`. Multiple Microsoft Learn examples (Posts API "Find Posts by Authors" doc) DO use `urn:li:person:5abc_dEfgH` with `q=author` finder, suggesting LinkedIn maps the pairwise sub correctly server-side. **Validation strategy:** Ship with `sub` first; if LinkedIn rejects with `INVALID_URN_ID`, fall back to deprecated `GET /v2/me` (which returns the canonical `id`). Build the fallback as a try/except in `_fetch_linkedin_identity`.
**Warning signs:** HTTP 400 from `/rest/posts` with `code: INVALID_URN_ID` on the `author` field.

### Pitfall 2: Forgetting `LinkedIn-Version` header
**What goes wrong:** `/rest/posts` accepts requests without the version header but treats them as legacy and may return inconsistent shapes.
**How to avoid:** Always include `LinkedIn-Version: 202401` (or higher) on every `/rest/*` call — `/rest/posts`, `/rest/images`, `/rest/videos`, `/v2/userinfo` does NOT need it (it's a v2 endpoint), but harmless to send.
**Warning signs:** Responses with deprecation warnings in body or unexpected error shapes.

### Pitfall 3: Image upload pre-signed URL needs no auth
**What goes wrong:** Sending `Authorization: Bearer ...` to LinkedIn's DMS upload URL fails with 403 because the URL already encodes auth in query params.
**How to avoid:** Use a fresh `httpx.AsyncClient` instance for the binary upload OR explicitly pass `headers={"Content-Type": "application/octet-stream"}` only.
**Warning signs:** 403 from `linkedin.com/dms-uploads/...` with no JSON body.

### Pitfall 4: ETag header capture for video parts
**What goes wrong:** Multi-part video upload requires submitting `uploadedPartIds[]` to `finalizeUpload`. These IDs come from the `etag` (or `ETag`) response header on each chunk's `PUT`. Forget to capture or get the casing wrong → finalize returns 400.
**How to avoid:** `etag = resp.headers.get("etag") or resp.headers.get("ETag")` (httpx normalizes headers but defensive is safer). Append in chunk order.
**Warning signs:** `finalizeUpload` returns 400 with `INVALID_PART_IDS` or similar.

### Pitfall 5: Webhook signature header capitalization
**What goes wrong:** HTTP headers are case-insensitive per RFC, but FastAPI's `request.headers.get("X-LI-Signature")` is case-insensitive. The trap is checking for the WRONG header name (`X-LinkedIn-Signature` — current code) returns empty string, signature check fails 100%, all real LinkedIn events get 403.
**How to avoid:** Hardcode `X-LI-Signature` (with the dash, not underscore; `LI` not `LinkedIn`). Verified against the official spec.
**Warning signs:** Production logs show 100% rejection rate of incoming LinkedIn webhooks.

### Pitfall 6: Raw body must be captured BEFORE JSON parse
**What goes wrong:** FastAPI consumes the request body once. If `request.json()` is called before `request.body()`, the bytes are gone and HMAC verification can't recompute the signature.
**How to avoid:** Always call `body = await request.body()` first, then `json.loads(body)` for parsing. Existing `webhooks.py:101` already does this correctly.
**Warning signs:** Body parse succeeds but signature verify fails on a request you know is genuine.

### Pitfall 7: PKCE in async path (Phase 101 dependency)
**What goes wrong:** Phase 101 will move PKCE verifiers to Redis. If Phase 103 ships before Phase 101, the in-memory `_pkce_verifiers` dict is still in use, which means OAuth callbacks fail randomly when Cloud Run scales horizontally.
**How to avoid:** Phase 103 changes do NOT touch the PKCE storage path; they only add `_fetch_linkedin_identity` after the existing token exchange. Compatible with both pre-101 and post-101 PKCE storage.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `/v2/ugcPosts` | `/rest/posts` (versioned) | Marketing 202204 (April 2022); 202504 sunset announced 2025 | All new integrations must use `/rest/posts` |
| Nested `specificContent.com.linkedin.ugc.ShareContent.shareCommentary.text` | Top-level `commentary` | Posts API GA | Drastically simpler payload |
| Nested `visibility.com.linkedin.ugc.MemberNetworkVisibility: "PUBLIC"` | Top-level `visibility: "PUBLIC"` (string) | Posts API GA | Schema cleanup |
| `/v2/me` for member ID (`r_liteprofile` scope) | `/v2/userinfo` (OIDC, `openid+profile` scopes) | Sign In with LinkedIn V2 (announced 2023) | New OIDC-based identity flow |
| Image upload via `/v2/assets?action=registerUpload` (Assets API) | `/rest/images?action=initializeUpload` | Per-API split | Purpose-built endpoints |
| Video upload via `/v2/assets?action=registerUpload` + manual chunking | `/rest/videos?action=initializeUpload` returns multi-part instructions | Per-API split | Server-side chunk planning |

**Deprecated/outdated:**
- `/v2/ugcPosts` — replaced by `/rest/posts`; keep working but no new features
- `/v2/me` — replaced by `/v2/userinfo` for new integrations; still works with `r_liteprofile`
- `/v2/assets` — replaced by `/rest/images` and `/rest/videos`
- `r_liteprofile` scope — replaced by `profile` (OIDC)
- LinkedIn-Version pre-202401 — Marketing 202504 sunset 2025-Q3; we're targeting 202401 minimum per audit

---

## Open Questions

1. **Is `urn:li:person:{sub}` accepted by `/rest/posts` for member-authored posts?**
   - **What we know:** OIDC `sub` is pairwise per RP app. Microsoft Learn examples for `q=author` finder use `urn:li:person:5abc_dEfgH` — visually similar to a pairwise subject, but not explicitly documented as identical.
   - **What's unclear:** Whether LinkedIn's `/rest/posts` server-side resolves `urn:li:person:{pairwise_sub}` correctly to the authenticated member or whether it requires the canonical member ID from `/v2/me`.
   - **Recommendation:** Implement the primary path (use `sub`); add a fallback to `/v2/me` (gated by detection of `INVALID_URN_ID` on first publish) so the system self-heals. Document both in `_fetch_linkedin_identity`. The planner should make this a defined verification step on the first integration test against the real LinkedIn API.

2. **Should the GET challenge handler also gate behind feature flag for the wrong-secret scenario?**
   - The existing `webhook_verification` at `webhooks.py:46-86` correctly uses `LINKEDIN_CLIENT_SECRET`, so it's already right. No change needed.

3. **What about non-public visibility (CONNECTIONS, LOGGED_IN)?**
   - Out of scope per success criterion #2 (text/image/video, all PUBLIC). Document in code comment that we hardcode `PUBLIC` and accept enhancement requests later.

4. **What happens to existing `LINKEDIN_WEBHOOK_SECRET` env var in deployed environments?**
   - It's set in `cloud-run-service.yaml`, three Terraform vars files, and Cloudflare worker. Deprecating it requires an update to all four. Plan 103-02 should include a note about which infrastructure files to update.

5. **Status code: 401 vs 403?**
   - Audit success criterion says 401. Existing code says 403. Both are RFC-compliant. **Recommend the planner adopt 401** to match the audit literally; it doesn't affect functionality.

6. **Should media upload retries handle 403 on the pre-signed `uploadUrl` (token expired)?**
   - The doc says upload URLs typically expire after 30 days but never specifies what happens if they're called with `Authorization` header. Decision: catch 401/403 from the binary upload step, log it, surface a clear error to the caller; do not retry.

---

## Plan Decomposition Hint

**Recommended:** 2 plans.

### Plan 103-01: URN capture + Posts API migration (POST-01 + POST-02)
**Scope:** `app/social/connector.py`, `app/social/publisher.py`, plus new unit tests. Single conceptual change ("LinkedIn posting works end-to-end with real URN and current API"). No webhook touches.
**Estimated waves:** 3
- Wave 0 (test infra): Add `tests/unit/test_social_connector.py` and `tests/unit/test_social_publisher.py` skeleton with `httpx` mocking pattern (use `respx` if not already a dep, or `unittest.mock.patch.object(httpx.AsyncClient, "post")`).
- Wave 1 (URN capture): `_fetch_linkedin_identity` helper; integrate into `handle_callback`; lazy-backfill in publisher; tests for callback shape and backfill path.
- Wave 2 (Posts API): rewrite LinkedIn branch of `post_with_media`; `_upload_linkedin_image`; `_upload_linkedin_video` (3-step with chunk loop); tests for text/image/video request shapes.
**Dependencies:** None hard-blocking; coordinate with Phase 101 if AUTH-02 ships first (Fernet encryption may wrap reads).

### Plan 103-02: Webhook signature realignment (POST-03)
**Scope:** `app/social/linkedin_webhook.py` (`verify_signature` rewrite), `app/routers/webhooks.py` (header name + status code), `.env.example` deprecation comment, deployment infra cleanup notes. Plus tests.
**Estimated waves:** 1-2
- Wave 0/1: Rewrite `verify_signature` for `LINKEDIN_CLIENT_SECRET` + `hmacsha256=` prefix; change header to `X-LI-Signature` and status to 401; tests for valid + invalid signatures (similar pattern to existing `tests/unit/test_webhook_auth.py`).
- Wave 2 (optional): Update Cloud Run YAML, Terraform vars, Cloudflare worker comment; deprecation notice in `.env.example`. Can be deferred to ops follow-up.
**Dependencies:** None.

**Why two plans, not one:** They touch disjoint files (publisher/connector vs webhook handler), have different risk profiles (publisher = active feature blocking; webhook = security defense-in-depth that's silently failing today), and can ship in either order. Two plans also let the planner schedule webhook fix urgently if security review demands it, while the bigger publisher rewrite gets careful verification.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x with pytest-asyncio (`pyproject.toml:61`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (line 127) |
| Quick run command | `uv run pytest tests/unit/test_social_*.py -x` |
| Full suite command | `make test` (runs unit + integration) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| POST-01 | `handle_callback` with mocked `/v2/userinfo` returns row with `platform_user_id="782bbtaQ"` | unit | `uv run pytest tests/unit/test_social_connector.py::test_linkedin_callback_captures_urn -x` | Wave 0 |
| POST-01 | `post_text` for LinkedIn includes `author=urn:li:person:{platform_user_id}` in request | unit | `uv run pytest tests/unit/test_social_publisher.py::test_linkedin_post_uses_persisted_urn -x` | Wave 0 |
| POST-01 | Lazy backfill: account with NULL `platform_user_id` triggers `/v2/userinfo` fetch and persists | unit | `uv run pytest tests/unit/test_social_publisher.py::test_linkedin_lazy_urn_backfill -x` | Wave 0 |
| POST-02 | LinkedIn text post POSTs to `/rest/posts` with `LinkedIn-Version: 202401` and correct shape | unit | `uv run pytest tests/unit/test_social_publisher.py::test_linkedin_text_post_shape -x` | Wave 0 |
| POST-02 | LinkedIn single-image post: 3-step (init upload → PUT bytes → posts) | unit | `uv run pytest tests/unit/test_social_publisher.py::test_linkedin_image_post_shape -x` | Wave 0 |
| POST-02 | LinkedIn video post: 4-step (init → PUT chunks → finalize → posts) | unit | `uv run pytest tests/unit/test_social_publisher.py::test_linkedin_video_post_shape -x` | Wave 0 |
| POST-03 | Valid `X-LI-Signature: hmacsha256=<correct>` accepted (200) | unit | `uv run pytest tests/unit/test_linkedin_webhook.py::test_valid_signature_accepted -x` | Wave 0 |
| POST-03 | Invalid signature rejected (401) | unit | `uv run pytest tests/unit/test_linkedin_webhook.py::test_invalid_signature_rejected -x` | Wave 0 |
| POST-03 | Missing header rejected (401) | unit | `uv run pytest tests/unit/test_linkedin_webhook.py::test_missing_signature_rejected -x` | Wave 0 |
| POST-03 | `LINKEDIN_CLIENT_SECRET` unset → 500/403 fail-closed | unit | `uv run pytest tests/unit/test_linkedin_webhook.py::test_missing_client_secret_rejects -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/test_social_*.py tests/unit/test_linkedin_webhook.py -x` (~5s for ~10 tests)
- **Per wave merge:** `uv run pytest tests/unit/test_social_*.py tests/unit/test_linkedin_webhook.py tests/unit/test_webhook_auth.py -x` (existing webhook auth tests as regression)
- **Phase gate:** `make test` (full unit + integration)

### Wave 0 Gaps
- [ ] `tests/unit/test_social_connector.py` — covers POST-01 (callback URN capture)
- [ ] `tests/unit/test_social_publisher.py` — covers POST-01 (publisher uses URN) + POST-02 (Posts API request shape, image upload, video upload)
- [ ] `tests/unit/test_linkedin_webhook.py` — covers POST-03 (signature verify, fail-closed when secret missing)
- [ ] No new framework install needed; `pytest-asyncio` and `httpx` already in `pyproject.toml`. Consider adding `respx` as dev dep for cleaner httpx mocking; otherwise `unittest.mock.patch.object(httpx.AsyncClient, ...)` is sufficient and used elsewhere.

---

## Sources

### Primary (HIGH confidence)
- [Posts API — Microsoft Learn (li-lms-2026-04)](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api) — text/image/video request bodies, headers, 201 response with `x-restli-id`, error codes
- [Image API — Microsoft Learn (li-lms-2026-04)](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/images-api) — initializeUpload action, response shape, image post body
- [Videos API — Microsoft Learn (li-lms-2026-04)](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/videos-api) — initializeUpload, multi-part upload, finalizeUpload, ETag capture
- [Sign In with LinkedIn using OpenID Connect — Microsoft Learn](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2) — `/v2/userinfo` shape, OIDC discovery, `sub` claim format, scopes
- [LinkedIn Webhook Validation — Microsoft Learn (2025-08-27)](https://learn.microsoft.com/en-us/linkedin/shared/api-guide/webhook-validation) — exact `X-LI-Signature: hmacsha256=...` spec, GET challenge response, 2-hour re-validation
- Local repo source: `app/social/connector.py`, `app/social/publisher.py:135-171`, `app/social/linkedin_webhook.py`, `app/routers/webhooks.py:45-134`, `supabase/migrations/0010_connected_accounts.sql:1-45`

### Secondary (MEDIUM confidence)
- [Hookdeck SHA256 Webhook Signature Verification Guide](https://hookdeck.com/webhooks/guides/how-to-implement-sha256-webhook-signature-verification) — corroborates `X-LI-Signature` header name and `hmacsha256=` prefix
- [Hookdeck LinkedIn Webhooks Guide](https://hookdeck.com/webhooks/platforms/guide-to-linkedin-webhooks-features-and-best-practices) — secondary corroboration of webhook flow

### Tertiary (LOW confidence — flagged)
- [n8n community: LinkedIn UGC v2 & REST both failing](https://community.n8n.io/t/linkedin-can-t-post-to-personal-or-company-feed-ugc-v2-rest-both-failing-need-help-with-linkedin-version-person-urn/108765) — informs Open Question 1 (pairwise sub vs canonical ID); not authoritative
- [DEV.to / bitoff.org commentary on Posts API migration](https://dev.to/jnv/linkedins-new-posts-api-the-good-the-bad-and-the-ugly-5e53) — community sentiment; useful framing only

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every endpoint, header, body shape verified against Microsoft Learn at li-lms-2026-04
- Architecture: HIGH — concrete code shape provided; reuses existing `httpx.AsyncClient` pattern in `connector.py:206`
- Pitfalls: HIGH for items 2-7 (verified against spec); MEDIUM for item 1 (pairwise sub) — flagged as Open Question 1 with mitigation strategy

**Research date:** 2026-05-08
**Valid until:** 2026-06-07 (LinkedIn versions are stable for 12+ months; webhook spec hasn't changed since at least 2025-08; OIDC userinfo shape stable since 2023)
