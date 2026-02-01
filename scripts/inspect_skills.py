
import sys
import os
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Import registry and external skills to ensure registration
try:
    from app.skills.registry import skills_registry, AgentID
    from app.skills.external_skills import EXTERNAL_SKILLS
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def main():
    print("--- Pikar AI Skills Registry Inspection ---")
    all_skills = skills_registry.list_all()
    print(f"Total Skills Registered: {len(all_skills)}")
    
    unmatched_skills = []
    matched_structure = {}

    for skill in all_skills:
        agents = skill.agent_ids
        if not agents:
            unmatched_skills.append(skill)
            agent_str = "ALL (Unmatched)"
        else:
            agent_str = ", ".join([a.value for a in agents])
            for agent in agents:
                if agent.value not in matched_structure:
                    matched_structure[agent.value] = []
                matched_structure[agent.value].append(skill.name)
        
        print(f"Skill: {skill.name:<30} | Category: {skill.category:<15} | Agents: {agent_str}")

    print("\n--- Unmatched Skills (Available to All) ---")
    if unmatched_skills:
        for s in unmatched_skills:
            print(f"- {s.name} ({s.category})")
    else:
        print("None. All skills are assigned to specific agents.")

    print("\n--- Agent Skill Counts ---")
    for agent_id, skills in matched_structure.items():
        print(f"{agent_id}: {len(skills)} skills")

if __name__ == "__main__":
    main()
