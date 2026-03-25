# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

import logging
import os
import time
import time as _time

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.services.supabase_client import get_service_client
from supabase import Client

logger = logging.getLogger(__name__)

# Persona to rate limit mapping
PERSONA_LIMITS = {
    "solopreneur": "10/minute",
    "startup": "30/minute",
    "sme": "60/minute",
    "enterprise": "120/minute",
}
DEFAULT_LIMIT = "10/minute"

# In-memory cache for persona lookups (fallback when Redis unavailable)
# TTL is handled by _cache_ttl tracking
_persona_cache: dict = {}
_cache_ttl_seconds = 300  # 5 minutes


def get_supabase_client() -> Client | None:
    try:
        return get_service_client()
    except Exception:
        logger.warning("Supabase credentials missing in rate limiter")
        return None


def _get_cached_persona(user_id: str) -> str | None:
    """Get persona from in-memory cache with TTL check."""
    cache_entry = _persona_cache.get(user_id)
    if cache_entry:
        persona, timestamp = cache_entry
        if time.time() - timestamp < _cache_ttl_seconds:
            return persona
        # Expired, remove from cache
        del _persona_cache[user_id]
    return None


def _set_cached_persona(user_id: str, persona: str) -> None:
    """Cache persona in memory with timestamp."""
    _persona_cache[user_id] = (persona, time.time())
    # Cleanup old entries if cache grows too large
    if len(_persona_cache) > 1000:
        current_time = time.time()
        expired_keys = [
            key
            for key, value in _persona_cache.items()
            if current_time - value[1] > _cache_ttl_seconds
        ]
        for key in expired_keys:
            del _persona_cache[key]


def get_user_persona_limit(request: Request = None) -> str:
    """
    Determines the rate limit based on the user's persona.
    Uses in-memory caching to reduce database queries.
    """
    if not request:
        return DEFAULT_LIMIT

    # 0. Fast path: persona cookie/header set by frontend proxy (avoids backend DB roundtrip)
    try:
        cookie_persona = request.cookies.get("x-pikar-persona")
        if cookie_persona and cookie_persona != "none":
            persona = str(cookie_persona).strip().lower()
            return PERSONA_LIMITS.get(persona, DEFAULT_LIMIT)
    except Exception:
        pass

    header_persona = request.headers.get("x-pikar-persona")
    if header_persona:
        persona = str(header_persona).strip().lower()
        if persona and persona != "none":
            return PERSONA_LIMITS.get(persona, DEFAULT_LIMIT)

    # 1. Extract User ID from Token
    user_id = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        if jwt_secret:
            try:
                import jwt

                decoded = jwt.decode(
                    token,
                    jwt_secret,
                    algorithms=["HS256"],
                    options={"verify_aud": False},
                )
                sub = decoded.get("sub")
                if isinstance(sub, str) and sub:
                    user_id = sub
            except Exception as exc:
                # Token might be invalid/expired or jwt unavailable. Fallback to default/cached.
                logger.debug("Rate limiter auth check failed: %s", exc)
        else:
            logger.debug(
                "Rate limiter skipped bearer token decoding because SUPABASE_JWT_SECRET is not configured"
            )

    if not user_id:
        return DEFAULT_LIMIT

    # 2. Check cache first
    cached_persona = _get_cached_persona(user_id)
    if cached_persona:
        return PERSONA_LIMITS.get(cached_persona, DEFAULT_LIMIT)

    # 3. Avoid DB/network lookups here to keep request path non-blocking.
    # If persona is not already cached, fall back to the default limit.
    return DEFAULT_LIMIT


# Initialize Limiter
limiter = Limiter(key_func=get_remote_address)


def _parse_limit_int(limit_str: str) -> int:
    """Parse '10/minute' → 10."""
    try:
        return int(limit_str.split("/")[0])
    except (ValueError, IndexError):
        return 10


async def redis_sliding_window_check(
    user_id: str,
    limit: int,
    window_seconds: int = 60,
) -> tuple[bool, int, int, int]:
    """Check rate limit using Redis sliding window.

    Returns (allowed, limit, remaining, reset_at_unix).
    Fails open (True) if Redis is unavailable.
    This is the AUTHORITATIVE distributed enforcement layer — called from
    RateLimitHeaderMiddleware for ALL requests, not just slowapi-decorated ones.
    """
    from app.services.cache import REDIS_KEY_PREFIXES, get_cache_service

    prefix = REDIS_KEY_PREFIXES["rate_limit"]
    now = int(_time.time())
    window_start = (now // window_seconds) * window_seconds
    reset_at = window_start + window_seconds
    key = f"{prefix}api:{user_id}:{window_start}"

    try:
        cache = get_cache_service()
        client = await cache._ensure_connection()
        if client is None:
            logger.warning(
                "Redis unavailable in rate limiter, failing open for user %s", user_id
            )
            return True, limit, limit, reset_at

        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds + 5)  # +5s buffer for clock skew
        results = await pipe.execute()
        count = results[0]
        remaining = max(0, limit - count)
        allowed = count <= limit
        return allowed, limit, remaining, reset_at
    except Exception as exc:
        logger.warning(
            "Rate limiter Redis error for user %s: %s — failing open", user_id, exc
        )
        return True, limit, limit, reset_at


def build_rate_limit_headers(
    limit: int, remaining: int, reset_at: int
) -> dict[str, str]:
    """Build standard rate limit response headers."""
    retry_after = max(0, reset_at - int(_time.time()))
    return {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(remaining),
        "Retry-After": str(retry_after),
    }
