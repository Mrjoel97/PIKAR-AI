---
phase: 103-linkedin-posting-fix
plan: 01
subsystem: app/social
tags: [linkedin, oauth, posts-api, urn, social-publishing]
requires:
  - phase 101-03 (platform_user_id captured at OAuth callback)
  - phase 101-02 (async get_access_token with per-key Lock)
provides:
  - SocialConnector._fetch_linkedin_identity (OIDC userinfo helper, used by both callback and lazy backfill)
  - SocialPublisher._post_linkedin (Posts API entrypoint replacing /v2/ugcPosts)
  - SocialPublisher._upload_linkedin_image (3-step initializeUpload flow)
  - SocialPublisher._upload_linkedin_video (4-step chunked-upload flow)
  - SocialPublisher._resolve_linkedin_author_urn (lazy backfill for pre-Phase-103 connections)
affects:
  - app/social/connector.py
  - app/social/publisher.py
  - tests/unit/test_social_connector_security.py (regression repair)
tech-stack:
  added: []
  patterns:
    - "Lazy backfill: when connected_accounts.platform_user_id is null, GET /v2/userinfo at publish time, persist sub, then proceed"
    - "Pre-signed URL upload: PUT to LinkedIn DMS uploadUrl WITHOUT Authorization header (LinkedIn pitfall #3)"
    - "Inclusive byte range: video chunks are body[firstByte:lastByte+1], not Python's exclusive slicing"
key-files:
  created:
    - tests/unit/test_social_connector_linkedin_identity.py
    - tests/unit/test_social_publisher_linkedin.py
  modified:
    - app/social/connector.py
    - app/social/publisher.py
    - tests/unit/test_social_connector_security.py
decisions:
  - "Reused Phase 101-03's _fetch_platform_profile dispatch by delegating its LinkedIn arm to the new _fetch_linkedin_identity helper, instead of duplicating the userinfo call. Single source of truth for OIDC display-name handling (name -> given_name fallback)."
  - "Repaired the test_social_connector_security.py _AsyncClient stub by adding a get() method that returns 500. This was a regression introduced by Phase 101-03 (the test was failing on main before this plan started) and the plan's done criterion explicitly required no regression in those 3 tests."
  - "LinkedIn carousel media_type is deferred (TODO comment in _post_linkedin). Out of scope for POST-02 per the plan."
metrics:
  duration: ~50 minutes
  completed: 2026-05-08
  task-count: 3
  test-count: 9 new (3 connector + 6 publisher); 3 pre-existing repaired
  files-modified: 5
---

# Phase 103 Plan 01: LinkedIn URN Capture + Posts API Migration Summary

LinkedIn member-authored posts now succeed end-to-end via the versioned `/rest/posts` API with member URNs derived from the OIDC `sub` claim.

## What Changed

### `app/social/connector.py` (lines 185-239)

**`_fetch_linkedin_identity(http, access_token) -> (sub, display_name)`** is a new async helper that GETs `https://api.linkedin.com/v2/userinfo` with the bearer token and returns the bare OIDC `sub` plus the OIDC display name. Display-name resolution prefers `name`, falls back to `given_name`, finally `None`. All failure modes (network error, non-200, malformed JSON) return `(None, None)` and log a WARNING — never raise.

`_fetch_platform_profile` (the AUTH-04 dispatch added in Phase 101-03) now delegates its LinkedIn arm to `_fetch_linkedin_identity` so the OAuth-callback path and the publisher's lazy-backfill path share one implementation. The other six platforms (twitter/facebook/instagram/tiktok/youtube/google_*) are unchanged.

### `app/social/publisher.py`

The 36-line legacy LinkedIn branch in `post_with_media` collapses to a single dispatch:

```python
elif platform == "linkedin":
    return await self._post_linkedin(http, token, user_id, content, media_urls, media_type)
```

Four new private methods carry the full flow:

| Method | Lines | Role |
| ---- | ---- | ---- |
| `_resolve_linkedin_author_urn` | 72-117 | Reads `platform_user_id` from `connected_accounts`; lazy-backfills via `_fetch_linkedin_identity` if null; persists the backfilled sub via `update`. Returns `urn:li:person:{sub}` or `None`. |
| `_upload_linkedin_image` | 119-178 | POST `/rest/images?action=initializeUpload`; GET media bytes from public URL; PUT to pre-signed `uploadUrl` (NO Authorization header per LinkedIn DMS contract); returns `urn:li:image:...`. |
| `_upload_linkedin_video` | 180-280 | GET media bytes; POST `/rest/videos?action=initializeUpload` with `fileSizeBytes`; PUT each `uploadInstruction` chunk capturing `etag`; POST `/rest/videos?action=finalizeUpload` with `uploadedPartIds`. Returns `urn:li:video:...`. |
| `_post_linkedin` | 282-369 | Resolves author URN; builds the flat Posts API body (`commentary`, `visibility: "PUBLIC"`, `distribution.feedDistribution: "MAIN_FEED"`); attaches `content.media.id` for image/video; POSTs `/rest/posts` with `LinkedIn-Version: 202401` + `X-Restli-Protocol-Version: 2.0.0`; reads the post URN from the `x-restli-id` response header. |

Carousel `media_type` for LinkedIn is documented as a TODO and falls through to text-only commentary (out of scope per POST-02).

### `tests/unit/test_social_connector_linkedin_identity.py` (new, 383 lines)

Three tests covering the OAuth-callback URN-capture path:
- `test_linkedin_callback_captures_urn` — happy path: `connected_accounts.platform_user_id == "782bbtaQ"`, `platform_username == "John Doe"`.
- `test_linkedin_callback_userinfo_failure_does_not_block_callback` — userinfo returns 500; callback still succeeds with both fields null; WARNING log captured.
- `test_non_linkedin_platform_does_not_call_userinfo` — Twitter callback never hits `/v2/userinfo` (correct dispatch).

### `tests/unit/test_social_publisher_linkedin.py` (new, 602 lines)

Six tests covering the publish path:
- `test_linkedin_text_post_request_shape` — exact body envelope, all four required headers, no `content` key for text-only.
- `test_linkedin_image_post_three_step_flow` — initializeUpload → GET media bytes → PUT (no auth) → /rest/posts with `content.media.id`. Asserts altText is non-empty and `<= 120` chars.
- `test_linkedin_video_post_four_step_flow` — chunked PUT body slicing is inclusive (`[firstByte:lastByte+1]`), etag capture (lowercase + uppercase fallback), finalize body shape, post body content.media.id.
- `test_linkedin_lazy_urn_backfill` — null `platform_user_id` triggers `/v2/userinfo` GET, persists `BACKFILLED_SUB`, post body uses `urn:li:person:BACKFILLED_SUB`.
- `test_linkedin_post_without_urn_after_backfill_failure_returns_error` — null URN AND userinfo 500 returns `{"error": "...reconnect..."}`; no `/rest/posts` call.
- `test_linkedin_post_uses_persisted_urn_no_backfill_call` — when URN already persisted, no `/v2/userinfo` GET happens.

### `tests/unit/test_social_connector_security.py` (regression repair)

The pre-existing `_AsyncClient` stub only had a `post` method. Phase 101-03 added a `/v2/userinfo` GET inside `handle_callback`, which made `test_callback_uses_persisted_pkce_and_stores_encrypted_tokens` fail with `AttributeError: '_AsyncClient' object has no attribute 'get'`. Added a `get()` method that records the call and returns a 500 response (best-effort no-op for profile capture). The test's original assertions are unchanged.

## Test Count Delta

| Suite | Before | After |
| ---- | ---- | ---- |
| `test_social_connector_linkedin_identity.py` | 0 | 3 PASSING |
| `test_social_publisher_linkedin.py` | 0 | 6 PASSING |
| `test_social_connector_security.py` | 2 PASSING + 1 FAILING (regression) | 3 PASSING (regression repaired) |
| **Total relevant** | **2 PASSING + 1 broken** | **12 PASSING** |

Verification command:

```
uv run pytest tests/unit/test_social_publisher_linkedin.py \
              tests/unit/test_social_connector_linkedin_identity.py \
              tests/unit/test_social_connector_security.py -v
# 12 passed in 8.25s
```

Grep verifications:

```
grep -rn "urn:li:person:PERSON_ID" app/         -> empty
grep -rn "/v2/ugcPosts" app/social/             -> empty
grep -rn "LinkedIn-Version" app/social/publisher.py
  -> 308:            "LinkedIn-Version": "202401",
grep -rn "_fetch_linkedin_identity" app/social/
  -> connector.py:185 (defined), connector.py:282 (used by dispatch),
     publisher.py:103 (used by lazy backfill)
```

## Open Question 1 (Pairwise vs Canonical Sub)

Did NOT surface during testing — all assertions are on mocked values. Flag for live UAT only:

> If real LinkedIn `/v2/userinfo` returns a per-app pairwise `sub` that LinkedIn's URN validator rejects with `INVALID_URN_ID` on `urn:li:person:{sub}`, we'll need a `/v2/me` fallback path. Mocked tests cannot detect this. Track via a follow-up phase if it manifests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Existing security test was failing on main before plan started**
- **Found during:** Pre-flight checks before Task 1.
- **Issue:** `tests/unit/test_social_connector_security.py::test_callback_uses_persisted_pkce_and_stores_encrypted_tokens` failed with `AttributeError: '_AsyncClient' object has no attribute 'get'`. Phase 101-03's `_fetch_platform_profile` added a `/v2/userinfo` GET inside `handle_callback`, but the test's `_AsyncClient` stub only had `post`.
- **Fix:** Added a `get()` method to the stub class that records the call and returns a 500 response. Profile capture becomes a best-effort no-op for that test, which is the intended behavior — the test's original assertions on token persistence are unaffected.
- **Files modified:** `tests/unit/test_social_connector_security.py`
- **Commit:** `533d547e` (combined with Task 2 since both fixes hit the same RED→GREEN transition)
- **Justification:** The plan's done criterion for Task 2 says "All 4 pre-existing security tests still pass (regression)" — fixing the broken stub was required to satisfy that gate.

### Plan Wording vs Reality

**2. Plan expected 9 failing tests after Task 1; only 6 actually failed.**
- The 3 connector identity tests passed immediately because Phase 101-03 had already implemented the LinkedIn URN-capture path inside `_fetch_platform_profile`. The plan was authored before 101-03 landed, and its critical_state_context flagged this. Tests still target the contract correctly — they validate the RIGHT behavior, just behavior that 101-03 had already shipped.
- No code change required; documenting for plan-fidelity audit.

**3. Architecture: kept `_fetch_platform_profile` in addition to `_fetch_linkedin_identity`, instead of inlining LinkedIn dispatch in `handle_callback`.**
- The plan's Task 2 action #3 says "extend the `async with httpx.AsyncClient()` block" and "if platform == 'linkedin': platform_user_id, platform_username = await self._fetch_linkedin_identity(...)". This was authored as if no per-platform dispatch existed.
- Phase 101-03 had already shipped the registry-style `_fetch_platform_profile` dispatch covering all 6 supported platforms. Re-introducing inline LinkedIn-only dispatch in `handle_callback` would have been a regression.
- **Adopted approach:** added `_fetch_linkedin_identity` as the LinkedIn-specific helper AND made `_fetch_platform_profile` delegate its LinkedIn arm to it. This satisfies the plan's literal "has `_fetch_linkedin_identity` method" requirement, preserves 101-03's architecture, AND gives the publisher a clean entry point for lazy backfill.

## Out-of-scope Items Surfaced (Deferred)

- LinkedIn carousel posting via `/rest/documents`. TODO in `_post_linkedin`. Track in a future plan if user demand surfaces.
- Phase 108 hygiene items still apply: TikTok username capture (needs `user.info.profile` scope), Threads/Pinterest/google_search_console/google_analytics profile capture.

## Self-Check: PASSED

- `app/social/connector.py:185` — `_fetch_linkedin_identity` defined: FOUND.
- `app/social/publisher.py:282` — `_post_linkedin` defined: FOUND.
- `app/social/publisher.py:308` — `LinkedIn-Version: 202401` header sent: FOUND.
- `tests/unit/test_social_connector_linkedin_identity.py` (383 lines): FOUND.
- `tests/unit/test_social_publisher_linkedin.py` (602 lines): FOUND.
- Commits `024af822`, `533d547e`, `e30fbd6d` exist on `feat/vault-fixes-and-agent-actions`: FOUND.
- All 12 tests pass on final run: VERIFIED.
- Grep verifications all match expected outcomes: VERIFIED.
