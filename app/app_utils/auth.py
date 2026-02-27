"""Authentication utilities for Pikar-AI.

This module provides functions to verify Supabase JWT tokens and extract user identity,
ensuring secure backend communication.

Security Policy:
================
This module supports two authentication modes controlled by REQUIRE_STRICT_AUTH env var:

1. STRICT MODE (REQUIRE_STRICT_AUTH=1) - RECOMMENDED for production:
   - Invalid tokens are rejected with 401 Unauthorized
   - Missing tokens are rejected unless ALLOW_ANONYMOUS_CHAT=1
   - Token verification failures are treated as security events
   
2. PERMISSIVE MODE (default for development):
   - Invalid tokens log warnings but may allow anonymous access
   - Missing tokens allow anonymous access if ALLOW_ANONYMOUS_CHAT=1
   - Useful for development and testing

For production deployments, set:
- REQUIRE_STRICT_AUTH=1
- SUPABASE_JWT_SECRET=<your-jwt-secret>
- ALLOW_ANONYMOUS_CHAT=0 (or omit)
"""

import logging
import os
import secrets
from typing import Optional

import jwt
from fastapi import HTTPException, Header, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client

from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)
security = HTTPBearer()


def _is_strict_auth_mode() -> bool:
    """Check if strict authentication mode is enabled.
    
    When True, authentication failures are treated as security violations
    and result in 401 responses. When False (default), the system may
    allow anonymous access in certain scenarios.
    """
    return os.environ.get("REQUIRE_STRICT_AUTH", "0") == "1"


def get_supabase_client() -> Client:
    """Get a Supabase client instance from centralized service."""
    return get_service_client()


def _get_jwt_secret() -> Optional[str]:
    """Get the JWT secret for token verification.

    For Supabase, this is the SUPABASE_JWT_SECRET or derived from the anon key.
    Falls back to None if not available (will rely on Supabase Auth).
    """
    return os.environ.get("SUPABASE_JWT_SECRET")


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """Verify the Supabase JWT token.

    This function verifies the token with Supabase Auth (primary method)
    and optionally validates JWT signature if secret is available.

    Args:
        credentials: The HTTP Bearer credentials.

    Returns:
        The user dictionary if valid.

    Raises:
        HTTPException: If token is invalid or user not found.
    """
    token = credentials.credentials
    supabase = get_supabase_client()

    try:
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            logger.warning("Invalid token provided")
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        user_metadata = user_response.user.user_metadata
        app_metadata = getattr(user_response.user, "app_metadata", None)
        if isinstance(user_metadata, dict):
            metadata = {**user_metadata, "app_metadata": app_metadata or {}}
        else:
            metadata = {
                "user_metadata": user_metadata,
                "app_metadata": app_metadata or {},
            }

        user_data = {
            "id": user_response.user.id,
            "email": user_response.user.email,
            "metadata": metadata,
            "role": user_response.user.role
        }

        jwt_secret = _get_jwt_secret()
        if jwt_secret:
            try:
                decoded = jwt.decode(
                    token,
                    jwt_secret,
                    algorithms=["HS256"],
                    options={"verify_aud": False}
                )
                user_data["jwt_claims"] = decoded
            except jwt.InvalidTokenError as e:
                logger.warning(f"JWT signature verification failed: {e}")

        return user_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Could not validate credentials")


def get_user_id_from_token(token: str) -> Optional[str]:
    """Extract user ID from a raw JWT token string with optional verification.

    For security, this now requires the JWT secret to be available for verification.
    If no secret is available, returns None for safety.

    Args:
        token: The JWT token string.

    Returns:
        The user ID or None if verification fails or secret not available.
    """
    jwt_secret = _get_jwt_secret()
    if not jwt_secret:
        logger.warning("JWT_SECRET not configured, cannot verify token locally")
        return None

    try:
        decoded = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        return decoded.get("sub")
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


def get_user_id_from_bearer_token(token: str) -> Optional[str]:
    """Verify the Bearer token with Supabase and return the user ID.

    Use when the request body does not include user_id (e.g. SSE chat) so the
    backend can still identify the authenticated user from the Authorization header.

    This method always verifies with Supabase Auth for security.

    Security Behavior:
        - In STRICT mode: Raises HTTPException on invalid/missing tokens
        - In PERMISSIVE mode: Returns None on failure (caller decides behavior)

    Args:
        token: The JWT Bearer token string.

    Returns:
        The user's UUID string or None if invalid/missing (in permissive mode).

    Raises:
        HTTPException: In strict mode, if token is invalid or missing.
    """
    if not token or not token.strip():
        if _is_strict_auth_mode():
            logger.warning("Strict auth mode: rejecting missing token")
            raise HTTPException(status_code=401, detail="Authentication required")
        return None

    try:
        supabase = get_supabase_client()
        logger.info(f"Attempting to validate token: {token[:10]}...{token[-10:] if len(token) > 20 else ''}")
        user_response = supabase.auth.get_user(token.strip())
        if user_response and user_response.user:
            logger.info(f"Successfully validated token for user {user_response.user.id}")
            return user_response.user.id
            
        # If we reach here, token was provided but no user was returned without an exception
        logger.warning(f"get_user_id_from_bearer_token: No user returned from Supabase get_user. Response: {user_response}")
        if _is_strict_auth_mode():
            logger.warning("Strict auth mode: rejecting invalid token")
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
            
    except Exception as e:
        logger.warning(f"Could not get user from Bearer token: {e}", exc_info=True)
        if _is_strict_auth_mode():
            raise HTTPException(status_code=401, detail="Authentication failed")

    return None

def verify_token_fast(token: str) -> Optional[dict]:
    """Fast token verification using JWT without Supabase call.

    WARNING: This method only verifies JWT structure and signature.
    It does NOT check if the token has been revoked or if the user still exists.
    Use this only for performance-critical paths where you have validated
    the token recently via verify_token or get_user_id_from_bearer_token.

    Args:
        token: The JWT token string.

    Returns:
        Decoded token claims or None if invalid.
    """
    jwt_secret = _get_jwt_secret()
    if not jwt_secret:
        logger.warning("JWT_SECRET not configured for fast verification")
        return None

    try:
        decoded = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={
                "verify_aud": False,
                "verify_exp": True,
                "verify_iat": True,
            }
        )
        return decoded
    except jwt.ExpiredSignatureError:
        logger.debug("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid token for fast verification: {e}")
        return None


def verify_service_auth(x_service_secret: str = Header(None, alias="X-Service-Secret")) -> bool:
    """Verify internal service-to-service authentication header."""
    expected_secret = os.environ.get("WORKFLOW_SERVICE_SECRET")
    if not expected_secret:
        logger.warning("Service authentication is not configured: WORKFLOW_SERVICE_SECRET is missing")
        raise HTTPException(status_code=500, detail="Service authentication not configured")

    provided_secret = x_service_secret or ""
    if not secrets.compare_digest(provided_secret, expected_secret):
        logger.warning("Unauthorized service request received for workflow service endpoint")
        raise HTTPException(status_code=401, detail="Unauthorized service request")

    return True
