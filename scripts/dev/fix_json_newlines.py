import os

def fix_json_newlines(directory):
    files = sorted([f for f in os.listdir(directory) if f.endswith('.sql')])
    
    for filename in files:
        filepath = os.path.join(directory, filename)
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # Find JSON start and end
        # We assume the metadata JSON is the LAST quoted string cast to ::jsonb
        
        end_marker = b"'::jsonb);"
        end_idx = content.rfind(end_marker)
        
        if end_idx == -1:
            print(f"Skipping {filename}: No jsonb cast found")
            continue
            
        # Find the start. It ends with quote '.
        # We need to find the matching opening quote.
        # Since the JSON string might contain escaped quotes, we can't just search for '.
        # However, we know it starts after the previous field.
        # The previous field is 'content', which ends with ', 
        # So we look for b', \'' before the end_idx?
        
        # Or we can look for the start of the key "name": "..."
        # All our records start with {"name":
        # So look for b'\'{"name":'
        
        # But some might start with `{"license":` or other?
        # The schema is name, description, category, content, metadata
        # So metadata usually starts with `{"name":` (Wait, metadata repeats name?)
        # Let's check chunk_002
        # '{"name": "audit-website", ...
        
        start_marker = b"', '{"
        # This matches the comma, space, quote, brace.
        # Be careful if content ends with ', '{
        
        # Let's search backwards from end_idx for b"', '{" 
        # But be safe, search for b"'::jsonb);" then search backwards for b"'"
        # But we don't know where the string starts easily if it contains escaped quotes.
        
        # Try searching for b', \'{"' or b', \'{\n' or similar.
        # In our chunks, it seems consistent: ', '{"
        
        start_idx = content.rfind(b"', '{", 0, end_idx)
        if start_idx == -1:
            # Maybe it starts with just , '{ if no space?
            start_idx = content.rfind(b",'^{", 0, end_idx)
        
        if start_idx == -1:
            print(f"Skipping {filename}: Could not find start of JSON")
            continue
            
        # start_idx points to the comma? b"', '{"
        # The JSON string starts at start_idx + 4 (after ', ')
        # No, b"', '{" is len 4. index points to start.
        # So content[start_idx] is ','
        # content[start_idx+1] is ' '
        # content[start_idx+2] is "'"
        # content[start_idx+3] is "{"
        
        # Wait, the JSON string literal includes the opening '
        # content[start_idx+2] is the opening quote.
        
        json_start = start_idx + 3 # Points to {
        json_end = end_idx # Points to ' before ::
        
        # Verify
        # content[json_end] is "'"
        # content[json_start] is "{"
        
        json_bytes = content[json_start:json_end]
        
        # Replace newlines
        # 0x0A -> \\n (0x5C 0x6E)
        # 0x0D -> \\n (for CRLF, we might get \r\n -> \n\n if replace separately)
        # Better: replace b'\r\n' with b'\\n', then b'\n' with b'\\n', then b'\r' with b'\\n'
        
        if b'\n' in json_bytes or b'\r' in json_bytes:
            print(f"Fixing newlines in {filename}")
            
            fixed_json = json_bytes.replace(b'\r\n', b'\\n')
            fixed_json = fixed_json.replace(b'\n', b'\\n')
            fixed_json = fixed_json.replace(b'\r', b'\\n')
            
            new_content = content[:json_start] + fixed_json + content[json_end:]
            
            with open(filepath, 'wb') as f:
                f.write(new_content)
        else:
            # print(f"Clean: {filename}")
            pass

if __name__ == "__main__":
    fix_json_newlines(r'c:\Users\expert\Documents\PKA\Pikar-Ai\.tmp\sql_chunks')
