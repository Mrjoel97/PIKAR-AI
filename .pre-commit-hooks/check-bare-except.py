#!/usr/bin/env python3
"""Check for bare except clauses in Python code."""

import re
import sys
from pathlib import Path


def check_file(filepath: str) -> list:
    """Check a Python file for bare except clauses."""
    errors = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            # Match bare except: (but not except Exception:)
            pattern = re.compile(r'^\s*except\s*:\s*$')
            
            for i, line in enumerate(lines, 1):
                if pattern.match(line):
                    errors.append(f"{filepath}:{i}: Bare except clause found")
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
