import sys
import os
import asyncio
import json
import urllib.request
import urllib.error

def test():
    token = "undefined"
    url = "http://localhost:8000/a2a/app/run_sse"
    req = urllib.request.Request(url, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps({"session_id": "test", "new_message": {"parts": [{"text": "hi"}]}}).encode("utf-8")
    
    try:
        response = urllib.request.urlopen(req, data=data)
        print("Response:", response.status)
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} - {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test()

