import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv('app/.env')

# Force API key mode
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"
print(f"GOOGLE_API_KEY present: {'GOOGLE_API_KEY' in os.environ}")

try:
    from google import genai
    from google.genai import types
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

async def test_genai():
    print("Initializing GenAI Client...")
    try:
        # Enable debug logging for http
        import logging
        logging.basicConfig(level=logging.DEBUG)
        
        # Explicitly set http options if possible, or just init
        client = genai.Client(
            api_key=os.environ.get("GOOGLE_API_KEY"),
            http_options={'api_version': 'v1beta'} # Try to force a version?
        )
        print("Client initialized.")
    except Exception as e:
        print(f"Client Init Error: {e}")
        return

    print("Generating content...")
    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents="Hello, purely testing genai."
        )
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Generation Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_genai())
