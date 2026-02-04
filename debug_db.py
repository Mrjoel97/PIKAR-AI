import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

async def main():
    print(f"Loaded keys: {[k for k in os.environ.keys() if 'SUPABASE' in k]}")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        print(f"Error: Missing credentials. URL={bool(url)}, KEY={bool(key)}")
        return

    supabase: Client = create_client(url, key)

    print("--- User Executive Agents (Top 5) ---")
    try:
        response = supabase.table("user_executive_agents").select("*").limit(5).execute()
        for row in response.data:
            print(f"User: {row.get('user_id')}")
            print(f"  Onboarding Completed: {row.get('onboarding_completed')}")
            print(f"  Persona: {row.get('persona')}")
            print(f"  Config: {row.get('configuration', {}).keys()}")
    except Exception as e:
        print(f"Error querying table: {e}")

if __name__ == "__main__":
    asyncio.run(main())
