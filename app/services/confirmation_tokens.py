# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Confirmation token service for admin action approvals.

Stores and atomically consumes UUID confirmation tokens in Redis with a
5-minute TTL. Uses GETDEL for atomic single-consumption so that tokens
cannot be replayed after the first use.
"""

import json
import logging

from app.services.cache import get_cache_service

logger = logging.getLogger(__name__)

# Redis key prefix for confirmation tokens
_KEY_PREFIX = "admin:confirm:"

# Token TTL in seconds (5 minutes)
_TOKEN_TTL = 300


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
    try:
        await redis_client.set(key, payload, ex=_TOKEN_TTL)
        logger.debug("Stored confirmation token %s (TTL=%ss)", token, _TOKEN_TTL)
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
