import os
import logging
import json
import asyncio
from typing import Optional, Dict, Any, Union
import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError

logger = logging.getLogger(__name__)

class CacheService:
    """Service for handling Redis caching operations with connection pooling."""
    
    _instance = None

    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._connected = False
        self._host = os.getenv("REDIS_HOST", "localhost")
        self._port = int(os.getenv("REDIS_PORT", 6379))
        self._password = os.getenv("REDIS_PASSWORD", None)
        self._db = int(os.getenv("REDIS_DB", 0))
        self._max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", 20))
        
        # TTL Constants in seconds
        self.TTL_USER_CONFIG = 3600  # 1 hour
        self.TTL_SESSION_META = 1800  # 30 minutes
        self.TTL_PERSONA = 7200      # 2 hours
        
        self.connect()

    def connect(self):
        """Initialize Redis connection pool."""
        try:
            self._redis = redis.Redis(
                host=self._host,
                port=self._port,
                password=self._password,
                db=self._db,
                max_connections=self._max_connections,
                decode_responses=True,
                socket_timeout=5.0,
                retry_on_timeout=True
            )
            self._connected = True
            logger.info(f"Redis client initialized for {self._host}:{self._port}")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            self._connected = False

    async def _get_connection(self) -> Optional[redis.Redis]:
        """Get active Redis connection."""
        if not self._connected or not self._redis:
            # Try to reconnect
            self.connect()
        return self._redis

    async def get_user_config(self, user_id: str) -> Optional[dict]:
        """Retrieve user configuration from cache."""
        try:
            client = await self._get_connection()
            if not client: return None
            
            data = await client.get(f"user_config:{user_id}")
            if data:
                await client.incr("stats:hits")
                return json.loads(data)
            
            await client.incr("stats:misses")
            return None
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Redis connection error (get_user_config): {e}")
            return None
        except Exception as e:
            logger.error(f"Cache error (get_user_config): {e}")
            return None

    async def set_user_config(self, user_id: str, config: dict, ttl: Optional[int] = None) -> bool:
        """Cache user configuration."""
        try:
            client = await self._get_connection()
            if not client: return False
            
            key = f"user_config:{user_id}"
            await client.set(
                key, 
                json.dumps(config), 
                ex=ttl or self.TTL_USER_CONFIG
            )
            return True
        except Exception as e:
            logger.error(f"Cache error (set_user_config): {e}")
            return False

    async def invalidate_user_config(self, user_id: str) -> bool:
        """Remove user configuration from cache."""
        try:
            client = await self._get_connection()
            if not client: return False
            
            await client.delete(f"user_config:{user_id}")
            logger.info(f"Invalidated user config cache for {user_id}")
            return True
        except Exception as e:
            logger.error(f"Cache error (invalidate_user_config): {e}")
            return False

    async def get_session_metadata(self, session_id: str) -> Optional[dict]:
        """Retrieve session metadata from cache."""
        try:
            client = await self._get_connection()
            if not client: return None
            
            data = await client.get(f"session:{session_id}")
            if data:
                await client.incr("stats:hits")
                return json.loads(data)
            
            await client.incr("stats:misses")
            return None
        except Exception as e:
            logger.warning(f"Cache error (get_session_metadata): {e}")
            return None

    async def set_session_metadata(self, session_id: str, metadata: dict, ttl: Optional[int] = None) -> bool:
        """Cache session metadata."""
        try:
            client = await self._get_connection()
            if not client: return False
            
            await client.set(
                f"session:{session_id}", 
                json.dumps(metadata), 
                ex=ttl or self.TTL_SESSION_META
            )
            return True
        except Exception as e:
            logger.error(f"Cache error (set_session_metadata): {e}")
            return False

    async def invalidate_session(self, session_id: str) -> bool:
        """Remove session from cache."""
        try:
            client = await self._get_connection()
            if not client: return False
            
            await client.delete(f"session:{session_id}")
            return True
        except Exception as e:
            logger.error(f"Cache error (invalidate_session): {e}")
            return False

    async def get_user_persona(self, user_id: str) -> Optional[str]:
        """Retrieve user persona from cache."""
        try:
            client = await self._get_connection()
            if not client: return None
            
            data = await client.get(f"persona:{user_id}")
            return data
        except Exception as e:
            return None

    async def set_user_persona(self, user_id: str, persona: str, ttl: Optional[int] = None) -> bool:
        """Cache user persona."""
        try:
            client = await self._get_connection()
            if not client: return False
            
            await client.set(
                f"persona:{user_id}", 
                persona, 
                ex=ttl or self.TTL_PERSONA
            )
            return True
        except Exception as e:
            return False

    async def invalidate_user_persona(self, user_id: str) -> bool:
        """Remove user persona from cache."""
        try:
            client = await self._get_connection()
            if not client: return False
            
            await client.delete(f"persona:{user_id}")
            return True
        except Exception as e:
            return False

    async def invalidate_user_all(self, user_id: str) -> bool:
        """Invalidate all cache entries for a user (config, persona)."""
        try:
            client = await self._get_connection()
            if not client: return False
            
            pipe = client.pipeline()
            pipe.delete(f"user_config:{user_id}")
            pipe.delete(f"persona:{user_id}")
            # Note: We can't easily find all user sessions without a lookup set, 
            # so session caches might persist until TTL expiries unless explicitly cleared.
            await pipe.execute()
            logger.info(f"Invalidated all caches for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Cache error (invalidate_user_all): {e}")
            return False

    async def flush_all(self) -> bool:
        """Clear the entire cache. Use with caution."""
        try:
            client = await self._get_connection()
            if not client: return False
            await client.flushdb()
            logger.warning("Flushed Redis cache")
            return True
        except Exception as e:
            logger.error(f"Cache error (flush_all): {e}")
            return False

    async def get_stats(self) -> dict:
        """Get cache statistics."""
        try:
            client = await self._get_connection()
            if not client: 
                return {"status": "disconnected"}
            
            info = await client.info()
            hits = await client.get("stats:hits") or 0
            misses = await client.get("stats:misses") or 0
            
            return {
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "hits": int(hits),
                "misses": int(misses),
                "hit_rate": (int(hits) / (int(hits) + int(misses)) * 100) if (int(hits) + int(misses)) > 0 else 0
            }
        except Exception as e:
            return {"error": str(e)}

    async def is_healthy(self) -> bool:
        """Check if Redis connection is working."""
        try:
            client = await self._get_connection()
            if not client: return False
            return await client.ping()
        except Exception:
            return False


# Singleton instance
_cache_service: Optional[CacheService] = None

def get_cache_service() -> CacheService:
    """Get the singleton CacheService instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service

def invalidate_cache_service():
    """Clear the cached service instance."""
    global _cache_service
    _cache_service = None
