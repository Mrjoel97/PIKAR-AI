import os
from supabase import create_client, Client

def get_service_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        # Fallback to loading from .env file for local scripts if needed, 
        # though usually handled by app environment.
        raise ValueError("Supabase URL and Service Role Key must be set")
    return create_client(url, key)
