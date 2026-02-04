
import sys
import os
# Add current dir to path
sys.path.append(os.getcwd())

try:
    from app.fast_api_app import app
    print("\n--- REGISTERED ROUTES ---")
    for route in app.routes:
        methods = getattr(route, "methods", None)
        print(f"{route.path} {methods}")
    print("-------------------------\n")
except Exception as e:
    print(f"Error loading app: {e}")
