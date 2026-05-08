---
phase: 101-security-hardening
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - supabase/migrations/20260509000000_phase101_verify_connected_accounts_rls.sql
  - tests/integration/test_connected_accounts_rls.py
  - tests/unit/social/__init__.py
  - tests/unit/social/test_connector_encryption.py
  - scripts/migrate_connected_accounts_encryption.py
  - tests/unit/scripts/test_migrate_connected_accounts_encryption.py
autonomous: true
requirements: [AUTH-01, AUTH-02]

must_haves:
  truths:
    - "RLS on public.connected_accounts is ENABLED and the only user-facing policies are the four user-scoped (SELECT/INSERT/UPDATE/DELETE) `(SELECT auth.uid()) = user_id` policies plus the service_role bypass — verified by an integration test that authenticates as user A with the anon client and asserts SELECT returns 0 rows for user B's user_id and 1 row for A's"
    - "Calling SocialConnector.handle_callback writes Fernet-encrypted access_token and refresh_token to connected_accounts (the upserted value, when fed back through decrypt_secret, returns the original plaintext bearer token) — verified by a unit test asserting the upsert payload is NOT the plaintext"
    - "Calling SocialConnector.get_access_token on a row with encrypted access_token returns the decrypted plaintext string — verified by a unit test"
    - "scripts/migrate_connected_accounts_encryption.py is idempotent: running it on a row whose access_token already starts with `gAAAAA` (Fernet header) and decrypts cleanly is a no-op; running it on a plaintext row encrypts and updates that row in place; running it twice in a row produces no further updates on the second run"
  artifacts:
    - path: "supabase/migrations/20260509000000_phase101_verify_connected_accounts_rls.sql"
      provides: "Idempotent re-assertion of the four user-scoped RLS policies + service_role bypass on public.connected_accounts (DROP POLICY IF EXISTS chain matching 20260415113000, then identical CREATE POLICY chain). Safe to apply on any environment regardless of whether 20260415113000 was previously applied."
      contains: "(SELECT auth.uid()) = user_id"
    - path: "tests/integration/test_connected_accounts_rls.py"
      provides: "Integration test that boots a local Supabase via fixture, seeds two users, signs in as user A with the anon client, asserts SELECT returns A's row only — proves cross-user denial works under the new policy"
      contains: "test_user_a_cannot_read_user_b_connected_accounts"
    - path: "tests/unit/social/__init__.py"
      provides: "New package marker so pytest collects the social subdirectory (does not currently exist per RESEARCH §Wave 0 Gaps)"
    - path: "tests/unit/social/test_connector_encryption.py"
      provides: "Unit tests covering: (a) handle_callback upserts ciphertext for both access_token and refresh_token; (b) get_access_token returns decrypted plaintext when the row contains a Fernet token; (c) get_access_token returns plaintext unchanged when the row contains a legacy plaintext value (decryption fallback path at connector.py:140-144)"
      contains: "test_handle_callback_writes_fernet_encrypted_tokens"
    - path: "scripts/migrate_connected_accounts_encryption.py"
      provides: "One-time backfill script: iterates all rows in connected_accounts via service-role client, attempts decrypt_secret on access_token/refresh_token; on InvalidToken (plaintext detected), encrypts in place and updates the row. CLI flags: --dry-run (default), --apply, --verbose. Logs counts: total rows / already-encrypted / migrated / failed."
      contains: "is_already_fernet"
    - path: "tests/unit/scripts/test_migrate_connected_accounts_encryption.py"
      provides: "Unit tests with a fake Supabase client covering the three main branches: row already Fernet (skip), row plaintext (encrypt + update), idempotent re-run (no-op on second pass)"
      contains: "test_migration_is_idempotent_on_already_encrypted_rows"
  key_links:
    - from: "supabase/migrations/20260509000000_phase101_verify_connected_accounts_rls.sql"
      to: "public.connected_accounts"
      via: "ALTER TABLE ... ENABLE ROW LEVEL SECURITY + DROP/CREATE POLICY chain"
      pattern: "(SELECT auth.uid()) = user_id"
    - from: "scripts/migrate_connected_accounts_encryption.py"
      to: "app.services.encryption.encrypt_secret"
      via: "Detect plaintext via decrypt_secret-raises-InvalidToken, then encrypt + .update(...).eq(\"id\", row_id).execute()"
      pattern: "encrypt_secret"
    - from: "tests/unit/social/test_connector_encryption.py"
      to: "app.social.connector.SocialConnector.handle_callback"
      via: "Patches httpx.AsyncClient + encrypt_secret/decrypt_secret; asserts upsert payload contains Fernet ciphertext, not raw bearer token"
      pattern: "connected_account_upserts"
---

<objective>
Lock down the on-disk security surface for `connected_accounts`: prove the existing RLS hardening migration (20260415113000) is correctly applied with an integration test, harden the encryption-at-rest contract with explicit unit tests on the boundary, and ship a one-time idempotent backfill script that converts any legacy plaintext token rows in production to Fernet ciphertext.

Purpose: Satisfy AUTH-01 success criterion #1 (cross-user RLS denial proved by an integration test — gap per ROADMAP line 451) and AUTH-02 success criterion #2 (raw `SELECT access_token` returns Fernet ciphertext, not a bearer token — verified for both new writes and existing legacy rows). Per RESEARCH §Current State, the codified migration history is good and `_encrypt_token`/`_decrypt_token` already wrap writes/reads in `app/social/connector.py:126-150`; the gaps are (a) no test asserts cross-user denial, (b) no test asserts the upsert-side-effect is ciphertext, (c) no backfill exists for legacy rows that predate the encryption code path.

Output: An idempotent verification SQL migration (safe to apply over the existing 20260415113000), one new integration test for cross-user RLS, three new unit tests for the encryption boundary, a Python backfill script with --dry-run / --apply CLI, and unit tests for the script. No changes to `app/social/connector.py` (it is already correct for AUTH-02; behavior is preserved).
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/101-security-hardening/101-RESEARCH.md
@.planning/phases/101-security-hardening/101-CONTEXT.md
@app/social/connector.py
@app/services/encryption.py
@tests/unit/test_social_connector_security.py
@supabase/migrations/0010_connected_accounts.sql
@supabase/migrations/20260415113000_harden_connected_accounts_rls.sql
@supabase/migrations/20260508123000_social_oauth_security.sql

<interfaces>
<!-- Key contracts the executor needs. Extracted from the codebase. -->
<!-- Use these directly — no codebase exploration needed. -->

From app/services/encryption.py:
```python
def encrypt_secret(plaintext: str) -> str:
    """Encrypt a plaintext string with the current primary Fernet key.
    Returns base64-encoded URL-safe Fernet token (starts with 'gAAAAA').
    Raises RuntimeError if ADMIN_ENCRYPTION_KEY is not configured.
    """

def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted ciphertext string.
    Tries all configured keys (MultiFernet) for rotation support.
    Raises:
        RuntimeError: ADMIN_ENCRYPTION_KEY not configured.
        cryptography.fernet.InvalidToken: ciphertext invalid/unknown key.
    """
```

From app/social/connector.py (already implemented — DO NOT modify in this plan):
```python
class SocialConnector:
    def __init__(self):
        self.client = self._get_supabase()  # service-role Supabase client
        self._pkce_verifiers: dict[str, str] = {}  # local-memory fallback

    def _encrypt_token(self, token: str | None) -> str | None: ...
    def _decrypt_token(self, token: str | None) -> str | None:
        # On InvalidToken, returns the value unchanged ONLY if it does NOT
        # start with 'gAAAAA' — supports legacy plaintext rows during migration.

    async def handle_callback(
        self, platform: str, code: str, state: str, redirect_uri: str
    ) -> dict[str, Any]:
        # Already encrypts before upsert (connector.py:315-316, 329-330)
        # Already pops PKCE verifier via _pop_pkce_verifier (Postgres-backed)

    def get_access_token(self, user_id: str, platform: str) -> str | None:
        # Already calls _decrypt_token on the row's access_token (connector.py:393)
```

From tests/unit/test_social_connector_security.py (existing partial coverage to AVOID duplicating):
```python
# Already covered:
def test_pkce_verifier_is_persisted_encrypted_and_consumed(): ...
async def test_callback_uses_persisted_pkce_and_stores_encrypted_tokens(monkeypatch): ...
def test_get_access_token_decrypts_stored_token(): ...

# These tests use the in-test _FakeClient + _FakeTable abstractions and
# patch encrypt_secret/decrypt_secret at app.social.connector. The new
# tests in tests/unit/social/test_connector_encryption.py SHOULD reuse
# this pattern (consider extracting _FakeClient to a fixture module if
# duplication grows past one file).
```

Project test command (from CLAUDE.md):
```bash
uv run pytest tests/unit/social/ -x
uv run pytest tests/integration/test_connected_accounts_rls.py -x
```

RLS migration shape (verified — copy-paste skeleton from 20260415113000):
```sql
ALTER TABLE public.connected_accounts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users manage own accounts" ON public.connected_accounts;
DROP POLICY IF EXISTS "Users can view own connected accounts" ON public.connected_accounts;
DROP POLICY IF EXISTS "Users can insert own connected accounts" ON public.connected_accounts;
DROP POLICY IF EXISTS "Users can update own connected accounts" ON public.connected_accounts;
DROP POLICY IF EXISTS "Users can delete own connected accounts" ON public.connected_accounts;
DROP POLICY IF EXISTS "Service Role manages all" ON public.connected_accounts;

CREATE POLICY "Users can view own connected accounts" ON public.connected_accounts
    FOR SELECT TO authenticated USING ((SELECT auth.uid()) = user_id);
-- ... INSERT/UPDATE/DELETE/service_role mirror 20260415113000 exactly
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add Wave-0 RED tests for AUTH-02 encryption boundary</name>
  <files>tests/unit/social/__init__.py, tests/unit/social/test_connector_encryption.py</files>
  <behavior>
    Create the new package directory and test module. Three NEW unit tests, each FAILING initially is NOT required here because the production code already implements the encryption pattern — the GREEN state should hold immediately when tests are added correctly. **The point of this task is locking in the contract with explicit assertions** (today only `tests/unit/test_social_connector_security.py` covers it implicitly). If any test FAILS on this run, that is a real regression and must be fixed in `app/social/connector.py` BEFORE moving on.

    1. **test_handle_callback_writes_fernet_encrypted_tokens_for_both_access_and_refresh**: Build a `_FakeClient` (copy the pattern from `tests/unit/test_social_connector_security.py:91-99` — do NOT import the private class; reproduce a minimal version inline). Set up a PKCE row keyed by `state="user-1:abc"`. Patch `httpx.AsyncClient` to return tokens `{"access_token": "real-bearer", "refresh_token": "real-refresh", "expires_in": 1800}`. Patch `encrypt_secret` so `encrypt_secret("real-bearer") == "gAAAAA-real-bearer"` and `encrypt_secret("real-refresh") == "gAAAAA-real-refresh"`. Patch `decrypt_secret` to return `"verifier"` (so the PKCE pop succeeds). Set `LINKEDIN_CLIENT_ID`/`LINKEDIN_CLIENT_SECRET` via `monkeypatch.setenv`. Run `await connector.handle_callback("linkedin", "code", "user-1:abc", "https://app.test/cb")`. Assert: `client.connected_account_upserts[0]["access_token"] == "gAAAAA-real-bearer"` AND `client.connected_account_upserts[0]["refresh_token"] == "gAAAAA-real-refresh"` AND **neither value equals the plaintext** (defensive `assert "real-bearer" not in client.connected_account_upserts[0]["access_token"]`).

    2. **test_get_access_token_falls_back_to_plaintext_for_legacy_rows**: Seed `client.connected_accounts = [{"access_token": "plaintext-legacy-token", "token_expires_at": (now + 5min).isoformat(), ...}]`. Patch `decrypt_secret` to raise `cryptography.fernet.InvalidToken`. Call `connector.get_access_token("user-1", "linkedin")`. Assert it returns `"plaintext-legacy-token"` (matching `connector.py:140-144` legacy fallback) AND a WARNING was logged with substring "legacy plaintext" (use `caplog.set_level(logging.WARNING, logger="app.social.connector")`). This pins the legacy-row migration tolerance contract.

    3. **test_get_access_token_returns_none_when_fernet_token_decryption_fails_with_gAAAAA_prefix**: Seed `client.connected_accounts = [{"access_token": "gAAAAAcorrupted", "token_expires_at": (now + 5min).isoformat(), ...}]`. Patch `decrypt_secret` to raise `InvalidToken`. Call `connector.get_access_token("user-1", "linkedin")`. Assert returns `None` (corrupted-ciphertext path at `connector.py:137-139`). Assert `logger.exception` was invoked with substring "could not be decrypted".

    Run `uv run pytest tests/unit/social/test_connector_encryption.py -x -v 2>&1 | tail -30`. ALL 3 tests should pass on first run because production code already implements the contract. If any FAIL, fix the production code first (this becomes a regression-recovery task instead).

    Add `tests/unit/social/__init__.py` as an empty file (package marker for pytest discovery).

    Commit message: `test(101-01): pin AUTH-02 encryption contract with explicit unit tests on connector boundary`.
  </behavior>
  <action>
    1. Create empty file `tests/unit/social/__init__.py`.
    2. Create `tests/unit/social/test_connector_encryption.py`. Use `from __future__ import annotations`, `import pytest`, `from datetime import datetime, timedelta, timezone`, `from unittest.mock import patch`, `from cryptography.fernet import InvalidToken`, `from app.social.connector import SocialConnector`. Reproduce the minimal `_FakeClient`/`_FakeTable` pattern (copy from `tests/unit/test_social_connector_security.py:12-99` — extract to a local helper at the top of the new file; do not import the private `_FakeClient` symbol since it is module-private).
    3. Use `pytest.mark.asyncio` on the async test (already configured per `pyproject.toml` per CLAUDE.md).
    4. Patch `app.social.connector.encrypt_secret` and `app.social.connector.decrypt_secret` (NOT the source module — the connector imports these at module scope per `connector.py:23`).
    5. Use `caplog` fixture for log assertions; ensure `caplog.set_level(logging.WARNING, logger="app.social.connector")` is called in tests that assert log lines.
    6. Verify tests collect AND pass: `uv run pytest tests/unit/social/ -x -v`.
    7. Lint: `uv run ruff check tests/unit/social/ --fix && uv run ruff format tests/unit/social/`.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/social/test_connector_encryption.py -x -v 2>&1 | tail -25</automated>
  </verify>
  <done>
    `tests/unit/social/__init__.py` exists. `tests/unit/social/test_connector_encryption.py` exists with 3 tests, all GREEN. `uv run ruff check tests/unit/social/` clean. Existing `tests/unit/test_social_connector_security.py` still passes (no regression). Commit `test(101-01): pin AUTH-02 encryption contract with explicit unit tests on connector boundary` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add Wave-0 failing test for AUTH-01 cross-user RLS denial</name>
  <files>tests/integration/test_connected_accounts_rls.py</files>
  <behavior>
    Add ONE new integration test that proves a user authenticated with their JWT against the anon-key Supabase client cannot SELECT another user's `connected_accounts` rows. This test MUST initially be skip-marked if no local Supabase stack is running, otherwise it MUST run and pass. **The test fails (or is "skipped" but visibly so) before the verification migration in Task 3 lands** if the prod env in CI does not yet have the harden migration applied.

    Test signature: `async def test_user_a_cannot_read_user_b_connected_accounts(supabase_local)` where `supabase_local` is a session-scoped pytest fixture that:
    - Calls `subprocess.run(["supabase", "status", "--output", "json"])` (or attempts a TCP probe of `localhost:54321`); if not running, `pytest.skip("supabase local stack not running; run `supabase start`")`.
    - Returns dict `{anon_url, anon_key, service_role_key}` parsed from `supabase status --output json`.

    Test body (numbered):
    1. Use the **service-role** client to: (a) create user A via `supabase.auth.admin.create_user({"email": "phase101-rls-a@test.local", "password": "test-A-pass-1234", "email_confirm": True})`, capture `user_a.id`; (b) same for user B; (c) insert one row into `connected_accounts` for each: `{"user_id": user_a.id, "platform": "linkedin", "access_token": "tok-a", "status": "active"}` and same for B with `tok-b`.
    2. Sign in as user A using the **anon** client: `client_a.auth.sign_in_with_password({...})`. Capture the session JWT.
    3. With `client_a` (now bound to A's JWT — the anon key + the access token), execute `client_a.table("connected_accounts").select("user_id, platform, access_token").execute()`.
    4. Assert `len(result.data) == 1` AND `result.data[0]["user_id"] == user_a.id` AND `result.data[0]["access_token"] == "tok-a"`.
    5. Cleanup: `supabase.auth.admin.delete_user(user_a.id)` and same for B; CASCADE on `auth.users → connected_accounts.user_id` (per `0010_connected_accounts.sql:6`) handles the row deletion.

    On a fresh checkout WITHOUT the existing 20260415113000 migration applied, this test would return 2 rows (the permissive `USING (true)` policy from 0010 line 30). With the harden migration applied, it returns 1 row. Therefore the test acts as a regression gate against any future migration that re-introduces a permissive policy. Task 3's verification migration is what guarantees the test passes regardless of the existing 20260415113000 migration's apply state.

    Commit message: `test(101-01): assert cross-user RLS denial on connected_accounts (AUTH-01)`.

    Run: `uv run pytest tests/integration/test_connected_accounts_rls.py -x -v -s 2>&1 | tail -30`. Outcome: PASS if `supabase start` is running locally; SKIP otherwise (with the message "supabase local stack not running"). NOT a hard FAIL when supabase isn't running — CI must still be green for the unit-test-only path.
  </behavior>
  <action>
    1. Create `tests/integration/test_connected_accounts_rls.py`. If `tests/integration/__init__.py` does not exist, create it as an empty file.
    2. Imports: `from __future__ import annotations`, `import json`, `import subprocess`, `import pytest`, `from supabase import create_client`. Use `pytest.mark.asyncio` only if any helper is genuinely async; otherwise keep the test sync.
    3. Implement the `supabase_local` fixture as session-scoped (`@pytest.fixture(scope="session")`). Probe with `subprocess.run(["supabase", "status", "--output", "json"], capture_output=True, text=True, timeout=5)`. On `FileNotFoundError`, `subprocess.TimeoutExpired`, or non-zero exit, `pytest.skip(...)`. On success, parse JSON and return the `{API URL, anon key, service_role key}` triple. Note the JSON keys returned by `supabase status --output json` may use display-friendly names like `"API URL"`; key by exact match to whatever the local CLI returns (verify with `supabase status --output json` in shell; document in test docstring).
    4. Inside the test, use unique emails per run (e.g. `f"phase101-rls-a-{uuid4().hex[:8]}@test.local"`) so reruns don't collide. Wrap the user-creation/cleanup in try/finally so failed asserts still clean up.
    5. Verify locally: `supabase start` (or skip if Docker not available); `uv run pytest tests/integration/test_connected_accounts_rls.py -x -v -s`.
    6. Lint: `uv run ruff check tests/integration/test_connected_accounts_rls.py --fix && uv run ruff format tests/integration/test_connected_accounts_rls.py`.
  </action>
  <verify>
    <automated>uv run pytest tests/integration/test_connected_accounts_rls.py -x -v 2>&1 | tail -15</automated>
  </verify>
  <done>
    `tests/integration/test_connected_accounts_rls.py` exists with the cross-user denial test. The test PASSES when a local Supabase stack is running with the harden migration applied; SKIPS cleanly otherwise (no FAIL / no ERROR). `ruff check` clean. Commit `test(101-01): assert cross-user RLS denial on connected_accounts (AUTH-01)` lands.
  </done>
</task>

<task type="auto">
  <name>Task 3: Ship idempotent verification migration for AUTH-01 RLS</name>
  <files>supabase/migrations/20260509000000_phase101_verify_connected_accounts_rls.sql</files>
  <action>
    Create `supabase/migrations/20260509000000_phase101_verify_connected_accounts_rls.sql`. The body MUST be a byte-for-byte equivalent of `20260415113000_harden_connected_accounts_rls.sql` — copy that file verbatim, change the leading comment to:
    ```sql
    -- Phase 101 (AUTH-01): Re-assert connected_accounts RLS policies idempotently.
    -- Mirrors 20260415113000_harden_connected_accounts_rls.sql exactly so any
    -- environment that missed the prior migration ends up in the correct state.
    -- Safe to re-apply: every CREATE is preceded by DROP IF EXISTS.
    ```
    Then keep the rest verbatim: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` + DROP POLICY IF EXISTS chain (6 lines) + four user-scoped CREATE POLICY statements + `Service Role manages all` policy.

    Verification — apply locally and inspect:
    1. `supabase db reset --local` (rebuilds from full migration chain including the new file).
    2. Connect to local DB: `psql "postgresql://postgres:postgres@localhost:54322/postgres"`.
    3. `\d+ public.connected_accounts` — confirm RLS is enabled.
    4. `SELECT polname, polcmd, pg_get_expr(polqual, polrelid) AS using_expr, pg_get_expr(polwithcheck, polrelid) AS check_expr FROM pg_policy WHERE polrelid = 'public.connected_accounts'::regclass ORDER BY polname;` — confirm exactly 5 policies present: 4 user-scoped + service_role bypass; user-scoped USING/WITH CHECK expressions read `(SELECT auth.uid()) = user_id`.
    5. Re-apply the migration twice without resetting: `supabase migration up --local` (idempotency check) — must report no errors and no policy duplications.
    6. Run the integration test from Task 2 — must PASS.

    Commit message: `feat(101-01): add idempotent RLS verification migration for connected_accounts (AUTH-01)`.

    DO NOT modify or delete `20260415113000_harden_connected_accounts_rls.sql`. Both files are kept; the new one is a defensive re-assertion so any environment that skipped the earlier one still ends up correct.
  </action>
  <verify>
    <automated>supabase db reset --local 2>&1 | tail -10 && supabase migration up --local 2>&1 | tail -5 && uv run pytest tests/integration/test_connected_accounts_rls.py -x 2>&1 | tail -10</automated>
  </verify>
  <done>
    `supabase/migrations/20260509000000_phase101_verify_connected_accounts_rls.sql` exists, mirrors `20260415113000` exactly with the comment header replaced. `supabase db reset --local` succeeds end-to-end. Re-running `supabase migration up --local` is a no-op. `pg_policy` query shows exactly 5 policies on `connected_accounts` with `(SELECT auth.uid()) = user_id` USING/WITH CHECK. Task 2's integration test PASSES. Commit `feat(101-01): add idempotent RLS verification migration for connected_accounts (AUTH-01)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 4: Wave-0 failing tests for the legacy-token backfill script</name>
  <files>tests/unit/scripts/__init__.py, tests/unit/scripts/test_migrate_connected_accounts_encryption.py</files>
  <behavior>
    Three tests, ALL FAILING initially because `scripts/migrate_connected_accounts_encryption.py` does not yet exist (`ImportError` is the expected failure mode). Tests describe the script's contract.

    1. **test_dry_run_does_not_write_anything**: Build a fake Supabase client with two seeded rows in `connected_accounts`: row A has `access_token="plaintext-A"` (legacy), row B has `access_token="gAAAAA-fernet-B"` (already encrypted). Patch `app.services.encryption.encrypt_secret` to be deterministic (`lambda v: f"enc:{v}"`) and `decrypt_secret` to raise `InvalidToken` on plaintext, return `"recovered-B"` on `gAAAAA-fernet-B`. Call `migrate_connected_accounts_encryption.run(client, dry_run=True)`. Assert: `result == {"total": 2, "already_encrypted": 1, "migrated": 0, "failed": 0}` (dry-run reports as if it migrated A but doesn't write). Assert NO `.update(...).execute()` was called on the fake table for either row.

    2. **test_apply_migrates_only_plaintext_rows**: Same seed. Call `run(client, dry_run=False)`. Assert: `result == {"total": 2, "already_encrypted": 1, "migrated": 1, "failed": 0}`. Assert exactly ONE `.update(...).execute()` was issued, targeting row A's `id`, with payload `{"access_token": "enc:plaintext-A"}` (and `refresh_token` updated similarly if seeded; for this test, leave `refresh_token=None` to keep the asserted payload minimal).

    3. **test_apply_is_idempotent_on_second_run**: Seed only row B (already-encrypted). Call `run(client, dry_run=False)`. Assert `result == {"total": 1, "already_encrypted": 1, "migrated": 0, "failed": 0}` AND no update calls. Then call `run(client, dry_run=False)` again. Same result, still no updates.

    Test infrastructure: import `from scripts.migrate_connected_accounts_encryption import run, is_already_fernet`. This import will FAIL initially — that IS the RED state.

    Commit message: `test(101-01): add failing tests for connected_accounts encryption backfill script`.
  </behavior>
  <action>
    1. Create empty `tests/unit/scripts/__init__.py` (if not already present).
    2. Create `tests/unit/scripts/test_migrate_connected_accounts_encryption.py`. Reuse the `_FakeClient`/`_FakeTable` pattern from `tests/unit/test_social_connector_security.py:12-99`, extended with: a `_FakeTable.update` method that records `(filter_kwargs, payload)` tuples in `client.update_calls` so tests can assert what was issued. The fake `.eq("id", row_id)` chain stores the filter; `.execute()` appends to `update_calls`.
    3. Stub `is_already_fernet(value: str) -> bool` and `run(client, *, dry_run: bool, verbose: bool = False) -> dict[str, int]` shape from imports — tests fail with `ImportError` (RED).
    4. `pytest.mark.asyncio` is NOT needed; the script is synchronous (mirrors how `IntegrationManager.store_credentials` interacts with Supabase via `.execute()`).
    5. Verify FAIL: `uv run pytest tests/unit/scripts/test_migrate_connected_accounts_encryption.py -x 2>&1 | tail -10` — expect `ImportError: cannot import name 'run'`.
    6. Lint: `uv run ruff check tests/unit/scripts/ --fix && uv run ruff format tests/unit/scripts/`.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/scripts/test_migrate_connected_accounts_encryption.py -x 2>&1 | tail -15</automated>
  </verify>
  <done>
    `tests/unit/scripts/test_migrate_connected_accounts_encryption.py` exists with 3 tests, ALL failing with `ImportError` (or `ModuleNotFoundError`). No production module yet exists. `ruff check` clean. Commit `test(101-01): add failing tests for connected_accounts encryption backfill script` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 5: Implement the backfill script (turn Task 4 GREEN)</name>
  <files>scripts/migrate_connected_accounts_encryption.py</files>
  <behavior>
    After this task, the 3 tests from Task 4 are GREEN. Module shape:

    ```python
    """One-time backfill: migrate plaintext access_token/refresh_token rows in
    public.connected_accounts to Fernet ciphertext. Idempotent.

    Usage:
        # Inspect what would change:
        uv run python scripts/migrate_connected_accounts_encryption.py --dry-run

        # Apply changes (requires SUPABASE_SERVICE_ROLE_KEY + ADMIN_ENCRYPTION_KEY):
        uv run python scripts/migrate_connected_accounts_encryption.py --apply
    """
    from __future__ import annotations

    import argparse
    import logging
    import sys
    from typing import Any

    from cryptography.fernet import InvalidToken

    from app.services.encryption import decrypt_secret, encrypt_secret
    from app.services.supabase import get_service_client

    logger = logging.getLogger(__name__)


    def is_already_fernet(value: str | None) -> bool:
        """Return True iff the value decrypts cleanly via decrypt_secret."""
        if not value:
            return True  # treat None as nothing-to-do
        try:
            decrypt_secret(value)
            return True
        except InvalidToken:
            return False
        except RuntimeError:
            # Encryption not configured — surface the failure to the caller
            raise


    def run(client: Any, *, dry_run: bool, verbose: bool = False) -> dict[str, int]:
        """Backfill all rows in connected_accounts. Returns counts dict."""
        result = client.table("connected_accounts").select("id, access_token, refresh_token").execute()
        rows = result.data or []
        stats = {"total": len(rows), "already_encrypted": 0, "migrated": 0, "failed": 0}

        for row in rows:
            access_plain = row.get("access_token")
            refresh_plain = row.get("refresh_token")
            access_already = is_already_fernet(access_plain)
            refresh_already = is_already_fernet(refresh_plain)

            if access_already and refresh_already:
                stats["already_encrypted"] += 1
                continue

            update_payload: dict[str, str] = {}
            if not access_already:
                update_payload["access_token"] = encrypt_secret(access_plain)
            if not refresh_already:
                update_payload["refresh_token"] = encrypt_secret(refresh_plain)

            if dry_run:
                stats["migrated"] += 1
                if verbose:
                    logger.info("[dry-run] would migrate row id=%s", row.get("id"))
                continue

            try:
                client.table("connected_accounts").update(update_payload).eq(
                    "id", row["id"]
                ).execute()
                stats["migrated"] += 1
            except Exception as exc:
                logger.warning("Failed to migrate row id=%s: %s", row.get("id"), exc)
                stats["failed"] += 1

        return stats


    def _main() -> int:
        parser = argparse.ArgumentParser(description="Encrypt legacy connected_accounts tokens")
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--dry-run", action="store_true", help="Report counts without writing")
        group.add_argument("--apply", action="store_true", help="Apply the migration")
        parser.add_argument("--verbose", "-v", action="store_true")
        args = parser.parse_args()

        logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
        client = get_service_client()
        stats = run(client, dry_run=args.dry_run, verbose=args.verbose)
        logger.info("Backfill complete: %s", stats)
        return 0 if stats["failed"] == 0 else 1


    if __name__ == "__main__":
        sys.exit(_main())
    ```

    Run `uv run pytest tests/unit/scripts/test_migrate_connected_accounts_encryption.py -x -v` — all 3 tests GREEN.

    Run `uv run ruff check scripts/migrate_connected_accounts_encryption.py --fix && uv run ruff format scripts/migrate_connected_accounts_encryption.py && uv run ty check scripts/migrate_connected_accounts_encryption.py`.

    Smoke (manual, NOT part of automated verify): `uv run python scripts/migrate_connected_accounts_encryption.py --dry-run` against a connected Supabase project — confirm output ends with a stats dict.

    Commit message: `feat(101-01): one-time encrypt-legacy-tokens backfill script for connected_accounts (AUTH-02)`.
  </behavior>
  <action>
    1. Create `scripts/` if it does not exist (likely does — check `ls scripts/`).
    2. Write the module with the contents above. Module-scope imports (no inline). Use `argparse` (stdlib) — do NOT add a new dep.
    3. The `is_already_fernet` shortcut for `None`/empty values returns `True` so the loop skips columns that legitimately have no token (`refresh_token` is optional per RESEARCH §AUTH-02).
    4. `RuntimeError` from `decrypt_secret` (raised when `ADMIN_ENCRYPTION_KEY` is not configured) propagates out of `is_already_fernet` → out of `run` — fail fast at process start, do not corrupt rows.
    5. Verify GREEN: `uv run pytest tests/unit/scripts/test_migrate_connected_accounts_encryption.py -x -v`.
    6. Lint + type-check: `uv run ruff check scripts/ --fix && uv run ruff format scripts/ && uv run ty check scripts/migrate_connected_accounts_encryption.py`.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/scripts/test_migrate_connected_accounts_encryption.py -x -v 2>&1 | tail -15 && uv run ruff check scripts/migrate_connected_accounts_encryption.py 2>&1 | tail -5</automated>
  </verify>
  <done>
    `scripts/migrate_connected_accounts_encryption.py` exists with `is_already_fernet`, `run`, and `_main` defined. All 3 tests in `tests/unit/scripts/test_migrate_connected_accounts_encryption.py` are GREEN. `ruff check` clean. `ty check` clean. The script is invokable via `uv run python scripts/migrate_connected_accounts_encryption.py --dry-run`. Commit `feat(101-01): one-time encrypt-legacy-tokens backfill script for connected_accounts (AUTH-02)` lands.
  </done>
</task>

</tasks>

<verification>
End-to-end:
1. `uv run pytest tests/unit/social/ tests/unit/scripts/ -x` — all 6 new unit tests GREEN; existing `tests/unit/test_social_connector_security.py` still GREEN.
2. `supabase db reset --local && uv run pytest tests/integration/test_connected_accounts_rls.py -x` — RLS integration test GREEN (or SKIP if Docker not available, which is acceptable for local dev).
3. `psql -c "SELECT polname FROM pg_policy WHERE polrelid='public.connected_accounts'::regclass ORDER BY polname"` returns exactly 5 rows: `Service Role manages all`, `Users can delete own connected accounts`, `Users can insert own connected accounts`, `Users can update own connected accounts`, `Users can view own connected accounts`.
4. `uv run python scripts/migrate_connected_accounts_encryption.py --dry-run` against the local stack returns a sensible stats dict (likely `{"total": 0, ...}` on a fresh local DB).

Manual UAT (deferred to phase-level UAT after 101-02 + 101-03 land):
- Run the script `--apply` against a staging Supabase project that has at least one legacy row, then re-run with `--dry-run` and confirm `migrated == 0`.
</verification>

<success_criteria>
- New SQL migration `20260509000000_phase101_verify_connected_accounts_rls.sql` exists, mirrors `20260415113000` shape, applies idempotently. Final RLS state on `public.connected_accounts` matches RESEARCH §Target State exactly.
- New integration test `tests/integration/test_connected_accounts_rls.py::test_user_a_cannot_read_user_b_connected_accounts` exists, PASSES against a local Supabase, SKIPS cleanly if not running.
- New unit test module `tests/unit/social/test_connector_encryption.py` covers (a) handle_callback writes Fernet ciphertext to both token columns, (b) get_access_token returns plaintext for legacy unencrypted rows, (c) get_access_token returns None for `gAAAAA`-prefixed but undecryptable values.
- `scripts/migrate_connected_accounts_encryption.py` exists with `--dry-run`/`--apply` CLI; `is_already_fernet` and `run` are unit-tested for the three branches: already-encrypted (skip), plaintext (encrypt + update), idempotent re-run (no-op).
- All new tests GREEN; existing `tests/unit/test_social_connector_security.py` still GREEN.
- `ruff check` and `ty check` clean for all new files.
- `app/social/connector.py` is UNCHANGED in this plan (encryption already correct; AUTH-02 production code path needs no edits).
</success_criteria>

<output>
After completion, create `.planning/phases/101-security-hardening/101-01-rls-fernet-data-migration-SUMMARY.md` documenting:
- The verification migration's relationship to `20260415113000` (idempotent re-assertion, both files retained)
- The decision to NOT modify `app/social/connector.py` (production code already implements AUTH-02 correctly)
- Test count delta (existing N → existing N + 3 unit + 3 script-unit + 1 integration)
- Backfill script invocation pattern for production deployment gate
</output>
