
import asyncio
import os
import sys
import logging
from unittest.mock import MagicMock

# Configure logging
logging.basicConfig(level=logging.ERROR)

# Add project root to path
sys.path.append(os.getcwd())

# Mock dependencies
sys.modules['app.services.request_context'] = MagicMock()
sys.modules['app.services.request_context'].get_current_user_id.return_value = "test_user"

# Needed for supabase client in media.py
os.environ["SUPABASE_URL"] = "https://example.supabase.co"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "mock_key"

# Set Google Credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.getcwd(), "secrets", "my-project-pk-484623-c72b7850d9d5.json")

from app.agents.tools import media

async def debug_video():
    print("--- Debugging Video Generation ---")
    print(f"Directory: {os.getcwd()}")
    print(f"GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
    print(f"GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
    print(f"REMOTION_RENDER_ENABLED: {os.getenv('REMOTION_RENDER_ENABLED')}")
    
    print("\nAttempting to generate video...")
    result = await media.generate_video("Test video prompt", duration_seconds=4)
    print(f"\nResult Success: {result.get('success')}")
    if not result.get('success'):
        print(f"Error: {result.get('error')}")
        print(f"User Message: {result.get('user_message')}")

if __name__ == "__main__":
    asyncio.run(debug_video())
