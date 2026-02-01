"""BaseService - Base class for authenticated Supabase services.

This module provides a base service class that properly authenticates with
Supabase using user JWT tokens, ensuring RLS policies are applied correctly.

Following supabase-best-practices skill guidelines:
- api-service-role-server-only: Never expose service role key in client-facing services
- auth-jwt-claims-validation: Always validate JWT claims
- rls-explicit-auth-check: Use explicit auth.uid() checks (enabled via proper JWT)
"""

import os
import logging
from typing import Optional
from supabase import create_client, Client

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
                return self.client.table("items").select("*").execute()
    """
    
    def __init__(self, user_token: Optional[str] = None):
        """Initialize the service with optional user authentication.
        
        Args:
            user_token: JWT token from the authenticated user. If provided,
                       the client will respect RLS policies for that user.
                       If None, the client will have limited access based on
                       anon policies.
        """
        self._url = os.environ.get("SUPABASE_URL")
        self._anon_key = os.environ.get("SUPABASE_ANON_KEY")
        self._user_token = user_token
        self._client: Optional[Client] = None
        
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
                    refresh_token=""  # Not needed for API calls
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


class AdminService:
    """Base service class for admin operations requiring service role.
    
    WARNING: Only use this for server-side admin operations that need to
    bypass RLS (e.g., system maintenance, analytics aggregation).
    
    NEVER use this for user-facing endpoints!
    """
    
    def __init__(self):
        """Initialize the admin service with service role key."""
        self._url = os.environ.get("SUPABASE_URL")
        self._service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        self._client: Optional[Client] = None
        
        if not self._url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not self._service_key:
            logger.warning("SUPABASE_SERVICE_ROLE_KEY not set - admin operations will fail")
    
    @property
    def client(self) -> Client:
        """Get the admin Supabase client (bypasses RLS).
        
        Returns:
            Supabase client with service role privileges.
        """
        if self._client is None:
            if not self._service_key:
                raise ValueError("Service role key required for admin operations")
            self._client = create_client(self._url, self._service_key)
        
        return self._client


__all__ = [
    "BaseService",
    "AdminService",
]

