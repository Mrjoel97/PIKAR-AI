# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

import logging
import os
import time
import time as _time

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.app_utils.env import get_stripped_env
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
UNLIMITED_TESTING_LIMIT = "100000/minute"

# In-memory cache for persona lookups (L1 — fallback when Redis unavailable)
# TTL is handled by _cache_ttl tracking
_persona_cache: dict = {}
_cache_ttl_seconds = 300  # 5 minutes

# Redis L2 key prefix — shared across all replicas (RDSC-04 namespace)
_REDIS_PERSONA_PREFIX = "pikar:persona:"

# ---------------------------------------------------------------------------
# In-process rate limit fallback — used when Redis circuit breaker is open.
# Uses a fixed-window counter per user. Less accurate than Redis sliding window
# (no cross-replica sharing), but prevents unlimited access during Redis outages.
# ---------------------------------------------------------------------------
_fallback_counters: dict[
    str, tuple[int, int]
] = {}  # key "{user_id}:{window_start}" -> (count, window_start)
_FALLBACK_ACTIVE = False  # Track if we've already logged the CRITICAL alert this window


def _as_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def is_rate_limit_override_enabled() -> bool:
    """Return True when persona-specific throttles should be bypassed for testing."""
    return _as_bool(os.getenv("ALLOW_UNLIMITED_TESTING")) or _as_bool(
        os.getenv("ALLOW_ALL_FEATURES_FOR_TESTING")
    )


def get_testing_override_limit() -> str:
    return get_stripped_env("UNLIMITED_TESTING_RATE_LIMIT", UNLIMITED_TESTING_LIMIT)


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


async def _get_cached_persona_async(user_id: str) -> str | None:
    """Get persona: L1 (local dict) then L2 (Redis).

    Checks the fast in-memory cache first. On a local miss, queries Redis
    (shared across all replicas). A Redis hit backfills L1 for subsequent
    sync reads in ``get_user_persona_limit``.
    """
    # L1: local in-memory check (fast, no await)
    local = _get_cached_persona(user_id)
    if local:
        return local

    # L2: Redis check (shared across replicas)
    try:
        from app.services.cache import get_cache_service

        client = await get_cache_service()._ensure_connection()
        if client:
            persona = await client.get(f"{_REDIS_PERSONA_PREFIX}{user_id}")
            if persona:
                persona_str = (
                    persona.decode() if isinstance(persona, bytes) else str(persona)
                )
                # Backfill L1 cache so sync path sees it next time
                _persona_cache[user_id] = (persona_str, time.time())
                return persona_str
    except Exception:
        logger.debug("Redis persona cache read failed, falling back to local only")

    return None


async def _set_cached_persona_async(user_id: str, persona: str) -> None:
    """Cache persona in Redis (shared across replicas) + local memory.

    Writes to both L1 (in-memory dict) and L2 (Redis SETEX with TTL).
    If Redis is unavailable, the local cache is still updated.
    """
    # L1: local cache (same as sync version)
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

    # L2: Redis cache (shared across replicas)
    try:
        from app.services.cache import get_cache_service

        client = await get_cache_service()._ensure_connection()
        if client:
            await client.setex(
                f"{_REDIS_PERSONA_PREFIX}{user_id}",
                _cache_ttl_seconds,
                persona,
            )
    except Exception:
        logger.debug("Redis persona cache write failed, local cache still active")


async def warm_persona_cache(user_id: str, persona: str) -> None:
    """Warm the persona cache from an async context (SSE endpoint / middleware).

    Call this when the user's persona is resolved from the database so that
    subsequent sync reads in ``get_user_persona_limit`` hit L1, and other
    replicas can read from Redis L2.
    """
    await _set_cached_persona_async(user_id, persona)


def get_user_persona_limit(request: Request = None) -> str:
    """
    Determines the rate limit based on the user's persona.
    Uses in-memory caching to reduce database queries.
    """
    if is_rate_limit_override_enabled():
        return get_testing_override_limit()

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
        jwt_secret = get_stripped_env("SUPABASE_JWT_SECRET")
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


def _in_process_rate_check(
    user_id: str,
    limit: int,
    window_seconds: int = 60,
) -> tuple[bool, int, int, int]:
    """In-process fixed-window rate check — fallback when Redis is unavailable.

    Less accurate than Redis sliding window (not shared across replicas),
    but ensures no single user can make unlimited calls during Redis outages.

    Returns (allowed, limit, remaining, reset_at_unix).
    """
    now = int(time.time())
    window_start = (now // window_seconds) * window_seconds
    reset_at = window_start + window_seconds
    key = f"{user_id}:{window_start}"

    entry = _fallback_counters.get(key)
    if entry is None:
        # Clean expired entries (older than 2 windows) to prevent unbounded growth
        cutoff = window_start - window_seconds
        expired = [k for k in _fallback_counters if int(k.rsplit(":", 1)[-1]) < cutoff]
        for k in expired:
            del _fallback_counters[k]
        _fallback_counters[key] = (1, window_start)
        return True, limit, limit - 1, reset_at

    count, _ = entry
    count += 1
    _fallback_counters[key] = (count, window_start)
    remaining = max(0, limit - count)
    allowed = count <= limit
    return allowed, limit, remaining, reset_at


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
    Falls back to in-process fixed-window limiter when the Redis circuit
    breaker is open — emitting a CRITICAL alert on first activation.
    Fails open (True) only for transient connection blips when the CB is closed.
    This is the AUTHORITATIVE distributed enforcement layer — called from
    RateLimitHeaderMiddleware for ALL requests, not just slowapi-decorated ones.
    """
    global _FALLBACK_ACTIVE

    from app.services.cache import REDIS_KEY_PREFIXES, get_cache_service

    cache = get_cache_service()

    # Check Redis circuit breaker state BEFORE attempting Redis operations.
    # When the breaker is open or half-open, skip Redis entirely and use the
    # in-process fallback to avoid hammering a failing service.
    cb_state = cache.get_circuit_breaker_state()
    if cb_state["state"] != "closed":
        if not _FALLBACK_ACTIVE:
            logger.critical(
                "Redis circuit breaker is %s — rate limiting falling back to in-process "
                "limiter. Cross-replica rate limits will NOT be enforced until Redis recovers.",
                cb_state["state"],
            )
            _FALLBACK_ACTIVE = True
        return _in_process_rate_check(user_id, limit, window_seconds)

    prefix = REDIS_KEY_PREFIXES["rate_limit"]
    now = int(_time.time())
    window_start = (now // window_seconds) * window_seconds
    reset_at = window_start + window_seconds
    key = f"{prefix}api:{user_id}:{window_start}"

    try:
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

        # Redis recovered — reset fallback flag and notify
        if _FALLBACK_ACTIVE:
            logger.info("Redis recovered — resuming distributed rate limiting")
            _FALLBACK_ACTIVE = False

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
