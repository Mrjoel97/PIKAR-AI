"""Authentication utilities for Pikar-AI.

This module provides functions to verify Supabase JWT tokens and extract user identity,
ensuring secure backend communication.

Security Policy:
================
This module supports two authentication modes controlled by REQUIRE_STRICT_AUTH env var:

1. STRICT MODE (REQUIRE_STRICT_AUTH=1) - RECOMMENDED for production:
   - Invalid tokens are rejected with 401 Unauthorized
   - Missing tokens are rejected unless ALLOW_ANONYMOUS_CHAT=1
   - Token verification failures are treated as security events

2. PERMISSIVE MODE (default for development):
   - Invalid tokens log warnings but may allow anonymous access
   - Missing tokens allow anonymous access if ALLOW_ANONYMOUS_CHAT=1
   - Useful for development and testing

For production deployments, set:
- REQUIRE_STRICT_AUTH=1
- SUPABASE_JWT_SECRET=<your-jwt-secret>
- ALLOW_ANONYMOUS_CHAT=0 (or omit)
"""

import logging
import os
import secrets
import threading
import time

import jwt
from fastapi import Header, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.app_utils.env import get_stripped_env
from app.services.supabase import get_service_client
from supabase import Client

logger = logging.getLogger(__name__)
security = HTTPBearer()

# ---------------------------------------------------------------------------
# JWT in-process cache (DBSC-03)
# Caches validated user_data dicts keyed by raw token string.
# TTL: JWT_CACHE_TTL_SECONDS (default 60s).
# Prevents supabase.auth.get_user() on every authenticated request.
# SECURITY: Cache is keyed by the full token string (not just the sub claim).
# A revoked token remains cached until TTL expires — acceptable for 60s window.
# ---------------------------------------------------------------------------
_JWT_CACHE_TTL: int = int(os.environ.get("JWT_CACHE_TTL_SECONDS", "60"))
_token_cache: dict[str, tuple[dict, float]] = {}  # token -> (user_data, cached_at)
_token_cache_lock = threading.Lock()
_TOKEN_CACHE_MAX_SIZE = 10_000  # prevent unbounded growth


def _cache_get(token: str) -> dict | None:
    """Return cached user_data if still within TTL, else None."""
    with _token_cache_lock:
        entry = _token_cache.get(token)
        if entry is None:
            return None
        user_data, cached_at = entry
        if time.monotonic() - cached_at > _JWT_CACHE_TTL:
            del _token_cache[token]
            return None
        return user_data


def _cache_set(token: str, user_data: dict) -> None:
    """Store user_data in cache, evicting oldest entry if at capacity."""
    with _token_cache_lock:
        if len(_token_cache) >= _TOKEN_CACHE_MAX_SIZE:
            oldest_key = next(iter(_token_cache))
            del _token_cache[oldest_key]
        _token_cache[token] = (user_data, time.monotonic())


def _cache_invalidate(token: str) -> None:
    """Remove a specific token from cache (e.g., on logout)."""
    with _token_cache_lock:
        _token_cache.pop(token, None)


def _is_strict_auth_mode() -> bool:
    """Check if strict authentication mode is enabled."""
    return os.environ.get("REQUIRE_STRICT_AUTH", "0") == "1"


def get_supabase_client() -> Client:
    """Get a Supabase client instance from centralized service."""
    return get_service_client()


def _get_jwt_secret() -> str | None:
    """Get the JWT secret for token verification."""
    return get_stripped_env("SUPABASE_JWT_SECRET")


def _get_token_algorithm(token: str) -> str | None:
    """Return the JWT ``alg`` header without verifying the token.

    Supabase projects may now issue asymmetric tokens such as ``ES256``.
    Our local fast-path verifier only supports legacy shared-secret ``HS256``
    tokens. For any other algorithm we skip local signature verification and
    fall back to Supabase's authoritative ``auth.get_user()`` check.
    """
    try:
        header = jwt.get_unverified_header(token)
    except Exception:
        return None
    alg = header.get("alg")
    return alg.upper() if isinstance(alg, str) else None


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """Verify the Supabase JWT token.

    Validates the JWT signature locally first (fast, CPU-only), then
    checks the in-process LRU cache. Only calls supabase.auth.get_user()
    on a cache miss, reducing network round-trips by ~95% for active users.
    """
    token = credentials.credentials

    # Step 1: Fast local JWT validation (no network call)
    jwt_secret = _get_jwt_secret()
    token_alg = _get_token_algorithm(token)
    if jwt_secret and token_alg in (None, "HS256"):
        try:
            decoded = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False, "verify_exp": True},
            )
        except jwt.InvalidTokenError as e:
            logger.warning("JWT signature verification failed: %s", e)
            raise HTTPException(
                status_code=401, detail="JWT signature verification failed"
            ) from e
    else:
        if token_alg and token_alg != "HS256":
            logger.debug(
                "Skipping local JWT verification for token signed with unsupported alg %s",
                token_alg,
            )
        decoded = None

    # Step 2: Cache lookup — skip Supabase call if token recently validated
    cached = _cache_get(token)
    if cached is not None:
        if decoded and "jwt_claims" not in cached:
            cached = {**cached, "jwt_claims": decoded}
        return cached

    # Step 3: Supabase call for full user data (cache miss only)
    supabase = get_supabase_client()
    try:
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            logger.warning("Invalid token provided")
            raise HTTPException(
                status_code=401, detail="Invalid authentication credentials"
            )

        user_metadata = user_response.user.user_metadata
        app_metadata = getattr(user_response.user, "app_metadata", None)
        if isinstance(user_metadata, dict):
            metadata = {**user_metadata, "app_metadata": app_metadata or {}}
        else:
            metadata = {
                "user_metadata": user_metadata,
                "app_metadata": app_metadata or {},
            }

        user_data = {
            "id": user_response.user.id,
            "email": user_response.user.email,
            "metadata": metadata,
            "role": user_response.user.role,
        }

        if decoded:
            user_data["jwt_claims"] = decoded

        # Store in cache for subsequent requests
        _cache_set(token, user_data)
        return user_data

    except HTTPException:
        raise
    except Exception:
        logger.error("Token verification failed")
        raise HTTPException(status_code=401, detail="Could not validate credentials")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """Resolve the authenticated user through the shared token verifier."""
    return await verify_token(credentials)


async def get_current_user_id(current_user: dict) -> str:
    """Extract the current authenticated user id from shared auth payloads."""
    user_id = current_user.get("id") if isinstance(current_user, dict) else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return user_id


def get_user_id_from_token(token: str) -> str | None:
    """Extract user ID from a raw JWT token string with verification."""
    jwt_secret = _get_jwt_secret()
    if not jwt_secret:
        logger.warning("JWT_SECRET not configured, cannot verify token locally")
        return None

    token_alg = _get_token_algorithm(token)
    if token_alg and token_alg != "HS256":
        logger.debug(
            "Skipping local user-id extraction for token signed with unsupported alg %s",
            token_alg,
        )
        return None

    try:
        decoded = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return decoded.get("sub")
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid token provided for local user-id extraction")
        return None


def get_user_id_from_bearer_token(token: str) -> str | None:
    """Verify the Bearer token with Supabase and return the user ID."""
    if not token or not token.strip():
        if _is_strict_auth_mode():
            logger.warning("Strict auth mode: rejecting missing token")
            raise HTTPException(status_code=401, detail="Authentication required")
        return None

    try:
        supabase = get_supabase_client()
        logger.info("Validating bearer token with Supabase")
        user_response = supabase.auth.get_user(token.strip())
        if user_response and user_response.user:
            logger.info(
                "Bearer token validation succeeded for user %s", user_response.user.id
            )
            return user_response.user.id

        logger.warning("Bearer token validation returned no user")
        if _is_strict_auth_mode():
            logger.warning("Strict auth mode: rejecting invalid token")
            raise HTTPException(
                status_code=401, detail="Invalid authentication credentials"
            )

    except HTTPException:
        raise
    except (jwt.InvalidTokenError, Exception) as e:
        # Distinguish auth errors from infrastructure errors
        error_type = type(e).__name__
        if "connect" in error_type.lower() or "timeout" in error_type.lower():
            logger.error("Auth service unavailable: %s", e)
            raise HTTPException(
                status_code=503, detail="Authentication service unavailable"
            )
        logger.warning("Bearer token validation failed: %s (%s)", e, error_type)
        if _is_strict_auth_mode():
            raise HTTPException(status_code=401, detail="Authentication failed")

    return None


def resolve_request_user_id(
    request: Request,
    *,
    allow_header_fallback: bool = True,
) -> str | None:
    """Resolve a request user id, preferring bearer auth over spoofable headers."""
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        bearer_token = authorization[7:].strip()
        if bearer_token:
            user_id = get_user_id_from_token(bearer_token)
            if user_id is not None:
                return user_id
        if not allow_header_fallback:
            return None

    if allow_header_fallback:
        header_user_id = request.headers.get("x-user-id") or request.headers.get(
            "user-id"
        )
        if header_user_id:
            return header_user_id
        state_user_id = getattr(request.state, "user_id", None)
        if state_user_id:
            return state_user_id

    return None


def verify_token_fast(token: str) -> dict | None:
    """Fast token verification using JWT without Supabase call."""
    jwt_secret = _get_jwt_secret()
    if not jwt_secret:
        logger.warning("JWT_SECRET not configured for fast verification")
        return None

    token_alg = _get_token_algorithm(token)
    if token_alg and token_alg != "HS256":
        logger.debug(
            "Skipping fast JWT verification for token signed with unsupported alg %s",
            token_alg,
        )
        return None

    try:
        decoded = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={
                "verify_aud": False,
                "verify_exp": True,
                "verify_iat": True,
            },
        )
        return decoded
    except jwt.ExpiredSignatureError:
        logger.debug("Token has expired")
        return None
    except jwt.InvalidTokenError:
        logger.debug("Invalid token for fast verification")
        return None


def verify_service_auth(
    x_service_secret: str = Header(None, alias="X-Service-Secret"),
) -> bool:
    """Verify internal service-to-service authentication header."""
    expected_secret = get_stripped_env("WORKFLOW_SERVICE_SECRET")
    if not expected_secret:
        logger.warning(
            "Service authentication is not configured: WORKFLOW_SERVICE_SECRET is missing"
        )
        raise HTTPException(
            status_code=500, detail="Service authentication not configured"
        )

    provided_secret = x_service_secret or ""
    if not secrets.compare_digest(provided_secret, expected_secret):
        logger.warning(
            "Unauthorized service request received for workflow service endpoint"
        )
        raise HTTPException(status_code=401, detail="Unauthorized service request")

    return True
