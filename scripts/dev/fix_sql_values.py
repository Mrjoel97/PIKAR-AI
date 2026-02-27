import re

def fix_sql_escaping(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the JSON parts and double-escape quotes
    # Pattern: match strings ending with '::jsonb
    # We use a pattern that captures the content between quotes
    # Heuristic: search for '::jsonb, then search backwards for the start '
    
    # Actually, simpler: finding '::jsonb is easy.
    # The JSON string start is hard to identify via regex cleanly due to nested content.
    # BUT, we know the Structure:
    # It's always at the end of the VALUES tuple?
    # No, order matters.
    # Lines ending with '::jsonb),
    
    # We can iterate line by line since the JSON blob seems to be on one single line in the view?
    # No, check_json.py processed the whole file.
    
    # Let's use the replacement logic inside the specific known structure
    # Use re.sub with a callback
    
    def replacement(match):
        full_str = match.group(0) # '...':jsonb
        json_content_quoted = match.group(1) # '{...}'
        
        # Replace \" with \\"
        new_content = json_content_quoted.replace('\\"', '\\\\"')
        
        # We assume the content assumes single quotes '...' around it
        return f"'{new_content}'::jsonb"

    # Pattern: ' ( { ... } ) ' ::jsonb
    # Note: DOTALL is important
    # non-greedy match might fail if } is inside.
    # BUT we validated that } is at the end.
    
    new_content = re.sub(r"'(\{.*?\})'::jsonb", replacement, content, flags=re.DOTALL)
    
    if new_content == content:
        print("No changes made.")
    else:
        print("Fixed escaping.")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

if __name__ == "__main__":
    fix_sql_escaping(r'c:\Users\expert\Documents\PKA\Pikar-Ai\supabase\migrations\0020_seed_skills.sql')
