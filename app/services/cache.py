"""Cache service for Pikar AI using Redis.

This module provides async Redis caching operations with connection pooling,
user config caching, session caching, and persona caching.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Optional, Union

import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError

from app.exceptions import CacheError, CacheConnectionError, CacheMissError

logger = logging.getLogger(__name__)


@dataclass
class CacheResult:
    """Result of a cache operation that distinguishes between different outcomes.
    
    Attributes:
        found: Whether the key was found in cache
        value: The cached value if found
        error: Error message if operation failed
        is_miss: True if key was not found (cache miss)
        is_error: True if there was an error during the operation
    """
    found: bool = False
    value: Any = None
    error: Optional[str] = None
    is_miss: bool = False
    is_error: bool = False
    
    @classmethod
    def hit(cls, value: Any) -> "CacheResult":
        """Create a cache hit result."""
        return cls(found=True, value=value, is_miss=False, is_error=False)
    
    @classmethod
    def miss(cls) -> "CacheResult":
        """Create a cache miss result."""
        return cls(found=False, value=None, is_miss=True, is_error=False)
    
    @classmethod
    def from_error(cls, error_message: str) -> "CacheResult":
        """Create an error result."""
        return cls(found=False, value=None, error=error_message, is_miss=False, is_error=True)


class CacheService:
    """Async service for handling Redis caching operations with connection pooling.
    
    Implements circuit breaker pattern for resilience:
    - Tracks consecutive failures
    - Opens circuit after threshold is reached
    - Half-open state allows test requests
    - Automatically recovers after recovery timeout
    """

    _instance: Optional["CacheService"] = None

    def __new__(cls) -> "CacheService":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the Redis connection pool and circuit breaker."""
        if self._initialized:
            return

        self._redis: Optional[redis.Redis] = None
        self._connected = False
        self._host = os.getenv("REDIS_HOST", "localhost")
        self._port = int(os.getenv("REDIS_PORT", 6379))
        self._password = os.getenv("REDIS_PASSWORD")
        self._db = int(os.getenv("REDIS_DB", 0))
        self._max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", 20))

        # TTLs
        self.TTL_USER_CONFIG = 3600
        self.TTL_SESSION_META = 1800
        self.TTL_PERSONA = 7200

        # Circuit breaker configuration
        self._circuit_breaker_failure_threshold = int(os.getenv("REDIS_CB_FAILURE_THRESHOLD", 5))
        self._circuit_breaker_recovery_timeout = int(os.getenv("REDIS_CB_RECOVERY_TIMEOUT", 30))
        self._circuit_breaker_state = "closed"  # closed, open, half-open
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure_time: Optional[float] = None

        self._initialized = True

    def _record_success(self) -> None:
        """Record a successful operation, close the circuit if half-open."""
        if self._circuit_breaker_state == "half-open":
            logger.info("Circuit breaker: Operation succeeded, closing circuit")
            self._circuit_breaker_state = "closed"
            self._circuit_breaker_failures = 0

    def _record_failure(self) -> None:
        """Record a failed operation, potentially open the circuit."""
        import time
        self._circuit_breaker_failures += 1
        self._circuit_breaker_last_failure_time = time.time()
        
        if self._circuit_breaker_state == "closed":
            if self._circuit_breaker_failures >= self._circuit_breaker_failure_threshold:
                logger.warning(
                    f"Circuit breaker: Failure threshold reached ({self._circuit_breaker_failure_threshold}), "
                    f"opening circuit"
                )
                self._circuit_breaker_state = "open"
        elif self._circuit_breaker_state == "half-open":
            logger.warning("Circuit breaker: Half-open test failed, reopening circuit")
            self._circuit_breaker_state = "open"

    def _should_allow_request(self) -> bool:
        """Check if a request should be allowed based on circuit breaker state."""
        import time
        
        if self._circuit_breaker_state == "closed":
            return True
        
        if self._circuit_breaker_state == "open":
            # Check if recovery timeout has passed
            if self._circuit_breaker_last_failure_time:
                elapsed = time.time() - self._circuit_breaker_last_failure_time
                if elapsed >= self._circuit_breaker_recovery_timeout:
                    logger.info("Circuit breaker: Recovery timeout passed, trying half-open")
                    self._circuit_breaker_state = "half-open"
                    return True
            return False
        
        # half-open state allows one test request
        return True

    def get_circuit_breaker_state(self) -> dict:
        """Get current circuit breaker state."""
        return {
            "state": self._circuit_breaker_state,
            "failures": self._circuit_breaker_failures,
            "failure_threshold": self._circuit_breaker_failure_threshold,
            "recovery_timeout": self._circuit_breaker_recovery_timeout,
            "last_failure_time": self._circuit_breaker_last_failure_time
        }

    async def _ensure_connection(self) -> Optional[redis.Redis]:
        """Ensure Redis connection is established."""
        if self._connected and self._redis:
            return self._redis

        try:
            self._redis = redis.Redis(
                host=self._host,
                port=self._port,
                password=self._password,
                db=self._db,
                max_connections=self._max_connections,
                decode_responses=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                retry_on_timeout=True,
            )
            await self._redis.ping()
            self._connected = True
            logger.info(f"Redis connected to {self._host}:{self._port}")
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            self._redis = None
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            self._connected = False
            self._redis = None

        return self._redis

    async def prewarm(self) -> bool:
        """Pre-warm the Redis connection pool at startup.
        
        Validates connection before accepting requests.
        Returns True if connection successful.
        """
        logger.info("Pre-warming Redis connection...")
        try:
            client = await self._ensure_connection()
            if client:
                # Test a simple operation
                await client.ping()
                logger.info("Redis connection pre-warmed successfully")
                return True
            else:
                logger.warning("Redis pre-warm failed - not connected")
                return False
        except Exception as e:
            logger.error(f"Redis pre-warm failed: {e}")
            return False

    async def get_user_config(self, user_id: str) -> CacheResult:
        """Retrieve user configuration from cache.
        
        Returns:
            CacheResult with found=True and value if hit,
            CacheResult with is_miss=True if not found,
            CacheResult with is_error=True if error occurred.
        """
        try:
            client = await self._ensure_connection()
            if not client:
                return CacheResult.from_error("Redis not connected")

            data = await client.get(f"user_config:{user_id}")
            if data:
                import json
                await client.incr("stats:hits")
                return CacheResult.hit(json.loads(data))

            await client.incr("stats:misses")
            return CacheResult.miss()
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(f"Redis connection error (get_user_config): {e}")
            return CacheResult.from_error(f"Connection error: {e}")
        except Exception as e:
            logger.error(f"Cache error (get_user_config): {e}")
            return CacheResult.from_error(str(e))

    async def set_user_config(self, user_id: str, config: dict, ttl: Optional[int] = None) -> bool:
        """Cache user configuration."""
        try:
            client = await self._ensure_connection()
            if not client:
                return False

            import json
            key = f"user_config:{user_id}"
            await client.set(key, json.dumps(config), ex=ttl or self.TTL_USER_CONFIG)
            return True
        except Exception as e:
            logger.error(f"Cache error (set_user_config): {e}")
            return False

    async def invalidate_user_config(self, user_id: str) -> bool:
        """Remove user configuration from cache."""
        try:
            client = await self._ensure_connection()
            if not client:
                return False

            await client.delete(f"user_config:{user_id}")
            logger.info(f"Invalidated user config cache for {user_id}")
            return True
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(f"Redis connection error (invalidate_user_config): {e}")
            return False
        except Exception as e:
            logger.error(f"Cache error (invalidate_user_config): {e}")
            return False

    async def get_session_metadata(self, session_id: str) -> CacheResult:
        """Retrieve session metadata from cache.
        
        Returns:
            CacheResult with found=True and value if hit,
            CacheResult with is_miss=True if not found,
            CacheResult with is_error=True if error occurred.
        """
        try:
            client = await self._ensure_connection()
            if not client:
                return CacheResult.from_error("Redis not connected")

            data = await client.get(f"session:{session_id}")
            if data:
                import json
                await client.incr("stats:hits")
                return CacheResult.hit(json.loads(data))

            await client.incr("stats:misses")
            return CacheResult.miss()
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(f"Redis connection error (get_session_metadata): {e}")
            return CacheResult.from_error(f"Connection error: {e}")
        except Exception as e:
            logger.warning(f"Cache error (get_session_metadata): {e}")
            return CacheResult.from_error(str(e))

    async def set_session_metadata(self, session_id: str, metadata: dict, ttl: Optional[int] = None) -> bool:
        """Cache session metadata."""
        try:
            client = await self._ensure_connection()
            if not client:
                return False

            import json
            await client.set(
                f"session:{session_id}",
                json.dumps(metadata),
                ex=ttl or self.TTL_SESSION_META
            )
            return True
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(f"Redis connection error (set_session_metadata): {e}")
            return False
        except Exception as e:
            logger.error(f"Cache error (set_session_metadata): {e}")
            return False

    async def invalidate_session(self, session_id: str) -> bool:
        """Remove session from cache."""
        try:
            client = await self._ensure_connection()
            if not client:
                return False

            await client.delete(f"session:{session_id}")
            return True
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(f"Redis connection error (invalidate_session): {e}")
            return False
        except Exception as e:
            logger.error(f"Cache error (invalidate_session): {e}")
            return False

    async def get_user_persona(self, user_id: str) -> CacheResult:
        """Retrieve user persona from cache.
        
        Returns:
            CacheResult with found=True and value if hit,
            CacheResult with is_miss=True if not found,
            CacheResult with is_error=True if error occurred.
        """
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
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(f"Redis connection error (get_user_persona): {e}")
            return CacheResult.from_error(f"Connection error: {e}")
        except Exception as e:
            logger.error(f"Cache error (get_user_persona): {e}")
            return CacheResult.from_error(str(e))

    async def set_user_persona(self, user_id: str, persona: str, ttl: Optional[int] = None) -> bool:
        """Cache user persona."""
        try:
            client = await self._ensure_connection()
            if not client:
                return False

            await client.set(
                f"persona:{user_id}",
                persona,
                ex=ttl or self.TTL_PERSONA
            )
            return True
        except (RedisConnectionError, RedisTimeoutError):
            return False
        except Exception:
            return False

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
            logger.info(f"Invalidated all caches for user {user_id}")
            return True
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(f"Redis connection error (invalidate_user_all): {e}")
            return False
        except Exception as e:
            logger.error(f"Cache error (invalidate_user_all): {e}")
            return False

    async def flush_all(self) -> bool:
        """Clear the entire cache. Use with caution."""
        try:
            client = await self._ensure_connection()
            if not client:
                return False

            await client.flushdb()
            logger.warning("Flushed Redis cache")
            return True
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(f"Redis connection error (flush_all): {e}")
            return False
        except Exception as e:
            logger.error(f"Cache error (flush_all): {e}")
            return False

    async def get_stats(self) -> dict:
        """Get cache statistics including circuit breaker state."""
        try:
            client = await self._ensure_connection()
            if not client:
                return {
                    "status": "disconnected",
                    "circuit_breaker": self.get_circuit_breaker_state()
                }

            info = await client.info()
            hits = await client.get("stats:hits") or 0
            misses = await client.get("stats:misses") or 0
            hits_int = int(hits)
            misses_int = int(misses)

            return {
                "status": "connected",
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "hits": hits_int,
                "misses": misses_int,
                "hit_rate": (hits_int / (hits_int + misses_int) * 100) if (hits_int + misses_int) > 0 else 0,
                "circuit_breaker": self.get_circuit_breaker_state()
            }
        except (RedisConnectionError, RedisTimeoutError) as e:
            self._record_failure()
            return {
                "error": f"Redis connection error: {e}",
                "circuit_breaker": self.get_circuit_breaker_state()
            }
        except Exception as e:
            self._record_failure()
            return {
                "error": str(e),
                "circuit_breaker": self.get_circuit_breaker_state()
            }

    async def is_healthy(self) -> bool:
        """Check if Redis connection is working and circuit is not open."""
        # First check circuit breaker
        if not self._should_allow_request():
            logger.warning("Circuit breaker is open, rejecting health check")
            return False
        
        try:
            client = await self._ensure_connection()
            if not client:
                self._record_failure()
                return False
            
            result = await client.ping()
            self._record_success()
            return result
        except (RedisConnectionError, RedisTimeoutError):
            self._record_failure()
            return False
        except Exception:
            self._record_failure()
            return False

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._redis:
            await self._redis.close()
            self._connected = False
            logger.info("Redis connection closed")


_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get the singleton CacheService instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


def invalidate_cache_service() -> None:
    """Clear the cached service instance."""
    global _cache_service
    _cache_service = None
