
import os
import sys
from google import genai

project = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

print(f"Listing models for project {project} in {location}...")

try:
    client = genai.Client(vertexai=True, project=project, location=location)
    # List models - note: SDK might default to Gemini API if vertexai=True isn't fully propagated to list call
    # but let's try standard list
    
    # In google-genai 0.3+, it's client.models.list()
    # It returns an iterator
    pager = client.models.list()
    
    print("Available Models:")
    count = 0
    for model in pager:
        # print specific interesting models
        if "gemini" in model.name or "veo" in model.name:
            print(f" - {model.name} ({model.display_name})")
        count += 1
        
    print(f"Total models found: {count}")

except Exception as e:
    print(f"Error listing models: {e}")
