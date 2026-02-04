
import requests
import json

try:
    print("Fetching /openapi.json...")
    response = requests.get("http://localhost:8000/openapi.json")
    if response.status_code == 200:
        data = response.json()
        print("Paths found in openapi.json:")
        for path in data.get('paths', {}):
            if 'onboarding' in path:
                print(f" - {path}")
    else:
        print(f"Failed to fetch openapi.json: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
