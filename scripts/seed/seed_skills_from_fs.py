import os
import re
import glob
import urllib.request
import urllib.parse
import json

# Configuration
PROJECT_ROOT = r"c:\Users\expert\Documents\PKA\Pikar-Ai"
SKILLS_DIR = os.path.join(PROJECT_ROOT, "antigravity-awesome-skills", "skills")
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")
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
        print("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
        # Try to find them in os.environ just in case
        DB_URL = os.environ.get('SUPABASE_URL')
        SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
        if not DB_URL or not SERVICE_KEY:
             raise Exception("Could not find Supabase credentials")

    print(f"Supabase URL: {DB_URL}")
    print("Service Key loaded.")

def parse_skill_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse Frontmatter
        metadata = {}
        description = ""
        category = "general" # default
        
        # Simple frontmatter parser
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter_raw = parts[1]
                body = parts[2]
                
                # Parse YAML-like frontmatter manually to avoid dependencies
                for line in frontmatter_raw.split('\n'):
                    if ':' in line:
                        k, v = line.split(':', 1)
                        k = k.strip()
                        v = v.strip().strip('"\'')
                        metadata[k] = v
                        if k == 'description':
                            description = v
                        if k == 'category':
                            category = v
            else:
                body = content
        else:
            body = content

        return {
            "content": content, # Store full content including frontmatter? Or just body? The SQL used full content.
            "metadata": metadata,
            "description": description,
            "category": category
        }
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return None

def seed_skills():
    load_env()
    
    url = f"{DB_URL}/rest/v1/skills"
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates" # Upsert based on primary key if possible? id is uuid. name is likely unique?
        # If name is not unique constraint, this just inserts.
        # Let's hope name is unique or we duplicate.
        # The SQL uses DELETE FROM skills; first.
        # I should probably delete first? Or assume empty since user said it's zero.
    }
    
    # Check if empty first?
    # User said equal 0.
    
    skills_to_insert = []
    
    print(f"Scanning {SKILLS_DIR}...")
    dirs = [d for d in os.listdir(SKILLS_DIR) if os.path.isdir(os.path.join(SKILLS_DIR, d))]
    
    total_found = 0
    for d in dirs:
        skill_path = os.path.join(SKILLS_DIR, d)
        # Look for SKILL.md or README.md
        md_file = os.path.join(skill_path, "SKILL.md")
        if not os.path.exists(md_file):
            md_file = os.path.join(skill_path, "README.md")
            if not os.path.exists(md_file):
                # print(f"Skipping {d}: No SKILL.md or README.md")
                continue
        
        data = parse_skill_file(md_file)
        if data:
            skill_name = d
            # Use metadata name if present, else dir name
            if 'name' in data['metadata']:
                skill_name = data['metadata']['name']
                
            skills_to_insert.append({
                "name": skill_name,
                "description": data['description'] or f"Skill for {skill_name}",
                "category": data['category'],
                "content": data['content'],
                "metadata": data['metadata']
            })
            total_found += 1

    print(f"Found {total_found} skills.")
    
    # Bath insert
    BATCH_SIZE = 50
    for i in range(0, len(skills_to_insert), BATCH_SIZE):
        batch = skills_to_insert[i:i+BATCH_SIZE]
        print(f"Inserting batch {i} to {i+BATCH_SIZE}...")
        
        try:
            req = urllib.request.Request(url, data=json.dumps(batch).encode('utf-8'), headers=headers, method='POST')
            with urllib.request.urlopen(req) as resp:
                print(f" Batch {i} status: {resp.status}")
        except urllib.error.HTTPError as e:
            print(f"Error inserting batch: {e.code} {e.read().decode('utf-8')}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    seed_skills()
