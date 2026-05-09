# Phase 106 Context: TikTok Publish Completion

**Created:** 2026-05-08
**Phase:** 106-tiktok-publish-completion
**Milestone:** v13.0 Authentication & Connections Hardening
**Requirements:** POST-08

## User Vision

Today the agent says "I posted your video to TikTok" but the video never appears. TikTok's
publish API is two-step asynchronous (`init/` returns a `publish_id`; you must poll
`/status/fetch/` to learn the actual outcome) and our code only does the first step. The
fix is to add the polling loop, surface the real outcome to the agent, and stop reporting
false success.

## Locked Decisions

These decisions are NON-NEGOTIABLE for any plan in this phase.

### Decision 1: Polling cadence is fixed (5s initial, 5s interval, 300s cap)

**What:** `asyncio.sleep(5.0)` once before the first poll, `asyncio.sleep(5.0)` between
polls, hard ceiling of 300 seconds total wall-clock from the first sleep. No exponential
backoff, no jitter.

**Why:** The phase success criterion mandates this cadence verbatim ("every 5s starting
5s after `init/`, with a hard cap of 5 minutes"). At ≤12 req/min worst case it stays well
under TikTok's 30-req/min/access_token rate limit, so backoff is unnecessary. The 5-minute
cap matches TikTok's "usually finishes within one minute" expectation while bounding the
calling request's blocking time.

**Implications:** Up to 60 polls per publish. Wall-clock cost is dominated by the actual
TikTok processing time, not by network round trips.

### Decision 2: PULL_FROM_URL source path only — FILE_UPLOAD is out of scope

**What:** Continue using `source: "PULL_FROM_URL"` with `video_url` pointing at the
caller-supplied URL. Do not add the FILE_UPLOAD chunked-upload alternative.

**Why:** Existing code already uses PULL_FROM_URL; agents posting to TikTok already pass
public URLs (Supabase Storage, Cloud Storage). Adding FILE_UPLOAD would require chunked
upload plumbing identical in shape to YouTube/Facebook resumable uploads (separate
phases). Phase scope is "complete the publish flow," not "add a second upload path."

**Implications:** If `video_pull_failed` becomes a recurring `fail_reason` due to the
verified-domain requirement, the operator must add the source URL host to the TikTok app's
verified-domain list (deploy-time, dashboard-only).

### Decision 3: Endpoint correction ships in the same plan as the polling loop

**What:** Fix `/v2/post/publish/content/init/` (photo/carousel endpoint) →
`/v2/post/publish/video/init/` (video endpoint) AND adjust `publish_id` extraction to read
`data.publish_id` (not top-level `publish_id`) AS PART OF THE SAME PLAN that adds polling.

**Why:** Shipping the endpoint fix without polling makes the false-success bug worse —
real publishes start happening, but the caller still sees `publish_id` reported as
`post_id` with no signal whether the video actually published. Single conceptual change,
single file, single commit boundary.

**Implications:** Plan 106-01 covers both the endpoint fix and the polling loop.

### Decision 4: TikTok response handling branches before the generic 2xx fall-through

**What:** Inside `post_with_media`, after the TikTok init response, the TikTok branch
returns its own dict (from the polling helper) before reaching the shared response
handler at lines 337-352. The generic handler is left untouched for other platforms.

**Why:** The generic handler's `resp.json().get("publish_id")` reads top-level —
TikTok's `publish_id` is nested under `data`. Forcing a `data.publish_id` accommodation
into the shared handler would couple TikTok's response shape into Twitter/LinkedIn/IG
paths. Cleaner to branch.

**Implications:** TikTok now has its own return path with a richer payload (`video_id`,
`publish_id`, `success`, optional `fail_reason`). Other platforms unchanged.

### Decision 5: `publicaly_available_post_id` typo is preserved verbatim with a comment

**What:** Read `data["publicaly_available_post_id"]` (one `l`, sic). Add an inline code
comment so future maintainers do not "fix" the typo to `publicly_available_post_id`.

**Why:** TikTok's API field is literally misspelled. Renaming our reader breaks the
contract. The comment prevents well-meaning autocorrect.

**Implications:** A unit test asserts the literal misspelled key is read.

### Decision 6: Best-effort polling failure is surfaced as structured error, not raised

**What:** Returns dict shape on every terminal outcome:
- Success → `{"success": True, "platform": "tiktok", "post_id": ..., "video_id": ..., "publish_id": ..., "media_type": "video", "message": ...}`
- Failure → `{"error": "...", "fail_reason": "...", "publish_id": ...}` (no `success` key)
- Cap exceeded → `{"error": "publish_pending — check TikTok manually", "publish_id": ...}`
- Status fetch HTTP error → `{"error": "TikTok status fetch failed (...): ..."}`

**Why:** Matches the existing `post_with_media` contract — every other platform path
returns dicts, the agent layer reads `result.get("error")` to detect failure. Raising
exceptions from inside `post_with_media` would require adding `try/except` at every
caller, breaking convention.

**Implications:** "Raises a structured error" in the success criterion is implemented as
"returns a dict with an `error` key" — the agent surfaces this to the user.

### Decision 7: New test file lives under `tests/unit/social/`

**What:** Create `tests/unit/social/__init__.py` (package marker) and
`tests/unit/social/test_tiktok_publish_polling.py`. Existing publisher tests are spread
across `tests/unit/test_workflow_publish_contracts.py` (workflow-level, not unit-level)
and there is no current `tests/unit/social/` directory.

**Why:** Convention in `tests/unit/` is one directory per `app/` subpackage
(`tests/unit/services/` mirrors `app/services/`). Aligning with that convention prevents
test sprawl and makes future Phase 107 (Facebook), Phase 108 (Threads/Pinterest)
testing land naturally beside this one.

**Implications:** Wave 0 of Plan 106-01 creates the package marker before adding tests.

## Deferred Ideas

These are explicitly OUT OF SCOPE for Phase 106 — do not add tasks for them.

- **FILE_UPLOAD source path** for TikTok (chunked upload alternative to PULL_FROM_URL).
  Mention in code comment as future work; do not implement.
- **Webhook-based status delivery.** TikTok offers webhooks for publish-status callbacks
  that would replace polling entirely. Requires receiver endpoint, signature verification,
  durable storage of `publish_id` → caller mapping. Defer until cross-cutting webhook
  infrastructure phase.
- **Publish status persistence.** Storing `publish_id` and outcome in Supabase
  (`social_posts` or similar) for audit trail. Out of scope; current return-from-call
  pattern matches other platforms.
- **Retry of failed publishes** (re-init on `internal` `fail_reason`). Phase scope is
  "report the outcome accurately." Retry policy is a follow-on.
- **Concurrent-publish rate-limit coordination.** If multiple publishes for the same
  user run in parallel, polls aggregate against the access_token's 30-req/min budget.
  At 12 req/min per publish, that is 2 concurrent publishes worst case before throttling
  risk. Single-publish-per-user is the current usage shape; revisit if usage changes.
- **Endpoint correction unit-test coverage for non-TikTok platforms.** A regression test
  asserts the TikTok URL is `/video/init/`; existing other-platform tests are unchanged.

## Claude's Discretion

Areas where the plan author should make reasonable choices and document them in the task:

- **Helper method placement.** Add `_poll_tiktok_publish_status` as an instance method on
  `SocialPublisher` near the existing `_upload_media_twitter` helper, OR as a module-level
  async function. Recommendation: instance method for symmetry with `_upload_media_twitter`,
  but either is acceptable as long as testability (patch target stability) is preserved.
- **Deadline implementation.** Use `asyncio.get_event_loop().time() + 300.0` as deadline,
  OR a poll counter (`for _ in range(60):`). Loop-time deadline is more accurate
  (accounts for HTTP latency); counter is simpler. Pick one and document.
- **Logging verbosity.** WARNING on each non-terminal poll iteration would be noisy. INFO
  on the first poll and DEBUG on subsequent polls is reasonable. WARNING only on terminal
  failure. Pick the convention; document in task action.
- **Exact wording of `error` strings.** "publish_pending — check TikTok manually" is
  literal from the success criterion. Other error strings (status-fetch HTTP failures,
  no `publish_id` returned, etc.) are at the author's discretion as long as they include
  the `publish_id` for diagnostics where available.
- **Whether to expose `_poll_tiktok_publish_status` in the test surface.** It is a
  private helper but tests may exercise it directly OR drive it through
  `post_with_media`. Driving through the public method is preferred; document if you
  diverge.

## Constraints from Project

- **Async-first.** `app/social/publisher.py` is full-async. New helpers must use
  `asyncio.sleep`, `httpx.AsyncClient`, and `await`. No `time.sleep`. No `requests.get`.
- **No bare except.** Pre-commit hook will reject `except:`. Use `except Exception` (not
  needed in this phase since we return error dicts on each branch rather than catching).
- **No mutable default args.** Pre-commit hook will reject `def f(x=[])`. Use sentinels
  if defaults are needed.
- **Ruff + ty clean.** `uv run ruff check app/social/publisher.py` and
  `uv run ty check app/social/publisher.py` must pass before merge.
- **Pre-commit interrogate (docstring coverage 80%+).** New helper method needs a
  docstring describing the polling contract.

## Dependencies

- **Phase 101** (Security Hardening for `connected_accounts`) — provides
  Fernet-encrypted token reads via the existing `connector.get_access_token` interface.
  This phase does not change token plumbing; it consumes whatever
  `_get_token_or_error` returns.
- **Existing `httpx.AsyncClient(timeout=60.0)` context** at `publisher.py:116` — reused
  for both init and polling calls. Polling extends the timeout window via the loop's
  300s cap, but each individual HTTP call still respects the 60s per-request timeout.

## Out-of-Scope (explicit)

- Mock-based UAT or end-to-end test posting to a real TikTok account. Unit tests with
  mocked `httpx.AsyncClient` and patched `asyncio.sleep` are sufficient per the success
  criteria. A live-API smoke test is out of scope for this phase.
- Adding a `social_post_status` table or any persistence of publish outcomes.
- Touching the YouTube branch (Phase 105) or the Facebook branch (Phase 107) even
  though they share the same `post_with_media` method.
