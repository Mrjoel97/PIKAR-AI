import os
import asyncio
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Ensure env vars are loaded if possible (dotenv)
from dotenv import load_dotenv
load_dotenv()

# Set dummy credentials if needed to bypass strict checks in some libs, 
# although ADK usually relies on google-auth.
# os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "dummy_path_if_needed")

async def test_agent():
    print("Importing executive_agent...")
    try:
        from app.agent import executive_agent
        print("Agent imported successfully.")
    except Exception as e:
        print(f"Failed to import agent: {e}")
        return

    print("Setting up session...")
    session_service = InMemorySessionService()
    session = await session_service.create_session(user_id="test_user", app_name="test")
    runner = Runner(agent=executive_agent, session_service=session_service, app_name="test")

    print("Sending prompt: 'Hello, are you responsive?'")
    message = types.Content(
        role="user", parts=[types.Part.from_text(text="Hello, are you responsive?")]
    )


    try:
        print("Running agent...")
        # Try StreamingMode.SSE as seen in tests
        
        events = runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
        
        count = 0
        for event in events:
            count += 1
            print(f"Event {count}: {event}")
            
        print(f"Total events: {count}")
        if count > 0:
            print("SUCCESS: Agent produced events.")
        else:
            print("FAILURE: Agent produced no events.")

    except Exception as e:
        print(f"ERROR during execution: {e}")
        try:
            print(f"Available StreamingMode: {[m for m in dir(StreamingMode) if not m.startswith('_')]}")
        except:
            pass
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent())
