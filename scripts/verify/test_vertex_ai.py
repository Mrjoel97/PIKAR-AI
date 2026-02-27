#!/usr/bin/env python3
"""Test script to verify Vertex AI setup is working correctly."""

import os
import sys

# Load environment from app/.env
from dotenv import load_dotenv
load_dotenv('app/.env')

def test_vertex_ai():
    """Test Vertex AI connection and model access."""
    
    print("=" * 60)
    print("Vertex AI Setup Verification")
    print("=" * 60)
    
    # Check environment variables
    print("\n1. Checking environment variables...")
    
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    api_key = os.environ.get("GOOGLE_API_KEY")
    
    print(f"   GOOGLE_CLOUD_PROJECT: {project or 'NOT SET'}")
    print(f"   GOOGLE_CLOUD_LOCATION: {location}")
    print(f"   GOOGLE_APPLICATION_CREDENTIALS: {creds_path or 'NOT SET'}")
    print(f"   GOOGLE_API_KEY: {'SET (will be ignored)' if api_key else 'NOT SET'}")
    
    # Check if credentials file exists
    if creds_path:
        if os.path.exists(creds_path):
            print(f"\n   [OK] Credentials file exists: {creds_path}")
        else:
            print(f"\n   [FAIL] Credentials file NOT FOUND: {creds_path}")
            print("     Please ensure the service account JSON file is in the correct location.")
            return False
    else:
        print("\n   [FAIL] GOOGLE_APPLICATION_CREDENTIALS not set")
        return False
    
    # Set Vertex AI mode
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
    
    # Test import and connection
    print("\n2. Testing Vertex AI connection...")
    
    try:
        from google.adk.models import Gemini
        from google.genai import types
        print("   [OK] Imports successful")
    except ImportError as e:
        print(f"   [FAIL] Import error: {e}")
        return False
    
    # Create model instance
    print("\n3. Creating Gemini model instance...")
    try:
        model = Gemini(
            model="gemini-2.5-flash",
            retry_options=types.HttpRetryOptions(
                attempts=3,
                initial_delay_seconds=1.0,
            ),
        )
        print("   [OK] Model instance created")
    except Exception as e:
        print(f"   [FAIL] Failed to create model: {e}")
        return False
    
    # Test a simple generation
    print("\n4. Testing model generation (simple prompt)...")
    try:
        from google import genai
        
        # Initialize client with Vertex AI
        client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Say 'Vertex AI is working!' in exactly 5 words.",
        )
        
        result = response.text.strip()
        print(f"   [OK] Response received: {result}")
        
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            print(f"   [FAIL] Rate limited (still using free tier?): {e}")
            return False
        elif "403" in error_msg or "PERMISSION_DENIED" in error_msg:
            print(f"   [FAIL] Permission denied. Check service account roles: {e}")
            return False
        elif "API_NOT_ENABLED" in error_msg or "has not been used" in error_msg:
            print(f"   [FAIL] Vertex AI API not enabled. Enable it in GCP Console: {e}")
            return False
        else:
            print(f"   [FAIL] Error: {e}")
            return False
    
    print("\n" + "=" * 60)
    print("SUCCESS! Vertex AI is configured correctly.")
    print("  You now have ~1,500 requests/minute rate limit!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_vertex_ai()
    sys.exit(0 if success else 1)
