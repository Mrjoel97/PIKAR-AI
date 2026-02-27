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
        print("Fetching human-gated workflows list...")
        report = build_workflow_readiness_report()
        # "human-gated" label comes from classify_workflow in readiness.py
        target_workflows = report["workflow_names_by_label"].get("human-gated", [])
        
        if not target_workflows:
            print("No human-gated workflows found!")
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
                    print(f"FAIL: {result['error']}")
                    results["fail"].append((name, result['error']))
                else:
                    exec_id = result["execution_id"]
                    status = result.get("status")
                    step_desc = result.get("current_step")
                    
                    # We expect it to start. It might be 'running' or 'suspended' or 'pending'.
                    # We just want to ensure it didn't fail immediately.
                    print(f"STARTED (ID: {exec_id}, Status: {status}, Step: {step_desc})", end=" ")
                    
                    # Check for immediate approval requirement (if first step is gated)
                    # In a real deep test we would poll, but here we just check startability.
                    
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
