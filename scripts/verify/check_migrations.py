"""Verification script to detect migration collisions.
Fails if any migration files share the same numeric prefix (e.g., 0037_).
"""
import os
import sys

def check_migrations():
    migrations_dir = "supabase/migrations"
    if not os.path.exists(migrations_dir):
        print(f"Error: {migrations_dir} not found.")
        return False

    files = [f for f in os.listdir(migrations_dir) if f.endswith(".sql")]
    prefixes = {}
    collisions = []

    for f in files:
        prefix = f.split("_")[0]
        if prefix in prefixes:
            collisions.append((prefixes[prefix], f))
        prefixes[prefix] = f

    if collisions:
        print("ERROR: Migration prefix collisions detected!")
        for orig, collision in collisions:
            print(f"  - {orig} <-> {collision}")
        return False

    print("SUCCESS: No migration prefix collisions found.")
    return True

if __name__ == "__main__":
    if not check_migrations():
        sys.exit(1)
    sys.exit(0)
