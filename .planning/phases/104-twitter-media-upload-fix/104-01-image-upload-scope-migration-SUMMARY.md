---
phase: 104-twitter-media-upload-fix
plan: 01
subsystem: social-publishing
tags: [twitter, x-api, oauth2, media-upload, scope-migration, post-04, post-06]
requires:
  - app.social.connector.SocialConnector (existing)
  - app.social.publisher.SocialPublisher (existing)
  - connected_accounts table (existing)
provides:
  - app.social.publisher._upload_image_twitter (new)
  - app.social.publisher._upload_video_twitter (stub for 104-02)
  - PLATFORM_CONFIGS["twitter"]["scopes"] now includes "media.write"
  - migration that flips active twitter rows -> reconnect_required
affects:
  - All Twitter (X) connected accounts: forced re-authorization on next deploy
tech_stack:
  added: []
  patterns:
    - Single-shot multipart POST to v2 /2/media/upload (replaces dead v1.1 chunked init)
    - 403-as-reconnect-gate (treats missing-scope as user-actionable, not 500)
    - Stub-pattern for split plans (NotImplementedError carrying plan reference)
key_files:
  created:
    - tests/unit/test_twitter_publisher.py
    - tests/smoke/__init__.py
    - tests/smoke/test_twitter_live.py
    - supabase/migrations/20260508130000_twitter_reconnect_required.sql
  modified:
    - app/social/connector.py (+5/-1 lines: scope list)
    - app/social/publisher.py (-21/+93 lines: replaced _upload_media_twitter, rewrote Twitter branch)
    - tests/unit/test_social_connector_security.py (+11 lines: test_twitter_scopes)
decisions:
  - Use api.x.com for /2/media/upload (per RESEARCH.md pitfall 2 -- api.twitter.com still routes for /2/tweets but /2/media/upload requires the X domain).
  - Size guard at 5MB before issuing the upload POST (saves a doomed network round-trip).
  - 403 from upload short-circuits with a "reconnect" message; the tweet POST is NOT attempted (better UX than ghost-tweeting an empty caption).
  - Video helper raises NotImplementedError carrying the explicit Plan 104-02 reference so the dispatch can ship now.
metrics:
  duration_minutes: 35
  completed_date: 2026-05-09
  tasks_completed: 2
  tests_added: 6
  files_changed: 7
---

# Phase 104 Plan 01: Twitter v2 Media Upload + media.write Scope Summary

Migrate the Twitter publisher off the sunset-2025-06-09 `upload.twitter.com` v1.1 chunked endpoint onto the GA `https://api.x.com/2/media/upload` v2 simple endpoint, add the missing `media.write` OAuth2 scope, and flip existing connections to `reconnect_required` so the frontend prompts re-authorization. Image path is fully working; video stub raises `NotImplementedError` for Plan 104-02 to fill in.

## What Shipped

### Production code

- **`app/social/connector.py:51`** -- appended `"media.write"` to `PLATFORM_CONFIGS["twitter"]["scopes"]`. The list is now reformatted as a 5-element vertical list (ruff format reflow). `get_access_token` already filters on `status == "active"` so `reconnect_required` rows correctly yield `None` -- no code change needed there.
- **`app/social/publisher.py:46-98`** -- new `_upload_image_twitter(self, http, headers, media_url) -> str | None`. Single GET to fetch bytes, 5MB guard, single multipart POST to `https://api.x.com/2/media/upload` with `media_category=tweet_image`, 403-as-reconnect logging, returns `media_id` from either `body["data"]["id"]` (v2) or legacy `body["media_id_string"]`.
- **`app/social/publisher.py:100-111`** -- new `_upload_video_twitter` stub that raises `NotImplementedError("Twitter video chunked upload is implemented in Plan 104-02")`.
- **`app/social/publisher.py` Twitter branch in `post_with_media` (lines ~466-498)** -- rewrote to dispatch by `media_type`: `"video"` calls the stub (caught and surfaced as "not yet available"), everything else (image/carousel/gif) calls `_upload_image_twitter`. On any media-upload failure, returns the standard reconnect-prompt error and DOES NOT attempt the tweet POST. Tweet POST adds explicit `Content-Type: application/json` (the multipart upload borrows the bare `headers` dict so the JSON content-type must be set on the second call).
- The dead `_upload_media_twitter` (the one with the fictional `source_url` form field and the `upload.twitter.com/1.1/media/upload.json` host) is gone.

### Migration

- **`supabase/migrations/20260508130000_twitter_reconnect_required.sql`** (17 lines, new). One `UPDATE connected_accounts SET status = 'reconnect_required' WHERE platform = 'twitter' AND status = 'active'` plus a column comment refresh. Idempotent. **NOT applied by this plan** -- the next deploy's Supabase migration cycle picks it up. The deployer should run `supabase db push --linked` (prod) or `supabase db reset --local` after pulling. No data loss; the `revoked` rows are untouched.

### Tests

- **`tests/unit/test_twitter_publisher.py`** (new, 217 lines, 5 tests across 4 classes):
  - `TestImageUpload::test_image_simple_upload` -- happy path, asserts exactly 2 `http.post` calls, `api.x.com/2/media/upload` first with `multipart files["media"]` + `data={"media_category": "tweet_image"}`, then `api.twitter.com/2/tweets` with `{"text": ..., "media": {"media_ids": ["MEDIA_ID_123"]}}`. Authorization header on both is `Bearer FAKE_TOKEN`.
  - `TestImageUpload::test_image_simple_upload_too_large_returns_error` -- 5MB+1 byte image rejected before upload; logs `>5MB` warning; tweet POST never fires.
  - `TestAuthErrorMessage::test_403_returns_reconnect_message` -- 403 from upload yields error containing `"reconnect"` (case-insensitive), logs both `"403"` and `"media.write"`, never attempts the tweet POST.
  - `TestNoFictionalSourceUrl::test_no_fictional_source_url_in_twitter_branch` -- grep test slicing the file between the `# ----- TWITTER / X -----` and `# ----- LINKEDIN -----` comment markers; asserts `source_url` and `upload.twitter.com` are absent and `_upload_image_twitter` + `api.x.com/2/media/upload` are present.
  - `TestVideoStubRaises::test_video_path_returns_not_yet_available_error` -- video media_type returns error containing `"not yet available"`, never attempts tweet POST.
- **`tests/unit/test_social_connector_security.py`** (extended, +11 lines) -- new module-level `test_twitter_scopes` asserts `"media.write" in PLATFORM_CONFIGS["twitter"]["scopes"]` and that the existing four scopes are still present.
- **`tests/smoke/__init__.py`** + **`tests/smoke/test_twitter_live.py`** (new). Gated by `RUN_LIVE=1`; one live smoke `test_image_post` posts a real 4MB JPEG to a sandbox X account using `TWITTER_TEST_USER_ID` + `TWITTER_TEST_IMAGE_URL`. Skipped by default to keep CI hermetic.

## Test Count Delta

| File                                            | Before | After | Delta |
| ----------------------------------------------- | ------ | ----- | ----- |
| `tests/unit/test_twitter_publisher.py`          | 0      | 5     | +5    |
| `tests/unit/test_social_connector_security.py`  | 3      | 4     | +1    |
| `tests/smoke/test_twitter_live.py`              | 0      | 1*    | +1    |

*\* Skipped without `RUN_LIVE=1`.*

Final state on `feat/vault-fixes-and-agent-actions`:
```
tests/unit/test_social_connector_security.py ....           [ 23%]
tests/unit/test_twitter_publisher.py .....                  [ 52%]
tests/unit/test_linkedin_webhook_signature.py ........      [100%]
17 passed in 7.03s
```

## Verification

- `uv run pytest tests/unit/test_twitter_publisher.py tests/unit/test_social_connector_security.py` -> **9/9 passed**.
- `uv run pytest tests/smoke/` -> **1 skipped** (RUN_LIVE not set, as expected).
- `uv run ruff check app/social/ tests/unit/test_twitter_publisher.py` -> **All checks passed**.
- `uv run ruff format app/social/` -> reflowed `_upload_image_twitter` MIME line; behavior unchanged.
- `ty check` not exercised: this sandbox's uv shim only allows `uv run <cmd>` and `ty` is not pre-installed; `make lint` at CI will catch any genuine type issue.
- Broader social suite (`test_social_connector_security.py`, `test_twitter_publisher.py`, `test_linkedin_webhook_signature.py`) -> **17/17 passed**, no regressions.

## Frontend impact

**No frontend change needed.** The configuration page (`frontend/src/app/dashboard/configuration/page.tsx`) already renders connections via a `connected: boolean` flag derived from `status == "active"`. Rows flipped to `reconnect_required` show as not-connected and surface the existing "Click to connect" CTA. Re-authorization through that CTA goes through `get_authorization_url` which now requests `media.write` -- so a single user click closes the loop.

## Deviations from Plan

### Rule 3 - Blocking issue: shared-working-tree git race with concurrent agents

**Found during:** Both Task 1 (RED) and Task 2 (GREEN) commit steps.

**Issue:** This plan was scheduled in parallel with Plan 102-02 (Google Workspace token refresh) and Plan 103-02 (LinkedIn webhook signature). All three agents share the same on-disk working tree at `C:/Users/expert/documents/pka/pikar-ai` -- there is no worktree isolation. When agent A runs `git add file_a.py` and agent B runs `git add file_b.py && git commit -m "..."`, agent B's commit picks up both files because the index is shared. This happened twice:

1. **Task 1 RED tests** (`tests/unit/test_twitter_publisher.py`, `tests/unit/test_social_connector_security.py`, `tests/smoke/__init__.py`, `tests/smoke/test_twitter_live.py`) were committed by the **102-02 agent** as part of commit **`1db9e340`** (`test(102-02): add failing tests for token refresh and disconnect-revoke`).
2. **Task 2 GREEN production code** (`app/social/connector.py`, `app/social/publisher.py`, `supabase/migrations/20260508130000_twitter_reconnect_required.sql`) was committed by the **102-02 agent** as part of commit **`260ecf14`** (`feat(102-02): sync Google OAuth refresh helper + wire into 7 tool helpers (WORKSPACE-04)`).

**Fix:** None applied. Per the executor's git-safety protocol I do not run destructive operations (`git reset`, `git rebase -i`, `git commit --amend` against someone else's commit) without explicit user authorization. The functional outcome is correct -- all files landed in `git log` on `feat/vault-fixes-and-agent-actions`, all 9 Wave-0 tests pass, the migration file exists -- but the commit messages do not reflect the 104-01 attribution the plan called for.

**Recommended user action:** Either (a) leave it as-is and rely on the file-level diff to attribute the work, or (b) after all three concurrent plans complete and agents drain, run `git rebase -i` to split the affected commits and re-attribute. **Do not** force-push or amend without first auditing all three plans' file lists.

**Tracking:** Both my staging attempts (`git add app/social/...` and `git add tests/...`) succeeded individually; the race occurs at the shared-index level when another agent's `git commit` consumes the staged paths. Future executor: either serialize parallel plans on shared trees, or add per-plan worktrees (`git worktree add ../pikar-ai-104-01`).

### No other deviations

The plan's interfaces block, target shape, and verify steps were followed verbatim. No bugs auto-fixed (Rule 1), no missing critical functionality discovered (Rule 2), no architectural changes proposed (Rule 4).

## Open Question Status

- **APPEND endpoint shape (104-02)** -- N/A for this plan; deferred to Plan 104-02 chunked video upload.
- **Memory pressure for >100MB videos (104-02)** -- N/A; deferred to Plan 104-02.
- **OAuth2 + media.write reliability** -- Mitigation shipped: any 403 from `/2/media/upload` surfaces the user-facing reconnect prompt (`"Twitter media upload failed. If you previously connected your Twitter account, please reconnect to grant the new media.write permission."`). The behavior is asserted by `TestAuthErrorMessage::test_403_returns_reconnect_message`.

## Self-Check: PASSED

Files claimed -> exist:
- `app/social/connector.py` -- `media.write` at line 51 (verified via grep).
- `app/social/publisher.py` -- `_upload_image_twitter` at line 46, `_upload_video_twitter` at line 100, dispatch in `post_with_media` references both at lines 474 and 484 (verified via grep).
- `supabase/migrations/20260508130000_twitter_reconnect_required.sql` -- exists.
- `tests/unit/test_twitter_publisher.py` -- exists.
- `tests/unit/test_social_connector_security.py::test_twitter_scopes` -- passes.
- `tests/smoke/__init__.py` + `tests/smoke/test_twitter_live.py` -- exist; smoke test correctly skipped without `RUN_LIVE=1`.

Commits claimed -> exist:
- `1db9e340` -- contains my Task 1 test files (cross-attributed; see Deviations).
- `260ecf14` -- contains my Task 2 production code + migration (cross-attributed; see Deviations).

Tests claimed -> pass: `9 passed, 1 skipped` confirmed for the directly-touched test surface; `17 passed` confirmed for the broader social suite (connector security + twitter publisher + linkedin webhook).
