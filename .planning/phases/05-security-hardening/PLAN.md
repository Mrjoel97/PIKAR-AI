# Plan: Phase 5 - Security Hardening

**Objective:** Enforce the missing production security controls on live request paths without changing the product surface or weakening local development ergonomics.

## Scope Rules
- Preserve the existing structured API error contract.
- Keep development and test workflows functional, but make production misconfiguration fail fast.
- Prefer small middleware/helpers plus targeted regression tests over broad refactors.
- Fix token exposure by reducing logged sensitivity, not by hiding auth failures from operators.
- Reject oversized uploads before expensive extraction work starts.

## 1. Harden HTTP and Auth Boundaries
**Goal:** close SEC-01 through SEC-04 together because they all sit on the request/middleware/auth edge.

**Tasks:**
- Add a dedicated security-headers middleware that stamps `X-Content-Type-Options`, `X-Frame-Options`, and `Strict-Transport-Security` on every response.
- Update `app/fast_api_app.py` to reject `ALLOWED_ORIGINS=*` when `ENVIRONMENT` is production/prod.
- Remove token-fragment and verbose bearer-response logging from `app/app_utils/auth.py` while preserving enough signal for operators.
- Remove the rate limiter's unverified JWT fallback so bearer-token decoding only happens when `SUPABASE_JWT_SECRET` is configured.
- Extend product-truth/security tests to cover the new middleware and production CORS guard.

**Files:**
- `app/fast_api_app.py`
- `app/middleware/security_headers.py`
- `app/middleware/rate_limiter.py`
- `app/app_utils/auth.py`
- `tests/unit/test_product_truth_guards.py`
- `tests/unit/test_security_hardening.py`

## 2. Add File Upload Guardrails
**Goal:** close SEC-05 on the backend upload path.

**Tasks:**
- Add a configurable upload-size ceiling for `app/routers/files.py`.
- Validate declared content length when available and enforce the limit during streaming to disk.
- Return a 413 response with the existing structured error envelope when uploads exceed the configured ceiling.
- Document the upload-size env var in `app/.env.example`.
- Add regression coverage for oversized uploads.

**Files:**
- `app/routers/files.py`
- `app/.env.example`
- `tests/unit/test_security_hardening.py`

## 3. Verification
**Backend checks:**
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_product_truth_guards.py tests/unit/test_security_hardening.py -q`
- `uv run python -` with `py_compile.compile(...)` for the changed backend modules

**Manual/contract checks:**
- confirm `/health/live` responses include the new security headers
- confirm production reload fails fast when `ALLOWED_ORIGINS=*`
- confirm rate limiter no longer performs `verify_signature=False` JWT decoding
- confirm auth logs no longer contain raw or partial bearer token strings
- confirm `/upload` returns 413 for oversized payloads before extraction work begins
