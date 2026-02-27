import sys
import os

def cat_batch(start, count, chunks_dir):
    content = ""
    for i in range(start, start + count):
        filename = os.path.join(chunks_dir, f"chunk_{i:03d}.sql")
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                content += f.read() + "\n"
    print(content)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python cat_batch.py <start> <count>")
        sys.exit(1)
    
    start = int(sys.argv[1])
    count = int(sys.argv[2])
    chunks_dir = r'c:\Users\expert\Documents\PKA\Pikar-Ai\.tmp\sql_chunks'
    cat_batch(start, count, chunks_dir)
