
import os
import json
import re
from pathlib import Path
from supabase import create_client, Client

# Config
PROJECT_ROOT = Path(r"c:\Users\expert\Documents\PKA\Pikar-Ai")
FS_SKILLS_DIR = PROJECT_ROOT / "antigravity-awesome-skills" / "skills"

# Load .env manually
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    with open(env_path, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key_val = line.strip().split("=", 1)
                if len(key_val) == 2:
                    os.environ[key_val[0]] = key_val[1]

# Initialize Supabase
url = os.environ.get("SUPABASE_URL")
# Prefer service role key, fallback to anon key
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
    exit(1)

supabase: Client = create_client(url, key)

def parse_skill_content(skill_dir):
    # Try SKILL.md, then README.md
    for fname in ["SKILL.md", "README.md"]:
        fpath = skill_dir / fname
        if fpath.exists():
            try:
                # Binary read to avoid encoding issues initially if possible, but we need string for json
                # Using utf-8 errors='replace' to be safe
                content = fpath.read_text(encoding="utf-8", errors="replace")
                
                # Parse description from frontmatter or content
                description = f"Skill for {skill_dir.name}"
                
                # Check for frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = parts[1]
                        for line in frontmatter.splitlines():
                            if line.startswith("description:"):
                                description = line.split(":", 1)[1].strip().strip('"\'')
                                break
                return content, description
            except Exception as e:
                print(f"Error reading {fpath}: {e}")
                
    return None, f"Skill for {skill_dir.name}"

def seed_skills():
    if not FS_SKILLS_DIR.exists():
        print(f"Error: Skills directory not found at {FS_SKILLS_DIR}")
        return

    # List all subdirectories
    skill_dirs = [d for d in FS_SKILLS_DIR.iterdir() if d.is_dir()]
    print(f"Found {len(skill_dirs)} skill directories.")
    
    success_count = 0
    fail_count = 0
    
    # Process in batches of 10 to avoid timeouts/rate limits
    batch_size = 10
    batch_data = []

    for i, skill_dir in enumerate(skill_dirs):
        name = skill_dir.name
        
        # Skip if name starts with . (hidden)
        if name.startswith("."):
            continue

        content, description = parse_skill_content(skill_dir)
        
        if content is None:
            print(f"Skipping {name}: No content file found (SKILL.md or README.md)")
            continue
            
        # Prepare record
        record = {
            "name": name,
            "description": description,
            "category": "general",
            "content": content,
            "metadata": {
                "name": name,
                "description": description
            }
        }
        
        batch_data.append(record)
        
        if len(batch_data) >= batch_size or i == len(skill_dirs) - 1:
            try:
                # Upsert batch
                response = supabase.table("skills").upsert(batch_data, on_conflict="name").execute()
                print(f"Upserted batch ending at {name} (Count: {len(batch_data)})")
                success_count += len(batch_data)
                batch_data = [] # Reset batch
            except Exception as e:
                print(f"Error upserting batch at {name}: {e}")
                # Try one by one if batch fails? 
                # For now just fail the batch
                fail_count += len(batch_data)
                batch_data = []

    print(f"Finished seeding. Success: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    seed_skills()
