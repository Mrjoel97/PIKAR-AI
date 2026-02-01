
import ast
import os
import glob
import json

WORKFLOW_DIR = "app/workflows"

def analyze_file(filepath):
    with open(filepath, 'r') as f:
        try:
            tree = ast.parse(f.read())
        except Exception as e:
            return {"file": filepath, "error": str(e)}

    workflows = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name.startswith("create_") and "pipeline" in node.name.lower():
                # Found a workflow factory
                wf = {
                    "name": node.name,
                    "file": os.path.basename(filepath),
                    "return_type": "Unknown",
                    "sub_agents": False,
                    "has_description": False
                }
                
                # Check return type annotation
                if node.returns:
                    if hasattr(node.returns, 'id'):
                        wf['return_type'] = node.returns.id
                    elif hasattr(node.returns, 'attr'): # e.g. agents.SequentialAgent
                         wf['return_type'] = node.returns.attr

                # Analyze body for SequentialAgent/LoopAgent instantiation
                for body_node in ast.walk(node):
                    if isinstance(body_body_node := body_node, ast.Call):
                        if hasattr(body_node.func, 'id') and body_node.func.id in ['SequentialAgent', 'LoopAgent', 'ParallelAgent']:
                            wf['type'] = body_node.func.id
                            # Check keywords for sub_agents
                            for kw in body_node.keywords:
                                if kw.arg == 'sub_agents':
                                    wf['sub_agents'] = True
                                if kw.arg == 'description':
                                    wf['has_description'] = True
                
                workflows.append(wf)
    return workflows

def main():
    files = glob.glob(os.path.join(WORKFLOW_DIR, "*.py"))
    all_workflows = []
    
    print(f"Scanning {len(files)} files in {WORKFLOW_DIR}...")
    
    for f in files:
        if os.path.basename(f) in ["__init__.py", "registry.py", "engine.py", "generator.py", "dynamic.py"]:
            continue
            
        wfs = analyze_file(f)
        if isinstance(wfs, dict) and "error" in wfs:
            print(f"Error parsing {f}: {wfs['error']}")
        else:
            all_workflows.extend(wfs)
            
    # Report
    print(f"\nFound {len(all_workflows)} workflow definitions.")
    
    # Check structure
    print("\n--- Structural Analysis ---")
    
    well_structured = 0
    issues = []
    
    for wf in all_workflows:
        ok = True
        if not wf.get('sub_agents'):
             issues.append(f"{wf['name']} ({wf['file']}) missing 'sub_agents'.")
             ok = False
        if not wf.get('has_description'):
             issues.append(f"{wf['name']} ({wf['file']}) missing 'description'.")
             ok = False
             
        if ok:
            well_structured += 1
            
    if issues:
        print(f"Issues found in {len(issues)} workflows:")
        for i in issues:
            print(f" - {i}")
    else:
        print("All workflows appear to be well-structured (contain sub-agents and descriptions).")
        
    print(f"\nSummary: {well_structured}/{len(all_workflows)} are well-structured.")

if __name__ == "__main__":
    main()
