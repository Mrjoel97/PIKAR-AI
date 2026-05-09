# Phase 103 Context: LinkedIn Posting Fix

**Authored:** 2026-05-08
**Source:** Derived directly from `103-RESEARCH.md` and `ROADMAP.md` Phase 103 success criteria. No `/gsd:discuss-phase` was run; the audit success criteria are treated as locked decisions.

---

## Decisions (locked — non-negotiable)

These decisions are derived from the audit + research and are NOT subject to revision during execution. If a deviation is required, surface it via revision-mode rather than silently changing course.

### Endpoints & versioning

- **Posts API:** `POST https://api.linkedin.com/rest/posts` (NOT `/v2/ugcPosts`).
- **Required headers on every `/rest/*` call:**
  - `LinkedIn-Version: 202401`
  - `X-Restli-Protocol-Version: 2.0.0`
  - `Content-Type: application/json`
  - `Authorization: Bearer <token>`
- **Image upload:** `POST /rest/images?action=initializeUpload` -> `PUT` raw bytes to returned `value.uploadUrl` -> reference `value.image` URN as `content.media.id`.
- **Video upload:** `POST /rest/videos?action=initializeUpload` -> `PUT` each chunk per `uploadInstructions[]` (capture `etag` from each response) -> `POST /rest/videos?action=finalizeUpload` with `uploadedPartIds[]` -> reference `value.video` URN as `content.media.id`. **Do NOT poll** for `AVAILABLE` state; LinkedIn publishes the post when the video finishes processing.
- **Identity:** `GET https://api.linkedin.com/v2/userinfo` (OIDC). Store the bare `sub` value as `platform_user_id`. Compose `urn:li:person:{platform_user_id}` at publish time.

### URN strategy

- **Primary:** `urn:li:person:{sub}` from `/v2/userinfo`. Existing `openid` + `profile` scopes are sufficient — no new scope requests.
- **Storage:** bare sub (e.g. `782bbtaQ`), NOT the full URN, in `connected_accounts.platform_user_id`.
- **Backfill:** Lazy backfill on first publish for accounts connected before this phase (`platform_user_id IS NULL`). No migration script.
- **Pairwise-sub fallback:** Open Question 1 in research. Defer to live integration testing. Do NOT pre-build a `/v2/me` fallback now; if `INVALID_URN_ID` shows up in production, file a follow-up phase.

### Visibility / distribution

- Posts hardcode `"visibility": "PUBLIC"` and `distribution.feedDistribution: "MAIN_FEED"`. CONNECTIONS / LOGGED_IN visibility is out of scope.
- `lifecycleState: "PUBLISHED"`, `isReshareDisabledByAuthor: false`.

### Webhook signature (POST-03)

- **Header:** `X-LI-Signature` (NOT `X-LinkedIn-Signature`).
- **Format:** `hmacsha256=<hex>` — strip prefix before HMAC compare.
- **Secret:** `LINKEDIN_CLIENT_SECRET` (LinkedIn signs with `clientSecret`). `LINKEDIN_WEBHOOK_SECRET` is **deprecated** in this phase; remove the env from `.env.example` (keep deployment configs untouched in this phase — that's an ops follow-up).
- **Status code on invalid signature:** **401** (matches audit success criterion #3 literally — overrides the existing 403).
- **Status code on missing `LINKEDIN_CLIENT_SECRET`:** 500 (fail-closed; mirrors Linear/Asana/Stripe webhook patterns).
- **GET challenge handler:** already correct at `app/routers/webhooks.py:46-86`; **do not modify**.

### Encryption / PKCE

- Tokens are stored Fernet-encrypted (Phase 101 AUTH-02 already shipped). Use `connector._encrypt_token` / `_decrypt_token` for any new persistence.
- PKCE persistence path is settled (Phase 101 AUTH-03). Phase 103 does NOT touch `_store_pkce_verifier` / `_pop_pkce_verifier`.

### Phase 101 coordination

- Phase 103 is NOT blocked on Phase 101 AUTH-04. Implement a LinkedIn-specific `_fetch_linkedin_identity` helper inline in `connector.py`. Phase 101 will later refactor this into a generic `PROFILE_FETCHERS` registry — keep the helper signature `async def _fetch_linkedin_identity(http: httpx.AsyncClient, access_token: str) -> tuple[str | None, str | None]` so the registry refactor is a one-liner.

---

## Deferred Ideas (NOT for this phase)

- Pre-built `/v2/me` fallback for canonical member ID. Build only if production data shows `INVALID_URN_ID`.
- Polling for video `AVAILABLE` state before posting.
- Non-PUBLIC visibility (CONNECTIONS, LOGGED_IN).
- Backfill migration that loops over existing `platform='linkedin'` rows (lazy backfill is sufficient).
- Removing `LINKEDIN_WEBHOOK_SECRET` from `cloud-run-service.yaml`, Terraform vars, and Cloudflare worker (ops follow-up — separate phase).
- Updating `linkedin_webhook.resolve_user_from_event` to compare against the new bare-`sub` storage (existing query at `linkedin_webhook.py:116` matches `platform_user_id` against the **full URN** in payloads — bug, but separate from POST-01/02/03 success criteria; document in 103-02 as a known follow-up).
- Real-API smoke tests against a sandbox LinkedIn account. All Phase 103 tests are mock-based.
- HYGIENE-04 (80% line coverage on `app/social/`) — that's Phase 108.

---

## Claude's Discretion

- **Test mocking pattern:** Use `unittest.mock.patch.object(httpx.AsyncClient, "post"/"get"/"put")` consistent with `tests/unit/test_social_connector_security.py`. Do NOT add `respx` as a new dev dep.
- **Helper function naming:** `_fetch_linkedin_identity`, `_post_linkedin`, `_upload_linkedin_image`, `_upload_linkedin_video` are reasonable; deviate only if a clearer name emerges.
- **Where to define helpers:** In `app/social/publisher.py` as private methods of `SocialPublisher`. The `_fetch_linkedin_identity` helper lives on `SocialConnector` so it can be reused by both callback path and lazy-backfill path.
- **Extraction of LinkedIn into a separate module:** OUT of scope for this phase. The branch in `post_with_media` simply dispatches to a new private method `_post_linkedin`; the file stays one publisher class.
- **Logging:** Match existing `logger.warning(...)` / `logger.exception(...)` style in `connector.py`. New errors should reference `LinkedIn` and the failing step (URN fetch / image init / video chunk N / post).

---

## Out of Scope

| Item | Reason |
|------|--------|
| Twitter chunked upload (POST-04/05/06) | Phase 104 |
| YouTube resumable upload (POST-07) | Phase 105 |
| TikTok status poll (POST-08) | Phase 106 |
| Facebook resumable video (POST-09) | Phase 107 |
| Threads / Pinterest / 80% coverage (HYGIENE-01..04) | Phase 108 |
| Cloud Run / Terraform / Cloudflare LINKEDIN_WEBHOOK_SECRET cleanup | Ops follow-up |
| Real-API smoke against LinkedIn sandbox | Manual UAT, not in this phase |
| Pairwise-sub fallback to `/v2/me` | Build only if production shows `INVALID_URN_ID` |
| `linkedin_webhook.resolve_user_from_event` URN-vs-bare-sub mismatch fix | Document as known follow-up; not a POST-03 success criterion |

---

## Success Criteria (verbatim from ROADMAP.md, locked)

1. After OAuth, `connected_accounts.platform_user_id` is the OIDC `sub` value; `/rest/posts` request body has `author=urn:li:person:{platform_user_id}` (NOT placeholder); unit test asserts both.
2. LinkedIn text post POSTs to `/rest/posts` with `LinkedIn-Version: 202401`, returns 201; image posts attach a `urn:li:image:...` registered via `/rest/images?action=initializeUpload`; video posts attach a `urn:li:video:...` registered via the matching `/rest/videos` flow; integration test (mocked network) asserts request shape for all three.
3. Inbound webhook with invalid `X-LI-Signature` rejected with HTTP 401; webhook with valid signature (computed using `LINKEDIN_CLIENT_SECRET`) accepted; unit test asserts both branches.

## Plan Decomposition

Two plans (per research recommendation):

- **103-01 — URN capture + Posts API migration (POST-01 + POST-02):** publisher + connector + tests. ~3 tasks.
- **103-02 — Webhook signature realignment (POST-03):** webhook handler + router + tests. ~2 tasks.

Both plans are independent (disjoint files) and can run in parallel (Wave 1).
