import os
import sys

# Force API key mode (bypass Vertex auth lookup)
os.environ["GOOGLE_API_KEY"] = "AIzaSyFakeKeyForTestingImports"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

print("Importing google.genai with fake API key...")
try:
    import google.genai
    print("Imported google.genai")
except Exception as e:
    print(f"Error importing google.genai: {e}")

print("Importing google.cloud.aiplatform...")
try:
    # This might still hang if it initializes on import, but usually it waits for use.
    import google.cloud.aiplatform
    print("Imported google.cloud.aiplatform")
except Exception as e:
    print(f"Error importing google.cloud.aiplatform: {e}")

print("Done.")
