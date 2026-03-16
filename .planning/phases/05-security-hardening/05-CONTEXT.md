# Phase 5 Context: Security Hardening

## Why This Phase Exists

Phase 4 aligned the frontend and backend contracts, but the application still had several production-security gaps on live request paths. The highest-risk issues were around HTTP hardening, permissive CORS behavior, unverified JWT decoding in the rate limiter, token-adjacent logging in auth utilities, and unrestricted file upload size on the `/upload` endpoint.

## Requirement Mapping

- SEC-01: Security headers middleware added: `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`
- SEC-02: Rate limiter JWT decode requires valid secret (no unverified fallback)
- SEC-03: Token logging removed from `auth.py` (partial token exposure)
- SEC-04: CORS wildcard explicitly rejected in production environment
- SEC-05: File upload size validation added to files router

## What The Audit Found

1. HTTP responses lacked a dedicated security-header middleware.
   - `app/fast_api_app.py` configured CORS and request logging, but no middleware stamped the baseline security headers required by SEC-01.

2. Production CORS could still degrade to wildcard behavior.
   - `app/fast_api_app.py` accepted `ALLOWED_ORIGINS=*` and merely disabled credentials, which is safer than credentialed wildcard CORS but still weaker than the roadmap requirement for production.

3. The rate limiter still fell back to unverified JWT decoding.
   - `app/middleware/rate_limiter.py` decoded bearer tokens with `verify_signature=False` when `SUPABASE_JWT_SECRET` was absent, directly violating SEC-02.

4. Auth logging still exposed token-adjacent material.
   - `app/app_utils/auth.py` logged token fragments and verbose Supabase responses on bearer-token validation paths, which is the exact SEC-03 concern.

5. The files router copied uploads to disk without enforcing a size ceiling.
   - `app/routers/files.py` streamed any multipart payload to a temporary file before parsing, with only content truncation after extraction. That left the request path without a protective 413 guard.

## Files In Scope

- `app/fast_api_app.py`
- `app/middleware/security_headers.py`
- `app/middleware/rate_limiter.py`
- `app/app_utils/auth.py`
- `app/routers/files.py`
- `app/.env.example`
- `tests/unit/test_product_truth_guards.py`
- `tests/unit/test_security_hardening.py`

## Planning Notes

- Preserve the structured error envelope already defined in `fast_api_app.py` rather than returning ad hoc security errors.
- Keep CORS safe for local/test workflows while making production wildcard configuration fail fast.
- Treat rate limiting as a non-blocking path, but never at the cost of unverified JWT parsing.
- Reject oversized uploads before expensive parsing/extraction work begins.
- Add narrow regression coverage for each hardening seam so the roadmap can mark SEC-01 through SEC-05 complete with evidence.
