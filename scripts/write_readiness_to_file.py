import asyncio
import os
import sys
import json

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.workflows.readiness import build_workflow_readiness_report

async def main():
    try:
        print("Generating report...")
        report = build_workflow_readiness_report()
        
        with open("scripts/readiness_report.txt", "w") as f:
            f.write("Workflow Names by Category:\n")
            for label, names in report["workflow_names_by_label"].items():
                f.write(f"\n=== {label} ({len(names)}) ===\n")
                for name in sorted(names):
                    f.write(f"- {name}\n")
            
            f.write("\n\nWorkflow Labels Summary:\n")
            f.write(json.dumps(report["workflow_labels"], indent=2))
            
        print("Report written to scripts/readiness_report.txt")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
