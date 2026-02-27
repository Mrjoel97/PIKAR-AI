
import os
import sys
from app.services.supabase import get_service_client

def check_buckets():
    try:
        supabase = get_service_client()
        buckets = supabase.storage.list_buckets()
        bucket_names = [b.name for b in buckets]
        
        required_buckets = ["generated-assets", "generated-videos"]
        
        for bucket in required_buckets:
            if bucket in bucket_names:
                print(f"Bucket '{bucket}' exists.")
            else:
                print(f"Bucket '{bucket}' missing. Attempting to create...")
                try:
                    supabase.storage.create_bucket(bucket, options={"public": True})
                    print(f"Bucket '{bucket}' created successfully.")
                except Exception as e:
                    print(f"Failed to create bucket '{bucket}': {e}")
                    
    except Exception as e:
        print(f"Error checking buckets: {e}")

if __name__ == "__main__":
    check_buckets()
