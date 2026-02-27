
import os
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_veo():
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    model_id = "veo-3.1-generate-001" 

    print(f"Checking Veo configuration:")
    print(f"  Project: {project}")
    print(f"  Location: {location}")
    print(f"  Model: {model_id}")

    try:
        from google import genai
        from google.genai.types import GenerateVideosConfig
        print("Successfully imported google.genai")
    except ImportError as e:
        print(f"ERROR: Failed to import google.genai: {e}")
        return

    try:
        client = genai.Client(vertexai=True, project=project, location=location)
        print("Successfully created genai Client")
    except Exception as e:
        print(f"ERROR: Failed to create genai Client: {e}")
        return

    print("Attempting to generate a short 4s video...")
    try:
        config = GenerateVideosConfig(
            aspect_ratio="16:9",
            duration_seconds=4,
            generate_audio=False
        )

        response = client.models.generate_videos(
            model=model_id,
            prompt="A cinematic drone shot of a futuristic city at sunset, 4k, detailed",
            config=config,
        )
        
        print(f"Operation started. Name: {response.name}")
        
        # We won't wait for the full generation to avoid blocking too long, 
        # but starting the operation successfully proves access/quota.
        print("SUCCESS: Veo API call initiated successfully.")
        
    except Exception as e:
        print(f"ERROR: Veo generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_veo()
