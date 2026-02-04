import os
import functools
import logging
from typing import Dict, Any, Optional
import httpx
from supabase import create_client, Client

# Configure logging
logger = logging.getLogger(__name__)

# Metrics counter
_client_creation_count = 0

def get_client_stats() -> Dict[str, Any]:
    """Return metrics about the Supabase client connection pool."""
    is_cached = _client_creation_count > 0
    
    stats = {
        "client_created": is_cached,
        "creation_count": _client_creation_count,
        "is_singleton": True,
        "max_connections": int(os.getenv("SUPABASE_MAX_CONNECTIONS", "50"))
    }
    
    # Try to access pool stats if client exists
    try:
        current_client = get_service_client()
        # Access internal httpx client stats if available
        # This depends on the Supabase client implementation details
        if hasattr(current_client, 'options') and hasattr(current_client.options, 'http_client'):
             http_client = current_client.options.http_client
             if hasattr(http_client, '_transport') and hasattr(http_client._transport, '_pool'):
                 pool = http_client._transport._pool
                 stats["pool_connections"] = len(pool._connections)
    except Exception:
        pass
        
    return stats

def invalidate_service_client():
    """Clear the cached service client. 
    
    Useful for testing, credential rotation, or connection recovery.
    """
    get_service_client.cache_clear()
    logger.warning("Supabase service client cache invalidated")

@functools.lru_cache(maxsize=1)
def get_service_client() -> Client:
    """Get the Supabase service client as a singleton.
    
    Uses lru_cache to maintain a single instance of the client across the application.
    This provides thread-safe connection pooling behavior.
    """
    global _client_creation_count
    _client_creation_count += 1
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        # Fallback to loading from .env file for local scripts if needed, 
        # though usually handled by app environment.
        raise ValueError("Supabase URL and Service Role Key must be set")
    
    # Configure client options with connection limits
    try:
        from supabase.lib.client_options import ClientOptions
        
        # Parse connection limits from environment
        max_connections = int(os.getenv("SUPABASE_MAX_CONNECTIONS", "50"))
        timeout = float(os.getenv("SUPABASE_TIMEOUT", "60.0"))
        
        # Configure httpx limits
        limits = httpx.Limits(
            max_keepalive_connections=max_connections, 
            max_connections=max_connections, 
            keepalive_expiry=60.0
        )
        
        # Create custom http client with limits
        http_client = httpx.AsyncClient(
            limits=limits, 
            timeout=httpx.Timeout(timeout)
        )
        
        options = ClientOptions(
            postgrest_client_timeout=timeout,
        )
        
        logger.info(f"Supabase service client initialized (singleton) with timeout={timeout}, max_connections={max_connections}")
        return create_client(url, key, options=options, http_client=http_client)
        
    except ImportError:
        logger.warning("Could not import ClientOptions, using default configuration")
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Error configuring Supabase client options: {e}")
        return create_client(url, key)
