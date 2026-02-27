import asyncio
import os
import sys
import logging

# Add project root to path
sys.path.append(os.getcwd())

# Load env vars
from dotenv import load_dotenv
load_dotenv('app/.env')

# Fix for Agent Connection Hang: Force independent API key mode
if os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"
    print("Forced GOOGLE_GENAI_USE_VERTEXAI='0' based on API Key presence.")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_runner():
    print("--- Starting Runner Test ---")

    # Import dependencies
    try:
        print("Importing app.agent...")
        from app.agent import app as adk_app
        print("Importing SupabaseSessionService...")
        from app.persistence.supabase_session_service import SupabaseSessionService
        print("Importing Runner...")
        from google.adk.runners import Runner
        print("Importing ArtifactService...")
        from google.adk.artifacts import InMemoryArtifactService
        print("Importing genai_types...")
        from google.genai import types as genai_types
    except ImportError as e:
        print(f"Import Error: {e}")
        return

    # Initialize Services
    try:
        session_service = SupabaseSessionService()
        artifact_service = InMemoryArtifactService()
        
        runner = Runner(
            app=adk_app,
            artifact_service=artifact_service,
            session_service=session_service
        )
        print("Runner initialized successfully.")
    except Exception as e:
        print(f"Initialization Error: {e}")
        return

    # Define test parameters
    session_id = "test-session-dev-1"
    user_id = "test-user-dev-1"
    test_message = "Hello, who are you?"

    # Create session if needed
    print(f"Ensuring session {session_id} exists...")
    try:
        existing = await session_service.get_session(
            app_name=adk_app.name,
            user_id=user_id,
            session_id=session_id
        )
        if not existing:
            await session_service.create_session(
                app_name=adk_app.name,
                user_id=user_id,
                session_id=session_id
            )
            print("Session created.")
        else:
            print("Session exists.")
    except Exception as e:
        print(f"Session Error: {e}")
        return

    # Run Agent
    print(f"Sending message: '{test_message}'")
    adk_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=test_message)]
    )

    try:
        print("Calling runner.run_async...")
        stream = runner.run_async(
            session_id=session_id,
            new_message=adk_message,
            user_id=user_id
        )
        
        event_count = 0
        async for event in stream:
            event_count += 1
            print(f"Event received: {type(event)}")
            # Try to print content if available
            if hasattr(event, "content"):
                print(f"  Content: {event.content}")
            if hasattr(event, "tool_call"):
                print(f"  Tool Call: {event.tool_call}")
        
        print(f"Stream finished. Total events: {event_count}")
        
    except Exception as e:
        print(f"Execution Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_runner())
