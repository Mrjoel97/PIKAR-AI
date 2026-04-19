"""Unified Supabase client service for Pikar AI.

This module provides single, centralized sync and async Supabase client
instances to avoid multiple connection pools and ensure consistent behavior
across the application.

The async client uses ``httpx.AsyncClient`` with configurable connection
pooling (``SUPABASE_MAX_CONNECTIONS``, ``SUPABASE_KEEPALIVE_CONNECTIONS``)
for native async DB calls without thread pool overhead.
"""

from __future__ import annotations

import asyncio
import logging
import os
from functools import lru_cache
from typing import Any, Optional

import httpx
from supabase._async.client import AsyncClient
from supabase._async.client import create_client as create_async_client
from supabase.lib.client_options import AsyncClientOptions, SyncClientOptions

from app.app_utils.env import get_stripped_env
from supabase import Client, create_client

logger = logging.getLogger(__name__)

_client_creation_count = 0


class SupabaseService:
    """Centralized Supabase client service.

    This class provides a single Supabase client instance with proper
    connection pooling and configuration. All code should use this
    service instead of creating separate clients.
    """

    _instance: Optional["SupabaseService"] = None
    _client: Client | None = None

    def __new__(cls) -> "SupabaseService":
        """Singleton pattern to ensure single client instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the service (only once due to singleton)."""
        if self._client is not None:
            return

        url = get_stripped_env("SUPABASE_URL")
        service_key = get_stripped_env("SUPABASE_SERVICE_ROLE_KEY")
        anon_key = get_stripped_env("SUPABASE_ANON_KEY")

        if not url or not service_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

        global _client_creation_count
        _client_creation_count += 1

        max_connections = int(os.getenv("SUPABASE_MAX_CONNECTIONS", "50"))
        timeout = float(os.getenv("SUPABASE_TIMEOUT", "60.0"))

        logger.info(
            "Supabase client initialized (singleton) with max_connections=%s, timeout=%s",
            max_connections,
            timeout,
        )

        self._url = url
        self._service_key = service_key
        self._anon_key = anon_key or service_key
        self._timeout = timeout
        self._service_http_client = self._build_http_client(timeout)
        self._anon_http_client: httpx.Client | None = None
        self._anon_client: Client | None = None
        self._client = create_client(
            url,
            service_key,
            options=self._build_client_options(self._service_http_client),
        )

    @staticmethod
    def _build_http_client(timeout: float) -> httpx.Client:
        return httpx.Client(timeout=timeout)

    @staticmethod
    def _build_client_options(http_client: httpx.Client) -> SyncClientOptions:
        return SyncClientOptions(httpx_client=http_client)

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
        if self._anon_key == self._service_key:
            return self.client
        if self._anon_client is None:
            if self._anon_http_client is None:
                self._anon_http_client = self._build_http_client(self._timeout)
            self._anon_client = create_client(
                self._url,
                self._anon_key,
                options=self._build_client_options(self._anon_http_client),
            )
        return self._anon_client


class AsyncSupabaseService:
    """Async Supabase client service with httpx.AsyncClient connection pooling.

    This class provides a singleton async Supabase client with configurable
    connection limits. Use ``get_instance()`` (async classmethod) to obtain
    the singleton since ``create_async_client`` is an async function.

    Configuration via environment variables:
    - ``SUPABASE_MAX_CONNECTIONS``: max total connections (default 200)
    - ``SUPABASE_KEEPALIVE_CONNECTIONS``: max keepalive connections (default 50)
    - ``SUPABASE_TIMEOUT``: request timeout in seconds (default 60.0)
    """

    _instance: AsyncSupabaseService | None = None
    _client: AsyncClient | None = None

    def __init__(self) -> None:
        """Private init — use ``get_instance()`` instead."""

    @classmethod
    async def get_instance(cls) -> AsyncSupabaseService:
        """Get or create the singleton AsyncSupabaseService.

        Lazily creates the async Supabase client on first call.

        Returns:
            The AsyncSupabaseService singleton instance.
        """
        if cls._instance is not None and cls._client is not None:
            return cls._instance

        url = get_stripped_env("SUPABASE_URL")
        service_key = get_stripped_env("SUPABASE_SERVICE_ROLE_KEY")
        anon_key = get_stripped_env("SUPABASE_ANON_KEY")

        if not url or not service_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

        max_connections = int(os.getenv("SUPABASE_MAX_CONNECTIONS", "200"))
        keepalive_connections = int(os.getenv("SUPABASE_KEEPALIVE_CONNECTIONS", "50"))
        timeout = float(os.getenv("SUPABASE_TIMEOUT", "60.0"))

        async_http_client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=keepalive_connections,
            ),
            timeout=httpx.Timeout(timeout),
        )

        options = AsyncClientOptions(httpx_client=async_http_client)
        async_client = await create_async_client(url, service_key, options=options)

        instance = super().__new__(cls)
        instance._url = url
        instance._service_key = service_key
        instance._anon_key = anon_key or service_key
        instance._timeout = timeout
        instance._async_http_client = async_http_client
        instance._anon_async_client: AsyncClient | None = None

        cls._instance = instance
        cls._client = async_client

        logger.info(
            "Async Supabase client initialized (singleton) "
            "max_connections=%s, keepalive=%s, timeout=%s",
            max_connections,
            keepalive_connections,
            timeout,
        )

        return instance

    @property
    def client(self) -> AsyncClient:
        """Get the async Supabase client instance."""
        if self._client is None:
            raise RuntimeError("AsyncSupabaseService not initialized — use get_instance()")
        return self._client

    async def get_anon_client(self) -> AsyncClient:
        """Get an async client with anon key for public operations."""
        if self._anon_key == self._service_key:
            return self.client
        if self._anon_async_client is None:
            anon_http = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_connections=int(os.getenv("SUPABASE_MAX_CONNECTIONS", "200")),
                    max_keepalive_connections=int(
                        os.getenv("SUPABASE_KEEPALIVE_CONNECTIONS", "50")
                    ),
                ),
                timeout=httpx.Timeout(self._timeout),
            )
            options = AsyncClientOptions(httpx_client=anon_http)
            self._anon_async_client = await create_async_client(
                self._url, self._anon_key, options=options
            )
        return self._anon_async_client

    async def close(self) -> None:
        """Close the underlying httpx.AsyncClient connections."""
        for http_client in (
            getattr(self, "_async_http_client", None),
            getattr(self._anon_async_client, "_httpx_client", None)
            if self._anon_async_client
            else None,
        ):
            if http_client is not None:
                try:
                    await http_client.aclose()
                except Exception:
                    logger.debug(
                        "Failed to close async Supabase HTTP client cleanly",
                        exc_info=True,
                    )


async def get_async_service() -> AsyncSupabaseService:
    """Get the singleton AsyncSupabaseService instance.

    Returns:
        The AsyncSupabaseService singleton instance.
    """
    return await AsyncSupabaseService.get_instance()


async def get_async_client() -> AsyncClient:
    """Get the primary async Supabase client (service role).

    Convenience shortcut for ``(await get_async_service()).client``.

    Returns:
        The async Supabase AsyncClient instance.
    """
    service = await get_async_service()
    return service.client


async def get_async_anon_client() -> AsyncClient:
    """Get an async client with anon key for public operations.

    Returns:
        An async Supabase AsyncClient with anon key.
    """
    service = await get_async_service()
    return await service.get_anon_client()


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


def get_client_stats() -> dict[str, Any]:
    """Get statistics about the Supabase client (sync and async).

    Returns:
        Dictionary with client statistics including async client status.
    """
    global _client_creation_count

    return {
        "client_created": _client_creation_count > 0,
        "creation_count": _client_creation_count,
        "is_singleton": True,
        "max_connections": int(os.getenv("SUPABASE_MAX_CONNECTIONS", "50")),
        "async_client_active": AsyncSupabaseService._instance is not None
        and AsyncSupabaseService._client is not None,
    }


def invalidate_client() -> None:
    """Invalidate the cached client instance (both sync and async).

    Useful for testing, credential rotation, or connection recovery.
    Clears both the sync SupabaseService and async AsyncSupabaseService singletons.
    """
    # Close sync HTTP clients
    service = SupabaseService._instance
    if service is not None:
        for http_client in (
            getattr(service, "_service_http_client", None),
            getattr(service, "_anon_http_client", None),
        ):
            if http_client is not None:
                try:
                    http_client.close()
                except Exception:
                    logger.debug(
                        "Failed to close Supabase HTTP client cleanly", exc_info=True
                    )

    # Schedule async client close if event loop is running
    async_service = AsyncSupabaseService._instance
    if async_service is not None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(async_service.close())
        except RuntimeError:
            # No running event loop — just clear references
            pass

    get_supabase_service.cache_clear()
    global _client_creation_count
    _client_creation_count = 0
    SupabaseService._client = None
    SupabaseService._instance = None
    AsyncSupabaseService._client = None
    AsyncSupabaseService._instance = None
    logger.warning("Supabase client cache invalidated (sync + async)")


get_supabase_client = get_client
