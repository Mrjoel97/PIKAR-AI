def inspect_chunk(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
    
    needle = b"tracking plan"
    idx = 0
    while True:
        idx = content.find(needle, idx)
        if idx == -1:
            break
            
        print(f"Found at {idx}")
        start = max(0, idx - 10)
        end = min(len(content), idx + 20)
        snippet = content[start:end]
        print(f"Snippet: {snippet}")
        print(f"Hex: {snippet.hex(' ')}")
        idx += 1

if __name__ == "__main__":
    inspect_chunk(r'c:\Users\expert\Documents\PKA\Pikar-Ai\.tmp\sql_chunks\chunk_001.sql')
