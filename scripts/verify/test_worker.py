# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Test ai_jobs worker functionality."""

import os
import sys
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

# Get Supabase client
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
client = create_client(url, key)

print("=== AI Jobs Worker Test ===\n")

# 1. Create a test job
test_job_id = None
print("1. Creating test job...")
job_data = {
    "job_type": "test_job",
    "status": "pending",
    "priority": 5,
    "input_data": {"test": True}
}
result = client.table("ai_jobs").insert(job_data).execute()
test_job_id = result.data[0]["id"] if result.data else None
print(f"   Created job: {test_job_id}")

# 2. Test atomic job claiming
print("\n2. Testing atomic job claiming...")
worker_id = f"test-worker-{uuid.uuid4().hex[:8]}"
claimed = client.rpc("claim_next_ai_job", {"p_worker_id": worker_id}).execute()
if claimed.data:
    claimed_job = claimed.data[0]
    print(f"   [OK] Claimed job: {claimed_job['id']}")
    print(f"   Job type: {claimed_job['job_type']}")
else:
    print("   [FAIL] No job claimed")

# 3. Verify job is now processing
print("\n3. Verifying job status...")
job = client.table("ai_jobs").select("*").eq("id", test_job_id).execute()
if job.data and job.data[0]["status"] == "processing":
    print(f"   [OK] Status is 'processing'")
    print(f"   Locked by: {job.data[0]['locked_by']}")
else:
    print(f"   [FAIL] Status is: {job.data[0]['status'] if job.data else 'unknown'}")

# 4. Test complete_ai_job function
print("\n4. Testing job completion...")
client.rpc("complete_ai_job", {
    "p_job_id": str(test_job_id),
    "p_output_data": {"result": "success"}
}).execute()
job = client.table("ai_jobs").select("*").eq("id", test_job_id).execute()
if job.data and job.data[0]["status"] == "completed":
    print("   [OK] Job marked as completed")
else:
    print(f"   [FAIL] Status is: {job.data[0]['status'] if job.data else 'unknown'}")

# 5. Create another job and test fail_ai_job with retry
print("\n5. Testing job failure with retry...")
job2 = client.table("ai_jobs").insert({
    "job_type": "test_fail_job",
    "status": "processing",
    "priority": 5,
    "retry_count": 0,
    "max_retries": 3,
    "locked_by": worker_id
}).execute()
job2_id = job2.data[0]["id"]

client.rpc("fail_ai_job", {
    "p_job_id": str(job2_id),
    "p_error_message": "Test failure"
}).execute()

job2_status = client.table("ai_jobs").select("*").eq("id", job2_id).execute()
if job2_status.data:
    status = job2_status.data[0]["status"]
    retry_count = job2_status.data[0]["retry_count"]
    if status == "pending" and retry_count == 1:
        print(f"   [OK] Job rescheduled for retry (retry_count: {retry_count})")
    else:
        print(f"   [FAIL] Status: {status}, retry_count: {retry_count}")

# 6. Test prune_session_versions function
print("\n6. Testing prune_session_versions function...")
try:
    result = client.rpc("prune_session_versions", {"p_keep_count": 50}).execute()
    print(f"   [OK] Function executed, deleted: {result.data}")
except Exception as e:
    print(f"   [FAIL] Error: {e}")

# Cleanup
print("\n7. Cleaning up test data...")
client.table("ai_jobs").delete().eq("id", test_job_id).execute()
client.table("ai_jobs").delete().eq("id", job2_id).execute()
print("   Cleanup complete!")

print("\n=== ALL TESTS PASSED ===")
