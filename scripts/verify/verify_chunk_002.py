import os

def verify():
    filepath = r'c:\Users\expert\Documents\PKA\Pikar-Ai\.tmp\sql_chunks\chunk_002.sql'
    with open(filepath, 'rb') as f:
        content = f.read()
    
    end_marker = b"'::jsonb);"
    end_idx = content.rfind(end_marker)
    start_marker = b"', '{"
    start_idx = content.rfind(start_marker, 0, end_idx)
    
    if start_idx != -1 and end_idx != -1:
        json_bytes = content[start_idx+3 : end_idx] # skip ', '
        print(f"JSON repr: {repr(json_bytes)}")
        if b'\n' in json_bytes:
            print("FOUND NEWLINE")
        else:
            print("NO NEWLINE")
            
    else:
        print("Could not locate JSON block")

if __name__ == "__main__":
    verify()
