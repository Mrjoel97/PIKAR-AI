import os
import re

def chunk_sql_file(input_file, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Fallback to latil-1 or cp1252 if utf-8 fails
        with open(input_file, 'r', encoding='cp1252') as f:
            content = f.read()

    print(f"File start: {repr(content[:200])}")
    
    # Simple string search
    start_idx = content.find("INSERT INTO skills")
    values_idx = content.find("VALUES", start_idx)
    
    if start_idx == -1 or values_idx == -1:
        print("Could not find INSERT...VALUES block")
        return
        
    insert_prefix = content[start_idx:values_idx + 6] # Include VALUES
    print(f"Prefix found: {insert_prefix}")
    
    values_content_start = values_idx + 6
    # Find the last semicolon
    end_idx = content.rfind(";")
    
    values_body = content[values_content_start:end_idx].strip()
    
    # Normalize line endings
    values_body = values_body.replace('\r\n', '\n')
    
    # Split
    # The pattern is `),\n`
    records = values_body.split('),\n')
    
    formatted_records = []
    for i, rec in enumerate(records):
        clean_rec = rec.strip()
        
        # Reconstruct
        if i < len(records) - 1:
            clean_rec += ")" # Add closing paren
            
        formatted_records.append(clean_rec)

    print(f"Found {len(formatted_records)} records.")
    
    chunk_index = 0
    current_chunk_records = []
    
    # Chunk 0: DELETE
    with open(os.path.join(output_dir, f"chunk_{chunk_index:03d}.sql"), 'w', encoding='utf-8') as f:
        f.write("BEGIN;\nDELETE FROM skills;\nCOMMIT;")
    chunk_index += 1
    
    for rec in formatted_records:
        current_chunk_records.append(rec)
        if len(current_chunk_records) >= 1: # 1 records per chunk
            with open(os.path.join(output_dir, f"chunk_{chunk_index:03d}.sql"), 'w', encoding='utf-8') as f:
                sql = insert_prefix + "\n" + ",\n".join(current_chunk_records) + ";"
                f.write(sql)
            current_chunk_records = []
            chunk_index += 1
            
    if current_chunk_records:
        with open(os.path.join(output_dir, f"chunk_{chunk_index:03d}.sql"), 'w', encoding='utf-8') as f:
            sql = insert_prefix + "\n" + ",\n".join(current_chunk_records) + ";"
            f.write(sql)
            
    print(f"Created {chunk_index + 1} chunks (including delete chunk).")

if __name__ == "__main__":
    chunk_sql_file(
        r'c:\Users\expert\Documents\PKA\Pikar-Ai\supabase\migrations\0020_seed_skills.sql',
        r'c:\Users\expert\Documents\PKA\Pikar-Ai\.tmp\sql_chunks'
    )
