---
phase: 105-youtube-resumable-upload
created: 2026-05-08
status: planned
research: 105-RESEARCH.md
---

# Phase 105 Context: YouTube Resumable Upload

## Summary

Replace the broken YouTube upload at `app/social/publisher.py:312-331` (sends a fictional `source_url` JSON field, missing `uploadType=resumable` — every call fails) with the proper two-step resumable protocol verified against Google Developers docs:

1. `POST https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status` with snippet/status JSON + `X-Upload-Content-Type` / `X-Upload-Content-Length` headers → 200 OK with session URL in `Location` header.
2. `PUT <session_url>` with raw video bytes → 201 Created with full Video resource.

Hybrid PUT path: ≤25MB single PUT, larger files chunked at 8MB (multiple of 256KB) with 308-Resume-Incomplete handling. All failure modes mapped to structured `{success:False, error, reason, retriable, remedy}` shape.

## Locked Decisions (from ROADMAP success criteria)

- MUST replace fictional `source_url` JSON with two-step resumable protocol — `source_url` ABSENT from codebase (grep verifiable)
- MUST use `POST .../videos?uploadType=resumable&part=snippet,status` then PUT bytes
- MUST surface structured errors with remediation hints for: network interrupt, expired session, rejected metadata (each tested)
- MUST add mock-based unit test asserting two-step request sequence
- MUST add real-API smoke test (feature-flagged) verifying live upload to test channel

## Claude's Discretion (per RESEARCH.md)

- Chunk size: 8MB (multiple of 256KB protocol minimum)
- Single-PUT threshold: 25MB (Pikar typical video size; chunked above)
- In-memory bytes (defer streaming-from-disk until profiling shows >50MB videos)
- Module-scope helpers `_upload_video_youtube`, `_put_chunked`, `_map_youtube_error` peer to `_upload_media_twitter`
- `categoryId="22"` (People & Blogs) hardcoded default; expose `category_id` kwarg for future agent use
- Smoke-test gating env var: `PIKAR_RUN_YOUTUBE_SMOKE=1` (matches research recommendation)

## Out of Scope

- OAuth token refresh on 401 — Phase 101 owns token lifecycle. Surface `authorizationRequired` with "re-authenticate" remedy; document follow-up.
- Streaming-from-disk for >50MB videos — RESEARCH.md flags as follow-up after profiling.
- `videoCategories.list` lookup — hardcoded `"22"` is sufficient.

## Dependencies

- **Phase 101** (encrypted token reads): assumed shipped. This phase consumes existing `connector.get_access_token()` exactly as `_upload_media_twitter` does.
- **Phase 102** (Workspace bridge): NOT a dependency. YouTube uses Google OAuth via `connector.py:63-72` (already declares `youtube.upload` + `youtube` scopes via `GOOGLE_CLIENT_ID/SECRET`). Connector is correct as-is per RESEARCH.md.

## Test Strategy

- Unit (12 tests, `tests/unit/test_youtube_publisher.py`): two-step sequence, init/PUT request shape, no `source_url` (grep), 5+ error mapping cases, missing Location header, chunked path with 308 resume.
- Smoke (gated, `tests/smoke/test_youtube_real_upload.py`): `PIKAR_RUN_YOUTUBE_SMOKE=1` triggers live upload of `tests/fixtures/test_video_1mb.mp4` to a real test channel; asserts `videos.list?id=<id>` resolves.
- Mocking: `respx` (preferred per RESEARCH.md). Add to dev deps: `uv add --dev respx`.

## Plan Decomposition

**1 plan, 3 waves (~5 tasks)** per RESEARCH.md hint. Helper + call-site change + tests are tightly coupled — splitting creates merge friction.

| Plan | Wave | Tasks | Touches |
|------|------|-------|---------|
| 105-01 | W0+W1+W2 | 5 | `app/social/publisher.py`, `tests/unit/test_youtube_publisher.py`, `tests/smoke/test_youtube_real_upload.py`, `tests/fixtures/test_video_1mb.mp4`, `pyproject.toml` (respx) |

## Open Questions (deferred)

1. Realistic file-size distribution → ship hybrid (single PUT ≤25MB, chunked >25MB); revisit if profiling shows >50MB.
2. Existing connected accounts may lack `youtube.upload` scope → covered by error mapping (`insufficientPermissions` → "re-authenticate").
3. `categoryId` per-upload configurability → kwarg added; agent wiring deferred.
4. OAuth token refresh on 401 → Phase 101 owns; out of scope here.
