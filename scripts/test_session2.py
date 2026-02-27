import sys
import os
import asyncio
import logging
import uuid
from app.persistence.supabase_session_service import SupabaseSessionService

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.DEBUG)

async def run():
    service = SupabaseSessionService()
    try:
        session = await service.get_session(
            app_name="agents",
            user_id=uuid.uuid4(),
            session_id="test-123"
        )
        print("RESULT:")
        print(session)
    except Exception as e:
        print("EXCEPTION:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
