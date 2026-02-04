import os
import re

def combine_chunks(start, end, output_file):
    input_dir = r'c:\Users\expert\Documents\PKA\Pikar-Ai\.tmp\sql_chunks'
    
    combined_values = []
    
    print(f"Combining chunks {start} to {end}")
    
    for i in range(start, end + 1):
        filename = f"chunk_{i:03d}.sql"
        filepath = os.path.join(input_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"Warning: {filename} not found.")
            continue
            
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse content to get VALUES (...)
        # The file structure is:
        # INSERT INTO skills ... VALUES
        # (...);
        
        values_idx = content.find("VALUES")
        if values_idx == -1:
            print(f"Warning: No VALUES in {filename}")
            continue
            
        # Get content after VALUES
        raw_values = content[values_idx + 6:].strip()
        
        # Remove trailing semicolon
        if raw_values.endswith(';'):
            raw_values = raw_values[:-1]
            
        combined_values.append(raw_values.strip())
        
    if not combined_values:
        print("No values found to combine.")
        return
        
    # Create combined SQL
    header = "INSERT INTO skills (name, description, category, content, metadata)\nVALUES\n"
    body = ",\n".join(combined_values) + ";"
    
    full_sql = header + body
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_sql)
        
    print(f"Created {output_file} with {len(combined_values)} records.")

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("start", type=int)
    parser.add_argument("end", type=int)
    parser.add_argument("--output", help="Output file path")
    args = parser.parse_args()
    
    start_chunk = args.start
    end_chunk = args.end
    
    if args.output:
        output = args.output
    else:
        output = rf'c:\Users\expert\Documents\PKA\Pikar-Ai\.tmp\sql_chunks\combined_{start_chunk}_{end_chunk}.sql'
        
    combine_chunks(start_chunk, end_chunk, output)
