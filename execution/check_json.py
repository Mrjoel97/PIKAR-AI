import json
import re

def check_json_in_sql(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find matches with DOTALL
    matches = re.finditer(r"'(\{.*?\})'::jsonb", content, re.DOTALL)
    
    count = 0
    errors = 0
    for m in matches:
        count += 1
        json_str = m.group(1)
        try:
            json.loads(json_str)
        except json.JSONDecodeError as e:
            errors += 1
            print(f"Invalid JSON at offset {m.start()}: {e}")
            print(f"Snippet: {json_str[:200]}...")
            
            # Simple fix attempt (specifically for the tracking plan issue)
            if 'tracking plan." For' in json_str:
                print("Found 'tracking plan' issue.")

    print(f"Processed {count} JSON blobs. Found {errors} errors.")

if __name__ == "__main__":
    check_json_in_sql(r'c:\Users\expert\Documents\PKA\Pikar-Ai\supabase\migrations\0020_seed_skills.sql')
