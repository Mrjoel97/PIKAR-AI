import os
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request
from supabase import Client
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    try:
        return get_service_client()
    except Exception:
        logger.warning("Supabase credentials missing in rate limiter")
        return None

def get_user_persona_limit(request: Request = None) -> str:
    """
    Determines the rate limit based on the user's persona.
    Querying user_executive_agents table.
    """
    default_limit = "10/minute"
    
    if not request:
        return default_limit
    
    # 1. Extract User ID from Token
    user_id = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            supabase = get_supabase_client()
            if supabase:
                # We use get_user to verify the token
                user_response = supabase.auth.get_user(token)
                if user_response and user_response.user:
                    user_id = user_response.user.id
        except Exception as e:
            # Token might be invalid or expired. Fallback to default.
            logger.debug(f"Rate limiter auth check failed: {e}")

    if not user_id:
        # Fallback to solopreneur/default limit if no user identified
        return default_limit

    # 2. Query Persona
    try:
        supabase = get_supabase_client()
        if supabase:
            response = supabase.table("user_executive_agents").select("persona").eq("user_id", user_id).execute()
            if response.data:
                persona = response.data[0].get("persona")
                if persona == "solopreneur":
                    return "10/minute"
                elif persona == "startup":
                    return "30/minute"
                elif persona == "sme":
                    return "60/minute"
                elif persona == "enterprise":
                    return "120/minute"
    except Exception as e:
        logger.error(f"Rate limiter persona fetch failed: {e}")

    return default_limit

# Initialize Limiter
# We use get_remote_address as a fallback key, but ideally we'd want to key by user_id if available.
# However, for simplicity and following the specific instruction about LIMITS (not keys),
# we keep standard key_func or we can enhance it.
# Given the instructions didn't specify keying strategy modification, we use get_remote_address
# but the LIMIT value varies by persona.
limiter = Limiter(key_func=get_remote_address)
