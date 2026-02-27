import os
import sys
import asyncio
from dotenv import load_dotenv

# Load env vars
load_dotenv('app/.env')

# Force API key mode
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

print("--- Starting Model Test ---")

try:
    print("Importing Gemini...")
    from google.adk.models import Gemini
    from google.genai import types
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

async def test_generate():
    print("Initializing Gemini model 'gemini-2.0-flash'...")
    try:
        model = Gemini(model="gemini-2.0-flash")
    except Exception as e:
        print(f"Model ID Error: {e}")
        return

    print("Generating content...")
    try:
        # prompt = "Hello"
        # response = await model.generate_content(prompt) # Is it async?
        # Check if generate_content is async. In ADK 0.1, it might differ.
        # But usually ADK models support async.
        
        # Actually ADK Model interface:
        # response = await model.generate_content(content)
        
        content = types.Content(
            role="user",
            parts=[types.Part(text="Hello, are you working?")]
        )
        
        response = await model.generate_content(content)
        print(f"Response: {response}")
        
    except Exception as e:
        print(f"Generation Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_generate())
