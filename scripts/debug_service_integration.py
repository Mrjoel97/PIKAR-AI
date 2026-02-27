
import os
import sys
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_integration")

# Add project root to path
sys.path.append(os.getcwd())

# Ensure env vars are set (simulating app start)
# In real app, these come from .env loading.
# We'll rely on the module reading os.environ, but we need to load .env first if not present options.
from dotenv import load_dotenv
load_dotenv()

# We need to ensure we have credentials. 
# In the app, standard google auth is used.
# If running locally, we might need to point to the secrets file if not auto-discovered.
secrets_file = os.path.join(os.getcwd(), "secrets", "my-project-pk-484623-c72b7850d9d5.json")
if os.path.exists(secrets_file):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = secrets_file
    print(f"Set GOOGLE_APPLICATION_CREDENTIALS to {secrets_file}")

print("Importing app.services.vertex_video_service...")
try:
    from app.services import vertex_video_service
    print("Successfully imported app.services.vertex_video_service")
except Exception as e:
    print(f"Failed to import service: {e}")
    sys.exit(1)

def test_generation():
    print("Testing generate_video...")
    prompt = "A cinematic drone shot of a waterfall"
    
    # helper to print result
    def run():
        result = vertex_video_service.generate_video(prompt, duration_seconds=6)
        print("Result:")
        print(f"Success: {result.get('success')}")
        if not result.get('success'):
            print(f"Error: {result.get('error')}")
            print(f"Model Used: {result.get('model_used')}")
        else:
            print("Video URL:", result.get('video_url'))
            print("Video Bytes Len:", len(result.get('video_bytes') or []) if result.get('video_bytes') else "None")

    run()

if __name__ == "__main__":
    test_generation()
