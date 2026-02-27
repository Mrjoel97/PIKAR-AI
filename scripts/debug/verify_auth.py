
import os
import sys
from dotenv import load_dotenv
import google.auth

# Load .env (simulating app behavior)
load_dotenv()

print(f"GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")

try:
    credentials, project = google.auth.default()
    print(f"Successfully obtained credentials for project: {project}")
except Exception as e:
    print(f"Failed to get credentials: {e}")
    sys.exit(1)
