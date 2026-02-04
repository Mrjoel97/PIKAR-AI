import os

def check_008():
    filepath = r'c:\Users\expert\Documents\PKA\Pikar-Ai\.tmp\sql_chunks\chunk_008.sql'
    with open(filepath, 'rb') as f:
        content = f.read()
    
    # Look for the section mentioning "write copy for"
    # It is near the end in metadata
    
    needle = b'write copy for'
    idx = content.rfind(needle)
    if idx == -1:
        print("Not found needle")
    else:
        # Show surroundings
        start = max(0, idx - 20)
        end = min(len(content), idx + 20)
        snippet = content[start:end]
        print(f"Snippet: {repr(snippet)}")

if __name__ == "__main__":
    check_008()
