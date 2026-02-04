
import requests
import sys

try:
    print("Testing /onboarding/agent-setup...")
    # Expecting 401 because we are not authenticated, BUT NOT 404.
    response = requests.post("http://localhost:8000/onboarding/agent-setup", json={})
    print(f"Status Code: {response.status_code}")
    if response.status_code == 404:
        print("FAILURE: Endpoint not found (404)")
    elif response.status_code in [200, 401, 422]:
        print("SUCCESS: Endpoint exists")
    else:
        print(f"UNKNOWN: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
