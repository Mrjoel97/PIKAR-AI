import os

def debug_chunk():
    filepath = r'c:\Users\expert\Documents\PKA\Pikar-Ai\.tmp\sql_chunks\chunk_002.sql'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"File length: {len(content)}")
    print("Last 200 chars:")
    print(repr(content[-200:]))
    
    # Check for the pattern manually
    # Looking for the start of the JSON metadata
    # It ends with '::jsonb);
    
    end_marker = "'::jsonb);"
    idx = content.rfind(end_marker)
    if idx == -1:
         print("End marker not found!")
         return

    # Find the start of the string literal before that
    # It should be the last quote before the end marker? 
    # The JSON string is '...}'::jsonb);
    # So it opens with ' somewhere.
    # But the content field before it also ends with '.
    # So we look for ', ' before the json string?
    
    # Let's verify what precedes the JSON
    # We expect: ', '{
    
    prefix_search_area = content[max(0, idx-500) : idx]
    # We look for ', '{ which indicates start of metadata
    
    # Note: content field ends with ', then comma, then space?
    
    print(f"Search area end: {repr(prefix_search_area[-100:])}")

if __name__ == "__main__":
    debug_chunk()
