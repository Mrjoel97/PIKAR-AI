import os
import glob
import json

SKILLS_DIR = r"c:\Users\expert\Documents\PKA\Pikar-Ai\apps\agent-skills"
OUTPUT_FILE = r"c:\Users\expert\Documents\PKA\Pikar-Ai\supabase\migrations\0020_seed_skills.sql"

def parse_frontmatter(content):
    """Simple parser for YAML frontmatter."""
    metadata = {}
    body = content
    if content.startswith("---\n"):
        try:
            _, fm, rest = content.split("---\n", 2)
            body = rest
            for line in fm.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    metadata[key.strip()] = val.strip().strip('"')
        except ValueError:
            pass # Failed to parse
    return metadata, body

def generate_sql():
    sql = [
        "-- Migration: 0020_seed_skills.sql",
        "-- Description: Seed skills from filesystem",
        "BEGIN;",
        "DELETE FROM skills;" # Re-seed logic
    ]
    
    # Find all SKILL.md files recursively
    # glob pattern for recursive search
    pattern = os.path.join(SKILLS_DIR, "**", "SKILL.md")
    files = glob.glob(pattern, recursive=True)
    
    values = []
    
    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        file_dir = os.path.dirname(file_path)
        dir_name = os.path.basename(file_dir)
        
        metadata, body = parse_frontmatter(content)
        
        # Use metadata name if available, else directory name
        name = metadata.get("name", dir_name)
        description = metadata.get("description", f"Skill for {name}")
        category = "general" # Default, could map based on parent dir
        
        # Escape for SQL
        safe_name = name.replace("'", "''")
        safe_desc = description.replace("'", "''")
        safe_content = content.replace("'", "''") # Store full content including frontmatter
        safe_metadata = json.dumps(metadata).replace("'", "''")
        
        val = f"('{safe_name}', '{safe_desc}', '{category}', '{safe_content}', '{safe_metadata}'::jsonb)"
        values.append(val)
        
    if values:
        sql.append("INSERT INTO skills (name, description, category, content, metadata)")
        sql.append("VALUES")
        sql.append(",\n".join(values) + ";")
        
    sql.append("COMMIT;")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(sql))

if __name__ == "__main__":
    generate_sql()
    print(f"Migration file 0020_seed_skills.sql generated with {len(values) if 'values' in locals() else 'unknown'} skills.")
