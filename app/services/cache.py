"""Cache service for Pikar AI using Redis.

This module provides async Redis caching operations with connection pooling,
user config caching, session caching, and persona caching.
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Redis key namespace constants (RDSC-04)
# All keys written to Redis MUST use one of these prefixes.
# ---------------------------------------------------------------------------
REDIS_KEY_PREFIXES: dict[str, str] = {
    "user_config": "pikar:user_config:",
    "session_meta": "pikar:session:",
    "persona": "pikar:persona:",
    "feature_flag": "pikar:flag:",
    "rate_limit": "pikar:rate:",
    "sse_conn": "pikar:sse:",
    "confirmation": "pikar:confirm:",
    "jwt_cache": "pikar:jwt:",
    "integration": "pikar:integration:",
    "agent_perm": "pikar:agent_perm:",
}


def with_circuit_breaker(func: Callable) -> Callable:
    """Decorator to apply circuit breaker logic to CacheService methods."""

    @functools.wraps(func)
    async def wrapper(self: CacheService, *args, **kwargs):
        if not await self._should_allow_request():
            if func.__name__.startswith("get_"):
                return CacheResult.from_error("Circuit breaker is open")
            return False

        try:
            _start = time.time()
            result = await func(self, *args, **kwargs)
            await self._track_latency((time.time() - _start) * 1000)
            if result is not False or not func.__name__.startswith("set_"):
                await self._record_success()
            return result
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.warning("Redis connection error in %s: %s", func.__name__, exc)
            await self._record_failure()
            if func.__name__.startswith("get_"):
                return CacheResult.from_error(f"Connection error: {exc}")
            return False
        except Exception as exc:
            logger.error("Unexpected error in %s: %s", func.__name__, exc)
            if func.__name__.startswith("get_"):
                return CacheResult.from_error(str(exc))
            return False

    return wrapper


@dataclass
class CacheResult:
    """Result of a cache operation that distinguishes between different outcomes."""

    found: bool = False
    value: Any = None
    error: str | None = None
    is_miss: bool = False
    is_error: bool = False

    @classmethod
    def hit(cls, value: Any) -> CacheResult:
        return cls(found=True, value=value, is_miss=False, is_error=False)

    @classmethod
    def miss(cls) -> CacheResult:
        return cls(found=False, value=None, is_miss=True, is_error=False)

    @classmethod
    def from_error(cls, error_message: str) -> CacheResult:
        return cls(
            found=False, value=None, error=error_message, is_miss=False, is_error=True
        )


class CacheService:
    """Async service for handling Redis caching operations with connection pooling.

    Implements circuit breaker pattern for resilience:
    - Tracks consecutive failures
    - Opens circuit after threshold is reached
    - Half-open state allows test requests
    - Automatically recovers after recovery timeout
    """

    _instance: CacheService | None = None
    _instance_lock = threading.RLock()

    def __new__(cls) -> CacheService:
        """Singleton pattern."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the Redis connection pool and circuit breaker."""
        if self._initialized:
            return

        with self.__class__._instance_lock:
            if self._initialized:
                return

            self._redis: redis.Redis | None = None
            self._connected = False
            self._redis_url = os.getenv("REDIS_URL")
            self._host = os.getenv("REDIS_HOST", "localhost")
            self._port = int(os.getenv("REDIS_PORT", 6379))
            self._password = os.getenv("REDIS_PASSWORD")
            self._db = int(os.getenv("REDIS_DB", 0))
            self._max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "200"))
            self._ssl = os.getenv("REDIS_SSL", "").lower() in ("1", "true", "yes")
            self._connection_lock: asyncio.Lock | None = None
            self._connection_lock_initialized = False

            self.TTL_USER_CONFIG = 3600
            self.TTL_SESSION_META = 1800
            self.TTL_PERSONA = 7200

            self._circuit_breaker_failure_threshold = int(
                os.getenv("REDIS_CB_FAILURE_THRESHOLD", 5)
            )
            self._circuit_breaker_recovery_timeout = int(
                os.getenv("REDIS_CB_RECOVERY_TIMEOUT", 30)
            )
            self._circuit_breaker_state = "closed"
            self._circuit_breaker_failures = 0
            self._circuit_breaker_last_failure_time: float | None = None
            self._cb_lock: asyncio.Lock | None = None
            self._cb_lock_initialized = False

            # Latency tracking ring buffer — last 100 operation durations in ms
            self._latency_buffer: list[float] = []
            self._latency_buffer_max = 100
            self._latency_lock: asyncio.Lock | None = None
            self._latency_lock_initialized = False

            self._initialized = True

    async def _get_connection_lock(self) -> asyncio.Lock:
        if not self._connection_lock_initialized:
            self._connection_lock = asyncio.Lock()
            self._connection_lock_initialized = True
        return self._connection_lock

    async def _get_cb_lock(self) -> asyncio.Lock:
        if not self._cb_lock_initialized:
            self._cb_lock = asyncio.Lock()
            self._cb_lock_initialized = True
        return self._cb_lock

    async def _get_latency_lock(self) -> asyncio.Lock:
        if not self._latency_lock_initialized:
            self._latency_lock = asyncio.Lock()
            self._latency_lock_initialized = True
        return self._latency_lock

    async def _track_latency(self, elapsed_ms: float) -> None:
        """Record one operation latency into the ring buffer."""
        async with (await self._get_latency_lock()):
            self._latency_buffer.append(elapsed_ms)
            if len(self._latency_buffer) > self._latency_buffer_max:
                self._latency_buffer.pop(0)

    async def _get_memory_stats(self) -> dict:
        """Read Redis INFO memory and evaluate alert threshold."""
        alert_threshold_mb = int(os.getenv("REDIS_MEMORY_ALERT_MB", "256"))
        try:
            client = await self._ensure_connection()
            if client is None:
                return {"available": False}
            info = await client.info("memory")
            used_mb = info.get("used_memory_rss", 0) / (1024 * 1024)
            peak_mb = info.get("used_memory_peak_rss", used_mb) / (1024 * 1024)
            return {
                "available": True,
                "used_mb": round(used_mb, 1),
                "peak_mb": round(peak_mb, 1),
                "alert_threshold_mb": alert_threshold_mb,
                "memory_alert": used_mb >= alert_threshold_mb,
            }
        except Exception as exc:
            logger.warning("Redis memory stats unavailable: %s", exc)
            return {"available": False, "error": str(exc)}

    async def _record_success(self) -> None:
        """Record a successful operation, close the circuit if half-open."""
        async with (await self._get_cb_lock()):
            if self._circuit_breaker_state == "half-open":
                logger.info("Circuit breaker: Operation succeeded, closing circuit")
                self._circuit_breaker_state = "closed"
                self._circuit_breaker_failures = 0

    async def _record_failure(self) -> None:
        """Record a failed operation, potentially open the circuit."""
        async with (await self._get_cb_lock()):
            self._circuit_breaker_failures += 1
            self._circuit_breaker_last_failure_time = time.time()

            if self._circuit_breaker_state == "closed":
                if (
                    self._circuit_breaker_failures
                    >= self._circuit_breaker_failure_threshold
                ):
                    logger.warning(
                        "Circuit breaker: Failure threshold reached (%s), opening circuit",
                        self._circuit_breaker_failure_threshold,
                    )
                    self._circuit_breaker_state = "open"
            elif self._circuit_breaker_state == "half-open":
                logger.warning(
                    "Circuit breaker: Half-open test failed, reopening circuit"
                )
                self._circuit_breaker_state = "open"

    async def _should_allow_request(self) -> bool:
        """Check if a request should be allowed based on circuit breaker state."""
        async with (await self._get_cb_lock()):
            if self._circuit_breaker_state == "closed":
                return True

            if self._circuit_breaker_state == "open":
                if self._circuit_breaker_last_failure_time:
                    elapsed = time.time() - self._circuit_breaker_last_failure_time
                    if elapsed >= self._circuit_breaker_recovery_timeout:
                        logger.info(
                            "Circuit breaker: Recovery timeout passed, trying half-open"
                        )
                        self._circuit_breaker_state = "half-open"
                        return True
                return False

            return True

    def get_circuit_breaker_state(self) -> dict:
        """Get current circuit breaker state."""
        return {
            "state": self._circuit_breaker_state,
            "failures": self._circuit_breaker_failures,
            "failure_threshold": self._circuit_breaker_failure_threshold,
            "recovery_timeout": self._circuit_breaker_recovery_timeout,
            "last_failure_time": self._circuit_breaker_last_failure_time,
        }

    def _build_client(self) -> redis.Redis:
        # Support REDIS_URL (e.g., Upstash: rediss://default:pass@host:port)
        if self._redis_url:
            return redis.Redis.from_url(
                self._redis_url,
                max_connections=self._max_connections,
                decode_responses=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                retry_on_timeout=True,
            )
        return redis.Redis(
            host=self._host,
            port=self._port,
            password=self._password,
            db=self._db,
            max_connections=self._max_connections,
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
            retry_on_timeout=True,
            ssl=self._ssl,
        )

    async def _close_client(self, client: Any) -> None:
        close_method = getattr(client, "aclose", None)
        if close_method is None:
            close_method = getattr(client, "close", None)
        if close_method is None:
            return

        result = close_method()
        if asyncio.iscoroutine(result):
            await result

    async def _ensure_connection(self) -> redis.Redis | None:
        """Ensure Redis connection is established."""
        if self._connected and self._redis:
            return self._redis

        async with (await self._get_connection_lock()):
            if self._connected and self._redis:
                return self._redis

            candidate = self._build_client()
            try:
                await candidate.ping()
            except (RedisConnectionError, RedisTimeoutError) as exc:
                logger.error("Failed to connect to Redis: %s", exc)
                await self._close_client(candidate)
                self._connected = False
                self._redis = None
                return None
            except Exception as exc:
                logger.error("Unexpected error connecting to Redis: %s", exc)
                await self._close_client(candidate)
                self._connected = False
                self._redis = None
                return None

            self._redis = candidate
            self._connected = True
            logger.info("Redis connected to %s:%s", self._host, self._port)
            return self._redis

    @with_circuit_breaker
    async def prewarm(self) -> bool:
        """Pre-warm the Redis connection pool at startup."""
        logger.info("Pre-warming Redis connection...")
        try:
            client = await self._ensure_connection()
            if client:
                await client.ping()
                logger.info("Redis connection pre-warmed successfully")
                return True
            logger.warning("Redis pre-warm failed - not connected")
            return False
        except Exception as exc:
            logger.error("Redis pre-warm failed: %s", exc)
            return False

    @with_circuit_breaker
    async def get_user_config(self, user_id: str) -> CacheResult:
        """Retrieve user configuration from cache."""
        try:
            client = await self._ensure_connection()
            if not client:
                return CacheResult.from_error("Redis not connected")

            data = await client.get(f"user_config:{user_id}")
            if data:
                await client.incr("stats:hits")
                return CacheResult.hit(json.loads(data))

            await client.incr("stats:misses")
            return CacheResult.miss()
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.warning("Redis connection error (get_user_config): %s", exc)
            return CacheResult.from_error(f"Connection error: {exc}")
        except Exception as exc:
            logger.error("Cache error (get_user_config): %s", exc)
            return CacheResult.from_error(str(exc))

    @with_circuit_breaker
    async def set_user_config(
        self, user_id: str, config: dict, ttl: int | None = None
    ) -> bool:
        """Cache user configuration."""
        try:
            client = await self._ensure_connection()
            if not client:
                return False

            key = f"user_config:{user_id}"
            await client.set(key, json.dumps(config), ex=ttl or self.TTL_USER_CONFIG)
            return True
        except Exception as exc:
            logger.error("Cache error (set_user_config): %s", exc)
            return False

    @with_circuit_breaker
    async def invalidate_user_config(self, user_id: str) -> bool:
        """Remove user configuration from cache."""
        try:
            client = await self._ensure_connection()
            if not client:
                return False

            await client.delete(f"user_config:{user_id}")
            logger.info("Invalidated user config cache for %s", user_id)
            return True
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.warning("Redis connection error (invalidate_user_config): %s", exc)
            return False
        except Exception as exc:
            logger.error("Cache error (invalidate_user_config): %s", exc)
            return False

    @with_circuit_breaker
    async def get_session_metadata(self, session_id: str) -> CacheResult:
        """Retrieve session metadata from cache."""
        try:
            client = await self._ensure_connection()
            if not client:
                return CacheResult.from_error("Redis not connected")

            data = await client.get(f"session:{session_id}")
            if data:
                await client.incr("stats:hits")
                return CacheResult.hit(json.loads(data))

            await client.incr("stats:misses")
            return CacheResult.miss()
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.warning("Redis connection error (get_session_metadata): %s", exc)
            return CacheResult.from_error(f"Connection error: {exc}")
        except Exception as exc:
            logger.warning("Cache error (get_session_metadata): %s", exc)
            return CacheResult.from_error(str(exc))

    @with_circuit_breaker
    async def set_session_metadata(
        self, session_id: str, metadata: dict, ttl: int | None = None
    ) -> bool:
        """Cache session metadata."""
        try:
            client = await self._ensure_connection()
            if not client:
                return False

            await client.set(
                f"session:{session_id}",
                json.dumps(metadata),
                ex=ttl or self.TTL_SESSION_META,
            )
            return True
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.warning("Redis connection error (set_session_metadata): %s", exc)
            return False
        except Exception as exc:
            logger.error("Cache error (set_session_metadata): %s", exc)
            return False

    @with_circuit_breaker
    async def invalidate_session(self, session_id: str) -> bool:
        """Remove session from cache."""
        try:
            client = await self._ensure_connection()
            if not client:
                return False

            await client.delete(f"session:{session_id}")
            return True
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.warning("Redis connection error (invalidate_session): %s", exc)
            return False
        except Exception as exc:
            logger.error("Cache error (invalidate_session): %s", exc)
            return False

    @with_circuit_breaker
    async def get_user_persona(self, user_id: str) -> CacheResult:
        """Retrieve user persona from cache."""
        try:
            client = await self._ensure_connection()
            if not client:
                return CacheResult.from_error("Redis not connected")

            data = await client.get(f"persona:{user_id}")
            if data:
                await client.incr("stats:hits")
                return CacheResult.hit(data)

            await client.incr("stats:misses")
            return CacheResult.miss()
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.warning("Redis connection error (get_user_persona): %s", exc)
            return CacheResult.from_error(f"Connection error: {exc}")
        except Exception as exc:
            logger.error("Cache error (get_user_persona): %s", exc)
            return CacheResult.from_error(str(exc))

    @with_circuit_breaker
    async def set_user_persona(
        self, user_id: str, persona: str, ttl: int | None = None
    ) -> bool:
        """Cache user persona."""
        try:
            client = await self._ensure_connection()
            if not client:
                return False

            await client.set(f"persona:{user_id}", persona, ex=ttl or self.TTL_PERSONA)
            return True
        except (RedisConnectionError, RedisTimeoutError):
            return False
        except Exception:
            return False

    @with_circuit_breaker
    async def invalidate_user_persona(self, user_id: str) -> bool:
        """Remove user persona from cache."""
        try:
            client = await self._ensure_connection()
            if not client:
                return False

            await client.delete(f"persona:{user_id}")
            return True
        except (RedisConnectionError, RedisTimeoutError):
            return False
        except Exception:
            return False

    @with_circuit_breaker
    async def invalidate_user_all(self, user_id: str) -> bool:
        """Invalidate all cache entries for a user."""
        try:
            client = await self._ensure_connection()
            if not client:
                return False

            pipe = client.pipeline()
            pipe.delete(f"user_config:{user_id}")
            pipe.delete(f"persona:{user_id}")
            await pipe.execute()
            logger.info("Invalidated all caches for user %s", user_id)
            return True
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.warning("Redis connection error (invalidate_user_all): %s", exc)
            return False
        except Exception as exc:
            logger.error("Cache error (invalidate_user_all): %s", exc)
            return False

    @with_circuit_breaker
    async def flush_all(self) -> bool:
        """Clear the entire cache. Use with caution."""
        try:
            client = await self._ensure_connection()
            if not client:
                return False

            await client.flushdb()
            logger.warning("Flushed Redis cache")
            return True
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.warning("Redis connection error (flush_all): %s", exc)
            return False
        except Exception as exc:
            logger.error("Cache error (flush_all): %s", exc)
            return False

    @with_circuit_breaker
    async def set_nx(self, key: str, value: str, ttl: int) -> bool:
        """Set a key only if it does not already exist (atomic SET NX + EXPIRE).

        Args:
            key: Redis key to set.
            value: String value to store.
            ttl: Time-to-live in seconds.

        Returns:
            ``True`` if the key was set (lock acquired), ``False`` if it already existed.
        """
        try:
            client = await self._ensure_connection()
            if not client:
                return False

            result = await client.set(key, value, nx=True, ex=ttl)
            return result is True
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.warning("Redis connection error (set_nx): %s", exc)
            return False
        except Exception as exc:
            logger.error("Cache error (set_nx): %s", exc)
            return False

    @with_circuit_breaker
    async def delete(self, key: str) -> bool:
        """Delete a key from the cache.

        Args:
            key: Redis key to remove.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        try:
            client = await self._ensure_connection()
            if not client:
                return False

            await client.delete(key)
            return True
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.warning("Redis connection error (delete): %s", exc)
            return False
        except Exception as exc:
            logger.error("Cache error (delete): %s", exc)
            return False

    @with_circuit_breaker
    async def get_generic(self, key: str) -> CacheResult:
        """Get a value from cache by arbitrary key.

        Args:
            key: Cache key string.

        Returns:
            CacheResult with the cached value (parsed from JSON) or miss/error.
        """
        raw = await self._redis.get(key)
        if raw is None:
            await self._redis.incr("stats:misses")
            return CacheResult.miss()
        await self._redis.incr("stats:hits")
        try:
            return CacheResult.hit(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            return CacheResult.hit(raw)

    @with_circuit_breaker
    async def set_generic(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set a value in cache with arbitrary key and TTL.

        Args:
            key: Cache key string.
            value: Value to cache (will be JSON serialized).
            ttl: Time-to-live in seconds (default 1 hour).

        Returns:
            True if set successfully.
        """
        serialized = json.dumps(value, default=str)
        await self._redis.set(key, serialized, ex=ttl)
        return True

    async def get_stats(self) -> dict:
        """Get cache statistics including circuit breaker state."""
        try:
            client = await self._ensure_connection()
            if not client:
                return {
                    "status": "disconnected",
                    "circuit_breaker": self.get_circuit_breaker_state(),
                }

            info = await client.info()
            hits = await client.get("stats:hits") or 0
            misses = await client.get("stats:misses") or 0
            hits_int = int(hits)
            misses_int = int(misses)

            # Latency stats from ring buffer
            async with (await self._get_latency_lock()):
                buf = list(self._latency_buffer)

            latency_stats: dict = {"sample_count": len(buf)}
            if len(buf) >= 3:
                sorted_buf = sorted(buf)
                p50_idx = int(len(sorted_buf) * 0.5)
                p99_idx = int(len(sorted_buf) * 0.99)
                latency_stats["p50_ms"] = round(sorted_buf[p50_idx], 2)
                latency_stats["p99_ms"] = round(
                    sorted_buf[min(p99_idx, len(sorted_buf) - 1)], 2
                )
                latency_stats["max_ms"] = round(sorted_buf[-1], 2)
            else:
                latency_stats["p50_ms"] = None
                latency_stats["p99_ms"] = None
                latency_stats["max_ms"] = None

            memory_stats = await self._get_memory_stats()

            return {
                "status": "connected",
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "pool_max_connections": self._max_connections,
                "hits": hits_int,
                "misses": misses_int,
                "hit_rate": (hits_int / (hits_int + misses_int) * 100)
                if (hits_int + misses_int) > 0
                else 0,
                "latency_stats": latency_stats,
                "memory_stats": memory_stats,
                "circuit_breaker": self.get_circuit_breaker_state(),
            }
        except (RedisConnectionError, RedisTimeoutError) as exc:
            await self._record_failure()
            return {
                "error": f"Redis connection error: {exc}",
                "circuit_breaker": self.get_circuit_breaker_state(),
            }
        except Exception as exc:
            await self._record_failure()
            return {
                "error": str(exc),
                "circuit_breaker": self.get_circuit_breaker_state(),
            }

    async def is_healthy(self) -> bool:
        """Check if Redis connection is working and circuit is not open."""
        if not await self._should_allow_request():
            logger.warning("Circuit breaker is open, rejecting health check")
            return False

        try:
            client = await self._ensure_connection()
            if not client:
                await self._record_failure()
                return False

            result = await client.ping()
            await self._record_success()
            return result
        except (RedisConnectionError, RedisTimeoutError):
            await self._record_failure()
            return False
        except Exception:
            await self._record_failure()
            return False

    async def close(self) -> None:
        """Close the Redis connection and clear local state."""
        async with (await self._get_connection_lock()):
            client = self._redis
            self._redis = None
            self._connected = False

        if client is not None:
            await self._close_client(client)
            logger.info("Redis connection closed")


_cache_service: CacheService | None = None


def get_cache_service() -> CacheService:
    """Get the singleton CacheService instance."""
    global _cache_service
    with CacheService._instance_lock:
        if _cache_service is None:
            _cache_service = CacheService()
        return _cache_service


def invalidate_cache_service() -> None:
    """Clear the cached service instance."""
    global _cache_service
    with CacheService._instance_lock:
        if _cache_service is not None:
            _cache_service._connected = False
            _cache_service._redis = None
            _cache_service._initialized = False
        _cache_service = None
        CacheService._instance = None
