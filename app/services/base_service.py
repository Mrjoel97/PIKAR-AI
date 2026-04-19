# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""BaseService - Base classes for authenticated Supabase services.

This module provides sync and async base service classes that properly
authenticate with Supabase using user JWT tokens, ensuring RLS policies
are applied correctly.

Sync classes (``BaseService``, ``AdminService``): Use the sync Client.
Async classes (``AsyncBaseService``, ``AsyncAdminService``): Use the
async Client with native async execution (no thread pool overhead).

Following supabase-best-practices skill guidelines:
- api-service-role-server-only: Never expose service role key in client-facing services
- auth-jwt-claims-validation: Always validate JWT claims
- rls-explicit-auth-check: Use explicit auth.uid() checks (enabled via proper JWT)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from app.app_utils.env import get_stripped_env
from app.services.supabase_async import execute_async
from app.services.supabase_client import get_async_client
from supabase import Client, create_client

logger = logging.getLogger(__name__)


class BaseService:
    """Base service class with proper user authentication.

    This class creates Supabase clients that respect RLS policies by:
    1. Using the ANON key (not service role key)
    2. Setting the user's JWT token for authentication

    Usage:
        class MyService(BaseService):
            def __init__(self, user_token: Optional[str] = None):
                super().__init__(user_token)

            async def get_items(self):
                return await self.execute(self.client.table("items").select("*"), op_name="items.list")
    """

    def __init__(self, user_token: str | None = None):
        """Initialize the service with optional user authentication.

        Args:
            user_token: JWT token from the authenticated user. If provided,
                       the client will respect RLS policies for that user.
                       If None, the client will have limited access based on
                       anon policies.
        """
        self._url = get_stripped_env("SUPABASE_URL")
        self._anon_key = get_stripped_env("SUPABASE_ANON_KEY")
        self._user_token = user_token
        self._client: Client | None = None

        if not self._url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not self._anon_key:
            raise ValueError("SUPABASE_ANON_KEY environment variable is required")

    @property
    def client(self) -> Client:
        """Get the authenticated Supabase client.

        Creates the client lazily and sets the user token if provided.

        Returns:
            Authenticated Supabase client.
        """
        if self._client is None:
            self._client = create_client(self._url, self._anon_key)

            # Set user JWT token for authentication
            if self._user_token:
                self._client.auth.set_session(
                    access_token=self._user_token,
                    refresh_token="",  # Not needed for API calls
                )

        return self._client

    def set_user_token(self, token: str) -> None:
        """Update the user token for subsequent requests.

        This is useful when the token is obtained after service initialization.

        Args:
            token: JWT token from the authenticated user.
        """
        self._user_token = token
        # Force client recreation on next access
        self._client = None

    @property
    def is_authenticated(self) -> bool:
        """Check if the service has a user token set.

        Returns:
            True if a user token is set, False otherwise.
        """
        return self._user_token is not None

    async def execute(
        self,
        query_builder: Any,
        *,
        timeout: float | None = None,
        op_name: str | None = None,
    ) -> Any:
        """Execute a blocking Supabase query without blocking the event loop."""
        return await execute_async(query_builder, timeout=timeout, op_name=op_name)


class AdminService:
    """Base service class for admin operations requiring service role.

    WARNING: Only use this for server-side admin operations that need to
    bypass RLS (e.g., system maintenance, analytics aggregation).

    NEVER use this for user-facing endpoints!
    """

    def __init__(self):
        """Initialize the admin service with service role key."""
        self._url = get_stripped_env("SUPABASE_URL")
        self._service_key = get_stripped_env("SUPABASE_SERVICE_ROLE_KEY")
        self._client: Client | None = None

        if not self._url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not self._service_key:
            logger.warning(
                "SUPABASE_SERVICE_ROLE_KEY not set - admin operations will fail"
            )

    @property
    def client(self) -> Client:
        """Get the admin Supabase client (bypasses RLS).

        Returns:
            Supabase client with service role privileges.
        """
        if self._client is None:
            # Use cached singleton for admin operations
            from app.services.supabase import get_service_client

            self._client = get_service_client()

        return self._client


class AsyncBaseService:
    """Async base service class with proper user authentication.

    Uses the async Supabase client for native async execution.
    For RLS-protected operations, creates per-request async clients
    with the user's JWT token.

    Usage::

        class MyService(AsyncBaseService):
            def __init__(self, user_token: str | None = None):
                super().__init__(user_token)

            async def get_items(self):
                client = await self.get_client()
                return await self.execute(
                    client.table("items").select("*"), op_name="items.list"
                )
    """

    def __init__(self, user_token: str | None = None):
        """Initialize the async service with optional user authentication.

        Args:
            user_token: JWT token from the authenticated user. If provided,
                       the client will respect RLS policies for that user.
        """
        self._url = get_stripped_env("SUPABASE_URL")
        self._anon_key = get_stripped_env("SUPABASE_ANON_KEY")
        self._user_token = user_token

        if not self._url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not self._anon_key:
            raise ValueError("SUPABASE_ANON_KEY environment variable is required")

    async def get_client(self):
        """Get the authenticated async Supabase client.

        If a user token is set, creates a per-request async client with
        proper RLS authentication. Otherwise returns the shared async client.

        Returns:
            Async Supabase client.
        """
        if self._user_token:
            # Per-request client with user JWT for RLS
            from supabase._async.client import create_client as create_async_client
            from supabase.lib.client_options import AsyncClientOptions

            client = await create_async_client(
                self._url,
                self._anon_key,
                options=AsyncClientOptions(),
            )
            await client.auth.set_session(
                access_token=self._user_token,
                refresh_token="",
            )
            return client
        # Service-level shared async client
        return await get_async_client()

    def set_user_token(self, token: str) -> None:
        """Update the user token for subsequent requests.

        Args:
            token: JWT token from the authenticated user.
        """
        self._user_token = token

    @property
    def is_authenticated(self) -> bool:
        """Check if the service has a user token set."""
        return self._user_token is not None

    async def execute(
        self,
        query_builder: Any,
        *,
        timeout: float | None = None,
        op_name: str | None = None,
    ) -> Any:
        """Execute an async Supabase query directly (no thread pool)."""
        return await execute_async(query_builder, timeout=timeout, op_name=op_name)


class AsyncAdminService:
    """Async base service class for admin operations requiring service role.

    WARNING: Only use this for server-side admin operations that need to
    bypass RLS (e.g., system maintenance, analytics aggregation).

    NEVER use this for user-facing endpoints!
    """

    def __init__(self):
        """Initialize the async admin service."""
        self._url = get_stripped_env("SUPABASE_URL")
        self._service_key = get_stripped_env("SUPABASE_SERVICE_ROLE_KEY")

        if not self._url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not self._service_key:
            logger.warning(
                "SUPABASE_SERVICE_ROLE_KEY not set - admin operations will fail"
            )

    async def get_client(self):
        """Get the admin async Supabase client (bypasses RLS).

        Returns the shared async client with service role key.

        Returns:
            Async Supabase client with service role privileges.
        """
        return await get_async_client()

    async def execute(
        self,
        query_builder: Any,
        *,
        timeout: float | None = None,
        op_name: str | None = None,
    ) -> Any:
        """Execute an async Supabase query directly (no thread pool)."""
        return await execute_async(query_builder, timeout=timeout, op_name=op_name)


__all__ = [
    "AdminService",
    "AsyncAdminService",
    "AsyncBaseService",
    "BaseService",
]
