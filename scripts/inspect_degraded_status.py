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

        print(f"Found {len(target_names)} degraded workflows. Querying details...")
        
        client = get_service_client()
        response = client.table("workflow_templates")\
            .select("name, lifecycle_status, personas_allowed")\
            .in_("name", target_names)\
            .execute()
            
        rows = response.data or []
        
        print(f"{'Name':<40} | {'Status':<15} | {'Personas'}")
        print("-" * 80)
        
        needs_update = []
        
        for row in rows:
            name = row["name"]
            status = row.get("lifecycle_status") or "unknown"
            personas = row.get("personas_allowed") or []
            
            print(f"{name:<40} | {status:<15} | {personas}")
            
            # Criteria: Must be published and have user+agent (assuming 'agent' is the system persona? 
            # or typically personas_allowed might correspond to roles like 'admin', 'user').
            # The user said "executed by both users and agents".
            # Usually strict personas might be ['user', 'admin']. 
            # If personas_allowed is empty/null, it might imply "all" or "none" depending on logic.
            # engine.py: list_templates matches if query.contains("personas_allowed", [persona])
            # So if we want them available to 'user' and 'agent', we probably need those strings in the list.
            
            if status != "published":
                needs_update.append(name)
                
        print("-" * 80)
        print(f"Total needing 'publish' update: {len(needs_update)}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
