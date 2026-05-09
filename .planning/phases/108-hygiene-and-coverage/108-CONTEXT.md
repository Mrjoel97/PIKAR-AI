# Phase 108 Planner Context

**Created:** 2026-05-08
**Source:** Synthesized from `108-RESEARCH.md`. No `/gsd:discuss-phase` was run; planner is exercising the documented research recommendations and resolving the open questions inline.

## Decisions (locked)

These decisions are NON-NEGOTIABLE for plan execution.

1. **Threads OAuth has its own credentials** — Use `THREADS_APP_ID` / `THREADS_APP_SECRET` env vars, NOT Facebook's. Allow optional fallback chain (`os.environ.get("THREADS_APP_ID") or os.environ.get("FACEBOOK_APP_ID")`) to keep dev ergonomics, but the canonical env var names ARE the Threads-specific ones. (Reconciles ROADMAP SC-1 with Meta's official Threads docs.)
2. **Pinterest uses Basic-auth at the token endpoint** — Add an `auth_method` discriminator to `PLATFORM_CONFIGS` (`"form"` default, `"basic"` for Pinterest). `handle_callback` and `_refresh_token` both branch on it. (Pinterest follows RFC 6749 strictly — body-only credentials are rejected.)
3. **`SOCIAL_TOOLS` keeps the unified surface** — `publish_to_social(platform="threads"|"pinterest", ...)` is the LLM-facing tool. `_post_threads` and `_post_pinterest` exist as private helpers in `publisher.py`. Do NOT bloat `SOCIAL_TOOLS` with per-platform LLM functions. (Resolves Open Question 2 toward idiomatic interpretation.)
4. **`disconnect_account` is async; status update over delete** — Refactor `revoke_connection` (sync) into async `disconnect_account` that:
   - loads token first,
   - POSTs to provider revoke endpoint (best-effort, never blocks user),
   - then UPDATES `connected_accounts.status='revoked'` (audit-trail value over hard delete).
   `revoke_connection` remains a thin sync wrapper that calls `asyncio.run(self.disconnect_account(...))` for backward compat with `app/agents/tools/social.py:disconnect_social_account`. (Reconciles ROADMAP SC-4 "BEFORE deleting the local row" with the existing update-based audit pattern.)
5. **LinkedIn has no remote revoke** — `_revoke_at_provider` returns `(False, "no_remote_revoke_endpoint")` for LinkedIn without making any HTTP call. The local row is still updated. (Verified negative claim; Microsoft Learn search returned zero hits for revoke endpoint.)
6. **`platform_user_id` column already exists** — `supabase/migrations/0010_connected_accounts.sql:8` declares `platform_user_id TEXT`. NO migration needed for the column itself. The CHECK constraint at `supabase/migrations/20260320000000_social_analytics_listening.sql:91-98` enumerates the allowed platforms; a NEW migration in plan 108-01 (Threads) and 108-02 (Pinterest) MUST add `'threads'` and `'pinterest'` to the platform CHECK constraint, otherwise upserts will fail.
7. **Test framework: `unittest.mock` only** — Patch `httpx.AsyncClient` and the supabase client. Do NOT introduce `respx` or `httpx_mock`. Match the project pattern from `tests/unit/test_phase89_media_tagging.py`. `pytest-cov` is already in dev deps (`pyproject.toml:63`).
8. **`asyncio_mode = "strict"`** — Add to `[tool.pytest.ini_options]` in `pyproject.toml`. Each async test gets an explicit `@pytest.mark.asyncio` decorator. Surfaces silent no-op decorator bugs.
9. **Coverage target: ≥80% line coverage on `app/social/`** — Enforced via `--cov-fail-under=80` in plan 108-04.
10. **Pinterest pin posting requires `extra["board_id"]`** — Extend `post_with_media` signature with `extra: dict[str, Any] | None = None`. `publish_to_social` passes through. Returns a structured error if missing.

## Deferred Ideas (NOT in scope for Phase 108)

These will NOT be planned or implemented:

- **Redis-backed PKCE verifier store** — Already partially shipped in `oauth_pkce_states` table per STATE.md; cross-worker hardening for the in-memory fallback is AUTH-03 territory. Phase 108 tests use the existing path with a monkeypatch.
- **Pinterest video pins / carousel pins / `image_base64` source type** — Out of scope; HYGIENE-02 only requires `image_url` source pins.
- **LinkedIn URN fix (`urn:li:person:PERSON_ID` placeholder)** — Phase 103 territory (POST-01).
- **Twitter chunked upload completeness (APPEND/FINALIZE)** — Phase 104 territory (POST-04, POST-05).
- **YouTube resumable upload migration** — Phase 105 territory (POST-07).
- **TikTok `publish/status/fetch/` polling** — Phase 106 territory (POST-08).
- **Facebook resumable video upload** — Phase 107 territory (POST-09).
- **Per-platform `post_threads(...)` / `post_pinterest_pin(...)` LLM tools** — Locked decision 3. Internal helpers only.
- **Manual smoke tests against real Meta + Pinterest dev accounts** — Documented as a manual UAT step in 108-04, not automated.

## Claude's Discretion

- Naming of internal helper methods (e.g., `_post_threads` vs `_threads_post_branch`) — pick what's clearest and consistent with `_upload_media_twitter`.
- Layout of `tests/unit/social/conftest.py` fixtures — design for reuse across the 4-5 test modules.
- Whether to commit the `pyproject.toml` `asyncio_mode` change as its own micro-commit or fold it into 108-04 plan's first task — fold it.
- Exact line where `*SOCIAL_TOOLS` is spread into the Content Director's tools list (research suggests "after `*GRAPH_TOOLS`" but any clean position works).

## Provenance

- `108-RESEARCH.md` (782 lines, 2026-05-08) — primary input
- `app/social/connector.py`, `app/social/publisher.py`, `app/agents/tools/social.py` — current code shape
- `app/agents/content/agent.py:27-103, 558-630` — Content Director construction
- `app/agents/marketing/agent.py:368-378` — `_SOCIAL_TOOLS_LIST` reference pattern
- `supabase/migrations/0010_connected_accounts.sql:8-9`, `20260320000000_social_analytics_listening.sql:91-98` — `platform_user_id` and platform CHECK constraint
- `tests/unit/test_phase89_media_tagging.py` — `unittest.mock` pattern reference
- `pyproject.toml:63, 127-134` — `pytest-cov` already present, `asyncio_mode` not set
- ROADMAP.md Phase 108 section + REQUIREMENTS.md HYGIENE-01..04
