import os
import sys

def read_chunks(start_idx, end_idx):
    output_dir = r'c:\Users\expert\Documents\PKA\Pikar-Ai\.tmp\sql_chunks'
    
    for i in range(start_idx, end_idx + 1):
        filename = f"chunk_{i:03d}.sql"
        filepath = os.path.join(output_dir, filename)
        
        if not os.path.exists(filepath):
            continue
            
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        print(f"--- START {filename} ---")
        print(content)
        print(f"--- END {filename} ---")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: read_chunks.py start_idx end_idx")
        sys.exit(1)
        
    start_idx = int(sys.argv[1])
    end_idx = int(sys.argv[2])
    read_chunks(start_idx, end_idx)
