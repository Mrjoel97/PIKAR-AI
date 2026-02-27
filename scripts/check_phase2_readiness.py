import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.workflows.readiness import build_workflow_readiness_report

def main():
    try:
        report = build_workflow_readiness_report()
        
        autonomous_workflows = report["workflow_names_by_label"].get("fully autonomous", [])
        print(f"Found {len(autonomous_workflows)} Fully Autonomous Workflows:")
        for name in autonomous_workflows:
            print(f"- {name}")
            
        print("\nReadiness Summary:")
        print(json.dumps(report["workflow_readiness"], indent=2))
        
        print("\nWorkflow Names by Category:")
        for label, names in report["workflow_names_by_label"].items():
            print(f"\n=== {label} ({len(names)}) ===")
            for name in sorted(names):
                print(f"- {name}")
        
        print("\nWorkflow Labels Summary:")
        print(json.dumps(report["workflow_labels"], indent=2))
        

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    print("Starting readiness check...", file=sys.stderr)
    main()

