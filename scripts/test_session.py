import sys
import os
import asyncio
import logging

# Setup env vars for script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.DEBUG)

from app.persistence.supabase_session_service import SupabaseSessionService
from app.services.supabase_client import get_supabase_service

async def test():
    supabase = get_supabase_service().client
    response = supabase.table("user_configurations").select("user_id").limit(1).execute()
    users = response.data
    
    if not users:
        print("No users found in database.")
        return
        
    user_id = users[0]["user_id"]
    
    service = SupabaseSessionService()
    print("Fetching session...")
    try:
        session = await service.get_session(
            app_name="agents",
            user_id=user_id,
            session_id="test-12345"
        )
        if not session:
             print("Could not retrieve or create session.")
             return
             
        # Create a dummy ADK Event object to append
        from google.adk.events import Event, EventActions
        from google.genai import types as genai_types
        dummy_event = Event(
            invocation_id="test-inv-id",
            author="user",
            content=genai_types.Content(role="user", parts=[])
        )
        
        print("Appending event...")
        appended = await service.append_event(session=session, event=dummy_event)
        print("Appended successfully:", appended)
    except Exception as e:
        print("Exception caught:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
