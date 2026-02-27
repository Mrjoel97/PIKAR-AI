import asyncio
import os
import sys
import json

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.workflows.readiness import build_workflow_readiness_report
from app.services.supabase import get_service_client

async def main():
    try:
        print("Fetching degraded-simulation-prone workflows list...")
        report = build_workflow_readiness_report()
        target_names = report["workflow_names_by_label"].get("degraded-simulation-prone", [])
        
        if not target_names:
            print("No degraded-simulation-prone workflows found!")
            return

        print(f"Found {len(target_names)} degraded workflows to update.")
        
        client = get_service_client()
        
        # We can update them all if we use the IN clause, but let's do one by one to count success/fail locally or just bulk update if supported.
        # Supabase update with check.
        
        print("Updating personas_allowed to ['user', 'agent']...")
        
        # Bulk update by name
        response = client.table("workflow_templates")\
            .update({"personas_allowed": ["user", "agent"]})\
            .in_("name", target_names)\
            .execute()
            
        updated = response.data or []
        print(f"Updated {len(updated)} rows.")
        
        # Verify
        if len(updated) != len(target_names):
            print(f"WARNING: Targeted {len(target_names)} but updated {len(updated)}")
        else:
            print("All targets updated successfully.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
