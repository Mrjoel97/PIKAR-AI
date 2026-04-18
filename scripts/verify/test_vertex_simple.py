#!/usr/bin/env python3
"""Simple test for Vertex AI setup."""

import os
import sys

# Load environment
from dotenv import load_dotenv
load_dotenv('app/.env')

print("=" * 50)
print("Vertex AI Quick Test")
print("=" * 50)

# Get config
project = os.environ.get("GOOGLE_CLOUD_PROJECT")
location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

print(f"\nProject: {project}")
print(f"Location: {location}")
print(f"Credentials: {creds_path}")

# Check credentials file
if creds_path and os.path.exists(creds_path):
    print(f"[OK] Credentials file found")
else:
    print(f"[FAIL] Credentials file not found at: {creds_path}")
    sys.exit(1)

# Force Vertex AI mode
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"

print("\nTesting connection...")

try:
    from google import genai
    
    client = genai.Client(
        vertexai=True,
        project=project,
        location=location,
    )
    
    print("Sending test prompt...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Reply with exactly: OK",
    )
    
    print(f"\n[OK] Response: {response.text.strip()}")
    print("\n" + "=" * 50)
    print("SUCCESS! Vertex AI is working!")
    print("=" * 50)
    
except Exception as e:
    print(f"\n[FAIL] Error: {e}")
    sys.exit(1)
