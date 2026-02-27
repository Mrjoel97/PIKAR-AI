

import os
import re
import json
import glob
from pathlib import Path
from supabase import create_client, Client

# Load .env manually
env_path = Path(r"c:\Users\expert\Documents\PKA\Pikar-Ai\.env")
if env_path.exists():
    with open(env_path, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key_val = line.strip().split("=", 1)
                if len(key_val) == 2:
                    os.environ[key_val[0]] = key_val[1]

# Initialize Supabase
url = os.environ.get("SUPABASE_URL")
# Prefer service role key, fallback to anon key (but anon key won't work for RLS writes usually)
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
    # print debug info
    print(f"URL: {url}")
    print(f"Key found: {'Yes' if key else 'No'}")
    exit(1)

supabase: Client = create_client(url, key)


def parse_sql_value(text):
    """
    Parses a single SQL string '...' handling '' escape.
    Returns the string value and the index where it ended.
    """
    if not text.startswith("'"):
        raise ValueError("Expected starting quote")
    
    value = []
    i = 1
    while i < len(text):
        char = text[i]
        if char == "'":
            # Check for escape
            if i + 1 < len(text) and text[i+1] == "'":
                value.append("'")
                i += 2
                continue
            else:
                # End of string
                return "".join(value), i + 1
        else:
            value.append(char)
            i += 1
    raise ValueError("Unterminated string")

def parse_chunk(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find start of VALUES (
    match = re.search(r"VALUES\s*\(", content, re.IGNORECASE)
    if not match:
        print(f"No VALUES found in {filepath}")
        return None

    current_pos = match.end()
    
    # Parse 5 fields
    fields = []
    
    # Skip whitespace
    while content[current_pos].isspace():
        current_pos += 1
        
    # 1. name
    val, consumed = parse_sql_value(content[current_pos:])
    fields.append(val)
    current_pos += consumed
    
    # Expect comma
    match_comma = re.match(r"\s*,\s*", content[current_pos:])
    if not match_comma: raise ValueError(f"Expected comma after name in {filepath}")
    current_pos += match_comma.end()
    
    # 2. description
    val, consumed = parse_sql_value(content[current_pos:])
    fields.append(val)
    current_pos += consumed
    
    # Expect comma
    match_comma = re.match(r"\s*,\s*", content[current_pos:])
    if not match_comma: raise ValueError(f"Expected comma after description in {filepath}")
    current_pos += match_comma.end()
    
    # 3. category
    val, consumed = parse_sql_value(content[current_pos:])
    fields.append(val)
    current_pos += consumed
    
    # Expect comma
    match_comma = re.match(r"\s*,\s*", content[current_pos:])
    if not match_comma: raise ValueError(f"Expected comma after category in {filepath}")
    current_pos += match_comma.end()
    
    # 4. content
    val, consumed = parse_sql_value(content[current_pos:])
    fields.append(val)
    current_pos += consumed
    
    # Expect comma
    match_comma = re.match(r"\s*,\s*", content[current_pos:])
    if not match_comma: raise ValueError(f"Expected comma after content in {filepath}")
    current_pos += match_comma.end()
    
    # 5. metadata
    # Metadata might have ::jsonb suffix
    val, consumed = parse_sql_value(content[current_pos:])
    fields.append(val)
    current_pos += consumed
    
    return {
        "name": fields[0],
        "description": fields[1],
        "category": fields[2],
        "content": fields[3],
        "metadata": json.loads(fields[4]) # json parsing
    }

def process_chunks(start=21, end=99):
    chunks_dir = r"c:\Users\expert\Documents\PKA\Pikar-Ai\.tmp\sql_chunks"
    
    success_count = 0
    fail_count = 0
    
    for i in range(start, end + 1):
        filename = f"chunk_{i:03d}.sql"
        filepath = os.path.join(chunks_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"Skipping {filename}: Not found")
            continue
            
        try:
            print(f"Processing {filename}...")
            data = parse_chunk(filepath)
            if data:
                # Insert into Supabase
                # Using upsert to handle potential conflicts if some were partial
                response = supabase.table("skills").upsert(data, on_conflict="name").execute()
                print(f"Successfully inserted {data['name']}")
                success_count += 1
            else:
                fail_count += 1

        except Exception as e:
            print(f"Error processing {filename}: {e}")
            import traceback
            traceback.print_exc()
            fail_count += 1


    print(f"Finished. Success: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    process_chunks()
