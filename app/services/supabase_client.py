"""Unified Supabase client service for Pikar AI.

This module provides a single, centralized Supabase client instance
to avoid multiple connection pools and ensure consistent behavior
across the application.
"""

import logging
import os
from functools import lru_cache
from typing import Any, Dict, Optional

from supabase import create_client, Client

logger = logging.getLogger(__name__)

_client_creation_count = 0


class SupabaseService:
    """Centralized Supabase client service.

    This class provides a single Supabase client instance with proper
    connection pooling and configuration. All code should use this
    service instead of creating separate clients.
    """

    _instance: Optional["SupabaseService"] = None
    _client: Optional[Client] = None

    def __new__(cls) -> "SupabaseService":
        """Singleton pattern to ensure single client instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the service (only once due to singleton)."""
        if self._client is not None:
            return

        url = os.getenv("SUPABASE_URL")
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        anon_key = os.getenv("SUPABASE_ANON_KEY")

        if not url or not service_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

        global _client_creation_count
        _client_creation_count += 1

        max_connections = int(os.getenv("SUPABASE_MAX_CONNECTIONS", "50"))
        timeout = float(os.getenv("SUPABASE_TIMEOUT", "60.0"))

        logger.info(
            f"Supabase client initialized (singleton) with max_connections={max_connections}, timeout={timeout}"
        )

        self._client = create_client(url, service_key)
        self._url = url
        self._service_key = service_key
        self._anon_key = anon_key or service_key

    @property
    def client(self) -> Client:
        """Get the Supabase client instance."""
        if self._client is None:
            raise RuntimeError("SupabaseService not initialized")
        return self._client

    @property
    def url(self) -> str:
        """Get the Supabase URL."""
        return self._url

    @property
    def service_key(self) -> str:
        """Get the Supabase service role key."""
        return self._service_key

    def get_anon_client(self) -> Client:
        """Get a client with anon key for public operations."""
        if self._anon_key != self._service_key:
            return create_client(self._url, self._anon_key)
        return self._client


@lru_cache(maxsize=1)
def get_supabase_service() -> SupabaseService:
    """Get the singleton SupabaseService instance.

    This is the recommended way to access Supabase throughout the application.
    Uses lru_cache for thread-safe singleton behavior.

    Returns:
        The SupabaseService singleton instance.
    """
    return SupabaseService()


def get_client() -> Client:
    """Get the primary Supabase client (service role).

    This is a convenience function that provides backward compatibility.
    Prefer using get_supabase_service() for new code.

    Returns:
        The Supabase Client instance.
    """
    return get_supabase_service().client


def get_service_client() -> Client:
    """Get the service client (alias for get_client).

    This function exists for backward compatibility with existing code.

    Returns:
        The Supabase Client instance.
    """
    return get_client()


def get_anon_client() -> Client:
    """Get a client with anon key for public operations.

    Use this for operations that don't require elevated permissions.

    Returns:
        A Supabase Client with anon key.
    """
    return get_supabase_service().get_anon_client()


def get_client_stats() -> Dict[str, Any]:
    """Get statistics about the Supabase client.

    Returns:
        Dictionary with client statistics.
    """
    global _client_creation_count

    return {
        "client_created": _client_creation_count > 0,
        "creation_count": _client_creation_count,
        "is_singleton": True,
        "max_connections": int(os.getenv("SUPABASE_MAX_CONNECTIONS", "50")),
    }


def invalidate_client() -> None:
    """Invalidate the cached client instance.

    Useful for testing, credential rotation, or connection recovery.
    """
    get_supabase_service.cache_clear()
    global _client_creation_count
    _client_creation_count = 0
    SupabaseService._client = None
    SupabaseService._instance = None
    logger.warning("Supabase client cache invalidated")


get_supabase_client = get_client
