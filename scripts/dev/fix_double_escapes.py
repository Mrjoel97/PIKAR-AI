import os

def fix_double_escapes(directory):
    files = sorted([f for f in os.listdir(directory) if f.endswith('.sql')])
    
    for filename in files:
        filepath = os.path.join(directory, filename)
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # Replace \\" with \"
        # In bytes: b'\\"' is 5c 22. b'\\\\"' is 5c 5c 22.
        
        # We target specifically \\" inside the file (which usually is in the JSON part)
        # But be careful not to break standard text if it had backslash at end of sentence? unlikely.
        
        pattern = b'\\\\"'
        replacement = b'\\"'
        
        if pattern in content:
            print(f"Fixing double escapes in {filename}")
            new_content = content.replace(pattern, replacement)
            with open(filepath, 'wb') as f:
                f.write(new_content)

if __name__ == "__main__":
    fix_double_escapes(r'c:\Users\expert\Documents\PKA\Pikar-Ai\.tmp\sql_chunks')
