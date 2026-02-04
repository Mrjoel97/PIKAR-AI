
import os
from pathlib import Path

AGENTS_DIR = Path(r"c:\Users\expert\Documents\PKA\Pikar-Ai\app\agents")

TARGET_FILES = [
    "compliance/agent.py",
    "content/agent.py",
    "customer_support/agent.py",
    "data/agent.py",
    "financial/agent.py",
    "hr/agent.py",
    "marketing/agent.py",
    "operations/agent.py",
    "reporting/agent.py",
    "sales/agent.py",
    "strategic/agent.py",
]

TOOL_NAME = "list_available_skills"

def enable_skill_discovery():
    count = 0
    for rel_path in TARGET_FILES:
        path = AGENTS_DIR / rel_path
        if not path.exists():
            print(f"Skipping {rel_path} (Not found)")
            continue
            
        content = path.read_text(encoding="utf-8")
        
        if TOOL_NAME in content:
            print(f"Skipping {rel_path} (Already enabled)")
            continue
            
        # Strategy: Find '    use_skill,' and append '    list_available_skills,'
        # This works for both the import block (if use_skill is imported) and the tool list.
        
        if "    use_skill," not in content:
            print(f"Warning: '    use_skill,' not found in {rel_path}. Manual check required. maybe formatting differs.")
            continue
            
        new_content = content.replace(
            "    use_skill,",
            f"    use_skill,\n    {TOOL_NAME},"
        )
        
        path.write_text(new_content, encoding="utf-8")
        print(f"Updated {rel_path}")
        count += 1
        
    print(f"Update complete. Modified {count} files.")

if __name__ == "__main__":
    enable_skill_discovery()
