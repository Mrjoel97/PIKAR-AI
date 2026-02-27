#!/usr/bin/env python3
"""Check for mutable default arguments in Python code."""

import re
import sys
from pathlib import Path


def check_file(filepath: str) -> list:
    """Check a Python file for mutable default arguments."""
    errors = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            # Match patterns like: def func(arg={}) or def func(arg=[])
            pattern = re.compile(r'def\s+\w+\s*\([^)]*=\s*(\[\s*\]|\{\s*\})')
            
            for i, line in enumerate(lines, 1):
                if pattern.search(line):
                    errors.append(f"{filepath}:{i}: Mutable default argument found")
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
    
    return errors


def main():
    """Main entry point."""
    files = sys.argv[1:]
    all_errors = []
    
    for filepath in files:
        if filepath.endswith('.py'):
            errors = check_file(filepath)
            all_errors.extend(errors)
    
    if all_errors:
        for error in all_errors:
            print(error, file=sys.stderr)
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
