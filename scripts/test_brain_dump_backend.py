
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app.services.supabase_client import get_service_client
from app.agents.tools.brain_dump import process_brain_dump

async def test_brain_dump():
    print("Testing Brain Dump Backend...")
    
    # 1. Create a dummy test file
    test_filename = "test_brain_dump.txt"
    test_content = b"This is a test brain dump audio content (simulated)."
    # Note: The tool expects audio/video, but Gemini might just handle text if we trick mime type, 
    # OR we normally upload .webm. Let's use a .webm name even if content is text for this connection test.
    test_path = "brain-dumps/test_user/test.webm"
    
    try:
        client = get_service_client()
        print(f"Uploading test file to {test_path}...")
        
        # Upload
        res = client.storage.from_("knowledge-vault").upload(
            test_path,
            test_content,
            {"content-type": "audio/webm", "upsert": "true"}
        )
        print(f"Upload result: {res}")
        
        # 2. Call process_brain_dump
        print("Calling process_brain_dump...")
        result = await process_brain_dump(test_path, context="Test context")
        
        print("\n--- Result ---")
        print(result)
        
        if result.get("success"):
            print("SUCCESS: Brain dump processed.")
        else:
            print(f"FAILURE: {result.get('error')}")

    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_brain_dump())
