# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Confirmation token service for admin action approvals.

Stores and atomically consumes UUID confirmation tokens in Redis. Uses
GETDEL for atomic single-consumption so a token cannot be replayed after
the first use. TTL defaults to 15 minutes — short enough that abandoned
tokens age out, long enough that an admin can read a refund summary or
permission diff and still confirm without re-triggering the flow.
"""

import json
import logging
import os

from app.services.cache import get_cache_service

logger = logging.getLogger(__name__)

# Redis key prefix for confirmation tokens
_KEY_PREFIX = "admin:confirm:"

# Default token TTL in seconds. Override with ADMIN_CONFIRMATION_TTL_SECONDS.
# 15 minutes (was 5 — too short to read a refund summary and double-check
# before approving). Bounded to [60, 3600] in _get_token_ttl().
_DEFAULT_TOKEN_TTL = 900
_MIN_TTL = 60
_MAX_TTL = 3600


def _get_token_ttl() -> int:
    """Return the configured confirmation token TTL, clamped to [60, 3600]s.

    Read at call time so ADMIN_CONFIRMATION_TTL_SECONDS can be tuned via
    Cloud Run env vars without a code change. Bounds prevent footguns: a
    sub-60s TTL would race the user's read-time; a >1h TTL keeps stale
    confirmation links hot for too long.
    """
    raw = os.environ.get("ADMIN_CONFIRMATION_TTL_SECONDS")
    if not raw:
        return _DEFAULT_TOKEN_TTL
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "Invalid ADMIN_CONFIRMATION_TTL_SECONDS=%r — falling back to %ds",
            raw,
            _DEFAULT_TOKEN_TTL,
        )
        return _DEFAULT_TOKEN_TTL
    if value < _MIN_TTL:
        logger.warning(
            "ADMIN_CONFIRMATION_TTL_SECONDS=%d below minimum — clamping to %ds",
            value,
            _MIN_TTL,
        )
        return _MIN_TTL
    if value > _MAX_TTL:
        logger.warning(
            "ADMIN_CONFIRMATION_TTL_SECONDS=%d above maximum — clamping to %ds",
            value,
            _MAX_TTL,
        )
        return _MAX_TTL
    return value


async def store_confirmation_token(
    token: str,
    action_details: dict,
    admin_user_id: str,
) -> bool:
    """Store a confirmation token in Redis with a 5-minute TTL.

    Args:
        token: UUID string identifying the token.
        action_details: Dict describing the action awaiting confirmation.
        admin_user_id: The admin user who triggered the action.

    Returns:
        True if stored successfully, False if Redis is unavailable.
    """
    cache = get_cache_service()
    redis_client = await cache._get_redis()
    if redis_client is None:
        logger.warning("Redis unavailable; confirmation token not stored for %s", token)
        return False

    payload = json.dumps(
        {"action_details": action_details, "admin_user_id": admin_user_id}
    )
    key = f"{_KEY_PREFIX}{token}"
    ttl = _get_token_ttl()
    try:
        await redis_client.set(key, payload, ex=ttl)
        logger.debug("Stored confirmation token %s (TTL=%ds)", token, ttl)
        return True
    except Exception as exc:
        logger.error("Failed to store confirmation token %s: %s", token, exc)
        return False


async def consume_confirmation_token(token: str) -> dict | None:
    """Consume a confirmation token atomically.

    Uses Redis GETDEL to retrieve and delete the token in a single atomic
    operation, ensuring the token cannot be used more than once.

    Args:
        token: UUID string of the token to consume.

    Returns:
        The stored payload dict if the token was valid and not yet consumed,
        or None if the token is expired, already consumed, or Redis is
        unavailable.
    """
    cache = get_cache_service()
    redis_client = await cache._get_redis()
    if redis_client is None:
        logger.warning("Redis unavailable; cannot consume confirmation token %s", token)
        return None

    key = f"{_KEY_PREFIX}{token}"
    try:
        raw = await redis_client.getdel(key)
        if raw is None:
            logger.debug("Confirmation token %s not found (expired or consumed)", token)
            return None
        payload: dict = json.loads(raw)
        logger.debug("Consumed confirmation token %s", token)
        return payload
    except Exception as exc:
        logger.error("Failed to consume confirmation token %s: %s", token, exc)
        return None
