import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

async def verify_runner():
    print("Verifying DepartmentRunner...")
    
    # Mock dependencies
    with patch("app.services.supabase.get_service_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock departments data
        departments_data = [
            {"id": "1", "name": "Sales", "type": "SALES", "status": "RUNNING", "state": {}},
            {"id": "2", "name": "Marketing", "type": "MARKETING", "status": "RUNNING", "state": {}},
            {"id": "3", "name": "Content", "type": "CONTENT", "status": "RUNNING", "state": {}},
            {"id": "4", "name": "Strategic", "type": "STRATEGIC", "status": "RUNNING", "state": {}},
            {"id": "5", "name": "Data", "type": "DATA", "status": "RUNNING", "state": {}},
            {"id": "6", "name": "Financial", "type": "FINANCIAL", "status": "RUNNING", "state": {}},
            {"id": "7", "name": "Support", "type": "SUPPORT", "status": "RUNNING", "state": {}},
            {"id": "8", "name": "HR", "type": "HR", "status": "RUNNING", "state": {}},
            {"id": "9", "name": "Compliance", "type": "COMPLIANCE", "status": "RUNNING", "state": {}},
            {"id": "10", "name": "Operations", "type": "OPERATIONS", "status": "RUNNING", "state": {}},
        ]
        
        # Setup mock return for select().eq().execute()
        mock_query = MagicMock()
        mock_query.execute.return_value.data = departments_data
        
        mock_client.table.return_value.select.return_value.eq.return_value = mock_query

        # Import runner
        from app.services.department_runner import DepartmentRunner
        
        runner = DepartmentRunner()
        
        # Run tick
        results = await runner.tick()
        
        print(f"Results count: {len(results)}")
        
        # Verify results
        expected_types = [d['type'] for d in departments_data]
        found_types = 0
        
        for res in results:
            print(f"Result: {res}")
            activity = res['activity']
            
            # Check if activity matches expected pattern
            if "Active" in activity or "active" in activity: # Case sensitive? The code uses "active".
                 found_types += 1
                 
        if found_types == 10:
            print("SUCCESS: All 10 departments executed successfully.")
        else:
            print(f"FAILURE: Only {found_types}/10 departments executed.")

if __name__ == "__main__":
    asyncio.run(verify_runner())
