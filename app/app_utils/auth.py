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

import jwt
from fastapi import Header, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.supabase import get_service_client
from supabase import Client

logger = logging.getLogger(__name__)
security = HTTPBearer()


def _is_strict_auth_mode() -> bool:
    """Check if strict authentication mode is enabled."""
    return os.environ.get("REQUIRE_STRICT_AUTH", "0") == "1"


def get_supabase_client() -> Client:
    """Get a Supabase client instance from centralized service."""
    return get_service_client()


def _get_jwt_secret() -> str | None:
    """Get the JWT secret for token verification."""
    return os.environ.get("SUPABASE_JWT_SECRET")


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """Verify the Supabase JWT token."""
    token = credentials.credentials
    supabase = get_supabase_client()

    try:
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            logger.warning("Invalid token provided")
            raise HTTPException(
                status_code=401, detail="Invalid authentication credentials"
            )

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
            "role": user_response.user.role,
        }

        jwt_secret = _get_jwt_secret()
        if jwt_secret:
            try:
                decoded = jwt.decode(
                    token,
                    jwt_secret,
                    algorithms=["HS256"],
                    options={"verify_aud": False},
                )
                user_data["jwt_claims"] = decoded
            except jwt.InvalidTokenError as e:
                logger.warning("JWT signature verification failed")
                raise HTTPException(status_code=401, detail="JWT signature verification failed") from e

        return user_data

    except HTTPException:
        raise
    except Exception:
        logger.error("Token verification failed")
        raise HTTPException(status_code=401, detail="Could not validate credentials")


def get_user_id_from_token(token: str) -> str | None:
    """Extract user ID from a raw JWT token string with verification."""
    jwt_secret = _get_jwt_secret()
    if not jwt_secret:
        logger.warning("JWT_SECRET not configured, cannot verify token locally")
        return None

    try:
        decoded = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return decoded.get("sub")
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid token provided for local user-id extraction")
        return None


def get_user_id_from_bearer_token(token: str) -> str | None:
    """Verify the Bearer token with Supabase and return the user ID."""
    if not token or not token.strip():
        if _is_strict_auth_mode():
            logger.warning("Strict auth mode: rejecting missing token")
            raise HTTPException(status_code=401, detail="Authentication required")
        return None

    try:
        supabase = get_supabase_client()
        logger.info("Validating bearer token with Supabase")
        user_response = supabase.auth.get_user(token.strip())
        if user_response and user_response.user:
            logger.info(
                "Bearer token validation succeeded for user %s", user_response.user.id
            )
            return user_response.user.id

        logger.warning("Bearer token validation returned no user")
        if _is_strict_auth_mode():
            logger.warning("Strict auth mode: rejecting invalid token")
            raise HTTPException(
                status_code=401, detail="Invalid authentication credentials"
            )

    except Exception:
        logger.warning("Bearer token validation failed with Supabase")
        if _is_strict_auth_mode():
            raise HTTPException(status_code=401, detail="Authentication failed")

    return None


def verify_token_fast(token: str) -> dict | None:
    """Fast token verification using JWT without Supabase call."""
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
            },
        )
        return decoded
    except jwt.ExpiredSignatureError:
        logger.debug("Token has expired")
        return None
    except jwt.InvalidTokenError:
        logger.debug("Invalid token for fast verification")
        return None


def verify_service_auth(
    x_service_secret: str = Header(None, alias="X-Service-Secret"),
) -> bool:
    """Verify internal service-to-service authentication header."""
    expected_secret = os.environ.get("WORKFLOW_SERVICE_SECRET")
    if not expected_secret:
        logger.warning(
            "Service authentication is not configured: WORKFLOW_SERVICE_SECRET is missing"
        )
        raise HTTPException(
            status_code=500, detail="Service authentication not configured"
        )

    provided_secret = x_service_secret or ""
    if not secrets.compare_digest(provided_secret, expected_secret):
        logger.warning(
            "Unauthorized service request received for workflow service endpoint"
        )
        raise HTTPException(status_code=401, detail="Unauthorized service request")

    return True
