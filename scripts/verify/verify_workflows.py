
import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

try:
    from app.workflows.registry import workflow_registry
    from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent, Agent
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def analyze_agent_structure(agent, depth=0):
    structure = {
        "name": agent.name,
        "type": type(agent).__name__,
        "description": getattr(agent, "description", "No description"),
        "steps": []
    }
    
    if isinstance(agent, (SequentialAgent, ParallelAgent, LoopAgent)):
        # LoopAgent might have sub_agents in a different way or just usually has 'sub_agents'
        # Check implementation of LoopAgent if different, but usually they share base structure or we handle sub_agents
        sub_agents = getattr(agent, "sub_agents", [])
        for sub in sub_agents:
            structure["steps"].append(analyze_agent_structure(sub, depth + 1))
            
    return structure

def main():
    report = workflow_registry.get_status_report()
    print(f"Total Workflows in Registry: {report['total_workflows']}")
    
    detailed_analysis = []
    errors = []

    for name in report["workflow_names"]:
        try:
            # Instantiate
            wf = workflow_registry.get(name)
            if not wf:
                errors.append(f"{name}: Returned None")
                continue
                
            # Analyze structure
            struct = analyze_agent_structure(wf)
            detailed_analysis.append(struct)
            
        except Exception as e:
            errors.append(f"{name}: Failed to instantiate - {str(e)}")

    # Summary
    print(f"\nSuccessfully analyzed: {len(detailed_analysis)}")
    print(f"Errors: {len(errors)}")
    
    if errors:
        print("\n--- Errors ---")
        for err in errors:
            print(err)
            
    # Check for empty steps or bad structure
    print("\n--- Structural Analysis ---")
    warnings = []
    for wf in detailed_analysis:
        if wf["type"] in ["SequentialAgent", "LoopAgent", "ParallelAgent"]:
            if not wf["steps"]:
                 warnings.append(f"{wf['name']} ({wf['type']}) has NO sub-agents/steps.")
    
    if warnings:
        for w in warnings:
            print(w)
    else:
        print("All analyzed workflows have sub-agents.")

    # Dump a few examples
    # print(json.dumps(detailed_analysis[:2], indent=2))

if __name__ == "__main__":
    main()
