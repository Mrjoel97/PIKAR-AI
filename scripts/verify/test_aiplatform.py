import os
import sys
from dotenv import load_dotenv

# Load env vars from app/.env
load_dotenv('app/.env')

print("Importing google.cloud.aiplatform...")
try:
    import google.cloud.aiplatform
    print("Imported google.cloud.aiplatform")
except Exception as e:
    print(f"Error importing google.cloud.aiplatform: {e}")

print("Done.")
