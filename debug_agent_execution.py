
import asyncio
import os
import sys
from dotenv import load_dotenv

# Load env
load_dotenv()

print("Environment loaded.")
print(f"Supabase URL present: {bool(os.getenv('SUPABASE_URL'))}")

try:
    print("Importing root_agent from agent.py...")
    from agent import root_agent
    print(f"Agent loaded: {root_agent.name}")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

async def main():
    print("Starting test run...")
    try:
        # Create a mock session if needed, but run_async handles it usually?
        # ADK agent.run_async() takes 'input' as string.
        
        # Cleaning up event loop issues logic
        # run_async is an async generator, so we iterate
        print("Inspecting run_async signature...")
        # Since root_agent is now an App, we must access the internal agent
        if hasattr(root_agent, 'root_agent'):
            agent_for_inspect = root_agent.root_agent
        else:
            agent_for_inspect = root_agent
            
        import inspect
        print(f"Signature: {inspect.signature(agent_for_inspect.run_async)}")
        
        # Try to guess usage.
        # If signature is (context, user_input, ...)
        # We might need to construct a context.
        # Try to guess usage.
        # Signature is (parent_context: InvocationContext)
        
        from google.adk.agents import InvocationContext
        from google.adk.events import Event, EventActions
        from google.genai import types as genai_types
        
        # We need a Session. ADK usually has it in `google.adk.session` or `google.adk.core`
        # Let's try likely locations or use a stub if type checking is loose.
        try:
            from google.adk.sessions.session import Session
        except ImportError:
            print("Could not import Session from google.adk.sessions.session, trying top level")
            # This handles the case where package structure vs file structure differs
            # Based on file find: sessions\session.py -> google.adk.sessions.session
            pass
        
        session = Session(id="debug-session")
        
        # Inject user message into session events or state
        # Standard ADK pattern for LlmAgent is usually retrieving from last event
        user_msg = Event(
            author="user",
            content=genai_types.Content(parts=[genai_types.Part(text="Hello, can you hear me?")]),
            actions=EventActions()
        )
        session.events.append(user_msg)
        
        context = InvocationContext(session=session, agent=root_agent)
        
        
        print("Sending message to agent with context...")
        # Since root_agent is now an App, we must access the internal agent
        if hasattr(root_agent, 'root_agent'):
            agent_instance = root_agent.root_agent
        else:
            agent_instance = root_agent # Fallback if it is an Agent
            
        print(f"Using agent: {agent_instance.name}")
        response_stream = agent_instance.run_async(context)
        
        print("\n--- RESPONSE STREAM ---")
        async for chunk in response_stream:
             print(f"Chunk: {chunk}")
        print("\n----------------")
    except Exception as e:
        print(f"\nExecution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
