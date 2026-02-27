import os
import re

def fix_chunks():
    chunks_dir = r'c:\Users\expert\Documents\PKA\Pikar-Ai\.tmp\sql_chunks'
    
    files = sorted([f for f in os.listdir(chunks_dir) if f.endswith('.sql')])
    
    print(f"Found {len(files)} chunks.")
    
    for filename in files:
        filepath = os.path.join(chunks_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find the JSON part for metadata
        # It usually looks like ', '{"name": ...}'::jsonb);
        # We want to capture the content inside '...'::jsonb
        
        # Regex to find the JSON string literal
        pattern = r"(', ')(\{.*?\})('::jsonb\);)"
        
        def replace_newlines(match):
            prefix = match.group(1)
            json_str = match.group(2)
            suffix = match.group(3)
            
            # Replace literal newlines with escaped newlines
            # Also handle \r\n
            fixed_json = json_str.replace('\r\n', '\\n').replace('\n', '\\n').replace('\r', '\\n')
            
            # Also fix potential unescaped double quotes if any (though fix_sql_values.py might have handled it)
            # But let's be careful not to break valid quotes.
            # The issue here is specifically newlines.
            
            return f"{prefix}{fixed_json}{suffix}"

        # Using DOTALL to match newlines if they exist
        new_content = re.sub(pattern, replace_newlines, content, flags=re.DOTALL)
        
        if content != new_content:
            print(f"Fixed newlines in {filename}")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
        else:
            # Check if there are newlines that weren't caught or just no newlines
            pass

if __name__ == "__main__":
    fix_chunks()
