
import os
import sys
import json
from supabase import create_client, Client

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load env vars manually if not loaded (or rely on os.environ if set by environment)
# For this execution environment, we assume .env needs loading or we parse it
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    try:
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k not in os.environ:
                        os.environ[k] = v
    except Exception as e:
        print(f"Warning: Could not load .env: {e}")

load_env()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found.")
    sys.exit(1)

supabase: Client = create_client(url, key)

DEPARTMENTS_TO_SEED = [
    {
        "name": "Marketing Command",
        "type": "MARKETING",
        "status": "PAUSED",
        "config": {"check_interval_mins": 60, "focus": "campaign_optimization"}
    },
    {
        "name": "Content Studio",
        "type": "CONTENT",
        "status": "PAUSED",
        "config": {"check_interval_mins": 120, "focus": "trend_monitoring"}
    },
    {
        "name": "Strategy Office",
        "type": "STRATEGIC",
        "status": "PAUSED",
        "config": {"check_interval_mins": 240, "focus": "okr_tracking"}
    },
    {
        "name": "Data Intelligence",
        "type": "DATA",
        "status": "PAUSED",
        "config": {"check_interval_mins": 60, "focus": "anomaly_detection"}
    },
    {
        "name": "Finance & Treasury",
        "type": "FINANCIAL",
        "status": "PAUSED",
        "config": {"check_interval_mins": 360, "focus": "cash_flow"}
    },
    {
        "name": "Customer Experience",
        "type": "SUPPORT",
        "status": "PAUSED",
        "config": {"check_interval_mins": 30, "focus": "ticket_triage"}
    },
    {
        "name": "People & Talent",
        "type": "HR",
        "status": "PAUSED",
        "config": {"check_interval_mins": 1440, "focus": "employee_sentiment"}
    },
    {
        "name": "Risk & Compliance",
        "type": "COMPLIANCE",
        "status": "PAUSED",
        "config": {"check_interval_mins": 1440, "focus": "regulatory_check"}
    },
    {
        "name": "Operations Control",
        "type": "OPERATIONS",
        "status": "PAUSED",
        "config": {"check_interval_mins": 120, "focus": "efficiency_metrics"}
    }
]

def seed():
    print("Starting Department Seeding...")
    
    for dept in DEPARTMENTS_TO_SEED:
        # Check if exists
        res = supabase.table("departments").select("id").eq("type", dept["type"]).execute()
        
        if res.data and len(res.data) > 0:
            print(f"Skipping {dept['type']} (already exists).")
        else:
            print(f"Inserting {dept['name']} ({dept['type']})...")
            try:
                supabase.table("departments").insert(dept).execute()
                print(" - Success")
            except Exception as e:
                print(f" - Failed: {e}")

    print("Seeding Complete.")

if __name__ == "__main__":
    seed()
