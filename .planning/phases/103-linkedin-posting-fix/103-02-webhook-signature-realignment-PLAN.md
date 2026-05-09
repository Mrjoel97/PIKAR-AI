---
phase: 103-linkedin-posting-fix
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - app/social/linkedin_webhook.py
  - app/routers/webhooks.py
  - .env.example
  - tests/unit/test_linkedin_webhook_signature.py
autonomous: true
requirements: [POST-03]

must_haves:
  truths:
    - "verify_signature reads LINKEDIN_CLIENT_SECRET (NOT LINKEDIN_WEBHOOK_SECRET) and strips the hmacsha256= prefix before HMAC compare"
    - "POST /webhooks/linkedin reads the X-LI-Signature header (NOT X-LinkedIn-Signature)"
    - "Invalid or missing signature is rejected with HTTP 401 (audit-mandated, was 403)"
    - "Missing LINKEDIN_CLIENT_SECRET returns HTTP 500 fail-closed (matches Linear/Asana/Stripe pattern)"
    - "Valid signature with hmacsha256= prefix is accepted and the event is stored via store_webhook_event"
    - "GET challenge handler at app/routers/webhooks.py:46-86 is UNCHANGED (already correct)"
    - ".env.example documents that LINKEDIN_WEBHOOK_SECRET is deprecated and unused (LinkedIn signs with LINKEDIN_CLIENT_SECRET)"
  artifacts:
    - path: "app/social/linkedin_webhook.py"
      provides: "verify_signature using LINKEDIN_CLIENT_SECRET + hmacsha256= prefix handling"
      contains: "LINKEDIN_CLIENT_SECRET"
    - path: "app/routers/webhooks.py"
      provides: "POST /webhooks/linkedin: reads X-LI-Signature, returns 401 on invalid, 500 on missing secret"
      contains: "X-LI-Signature"
    - path: "tests/unit/test_linkedin_webhook_signature.py"
      provides: "Unit tests for valid + invalid + missing-header + missing-secret + GET-challenge-unchanged behaviors"
      contains: "test_valid_signature_accepted"
    - path: ".env.example"
      provides: "Deprecation note for LINKEDIN_WEBHOOK_SECRET"
      contains: "DEPRECATED"
  key_links:
    - from: "app/routers/webhooks.py:linkedin_webhook_event"
      to: "app/social/linkedin_webhook.py:verify_signature"
      via: "passes raw body bytes + X-LI-Signature header value"
      pattern: "X-LI-Signature"
    - from: "app/social/linkedin_webhook.py:verify_signature"
      to: "os.environ['LINKEDIN_CLIENT_SECRET']"
      via: "shared secret for HMAC-SHA256 hex digest"
      pattern: "LINKEDIN_CLIENT_SECRET"
---

<objective>
Fix three concrete defects in the LinkedIn webhook signature path so real LinkedIn signatures actually verify (currently 100% rejected because of header-name + secret + prefix bugs). Implements POST-03 success criterion: invalid signatures return 401, valid signatures are accepted, missing secret fails closed with 500.

Purpose: today, every real LinkedIn webhook delivery is rejected with HTTP 403 because (a) the header name is wrong (`X-LinkedIn-Signature` instead of `X-LI-Signature`), (b) the secret env var is wrong (`LINKEDIN_WEBHOOK_SECRET` instead of `LINKEDIN_CLIENT_SECRET`), and (c) the `hmacsha256=` prefix is never stripped. After this plan, LinkedIn webhook events flow through to `store_webhook_event` and downstream agent processing.

Output: `app/social/linkedin_webhook.py:verify_signature` rewritten; `app/routers/webhooks.py:linkedin_webhook_event` reads correct header and returns 401 on invalid (instead of 403); `.env.example` deprecates `LINKEDIN_WEBHOOK_SECRET`; new test file `test_linkedin_webhook_signature.py` covers valid/invalid/missing/secret-missing branches plus a smoke test that GET challenge handler still works.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/103-linkedin-posting-fix/103-CONTEXT.md
@.planning/phases/103-linkedin-posting-fix/103-RESEARCH.md
@app/social/linkedin_webhook.py
@app/routers/webhooks.py
@tests/unit/test_webhook_auth.py

<interfaces>
<!-- Contracts the executor MUST use. -->

LinkedIn signature spec (verbatim from Microsoft Learn 2025-08-27):

> The POST request sent by LinkedIn will include a header called `X-LI-Signature`. The value of this header is the HMACSHA256 hash of the JSON-encoded string representation of the POST body prefixed by `hmacsha256=` and it is computed using your app's clientSecret.

Reference verification algorithm:
```python
def verify_signature(payload: bytes, signature_header: str, client_secret: str) -> bool:
    if not signature_header or not signature_header.startswith("hmacsha256="):
        return False
    received = signature_header[len("hmacsha256="):]
    expected = hmac.new(client_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received)
```

GET challenge handler (already correct at `app/routers/webhooks.py:46-86` — DO NOT MODIFY):
```python
challenge_response = hmac.new(
    LINKEDIN_CLIENT_SECRET.encode("utf-8"),
    challengeCode.encode("utf-8"),
    hashlib.sha256,
).hexdigest()
return {"challengeCode": echo, "challengeResponse": <hex>}
```

Test fixture pattern (match `tests/unit/test_webhook_auth.py`):
```python
def _build_minimal_app():
    from fastapi import FastAPI
    import app.routers.webhooks as webhooks_module
    mini = FastAPI()
    mini.include_router(webhooks_module.router)
    return mini

# Usage:
with TestClient(_build_minimal_app(), raise_server_exceptions=False) as client:
    response = client.post("/webhooks/linkedin", ...)
```

Existing FastAPI router (relevant excerpts from app/routers/webhooks.py):
- Line 89-134: POST /webhooks/linkedin handler. Currently:
  - Line 104: `signature = request.headers.get("X-LinkedIn-Signature", "")` -- WRONG HEADER
  - Line 107: `raise HTTPException(status_code=403, detail="Invalid signature")` -- WRONG STATUS
- Line 27-33: imports `verify_signature` from `app.social.linkedin_webhook`.

Existing app/social/linkedin_webhook.py (lines 28-58 — current broken implementation):
- Line 29: `LINKEDIN_WEBHOOK_SECRET_ENV = "LINKEDIN_WEBHOOK_SECRET"` -- WRONG ENV
- Line 32-34: `_get_webhook_secret()` reads from wrong env var
- Line 37-58: `verify_signature` does NOT strip `hmacsha256=` prefix
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wave 0 — write failing tests for X-LI-Signature header + LINKEDIN_CLIENT_SECRET + 401 status code</name>
  <files>tests/unit/test_linkedin_webhook_signature.py</files>
  <behavior>
    Create `tests/unit/test_linkedin_webhook_signature.py`. Use the `_build_minimal_app` + `TestClient` pattern from `tests/unit/test_webhook_auth.py`. Use `monkeypatch.setenv` for env vars. Use `monkeypatch.setattr` to stub out `store_webhook_event` so tests don't hit Supabase.

    Tests (all FAIL initially):

    - **test_valid_signature_accepted_with_201_path**: Set `LINKEDIN_CLIENT_SECRET=test-secret`. Compute the correct HMAC: `expected = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()`. POST `/webhooks/linkedin` with body `{"eventType": "MEMBER_SOCIAL_ACTION", "actor": "urn:li:person:abc"}` and header `X-LI-Signature: hmacsha256={expected}`. Stub `app.social.linkedin_webhook.store_webhook_event` to return `{"id": "evt-1"}`. Assert response status 200 and JSON contains `"event_id": "evt-1"`. Assert `store_webhook_event` was called once.

    - **test_invalid_signature_rejected_with_401**: Set `LINKEDIN_CLIENT_SECRET=test-secret`. POST with header `X-LI-Signature: hmacsha256=deadbeef0000` (wrong digest). Assert response status **401** (NOT 403 — this is the explicit audit success criterion). Assert `store_webhook_event` was NOT called.

    - **test_missing_signature_header_rejected_with_401**: Set `LINKEDIN_CLIENT_SECRET=test-secret`. POST with no `X-LI-Signature` header. Assert 401.

    - **test_signature_without_hmacsha256_prefix_rejected**: Set `LINKEDIN_CLIENT_SECRET=test-secret`. POST with header `X-LI-Signature: <correct-hex-without-prefix>`. Assert 401 (the prefix is mandatory per LinkedIn spec).

    - **test_old_X_LinkedIn_Signature_header_rejected**: Set `LINKEDIN_CLIENT_SECRET=test-secret`. POST with the OLD header name `X-LinkedIn-Signature: hmacsha256={correct}`. Assert 401 (the new code does not accept the old header name; if a user is sending real LinkedIn events with the new header, the old header name is irrelevant and must be ignored).

    - **test_missing_LINKEDIN_CLIENT_SECRET_returns_500**: Delete `LINKEDIN_CLIENT_SECRET` from env. POST with any signature. Assert 500 (fail-closed). Detail string contains the word "secret".

    - **test_LINKEDIN_WEBHOOK_SECRET_alone_does_not_verify**: Delete `LINKEDIN_CLIENT_SECRET`. Set `LINKEDIN_WEBHOOK_SECRET=test-secret` (the deprecated env). POST with a signature computed from `test-secret`. Assert 500 (because `LINKEDIN_CLIENT_SECRET` is absent, even though the legacy var is set — this proves the deprecation).

    - **test_get_challenge_handler_still_works**: Set `LINKEDIN_CLIENT_SECRET=test-secret`. GET `/webhooks/linkedin?challengeCode=abc123`. Assert 200, JSON contains `challengeCode == "abc123"` and `challengeResponse == hmac.new(b"test-secret", b"abc123", hashlib.sha256).hexdigest()`. (Regression check — proves Plan 103-02 did not break the existing-and-correct GET handler.)

    Run `uv run pytest tests/unit/test_linkedin_webhook_signature.py -x -v`. Expect:
    - First 5 tests FAIL with status 403 (current code) or 200 (current code accepts wrong header due to mismatched comparison).
    - Test 6 (`missing_LINKEDIN_CLIENT_SECRET`) FAILS because current code reads `LINKEDIN_WEBHOOK_SECRET`.
    - Test 7 FAILS because current code accepts `LINKEDIN_WEBHOOK_SECRET`.
    - Test 8 (GET challenge) PASSES (already correct).

    Total: 7 fail, 1 pass.

    Commit: `test(103-02): add failing tests for LinkedIn webhook signature realignment (POST-03)`.
  </behavior>
  <action>
    1. Create `tests/unit/test_linkedin_webhook_signature.py`. Imports:
       ```python
       from __future__ import annotations
       import hashlib
       import hmac
       import json
       from unittest.mock import AsyncMock, patch

       import pytest
       from fastapi import FastAPI
       from fastapi.testclient import TestClient

       import app.routers.webhooks as webhooks_module
       import app.social.linkedin_webhook as linkedin_webhook_module
       ```

    2. Add `_build_app()` helper that mirrors `tests/unit/test_webhook_auth.py:_build_minimal_app`.

    3. Add a fixture or shared helper to compute the correct signature header value:
       ```python
       def _sign(body_bytes: bytes, secret: str) -> str:
           digest = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
           return f"hmacsha256={digest}"
       ```

    4. For each test, use `monkeypatch.setattr` to replace `app.social.linkedin_webhook.store_webhook_event` with an `AsyncMock` returning `{"id": "evt-1"}`. The router imports it via `from app.social.linkedin_webhook import store_webhook_event`, so the patch target IS `app.routers.webhooks.store_webhook_event` (the imported name in the router module). Apply the patch on the router module to be safe:
       ```python
       monkeypatch.setattr(
           "app.routers.webhooks.store_webhook_event",
           AsyncMock(return_value={"id": "evt-1"}),
       )
       monkeypatch.setattr(
           "app.routers.webhooks.extract_event_type",
           lambda payload: "MEMBER_SOCIAL_ACTION",
       )
       monkeypatch.setattr(
           "app.routers.webhooks.extract_organization_id",
           lambda payload: None,
       )
       monkeypatch.setattr(
           "app.routers.webhooks.resolve_user_from_event",
           lambda payload: None,
       )
       ```

    5. Implement the 8 tests as described in `<behavior>`. Use `client.post("/webhooks/linkedin", content=body_bytes, headers={"X-LI-Signature": sig, "Content-Type": "application/json"})` — note `content=` (raw bytes) NOT `json=` because the signature is computed over the literal body bytes that the server will read via `await request.body()`. The exact byte sequence MUST match.

    6. For `test_get_challenge_handler_still_works`, use `client.get("/webhooks/linkedin", params={"challengeCode": "abc123"})`.

    7. Run `uv run pytest tests/unit/test_linkedin_webhook_signature.py -x -v` — confirm 7 fail, 1 pass.

    8. Lint + format the test file.

    9. Commit: `test(103-02): add failing tests for LinkedIn webhook signature realignment (POST-03)`.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_linkedin_webhook_signature.py -x -v 2>&amp;1 | tail -40</automated>
  </verify>
  <done>
    `tests/unit/test_linkedin_webhook_signature.py` exists with 8 tests. 7 of 8 FAIL with status-code mismatches or signature-comparison failures. The GET-challenge test PASSES (proves the existing handler is preserved by the test setup). `ruff check` clean. Commit `test(103-02): add failing tests for LinkedIn webhook signature realignment (POST-03)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Realign verify_signature + router header/status, deprecate LINKEDIN_WEBHOOK_SECRET</name>
  <files>app/social/linkedin_webhook.py, app/routers/webhooks.py, .env.example</files>
  <behavior>
    After this task, all 8 tests in `test_linkedin_webhook_signature.py` are GREEN. All existing webhook tests in `test_webhook_auth.py` still pass.

    **app/social/linkedin_webhook.py** changes:

    1. Replace lines 28-29:
       ```python
       LINKEDIN_WEBHOOK_SECRET_ENV = "LINKEDIN_WEBHOOK_SECRET"
       ```
       with:
       ```python
       LINKEDIN_CLIENT_SECRET_ENV = "LINKEDIN_CLIENT_SECRET"
       _LINKEDIN_SIG_PREFIX = "hmacsha256="
       ```

    2. Replace `_get_webhook_secret()` (lines 32-34) with:
       ```python
       def _get_client_secret() -> str | None:
           """Get the LinkedIn application client secret used for webhook HMAC."""
           return os.environ.get(LINKEDIN_CLIENT_SECRET_ENV)
       ```

    3. Replace `verify_signature` (lines 37-58) with:
       ```python
       def verify_signature(payload: bytes, signature_header: str) -> bool:
           """Verify LinkedIn webhook X-LI-Signature header.

           LinkedIn signs payloads with HMAC-SHA256 of the raw body, prefixed
           with 'hmacsha256=', using the application's clientSecret.

           Args:
               payload: Raw request body bytes.
               signature_header: Value of the X-LI-Signature header.

           Returns:
               True if the signature is valid.
           """
           secret = _get_client_secret()
           if not secret:
               logger.warning(
                   "%s not configured -- rejecting LinkedIn webhook",
                   LINKEDIN_CLIENT_SECRET_ENV,
               )
               return False
           if not signature_header or not signature_header.startswith(_LINKEDIN_SIG_PREFIX):
               return False
           received = signature_header[len(_LINKEDIN_SIG_PREFIX):]
           expected = hmac.new(
               secret.encode("utf-8"),
               payload,
               hashlib.sha256,
           ).hexdigest()
           return hmac.compare_digest(expected, received)
       ```

    4. Update the docstring on `verify_signature` to reference `X-LI-Signature` (NOT `X-LinkedIn-Signature`).

    **app/routers/webhooks.py** changes:

    5. In `linkedin_webhook_event` (around lines 89-134):
       - BEFORE reading the body / signature, add a fail-closed guard for the secret:
         ```python
         if not os.environ.get("LINKEDIN_CLIENT_SECRET"):
             logger.error("LINKEDIN_CLIENT_SECRET not configured -- cannot verify webhook")
             raise HTTPException(
                 status_code=500,
                 detail="LinkedIn client secret not configured",
             )
         ```
         (This must run BEFORE `verify_signature`, which would also catch the missing secret but returns False -- producing 401 instead of 500. Audit pattern matches Linear/Asana/Stripe = 500 for missing secret, 401/403 for invalid signature.)
       - Change line 104 from:
         ```python
         signature = request.headers.get("X-LinkedIn-Signature", "")
         ```
         to:
         ```python
         signature = request.headers.get("X-LI-Signature", "")
         ```
       - Change line 107 from `status_code=403` to `status_code=401`.
       - Update the docstring (lines 91-99) to reference `X-LI-Signature` and the `hmacsha256=` prefix.

    6. Update the docstring at the top of `linkedin_webhook_event` to clarify: "LinkedIn signs every payload with HMAC-SHA256 via the `X-LI-Signature` header (value format: `hmacsha256=<hex>`). The verification uses `LINKEDIN_CLIENT_SECRET`."

    **`.env.example`** changes:

    7. Find the line that defines `LINKEDIN_WEBHOOK_SECRET=...` (line 87 per research). Update it to:
       ```
       # LINKEDIN_WEBHOOK_SECRET=...  # DEPRECATED -- LinkedIn signs webhooks with LINKEDIN_CLIENT_SECRET. This var is unused as of Phase 103 and may be removed from infrastructure configs in a future ops follow-up.
       ```
       Keep it commented so existing deployments do not break on env-var validation.

    Run `uv run pytest tests/unit/test_linkedin_webhook_signature.py tests/unit/test_webhook_auth.py -x -v`. All GREEN.

    Lint + format `app/social/linkedin_webhook.py` and `app/routers/webhooks.py`. Run `uv run ty check app/social/linkedin_webhook.py app/routers/webhooks.py`.

    Note: `app/social/linkedin_webhook.py:resolve_user_from_event` at line 116 looks up `connected_accounts.platform_user_id` against the FULL URN `actor_urn` from the payload (e.g. `urn:li:person:ABC123`). Plan 103-01 stores the BARE sub (e.g. `ABC123`). This is a known mismatch. **Out of scope for this phase** (per CONTEXT.md). Add a TODO comment at the top of `resolve_user_from_event`:
    ```python
    # TODO(post-Phase-103): platform_user_id is now the bare OIDC sub
    # (Phase 103 POST-01) but actor_urn here is the full URN. Either strip
    # the 'urn:li:person:' prefix here or denormalize. Track as follow-up.
    ```

    Commit: `fix(103-02): use X-LI-Signature header + LINKEDIN_CLIENT_SECRET + hmacsha256= prefix; reject invalid with 401 (POST-03)`.
  </behavior>
  <action>
    1. Edit `app/social/linkedin_webhook.py`:
       - Replace constants (line 29) and `_get_webhook_secret` (lines 32-34) and `verify_signature` (lines 37-58) per `<behavior>` step 1-3.
       - Add the TODO comment to `resolve_user_from_event` (above line 96).

    2. Edit `app/routers/webhooks.py`:
       - In `linkedin_webhook_event` (line 89-134):
         - Insert fail-closed guard for `LINKEDIN_CLIENT_SECRET` BEFORE `body = await request.body()` (so we 500 before reading the body if env is missing).
         - Change header lookup `X-LinkedIn-Signature` -> `X-LI-Signature`.
         - Change status code 403 -> 401.
         - Update docstring per step 6.

    3. Edit `.env.example`: find the `LINKEDIN_WEBHOOK_SECRET` line and replace with the deprecation comment per step 7. Use the Edit tool on the exact line.

    4. Run `uv run pytest tests/unit/test_linkedin_webhook_signature.py tests/unit/test_webhook_auth.py -x -v`. Confirm all 8 new tests + all existing webhook_auth tests GREEN.

    5. Lint:
       ```
       uv run ruff check app/social/linkedin_webhook.py app/routers/webhooks.py --fix
       uv run ruff format app/social/linkedin_webhook.py app/routers/webhooks.py
       uv run ty check app/social/linkedin_webhook.py app/routers/webhooks.py
       ```

    6. Verify `grep -rn "X-LinkedIn-Signature" app/` returns empty (old header gone). Verify `grep -rn "LINKEDIN_WEBHOOK_SECRET" app/social/ app/routers/` returns empty (the env-var lookup is gone from runtime code; `.env.example` may still reference it via the deprecation comment, which is intentional).

    7. Commit: `fix(103-02): use X-LI-Signature header + LINKEDIN_CLIENT_SECRET + hmacsha256= prefix; reject invalid with 401 (POST-03)`.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_linkedin_webhook_signature.py tests/unit/test_webhook_auth.py -x -v 2>&amp;1 | tail -30 &amp;&amp; uv run ruff check app/social/linkedin_webhook.py app/routers/webhooks.py 2>&amp;1 | tail -5</automated>
  </verify>
  <done>
    `app/social/linkedin_webhook.py:verify_signature` reads `LINKEDIN_CLIENT_SECRET` and strips `hmacsha256=` prefix. `app/routers/webhooks.py:linkedin_webhook_event` reads `X-LI-Signature`, returns 500 when secret missing, 401 when signature invalid. `.env.example` deprecation comment present. 8 of 8 new tests pass. Existing `test_webhook_auth.py` (Linear/Asana tests) still pass. `grep -rn "X-LinkedIn-Signature" app/` empty. `ruff check` and `ty check` clean. Commit `fix(103-02): use X-LI-Signature header + LINKEDIN_CLIENT_SECRET + hmacsha256= prefix; reject invalid with 401 (POST-03)` lands.
  </done>
</task>

</tasks>

<verification>
End-to-end: `uv run pytest tests/unit/test_linkedin_webhook_signature.py tests/unit/test_webhook_auth.py -x -v` -> all GREEN.

Grep verifications:
- `grep -rn "X-LinkedIn-Signature" app/` -> empty.
- `grep -rn "LINKEDIN_WEBHOOK_SECRET" app/social/ app/routers/` -> empty.
- `grep -rn "hmacsha256=" app/social/linkedin_webhook.py` -> at least one match (prefix constant).
- `grep -rn "X-LI-Signature" app/routers/webhooks.py` -> exactly one match.

Manual smoke (deferred to phase-level UAT):
- Configure a LinkedIn app webhook subscription pointing at the dev environment.
- Trigger an event (e.g. like a member post in the linked LinkedIn account).
- Observe a row in `social_webhook_events` and a `200 OK` response in the `webhooks/linkedin` POST log line. (If 401: verify the test signature matches `hmac.new(LINKEDIN_CLIENT_SECRET, body, sha256).hexdigest()` and the header value starts with `hmacsha256=`.)
</verification>

<success_criteria>
- ROADMAP success criterion #3 (POST-03): valid `X-LI-Signature: hmacsha256=<correct-hex>` (computed with `LINKEDIN_CLIENT_SECRET`) is accepted (200 + event stored); invalid signature is rejected with 401; missing secret returns 500. Verified by 8 tests.
- The deprecated env var `LINKEDIN_WEBHOOK_SECRET` is no longer read by any runtime code in `app/social/` or `app/routers/`.
- The GET challenge handler is unchanged (regression test `test_get_challenge_handler_still_works` confirms).
- The `resolve_user_from_event` URN-vs-bare-sub mismatch is documented as a TODO but not fixed (out of scope per CONTEXT).
- `ruff check` and `ty check` clean on both modified production files.
</success_criteria>

<output>
After completion, create `.planning/phases/103-linkedin-posting-fix/103-02-webhook-signature-realignment-SUMMARY.md` documenting:
- Exact diff summary (lines changed in `linkedin_webhook.py`, `webhooks.py`, `.env.example`).
- Confirmation that the GET challenge handler (`webhooks.py:46-86`) is byte-for-byte unchanged.
- The known follow-up: `resolve_user_from_event` URN normalization (URN vs bare sub).
- Test count delta: 0 -> 8 GREEN.
- Any deviations from this plan.
</output>
