
import os
import sys

# Set bypass to avoid missing gcp credentials or complex dependencies
os.environ["LOCAL_DEV_BYPASS"] = "1"
os.environ["SUPABASE_URL"] = "https://fake.supabase.co"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "fake-key"
os.environ["LOGS_BUCKET_NAME"] = "fake-bucket"

# Add project root to sys.path
sys.path.append(os.getcwd())

try:
    from fastapi.testclient import TestClient
    from app.fast_api_app import app
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def test_rate_limiting():
    client = TestClient(app)
    
    # Mocking supabase client within the rate limiter if possible would be better,
    # but since we rely on fallback behavior (10/min) when no user found, 
    # we don't strictly need a real supabase connection for the RATE LIMITER part.
    # The endpoint /pages/{page_id} attempts to use supabase, which might fail.
    # However, SlowAPI middleware should kick in BEFORE the endpoint logic if limit exceeded.
    
    print("Sending 15 requests to /pages/123...")
    results = []
    for i in range(15):
        # We expect some failures due to mocking, but we care about 429
        try:
            response = client.get("/pages/123")
            results.append(response.status_code)
            print(f"Request {i+1}: {response.status_code}")
        except Exception as e:
            import traceback
            print(f"Request {i+1} failed with exception: {e}")
            traceback.print_exc()
            results.append(500)

    # Analyze results
    # Default limit is 10/minute.
    # So first 10 should be non-429 (likely 404 or 500 depending on DB mock, or 200 if mocked well)
    # The 11th+ should be 429.
    
    rate_limited_count = results.count(429)
    print(f"Number of 429 responses: {rate_limited_count}")
    
    if rate_limited_count > 0:
        print("SUCCESS: Rate limiting is active.")
        # Check if the first few were NOT 429 (proving it's not blocking everything)
        if results[0] != 429:
             print("SUCCESS: Initial requests allowed.")
        else:
             print("WARNING: Initial requests blocked. Limit might be too low or state persisted.")
    else:
        print("FAILURE: No 429 responses received.")
        sys.exit(1)

if __name__ == "__main__":
    test_rate_limiting()
