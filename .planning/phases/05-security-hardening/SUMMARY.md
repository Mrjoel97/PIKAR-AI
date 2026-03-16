# Phase 5 Summary: Security Hardening

## Outcome

Completed the Phase 5 security-hardening plan. HTTP responses now carry the baseline security headers, production wildcard CORS is rejected at startup, the rate limiter no longer falls back to unverified JWT decoding, auth logging no longer exposes token fragments, and the files router rejects oversized uploads with a 413 before parsing/extraction work begins.

## What Changed

- Added `app/middleware/security_headers.py` and registered it in `app/fast_api_app.py` so responses now include:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- Tightened CORS startup behavior in `app/fast_api_app.py` so `ALLOWED_ORIGINS=*` raises immediately in production/prod instead of silently downgrading to a weaker-but-still-permissive configuration.
- Updated `app/middleware/rate_limiter.py` so bearer-token persona lookup only uses verified JWT decoding when `SUPABASE_JWT_SECRET` is configured.
- Sanitized auth logging in `app/app_utils/auth.py` by removing token-fragment logging and verbose response/error payload logging from bearer-token validation paths.
- Added upload-size enforcement in `app/routers/files.py`, including declared-size checks, streaming byte-count enforcement, and a configurable `MAX_UPLOAD_SIZE_BYTES` ceiling documented in `app/.env.example`.
- Added regression coverage in:
  - `tests/unit/test_product_truth_guards.py`
  - `tests/unit/test_security_hardening.py`

## Verification

Passed checks:
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_product_truth_guards.py tests/unit/test_security_hardening.py -q`
- `uv run python -` with `py_compile.compile(...)` for:
  - `app/middleware/security_headers.py`
  - `app/middleware/rate_limiter.py`
  - `app/app_utils/auth.py`
  - `app/routers/files.py`
  - `app/fast_api_app.py`
  - `tests/unit/test_product_truth_guards.py`
  - `tests/unit/test_security_hardening.py`

Notes:
- The targeted pytest slice passed with two unrelated deprecation warnings from `datetime.utcnow()` in existing health/error helpers.
- Phase 5 verification still needed unrestricted pytest because this workstation's sandboxed `.venv` access remains permission-sensitive.

## Follow-up

- Phase 6 planning should focus on configuration and deployment alignment next.
- Refresh `uv.lock` in an environment with full `uv lock` support.
- Upgrade the local Supabase CLI so future database verification can stay on the supported local command path.
