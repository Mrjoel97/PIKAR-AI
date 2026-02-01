"""Authentication utilities for Pikar-AI.

This module provides functions to verify Supabase JWT tokens and extract user identity,
ensuring secure backend communication.
"""

import os
import logging
from typing import Optional
from supabase import create_client, Client
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)
security = HTTPBearer()

def get_supabase_client() -> Client:
    """Get a Supabase client instance."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables")
        raise RuntimeError("Supabase configuration missing")
        
    return create_client(url, key)

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """Verify the Supabase JWT token.
    
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
        # Verify token using Supabase Auth (GoTrue)
        user_response = supabase.auth.get_user(token)
        
        if not user_response or not user_response.user:
            logger.warning("Invalid token provided")
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
            
        return {
            "id": user_response.user.id,
            "email": user_response.user.email,
            "metadata": user_response.user.user_metadata,
            "role": user_response.user.role
        }
        
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Could not validate credentials")

def get_user_id_from_token(token: str) -> Optional[str]:
    """Extract user ID from a raw JWT token string without verification (fast path).
    
    Use this ONLY when the token has already been verified by a gateway or middleware.
    
    Args:
        token: The JWT token string.
        
    Returns:
        The user ID or None.
    """
    # Note: Requires pyjwt
    try:
        import jwt
        # We don't verify signature here as we assume it's done elsewhere or we don't have the secret handy efficiently
        # BUT for security, verify_token() above is preferred.
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded.get("sub")
    except ImportError:
        logger.warning("pyjwt not installed, cannot decode token locally")
        return None
    except Exception as e:
        logger.warning(f"Failed to decode token: {e}")
        return None
