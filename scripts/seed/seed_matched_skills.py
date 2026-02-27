import sys
import os
import json
import urllib.request
import urllib.parse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

# Load Env
ENV_FILE = PROJECT_ROOT / ".env"
DB_URL = None
SERVICE_KEY = None

def load_env():
    global DB_URL, SERVICE_KEY
    print(f"Loading env from {ENV_FILE}...")
    try:
        with open(ENV_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    if key.strip() == 'SUPABASE_URL':
                        DB_URL = value.strip()
                    elif key.strip() == 'SUPABASE_SERVICE_ROLE_KEY':
                        SERVICE_KEY = value.strip()
    except Exception as e:
        print(f"Error loading .env: {e}")

    if not DB_URL or not SERVICE_KEY:
        # Try os.environ
        DB_URL = os.environ.get('SUPABASE_URL')
        SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
        if not DB_URL or not SERVICE_KEY:
            # Hard fallback if .env not read correctly (sometimes needed in this env)
            pass 

    print(f"Supabase URL: {DB_URL}")

def seed_matched_skills():
    load_env()
    if not DB_URL or not SERVICE_KEY:
        print("Failed to find credentials.")
        return

    import logging
    logging.basicConfig(level=logging.INFO)

    # Import Registry and Libraries
    print("Importing skills library...")
    try:
        from app.skills.registry import skills_registry, AgentID
        import app.skills.library
        
        from app.skills.loader import load_custom_skills
        print("Forcing custom skills load...")
        custom_loaded = load_custom_skills()
        print(f"Custom skills loaded: {len(custom_loaded)}")
        
        # external_skills is imported by library, so we are good.
    except Exception as e:
        print(f"Import/Load Assessment Error: {e}")
        import traceback
        traceback.print_exc()
        return

    all_skills = skills_registry.list_all()
    print(f"Total skills in registry: {len(all_skills)}")

    matched_skills = []
    mapped_skill_names = set()

    for skill in all_skills:
        # Check if mapped to agents
        if skill.agent_ids and len(skill.agent_ids) > 0:
            agent_ids_str = [a.value for a in skill.agent_ids]
            
            # Prepare metadata
            metadata = {
                "agent_ids": agent_ids_str,
                "implementation_defined": bool(skill.implementation)
            }
            
            matched_skills.append({
                "name": skill.name,
                "description": skill.description,
                "category": skill.category,
                "content": skill.knowledge or "Function-based skill",
                "metadata": metadata
            })
            mapped_skill_names.add(skill.name)

    print(f"Found {len(matched_skills)} matched skills.")

    # Insert into Supabase
    url = f"{DB_URL}/rest/v1/skills"
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    BATCH_SIZE = 50
    for i in range(0, len(matched_skills), BATCH_SIZE):
        batch = matched_skills[i:i+BATCH_SIZE]
        print(f"Inserting batch {i} to {i+BATCH_SIZE}...")
        try:
            req = urllib.request.Request(url, data=json.dumps(batch).encode('utf-8'), headers=headers, method='POST')
            with urllib.request.urlopen(req) as resp:
                print(f" Batch {i} status: {resp.status}")
        except Exception as e:
            print(f"Error inserting batch: {e}")

    # Identify Unmapped Skills from Filesystem
    FS_SKILLS_DIR = PROJECT_ROOT / "antigravity-awesome-skills" / "skills"
    unmapped_skills = []
    
    if FS_SKILLS_DIR.exists():
        fs_skill_dirs = [d.name for d in FS_SKILLS_DIR.iterdir() if d.is_dir()]
        for skill_name in fs_skill_dirs:
            # We assume directory name matches skill name roughly
            # Normalize names (underscores vs hyphens)
            norm_name = skill_name.replace("-", "_")
            if norm_name not in mapped_skill_names and skill_name not in mapped_skill_names:
                unmapped_skills.append(skill_name)
    
    print(f"Found {len(unmapped_skills)} unmapped skills in filesystem.")
    
    # Save unmapped list for plan
    with open("execution/unmapped_skills.json", "w") as f:
        json.dump(unmapped_skills, f, indent=2)

if __name__ == "__main__":
    seed_matched_skills()
