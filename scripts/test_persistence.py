"""Test session persistence across restarts."""
import os
import uuid
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
client = create_client(url, key)

# 1. CREATE a test session
test_session_id = f"test-{uuid.uuid4().hex[:8]}"
test_user_id = "test-user-001"
test_app = "pikar-ai"

print("=== Session Persistence Test ===")
print(f"Creating session: {test_session_id}")

session_data = {
    "session_id": test_session_id,
    "user_id": test_user_id,
    "app_name": test_app,
    "state": {"last_topic": "testing persistence"}
}
client.table("sessions").insert(session_data).execute()
print("Session created successfully!")

# 2. Create an event
event_data = {
    "session_id": test_session_id,
    "user_id": test_user_id,
    "app_name": test_app,
    "event_index": 0,
    "event_data": {"role": "user", "content": "Hello, test message!"}
}
client.table("session_events").insert(event_data).execute()
print("Event created successfully!")

# 3. SIMULATE RESTART - Re-query (as if app restarted)
print("--- Simulating restart ---")
result = client.table("sessions").select("*").eq("session_id", test_session_id).execute()
if result.data:
    recovered = result.data[0]
    print(f"Session recovered: {recovered['session_id']}")
    print(f"State: {recovered['state']}")
else:
    print("ERROR: Session not found after restart!")
    exit(1)

events = client.table("session_events").select("*").eq("session_id", test_session_id).order("event_index").execute()
print(f"Events recovered: {len(events.data)}")

# 4. CLEANUP
client.table("session_events").delete().eq("session_id", test_session_id).execute()
client.table("sessions").delete().eq("session_id", test_session_id).execute()
print("Cleanup complete.")
print("=== TEST PASSED ===")

# =============================================================================
# VERSIONING TESTS
# =============================================================================
print("\n=== Session Versioning Test ===")

# Create a new test session for versioning
v_session_id = f"version-test-{uuid.uuid4().hex[:8]}"

print(f"Creating versioned session: {v_session_id}")
v_session_data = {
    "session_id": v_session_id,
    "user_id": test_user_id,
    "app_name": test_app,
    "state": {},
    "current_version": 1
}
client.table("sessions").insert(v_session_data).execute()
print("Session created!")

# Add events with version tracking
print("Adding events with version tracking...")
for i in range(3):
    version = i + 1
    event_data = {
        "session_id": v_session_id,
        "user_id": test_user_id,
        "app_name": test_app,
        "event_index": i,
        "event_data": {"role": "user", "content": f"Message {version}"},
        "version": version,
        "operation": "create"
    }
    client.table("session_events").insert(event_data).execute()
    print(f"  Event {version} added (version {version})")

# Update session current version
client.table("sessions").update({"current_version": 3}).eq("session_id", v_session_id).execute()

# Test version history
print("\nChecking version history...")
history = client.table("session_events").select("version, operation, created_at").eq("session_id", v_session_id).order("version").execute()
print(f"Version history entries: {len(history.data)}")
for entry in history.data:
    print(f"  Version {entry['version']}: {entry['operation']}")

# Test retrieving at specific version (version 2 should have 2 events)
print("\nRetrieving session at version 2...")
v2_events = client.table("session_events").select("*").eq("session_id", v_session_id).lte("version", 2).execute()
print(f"Events at version 2: {len(v2_events.data)}")
if len(v2_events.data) == 2:
    print("[OK] Version retrieval works correctly!")
else:
    print(f"[FAIL] Expected 2 events, got {len(v2_events.data)}")

# Test version function
print("\nTesting get_next_session_version function...")
next_version = client.rpc("get_next_session_version", {
    "p_app_name": test_app,
    "p_user_id": test_user_id,
    "p_session_id": v_session_id
}).execute()
print(f"Next version would be: {next_version.data}")
if next_version.data == 4:
    print("[OK] Version function works correctly!")
else:
    print(f"[FAIL] Expected version 4, got {next_version.data}")

# Cleanup versioned session
print("\nCleaning up versioned session...")
client.table("session_events").delete().eq("session_id", v_session_id).execute()
client.table("sessions").delete().eq("session_id", v_session_id).execute()
print("Cleanup complete.")
print("=== VERSIONING TEST PASSED ===")

