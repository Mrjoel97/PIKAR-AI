import asyncio
import os
import sys
import uuid

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.workflows.readiness import build_workflow_readiness_report
from app.workflows.engine import WorkflowEngine

# Canary user ID from allowlist
TEST_USER_ID = "00000000-0000-0000-0000-000000000001"

async def main():
    try:
        print("Fetching integration-dependent workflows list...")
        report = build_workflow_readiness_report()
        # "integration-dependent" label
        target_workflows = report["workflow_names_by_label"].get("integration-dependent", [])
        
        if not target_workflows:
            print("No integration-dependent workflows found!")
            return

        print(f"Found {len(target_workflows)} workflows to verify.")
        
        engine = WorkflowEngine()
        results = {"pass": [], "fail": []}

        for name in target_workflows:
            print(f"Verifying: {name}...", end=" ")
            try:
                # Attempt to start
                result = await engine.start_workflow(
                    user_id=TEST_USER_ID,
                    template_name=name,
                    run_source="user_ui" 
                )
                
                if "error" in result:
                    # If it fails due to readiness, that might be expected if integrations are missing
                    # But for now we assume they haven't been manually blocked yet.
                    print(f"FAIL: {result['error']}")
                    results["fail"].append((name, result['error']))
                else:
                    exec_id = result["execution_id"]
                    status = result.get("status")
                    
                    print(f"STARTED (ID: {exec_id}, Status: {status})", end=" ")
                    
                    # Cleanup: Cancel immediately
                    await engine.cancel_execution(
                        execution_id=exec_id,
                        user_id=TEST_USER_ID,
                        reason="Automated verification cleanup"
                    )
                    print("-> Cancelled")
                    results["pass"].append(name)
                    
            except Exception as e:
                print(f"CRITICAL FAIL: {e}")
                results["fail"].append((name, str(e)))

        print("\n=== Verification Summary ===")
        print(f"Passed: {len(results['pass'])}")
        print(f"Failed: {len(results['fail'])}")
        
        if results["fail"]:
            print("\nFailures:")
            for name, err in results["fail"]:
                print(f"- {name}: {err}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Script Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
