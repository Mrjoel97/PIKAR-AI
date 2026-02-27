
import os
import asyncio
from supabase import create_client, Client

# Use the env vars
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Error: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    exit(1)

async def test_supabase():
    print(f"Testing Supabase connection to: {url}")
    try:
        # Initialize client
        supabase: Client = create_client(url, key)
        
        # Try a simple select. Assuming 'users' table or similar exists? 
        # Or just 'auth.users' if service role?
        # Let's try to query a known public table or just check health?
        # Supabase doesn't have a simple "ping".
        # We'll try to list buckets as it's usually harmless? or query a table.
        # Let's try to access auth users (service role can do this)
        
        print("Fetching users (limit 1)...")
        response = supabase.auth.admin.list_users(page=1, per_page=1)
        print(f"Success! Found {len(response.users)} users.")
        
    except Exception as e:
        print(f"Supabase Client Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_supabase())
